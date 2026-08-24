#!/usr/bin/env python3
"""Hardware-free tests for the read-only persistent-root live runner."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "scripts/host/run-persistent-root-storage-live-cycle.py"
SPEC = importlib.util.spec_from_file_location("persistent_root_live", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load persistent-root live runner")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PersistentRootLiveCycleTest(unittest.TestCase):
    def test_profile_and_artifact_identities_are_exact(self) -> None:
        self.assertEqual(
            MODULE.PROFILE_ID,
            "local-image-stage-writer-v2-generation111-live-v1",
        )
        self.assertEqual(MODULE.PROFILE.candidate, MODULE.BUNDLE)
        self.assertEqual(MODULE.PROFILE.bundle, MODULE.BUNDLE)
        self.assertEqual(MODULE.PROFILE.bundle_profile, "persistent-root-ro-v1")
        self.assertEqual(MODULE.PROFILE.recovery_profile, MODULE.PROFILE_ID)
        self.assertFalse(MODULE.PROFILE.diagnostic)
        self.assertEqual(MODULE.TARGET_PRODUCT, "ROG5 local image stage")
        self.assertEqual(MODULE.TARGET_UDEV_MODEL, "ROG5_local_image_stage")
        self.assertEqual(
            MODULE.BUNDLE,
            "local-image-stage-writer-v2",
        )
        for digest in (
            MODULE.MANIFEST_SHA256,
            MODULE.RECOVERY_SHA256,
            MODULE.TRUST_KEY_SHA256,
            MODULE.HOST_VERIFIER_SHA256,
        ):
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertNotEqual(digest, "0" * 64)
        gate = (REPO / "scripts/host/run-stable-recovery-live-gate.sh").read_text()
        for exact in (
            MODULE.PROFILE_ID,
            MODULE.BUNDLE,
            MODULE.MANIFEST_SHA256,
            MODULE.RECOVERY_SHA256,
            MODULE.TRUST_KEY_SHA256,
            MODULE.HOST_VERIFIER_SHA256,
            "generation111",
        ):
            self.assertIn(exact, gate)
        self.assertIn(
            MODULE.PROFILE_ID,
            MODULE.CYCLE.STOCK_FALLBACK_RECOVERY_PROFILES,
        )
        self.assertNotIn(
            MODULE.PROFILE_ID,
            MODULE.CYCLE.POWER_USB_RECEIPT_RECOVERY_PROFILES,
        )
        self.assertEqual(
            MODULE.CYCLE.CLAIM_CONSUMER.CLAIMS[MODULE.PROFILE_ID],
            MODULE.CLAIM_RECORD,
        )
        self.assertEqual(
            MODULE.CLAIM_ENTRYPOINT.name,
            "consume-local-image-stage-writer-v2-claim.py",
        )

    def test_continuous_runner_has_no_manual_boundary_after_commit(self) -> None:
        source = MODULE_PATH.read_text()
        cleanup = source.index("        wait_post_commit_host_cleanup(cycle)\n")
        network = source.index("interface = activate_target_network(cycle, anchor)")
        host_key = source.index("wait_for_stage_host_key(cycle, anchor, target_known_hosts)")
        transfer = source.index("transfer_arch_image(cycle, target_ssh, exact_arch_image())")
        self.assertLess(cleanup, network)
        self.assertLess(network, host_key)
        self.assertLess(host_key, transfer)
        segment = source[cleanup:transfer]
        self.assertNotIn("input(", segment)
        self.assertNotIn("fastboot", segment)

    def test_terminal_stage_stops_the_host_key_wait(self) -> None:
        source = MODULE_PATH.read_text()
        receive = source.index("current = receive_stage_record(listener)")
        terminal = source.index('if current.state == "FAIL":', receive)
        wait = source.index("status = CYCLE.wait_process(process, 5)", receive)
        self.assertLess(receive, terminal)
        self.assertLess(terminal, wait)

    def test_diagnostics_capture_bounded_systemd_timing(self) -> None:
        diagnostic = MODULE.DIAGNOSTIC_COMMAND
        self.assertIn("=== systemd time ===", diagnostic)
        self.assertIn("systemd-analyze time", diagnostic)
        self.assertIn("systemd-analyze blame --no-pager", diagnostic)
        self.assertIn("sed -n '1,80p'", diagnostic)
        self.assertIn("systemd-analyze critical-chain --no-pager", diagnostic)
        self.assertIn(
            "systemd-analyze critical-chain --no-pager rog5-early-sshd.service",
            diagnostic,
        )
        self.assertIn(
            "rog5-sshd-ed25519-key.service",
            diagnostic,
        )
        self.assertIn("sshdgenkeys.service", diagnostic)
        self.assertIn("rog5-early-sshd.service", diagnostic)
        self.assertIn("ssh_host_*_key*", diagnostic)
        self.assertIn("=== side-port power/USB ===", diagnostic)
        self.assertIn("/run/rog5-power-usb-ready", diagnostic)

    def test_runtime_evidence_accepts_dynamic_device_letter(self) -> None:
        payload = "\n".join(
            (
                "format=rog5-persistent-root-live-evidence-v1",
                "boot_id=11111111-2222-3333-4444-555555555555",
                "uptime_seconds=21.00",
                "status=PASS",
                f"kernel={MODULE.TARGET_RELEASE}",
                "physical_blocks=116",
                "block_backed_mounts=2",
                "userdata_mount=ro-noload",
                "local_image_mount=ro-noload",
                "local_image_write_probe=PASS",
                "root=local-ext4-overlay-tmpfs",
                "blocked_device_queries=0",
                "blocked_scsi_commands=0",
                "journal_recovery_events=0",
                "ufs_error_events=0",
                "backlights=0",
                "ssh=strict-key-only",
                "userdata_device=/dev/sdg23",
                "result=PASS",
                "",
            )
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "runtime.log"
            path.write_text(payload)
            self.assertEqual(
                MODULE.parse_runtime_evidence(path),
                "11111111-2222-3333-4444-555555555555",
            )

    def test_runtime_evidence_rejects_missing_duplicate_and_wrong_storage(self) -> None:
        baseline = [
            "format=rog5-persistent-root-live-evidence-v1",
            "boot_id=11111111-2222-3333-4444-555555555555",
            "status=PASS",
            f"kernel={MODULE.TARGET_RELEASE}",
            "physical_blocks=116",
            "block_backed_mounts=2",
            "userdata_mount=ro-noload",
            "local_image_mount=ro-noload",
            "local_image_write_probe=PASS",
            "root=local-ext4-overlay-tmpfs",
            "blocked_device_queries=0",
            "blocked_scsi_commands=0",
            "journal_recovery_events=0",
            "ufs_error_events=0",
            "ssh=strict-key-only",
            "userdata_device=/dev/sda23",
            "result=PASS",
        ]
        hostile = (
            baseline[:-2] + ["userdata_device=/dev/mmcblk0p23", "result=PASS"],
            baseline + ["boot_id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"],
            [line for line in baseline if line != "physical_blocks=116"],
            baseline + ["blocked_scsi_commands=0"],
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "runtime.log"
            for payload in hostile:
                with self.subTest(payload=payload[-2:]):
                    path.write_text("\n".join(payload) + "\n")
                    with self.assertRaises(MODULE.PersistentCycleError):
                        MODULE.parse_runtime_evidence(path)

    def test_ssh_is_key_only_and_pins_the_bootstrap_alias(self) -> None:
        inputs = SimpleNamespace(ssh_key=Path("/private/key"))
        arguments = MODULE.ssh_arguments(inputs, Path("/private/known-hosts"))
        joined = " ".join(arguments)
        self.assertIn("BatchMode=yes", joined)
        self.assertIn("IdentitiesOnly=yes", joined)
        self.assertIn("PasswordAuthentication=no", joined)
        self.assertIn("StrictHostKeyChecking=yes", joined)
        self.assertIn("HostKeyAlias=rog5-minimal-headless-v1", joined)
        self.assertNotIn("StrictHostKeyChecking=no", joined)

    def test_authenticated_ssh_rendezvous_retries_cold_session_startup(self) -> None:
        failures = (
            subprocess.CompletedProcess([], 255, "connection timed out\n"),
            subprocess.TimeoutExpired("ssh", 20),
            subprocess.CompletedProcess(
                [], 0, f"{MODULE.AUTHENTICATED_SSH_READY_MARKER}\n"
            ),
        )
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            MODULE.CYCLE, "run_capture", side_effect=failures
        ) as runner, mock.patch.object(
            MODULE.time, "monotonic", side_effect=(0.0, 0.0, 1.0, 2.0, 3.0)
        ), mock.patch.object(MODULE.time, "sleep") as sleep:
            attempts, elapsed = MODULE.wait_for_authenticated_ssh(
                ["ssh", "root@169.254.77.2"],
                Path(temporary) / "readiness.log",
            )
        self.assertEqual(attempts, 3)
        self.assertEqual(elapsed, 3.0)
        self.assertEqual(runner.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        for call in runner.call_args_list:
            self.assertEqual(call.args[0][-1], MODULE.AUTHENTICATED_SSH_COMMAND)

    def test_authenticated_ssh_rendezvous_accepts_one_bounded_marker_line(self) -> None:
        cold_success = subprocess.CompletedProcess(
            [],
            0,
            "cold-session startup notice\n"
            f"{MODULE.AUTHENTICATED_SSH_READY_MARKER}\n",
        )
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            MODULE.CYCLE, "run_capture", return_value=cold_success
        ), mock.patch.object(
            MODULE.time, "monotonic", side_effect=(0.0, 0.0, 1.0)
        ):
            attempts, elapsed = MODULE.wait_for_authenticated_ssh(
                ["ssh", "root@169.254.77.2"],
                Path(temporary) / "readiness.log",
            )
        self.assertEqual(attempts, 1)
        self.assertEqual(elapsed, 1.0)

    def test_authenticated_ssh_rendezvous_is_bounded(self) -> None:
        unavailable = subprocess.CompletedProcess([], 255, "unavailable\n")
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            MODULE.CYCLE, "run_capture", return_value=unavailable
        ) as runner, mock.patch.object(
            MODULE.time, "monotonic", side_effect=(0.0, 0.0, 151.0)
        ), mock.patch.object(MODULE.time, "sleep"):
            with self.assertRaisesRegex(
                MODULE.PersistentCycleError,
                "authenticated SSH did not become ready",
            ):
                MODULE.wait_for_authenticated_ssh(
                    ["ssh", "root@169.254.77.2"],
                    Path(temporary) / "readiness.log",
                )
        self.assertEqual(runner.call_count, 1)

    def test_authenticated_ssh_rendezvous_rejects_wrong_success_output(self) -> None:
        wrong = subprocess.CompletedProcess([], 0, "wrong target\n")
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            MODULE.CYCLE, "run_capture", return_value=wrong
        ), mock.patch.object(
            MODULE.time, "monotonic", side_effect=(0.0, 0.0)
        ):
            with self.assertRaisesRegex(
                MODULE.PersistentCycleError,
                "unexpected authenticated SSH readiness output",
            ):
                MODULE.wait_for_authenticated_ssh(
                    ["ssh", "root@169.254.77.2"],
                    Path(temporary) / "readiness.log",
                )

    def test_nmcli_has_one_unprivileged_then_noninteractive_sudo_path(self) -> None:
        results = (
            SimpleNamespace(returncode=1, stdout="not authorized\n"),
            SimpleNamespace(returncode=0, stdout="ok\n"),
        )
        with mock.patch.object(
            MODULE.CYCLE,
            "run_capture",
            side_effect=results,
        ) as runner:
            MODULE.privileged_nmcli(["device", "set", "enxrog5", "managed", "yes"])
        self.assertEqual(runner.call_count, 2)
        self.assertEqual(runner.call_args_list[0].args[0][0], "/usr/bin/nmcli")
        self.assertEqual(
            runner.call_args_list[1].args[0][:3],
            ["/usr/bin/sudo", "-n", "/usr/bin/nmcli"],
        )

    def test_post_commit_cleanup_allows_recovery_usb_to_reenumerate(self) -> None:
        cycle = SimpleNamespace(wait_host_clean=mock.Mock())
        MODULE.wait_post_commit_host_cleanup(cycle)
        cycle.wait_host_clean.assert_called_once_with()

    def test_failure_cleanup_stops_both_clients_before_host_proof(self) -> None:
        parent = mock.Mock()
        cycle = SimpleNamespace(wait_host_clean=parent.wait_host_clean)
        control = object()
        bundle = object()
        recovery_ncm = (object(),)
        with mock.patch.object(
            MODULE.CYCLE,
            "terminate",
            side_effect=parent.terminate,
        ):
            MODULE.stop_recovery_host(
                cycle,
                control,
                bundle,
                recovery_ncm,
            )
        self.assertEqual(
            parent.mock_calls,
            [
                mock.call.terminate(control),
                mock.call.terminate(bundle),
                mock.call.wait_host_clean(recovery_ncm=recovery_ncm),
            ],
        )

    def test_failure_cleanup_without_ncm_uses_unpinned_host_proof(self) -> None:
        cycle = SimpleNamespace(wait_host_clean=mock.Mock())
        with mock.patch.object(MODULE.CYCLE, "terminate"):
            MODULE.stop_recovery_host(cycle, None, None, None)
        cycle.wait_host_clean.assert_called_once_with()

    def test_failure_cleanup_defers_host_proof_after_target_activation(self) -> None:
        cycle = SimpleNamespace(wait_host_clean=mock.Mock())
        with mock.patch.object(MODULE.CYCLE, "terminate"):
            MODULE.stop_recovery_host(
                cycle,
                None,
                None,
                (object(),),
                target_network_active=True,
            )
        cycle.wait_host_clean.assert_not_called()

    def test_stage_records_are_exact_monotonic_and_bounded(self) -> None:
        boot_id = "11111111-2222-3333-4444-555555555555"
        first = (
            "format=rog5-persistent-root-stage-v2\n"
            f"target_release={MODULE.TARGET_RELEASE}\n"
            f"boot_id={boot_id}\n"
            "sequence=6\n"
            "stage=root-verify\n"
            "state=ENTER\n"
            "detail=none\n"
        ).encode()
        parsed = MODULE.parse_stage_record(first)
        self.assertEqual(parsed.sequence, 6)
        self.assertEqual(parsed.stage, "root-verify")
        self.assertEqual(parsed.state, "ENTER")
        self.assertEqual(parsed.detail, "none")

        image_write = first.replace(b"root-verify", b"image-write")
        self.assertEqual(
            MODULE.parse_stage_record(image_write).stage, "image-write"
        )
        for stage in (
            "userdata-unmount",
            "image-write-window",
            "write-window-precheck",
            "userdata-partition-rw",
            "userdata-disk-rw",
            "write-window-selected-disk-blockdev",
            "write-window-selected-disk-sysfs",
            "write-window-selected-part-blockdev",
            "write-window-selected-part-sysfs",
            "write-window-other-disk-blockdev",
            "write-window-other-disk-sysfs",
            "write-window-other-part-blockdev",
            "write-window-other-part-sysfs",
            "write-window-count",
            "userdata-rw",
            "image-loop-rw",
            "image-fs-rw",
            "image-probe",
            "storage-relock",
        ):
            with self.subTest(stage=stage):
                payload = first.replace(b"root-verify", stage.encode("ascii"))
                self.assertEqual(MODULE.parse_stage_record(payload).stage, stage)

        second = first.replace(b"sequence=6", b"sequence=7").replace(
            b"state=ENTER", b"state=PASS"
        )
        later = MODULE.parse_stage_record(second)
        MODULE.require_stage_successor(parsed, later)
        for hostile in (
            first.rstrip(b"\n"),
            first + b"extra=1\n",
            first.replace(b"root-verify", b"unknown"),
            first.replace(b"state=ENTER", b"state=UNKNOWN"),
            first.replace(b"detail=none", b"detail=UPPERCASE"),
            first.replace(b"detail=none", b"detail=bad/value"),
            first.replace(b"target_release=", b"target_release=wrong-"),
            b"x" * (MODULE.STAGE_RECORD_MAX_BYTES + 1),
        ):
            with self.subTest(payload=hostile[-24:]):
                with self.assertRaises(MODULE.PersistentCycleError):
                    MODULE.parse_stage_record(hostile)

        duplicate = MODULE.parse_stage_record(first)
        MODULE.require_stage_successor(parsed, duplicate)
        with self.assertRaises(MODULE.PersistentCycleError):
            MODULE.require_stage_successor(later, parsed)
        changed_duplicate = MODULE.StageRecord(
            boot_id=parsed.boot_id,
            sequence=parsed.sequence,
            stage="overlay",
            state=parsed.state,
            detail=parsed.detail,
            payload=parsed.payload,
        )
        with self.assertRaises(MODULE.PersistentCycleError):
            MODULE.require_stage_successor(parsed, changed_duplicate)

    def test_fallback_transition_uses_usb_identity_not_nm_state(self) -> None:
        with mock.patch.object(
            MODULE.PIN,
            "fallback_returned",
            return_value=True,
        ) as fallback:
            self.assertTrue(
                MODULE.alpine_fallback_is_present("pci0000:00/usb1/1-1")
            )
        fallback.assert_called_once_with("pci0000:00/usb1/1-1")
        source = MODULE_PATH.read_text()
        shared = (REPO / "scripts/host/run-minimal-headless-live-cycle.py").read_text()
        self.assertIn("cycle.capture_stock_fallback_preboot()", source)
        self.assertIn(MODULE.PROFILE_ID, shared)
        self.assertNotIn("capture_postmortem", source)
        self.assertNotIn("exact Alpine fallback", source)

    def test_runner_delegates_one_bounded_write_to_the_sealed_installer(self) -> None:
        source = MODULE_PATH.read_text()
        for forbidden in (
            "fastboot flash",
            "fastboot erase",
            "mkfs.",
            "sgdisk",
            "parted",
            "blockdev --setrw",
            "ALLOW_NETWORK_ROOT_NFS_HANDOFF",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn('"prepare-commit",', source)
        self.assertIn('"/usr/local/sbin/rog5-install-local-arch-image"', source)
        self.assertIn("ARCH_IMAGE_SHA256", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
