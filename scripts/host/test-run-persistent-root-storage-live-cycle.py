#!/usr/bin/env python3
"""Hardware-free tests for the read-only watchdog probe runner."""

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
    def test_exact_slot_a_fastboot_terminates_target_wait_early(self) -> None:
        with mock.patch.object(MODULE.STOCK, "exact_fastboot", return_value=True) as exact, mock.patch.object(
            MODULE.STOCK,
            "fastboot_value",
            side_effect=lambda name: {"product": "lahaina", "current-slot": "a"}[name],
        ):
            self.assertTrue(
                MODULE.stock_fastboot_returned(
                    "pci0000:00/0000:00:08.1/0000:04:00.3/usb1/1-1/1-1.2"
                )
            )
            exact.assert_called_once_with("1-1.2")

        with mock.patch.object(MODULE.STOCK, "exact_fastboot", return_value=False):
            self.assertFalse(
                MODULE.stock_fastboot_returned(
                    "pci0000:00/0000:00:08.1/0000:04:00.3/usb1/1-1/1-1.2"
                )
            )

        with mock.patch.object(MODULE.STOCK, "exact_fastboot", return_value=True), mock.patch.object(
            MODULE.STOCK,
            "fastboot_value",
            side_effect=lambda name: {"product": "lahaina", "current-slot": "b"}[name],
        ):
            with self.assertRaises(MODULE.PersistentCycleError):
                MODULE.stock_fastboot_returned(
                    "pci0000:00/0000:00:08.1/0000:04:00.3/usb1/1-1/1-1.2"
                )

    def test_profile_and_artifact_identities_are_exact(self) -> None:
        self.assertEqual(MODULE.FALLBACK_TIMEOUT_SECONDS, 930)
        self.assertEqual(
            MODULE.PROFILE_ID,
            "storage-layout-stage2-softdog-direct-clone-v1-generation211-live-v1",
        )
        self.assertEqual(MODULE.PROFILE.candidate, MODULE.BUNDLE)
        self.assertEqual(MODULE.PROFILE.bundle, MODULE.BUNDLE)
        self.assertEqual(MODULE.PROFILE.bundle_profile, "persistent-root-ro-v1")
        self.assertEqual(MODULE.PROFILE.recovery_profile, MODULE.PROFILE_ID)
        self.assertFalse(MODULE.PROFILE.diagnostic)
        self.assertEqual(MODULE.TARGET_PRODUCT, "ROG5 local image stage")
        self.assertEqual(MODULE.TARGET_UDEV_MODEL, "ROG5_local_image_stage")
        sealed_init = (REPO / "initramfs/local-image-stage-init").read_text()
        self.assertIn(
            f"echo '{MODULE.TARGET_PRODUCT}' >\"$gadget/strings/0x409/product\"",
            sealed_init,
        )
        self.assertEqual(
            MODULE.BUNDLE,
            "storage-layout-stage2-softdog-direct-clone-v1",
        )

    def test_watchdog_lifetime_artifact_and_admission_identities_are_exact(self) -> None:
        self.assertEqual(
            MODULE.COMPONENT_ROOT.name,
            "storage-layout-stage2-mainline-readonly-v2-recovery-components-20260826-r1",
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
            "generation211",
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
            "consume-exact-boot-claim.py",
        )

    def test_continuous_runner_has_no_manual_boundary_after_commit(self) -> None:
        source = MODULE_PATH.read_text()
        handoff = source.index("        cycle.wait_bundle(bundle_process, control_process)\n")
        network = source.index("interface = activate_target_network(cycle, anchor)")
        host_key = source.index("wait_for_target_host_key(cycle, anchor, target_known_hosts)")
        runtime = source.index("runtime_status = run_optional_logged(")
        self.assertLess(handoff, network)
        self.assertLess(network, host_key)
        self.assertLess(host_key, runtime)
        segment = source[handoff:runtime]
        self.assertNotIn("input(", segment)
        self.assertNotIn("STOCK.fastboot(", segment)
        self.assertNotIn("wait_for_stage_host_key(", segment)

    def test_local_root_preflight_has_no_image_transfer_or_write(self) -> None:
        source = MODULE_PATH.read_text()
        preflight = source[
            source.index("def preflight(") : source.index("def stop_recovery_host(")
        ]
        self.assertNotIn("ARCH_IMAGE_GZ", preflight)
        self.assertNotIn("transfer_arch_image", source)
        self.assertNotIn("ARCH_IMAGE_RAW", source)
        self.assertNotIn("DIRECT_STREAMER", source)
        self.assertIn("parse_runtime_evidence(runtime_log)", source)

    def test_terminal_stage_stops_the_host_key_wait(self) -> None:
        source = MODULE_PATH.read_text()
        receive = source.index("current = receive_stage_record(listener)")
        terminal = source.index('if current.state == "FAIL":', receive)
        wait = source.index("status = CYCLE.wait_process(process, 5)", receive)
        self.assertLess(receive, terminal)
        self.assertLess(terminal, wait)

    def test_softdog_armed_stage_is_an_exact_terminal_successor(self) -> None:
        source = MODULE_PATH.read_text()
        self.assertEqual(MODULE.SOFTDOG_PROBE_DETAIL, "softdog-armed-20")
        self.assertEqual(source.count("or current.detail == SOFTDOG_PROBE_DETAIL"), 1)
        self.assertEqual(
            source.count("or accepted_stage.detail == SOFTDOG_PROBE_DETAIL"), 1
        )

    def test_fastboot_return_stops_the_post_ncm_host_key_wait(self) -> None:
        source = MODULE_PATH.read_text()
        start = source.index("def wait_for_target_host_key(")
        timeout = source.index("except (TimeoutError, socket.timeout):", start)
        next_stage = source.index("if previous is not None:", timeout)
        self.assertIn("stock_fastboot_returned(expected_location)", source[timeout:next_stage])

    def test_success_uses_the_exact_fallback_proof_once(self) -> None:
        source = MODULE_PATH.read_text()
        fallback = source.index("        cycle.wait_fallback(None)\n")
        clean = source.index("        cycle.wait_host_clean(final=True)\n", fallback)
        resolved = source.index('        cycle.resolve_intent(intent, "TARGET_ACCEPTED")\n', clean)
        segment = source[fallback:clean]
        self.assertNotIn("stock_fastboot_returned(", segment)
        self.assertLess(clean, resolved)

    def test_runtime_evidence_accepts_dynamic_device_letter(self) -> None:
        payload = "\n".join(
            (
                "format=rog5-native-clone-runtime-v1",
                "boot_id=11111111-2222-3333-4444-555555555555",
                "uptime_seconds=21.00",
                "state=READY",
                "physical_blocks=117",
                "storage=read-only",
                "ssh=key-only",
                "userdata=/dev/sdg23",
                "watchdog_record=present",
                f"watchdog_record_sha256={'1' * 64}",
                "watchdog_pid=123",
                "watchdog_process=absent",
                "watchdog_log_bytes=0",
                "watchdog_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "watchdog_log_hex=",
                "watchdog_driver=qcom_wdt",
                "watchdog_compatible=qcom,kpss-wdt",
                "watchdog_device=present",
                "watchdog_module=present",
                "watchdog_observer=absent",
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
            observed = payload.replace(
                "watchdog_observer=absent",
                "watchdog_observer=ROG5_WDT_OBSERVER_V1 rate=32764 "
                "en=00000001 sts=00000001 bark=000b0000 bite=000c8000",
            )
            path.write_text(observed)
            self.assertEqual(
                MODULE.parse_runtime_evidence(path),
                "11111111-2222-3333-4444-555555555555",
            )

    def test_runtime_evidence_rejects_missing_duplicate_and_wrong_storage(self) -> None:
        baseline = [
            "format=rog5-native-clone-runtime-v1",
            "boot_id=11111111-2222-3333-4444-555555555555",
            "state=READY",
            "physical_blocks=117",
            "storage=read-only",
            "ssh=key-only",
            "userdata=/dev/sda23",
            "watchdog_record=present",
            f"watchdog_record_sha256={'1' * 64}",
            "watchdog_pid=123",
            "watchdog_process=absent",
            "watchdog_log_bytes=0",
            "watchdog_log_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "watchdog_log_hex=",
            "watchdog_driver=qcom_wdt",
            "watchdog_compatible=qcom,kpss-wdt",
            "watchdog_device=present",
            "watchdog_module=present",
            "watchdog_observer=absent",
            "result=PASS",
        ]
        hostile = (
            baseline[:-2] + ["userdata=/dev/mmcblk0p23", "result=PASS"],
            baseline + ["boot_id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"],
            [line for line in baseline if line != "physical_blocks=117"],
            baseline + ["storage=read-only"],
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

    def test_post_commit_activates_target_without_redundant_cleanup_wait(self) -> None:
        source = MODULE_PATH.read_text()
        handoff = source.index("        cycle.wait_bundle(bundle_process, control_process)\n")
        forget = source.index("        recovery_ncm = None\n", handoff)
        target = source.index(
            "        interface = activate_target_network(cycle, anchor)\n",
            handoff,
        )
        self.assertNotIn("wait_post_commit_host_cleanup", source)
        self.assertLess(handoff, forget)
        self.assertLess(forget, target)

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

    def test_failed_fallback_proof_cannot_resolve_the_intent(self) -> None:
        source = MODULE_PATH.read_text()
        self.assertIn("fallback_proven = False", source)
        self.assertIn("and fallback_proven:", source)
        self.assertNotIn(
            "and fallback_attempted:\n            try:\n                cycle.resolve_intent",
            source,
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
        self.assertIn("power-usb", MODULE.STAGES)
        self.assertIn("storage-locked", MODULE.STAGES)
        self.assertNotIn("storage-relock", MODULE.STAGES)
        boot_id = "11111111-2222-3333-4444-555555555555"
        first = (
            "format=rog5-persistent-root-stage-v2\n"
            f"target_release={MODULE.TARGET_RELEASE}\n"
            f"boot_id={boot_id}\n"
            "sequence=6\n"
            "stage=runtime\n"
            "state=ENTER\n"
            "detail=none\n"
        ).encode()
        parsed = MODULE.parse_stage_record(first)
        self.assertEqual(parsed.sequence, 6)
        self.assertEqual(parsed.stage, "runtime")
        self.assertEqual(parsed.state, "ENTER")
        self.assertEqual(parsed.detail, "none")

        second = first.replace(b"sequence=6", b"sequence=7").replace(
            b"state=ENTER", b"state=PASS"
        )
        later = MODULE.parse_stage_record(second)
        MODULE.require_stage_successor(parsed, later)
        locked = MODULE.parse_stage_record(
            first.replace(b"stage=runtime", b"stage=storage-locked")
        )
        self.assertEqual(locked.stage, "storage-locked")
        observer_detail = (
            b"wdt-r32764-e00000001-s00000001-b000b0000-i000c8000"
        )
        observer = MODULE.parse_stage_record(
            first.replace(b"detail=none", b"detail=" + observer_detail)
        )
        self.assertRegex(observer.detail, MODULE.WATCHDOG_OBSERVER_DETAIL)
        for hostile in (
            first.rstrip(b"\n"),
            first + b"extra=1\n",
            first.replace(b"runtime", b"unknown"),
            first.replace(b"runtime", b"storage-relock"),
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
            stage="ufs-ready",
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

    def test_runner_executes_one_bounded_clone_then_fastboot(self) -> None:
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
        self.assertIn("RUNTIME_COMMAND", source)
        self.assertIn('CLONE_COMMAND = "/usr/local/sbin/rog5-install-local-arch-image"', source)
        self.assertIn("parse_clone_evidence(clone_log)", source)
        self.assertIn("ALLOW_STAGE2_P24_CLONE", source)
        self.assertIn("clone_log, 850", source)
        self.assertLess(850, MODULE.FALLBACK_TIMEOUT_SECONDS)
        self.assertNotIn('"/usr/bin/systemctl reboot"', source)
        self.assertNotIn("ARCH_IMAGE_SHA256", source)

    def test_clone_evidence_is_exact(self) -> None:
        expected = [
            "ROG5_NATIVE_CLONE_V1 stage=source status=VERIFY",
            "ROG5_NATIVE_CLONE_V1 stage=clone status=WRITE",
            "ROG5_NATIVE_CLONE_V1 stage=watchdog status=ARMED",
            "ROG5_NATIVE_CLONE_V1 stage=filesystem status=GROW",
            "ROG5_NATIVE_CLONE_V1 stage=seal status=WRITE",
            "ROG5_NATIVE_CLONE_V1 stage=readonly status=VERIFY",
            "ROG5_NATIVE_CLONE_V1 stage=watchdog status=DISARMED",
            "ROG5_NATIVE_CLONE_V1 stage=terminal status=PASS "
            "target_uuid=8b03827a-cc2d-4408-8558-e9b61195f96b target_blocks=8388603",
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "clone.log"
            path.write_text("\n".join([*expected, "Connection closed"]) + "\n")
            MODULE.parse_clone_evidence(path)
            hostile = (
                expected[:1],
                [*expected, expected[-1]],
                [*expected[:-1], expected[-1].replace("PASS", "FAIL")],
                [expected[1], expected[0], *expected[2:]],
            )
            for payload in hostile:
                path.write_text("\n".join(payload) + "\n")
                with self.assertRaises(MODULE.PersistentCycleError):
                    MODULE.parse_clone_evidence(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
