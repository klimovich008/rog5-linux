#!/usr/bin/env python3
"""Pseudo-terminal tests for the native recovery control responder."""

from __future__ import annotations

import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import subprocess
import tempfile
import termios
import time
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "tools/recovery_control/rog5-recovery-control.c"

import sys

sys.path.insert(0, str(REPO))

from tools.recovery_control import (  # noqa: E402
    FrameParser,
    RecoveryModel,
    RecoveryState,
    ZERO_ID,
    decode_request,
    decode_response,
    encode_frame,
    encode_request,
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
            ],
            cwd=REPO,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
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
        frame = encode_frame(payload)
        if fragments:
            for byte in frame:
                os.write(master, bytes([byte]))
        else:
            os.write(master, frame)
        responses = self.read_payloads(
            master,
            read_size=response_read_size,
        )
        self.assertEqual(len(responses), 1)
        return decode_response(responses[0])

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

    def wait_exit(self, process: subprocess.Popen) -> None:
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.fail("responder did not reach the injected exit")

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

        self.watchdog.unlink()
        self.watchdog.write_text(valid, encoding="ascii")
        self.watchdog.chmod(0o644)
        refusal = self.run_startup_probe(self.state)
        self.assertNotEqual(refusal.returncode, 0)
        self.assertIn("unsafe rollback-watchdog lease", refusal.stderr)

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
        for number in range(100, 130):
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
            self.commit_payload(session, number=130),
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

    def test_claim_reconstruction_does_not_overflow_full_ledger(self):
        process, master = self.start(crash="after_claim")
        session = self.hello(master)
        self.prepare(master, session)
        commit = self.commit_payload(session)
        os.write(master, encode_frame(commit))
        self.wait_exit(process)

        _, new_master = self.start()
        for number in range(100, 129):
            self.assertEqual(
                self.exchange(
                    new_master,
                    self.commit_payload(session, number=number),
                ).result,
                "ALREADY_CLAIMED",
            )
        self.assertEqual(
            len(list((self.state / "requests").iterdir())),
            30,
        )
        duplicate = self.exchange(new_master, commit)
        self.assertEqual(duplicate.result, "CLAIMED")
        self.assertEqual(
            len(list((self.state / "requests").iterdir())),
            30,
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
        self.assertIn("rog5-kexec", production_strings)
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
