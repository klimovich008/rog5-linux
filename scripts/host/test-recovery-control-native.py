#!/usr/bin/env python3
"""Pseudo-terminal tests for the native recovery control responder."""

from __future__ import annotations

import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import socket
import subprocess
import tempfile
import termios
import textwrap
import time
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "tools/recovery_control/rog5-recovery-control.c"

import sys

sys.path.insert(0, str(REPO))

from tools.recovery_control import (  # noqa: E402
    FrameParser,
    PREPARE_PROGRESS_PHASES,
    Progress,
    RecoveryModel,
    RecoveryState,
    Response,
    ZERO_ID,
    decode_recovery_record,
    decode_request,
    decode_response,
    encode_frame,
    encode_request,
)
from tools.recovery_control.host_progress_collector import (  # noqa: E402
    collect_connection,
)


MANIFEST = "a" * 64
OTHER_MANIFEST = "b" * 64


def request_id(number: int) -> str:
    return f"{number:032x}"


class NativeResponderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory()
        override = os.environ.get("ROG5_CONTROL_TEST_BINARY")
        cls.runner = shlex.split(
            os.environ.get("ROG5_CONTROL_TEST_RUNNER", "")
        )
        cls.binary = (
            Path(override)
            if override is not None
            else Path(cls.build.name) / "rog5-recovery-control-test"
        )
        cls.production = Path(cls.build.name) / "rog5-recovery-control"
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
                str(SOURCE),
        ]
        if override is None:
            subprocess.run(
                [
                    *common[:-1],
                    "-DROG5_CONTROL_TESTING=1",
                    common[-1],
                    "-o",
                    str(cls.binary),
                ],
                check=True,
                cwd=REPO,
            )
        elif not cls.binary.is_file():
            raise RuntimeError("ROG5_CONTROL_TEST_BINARY is not a file")
        subprocess.run(
            [*common, "-o", str(cls.production)],
            check=True,
            cwd=REPO,
        )

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.state = self.root / "state"
        self.state.mkdir(mode=0o700)
        self.watchdog = self.root / "watchdog"
        self.postmortem = self.root / "postmortem.status"
        self.postmortem.write_text(
            "state=UNAVAILABLE\n"
            "records=0\n"
            "bytes=0\n"
            f"sha256={'0' * 64}\n"
            "tail_hex=none\n",
            encoding="ascii",
        )
        self.postmortem.chmod(0o600)
        self.processes: list[subprocess.Popen] = []
        self.descriptors: list[int] = []
        self.start_watchdog()

    def start_watchdog(self) -> subprocess.Popen:
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
        starttime = fields[19]
        self.watchdog.write_text(
            f"pid={process.pid}\nstarttime={starttime}\n",
            encoding="ascii",
        )
        self.watchdog.chmod(0o600)
        self.watchdog_process = process
        return process

    def stop_watchdog(self) -> None:
        if self.watchdog_process.poll() is None:
            self.watchdog_process.terminate()
            self.watchdog_process.wait(timeout=2)

    def tearDown(self):
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
        self.temporary.cleanup()

    def start(
        self,
        *,
        crash: str | None = None,
        execute: str = "depart",
        device: Path | None = None,
        reply_delay_ms: int = 0,
        io_timeout_ms: int = 500,
        write_chunk: bool = False,
        drain_stall: str | None = None,
        execute_delay_ms: int = 0,
        persist_crash: str | None = None,
        fetcher_path: Path | None = None,
        verifier_path: Path | None = None,
        kexec_path: Path | None = None,
        fetch_timeout_ms: int | None = None,
        verify_timeout_ms: int | None = None,
        load_timeout_ms: int | None = None,
        progress_fail_at: int | None = None,
        ncm_progress_fd: int | None = None,
        ncm_partial_at: int | None = None,
    ) -> tuple[subprocess.Popen, int]:
        master, slave = pty.openpty()
        self.descriptors.append(master)
        slave_path = Path(os.ttyname(slave))
        self.last_slave_path = slave_path
        if device is None:
            device = slave_path
        elif not device.exists():
            device.symlink_to(slave_path)
        os.close(slave)

        ready = self.state / "test-ready"
        ready.unlink(missing_ok=True)
        environment = os.environ.copy()
        environment.update(
            {
                "ROG5_TEST_ALLOW_MANIFEST": MANIFEST,
                "ROG5_TEST_EXEC_MODE": execute,
                "ROG5_TEST_READY_FILE": str(ready),
                "ROG5_TEST_REPLY_DELAY_MS": str(reply_delay_ms),
                "ROG5_TEST_IO_TIMEOUT_MS": str(io_timeout_ms),
                "ROG5_TEST_EXEC_DELAY_MS": str(execute_delay_ms),
            }
        )
        if crash is not None:
            environment["ROG5_TEST_CRASH"] = crash
        if write_chunk:
            environment["ROG5_TEST_WRITE_CHUNK"] = "1"
        if drain_stall is not None:
            environment["ROG5_TEST_DRAIN_STALL"] = drain_stall
        if persist_crash is not None:
            environment["ROG5_TEST_PERSIST_CRASH"] = persist_crash
        if verifier_path is not None:
            if fetcher_path is None:
                fetcher_path = verifier_path.with_name("fake-fetcher")
            if kexec_path is None or not fetcher_path.is_file():
                self.fail("test PREPARE paths must be configured together")
            environment["ROG5_TEST_FETCHER_PATH"] = str(fetcher_path)
            environment["ROG5_TEST_VERIFIER_PATH"] = str(verifier_path)
            environment["ROG5_TEST_KEXEC_PATH"] = str(kexec_path)
        elif fetcher_path is not None or kexec_path is not None:
            self.fail("test PREPARE paths must be configured together")
        if fetch_timeout_ms is not None:
            environment["ROG5_TEST_FETCH_TIMEOUT_MS"] = str(
                fetch_timeout_ms
            )
        if verify_timeout_ms is not None:
            environment["ROG5_TEST_VERIFY_TIMEOUT_MS"] = str(
                verify_timeout_ms
            )
        if load_timeout_ms is not None:
            environment["ROG5_TEST_LOAD_TIMEOUT_MS"] = str(load_timeout_ms)
        if progress_fail_at is not None:
            environment["ROG5_TEST_PROGRESS_FAIL_AT"] = str(
                progress_fail_at
            )
        if ncm_progress_fd is not None:
            environment["ROG5_TEST_NCM_PROGRESS_FD"] = str(
                ncm_progress_fd
            )
        if ncm_partial_at is not None:
            environment["ROG5_TEST_NCM_PROGRESS_PARTIAL_AT"] = str(
                ncm_partial_at
            )
        process = subprocess.Popen(
            [
                *self.runner,
                str(self.binary),
                "--device",
                str(device),
                "--state-dir",
                str(self.state),
                "--watchdog",
                str(self.watchdog),
                "--postmortem",
                str(self.postmortem),
            ],
            cwd=REPO,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            pass_fds=(ncm_progress_fd,) if ncm_progress_fd is not None else (),
        )
        self.processes.append(process)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if ready.exists():
                break
            if process.poll() is not None:
                stderr = process.stderr.read().decode(errors="replace")
                self.fail(
                    f"responder exited before opening the TTY: "
                    f"{process.returncode}: {stderr}"
                )
            time.sleep(0.01)
        else:
            self.fail("responder did not report a configured raw TTY")
        return process, master

    def read_payloads(
        self,
        master: int,
        count: int = 1,
        timeout: float = 2,
        read_size: int = 8192,
    ) -> list[bytes]:
        parser = FrameParser()
        payloads: list[bytes] = []
        deadline = time.monotonic() + timeout
        while len(payloads) < count and time.monotonic() < deadline:
            readable, _, _ = select.select(
                [master],
                [],
                [],
                max(0, deadline - time.monotonic()),
            )
            if not readable:
                break
            try:
                chunk = os.read(master, read_size)
            except OSError:
                break
            if not chunk:
                break
            payloads.extend(parser.feed(chunk))
        return payloads

    def exchange(
        self,
        master: int,
        payload: bytes,
        *,
        fragments: bool = False,
        response_read_size: int = 8192,
    ):
        records = self.exchange_records(
            master,
            payload,
            fragments=fragments,
            response_read_size=response_read_size,
        )
        self.assertIsInstance(records[-1], Response)
        return records[-1]

    def exchange_records(
        self,
        master: int,
        payload: bytes,
        *,
        fragments: bool = False,
        response_read_size: int = 8192,
    ) -> list[Response | Progress]:
        frame = encode_frame(payload)
        if fragments:
            for byte in frame:
                os.write(master, bytes([byte]))
        else:
            os.write(master, frame)
        parser = FrameParser()
        records: list[Response | Progress] = []
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            readable, _, _ = select.select(
                [master],
                [],
                [],
                max(0, deadline - time.monotonic()),
            )
            if not readable:
                break
            try:
                chunk = os.read(master, response_read_size)
            except OSError:
                break
            if not chunk:
                break
            for framed_payload in parser.feed(chunk):
                record = decode_recovery_record(framed_payload)
                records.append(record)
                if isinstance(record, Response):
                    return records
        self.fail("responder did not return a terminal response")

    def hello(self, master: int, number: int = 1) -> str:
        response = self.exchange(
            master,
            encode_request(
                session=ZERO_ID,
                request=request_id(number),
                verb="HELLO",
            ),
        )
        self.assertEqual(response.result, "OK")
        self.assertNotEqual(response.session, ZERO_ID)
        return response.session

    def status(self, master: int, session: str, number: int):
        return self.exchange(
            master,
            encode_request(
                session=session,
                request=request_id(number),
                verb="STATUS",
            ),
        )

    def prepare(self, master: int, session: str, number: int = 10):
        return self.exchange(
            master,
            encode_request(
                session=session,
                request=request_id(number),
                verb="PREPARE",
                body={
                    "bundle": "arch-v1",
                    "manifest_sha256": MANIFEST,
                },
            ),
        )

    def commit_payload(
        self,
        session: str,
        number: int = 11,
        prepare_number: int = 10,
    ) -> bytes:
        return encode_request(
            session=session,
            request=request_id(number),
            verb="COMMIT_EXEC",
            body={
                "prepare_request": request_id(prepare_number),
                "manifest_sha256": MANIFEST,
            },
        )

    def make_prepare_pipeline(
        self,
        name: str,
        *,
        fetcher_mode: str = "ok",
        verifier_mode: str = "ok",
        loader_mode: str = "ok",
    ) -> tuple[Path, Path, Path]:
        pipeline = self.root / f"pipeline-{name}"
        pipeline.mkdir(mode=0o700)
        artifacts = pipeline / "artifacts"
        artifacts.mkdir(mode=0o700)
        content = {
            "Image": b"K" * 64,
            "board.dtb": b"D" * 40,
            "initramfs.cpio.gz": b"I" * 2,
        }
        for filename, payload in content.items():
            path = artifacts / filename
            path.write_bytes(payload)
            path.chmod(0o600)
        marker = pipeline / "load-marker"
        unload_marker = pipeline / "unload-marker"
        loaded_state = pipeline / "loaded-state"
        events = pipeline / "events"
        fetcher_pid = pipeline / "fetcher-pid"
        fetcher_worker_pid = pipeline / "fetcher-worker-pid"
        fetcher_runs = pipeline / "fetcher-runs"
        verifier_pid = pipeline / "verifier-pid"
        verifier_runs = pipeline / "verifier-runs"
        loader_pid = pipeline / "loader-pid"
        executor_pid = pipeline / "executor-pid"
        executor_marker = pipeline / "executor-marker"
        fetcher = pipeline / "fake-fetcher"
        verifier = pipeline / "fake-verifier"
        loader = pipeline / "fake-kexec"
        artifact_paths = [
            str(artifacts / "Image"),
            str(artifacts / "board.dtb"),
            str(artifacts / "initramfs.cpio.gz"),
        ]
        fetcher.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/python3
                import ctypes
                import os
                from pathlib import Path
                import signal
                import sys
                import time

                mode = {fetcher_mode!r}
                Path({str(fetcher_pid)!r}).write_text(
                    str(os.getpid()), encoding="ascii"
                )
                with Path({str(fetcher_runs)!r}).open(
                    "a", encoding="ascii"
                ) as stream:
                    stream.write("run\\n")
                with Path({str(events)!r}).open(
                    "a", encoding="ascii"
                ) as stream:
                    stream.write("fetch\\n")
                if (
                    len(sys.argv) != 3
                    or sys.argv[1] != "arch-v1"
                    or sys.argv[2] != {MANIFEST!r}
                ):
                    raise SystemExit(80)
                if mode == "hang":
                    time.sleep(5)
                if mode == "nested_hang":
                    parent = os.getpid()
                    child = os.fork()
                    if child == 0:
                        libc = ctypes.CDLL(None, use_errno=True)
                        if (
                            libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0
                            or os.getppid() != parent
                        ):
                            os._exit(82)
                        Path({str(fetcher_worker_pid)!r}).write_text(
                            str(os.getpid()), encoding="ascii"
                        )
                        time.sleep(5)
                        os._exit(0)
                    os.waitpid(child, 0)
                if mode == "conflict":
                    raise SystemExit(42)
                if mode == "fail":
                    raise SystemExit(9)
                if mode.startswith("exit-"):
                    raise SystemExit(int(mode.removeprefix("exit-")))
                if mode != "ok":
                    raise SystemExit(81)
                """
            ),
            encoding="utf-8",
        )
        verifier.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/python3
                import array
                import fcntl
                import hashlib
                import os
                from pathlib import Path
                import socket
                import sys
                import time

                mode = {verifier_mode!r}
                paths = {artifact_paths!r}
                Path({str(verifier_pid)!r}).write_text(
                    str(os.getpid()), encoding="ascii"
                )
                with Path({str(verifier_runs)!r}).open(
                    "a", encoding="ascii"
                ) as stream:
                    stream.write("run\\n")
                with Path({str(events)!r}).open(
                    "a", encoding="ascii"
                ) as stream:
                    stream.write("verify\\n")
                if sys.argv[1] != "--handoff-fd3" or len(sys.argv) != 4:
                    raise SystemExit(80)
                if mode == "hang":
                    time.sleep(5)
                if mode == "no_packet":
                    raise SystemExit(9)
                bundle = sys.argv[2]
                manifest = sys.argv[3]
                if mode == "wrong_manifest":
                    manifest = "b" * 64
                command = (
                    "console=ttyMSM0,115200n8 rdinit=/init "
                    "rog5.bundle=" + bundle
                )
                command_hash = hashlib.sha256(
                    command.encode("ascii")
                ).hexdigest()
                if mode == "wrong_command_hash":
                    command_hash = "b" * 64
                format_name = (
                    "rog5-corrupt-plan-v1"
                    if mode == "malformed_plan"
                    else "rog5-verified-plan-v1"
                )
                plan = (
                    f"format={{format_name}}\\n"
                    f"bundle={{bundle}}\\n"
                    f"manifest_sha256={{manifest}}\\n"
                    "profile=network-root-v1\\n"
                    "kernel_file=Image\\n"
                    "dtb_file=board.dtb\\n"
                    "initramfs_file=initramfs.cpio.gz\\n"
                    "target_id=rog5-test\\n"
                    "target_release=test-1\\n"
                    "target_timeout=90\\n"
                    f"cmdline_sha256={{command_hash}}\\n"
                    f"cmdline={{command}}\\n"
                ).encode("ascii")
                if mode == "extra_plan_field":
                    plan = plan.replace(
                        b"cmdline=",
                        b"unexpected=value\\ncmdline=",
                    )
                if mode == "embedded_nul":
                    plan += b"\\0"
                if mode == "oversized_plan":
                    plan += b"X" * 2048
                required_seals = (
                    fcntl.F_SEAL_SEAL
                    | fcntl.F_SEAL_SHRINK
                    | fcntl.F_SEAL_GROW
                    | fcntl.F_SEAL_WRITE
                )
                descriptors = []
                for index, path in enumerate(paths):
                    descriptor = os.memfd_create(
                        f"rog5-test-{{index}}",
                        os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
                    )
                    with open(path, "rb") as stream:
                        payload = stream.read()
                    os.write(descriptor, payload)
                    os.fchmod(descriptor, 0o400)
                    fcntl.fcntl(
                        descriptor,
                        fcntl.F_ADD_SEALS,
                        required_seals,
                    )
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    descriptors.append(descriptor)
                if mode == "unsafe_descriptor":
                    os.close(descriptors[1])
                    descriptors[1] = os.open(
                        os.path.dirname(paths[1]), os.O_RDONLY
                    )
                if mode == "aliased_descriptor":
                    os.close(descriptors[1])
                    descriptors[1] = os.dup(descriptors[0])
                if mode == "unsealed_descriptor":
                    os.close(descriptors[0])
                    descriptors[0] = os.memfd_create(
                        "rog5-test-unsealed",
                        os.MFD_CLOEXEC | os.MFD_ALLOW_SEALING,
                    )
                    with open(paths[0], "rb") as stream:
                        os.write(descriptors[0], stream.read())
                    os.fchmod(descriptors[0], 0o400)
                    os.lseek(descriptors[0], 0, os.SEEK_SET)
                if mode == "nonzero_offset":
                    os.lseek(descriptors[0], 1, os.SEEK_SET)
                extra_descriptors = []
                if mode == "four_rights":
                    extra_descriptors.append(os.dup(descriptors[0]))
                if mode == "sixteen_rights":
                    for _ in range(13):
                        extra_descriptors.append(
                            os.dup(descriptors[0])
                        )
                if mode == "maximum_rights":
                    for _ in range(250):
                        extra_descriptors.append(
                            os.dup(descriptors[0])
                        )
                sent = (
                    descriptors[:2]
                    if mode == "wrong_fd_count"
                    else descriptors + extra_descriptors
                )
                control = array.array("i", sent)
                channel = socket.socket(fileno=3)
                channel.sendmsg(
                    [b"" if mode == "zero_packet_rights" else plan],
                    [(socket.SOL_SOCKET, socket.SCM_RIGHTS, control)],
                )
                channel.close()
                for descriptor in descriptors:
                    os.close(descriptor)
                for descriptor in extra_descriptors:
                    os.close(descriptor)
                if mode == "hang_after_send":
                    time.sleep(5)
                if mode == "fail_after_send":
                    raise SystemExit(9)
                """
            ),
            encoding="utf-8",
        )
        loader.write_text(
            textwrap.dedent(
                f"""\
                #!/usr/bin/python3
                import os
                from pathlib import Path
                import sys
                import time

                mode = {loader_mode!r}
                paths = [
                    Path(value) for value in {artifact_paths!r}
                ]
                marker = Path({str(marker)!r})
                unload_marker = Path({str(unload_marker)!r})
                loaded_state = Path({str(loaded_state)!r})
                executor_pid = Path({str(executor_pid)!r})
                executor_marker = Path({str(executor_marker)!r})
                expected = {
                    {
                        "Image": content["Image"].hex(),
                        "board.dtb": content["board.dtb"].hex(),
                        "initramfs.cpio.gz":
                            content["initramfs.cpio.gz"].hex(),
                    }!r
                }
                if sys.argv[1:] == ["-c", "-u"]:
                    if mode == "unload_fail":
                        raise SystemExit(9)
                    with unload_marker.open(
                        "a", encoding="ascii"
                    ) as stream:
                        stream.write("unloaded\\n")
                    loaded_state.unlink(missing_ok=True)
                    raise SystemExit(0)
                if sys.argv[1:] == ["-e"]:
                    executor_pid.write_text(
                        str(os.getpid()), encoding="ascii"
                    )
                    if not loaded_state.is_file():
                        raise SystemExit(90)
                    if mode == "exec_hang":
                        time.sleep(5)
                    if mode == "exec_fail":
                        raise SystemExit(9)
                    executor_marker.write_text(
                        "returned\\n", encoding="ascii"
                    )
                    raise SystemExit(0)
                Path({str(loader_pid)!r}).write_text(
                    str(os.getpid()), encoding="ascii"
                )
                with Path({str(events)!r}).open(
                    "a", encoding="ascii"
                ) as stream:
                    stream.write("load\\n")
                if mode == "hang":
                    time.sleep(5)
                if mode == "fail":
                    raise SystemExit(9)
                if (
                    len(sys.argv) != 7
                    or sys.argv[1] != "-c"
                    or sys.argv[2] != "-l"
                ):
                    raise SystemExit(81)
                if mode == "hang_after_load":
                    loaded_state.write_text(
                        "loaded\\n", encoding="ascii"
                    )
                    with marker.open("a", encoding="ascii") as stream:
                        stream.write("loaded\\n")
                    time.sleep(5)
                if mode == "count":
                    loaded_state.write_text(
                        "loaded\\n", encoding="ascii"
                    )
                    with marker.open("a", encoding="ascii") as stream:
                        stream.write("loaded\\n")
                    raise SystemExit(0)
                kernel = sys.argv[3]
                initramfs = sys.argv[4].removeprefix("--initrd=")
                dtb = sys.argv[5].removeprefix("--dtb=")
                if not sys.argv[4].startswith("--initrd=/proc/self/fd/"):
                    raise SystemExit(82)
                if not sys.argv[5].startswith("--dtb=/proc/self/fd/"):
                    raise SystemExit(83)
                if not sys.argv[6].startswith("--command-line="):
                    raise SystemExit(84)
                replacement = {{
                    "Image": b"R" * 64,
                    "board.dtb": b"S" * 40,
                    "initramfs.cpio.gz": b"T" * 2,
                }}
                for path in paths:
                    temporary = path.with_name("." + path.name + ".new")
                    temporary.write_bytes(replacement[path.name])
                    temporary.chmod(0o600)
                    os.replace(temporary, path)
                observed = {{
                    "Image": Path(kernel).read_bytes().hex(),
                    "board.dtb": Path(dtb).read_bytes().hex(),
                    "initramfs.cpio.gz":
                        Path(initramfs).read_bytes().hex(),
                }}
                if observed != expected:
                    raise SystemExit(85)
                loaded_state.write_text(
                    "loaded\\n", encoding="ascii"
                )
                marker.write_text(
                    "\\n".join(sys.argv[1:]) + "\\n",
                    encoding="ascii",
                )
                """
            ),
            encoding="utf-8",
        )
        fetcher.chmod(0o700)
        verifier.chmod(0o700)
        loader.chmod(0o700)
        return verifier, loader, marker

    def wait_exit(self, process: subprocess.Popen) -> None:
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.fail("responder did not reach the injected exit")

    def wait_pid_file(self, path: Path) -> int:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                value = path.read_text(encoding="ascii").strip()
            except FileNotFoundError:
                value = ""
            if value.isdecimal() and int(value) > 0:
                return int(value)
            time.sleep(0.01)
        self.fail(f"child PID file did not become complete: {path}")
        raise AssertionError("unreachable")

    def assert_process_gone(self, pid: int) -> None:
        deadline = time.monotonic() + 2
        process = Path(f"/proc/{pid}")
        while time.monotonic() < deadline:
            if not process.exists():
                return
            time.sleep(0.01)
        self.fail(f"process {pid} remained after its lifecycle deadline")

    def stop_responder(
        self,
        process: subprocess.Popen,
        master: int,
    ) -> None:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=2)
        if process.stderr is not None:
            process.stderr.close()
        self.processes.remove(process)
        os.close(master)
        self.descriptors.remove(master)

    def run_startup_probe(self, state: Path) -> subprocess.CompletedProcess:
        environment = os.environ.copy()
        environment.update(
            {
                "ROG5_TEST_ALLOW_MANIFEST": MANIFEST,
                "ROG5_TEST_EXEC_MODE": "depart",
                "ROG5_TEST_REPLY_DELAY_MS": "0",
            }
        )
        return subprocess.run(
            [
                *self.runner,
                str(self.binary),
                "--device",
                "/dev/null",
                "--state-dir",
                str(state),
                "--watchdog",
                str(self.watchdog),
                "--postmortem",
                str(self.postmortem),
            ],
            cwd=REPO,
            env=environment,
            text=True,
            capture_output=True,
            timeout=2,
            check=False,
        )

    def test_delayed_open_fragmentation_coalescing_and_no_echo(self):
        device = self.root / "delayed-tty"
        master, slave = pty.openpty()
        self.descriptors.append(master)
        slave_path = Path(os.ttyname(slave))
        os.close(slave)

        ready = self.state / "test-ready"
        environment = os.environ.copy()
        environment.update(
            {
                "ROG5_TEST_ALLOW_MANIFEST": MANIFEST,
                "ROG5_TEST_EXEC_MODE": "depart",
                "ROG5_TEST_READY_FILE": str(ready),
                "ROG5_TEST_REPLY_DELAY_MS": "0",
            }
        )
        process = subprocess.Popen(
            [
                *self.runner,
                str(self.binary),
                "--device",
                str(device),
                "--state-dir",
                str(self.state),
                "--watchdog",
                str(self.watchdog),
                "--postmortem",
                str(self.postmortem),
            ],
            cwd=REPO,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self.processes.append(process)
        time.sleep(0.1)
        self.assertIsNone(process.poll())
        self.assertFalse(ready.exists())
        device.symlink_to(slave_path)

        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not ready.exists():
            time.sleep(0.01)
        self.assertTrue(ready.exists())

        hello = encode_request(
            session=ZERO_ID,
            request=request_id(1),
            verb="HELLO",
        )
        hello_response = self.exchange(
            master,
            hello,
            fragments=True,
            response_read_size=1,
        )
        session = hello_response.session

        first = encode_request(
            session=session,
            request=request_id(2),
            verb="STATUS",
        )
        second = encode_request(
            session=session,
            request=request_id(3),
            verb="STATUS",
        )
        os.write(master, encode_frame(first) + encode_frame(second))
        responses = [
            decode_response(payload)
            for payload in self.read_payloads(master, count=2)
        ]
        self.assertEqual([item.request for item in responses], [
            request_id(2),
            request_id(3),
        ])
        self.assertEqual([item.result for item in responses], ["OK", "OK"])

    def test_watchdog_death_while_waiting_for_tty_is_terminal(self):
        device = self.root / "never-created-tty"
        ready = self.state / "test-ready"
        environment = os.environ.copy()
        environment.update(
            {
                "ROG5_TEST_ALLOW_MANIFEST": MANIFEST,
                "ROG5_TEST_EXEC_MODE": "depart",
                "ROG5_TEST_READY_FILE": str(ready),
                "ROG5_TEST_IO_TIMEOUT_MS": "200",
            }
        )
        process = subprocess.Popen(
            [
                *self.runner,
                str(self.binary),
                "--device",
                str(device),
                "--state-dir",
                str(self.state),
                "--watchdog",
                str(self.watchdog),
                "--postmortem",
                str(self.postmortem),
            ],
            cwd=REPO,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        self.processes.append(process)
        time.sleep(0.1)
        self.assertIsNone(process.poll())
        self.assertFalse(ready.exists())
        self.stop_watchdog()
        self.wait_exit(process)
        stderr = process.stderr.read().decode(errors="replace")
        self.assertIn("watchdog process died while waiting", stderr)

    def test_shell_text_and_malformed_frame_never_execute(self):
        process, master = self.start()
        os.write(master, b"kexec -e\n")
        self.assertEqual(self.read_payloads(master, timeout=0.2), [])
        time.sleep(0.1)
        self.assertFalse((self.state / "execution-started").exists())
        self.assertFalse((self.state / "test-executed").exists())
        self.assertIsNone(process.poll())

    def test_stale_watchdog_lease_is_rejected_at_startup(self):
        self.stop_watchdog()
        refusal = self.run_startup_probe(self.state)
        self.assertNotEqual(refusal.returncode, 0)
        self.assertIn("stale rollback-watchdog lease", refusal.stderr)
        self.assertFalse((self.state / "session").exists())

    def test_watchdog_lease_rejects_symlink_mode_and_wrong_identity(self):
        valid = self.watchdog.read_text(encoding="ascii")
        outside = self.root / "outside-watchdog"
        outside.write_text(valid, encoding="ascii")
        outside.chmod(0o600)
        self.watchdog.unlink()
        self.watchdog.symlink_to(outside)
        refusal = self.run_startup_probe(self.state)
        self.assertNotEqual(refusal.returncode, 0)
        self.assertIn("rollback-watchdog lease", refusal.stderr)
        self.assertFalse((self.state / "session").exists())

        self.watchdog.unlink()
        self.watchdog.write_text(valid, encoding="ascii")
        self.watchdog.chmod(0o644)
        refusal = self.run_startup_probe(self.state)
        self.assertNotEqual(refusal.returncode, 0)
        self.assertIn("unsafe rollback-watchdog lease", refusal.stderr)
        self.assertFalse((self.state / "session").exists())

        pid_line, start_line = valid.splitlines()
        wrong_start = int(start_line.removeprefix("starttime=")) + 1
        self.watchdog.write_text(
            f"{pid_line}\nstarttime={wrong_start}\n",
            encoding="ascii",
        )
        self.watchdog.chmod(0o600)
        refusal = self.run_startup_probe(self.state)
        self.assertNotEqual(refusal.returncode, 0)
        self.assertIn("stale rollback-watchdog lease", refusal.stderr)
        self.assertFalse((self.state / "session").exists())

    def test_watchdog_death_terminates_an_idle_responder(self):
        process, _ = self.start()
        self.stop_watchdog()
        self.wait_exit(process)
        stderr = process.stderr.read().decode(errors="replace")
        self.assertIn("watchdog process is not alive", stderr)

    def test_incomplete_prefix_and_body_have_bounded_lifetimes(self):
        for incomplete in (b"12", b"12:abc"):
            with self.subTest(incomplete=incomplete):
                process, master = self.start(io_timeout_ms=100)
                os.write(master, incomplete)
                time.sleep(0.25)
                self.assertIsNone(process.poll())
                self.assertFalse((self.state / "prepared").exists())
                self.assertFalse((self.state / "claim").exists())
                session = self.hello(master, number=20)
                self.assertNotEqual(session, ZERO_ID)
                process.terminate()
                process.wait(timeout=2)
                if process.stderr is not None:
                    process.stderr.close()
                self.processes.remove(process)
                os.close(master)
                self.descriptors.remove(master)

    def test_forced_short_writes_preserve_response_framing(self):
        _, master = self.start(write_chunk=True)
        session = self.hello(master)
        response = self.status(master, session, 2)
        self.assertEqual(response.result, "OK")
        self.assertEqual(response.state, "IDLE")

    def test_status_exports_bounded_postmortem_evidence(self):
        self.postmortem.write_text(
            "state=PRESENT\n"
            "records=1\n"
            "bytes=5\n"
            f"sha256={MANIFEST}\n"
            "tail_hex=70616e6963\n",
            encoding="ascii",
        )
        _, master = self.start()
        session = self.hello(master)
        response = self.status(master, session, 2)
        self.assertEqual(response.postmortem_state, "PRESENT")
        self.assertEqual(response.postmortem_records, "1")
        self.assertEqual(response.postmortem_bytes, "5")
        self.assertEqual(response.postmortem_sha256, MANIFEST)
        self.assertEqual(bytes.fromhex(response.postmortem_tail_hex), b"panic")

    def test_inconsistent_postmortem_status_is_rejected_at_startup(self):
        self.postmortem.write_text(
            "state=PRESENT\n"
            "records=0\n"
            "bytes=0\n"
            f"sha256={'0' * 64}\n"
            "tail_hex=none\n",
            encoding="ascii",
        )
        refusal = self.run_startup_probe(self.state)
        self.assertNotEqual(refusal.returncode, 0)
        self.assertIn("inconsistent present postmortem status", refusal.stderr)
        self.assertFalse((self.state / "session").exists())

    def test_complete_malformed_frames_close_without_state_change(self):
        malformed = (
            b"01:a,",
            b"4097:",
            b"1:a;",
            b"1:\xff,",
        )
        for frame in malformed:
            with self.subTest(frame=frame):
                process, master = self.start()
                os.write(master, frame)
                self.assertEqual(
                    self.read_payloads(master, timeout=0.15),
                    [],
                )
                time.sleep(0.05)
                self.assertIsNone(process.poll())
                self.assertFalse((self.state / "prepared").exists())
                self.assertFalse((self.state / "claim").exists())
                process.terminate()
                process.wait(timeout=2)
                if process.stderr is not None:
                    process.stderr.close()
                self.processes.remove(process)
                os.close(master)
                self.descriptors.remove(master)

    def test_symlink_and_weak_state_paths_are_rejected(self):
        real = self.root / "real-state"
        real.mkdir(mode=0o700)
        linked = self.root / "linked-state"
        linked.symlink_to(real, target_is_directory=True)
        refusal = self.run_startup_probe(linked)
        self.assertNotEqual(refusal.returncode, 0)
        self.assertIn("state directory", refusal.stderr)

        weak = self.root / "weak-state"
        weak.mkdir(mode=0o755)
        refusal = self.run_startup_probe(weak)
        self.assertNotEqual(refusal.returncode, 0)
        self.assertIn("unsafe state directory", refusal.stderr)

    def test_symlink_state_record_is_never_followed(self):
        process, master = self.start()
        self.hello(master)
        process.terminate()
        process.wait(timeout=2)
        if process.stderr is not None:
            process.stderr.close()
        self.processes.remove(process)

        outside = self.root / "outside"
        outside.write_text("not-state\n", encoding="ascii")
        (self.state / "prepared").symlink_to(outside)
        refusal = self.run_startup_probe(self.state)
        self.assertNotEqual(refusal.returncode, 0)
        self.assertIn("prepared", refusal.stderr)
        self.assertEqual(
            outside.read_text(encoding="ascii"),
            "not-state\n",
        )

    def test_prepare_commit_depart_and_restart_status(self):
        process, master = self.start()
        session = self.hello(master)
        prepared = self.prepare(master, session)
        self.assertEqual(prepared.result, "PREPARED")

        commit = self.commit_payload(session)
        claimed = self.exchange(master, commit)
        self.assertEqual(claimed.result, "CLAIMED")
        self.wait_exit(process)
        self.assertTrue((self.state / "execution-started").is_file())
        self.assertTrue((self.state / "test-executed").is_file())
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)
        for name in (
            "session",
            "prepared",
            "claim",
            "execution-started",
            "test-executed",
        ):
            self.assertEqual(
                (self.state / name).stat().st_mode & 0o777,
                0o600,
            )

        restarted, new_master = self.start()
        self.assertIsNone(restarted.poll())
        status = self.status(new_master, session, 20)
        self.assertEqual(status.state, "CLAIMED")
        self.assertEqual(status.execution_started, "YES")
        self.assertEqual(status.prepare_request, request_id(10))
        self.assertEqual(status.commit_request, request_id(11))
        replay = self.exchange(new_master, commit)
        self.assertEqual(replay.result, "CLAIMED")
        self.assertEqual(replay.execution_started, "YES")
        self.assertEqual(
            (self.state / "test-executed").read_text(encoding="ascii"),
            "executed\n",
        )

    def test_prepare_pipeline_loads_exact_descriptors_before_persist(self):
        verifier, loader, marker = self.make_prepare_pipeline("exact")
        process, master = self.start(
            verifier_path=verifier,
            kexec_path=loader,
        )
        session = self.hello(master)
        baseline_fds = len(
            list(Path(f"/proc/{process.pid}/fd").iterdir())
        )
        prepare_identifier = request_id(10)
        request = encode_request(
            session=session,
            request=prepare_identifier,
            verb="PREPARE",
            body={
                "bundle": "arch-v1",
                "manifest_sha256": MANIFEST,
            },
        )
        records = self.exchange_records(master, request)
        progress = records[:-1]
        response = records[-1]
        self.assertTrue(all(isinstance(item, Progress) for item in progress))
        self.assertIsInstance(response, Response)
        self.assertEqual(
            [item.phase for item in progress],
            list(PREPARE_PROGRESS_PHASES),
        )
        for sequence, item in enumerate(progress, 1):
            self.assertEqual(item.sequence, sequence)
            self.assertEqual(item.session, session)
            self.assertEqual(item.request, prepare_identifier)
            self.assertEqual(item.bundle, "arch-v1")
            self.assertEqual(item.manifest_sha256, MANIFEST)
            self.assertEqual(item.watchdog, "ARMED")
        self.assertEqual(response.result, "PREPARED")
        self.assertTrue((self.state / "prepared").is_file())
        self.assertEqual(
            len(list(Path(f"/proc/{process.pid}/fd").iterdir())),
            baseline_fds,
        )
        loaded = marker.read_text(encoding="ascii").splitlines()
        self.assertEqual(loaded[:2], ["-c", "-l"])
        self.assertRegex(loaded[2], r"^/proc/self/fd/[0-9]+$")
        self.assertRegex(
            loaded[3],
            r"^--initrd=/proc/self/fd/[0-9]+$",
        )
        self.assertRegex(
            loaded[4],
            r"^--dtb=/proc/self/fd/[0-9]+$",
        )
        self.assertTrue(loaded[5].startswith("--command-line="))
        self.assertEqual(
            (marker.parent / "events").read_text(
                encoding="ascii"
            ).splitlines(),
            ["fetch", "verify", "load"],
        )
        replay = self.exchange_records(master, request)
        self.assertEqual(replay, [response])
        self.stop_responder(process, master)

    def test_prepare_failures_emit_only_contiguous_progress_prefixes(self):
        cases = (
            ("fetch", "fail", "ok", "ok", 1, "FETCH_FAILED"),
            (
                "verify",
                "ok",
                "malformed_plan",
                "ok",
                2,
                "VERIFY_FAILED",
            ),
            ("load", "ok", "ok", "fail", 3, "VERIFY_FAILED"),
        )
        for index, (
            name,
            fetcher_mode,
            verifier_mode,
            loader_mode,
            expected_count,
            expected_result,
        ) in enumerate(cases):
            with self.subTest(boundary=name):
                self.state = self.root / f"state-progress-{name}"
                self.state.mkdir(mode=0o700)
                verifier, loader, _marker = self.make_prepare_pipeline(
                    f"progress-{name}",
                    fetcher_mode=fetcher_mode,
                    verifier_mode=verifier_mode,
                    loader_mode=loader_mode,
                )
                process, master = self.start(
                    verifier_path=verifier,
                    kexec_path=loader,
                )
                session = self.hello(master, number=800 + index * 2)
                identifier = request_id(801 + index * 2)
                request = encode_request(
                    session=session,
                    request=identifier,
                    verb="PREPARE",
                    body={
                        "bundle": "arch-v1",
                        "manifest_sha256": MANIFEST,
                    },
                )
                records = self.exchange_records(master, request)
                progress = records[:-1]
                response = records[-1]
                self.assertEqual(
                    [item.phase for item in progress],
                    list(PREPARE_PROGRESS_PHASES[:expected_count]),
                )
                self.assertTrue(
                    all(item.request == identifier for item in progress)
                )
                self.assertEqual(response.result, expected_result)
                self.assertEqual(response.state, "IDLE")
                self.stop_responder(process, master)

    def test_progress_send_failure_is_advisory_and_suppresses_later_phases(self):
        verifier, loader, _marker = self.make_prepare_pipeline(
            "progress-send-failure"
        )
        process, master = self.start(
            verifier_path=verifier,
            kexec_path=loader,
            progress_fail_at=3,
        )
        session = self.hello(master)
        request = encode_request(
            session=session,
            request=request_id(10),
            verb="PREPARE",
            body={
                "bundle": "arch-v1",
                "manifest_sha256": MANIFEST,
            },
        )
        os.write(master, encode_frame(request))
        payloads = self.read_payloads(master, count=3, timeout=0.2)
        records = [decode_recovery_record(payload) for payload in payloads]
        self.assertEqual(
            [item.phase for item in records],
            list(PREPARE_PROGRESS_PHASES[:2]),
        )
        self.assertTrue((self.state / "prepared").is_file())
        self.stop_responder(process, master)
        restarted, restarted_master = self.start()
        replay = self.exchange(restarted_master, request)
        self.assertEqual(replay.result, "PREPARED")
        self.stop_responder(restarted, restarted_master)

    def test_ncm_progress_survives_generation10_shaped_acm_loss(self):
        host_progress, device_progress = socket.socketpair()
        self.addCleanup(host_progress.close)
        process, master = self.start(
            progress_fail_at=2,
            ncm_progress_fd=device_progress.fileno(),
        )
        device_progress.close()
        session = self.hello(master)
        request = encode_request(
            session=session,
            request=request_id(10),
            verb="PREPARE",
            body={
                "bundle": "arch-v1",
                "manifest_sha256": MANIFEST,
            },
        )
        os.write(master, encode_frame(request))
        acm_payloads = self.read_payloads(master, count=2, timeout=0.2)
        acm_records = [
            decode_recovery_record(payload) for payload in acm_payloads
        ]
        self.assertEqual(
            [record.phase for record in acm_records],
            list(PREPARE_PROGRESS_PHASES[:1]),
        )
        capture = collect_connection(
            host_progress,
            bundle="arch-v1",
            manifest_sha256=MANIFEST,
            deadline=time.monotonic() + 2,
            expected_session=session,
            expected_request=request_id(10),
        )
        self.assertTrue(capture.complete)
        self.assertEqual(capture.phases, PREPARE_PROGRESS_PHASES)
        self.assertTrue((self.state / "prepared").is_file())
        self.assertFalse((self.state / "claim").exists())
        self.stop_responder(process, master)

    def test_ncm_progress_never_authorizes_commit(self):
        host_progress, device_progress = socket.socketpair()
        self.addCleanup(host_progress.close)
        self.addCleanup(device_progress.close)
        process, master = self.start(
            ncm_progress_fd=device_progress.fileno()
        )
        hostile_input = b"COMMIT_EXEC\nrequest=host-injected\n"
        host_progress.sendall(hostile_input)
        session = self.hello(master)
        response = self.prepare(master, session)
        self.assertEqual(response.result, "PREPARED")
        device_progress.settimeout(0.2)
        self.assertEqual(device_progress.recv(len(hostile_input)), hostile_input)
        device_progress.close()
        capture = collect_connection(
            host_progress,
            bundle="arch-v1",
            manifest_sha256=MANIFEST,
            deadline=time.monotonic() + 2,
            expected_session=session,
            expected_request=request_id(10),
        )
        self.assertTrue(capture.complete)
        self.assertFalse((self.state / "claim").exists())
        committed = self.exchange(master, self.commit_payload(session))
        self.assertEqual(committed.result, "CLAIMED")
        self.assertTrue((self.state / "claim").is_file())
        self.stop_responder(process, master)

    def test_torn_ncm_record_is_advisory_to_healthy_acm(self):
        host_progress, device_progress = socket.socketpair()
        self.addCleanup(host_progress.close)
        process, master = self.start(
            ncm_progress_fd=device_progress.fileno(),
            ncm_partial_at=3,
        )
        device_progress.close()
        session = self.hello(master)
        response = self.prepare(master, session)
        self.assertEqual(response.result, "PREPARED")
        capture = collect_connection(
            host_progress,
            bundle="arch-v1",
            manifest_sha256=MANIFEST,
            deadline=time.monotonic() + 2,
            expected_session=session,
            expected_request=request_id(10),
        )
        self.assertFalse(capture.complete)
        self.assertEqual(capture.phases, PREPARE_PROGRESS_PHASES[:2])
        self.assertEqual(capture.reason, "TORN_FRAME")
        self.assertTrue((self.state / "prepared").is_file())
        self.assertFalse((self.state / "claim").exists())
        self.stop_responder(process, master)

    def test_dead_ncm_peer_does_not_delay_or_gate_prepare(self):
        host_progress, device_progress = socket.socketpair()
        device_progress.shutdown(socket.SHUT_RDWR)
        device_progress.close()
        process, master = self.start(
            ncm_progress_fd=host_progress.fileno()
        )
        host_progress.close()
        session = self.hello(master)
        started = time.monotonic()
        response = self.prepare(master, session)
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertEqual(response.result, "PREPARED")
        self.assertTrue((self.state / "prepared").is_file())
        self.assertFalse((self.state / "claim").exists())
        self.stop_responder(process, master)

    def test_fetch_failure_and_conflict_never_reach_verifier(self):
        cases = (
            ("failure", "fail", "FETCH_FAILED", "FETCH_EXEC"),
            (
                "conflict",
                "conflict",
                "BUNDLE_ID_CONFLICT",
                "BUNDLE_ID_CONFLICT",
            ),
        )
        for index, (name, mode, expected, expected_error) in enumerate(cases):
            with self.subTest(boundary=name):
                self.state = self.root / f"state-fetch-{name}"
                self.state.mkdir(mode=0o700)
                verifier, loader, marker = self.make_prepare_pipeline(
                    f"fetch-{name}",
                    fetcher_mode=mode,
                )
                process, master = self.start(
                    verifier_path=verifier,
                    kexec_path=loader,
                )
                session = self.hello(master, number=600 + index * 2)
                request = encode_request(
                    session=session,
                    request=request_id(601 + index * 2),
                    verb="PREPARE",
                    body={
                        "bundle": "arch-v1",
                        "manifest_sha256": MANIFEST,
                    },
                )
                response = self.exchange(master, request)
                self.assertEqual(response.result, expected)
                self.assertEqual(response.state, "IDLE")
                self.assertEqual(response.last_error, expected_error)
                self.assertFalse(
                    (marker.parent / "verifier-runs").exists()
                )
                self.assertFalse(marker.exists())
                replay = self.exchange(master, request)
                self.assertEqual(replay, response)
                self.assertEqual(
                    (marker.parent / "fetcher-runs").read_text(
                        encoding="ascii"
                    ).splitlines(),
                    ["run"],
                )
                changed_id = self.prepare(
                    master, session, number=603 + index * 2
                )
                self.assertEqual(
                    changed_id.result, "PREPARE_ID_CONFLICT"
                )
                self.assertEqual(changed_id.state, "IDLE")
                self.assertEqual(changed_id.last_error, expected_error)
                self.assertEqual(
                    (marker.parent / "fetcher-runs").read_text(
                        encoding="ascii"
                    ).splitlines(),
                    ["run"],
                )
                self.assertFalse(
                    (marker.parent / "verifier-runs").exists()
                )
                self.stop_responder(process, master)

    def test_fetch_outer_timeout_reaps_helper_tree_and_fails_closed(self):
        verifier, loader, marker = self.make_prepare_pipeline(
            "fetch-outer-timeout",
            fetcher_mode="nested_hang",
        )
        process, master = self.start(
            verifier_path=verifier,
            kexec_path=loader,
            fetch_timeout_ms=100,
        )
        session = self.hello(master)
        started = time.monotonic()
        response = self.prepare(master, session)
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(response.result, "FETCH_FAILED")
        self.assertEqual(response.state, "IDLE")
        self.assertEqual(response.last_error, "FETCH_CONTROL_TIMEOUT")
        fetcher_pid = self.wait_pid_file(
            marker.parent / "fetcher-pid"
        )
        worker_pid = self.wait_pid_file(
            marker.parent / "fetcher-worker-pid"
        )
        self.assert_process_gone(fetcher_pid)
        self.assert_process_gone(worker_pid)
        self.assertFalse((marker.parent / "verifier-runs").exists())
        self.assertFalse(marker.exists())
        self.stop_responder(process, master)

    def test_fetch_stage_exit_is_preserved_in_last_error(self):
        cases = (
            (43, "FETCH_ROOT"),
            (44, "FETCH_STAGE"),
            (45, "FETCH_CONNECT"),
            (46, "FETCH_WORKER_TIMEOUT"),
            (47, "FETCH_WORKER_SIGNAL"),
            (48, "FETCH_TRANSPORT"),
            (49, "FETCH_HEADER"),
            (50, "FETCH_MANIFEST"),
            (51, "FETCH_ARTIFACT"),
            (52, "FETCH_EOF"),
            (53, "FETCH_PARENT_VERIFY"),
            (54, "FETCH_NORMALIZE"),
            (55, "FETCH_FINAL_VERIFY"),
            (56, "FETCH_PUBLISH"),
            (57, "FETCH_WORKER_SETUP"),
            (58, "FETCH_WORKER_FORK"),
        )
        for index, (status, expected) in enumerate(cases):
            with self.subTest(status=status):
                self.state = self.root / f"state-fetch-stage-{status}"
                self.state.mkdir(mode=0o700)
                verifier, loader, marker = self.make_prepare_pipeline(
                    f"fetch-stage-{status}",
                    fetcher_mode=f"exit-{status}",
                )
                process, master = self.start(
                    verifier_path=verifier,
                    kexec_path=loader,
                )
                session = self.hello(master, number=700 + index * 2)
                response = self.prepare(
                    master,
                    session,
                    number=701 + index * 2,
                )
                self.assertEqual(response.result, "FETCH_FAILED")
                self.assertEqual(response.state, "IDLE")
                self.assertEqual(response.last_error, expected)
                self.assertFalse(
                    (marker.parent / "verifier-runs").exists()
                )
                self.stop_responder(process, master)

    def test_abrupt_responder_death_kills_fetch_helper_tree(self):
        verifier, loader, marker = self.make_prepare_pipeline(
            "fetch-responder-death",
            fetcher_mode="nested_hang",
        )
        process, master = self.start(
            verifier_path=verifier,
            kexec_path=loader,
            fetch_timeout_ms=5000,
        )
        session = self.hello(master)
        os.write(
            master,
            encode_frame(
                encode_request(
                    session=session,
                    request=request_id(10),
                    verb="PREPARE",
                    body={
                        "bundle": "arch-v1",
                        "manifest_sha256": MANIFEST,
                    },
                )
            ),
        )
        fetcher_pid = self.wait_pid_file(
            marker.parent / "fetcher-pid"
        )
        worker_pid = self.wait_pid_file(
            marker.parent / "fetcher-worker-pid"
        )
        process.kill()
        process.wait(timeout=2)
        self.assert_process_gone(fetcher_pid)
        self.assert_process_gone(worker_pid)
        self.assertFalse((marker.parent / "verifier-runs").exists())
        self.assertFalse((self.state / "prepared").exists())
        self.assertFalse(marker.exists())
        if process.stderr is not None:
            process.stderr.close()
        self.processes.remove(process)
        os.close(master)

    def test_prepare_pipeline_rejects_every_failed_boundary(self):
        cases = (
            ("malformed-plan", "malformed_plan", "ok"),
            ("wrong-manifest", "wrong_manifest", "ok"),
            ("wrong-command-hash", "wrong_command_hash", "ok"),
            ("extra-plan-field", "extra_plan_field", "ok"),
            ("embedded-nul", "embedded_nul", "ok"),
            ("oversized-plan", "oversized_plan", "ok"),
            ("short-rights", "wrong_fd_count", "ok"),
            ("unsafe-rights", "unsafe_descriptor", "ok"),
            ("aliased-rights", "aliased_descriptor", "ok"),
            ("unsealed-rights", "unsealed_descriptor", "ok"),
            ("nonzero-offset", "nonzero_offset", "ok"),
            ("four-rights", "four_rights", "ok"),
            ("sixteen-rights", "sixteen_rights", "ok"),
            ("maximum-rights", "maximum_rights", "ok"),
            ("zero-packet-rights", "zero_packet_rights", "ok"),
            ("verifier-exit", "fail_after_send", "ok"),
            ("no-packet", "no_packet", "ok"),
            ("loader-exit", "ok", "fail"),
        )
        for index, (name, verifier_mode, loader_mode) in enumerate(cases):
            with self.subTest(boundary=name):
                verifier, loader, marker = self.make_prepare_pipeline(
                    name,
                    verifier_mode=verifier_mode,
                    loader_mode=loader_mode,
                )
                process, master = self.start(
                    verifier_path=verifier,
                    kexec_path=loader,
                )
                session = self.hello(master, number=100 + index * 2)
                response = self.prepare(
                    master,
                    session,
                    number=101 + index * 2,
                )
                self.assertEqual(response.result, "VERIFY_FAILED")
                self.assertFalse((self.state / "prepared").exists())
                self.assertFalse(marker.exists())
                self.stop_responder(process, master)

    def test_malformed_rights_never_leak_descriptors(self):
        for mode_index, mode in enumerate(
            (
                "four_rights",
                "sixteen_rights",
                "maximum_rights",
                "zero_packet_rights",
                "unsafe_descriptor",
                "aliased_descriptor",
                "unsealed_descriptor",
                "nonzero_offset",
                "fail_after_send",
            )
        ):
            with self.subTest(mode=mode):
                self.state = self.root / f"state-leak-{mode}"
                self.state.mkdir(mode=0o700)
                verifier, loader, marker = self.make_prepare_pipeline(
                    f"leak-{mode}",
                    verifier_mode=mode,
                )
                process, master = self.start(
                    verifier_path=verifier,
                    kexec_path=loader,
                )
                session = self.hello(
                    master,
                    number=400 + mode_index * 20,
                )
                baseline = len(list(Path(f"/proc/{process.pid}/fd").iterdir()))
                for attempt in range(5):
                    response = self.prepare(
                        master,
                        session,
                        number=401 + mode_index * 20 + attempt,
                    )
                    self.assertEqual(response.result, "VERIFY_FAILED")
                    self.assertEqual(
                        len(list(
                            Path(f"/proc/{process.pid}/fd").iterdir()
                        )),
                        baseline,
                    )
                self.assertFalse(marker.exists())
                self.stop_responder(process, master)

    def test_verifier_timeout_after_handoff_closes_descriptors(self):
        verifier, loader, marker = self.make_prepare_pipeline(
            "handoff-timeout",
            verifier_mode="hang_after_send",
        )
        process, master = self.start(
            verifier_path=verifier,
            kexec_path=loader,
            verify_timeout_ms=100,
        )
        session = self.hello(master)
        baseline = len(list(Path(f"/proc/{process.pid}/fd").iterdir()))
        response = self.prepare(master, session)
        self.assertEqual(response.result, "VERIFY_FAILED")
        self.assertEqual(
            len(list(Path(f"/proc/{process.pid}/fd").iterdir())),
            baseline,
        )
        child_pid = self.wait_pid_file(marker.parent / "verifier-pid")
        self.assertFalse(Path(f"/proc/{child_pid}").exists())
        self.assertFalse(marker.exists())
        self.stop_responder(process, master)

    def test_prepare_pipeline_timeouts_are_fail_closed(self):
        cases = (
            ("verifier-timeout", "hang", "ok", 100, None),
            ("loader-timeout", "ok", "hang", None, 100),
        )
        for index, (
            name,
            verifier_mode,
            loader_mode,
            verify_timeout,
            load_timeout,
        ) in enumerate(cases):
            with self.subTest(boundary=name):
                verifier, loader, marker = self.make_prepare_pipeline(
                    name,
                    verifier_mode=verifier_mode,
                    loader_mode=loader_mode,
                )
                process, master = self.start(
                    verifier_path=verifier,
                    kexec_path=loader,
                    verify_timeout_ms=verify_timeout,
                    load_timeout_ms=load_timeout,
                )
                session = self.hello(master, number=200 + index * 2)
                started = time.monotonic()
                response = self.prepare(
                    master,
                    session,
                    number=201 + index * 2,
                )
                self.assertLess(time.monotonic() - started, 2)
                self.assertEqual(response.result, "VERIFY_FAILED")
                self.assertFalse((self.state / "prepared").exists())
                self.assertFalse(marker.exists())
                pid_name = (
                    "verifier-pid"
                    if verifier_mode == "hang"
                    else "loader-pid"
                )
                child_pid = self.wait_pid_file(marker.parent / pid_name)
                self.assertFalse(Path(f"/proc/{child_pid}").exists())
                self.stop_responder(process, master)

    def test_loader_timeout_after_kernel_acceptance_unloads_image(self):
        verifier, loader, marker = self.make_prepare_pipeline(
            "loaded-timeout",
            loader_mode="hang_after_load",
        )
        process, master = self.start(
            verifier_path=verifier,
            kexec_path=loader,
            load_timeout_ms=100,
        )
        session = self.hello(master)
        response = self.prepare(master, session)
        self.assertEqual(response.result, "VERIFY_FAILED")
        self.assertEqual(
            marker.read_text(encoding="ascii").splitlines(),
            ["loaded"],
        )
        self.assertFalse((marker.parent / "loaded-state").exists())
        self.assertGreaterEqual(
            len(
                (marker.parent / "unload-marker")
                .read_text(encoding="ascii")
                .splitlines()
            ),
            1,
        )
        child_pid = self.wait_pid_file(marker.parent / "loader-pid")
        self.assertFalse(Path(f"/proc/{child_pid}").exists())
        self.assertFalse((self.state / "prepared").exists())
        self.stop_responder(process, master)

    def test_crash_after_load_retries_without_false_prepared_state(self):
        verifier, loader, marker = self.make_prepare_pipeline(
            "load-crash",
            loader_mode="count",
        )
        process, master = self.start(
            crash="after_prepare_load",
            verifier_path=verifier,
            kexec_path=loader,
        )
        session = self.hello(master)
        request = encode_request(
            session=session,
            request=request_id(10),
            verb="PREPARE",
            body={
                "bundle": "arch-v1",
                "manifest_sha256": MANIFEST,
            },
        )
        os.write(master, encode_frame(request))
        self.wait_exit(process)
        self.assertEqual(
            marker.read_text(encoding="ascii").splitlines(),
            ["loaded"],
        )
        self.assertFalse((self.state / "prepared").exists())
        self.assertTrue((marker.parent / "loaded-state").is_file())
        self.assertGreaterEqual(
            len(
                (marker.parent / "unload-marker")
                .read_text(encoding="ascii")
                .splitlines()
            ),
            1,
        )
        self.stop_responder(process, master)

        restarted, restarted_master = self.start(
            verifier_path=verifier,
            kexec_path=loader,
        )
        replay = self.exchange(restarted_master, request)
        self.assertEqual(replay.result, "PREPARED")
        self.assertTrue((self.state / "prepared").is_file())
        self.assertEqual(
            marker.read_text(encoding="ascii").splitlines(),
            ["loaded", "loaded"],
        )
        self.assertTrue((marker.parent / "loaded-state").is_file())
        self.assertGreaterEqual(
            len(
                (marker.parent / "unload-marker")
                .read_text(encoding="ascii")
                .splitlines()
            ),
            2,
        )
        self.stop_responder(restarted, restarted_master)

    def test_fixed_executor_return_unloads_and_persists_failure(self):
        verifier, loader, marker = self.make_prepare_pipeline(
            "fixed-executor-return",
            loader_mode="exec_return",
        )
        process, master = self.start(
            execute="fixed_path",
            verifier_path=verifier,
            kexec_path=loader,
        )
        session = self.hello(master)
        self.assertEqual(self.prepare(master, session).result, "PREPARED")
        self.assertTrue((marker.parent / "loaded-state").is_file())
        claimed = self.exchange(master, self.commit_payload(session))
        self.assertEqual(claimed.result, "CLAIMED")
        failure = self.state / "failure"
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not failure.exists():
            time.sleep(0.01)
        self.assertTrue(failure.is_file())
        self.assertFalse((marker.parent / "loaded-state").exists())
        self.assertEqual(
            (marker.parent / "executor-marker").read_text(
                encoding="ascii"
            ),
            "returned\n",
        )
        self.assertGreaterEqual(
            len(
                (marker.parent / "unload-marker")
                .read_text(encoding="ascii")
                .splitlines()
            ),
            1,
        )
        status = self.status(master, session, 20)
        self.assertEqual(status.state, "EXEC_FAILED")
        self.assertEqual(status.last_error, "EXEC_RETURNED")
        self.stop_responder(process, master)

    def test_fixed_executor_failure_unloads_and_persists_failure(self):
        verifier, loader, marker = self.make_prepare_pipeline(
            "fixed-executor-failure",
            loader_mode="exec_fail",
        )
        process, master = self.start(
            execute="fixed_path",
            verifier_path=verifier,
            kexec_path=loader,
        )
        session = self.hello(master)
        self.assertEqual(self.prepare(master, session).result, "PREPARED")
        claimed = self.exchange(master, self.commit_payload(session))
        self.assertEqual(claimed.result, "CLAIMED")
        failure = self.state / "failure"
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not failure.exists():
            time.sleep(0.01)
        self.assertTrue(failure.is_file())
        self.assertFalse((marker.parent / "loaded-state").exists())
        status = self.status(master, session, 20)
        self.assertEqual(status.state, "EXEC_FAILED")
        self.assertEqual(status.last_error, "EXEC_FAILED")
        self.stop_responder(process, master)

    def test_watchdog_death_during_fixed_executor_reaps_and_reconciles(self):
        verifier, loader, marker = self.make_prepare_pipeline(
            "fixed-executor-watchdog",
            loader_mode="exec_hang",
        )
        process, master = self.start(
            execute="fixed_path",
            verifier_path=verifier,
            kexec_path=loader,
        )
        session = self.hello(master)
        self.assertEqual(self.prepare(master, session).result, "PREPARED")
        claimed = self.exchange(master, self.commit_payload(session))
        self.assertEqual(claimed.result, "CLAIMED")
        pid_file = marker.parent / "executor-pid"
        child_pid = self.wait_pid_file(pid_file)
        self.stop_watchdog()
        self.wait_exit(process)
        stderr = process.stderr.read().decode(errors="replace")
        self.assertIn(
            "rollback watchdog died while executor ran",
            stderr,
        )
        self.assertFalse(Path(f"/proc/{child_pid}").exists())
        self.assertTrue((marker.parent / "loaded-state").is_file())

        self.start_watchdog()
        restarted, restarted_master = self.start(
            execute="fixed_path",
            verifier_path=verifier,
            kexec_path=loader,
        )
        self.assertFalse((marker.parent / "loaded-state").exists())
        self.assertGreaterEqual(
            len(
                (marker.parent / "unload-marker")
                .read_text(encoding="ascii")
                .splitlines()
            ),
            2,
        )
        status = self.status(restarted_master, session, 20)
        self.assertEqual(status.state, "CLAIMED")
        self.assertEqual(status.execution_started, "YES")
        self.stop_responder(restarted, restarted_master)

    def test_watchdog_death_after_acm_progress_loss_reaps_fetch_tree(self):
        verifier, loader, marker = self.make_prepare_pipeline(
            "watchdog-fetch",
            fetcher_mode="nested_hang",
        )
        process, master = self.start(
            verifier_path=verifier,
            kexec_path=loader,
            fetch_timeout_ms=5000,
            progress_fail_at=1,
        )
        session = self.hello(master)
        os.write(
            master,
            encode_frame(
                encode_request(
                    session=session,
                    request=request_id(10),
                    verb="PREPARE",
                    body={
                        "bundle": "arch-v1",
                        "manifest_sha256": MANIFEST,
                    },
                )
            ),
        )
        fetcher_pid = self.wait_pid_file(
            marker.parent / "fetcher-pid"
        )
        worker_pid = self.wait_pid_file(
            marker.parent / "fetcher-worker-pid"
        )
        self.stop_watchdog()
        self.wait_exit(process)
        stderr = process.stderr.read().decode(errors="replace")
        self.assertIn("rollback watchdog died during PREPARE", stderr)
        self.assert_process_gone(fetcher_pid)
        self.assert_process_gone(worker_pid)
        self.assertFalse((marker.parent / "verifier-runs").exists())
        self.assertFalse((self.state / "prepared").exists())
        self.assertFalse(marker.exists())

    def test_watchdog_death_during_verifier_is_terminal(self):
        verifier, loader, marker = self.make_prepare_pipeline(
            "watchdog-verifier",
            verifier_mode="hang",
        )
        process, master = self.start(
            verifier_path=verifier,
            kexec_path=loader,
            verify_timeout_ms=5000,
        )
        session = self.hello(master)
        os.write(
            master,
            encode_frame(
                encode_request(
                    session=session,
                    request=request_id(10),
                    verb="PREPARE",
                    body={
                        "bundle": "arch-v1",
                        "manifest_sha256": MANIFEST,
                    },
                )
            ),
        )
        pid_file = marker.parent / "verifier-pid"
        child_pid = self.wait_pid_file(pid_file)
        self.stop_watchdog()
        self.wait_exit(process)
        stderr = process.stderr.read().decode(errors="replace")
        self.assertIn("watchdog died during verifier handoff", stderr)
        self.assertFalse(Path(f"/proc/{child_pid}").exists())
        self.assertFalse((self.state / "prepared").exists())
        self.assertFalse(marker.exists())

    def test_watchdog_death_during_loader_reaps_child(self):
        verifier, loader, marker = self.make_prepare_pipeline(
            "watchdog-loader",
            loader_mode="hang",
        )
        process, master = self.start(
            verifier_path=verifier,
            kexec_path=loader,
            load_timeout_ms=5000,
        )
        session = self.hello(master)
        os.write(
            master,
            encode_frame(
                encode_request(
                    session=session,
                    request=request_id(10),
                    verb="PREPARE",
                    body={
                        "bundle": "arch-v1",
                        "manifest_sha256": MANIFEST,
                    },
                )
            ),
        )
        pid_file = marker.parent / "loader-pid"
        child_pid = self.wait_pid_file(pid_file)
        self.stop_watchdog()
        self.wait_exit(process)
        stderr = process.stderr.read().decode(errors="replace")
        self.assertIn("watchdog died during PREPARE", stderr)
        self.assertFalse(Path(f"/proc/{child_pid}").exists())
        self.assertFalse((self.state / "prepared").exists())
        self.assertFalse(marker.exists())

    def test_crash_after_claim_is_not_executed_by_restart(self):
        process, master = self.start(crash="after_claim")
        session = self.hello(master)
        self.assertEqual(self.prepare(master, session).result, "PREPARED")
        os.write(master, encode_frame(self.commit_payload(session)))
        self.wait_exit(process)
        self.assertEqual(self.read_payloads(master, timeout=0.1), [])
        self.assertFalse((self.state / "execution-started").exists())

        _, new_master = self.start()
        status = self.status(new_master, session, 20)
        self.assertEqual(status.state, "CLAIMED")
        self.assertEqual(status.execution_started, "NO")
        duplicate = self.exchange(new_master, self.commit_payload(session))
        self.assertEqual(duplicate.result, "CLAIMED")
        self.assertFalse((self.state / "test-executed").exists())

    def test_crash_before_claim_preserves_prepared_state(self):
        process, master = self.start(crash="before_claim")
        session = self.hello(master)
        self.prepare(master, session)
        os.write(master, encode_frame(self.commit_payload(session)))
        self.wait_exit(process)
        self.assertFalse((self.state / "claim").exists())
        self.assertFalse((self.state / "execution-started").exists())

        _, new_master = self.start()
        status = self.status(new_master, session, 20)
        self.assertEqual(status.state, "PREPARED")
        self.assertEqual(status.execution_started, "NO")

    def test_crash_after_prepare_reconstructs_same_request_response(self):
        process, master = self.start(crash="after_prepare")
        session = self.hello(master)
        payload = encode_request(
            session=session,
            request=request_id(10),
            verb="PREPARE",
            body={
                "bundle": "arch-v1",
                "manifest_sha256": MANIFEST,
            },
        )
        os.write(master, encode_frame(payload))
        self.wait_exit(process)
        self.assertTrue((self.state / "prepared").exists())
        self.assertFalse(
            (self.state / "requests" / request_id(10)).exists()
        )

        restarted, new_master = self.start()
        replay = self.exchange(new_master, payload)
        self.assertEqual(replay.result, "PREPARED")
        self.assertEqual(replay.prepare_request, request_id(10))
        claimed = self.exchange(new_master, self.commit_payload(session))
        self.assertEqual(claimed.result, "CLAIMED")
        self.wait_exit(restarted)

        _, final_master = self.start()
        replay_after_claim = self.exchange(final_master, payload)
        self.assertEqual(replay_after_claim.result, "PREPARED")
        self.assertEqual(replay_after_claim.state, "CLAIMED")

    def test_prepare_publication_crash_boundaries_reconstruct_safely(self):
        stages = {
            "before_write": False,
            "after_write": False,
            "after_file_fsync": False,
            "after_link": True,
            "after_unlink": True,
            "after_dir_fsync": True,
        }
        for stage, published in stages.items():
            with self.subTest(stage=stage):
                self.state = self.root / f"state-{stage}"
                self.state.mkdir(mode=0o700)
                process, master = self.start(
                    persist_crash=f"prepared:{stage}"
                )
                session = self.hello(master)
                payload = encode_request(
                    session=session,
                    request=request_id(10),
                    verb="PREPARE",
                    body={
                        "bundle": "arch-v1",
                        "manifest_sha256": MANIFEST,
                    },
                )
                os.write(master, encode_frame(payload))
                self.wait_exit(process)
                self.assertEqual(
                    (self.state / "prepared").exists(),
                    published,
                )

                restarted, new_master = self.start()
                status = self.status(new_master, session, 20)
                self.assertEqual(
                    status.state,
                    "PREPARED" if published else "IDLE",
                )
                if published:
                    replay = self.exchange(new_master, payload)
                    self.assertEqual(replay.result, "PREPARED")
                self.stop_responder(restarted, new_master)
                os.close(master)
                self.descriptors.remove(master)

    def test_request_decision_crash_boundaries_replay_from_state(self):
        stages = {
            "before_write": False,
            "after_write": False,
            "after_file_fsync": False,
            "after_link": True,
            "after_unlink": True,
            "after_dir_fsync": True,
        }
        for stage, published in stages.items():
            with self.subTest(stage=stage):
                self.state = self.root / f"ledger-state-{stage}"
                self.state.mkdir(mode=0o700)
                process, master = self.start(
                    persist_crash=f"{request_id(10)}:{stage}"
                )
                session = self.hello(master)
                payload = encode_request(
                    session=session,
                    request=request_id(10),
                    verb="PREPARE",
                    body={
                        "bundle": "arch-v1",
                        "manifest_sha256": MANIFEST,
                    },
                )
                os.write(master, encode_frame(payload))
                self.wait_exit(process)
                decision = self.state / "requests" / request_id(10)
                self.assertEqual(decision.exists(), published)
                self.assertTrue((self.state / "prepared").exists())

                restarted, new_master = self.start()
                replay = self.exchange(new_master, payload)
                self.assertEqual(replay.result, "PREPARED")
                self.assertEqual(replay.state, "PREPARED")
                self.stop_responder(restarted, new_master)
                os.close(master)
                self.descriptors.remove(master)

    def test_last_error_rename_crashes_are_conservative(self):
        stages = {
            "before_write": False,
            "after_write": False,
            "after_file_fsync": False,
            "before_rename": False,
            "after_rename": True,
            "after_dir_fsync": True,
        }
        for stage, published in stages.items():
            with self.subTest(stage=stage):
                self.state = self.root / f"error-state-{stage}"
                self.state.mkdir(mode=0o700)
                process, master = self.start(
                    persist_crash=f"last-error:{stage}"
                )
                session = self.hello(master)
                rejected = encode_request(
                    session=session,
                    request=request_id(10),
                    verb="PREPARE",
                    body={
                        "bundle": "arch-v1",
                        "manifest_sha256": OTHER_MANIFEST,
                    },
                )
                os.write(master, encode_frame(rejected))
                self.wait_exit(process)
                self.assertEqual(
                    (self.state / "last-error").exists(),
                    published,
                )

                restarted, new_master = self.start()
                status = self.status(new_master, session, 20)
                self.assertEqual(
                    status.last_error,
                    "VERIFY_FAILED" if published else "NONE",
                )
                self.stop_responder(restarted, new_master)
                os.close(master)
                self.descriptors.remove(master)

    def test_claim_publication_crash_boundaries_reconstruct_safely(self):
        stages = {
            "before_write": False,
            "after_write": False,
            "after_file_fsync": False,
            "after_link": True,
            "after_unlink": True,
            "after_dir_fsync": True,
        }
        for stage, published in stages.items():
            with self.subTest(stage=stage):
                self.state = self.root / f"claim-state-{stage}"
                self.state.mkdir(mode=0o700)
                process, master = self.start(
                    persist_crash=f"claim:{stage}"
                )
                session = self.hello(master)
                self.prepare(master, session)
                os.write(
                    master,
                    encode_frame(self.commit_payload(session)),
                )
                self.wait_exit(process)
                self.assertEqual(
                    (self.state / "claim").exists(),
                    published,
                )
                self.assertFalse(
                    (self.state / "execution-started").exists()
                )

                restarted, new_master = self.start()
                status = self.status(new_master, session, 20)
                self.assertEqual(
                    status.state,
                    "CLAIMED" if published else "PREPARED",
                )
                self.assertEqual(status.execution_started, "NO")
                self.stop_responder(restarted, new_master)
                os.close(master)
                self.descriptors.remove(master)

    def test_failure_publication_crash_boundaries_are_conservative(self):
        stages = {
            "before_write": False,
            "after_write": False,
            "after_file_fsync": False,
            "after_link": True,
            "after_unlink": True,
            "after_dir_fsync": True,
        }
        for stage, published in stages.items():
            with self.subTest(stage=stage):
                self.state = self.root / f"failure-state-{stage}"
                self.state.mkdir(mode=0o700)
                process, master = self.start(
                    execute="return",
                    persist_crash=f"failure:{stage}",
                )
                session = self.hello(master)
                self.prepare(master, session)
                claimed = self.exchange(
                    master,
                    self.commit_payload(session),
                )
                self.assertEqual(claimed.result, "CLAIMED")
                self.wait_exit(process)
                self.assertEqual(
                    (self.state / "failure").exists(),
                    published,
                )
                self.assertTrue(
                    (self.state / "execution-started").exists()
                )

                restarted, new_master = self.start()
                status = self.status(new_master, session, 20)
                self.assertEqual(
                    status.state,
                    "EXEC_FAILED" if published else "CLAIMED",
                )
                self.assertEqual(status.execution_started, "YES")
                duplicate = self.exchange(
                    new_master,
                    self.commit_payload(session),
                )
                self.assertEqual(duplicate.result, "CLAIMED")
                self.assertEqual(
                    (self.state / "test-executed").read_text(
                        encoding="ascii"
                    ),
                    "executed\n",
                )
                self.stop_responder(restarted, new_master)
                os.close(master)
                self.descriptors.remove(master)

    def test_execution_marker_crash_boundaries_never_reexecute(self):
        stages = {
            "before_write": False,
            "after_write": False,
            "after_file_fsync": False,
            "after_link": True,
            "after_unlink": True,
            "after_dir_fsync": True,
        }
        for stage, published in stages.items():
            with self.subTest(stage=stage):
                self.state = self.root / f"execute-state-{stage}"
                self.state.mkdir(mode=0o700)
                process, master = self.start(
                    persist_crash=f"execution-started:{stage}"
                )
                session = self.hello(master)
                self.prepare(master, session)
                claimed = self.exchange(
                    master,
                    self.commit_payload(session),
                )
                self.assertEqual(claimed.result, "CLAIMED")
                self.wait_exit(process)
                self.assertEqual(
                    (self.state / "execution-started").exists(),
                    published,
                )
                self.assertFalse((self.state / "test-executed").exists())

                restarted, new_master = self.start()
                status = self.status(new_master, session, 20)
                self.assertEqual(status.state, "CLAIMED")
                self.assertEqual(
                    status.execution_started,
                    "YES" if published else "NO",
                )
                duplicate = self.exchange(
                    new_master,
                    self.commit_payload(session),
                )
                self.assertEqual(duplicate.result, "CLAIMED")
                time.sleep(0.05)
                self.assertFalse((self.state / "test-executed").exists())
                self.stop_responder(restarted, new_master)
                os.close(master)
                self.descriptors.remove(master)

    def test_crash_after_response_remains_claimed_without_execution(self):
        process, master = self.start(crash="after_response")
        session = self.hello(master)
        self.prepare(master, session)
        claimed = self.exchange(master, self.commit_payload(session))
        self.assertEqual(claimed.result, "CLAIMED")
        self.wait_exit(process)
        self.assertFalse((self.state / "execution-started").exists())

        _, new_master = self.start()
        status = self.status(new_master, session, 20)
        self.assertEqual(status.state, "CLAIMED")
        self.assertEqual(status.execution_started, "NO")

    def test_crash_after_execution_marker_never_reexecutes(self):
        process, master = self.start(crash="after_execute_start")
        session = self.hello(master)
        self.prepare(master, session)
        self.assertEqual(
            self.exchange(master, self.commit_payload(session)).result,
            "CLAIMED",
        )
        self.wait_exit(process)
        self.assertTrue((self.state / "execution-started").exists())
        self.assertFalse((self.state / "test-executed").exists())

        _, new_master = self.start()
        status = self.status(new_master, session, 20)
        self.assertEqual(status.execution_started, "YES")
        self.assertFalse((self.state / "test-executed").exists())

    def test_disconnect_before_reply_never_executes(self):
        process, master = self.start(reply_delay_ms=300)
        session = self.hello(master)
        self.prepare(master, session)
        os.write(master, encode_frame(self.commit_payload(session)))
        deadline = time.monotonic() + 2
        while (
            time.monotonic() < deadline
            and not (self.state / "claim").exists()
        ):
            time.sleep(0.005)
        self.assertTrue((self.state / "claim").exists())
        os.close(master)
        self.descriptors.remove(master)
        time.sleep(0.5)
        self.assertIsNone(process.poll())
        self.assertFalse((self.state / "execution-started").exists())
        self.assertFalse((self.state / "test-executed").exists())

    def test_disconnect_before_complete_commit_never_claims(self):
        process, master = self.start(io_timeout_ms=150)
        session = self.hello(master)
        self.prepare(master, session)
        frame = encode_frame(self.commit_payload(session))
        os.write(master, frame[: len(frame) // 2])
        os.close(master)
        self.descriptors.remove(master)
        time.sleep(0.3)
        self.assertIsNone(process.poll())
        self.assertFalse((self.state / "claim").exists())
        self.assertFalse((self.state / "execution-started").exists())

    def test_drain_timeout_after_claim_never_executes(self):
        process, master = self.start(
            io_timeout_ms=150,
            drain_stall="claim",
        )
        session = self.hello(master)
        self.prepare(master, session)
        claimed = self.exchange(master, self.commit_payload(session))
        self.assertEqual(claimed.result, "CLAIMED")
        time.sleep(0.3)
        self.assertIsNone(process.poll())
        self.assertTrue((self.state / "claim").exists())
        self.assertFalse((self.state / "execution-started").exists())
        self.assertFalse((self.state / "test-executed").exists())

    def test_real_tty_write_backpressure_after_claim_never_executes(self):
        process, master = self.start(io_timeout_ms=150)
        session = self.hello(master)
        self.prepare(master, session)
        control = os.open(
            self.last_slave_path,
            os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK,
        )
        try:
            termios.tcflow(control, termios.TCOOFF)
            filled = 0
            while filled < 1024 * 1024:
                try:
                    filled += os.write(control, b"x" * 4096)
                except BlockingIOError:
                    break
            self.assertLess(filled, 1024 * 1024)
            os.write(master, encode_frame(self.commit_payload(session)))
            deadline = time.monotonic() + 2
            while (
                time.monotonic() < deadline
                and not (self.state / "claim").exists()
            ):
                time.sleep(0.005)
            self.assertTrue((self.state / "claim").exists())
            time.sleep(0.3)
            self.assertIsNone(process.poll())
            self.assertFalse(
                (self.state / "execution-started").exists()
            )
            self.assertFalse((self.state / "test-executed").exists())
        finally:
            termios.tcflow(control, termios.TCOON)
            os.close(control)

    def test_watchdog_death_before_response_never_executes(self):
        process, master = self.start(reply_delay_ms=300)
        session = self.hello(master)
        self.prepare(master, session)
        os.write(master, encode_frame(self.commit_payload(session)))
        deadline = time.monotonic() + 2
        while (
            time.monotonic() < deadline
            and not (self.state / "claim").exists()
        ):
            time.sleep(0.005)
        self.assertTrue((self.state / "claim").exists())
        self.stop_watchdog()
        self.wait_exit(process)
        self.assertFalse((self.state / "execution-started").exists())
        self.assertFalse((self.state / "test-executed").exists())

    def test_watchdog_death_after_execution_marker_stops_executor(self):
        process, master = self.start(execute_delay_ms=400)
        session = self.hello(master)
        self.prepare(master, session)
        claimed = self.exchange(master, self.commit_payload(session))
        self.assertEqual(claimed.result, "CLAIMED")
        deadline = time.monotonic() + 2
        while (
            time.monotonic() < deadline
            and not (self.state / "execution-started").exists()
        ):
            time.sleep(0.005)
        self.assertTrue((self.state / "execution-started").exists())
        self.stop_watchdog()
        self.wait_exit(process)
        self.assertFalse((self.state / "test-executed").exists())

    def test_execute_return_is_permanent_failure(self):
        _, master = self.start(execute="return")
        session = self.hello(master)
        self.prepare(master, session)
        claimed = self.exchange(master, self.commit_payload(session))
        self.assertEqual(claimed.result, "CLAIMED")

        deadline = time.monotonic() + 2
        while (
            time.monotonic() < deadline
            and not (self.state / "failure").exists()
        ):
            time.sleep(0.01)
        self.assertTrue((self.state / "failure").exists())
        status = self.status(master, session, 20)
        self.assertEqual(status.state, "EXEC_FAILED")
        self.assertEqual(status.execution_started, "YES")
        self.assertEqual(status.last_error, "EXEC_RETURNED")
        replay = self.exchange(master, self.commit_payload(session))
        self.assertEqual(replay.result, "CLAIMED")
        self.assertEqual(replay.state, "EXEC_FAILED")
        self.assertEqual(replay.execution_started, "YES")

    def test_replay_conflict_prepare_conflict_and_stale_session(self):
        process, master = self.start()
        session = self.hello(master)
        status_payload = encode_request(
            session=session,
            request=request_id(2),
            verb="STATUS",
        )
        first = self.exchange(master, status_payload)
        replay = self.exchange(master, status_payload)
        self.assertEqual(replay, first)
        self.assertEqual(
            len(list((self.state / "requests").iterdir())),
            0,
        )

        prepared = encode_request(
            session=session,
            request=request_id(10),
            verb="PREPARE",
            body={
                "bundle": "arch-v1",
                "manifest_sha256": MANIFEST,
            },
        )
        self.assertEqual(
            self.exchange(master, prepared).result,
            "PREPARED",
        )
        changed = encode_request(
            session=session,
            request=request_id(10),
            verb="PREPARE",
            body={
                "bundle": "arch-v2",
                "manifest_sha256": MANIFEST,
            },
        )
        self.assertEqual(
            self.exchange(master, changed).result,
            "REQUEST_CONFLICT",
        )
        cross_verb = self.commit_payload(
            session,
            number=10,
            prepare_number=10,
        )
        self.assertEqual(
            self.exchange(master, cross_verb).result,
            "REQUEST_CONFLICT",
        )
        self.assertIsNone(process.poll())

        duplicate_prepare = self.prepare(master, session, number=12)
        self.assertEqual(
            duplicate_prepare.result,
            "PREPARE_ID_CONFLICT",
        )
        stale = self.status(master, "f" * 32, 30)
        self.assertEqual(stale.result, "STALE_SESSION")

    def test_ledger_capacity_is_fail_closed_without_eviction(self):
        _, master = self.start()
        session = self.hello(master)
        for number in range(100, 129):
            self.assertEqual(
                self.exchange(
                    master,
                    self.commit_payload(
                        session,
                        number=number,
                    ),
                ).result,
                "PREPARE_REQUIRED",
            )
        self.assertEqual(
            self.status(master, session, 2).result,
            "OK",
        )
        full = self.exchange(
            master,
            self.commit_payload(session, number=129),
        )
        self.assertEqual(full.result, "LEDGER_FULL")
        self.assertEqual(
            self.prepare(master, session).result,
            "PREPARED",
        )
        self.assertEqual(
            self.exchange(master, self.commit_payload(session)).result,
            "CLAIMED",
        )

    def test_ledger_boundary_never_loads_without_three_reserved_slots(self):
        process, master = self.start()
        session = self.hello(master)
        self.stop_responder(process, master)
        requests = self.state / "requests"
        for index in range(31):
            record = requests / request_id(100 + index)
            record.write_text(
                f"fingerprint={index + 1:064x}\n"
                "verb=COMMIT_EXEC\n"
                "result=PREPARE_REQUIRED\n",
                encoding="ascii",
            )
            record.chmod(0o600)

        verifier, loader, marker = self.make_prepare_pipeline(
            "ledger-boundary"
        )
        restarted, restarted_master = self.start(
            verifier_path=verifier,
            kexec_path=loader,
        )
        self.assertEqual(
            self.prepare(restarted_master, session, number=301).result,
            "LEDGER_FULL",
        )
        self.assertFalse(marker.exists())
        self.assertFalse((self.state / "prepared").exists())
        self.stop_responder(restarted, restarted_master)

    def test_ledger_boundary_records_failed_prepare_once(self):
        process, master = self.start()
        session = self.hello(master)
        self.stop_responder(process, master)
        requests = self.state / "requests"
        for index in range(29):
            record = requests / request_id(100 + index)
            record.write_text(
                f"fingerprint={index + 1:064x}\n"
                "verb=COMMIT_EXEC\n"
                "result=PREPARE_REQUIRED\n",
                encoding="ascii",
            )
            record.chmod(0o600)

        verifier, loader, marker = self.make_prepare_pipeline(
            "ledger-failed-prepare",
            verifier_mode="malformed_plan",
        )
        responder, responder_master = self.start(
            verifier_path=verifier,
            kexec_path=loader,
        )
        payload = encode_request(
            session=session,
            request=request_id(300),
            verb="PREPARE",
            body={
                "bundle": "arch-v1",
                "manifest_sha256": MANIFEST,
            },
        )
        self.assertEqual(
            self.exchange(responder_master, payload).result,
            "VERIFY_FAILED",
        )
        runs = marker.parent / "verifier-runs"
        self.assertEqual(
            runs.read_text(encoding="ascii").splitlines(),
            ["run"],
        )
        self.assertEqual(
            self.exchange(responder_master, payload).result,
            "VERIFY_FAILED",
        )
        self.assertEqual(
            self.prepare(responder_master, session, number=301).result,
            "LEDGER_FULL",
        )
        self.assertEqual(
            runs.read_text(encoding="ascii").splitlines(),
            ["run"],
        )
        self.assertFalse(marker.exists())
        self.stop_responder(responder, responder_master)

    def test_claim_reconstruction_does_not_overflow_full_ledger(self):
        process, master = self.start(crash="after_claim")
        session = self.hello(master)
        self.prepare(master, session)
        commit = self.commit_payload(session)
        os.write(master, encode_frame(commit))
        self.wait_exit(process)

        _, new_master = self.start()
        for number in range(100, 128):
            self.assertEqual(
                self.exchange(
                    new_master,
                    self.commit_payload(session, number=number),
                ).result,
                "ALREADY_CLAIMED",
            )
        self.assertEqual(
            len(list((self.state / "requests").iterdir())),
            29,
        )
        self.assertEqual(
            self.exchange(
                new_master,
                self.commit_payload(session, number=128),
            ).result,
            "LEDGER_FULL",
        )
        duplicate = self.exchange(new_master, commit)
        self.assertEqual(duplicate.result, "CLAIMED")
        self.assertEqual(
            len(list((self.state / "requests").iterdir())),
            29,
        )
        self.assertEqual(
            self.status(new_master, session, 200).result,
            "OK",
        )

    def test_native_sequence_matches_reference_oracle(self):
        process, master = self.start(crash="after_response")
        hello_payload = encode_request(
            session=ZERO_ID,
            request=request_id(1),
            verb="HELLO",
        )
        native = self.exchange(master, hello_payload)
        oracle = RecoveryModel(RecoveryState(session=native.session))
        self.assertEqual(
            native,
            oracle.handle(decode_request(hello_payload)),
        )

        sequence = [
            encode_request(
                session=native.session,
                request=request_id(2),
                verb="STATUS",
            ),
            encode_request(
                session=native.session,
                request=request_id(10),
                verb="PREPARE",
                body={
                    "bundle": "arch-v1",
                    "manifest_sha256": MANIFEST,
                },
            ),
            encode_request(
                session=native.session,
                request=request_id(12),
                verb="PREPARE",
                body={
                    "bundle": "arch-v1",
                    "manifest_sha256": MANIFEST,
                },
            ),
            encode_request(
                session=native.session,
                request=request_id(13),
                verb="COMMIT_EXEC",
                body={
                    "prepare_request": request_id(9),
                    "manifest_sha256": MANIFEST,
                },
            ),
            self.commit_payload(native.session),
        ]
        for payload in sequence:
            with self.subTest(verb=decode_request(payload).verb):
                self.assertEqual(
                    self.exchange(master, payload),
                    oracle.handle(decode_request(payload)),
                )
        self.wait_exit(process)

    def test_source_and_binary_have_no_shell_execution_path(self):
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "system(",
            "popen(",
            "/bin/sh",
            "sh -c",
            "execlp(",
            "execvp(",
        ):
            self.assertNotIn(forbidden, source)
        undefined = subprocess.check_output(
            ["nm", "-u", str(self.binary)],
            text=True,
        )
        self.assertNotIn(" system", undefined)
        self.assertNotIn(" popen", undefined)
        strings = subprocess.check_output(
            ["strings", str(self.binary)],
            text=True,
        )
        self.assertNotIn("/bin/sh", strings)
        self.assertNotIn("kexec -e", strings)

        production_strings = subprocess.check_output(
            ["strings", str(self.production)],
            text=True,
        )
        self.assertIn("/usr/sbin/kexec", production_strings)
        self.assertIn(
            "/usr/libexec/rog5-bundle-fetch",
            production_strings,
        )
        self.assertIn(
            "/usr/libexec/rog5-bundle-verify",
            production_strings,
        )
        self.assertIn("--handoff-fd3", production_strings)
        self.assertIn("/proc/self/fd/%d", production_strings)
        self.assertIn("rog5-kexec", production_strings)
        self.assertIn("usb0", production_strings)
        self.assertIn("169.254.77.1", production_strings)
        self.assertIn("169.254.77.2", production_strings)
        self.assertNotIn("ROG5_TEST_", production_strings)
        self.assertNotIn("test-executed", production_strings)
        refused = subprocess.run(
            [str(self.production), "--device", "/dev/null"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn(
            "production responder accepts no arguments",
            refused.stderr,
        )


if __name__ == "__main__":
    if shutil.which("gcc") is None:
        raise SystemExit("gcc is required")
    unittest.main(verbosity=2)
