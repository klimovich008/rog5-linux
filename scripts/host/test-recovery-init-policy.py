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

    def test_target_payloads_expose_ncm_only(self) -> None:
        for path in (NETWORK_ROOT, PERSISTENT_ROOT):
            source = self.source(path)
            with self.subTest(path=path.name):
                self.assertIn("functions/ncm.usb0", source)
                self.assertNotIn("functions/acm.usb0", source)
                self.assertNotIn("/dev/ttyGS0", source)
                self.assertNotIn("acm", source.lower())
                self.assertIn("169.254.77.2/30", source)

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
        control = source.index("/usr/libexec/rog5-recovery-control &")
        session = source.index("/run/rog5-control/session")
        bind = source.index('echo "$udc" >"$gadget/UDC"')
        self.assertLess(lease, first_isolation)
        self.assertLess(first_isolation, pre_contract)
        self.assertLess(pre_contract, second_isolation)
        self.assertLess(second_isolation, post_contract)
        self.assertLess(post_contract, control)
        self.assertLessEqual(control, session)
        self.assertLess(session, bind)
        self.assertIn(
            "grep -Eq '^session=[0-9a-f]{64}$'",
            source,
        )
        self.assertIn("expected_wrapper_physical_count=116", source)
        self.assertIn(
            '"$expected_wrapper_physical_count"',
            source,
        )

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
