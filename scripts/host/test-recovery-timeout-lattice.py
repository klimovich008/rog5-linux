#!/usr/bin/env python3
"""Keep recovery transfer, cleanup, PREPARE, and COMMIT deadlines nested."""

from __future__ import annotations

from pathlib import Path
import re
import unittest


REPO = Path(__file__).resolve().parents[2]


def source(relative: str) -> str:
    return (REPO / relative).read_text(encoding="utf-8")


def integer_constant(payload: str, name: str) -> int:
    patterns = (
        rf"^#define\s+{re.escape(name)}\s+([0-9]+)$",
        rf"^{re.escape(name)}\s*=\s*([0-9]+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, payload, flags=re.MULTILINE)
        if match is not None:
            return int(match.group(1))
    raise AssertionError(f"missing integer constant {name}")


class RecoveryTimeoutLatticeTest(unittest.TestCase):
    def test_production_deadlines_are_explicit_and_safely_nested(self) -> None:
        fetch = source("tools/recovery_control/rog5-bundle-fetch.c")
        control = source("tools/recovery_control/rog5-recovery-control.c")
        server = source("tools/recovery_control/host_bundle_server.py")
        controller = source("packaging/host/rog5-recovery-bundle-controller")
        lifecycle = source("scripts/host/run-minimal-headless-live-cycle.py")
        stable = source("scripts/host/stable-recovery-control.py")

        worker_ms = integer_constant(fetch, "FETCH_TIMEOUT_MS")
        supervisor_ms = integer_constant(control, "FETCH_TIMEOUT_MS")
        kexec_ms = integer_constant(control, "KEXEC_LOAD_TIMEOUT_MS")
        transfer = integer_constant(server, "TRANSFER_TIMEOUT_SECONDS")
        watchdog = integer_constant(controller, "HARD_SERVER_TIMEOUT_SECONDS")
        offline_watchdog = integer_constant(
            controller, "OFFLINE_HARD_SERVER_TIMEOUT_MAX_SECONDS"
        )
        bundle = integer_constant(lifecycle, "BUNDLE_TIMEOUT_SECONDS")
        prepare = integer_constant(stable, "PREPARE_DEADLINE_SECONDS")
        nfs_ready = integer_constant(stable, "NFS_READY_TIMEOUT_SECONDS")
        control_total = integer_constant(lifecycle, "CONTROL_TIMEOUT_SECONDS")

        self.assertEqual(worker_ms, 180_000)
        self.assertEqual(supervisor_ms, 190_000)
        self.assertEqual(kexec_ms, 15_000)
        self.assertGreaterEqual(supervisor_ms - worker_ms, 10_000)

        supervisor = supervisor_ms // 1000
        kexec = kexec_ms // 1000
        self.assertGreaterEqual(transfer, supervisor + 5)
        self.assertGreaterEqual(watchdog, transfer + 10)
        self.assertGreaterEqual(bundle, watchdog + 10)
        self.assertGreaterEqual(prepare, bundle + 30)
        self.assertGreaterEqual(prepare, supervisor + kexec + 30)
        self.assertGreaterEqual(control_total, prepare + nfs_ready + 10)
        self.assertLessEqual(offline_watchdog, 5)

        self.assertIn(
            "hard_server_timeout=${ROG5_TEST_HARD_SERVER_TIMEOUT:-$OFFLINE_HARD_SERVER_TIMEOUT_MAX_SECONDS}",
            controller,
        )
        self.assertIn("hard_server_timeout=$HARD_SERVER_TIMEOUT_SECONDS", controller)
        self.assertIn("self.bundle_timeout = (", lifecycle)
        self.assertIn("else BUNDLE_TIMEOUT_SECONDS", lifecycle)
        self.assertIn("self.control_timeout = (", lifecycle)
        self.assertIn("else CONTROL_TIMEOUT_SECONDS", lifecycle)


if __name__ == "__main__":
    unittest.main()
