#!/usr/bin/env python3
"""Hardware-free tests for the active read-only Stage-2 runner."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO / "scripts/host/run-persistent-root-storage-live-cycle.py"
LIVE_GATE_PATH = REPO / "scripts/host/run-stable-recovery-live-gate.sh"
SPEC = importlib.util.spec_from_file_location("persistent_root_live", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load persistent-root live runner")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PersistentRootLiveCycleTest(unittest.TestCase):
    def test_v9_track_is_exact_and_probe_bounded(self) -> None:
        specification = importlib.util.spec_from_file_location(
            "persistent_root_live_v9", MODULE_PATH
        )
        assert specification is not None and specification.loader is not None
        candidate = importlib.util.module_from_spec(specification)
        with mock.patch.dict(
            os.environ, {"ROG5_PERSISTENT_ROOT_TRACK": "v9"}
        ):
            specification.loader.exec_module(candidate)
        self.assertEqual(
            candidate.PROFILE_ID,
            "persistent-native-root-v9-generation234-live-v1",
        )
        self.assertEqual(candidate.BUNDLE, "persistent-native-root-v9")
        self.assertEqual(
            candidate.MANIFEST_SHA256,
            "8bc47f291c97c5d52754bd800011864dd385e6993f04d7da1be31b0fc96563e3",
        )
        self.assertEqual(
            candidate.RECOVERY_SHA256,
            "6826c4632a835deec8e5249a601f96c47ba973657ff61dca1067b5eecf3a1334",
        )
        self.assertEqual(
            candidate.SOFTDOG_SHA256,
            "ab0175a40b7dd6186d07b4166d5c2ea3ef3f94f9f0ddf9e08d19e431be294dc4",
        )
        self.assertIn("soft_margin=240", candidate.RUNTIME_COMMAND)
        self.assertIn("count=64", candidate.RUNTIME_COMMAND)
        self.assertIn("sync -f \"$probe\"", candidate.RUNTIME_COMMAND)
        self.assertIn("storage_scope=p23-state-image-only", candidate.RUNTIME_COMMAND)
        self.assertIn("watchdog=softdog-240-disarmed", candidate.RUNTIME_COMMAND)
        self.assertIn("transfer_softdog_module", MODULE_PATH.read_text())

        gate = LIVE_GATE_PATH.read_text()
        contract_table = gate[gate.index("# Historical profiles retain") :]
        profile_start = contract_table.index(
            "\tpersistent-native-root-v9-generation234-live-v1)"
        )
        profile_end = contract_table.index("\n\t\t;;", profile_start)
        profile_contract = contract_table[profile_start:profile_end]
        self.assertIn(
            "initramfs_contract=exact-a600000-pinned-v1", profile_contract
        )
        self.assertIn(
            "initramfs_verifier_expected=$expected_initramfs", profile_contract
        )
        self.assertIn("recovery_init=-", profile_contract)

        evidence = tempfile.NamedTemporaryFile("w", delete=False)
        self.addCleanup(Path(evidence.name).unlink, missing_ok=True)
        evidence.write(
            "\n".join(
                (
                    "format=rog5-persistent-ufs-high-speed-probe-v1",
                    "bytes=67108864",
                    "sha256=3b6a07d0d404fab4e23b6d34bc6696a6a312dd92821332385e5af7c01c421351",
                    "elapsed_ms=8123",
                    "high_speed_markers=2",
                    "ufs_error_events=0",
                    "storage_scope=p23-state-image-only",
                    "watchdog=softdog-240-disarmed",
                    "ufs_probe_result=PASS",
                )
            )
            + "\n"
        )
        evidence.close()
        candidate.parse_ufs_high_speed_probe(Path(evidence.name))

    def test_functional_successor_uses_one_attempt_before_runtime(self) -> None:
        source = MODULE_PATH.read_text()
        self.assertEqual(MODULE.SSH_DIAGNOSTIC_PORT, 8078)
        self.assertEqual(MODULE.SSH_DIAGNOSTIC_MAX_BYTES, 16384)
        self.assertIn("run_one_authenticated_ssh_diagnostic", source)
        self.assertIn("receive_ssh_diagnostic", source)
        self.assertIn("native-root-ssh-client.log", source)
        active = source[source.index("        target_ssh = ssh_arguments") : source.index("    except BaseException")]
        self.assertEqual(active.count("run_one_authenticated_ssh_diagnostic("), 1)
        self.assertNotIn("receive_ssh_diagnostic(", active)
        self.assertIn("parse_runtime_evidence(runtime_log)", active)
        self.assertNotIn("wait_for_authenticated_ssh(", source)
        self.assertNotIn("while True:\n            now = time.monotonic()", source)

    def test_runtime_waits_boundedly_for_the_systemd_ready_marker(self) -> None:
        command = MODULE.RUNTIME_COMMAND
        self.assertIn('ready=/run/rog5-p2-ready', command)
        self.assertIn('ready_wait=0', command)
        self.assertIn(
            'while ! runtime_ready && [ "$ready_wait" -lt 90 ]; do',
            command,
        )
        self.assertEqual(command.count('sleep 1'), 1)
        self.assertIn('ready_wait=$((ready_wait + 1))', command)
        self.assertIn('runtime_ready() {', command)
        self.assertEqual(command.count('runtime_ready\n'), 1)
        self.assertIn('systemctl is-active --quiet rog5-early-sshd.service', command)
        self.assertIn('systemctl is-active --quiet rog5-p2-ready.service', command)

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
            "persistent-native-root-v8-generation233-live-v1",
        )
        self.assertEqual(MODULE.PROFILE.candidate, MODULE.BUNDLE)
        self.assertEqual(MODULE.PROFILE.bundle, MODULE.BUNDLE)
        self.assertEqual(MODULE.PROFILE.bundle_profile, "persistent-root-ro-v1")
        self.assertEqual(MODULE.PROFILE.recovery_profile, MODULE.PROFILE_ID)
        self.assertFalse(MODULE.PROFILE.diagnostic)
        self.assertEqual(MODULE.TARGET_PRODUCT, "ROG5 persistent root")
        self.assertEqual(MODULE.TARGET_UDEV_MODEL, "ROG5_persistent_root")
        sealed_init = (REPO / "initramfs/persistent-root-init").read_text()
        self.assertIn(
            f"echo '{MODULE.TARGET_PRODUCT}' >\"$gadget/strings/0x409/product\"",
            sealed_init,
        )
        self.assertEqual(
            MODULE.BUNDLE,
            "persistent-native-root-v8",
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
            "generation233",
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
        runtime = source.index("runtime_status = run_optional_logged(", host_key)
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

    def test_runtime_evidence_accepts_exact_native_root(self) -> None:
        payload = "\n".join(
            (
                "format=rog5-native-root-runtime-v1",
                "boot_id=11111111-2222-3333-4444-555555555555",
                "uptime_seconds=21.00",
                "status=PASS",
                "kernel=7.1.4-g359318de534f",
                "physical_blocks=117",
                "block_backed_mounts=1",
                "root_mount=native-root-ro-noload",
                "local_image_write_probe=PASS",
                "root=native-ext4-overlay-tmpfs",
                "blocked_device_queries=0",
                "blocked_scsi_commands=0",
                "journal_recovery_events=0",
                "ufs_error_events=0",
                "backlights=0",
                "ssh=strict-key-only",
                "failed_units=0",
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
    def test_runtime_evidence_rejects_missing_duplicate_and_wrong_root(self) -> None:
        baseline = [
            "format=rog5-native-root-runtime-v1",
            "boot_id=11111111-2222-3333-4444-555555555555",
            "status=PASS",
            "kernel=7.1.4-g359318de534f",
            "physical_blocks=117",
            "block_backed_mounts=1",
            "root_mount=native-root-ro-noload",
            "root=native-ext4-overlay-tmpfs",
            "blocked_device_queries=0",
            "blocked_scsi_commands=0",
            "journal_recovery_events=0",
            "ufs_error_events=0",
            "ssh=strict-key-only",
            "failed_units=0",
            "result=PASS",
        ]
        hostile = (
            [line.replace("native-ext4", "local-ext4") for line in baseline],
            baseline + ["boot_id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"],
            [line for line in baseline if line != "physical_blocks=117"],
            baseline + ["root=native-ext4-overlay-tmpfs"],
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

    def test_one_ssh_attempt_retains_complete_bounded_transcript(self) -> None:
        result = subprocess.CompletedProcess([], 255, "first refusal\n")
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            MODULE.CYCLE, "run_capture", return_value=result
        ) as runner, mock.patch.object(
            MODULE.time, "monotonic", side_effect=(0.0, 1.25)
        ):
            status, elapsed = MODULE.run_one_authenticated_ssh_diagnostic(
                ["ssh", "root@169.254.77.2"],
                Path(temporary) / "client.log",
            )
            payload = (Path(temporary) / "client.log").read_text()
        self.assertEqual(status, 255)
        self.assertEqual(elapsed, 1.25)
        self.assertEqual(runner.call_count, 1)
        self.assertIn("status=255\n", payload)
        self.assertIn("output_hex=6669727374207265667573616c0a\n", payload)

    def test_one_ssh_attempt_rejects_oversized_output(self) -> None:
        result = subprocess.CompletedProcess(
            [], 255, "x" * (MODULE.SSH_CLIENT_MAX_BYTES + 1)
        )
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            MODULE.CYCLE, "run_capture", return_value=result
        ), mock.patch.object(MODULE.time, "monotonic", side_effect=(0.0, 1.0)):
            with self.assertRaisesRegex(
                MODULE.PersistentCycleError, "transcript exceeded"
            ):
                MODULE.run_one_authenticated_ssh_diagnostic(
                    ["ssh"], Path(temporary) / "client.log"
                )

    def test_one_successful_ssh_attempt_requires_the_exact_marker(self) -> None:
        good = subprocess.CompletedProcess(
            [], 0, f"debug line\n{MODULE.AUTHENTICATED_SSH_READY_MARKER}\n"
        )
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            MODULE.CYCLE, "run_capture", return_value=good
        ), mock.patch.object(MODULE.time, "monotonic", side_effect=(0.0, 1.0)):
            status, _ = MODULE.run_one_authenticated_ssh_diagnostic(
                ["ssh"], Path(temporary) / "good.log"
            )
            self.assertEqual(status, 0)

        wrong = subprocess.CompletedProcess([], 0, "debug only\n")
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            MODULE.CYCLE, "run_capture", return_value=wrong
        ), mock.patch.object(MODULE.time, "monotonic", side_effect=(0.0, 1.0)):
            with self.assertRaisesRegex(
                MODULE.PersistentCycleError, "lacks its exact readiness marker"
            ):
                MODULE.run_one_authenticated_ssh_diagnostic(
                    ["ssh"], Path(temporary) / "wrong.log"
                )

    def test_target_ssh_diagnostic_is_exact_bounded_and_boot_correlated(self) -> None:
        boot_id = "12345678-1234-1234-1234-123456789abc"
        values = {
            "format": "rog5-native-ssh-diagnostic-v1",
            "target_release": MODULE.TARGET_RELEASE,
            "boot_id": boot_id,
            "auth_event": "present",
            "shadow_class": "x",
            "shadow_metadata": "0:0:600:123:1",
            "lower_shadow_class": "locked",
            "lower_shadow_metadata": "0:0:600:234:1",
            "root_metadata": "0:0:700:4096:3",
            "root_ssh_metadata": "0:0:700:4096:2",
            "authorized_keys_metadata": "0:0:600:81:1",
            "run_nologin": "absent",
            "etc_nologin": "absent",
            "system_state": "starting",
            "early_sshd": "active",
            "sshd_usepam": "yes",
            "sshd_permitrootlogin": "prohibit-password",
            "sshd_pubkeyauthentication": "yes",
            "sshd_passwordauthentication": "no",
            "sshd_kbdinteractiveauthentication": "no",
            "sshd_persourcepenalties_sha256": "1" * 64,
            "log_bytes": "12",
            "log_sha256": "2" * 64,
            "log_tail_hex": "414243",
            "result": "PASS",
        }

        def payload(overrides: dict[str, str] | None = None) -> bytes:
            current = {**values, **(overrides or {})}
            return "".join(
                f"{name}={current[name]}\n" for name in MODULE.SSH_DIAGNOSTIC_FIELDS
            ).encode("ascii")

        class Connection:
            def __init__(self, raw: bytes) -> None:
                self.raw = raw

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def settimeout(self, _timeout: float) -> None:
                pass

            def recv(self, _maximum: int) -> bytes:
                raw, self.raw = self.raw, b""
                return raw

            def getsockname(self):
                return ("169.254.77.1", MODULE.SSH_DIAGNOSTIC_PORT)

        class Listener:
            def __init__(self, raw: bytes) -> None:
                self.raw = raw

            def accept(self):
                return Connection(self.raw), ("169.254.77.2", 40000)

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "target.record"
            parsed = MODULE.receive_ssh_diagnostic(
                Listener(payload()), boot_id, output
            )
            self.assertEqual(parsed["shadow_class"], "x")
            self.assertEqual(output.read_bytes(), payload())
            with self.assertRaises(MODULE.PersistentCycleError):
                MODULE.receive_ssh_diagnostic(
                    Listener(payload({"boot_id": "0" * 36})),
                    boot_id,
                    Path(temporary) / "wrong.record",
                )

    def test_fastboot_fallback_record_rejects_recovery(self) -> None:
        base = (
            "format=rog5-stock-android-fallback-v1\n"
            "serial=M5AIKN00F0353YH\n"
            "usb_location=1-1.2\n"
            "evidence_mode=fastboot-slot-a\n"
            "slot_suffix=_a\n"
            "usb_config=fastboot\n"
            "result=PASS\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fallback.record"
            path.write_text(base)
            self.assertTrue(MODULE.exact_fastboot_fallback_record(path))
            path.write_text(
                base.replace("fastboot-slot-a", "usb-unauthorized-slot-a").replace(
                    "usb_config=fastboot", "usb_config=adb-unauthorized"
                )
            )
            self.assertFalse(MODULE.exact_fastboot_fallback_record(path))

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

    def test_runner_executes_one_read_only_native_boot_then_fastboot(self) -> None:
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
        self.assertIn("run_one_authenticated_ssh_diagnostic", source)
        self.assertIn("parse_runtime_evidence(runtime_log)", source)
        self.assertIn("ALLOW_NATIVE_ROOT_BOOT", source)
        self.assertNotIn("ALLOW_STAGE2_NATIVE_FSCK", source)
        self.assertNotIn("ALLOW_STAGE2_P24_CLONE", source)
        self.assertIn("exact_fastboot_fallback_record", source)
        self.assertIn("native-root-reboot.log", source)
        self.assertNotIn('"/usr/bin/systemctl reboot"', source)
        self.assertNotIn("ARCH_IMAGE_SHA256", source)

    def test_native_verify_evidence_is_exact_and_hostile(self) -> None:
        tree = [
            "ROG5_NATIVE_TREE_V1 item=seal status=PASS metadata=0:0:444:430:1 "
            "sha256=02231e86746fbc656090f52c96d7e0c968c7ca86ba7449c306f611ea20c6a876",
            "ROG5_NATIVE_TREE_V1 item=init status=PASS metadata=symlink "
            "sha256=a8da8f10c8ab68bf1cc2234032b9ba3fd66d16ea84872acca9461c985224dc94",
            "ROG5_NATIVE_TREE_V1 item=systemd status=PASS metadata=0:0:755:198968:1 "
            "sha256=dad2b1339d6b9178f83ef96791e5c020604e16ec7921e6eaf89d3b38eec478d0",
            "ROG5_NATIVE_TREE_V1 item=sshd status=PASS metadata=0:0:755:527008:1 "
            "sha256=6a88a601266f5775291e394106e97fa0c1c38ac10a1715c56156cda7e8812932",
            "ROG5_NATIVE_TREE_V1 item=ssh-keygen status=PASS metadata=0:0:755:526688:1 "
            "sha256=e238ce08e1a4fa0d9d8fe5022e47bf9a841de23370b043c457e13f45e9d90d4e",
            "ROG5_NATIVE_TREE_V1 item=authorized-keys status=PASS metadata=0:0:600:81:1 "
            "sha256=04f39d5949c813450e201b7e579256b1afcd5c7fcea077d36ae445aa53519b61",
            "ROG5_NATIVE_TREE_V1 item=ssh-policy status=PASS metadata=0:0:644:201:1 "
            "sha256=c6b01ef801333ee11bb8805a250df2c4f02f38f0015df1449dadb66490e43693",
        ]
        terminal = (
            "ROG5_NATIVE_POSTMORTEM_V1 stage=terminal status=PASS "
            "disposition=grown-target "
            "uuid=8b03827a-cc2d-4408-8558-e9b61195f96b blocks=8388603 "
            "state=clean label=ROG5_ARCH_A tree=BOOT_CRITICAL_PASS "
            "prefix_sha256="
            "4624159a5ad652036ad1facfc3e1dcf0c38024d1a3d7aeda9e7c9d92a13a0647"
        )
        expected = [
            "ROG5_NATIVE_POSTMORTEM_V1 stage=inspect status=READ",
            *tree,
            terminal,
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "verify.log"
            path.write_text(
                "\n".join([*expected, "Connection closed"]) + "\n"
            )
            result = MODULE.parse_verify_evidence(path)
            self.assertEqual(result.disposition, "BOOT_CRITICAL_PASS")
            self.assertEqual(result.mismatches, ())

            mismatch = list(expected)
            mismatch[4] = mismatch[4].replace(
                "status=PASS", "status=MISMATCH"
            ).replace(
                "6a88a601266f5775291e394106e97fa0c1c38ac10a1715c56156cda7e8812932",
                "0" * 64,
            )
            mismatch[-1] = mismatch[-1].replace(
                "BOOT_CRITICAL_PASS", "BOOT_CRITICAL_MISMATCH"
            )
            path.write_text("\n".join(mismatch) + "\n")
            result = MODULE.parse_verify_evidence(path)
            self.assertEqual(result.mismatches, ("sshd",))
            hostile = (
                expected[:1],
                [*expected, expected[-1]],
                [expected[1], expected[0]],
                [expected[0], *tree, terminal.replace("grown-target", "partial-ext4")],
                [expected[0], *tree, terminal.replace("BOOT_CRITICAL_PASS", "SKIP")],
                [expected[0], *tree, terminal.replace("8388603", "4194304")],
                [expected[0], *tree[:-1], terminal],
                [expected[0], *tree, tree[-1], terminal],
                [
                    expected[0],
                    tree[0].replace("status=PASS", "status=MISMATCH"),
                    *tree[1:],
                    terminal,
                ],
                [
                    expected[0],
                    *tree,
                    "ROG5_NATIVE_POSTMORTEM_V1 stage=terminal status=FAIL reason=target-tree",
                ],
            )
            for payload in hostile:
                path.write_text("\n".join(payload) + "\n")
                with self.assertRaises(MODULE.PersistentCycleError):
                    MODULE.parse_verify_evidence(path)

    def test_native_repair_evidence_is_exact_and_hostile(self) -> None:
        expected = [
            "ROG5_NATIVE_REPAIR_V1 stage=repair status=BEGIN",
            "ROG5_NATIVE_REPAIR_V1 stage=watchdog status=ARMED",
            "ROG5_NATIVE_REPAIR_V1 stage=watchdog status=DISARMED",
            "ROG5_NATIVE_REPAIR_V1 stage=terminal status=PASS "
            "files=sshd,ssh-keygen bytes=1053696 storage=RELOCKED",
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "repair.log"
            path.write_text("\n".join([*expected, "Connection closed"]) + "\n")
            MODULE.parse_repair_evidence(path)
            hostile = (
                expected[:-1],
                [*expected, expected[-1]],
                [expected[1], expected[0], *expected[2:]],
                [*expected[:-1], expected[-1].replace("RELOCKED", "WRITABLE")],
                [*expected[:-1], expected[-1].replace("1053696", "1053695")],
                [expected[0], expected[1], expected[-1]],
                [expected[0], expected[1], "ROG5_NATIVE_REPAIR_V1 stage=terminal status=FAIL reason=write-sshd"],
            )
            for payload in hostile:
                path.write_text("\n".join(payload) + "\n")
                with self.assertRaises(MODULE.PersistentCycleError):
                    MODULE.parse_repair_evidence(path)

    def test_native_fsck_evidence_is_exact_and_hostile(self) -> None:
        prefix = [
            "ROG5_NATIVE_REPAIR_V1 stage=fsck status=BEGIN",
            "ROG5_NATIVE_REPAIR_V1 stage=watchdog status=ARMED",
            "ROG5_NATIVE_REPAIR_V1 stage=watchdog status=DISARMED",
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fsck.log"
            for status in (0, 1, 2):
                terminal = (
                    "ROG5_NATIVE_REPAIR_V1 stage=terminal status=PASS "
                    f"operation=fsck status_code={status} "
                    "storage=RELOCKED tree=PASS"
                )
                path.write_text("\n".join([*prefix, terminal]) + "\n")
                self.assertEqual(MODULE.parse_fsck_evidence(path), status)
            hostile = (
                prefix,
                [prefix[1], prefix[0], prefix[2], terminal],
                [*prefix, terminal.replace("status_code=2", "status_code=4")],
                [*prefix, terminal.replace("RELOCKED", "WRITABLE")],
                [*prefix, terminal, terminal],
            )
            for payload in hostile:
                path.write_text("\n".join(payload) + "\n")
                with self.assertRaises(MODULE.PersistentCycleError):
                    MODULE.parse_fsck_evidence(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
