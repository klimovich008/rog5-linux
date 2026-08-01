#!/usr/bin/env python3
"""Static fail-closed policy tests for recovery and target init variants."""

from __future__ import annotations

from pathlib import Path
import re
import unittest


REPO = Path(__file__).resolve().parents[2]
RECOVERY = REPO / "initramfs" / "recovery-init"
NETWORK_ROOT = REPO / "initramfs" / "network-root-init"
PERSISTENT_ROOT = REPO / "initramfs" / "persistent-root-init"
RECOVERY_CONTROL = REPO / "tools/recovery_control/rog5-recovery-control.c"
RECOVERY_FETCH = REPO / "tools/recovery_control/rog5-bundle-fetch.c"


class InitPolicyTest(unittest.TestCase):
    def source(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def test_no_init_exposes_an_interactive_control_surface(self) -> None:
        forbidden = (
            r"\bsh\s+-i\b",
            r"\bsetsid\s+sh\b",
            r"\bserve_acm\b",
            r"\bgetty\b",
        )
        for path in (RECOVERY, NETWORK_ROOT, PERSISTENT_ROOT):
            source = self.source(path)
            with self.subTest(path=path.name):
                for pattern in forbidden:
                    self.assertIsNone(re.search(pattern, source))
        recovery = self.source(RECOVERY)
        for pattern in (
            r"\bauthorized_keys\b",
            r"\bssh-keygen\b",
            r"/usr/sbin/sshd\b",
        ):
            self.assertIsNone(re.search(pattern, recovery))

    def test_target_payload_transports_are_profile_bounded(self) -> None:
        persistent = self.source(PERSISTENT_ROOT)
        self.assertIn("functions/ncm.usb0", persistent)
        self.assertNotIn("functions/acm.usb0", persistent)
        self.assertNotIn("/dev/ttyGS0", persistent)
        self.assertNotIn("acm", persistent.lower())
        self.assertIn("169.254.77.2/30", persistent)

        network = self.source(NETWORK_ROOT)
        self.assertIn("functions/ncm.usb0", network)
        self.assertIn("169.254.77.2/30", network)
        self.assertNotIn("/dev/ttyGS0", network)
        self.assertIn(
            "diagnostic_candidate=headless-netroot-early-diag-v1",
            network,
        )
        self.assertIn(
            '[ "$bundle" = "$diagnostic_candidate" ]', network
        )
        guarded_acm = re.search(
            r'if \[ "\$diagnostic_mode" -eq 1 \]; then\n'
            r'\s*mkdir -p "\$gadget/functions/acm\.usb0".*?\n\s*fi',
            network,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(guarded_acm)
        self.assertIn(
            '"$gadget/configs/c.1/acm.usb0"', guarded_acm.group(0)
        )
        self.assertEqual(network.count("functions/acm.usb0"), 2)
        self.assertEqual(guarded_acm.group(0).count("functions/acm.usb0"), 2)

    def test_recovery_mints_session_after_isolation_before_usb_bind(self) -> None:
        source = self.source(RECOVERY)
        lease = source.index(
            "watchdog_lease=/run/rog5-recovery-watchdog.lease"
        )
        self.assertEqual(source.count("if ! isolate_storage; then"), 2)
        first_isolation = source.index("if ! isolate_storage; then")
        pre_contract = source.index(
            "ASUS wrapper storage topology mismatch before USB configuration"
        )
        second_isolation = source.index(
            "if ! isolate_storage; then",
            first_isolation + 1,
        )
        post_contract = source.index(
            "ASUS wrapper storage topology mismatch after device-node rescan"
        )
        watchdog = source.index("log 'rollback timer armed'")
        postmortem = source.index("if ! snapshot_postmortem; then")
        control = source.index("/usr/libexec/rog5-recovery-control &")
        session = source.index("/run/rog5-control/session")
        bind = source.index('echo "$udc" >"$gadget/UDC"')
        self.assertLess(lease, first_isolation)
        self.assertLess(first_isolation, pre_contract)
        self.assertLess(pre_contract, second_isolation)
        self.assertLess(second_isolation, post_contract)
        self.assertLess(watchdog, postmortem)
        self.assertLess(postmortem, control)
        self.assertLess(post_contract, control)
        self.assertLessEqual(control, session)
        self.assertLess(session, bind)
        self.assertIn(
            "grep -Eq '^session=[0-9a-f]{32}$'",
            source,
        )
        self.assertIn("expected_wrapper_physical_count=116", source)
        self.assertIn(
            '"$expected_wrapper_physical_count"',
            source,
        )

    def test_recovery_session_width_matches_native_responder(self) -> None:
        init_source = self.source(RECOVERY)
        control_source = self.source(RECOVERY_CONTROL)
        native = re.search(
            r'^#define ZERO_ID "([0]+)"$',
            control_source,
            flags=re.MULTILINE,
        )
        init_gate = re.search(
            r"grep -Eq '\^session=\[0-9a-f\]\{([0-9]+)\}\$'",
            init_source,
        )
        self.assertIsNotNone(native)
        self.assertIsNotNone(init_gate)
        self.assertEqual(int(init_gate.group(1)), len(native.group(1)))
        self.assertEqual(len(native.group(1)), 32)

    def test_recovery_creates_fetchers_exact_volatile_root(self) -> None:
        init_source = self.source(RECOVERY)
        fetch_source = self.source(RECOVERY_FETCH)
        native = re.search(
            r'^static const char \*bundle_root = "([^"]+)";$',
            fetch_source,
            flags=re.MULTILINE,
        )
        init_root = re.search(
            r"^bundle_root=(/[A-Za-z0-9/_-]+)$",
            init_source,
            flags=re.MULTILINE,
        )
        self.assertIsNotNone(native)
        self.assertIsNotNone(init_root)
        self.assertEqual(init_root.group(1), native.group(1))
        self.assertEqual(native.group(1), "/run/rog5-bundles")
        for operation in (
            'mkdir -p "$bundle_root"',
            'chown 0:0 "$bundle_root"',
            'chmod 0700 "$bundle_root"',
        ):
            self.assertIn(operation, init_source)
        self.assertLess(
            init_source.index('chmod 0700 "$bundle_root"'),
            init_source.index("/usr/libexec/rog5-recovery-control &"),
        )

    def test_fetch_stage_exit_and_timeout_contracts_match(self) -> None:
        fetch = self.source(RECOVERY_FETCH)
        control = self.source(RECOVERY_CONTROL)
        pairs = (
            ("EXIT_FETCH_ROOT_FAILED", "FETCH_ROOT_FAILED_EXIT"),
            ("EXIT_FETCH_STAGE_FAILED", "FETCH_STAGE_FAILED_EXIT"),
            ("EXIT_FETCH_CONNECT_FAILED", "FETCH_CONNECT_FAILED_EXIT"),
            ("EXIT_FETCH_WORKER_TIMEOUT", "FETCH_WORKER_TIMEOUT_EXIT"),
            ("EXIT_FETCH_WORKER_SIGNAL", "FETCH_WORKER_SIGNAL_EXIT"),
            ("EXIT_FETCH_TRANSPORT_FAILED", "FETCH_TRANSPORT_FAILED_EXIT"),
            ("EXIT_FETCH_HEADER_FAILED", "FETCH_HEADER_FAILED_EXIT"),
            ("EXIT_FETCH_MANIFEST_FAILED", "FETCH_MANIFEST_FAILED_EXIT"),
            ("EXIT_FETCH_ARTIFACT_FAILED", "FETCH_ARTIFACT_FAILED_EXIT"),
            ("EXIT_FETCH_EOF_FAILED", "FETCH_EOF_FAILED_EXIT"),
            (
                "EXIT_FETCH_PARENT_VERIFY_FAILED",
                "FETCH_PARENT_VERIFY_FAILED_EXIT",
            ),
            ("EXIT_FETCH_NORMALIZE_FAILED", "FETCH_NORMALIZE_FAILED_EXIT"),
            (
                "EXIT_FETCH_FINAL_VERIFY_FAILED",
                "FETCH_FINAL_VERIFY_FAILED_EXIT",
            ),
            ("EXIT_FETCH_PUBLISH_FAILED", "FETCH_PUBLISH_FAILED_EXIT"),
            (
                "EXIT_FETCH_WORKER_SETUP_FAILED",
                "FETCH_WORKER_SETUP_FAILED_EXIT",
            ),
            (
                "EXIT_FETCH_WORKER_FORK_FAILED",
                "FETCH_WORKER_FORK_FAILED_EXIT",
            ),
        )

        def macro(source: str, name: str) -> int:
            match = re.search(
                rf"^#define {re.escape(name)} ([0-9]+)$",
                source,
                flags=re.MULTILINE,
            )
            self.assertIsNotNone(match, name)
            return int(match.group(1))

        for fetch_name, control_name in pairs:
            self.assertEqual(
                macro(fetch, fetch_name),
                macro(control, control_name),
            )
        self.assertEqual(macro(fetch, "FETCH_TIMEOUT_MS"), 180000)
        self.assertEqual(macro(control, "FETCH_TIMEOUT_MS"), 190000)

    def test_recovery_snapshots_pstore_without_clearing_it(self) -> None:
        source = self.source(RECOVERY)
        self.assertIn("mount -t pstore -o ro pstore /sys/fs/pstore", source)
        self.assertIn("tail -c 512", source)
        self.assertIn('sha256sum "$snapshot"', source)
        self.assertIn("/run/rog5-postmortem.status", source)
        for forbidden in (
            "rm /sys/fs/pstore",
            "rm -f /sys/fs/pstore",
            "unlink /sys/fs/pstore",
        ):
            self.assertNotIn(forbidden, source)

    def test_recovery_network_is_fixed_and_has_no_route_override(self) -> None:
        source = self.source(RECOVERY)
        self.assertIn("ip address add 169.254.77.2/30 dev usb0", source)
        for forbidden in (
            "rog5.recovery_cidr",
            "rog5.recovery_gateway",
            "udhcpc",
            "ip route replace default",
        ):
            self.assertNotIn(forbidden, source)

    def test_recovery_failures_leave_rollback_armed(self) -> None:
        source = self.source(RECOVERY)
        self.assertIn("touch /run/rog5-recovery-armed", source)
        self.assertIn(
            "watchdog_lease=/run/rog5-recovery-watchdog.lease",
            source,
        )
        self.assertNotIn("rm -f /run/rog5-recovery-armed", source)
        self.assertIn(
            "framed recovery responder exited; rebooting",
            source,
        )
        configfs_failure = re.search(
            r"if ! mount -t configfs.*?\nfi",
            source,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(configfs_failure)
        self.assertIn("force_rollback", configfs_failure.group(0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
