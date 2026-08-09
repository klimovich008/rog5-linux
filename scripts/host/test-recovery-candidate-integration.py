#!/usr/bin/env python3
"""End-to-end offline test for stable-recovery candidate execution plumbing.

The test composes the production packager and host-server core with testing
builds of the real fetcher, verifier, and framed responder. Only kexec itself
is replaced: the fake records descriptor hashes for load, execute, and unload.

When the ignored consumed P2 artifacts are present, the success case uses
their tracked candidate record. A tiny policy-valid fixture exercises the
same composition in clean clones and hosted CI.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest


REPO = Path(__file__).resolve().parents[2]
CONTROL_SOURCE = REPO / "tools/recovery_control/rog5-recovery-control.c"
FETCH_SOURCE = REPO / "tools/recovery_control/rog5-bundle-fetch.c"
VERIFY_SOURCE = REPO / "tools/recovery_control/rog5-bundle-verify.c"
P2_CANDIDATE = "persistent-root-p2-parity"
P2_MANIFEST_SHA256 = (
    "7dbabf68f532265d45f00e8521989577fd82da7a7b0dd461bae384fc82eea4fd"
)
ZERO_HASH = "0" * 64
SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")
FILES = (
    "manifest",
    "manifest.sig",
    "Image",
    "board.dtb",
    "initramfs.cpio.gz",
)


def load_module(name: str, path: Path):
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


PACKAGER = load_module(
    "rog5_candidate_integration_packager",
    REPO / "scripts/host/prepare-recovery-runtime-bundle.py",
)
CANDIDATE = load_module(
    "rog5_candidate_integration_adapter",
    REPO / "scripts/host/prepare-recovery-candidate.py",
)
SERVER = load_module(
    "rog5_candidate_integration_server",
    REPO / "tools/recovery_control/host_bundle_server.py",
)

sys.path.insert(0, str(REPO))
from tools.recovery_control import (  # noqa: E402
    FrameParser,
    PREPARE_PROGRESS_PHASES,
    Progress,
    Response,
    ZERO_ID,
    decode_recovery_record,
    encode_frame,
    encode_request,
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def request_id(number: int) -> str:
    return f"{number:032x}"


def newc_header(
    name: str,
    size: int,
    *,
    mode: int = 0o100644,
    inode: int = 1,
) -> bytes:
    encoded_name = name.encode("ascii") + b"\0"
    fields = (
        inode,
        mode,
        0,
        0,
        1,
        0,
        size,
        0,
        0,
        0,
        0,
        len(encoded_name),
        0,
    )
    header = b"070701" + "".join(
        f"{value:08x}" for value in fields
    ).encode("ascii")
    record = header + encoded_name
    return record + bytes((-len(record)) % 4)


def newc_entry(
    name: str,
    payload: bytes,
    *,
    mode: int,
    inode: int,
) -> bytes:
    return (
        newc_header(name, len(payload), mode=mode, inode=inode)
        + payload
        + bytes((-len(payload)) % 4)
    )


def minimal_initramfs() -> bytes:
    archive = bytearray()
    archive.extend(
        newc_entry(
            "init",
            b"#!/bin/sh\nexec /bin/sh\n",
            mode=0o100755,
            inode=1,
        )
    )
    archive.extend(newc_header("TRAILER!!!", 0, mode=0, inode=2))
    archive.extend(bytes((-len(archive)) % 512))
    return gzip.compress(bytes(archive), mtime=0)


def valid_dts() -> str:
    return """/dts-v1/;

/ {
\tmodel = "ASUS ROG Phone 5";
\tcompatible = "asus,rog-phone5", "qcom,sm8350";
\t#address-cells = <2>;
\t#size-cells = <2>;

\taliases {
\t\tserial0 = &uart2;
\t};

\tchosen {
\t\tstdout-path = "serial0:115200n8";
\t};

\tsoc@0 {
\t\tcompatible = "simple-bus";
\t\t#address-cells = <2>;
\t\t#size-cells = <2>;
\t\tranges = <0 0 0 0 0x10 0>;

\t\tgeniqup@9c0000 {
\t\t\tcompatible = "qcom,geni-se-qup";
\t\t\treg = <0 0x9c0000 0 0x6000>;
\t\t\t#address-cells = <2>;
\t\t\t#size-cells = <2>;
\t\t\tranges;
\t\t\tstatus = "okay";

\t\t\tuart2: serial@98c000 {
\t\t\t\tcompatible = "qcom,geni-debug-uart";
\t\t\t\treg = <0 0x98c000 0 0x4000>;
\t\t\t\tpinctrl-names = "default";
\t\t\t\tpinctrl-0 = <&uart2_default>;
\t\t\t\tstatus = "okay";
\t\t\t};
\t\t};

\t\tpinctrl@f100000 {
\t\t\tcompatible = "qcom,sm8350-tlmm";
\t\t\treg = <0 0xf100000 0 0x300000>;

\t\t\tuart2_default: qup-uart3-default-state {
\t\t\t\trx-pins {
\t\t\t\t\tpins = "gpio18";
\t\t\t\t\tfunction = "qup3";
\t\t\t\t};

\t\t\t\ttx-pins {
\t\t\t\t\tpins = "gpio19";
\t\t\t\t\tfunction = "qup3";
\t\t\t\t};
\t\t\t};
\t\t};
\t};

\treserved-memory {
\t\t#address-cells = <2>;
\t\t#size-cells = <2>;
\t\tranges;

\t\tmemory@9b800000 {
\t\t\tno-map;
\t\t\treg = <0 0x9b800000 0 0x400000>;
\t\t};

\t\tmemory@9bc00000 {
\t\t\tno-map;
\t\t\treg = <0 0x9bc00000 0 0x100000>;
\t\t};
\t};
};
"""


class CandidateIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        for command in ("dtc", "gcc", "openssl"):
            if shutil.which(command) is None:
                raise RuntimeError(f"{command} is required")
        cls.build = tempfile.TemporaryDirectory()
        cls.build_path = Path(cls.build.name)
        cls.control = cls.build_path / "rog5-recovery-control-test"
        cls.fetcher = cls.build_path / "rog5-bundle-fetch-test"
        cls.verifier = cls.build_path / "rog5-bundle-verify-test"
        common = [
            "gcc",
            "-std=c11",
            "-O2",
            "-fPIE",
            "-pie",
            "-fstack-protector-strong",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none",
        ]
        subprocess.run(
            [
                *common,
                "-DROG5_CONTROL_TESTING=1",
                str(CONTROL_SOURCE),
                "-o",
                str(cls.control),
            ],
            check=True,
            cwd=REPO,
        )
        subprocess.run(
            [
                *common,
                "-DROG5_FETCH_TESTING=1",
                str(FETCH_SOURCE),
                "-o",
                str(cls.fetcher),
            ],
            check=True,
            cwd=REPO,
        )
        subprocess.run(
            [
                *common,
                "-DROG5_BUNDLE_TESTING=1",
                str(VERIFY_SOURCE),
                "-o",
                str(cls.verifier),
                "-lcrypto",
                "-lz",
            ],
            check=True,
            cwd=REPO,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.build.cleanup()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.processes: list[subprocess.Popen] = []
        self.descriptors: list[int] = []
        self.server_threads: list[threading.Thread] = []
        self.server_errors: list[BaseException] = []
        self.private_key = self.root / "ephemeral-ed25519.pem"
        subprocess.run(
            [
                "openssl",
                "genpkey",
                "-algorithm",
                "ED25519",
                "-out",
                str(self.private_key),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self.private_key.chmod(0o600)
        public_der = subprocess.check_output(
            [
                "openssl",
                "pkey",
                "-in",
                str(self.private_key),
                "-pubout",
                "-outform",
                "DER",
            ],
            stderr=subprocess.PIPE,
        )
        if (
            not public_der.startswith(SPKI_PREFIX)
            or len(public_der) != len(SPKI_PREFIX) + 32
        ):
            raise RuntimeError("unexpected Ed25519 public-key encoding")
        self.public_key = self.root / "ephemeral-ed25519.pub"
        self.public_key.write_bytes(public_der[len(SPKI_PREFIX) :])
        self.public_key.chmod(0o400)

    def tearDown(self) -> None:
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
            if process.stderr is not None:
                process.stderr.close()
        for descriptor in self.descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass
        for thread in self.server_threads:
            thread.join(timeout=2)
        self.temporary.cleanup()

    def consumed_p2_available(self) -> bool:
        try:
            record = CANDIDATE.load_candidate(P2_CANDIDATE)
        except CANDIDATE.CandidateError:
            return False
        for artifact in record["artifacts"].values():
            path = REPO / artifact["path"]
            if (
                not path.is_file()
                or path.is_symlink()
                or path.stat().st_size != artifact["size"]
            ):
                return False
        return True

    def prepare_consumed_p2(self, bundle_root: Path) -> tuple[str, str]:
        _record, manifest_hash, _trust_hash = CANDIDATE.prepare(
            P2_CANDIDATE,
            self.private_key,
            bundle_root,
        )
        self.assertEqual(manifest_hash, P2_MANIFEST_SHA256)
        return P2_CANDIDATE, manifest_hash

    def prepare_synthetic_parity(self, bundle_root: Path) -> tuple[str, str]:
        sources = self.root / f"sources-{len(list(self.root.iterdir()))}"
        sources.mkdir(mode=0o700)
        image = bytearray(4096)
        struct.pack_into("<Q", image, 16, len(image))
        struct.pack_into("<Q", image, 24, 0xA)
        image[56:60] = b"ARM\x64"
        image[64:] = bytes(
            (index * 17 + 3) & 0xFF for index in range(len(image) - 64)
        )
        image_path = sources / "Image"
        image_path.write_bytes(image)
        dts = sources / "board.dts"
        dts.write_text(valid_dts(), encoding="ascii")
        dtb_path = sources / "board.dtb"
        subprocess.run(
            [
                "dtc",
                "-q",
                "-I",
                "dts",
                "-O",
                "dtb",
                "-o",
                str(dtb_path),
                str(dts),
            ],
            check=True,
            cwd=REPO,
        )
        initramfs_path = sources / "initramfs.cpio.gz"
        initramfs_path.write_bytes(minimal_initramfs())
        for path in (image_path, dtb_path, initramfs_path):
            path.chmod(0o400)
        config = PACKAGER.Configuration(
            bundle="persistent-root-p2-parity",
            profile="persistent-root-ro-v1",
            image=image_path,
            dtb=dtb_path,
            initramfs=initramfs_path,
            target_id="persistent-root-p2",
            target_release="7.1.4-ci-fixture",
            rollback_timeout="600",
            target_timeout="480",
            a660_command_manifest_sha256=ZERO_HASH,
            root_generation="none",
            root_tree_sha256=ZERO_HASH,
            root_seal_sha256=ZERO_HASH,
            root_tree_entries="0",
            root_subtree="none",
            private_key=self.private_key,
            bundle_root=bundle_root,
        )
        manifest_hash, _trust_hash = PACKAGER.prepare_bundle(config)
        return config.bundle, manifest_hash

    def prepare_source(
        self,
        name: str,
        *,
        actual_p2: bool,
    ) -> tuple[Path, str, str]:
        bundle_root = self.root / f"source-{name}"
        bundle_root.mkdir(mode=0o700)
        if actual_p2:
            bundle, manifest_hash = self.prepare_consumed_p2(bundle_root)
        else:
            bundle, manifest_hash = self.prepare_synthetic_parity(bundle_root)
        return bundle_root, bundle, manifest_hash

    def start_server(
        self,
        source_root: Path,
        bundle: str,
        manifest_hash: str,
    ) -> int:
        root_fd = os.open(
            source_root,
            os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC,
        )
        try:
            prepared = SERVER.prepare_bundle(
                root_fd,
                bundle,
                manifest_hash,
                os.geteuid(),
            )
        finally:
            os.close(root_fd)
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def serve() -> None:
            try:
                with listener, prepared:
                    SERVER.serve_listener(
                        listener,
                        prepared,
                        lambda peer: (
                            isinstance(peer, tuple)
                            and len(peer) >= 2
                            and peer[0] == "127.0.0.1"
                        ),
                        timeout_seconds=30,
                    )
            except BaseException as error:
                self.server_errors.append(error)

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        self.server_threads.append(thread)
        return port

    def write_wrappers(
        self,
        fetched_root: Path,
        port: int,
        expected: dict[str, str],
    ) -> tuple[Path, Path, Path, Path]:
        wrappers = self.root / f"wrappers-{port}"
        wrappers.mkdir(mode=0o700)
        events = wrappers / "kexec-events"
        fetch_wrapper = wrappers / "fetch"
        verify_wrapper = wrappers / "verify"
        kexec_wrapper = wrappers / "kexec"
        fetch_command = [
            str(self.fetcher),
            "--bundle-root",
            str(fetched_root),
            "--server-ip",
            "127.0.0.1",
            "--source-ip",
            "127.0.0.1",
            "--port",
            str(port),
            "--timeout-ms",
            "30000",
            "--worker-uid",
            str(os.geteuid()),
            "--worker-gid",
            str(os.getegid()),
            "--skip-device-bind",
        ]
        fetch_wrapper.write_text(
            "#!/bin/sh\n"
            "exec "
            + " ".join(shlex.quote(value) for value in fetch_command)
            + ' "$@"\n',
            encoding="ascii",
        )
        verify_command = [
            str(self.verifier),
            "--bundle-root",
            str(fetched_root),
            "--trust-key",
            str(self.public_key),
        ]
        verify_wrapper.write_text(
            "#!/bin/sh\n"
            "exec "
            + " ".join(shlex.quote(value) for value in verify_command)
            + ' "$@"\n',
            encoding="ascii",
        )
        kexec_wrapper.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/python3
                import hashlib
                import json
                from pathlib import Path
                import sys

                events = Path({str(events)!r})
                expected = {expected!r}
                arguments = sys.argv[1:]

                def record(value):
                    with events.open("a", encoding="ascii") as stream:
                        stream.write(json.dumps(value, sort_keys=True) + "\\n")

                if arguments == ["-c", "-u"]:
                    record({{"operation": "unload"}})
                    raise SystemExit(0)
                if arguments == ["-e"]:
                    record({{"operation": "execute"}})
                    raise SystemExit(0)
                if len(arguments) != 6 or arguments[:2] != ["-c", "-l"]:
                    raise SystemExit(80)
                paths = {{
                    "Image": arguments[2],
                    "initramfs.cpio.gz": arguments[3].removeprefix("--initrd="),
                    "board.dtb": arguments[4].removeprefix("--dtb="),
                }}
                observed = {{
                    name: hashlib.sha256(Path(path).read_bytes()).hexdigest()
                    for name, path in paths.items()
                }}
                if observed != expected:
                    raise SystemExit(81)
                command_line = arguments[5].removeprefix("--command-line=")
                if (
                    command_line == arguments[5]
                    or "rog5.ufs_discovery=1" not in command_line
                    or "rog5.persistent_ro=1" not in command_line
                    or "rog5.netroot=1" in command_line
                ):
                    raise SystemExit(82)
                record({{
                    "operation": "load",
                    "artifacts": observed,
                    "cmdline_sha256": hashlib.sha256(
                        command_line.encode("ascii")
                    ).hexdigest(),
                }})
                """
            ),
            encoding="utf-8",
        )
        for path in (fetch_wrapper, verify_wrapper, kexec_wrapper):
            path.chmod(0o700)
        return fetch_wrapper, verify_wrapper, kexec_wrapper, events

    def start_watchdog(self, root: Path) -> tuple[Path, subprocess.Popen]:
        watchdog = root / "watchdog"
        process = subprocess.Popen(
            ["sleep", "120"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.processes.append(process)
        record = Path(f"/proc/{process.pid}/stat").read_text(
            encoding="ascii"
        )
        fields = record[record.rfind(") ") + 2 :].split()
        watchdog.write_text(
            f"pid={process.pid}\nstarttime={fields[19]}\n",
            encoding="ascii",
        )
        watchdog.chmod(0o600)
        return watchdog, process

    def start_responder(
        self,
        name: str,
        manifest_hash: str,
        fetch_wrapper: Path,
        verify_wrapper: Path,
        kexec_wrapper: Path,
    ) -> tuple[subprocess.Popen, int, Path]:
        runtime = self.root / f"runtime-{name}"
        runtime.mkdir(mode=0o700)
        state = runtime / "state"
        state.mkdir(mode=0o700)
        watchdog, _watchdog_process = self.start_watchdog(runtime)
        postmortem = runtime / "postmortem.status"
        postmortem.write_text(
            "state=UNAVAILABLE\n"
            "records=0\n"
            "bytes=0\n"
            f"sha256={ZERO_HASH}\n"
            "tail_hex=none\n",
            encoding="ascii",
        )
        postmortem.chmod(0o600)
        postmortem_snapshot = runtime / "postmortem.snapshot"
        postmortem_snapshot.write_bytes(b"")
        postmortem_snapshot.chmod(0o600)
        master, slave = pty.openpty()
        self.descriptors.append(master)
        device = Path(os.ttyname(slave))
        os.close(slave)
        ready = runtime / "ready"
        environment = os.environ.copy()
        environment.update(
            {
                "ROG5_TEST_ALLOW_MANIFEST": manifest_hash,
                "ROG5_TEST_EXEC_MODE": "fixed_path",
                "ROG5_TEST_READY_FILE": str(ready),
                "ROG5_TEST_IO_TIMEOUT_MS": "2000",
                "ROG5_TEST_FETCH_TIMEOUT_MS": "60000",
                "ROG5_TEST_VERIFY_TIMEOUT_MS": "30000",
                "ROG5_TEST_LOAD_TIMEOUT_MS": "10000",
                "ROG5_TEST_FETCHER_PATH": str(fetch_wrapper),
                "ROG5_TEST_VERIFIER_PATH": str(verify_wrapper),
                "ROG5_TEST_KEXEC_PATH": str(kexec_wrapper),
            }
        )
        process = subprocess.Popen(
            [
                str(self.control),
                "--device",
                str(device),
                "--state-dir",
                str(state),
                "--watchdog",
                str(watchdog),
                "--postmortem",
                str(postmortem),
                "--postmortem-snapshot",
                str(postmortem_snapshot),
            ],
            cwd=REPO,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self.processes.append(process)
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if ready.exists():
                return process, master, state
            if process.poll() is not None:
                stderr = process.stderr.read().decode(errors="replace")
                self.fail(
                    "responder exited before opening the test TTY: "
                    f"{process.returncode}: {stderr}"
                )
            time.sleep(0.01)
        self.fail("responder did not configure the test TTY")
        raise AssertionError("unreachable")

    def read_response(
        self,
        master: int,
        timeout: float = 65,
        progress: list[Progress] | None = None,
    ) -> Response:
        parser = FrameParser()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            readable, _, _ = select.select(
                [master],
                [],
                [],
                max(0, deadline - time.monotonic()),
            )
            if not readable:
                break
            chunk = os.read(master, 8192)
            if not chunk:
                break
            payloads = parser.feed(chunk)
            if payloads:
                response = None
                for payload in payloads:
                    record = decode_recovery_record(payload)
                    if isinstance(record, Progress):
                        if response is not None:
                            self.fail("progress followed a terminal response")
                        if progress is None:
                            self.fail("unexpected progress for a fixed verb")
                        progress.append(record)
                    elif response is not None:
                        self.fail("responder returned multiple responses")
                    else:
                        response = record
                if response is not None:
                    return response
        self.fail("framed responder did not return one complete response")
        raise AssertionError("unreachable")

    def exchange(
        self,
        master: int,
        payload: bytes,
        timeout: float = 65,
        progress: list[Progress] | None = None,
    ) -> Response:
        os.write(master, encode_frame(payload))
        return self.read_response(master, timeout, progress)

    def hello(self, master: int) -> str:
        response = self.exchange(
            master,
            encode_request(
                session=ZERO_ID,
                request=request_id(1),
                verb="HELLO",
            ),
        )
        self.assertEqual(response.result, "OK")
        self.assertNotEqual(response.session, ZERO_ID)
        return response.session

    def run_prepare(
        self,
        master: int,
        session: str,
        bundle: str,
        manifest_hash: str,
    ) -> tuple[Response, list[Progress]]:
        progress: list[Progress] = []
        response = self.exchange(
            master,
            encode_request(
                session=session,
                request=request_id(10),
                verb="PREPARE",
                body={
                    "bundle": bundle,
                    "manifest_sha256": manifest_hash,
                },
            ),
            progress=progress,
        )
        return response, progress

    def assert_server_finished(self) -> None:
        for thread in self.server_threads:
            thread.join(timeout=35)
            self.assertFalse(thread.is_alive(), "bundle server did not finish")
        if self.server_errors:
            self.fail(f"bundle server failed: {self.server_errors[0]}")

    def artifact_hashes(self, source_root: Path, bundle: str) -> dict[str, str]:
        return {
            name: sha256((source_root / bundle / name).read_bytes())
            for name in ("Image", "board.dtb", "initramfs.cpio.gz")
        }

    def test_prepare_serve_verify_load_and_execute(self) -> None:
        actual_p2 = self.consumed_p2_available()
        source_root, bundle, manifest_hash = self.prepare_source(
            "success",
            actual_p2=actual_p2,
        )
        expected = self.artifact_hashes(source_root, bundle)
        fetched_root = self.root / "fetched-success"
        fetched_root.mkdir(mode=0o700)
        port = self.start_server(source_root, bundle, manifest_hash)
        fetch, verify, kexec, events = self.write_wrappers(
            fetched_root,
            port,
            expected,
        )
        process, master, state = self.start_responder(
            "success",
            manifest_hash,
            fetch,
            verify,
            kexec,
        )
        session = self.hello(master)
        prepared, progress = self.run_prepare(
            master, session, bundle, manifest_hash
        )
        self.assertEqual(
            [record.phase for record in progress],
            list(PREPARE_PROGRESS_PHASES),
        )
        for sequence, record in enumerate(progress, 1):
            self.assertEqual(record.sequence, sequence)
            self.assertEqual(record.session, session)
            self.assertEqual(record.request, request_id(10))
            self.assertEqual(record.bundle, bundle)
            self.assertEqual(record.manifest_sha256, manifest_hash)
            self.assertEqual(record.watchdog, "ARMED")
        self.assertEqual(prepared.result, "PREPARED")
        commit = self.exchange(
            master,
            encode_request(
                session=session,
                request=request_id(11),
                verb="COMMIT_EXEC",
                body={
                    "prepare_request": request_id(10),
                    "manifest_sha256": manifest_hash,
                },
            ),
        )
        self.assertEqual(commit.result, "CLAIMED")
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not (state / "failure").exists():
            time.sleep(0.01)
        self.assertEqual(
            (state / "failure").read_text(encoding="ascii"),
            "error=EXEC_RETURNED\n",
        )
        self.assert_server_finished()
        fetched_bundle = fetched_root / bundle
        self.assertEqual(
            {path.name for path in fetched_bundle.iterdir()},
            set(FILES),
        )
        for name in FILES:
            self.assertEqual(
                sha256((fetched_bundle / name).read_bytes()),
                sha256((source_root / bundle / name).read_bytes()),
            )
        records = [
            json.loads(line)
            for line in events.read_text(encoding="ascii").splitlines()
        ]
        operations = [record["operation"] for record in records]
        self.assertEqual(
            operations,
            ["unload", "load", "execute", "unload"],
        )
        self.assertEqual(records[1]["artifacts"], expected)
        self.assertRegex(records[1]["cmdline_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual((state / "execution-started").stat().st_mode & 0o777, 0o600)
        self.assertIsNone(process.poll())
        print(
            "PASS stable-recovery composition fixture="
            + ("consumed-p2" if actual_p2 else "synthetic-ci")
        )

    def test_signature_mutation_never_reaches_load(self) -> None:
        source_root, bundle, manifest_hash = self.prepare_source(
            "mutated-signature",
            actual_p2=False,
        )
        signature = source_root / bundle / "manifest.sig"
        payload = bytearray(signature.read_bytes())
        payload[0] ^= 1
        signature.chmod(0o600)
        signature.write_bytes(payload)
        signature.chmod(0o400)
        expected = self.artifact_hashes(source_root, bundle)
        fetched_root = self.root / "fetched-mutated"
        fetched_root.mkdir(mode=0o700)
        port = self.start_server(source_root, bundle, manifest_hash)
        fetch, verify, kexec, events = self.write_wrappers(
            fetched_root,
            port,
            expected,
        )
        _process, master, _state = self.start_responder(
            "mutated-signature",
            manifest_hash,
            fetch,
            verify,
            kexec,
        )
        session = self.hello(master)
        response, progress = self.run_prepare(
            master, session, bundle, manifest_hash
        )
        self.assertEqual(
            [record.phase for record in progress],
            list(PREPARE_PROGRESS_PHASES[:2]),
        )
        self.assertEqual(response.result, "VERIFY_FAILED")
        self.assert_server_finished()
        operations = [
            json.loads(line)["operation"]
            for line in events.read_text(encoding="ascii").splitlines()
        ]
        self.assertEqual(operations, ["unload"])


if __name__ == "__main__":
    unittest.main()
