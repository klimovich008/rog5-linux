#!/usr/bin/env python3
"""Hostile tests for held-descriptor execution without live helper wiring."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import os
from pathlib import Path
import resource
import signal
import stat
import time
from unittest import mock
import unittest


REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "scripts/host/retention-cycle-descriptor-execution.py"
PROBE = REPO / "scripts/host/retention-cycle-descriptor-probe.py"
PROFILE = REPO / "configs/retention-cycles/host-rendezvous-v3-observer-v1.json"
POLICY = REPO / "manifests/temporary-boot-images.tsv"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EXECUTION = load_module("rog5_retention_descriptor_execution", SOURCE)


def pinned_interpreter_available() -> bool:
    """Return true only on the exact deployment host runtime."""

    try:
        logical = EXECUTION.INTERPRETER_LOGICAL.lstat()
        resolved = EXECUTION.INTERPRETER_RESOLVED.stat(follow_symlinks=False)
        return (
            stat.S_ISLNK(logical.st_mode)
            and logical.st_uid == 0
            and logical.st_gid == 0
            and os.readlink(EXECUTION.INTERPRETER_LOGICAL)
            == EXECUTION.INTERPRETER_LINK_TARGET
            and stat.S_ISREG(resolved.st_mode)
            and resolved.st_uid == 0
            and resolved.st_gid == 0
            and resolved.st_nlink == 1
            and stat.S_IMODE(resolved.st_mode) == EXECUTION.INTERPRETER_MODE
            and resolved.st_size == EXECUTION.INTERPRETER_SIZE
            and hashlib.sha256(
                EXECUTION.INTERPRETER_RESOLVED.read_bytes()
            ).hexdigest()
            == EXECUTION.INTERPRETER_SHA256
        )
    except OSError:
        return False


@unittest.skipUnless(
    pinned_interpreter_available(),
    "requires the exact pinned deployment-host interpreter",
)
class RetentionCycleDescriptorExecutionTest(unittest.TestCase):
    def prepare(self, mode: str = "success"):
        prepared = EXECUTION.prepare_fixture(mode)
        self.addCleanup(prepared.close)
        return prepared

    def test_success_executes_exact_held_descriptors_and_context(self) -> None:
        prepared = self.prepare()
        proof = EXECUTION.run_fixture(prepared)
        decoded = EXECUTION.decode_fixture(prepared, proof)

        self.assertEqual(proof.mode, "success")
        self.assertEqual(proof.outcome.exit_code, 0)
        self.assertEqual(proof.outcome.stderr, b"")
        self.assertFalse(proof.outcome.timed_out)
        self.assertFalse(proof.outcome.output_overflow)
        self.assertTrue(proof.stdout_eof)
        self.assertTrue(proof.stderr_eof)
        self.assertNotEqual(proof.stdout_pipe_inode, proof.stderr_pipe_inode)
        self.assertLess(proof.pipe_created_ns, proof.spawned_ns)
        self.assertLessEqual(proof.spawned_ns, proof.finished_ns)
        self.assertEqual(decoded.authority, "none")
        self.assertFalse(decoded.adapter_eligible)
        self.assertEqual(decoded.evidence["format"], EXECUTION.FORMAT)
        self.assertEqual(decoded.evidence["nonce"], prepared.nonce)
        self.assertEqual(decoded.evidence["mode"], "success")
        exec_argv = b"\0".join(
            value.encode("ascii") for value in prepared.spec.argv
        ) + b"\0"
        self.assertEqual(
            decoded.evidence["exec_argv_sha256"],
            hashlib.sha256(exec_argv).hexdigest(),
        )
        self.assertEqual(
            decoded.evidence["program_sha256"], EXECUTION.PROGRAM_SHA256
        )
        self.assertEqual(
            decoded.evidence["interpreter_sha256"],
            EXECUTION.INTERPRETER_SHA256,
        )
        self.assertEqual(decoded.evidence["cwd"], str(REPO))
        self.assertEqual(decoded.evidence["umask"], "0077")
        self.assertEqual(decoded.evidence["open_fds"], "0,1,2,198")
        self.assertEqual(decoded.evidence["program_fd"], 198)
        self.assertTrue(decoded.evidence["stdin_devnull"])
        self.assertTrue(decoded.evidence["stdout_pipe"])
        self.assertTrue(decoded.evidence["stderr_pipe"])
        self.assertTrue(decoded.evidence["session_leader"])
        self.assertTrue(decoded.evidence["process_group_leader"])

        with self.assertRaisesRegex(
            EXECUTION.DescriptorExecutionError, "already decoded"
        ):
            EXECUTION.decode_fixture(prepared, proof)
        with self.assertRaisesRegex(
            EXECUTION.DescriptorExecutionError, "already attempted"
        ):
            EXECUTION.run_fixture(prepared)

    def test_exact_argv_environment_cwd_umask_and_limits_are_immutable(self) -> None:
        mutations = (
            ("argv", lambda value: value + ("extra",)),
            ("environment", lambda value: value + (("EXTRA", "1"),)),
            ("cwd", lambda _value: "/tmp"),
            ("umask", lambda _value: "0022"),
            ("stdin", lambda _value: "inherit"),
            ("stdout", lambda _value: "inherit"),
            ("stderr", lambda _value: "inherit"),
            ("output_limit_bytes", lambda value: value + 1),
            ("deadline_milliseconds", lambda value: value + 1),
            ("program_fd", lambda value: value + 1),
            ("interpreter_fd", lambda value: value + 1),
        )
        for field, mutate in mutations:
            with self.subTest(field=field):
                prepared = self.prepare()
                changed = EXECUTION.dataclass_replace(
                    prepared.spec,
                    **{field: mutate(getattr(prepared.spec, field))},
                )
                object.__setattr__(prepared, "spec", changed)
                with self.assertRaisesRegex(
                    EXECUTION.DescriptorExecutionError,
                    "fixture process specification changed",
                ):
                    EXECUTION.run_fixture(prepared)

    def test_program_and_interpreter_path_changes_fail_before_fork(self) -> None:
        for label, selected in (
            ("program descriptor", "program"),
            ("interpreter descriptor", "interpreter"),
            ("repository directory", "repository"),
        ):
            with self.subTest(label=label):
                prepared = self.prepare()
                real_stat = EXECUTION._stat_named

                def changed_stat(which, *args, **kwargs):
                    observed = real_stat(which, *args, **kwargs)
                    if which == selected:
                        return EXECUTION.dataclass_replace(
                            observed, inode=observed.inode + 1
                        )
                    return observed

                with mock.patch.object(
                    EXECUTION, "_stat_named", side_effect=changed_stat
                ), mock.patch.object(os, "fork") as fork:
                    with self.assertRaisesRegex(
                        EXECUTION.DescriptorExecutionError, f"{label} changed"
                    ):
                        EXECUTION.run_fixture(prepared)
                    fork.assert_not_called()

    def test_program_path_change_during_run_and_before_decode_is_refused(
        self,
    ) -> None:
        prepared = self.prepare()
        real_stat = EXECUTION._stat_named
        program_checks = 0

        def changes_after_fork(which, *args, **kwargs):
            nonlocal program_checks
            observed = real_stat(which, *args, **kwargs)
            if which == "program":
                program_checks += 1
                if program_checks == 2:
                    return EXECUTION.dataclass_replace(
                        observed, inode=observed.inode + 1
                    )
            return observed

        with mock.patch.object(
            EXECUTION,
            "_stat_named",
            side_effect=changes_after_fork,
        ), self.assertRaisesRegex(
            EXECUTION.DescriptorExecutionError,
            "program descriptor changed",
        ):
            EXECUTION.run_fixture(prepared)
        self.assertTrue(prepared._attempted)

        other = self.prepare()
        proof = EXECUTION.run_fixture(other)

        def changed_before_decode(which, *args, **kwargs):
            observed = real_stat(which, *args, **kwargs)
            if which == "program":
                return EXECUTION.dataclass_replace(
                    observed, inode=observed.inode + 1
                )
            return observed

        with mock.patch.object(
            EXECUTION,
            "_stat_named",
            side_effect=changed_before_decode,
        ), self.assertRaisesRegex(
            EXECUTION.DescriptorExecutionError,
            "program descriptor changed",
        ):
            EXECUTION.decode_fixture(other, proof)

    def test_parent_inheritable_descriptor_does_not_cross_exec(self) -> None:
        sentinel = os.open("/dev/null", os.O_RDONLY)
        self.addCleanup(os.close, sentinel)
        os.set_inheritable(sentinel, True)
        prepared = self.prepare()
        decoded = EXECUTION.decode_fixture(
            prepared, EXECUTION.run_fixture(prepared)
        )
        self.assertEqual(decoded.evidence["open_fds"], "0,1,2,198")
        self.assertNotIn(str(sentinel), decoded.evidence["open_fds"].split(","))

    def test_fd_above_lowered_soft_limit_does_not_cross_exec(self) -> None:
        sentinel = os.open("/dev/null", os.O_RDONLY)
        high_descriptor = 500
        os.dup2(sentinel, high_descriptor, inheritable=True)
        os.close(sentinel)
        self.addCleanup(os.close, high_descriptor)
        old_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
        if old_limit[1] < high_descriptor + 1:
            self.skipTest("hard descriptor limit is too low for hostile fixture")
        prepared = self.prepare()
        try:
            resource.setrlimit(resource.RLIMIT_NOFILE, (256, old_limit[1]))
            decoded = EXECUTION.decode_fixture(
                prepared, EXECUTION.run_fixture(prepared)
            )
        finally:
            resource.setrlimit(resource.RLIMIT_NOFILE, old_limit)
        self.assertEqual(decoded.evidence["open_fds"], "0,1,2,198")

    def test_reaped_group_never_falls_back_to_direct_pid_signal(self) -> None:
        with mock.patch.object(
            os, "waitpid", side_effect=ChildProcessError
        ):
            reaped = EXECUTION._wait_nonblocking(424242)
        self.assertIs(
            reaped,
            EXECUTION._ChildState.REAPED_WITHOUT_STATUS,
        )

        with mock.patch.object(
            os, "killpg", side_effect=ProcessLookupError
        ) as kill_group, mock.patch.object(os, "kill") as kill_direct:
            stopped = EXECUTION._stop_group(424242, reaped)
        self.assertIs(stopped, reaped)
        self.assertEqual(kill_group.call_count, 2)
        kill_direct.assert_not_called()

        with mock.patch.object(
            os, "killpg", side_effect=ProcessLookupError
        ) as kill_group, mock.patch.object(os, "kill") as kill_direct:
            EXECUTION._signal_group(
                424242,
                signal.SIGKILL,
                allow_direct_child=False,
            )
        kill_group.assert_called_once_with(424242, signal.SIGKILL)
        kill_direct.assert_not_called()

        with mock.patch.object(
            os, "killpg", side_effect=ProcessLookupError
        ), mock.patch.object(os, "kill") as kill_direct:
            EXECUTION._signal_group(
                424242,
                signal.SIGTERM,
                allow_direct_child=True,
            )
        kill_direct.assert_called_once_with(424242, signal.SIGTERM)

    def test_timeout_descendant_overflow_and_exit_are_bounded(self) -> None:
        expectations = {
            "timeout": (True, False, None),
            "descendant": (True, False, None),
            "overflow": (False, True, None),
            "exit": (False, False, 7),
        }
        for mode, expected in expectations.items():
            with self.subTest(mode=mode):
                prepared = self.prepare(mode)
                proof = EXECUTION.run_fixture(prepared)
                timed_out, overflow, exit_code = expected
                self.assertEqual(proof.outcome.timed_out, timed_out)
                self.assertEqual(proof.outcome.output_overflow, overflow)
                if exit_code is not None:
                    self.assertEqual(proof.outcome.exit_code, exit_code)
                if mode == "descendant":
                    self.assertRegex(
                        proof.outcome.stderr,
                        rb"\Adescendant-pid:[1-9][0-9]*\n\Z",
                    )
                    self.assertTrue(proof.stderr_eof)
                    descendant_pid = int(
                        proof.outcome.stderr
                        .removeprefix(b"descendant-pid:")
                        .strip()
                    )
                    absent_deadline = time.monotonic() + 0.5
                    while (
                        Path(f"/proc/{descendant_pid}").exists()
                        and time.monotonic() < absent_deadline
                    ):
                        time.sleep(0.005)
                    self.assertFalse(Path(f"/proc/{descendant_pid}").exists())
                self.assertLessEqual(
                    len(proof.outcome.stdout),
                    prepared.spec.output_limit_bytes + 1,
                )
                self.assertLessEqual(
                    len(proof.outcome.stderr),
                    prepared.spec.output_limit_bytes + 1,
                )
                with self.assertRaisesRegex(
                    EXECUTION.DescriptorExecutionError,
                    "successful descriptor fixture",
                ):
                    EXECUTION.decode_fixture(prepared, proof)

    def test_cross_preparation_proof_and_reopened_objects_are_refused(self) -> None:
        first = self.prepare()
        second = self.prepare()
        proof = EXECUTION.run_fixture(first)
        self.assertNotEqual(first.nonce, second.nonce)
        with self.assertRaisesRegex(
            EXECUTION.DescriptorExecutionError, "different preparation"
        ):
            EXECUTION.decode_fixture(second, proof)
        first.close()
        with self.assertRaisesRegex(
            EXECUTION.DescriptorExecutionError, "unavailable"
        ):
            EXECUTION.decode_fixture(first, proof)

    def test_malformed_probe_output_and_pipe_identity_fail_closed(self) -> None:
        prepared = self.prepare()
        proof = EXECUTION.run_fixture(prepared)
        object.__setattr__(
            proof,
            "outcome",
            EXECUTION.dataclass_replace(proof.outcome, stdout=b"{}\n"),
        )
        with self.assertRaisesRegex(
            EXECUTION.DescriptorExecutionError, "output is not exact"
        ):
            EXECUTION.decode_fixture(prepared, proof)
        with self.assertRaisesRegex(
            EXECUTION.DescriptorExecutionError, "already decoded"
        ):
            EXECUTION.decode_fixture(prepared, proof)

        other = self.prepare()
        proof = EXECUTION.run_fixture(other)
        object.__setattr__(
            proof,
            "stderr_pipe_inode",
            proof.stdout_pipe_inode,
        )
        object.__setattr__(
            proof,
            "stderr_pipe_device",
            proof.stdout_pipe_device,
        )
        with self.assertRaisesRegex(
            EXECUTION.DescriptorExecutionError, "proof identity"
        ):
            EXECUTION.decode_fixture(other, proof)

    def test_source_and_profile_expose_no_live_or_injection_surface(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        probe = PROBE.read_text(encoding="utf-8")
        signature = inspect.signature(EXECUTION.run_fixture)
        self.assertEqual(tuple(signature.parameters), ("prepared",))
        for token in (
            "subprocess",
            "socket",
            "getpass",
            "GITHUB_TOKEN",
            "SSH_KEY",
            "ALLOW_TEMPORARY_BOOT",
            "ALLOW_PHONE_CREDENTIAL_USE",
            "if __name__ ==",
        ):
            self.assertNotIn(token, source)
            self.assertNotIn(token, probe)
        self.assertEqual(EXECUTION.LIVE_ENTRYPOINT, "none")
        self.assertEqual(EXECUTION.ADAPTER_WIRING, "none")
        self.assertEqual(EXECUTION.PRODUCTION_EXECUTION, "none")
        self.assertEqual(EXECUTION.CONNECTED_ADMISSION, "none")
        self.assertEqual(EXECUTION.CREDENTIAL_USE, "none")
        self.assertEqual(EXECUTION.RESULT_AUTHORITY, "none")

        profile = json.loads(PROFILE.read_text(encoding="utf-8"))
        record = profile["claims"]["executor_descriptor_fixture"]
        self.assertEqual(record["runner_path"], SOURCE.relative_to(REPO).as_posix())
        self.assertEqual(record["probe_path"], PROBE.relative_to(REPO).as_posix())
        self.assertEqual(record["implementation"], "offline-held-fd-exec-v1")
        self.assertEqual(record["fixture_descriptor_execution"], "proven")
        self.assertEqual(record["production_descriptor_execution"], "unproven")
        self.assertEqual(record["adapter_wiring"], "none")
        self.assertEqual(record["live_entrypoint"], "none")
        self.assertEqual(record["credential_use"], "none")
        self.assertEqual(record["result_authority"], "none")
        self.assertEqual(profile["state"], "hold")
        self.assertEqual(profile["authority"], "none")
        self.assertEqual(profile["boot_authority"], "none")
        rows = [
            line.split("\t")
            for line in POLICY.read_text(encoding="utf-8").splitlines()[1:]
            if line
        ]
        self.assertEqual(
            sum(
                row[0]
                == "build/observation-recovery-mainline-udc-v11-generation10-20260811-r1/repack/stable-recovery-a.avb.img"
                and row[1] == "revoked"
                for row in rows
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
