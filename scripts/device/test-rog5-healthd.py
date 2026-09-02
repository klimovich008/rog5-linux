#!/usr/bin/env python3
from __future__ import annotations

import http.client
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
TARGET = REPO / "scripts/device/rog5-healthd.py"
UNIT = REPO / "packaging/arch/rog5-healthd.service"
HEALTH_BODY = b'{"service":"rog5-healthd","status":"ok","version":1}\n'


class HealthdTest(unittest.TestCase):
    def test_exact_health_and_not_found_responses(self) -> None:
        process = subprocess.Popen(
            [sys.executable, str(TARGET), "--bind", "127.0.0.1", "--port", "0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(process.kill)
        assert process.stdout is not None
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        self.assertTrue(selector.select(timeout=5), "healthd did not become ready")
        ready = process.stdout.readline().strip()
        match = re.fullmatch(r"READY bind=127[.]0[.]0[.]1 port=([1-9][0-9]*)", ready)
        self.assertIsNotNone(match)
        port = int(match.group(1))

        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
        connection.request("GET", "/healthz")
        response = connection.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(response.read(), HEALTH_BODY)
        self.assertEqual(response.getheader("Content-Type"), "application/json")
        self.assertEqual(response.getheader("Cache-Control"), "no-store")
        self.assertNotIn("Python", response.getheader("Server", ""))

        connection.request("GET", "/missing")
        response = connection.getresponse()
        self.assertEqual(response.status, 404)
        self.assertEqual(response.read(), b"not found\n")
        connection.close()
        process.terminate()
        self.assertEqual(process.wait(timeout=5), -signal.SIGTERM)
        process.stdout.close()
        assert process.stderr is not None
        process.stderr.close()

    def test_invalid_bind_and_port_fail_before_listen(self) -> None:
        for arguments in (("--bind", "localhost"), ("--port", "65536")):
            with self.subTest(arguments=arguments):
                result = subprocess.run(
                    [sys.executable, str(TARGET), *arguments],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("READY", result.stdout)

    def test_unit_is_bounded_and_registered_for_boot(self) -> None:
        unit = UNIT.read_text()
        for contract in (
            "DynamicUser=yes",
            "ExecStart=/usr/local/libexec/rog5-healthd --bind 0.0.0.0 --port 8787",
            "ProtectSystem=strict",
            "CapabilityBoundingSet=",
            "MemoryMax=64M",
            "RestrictAddressFamilies=AF_INET",
            "SocketBindAllow=tcp:8787",
            "SocketBindDeny=any",
            "WantedBy=multi-user.target",
        ):
            self.assertIn(contract + "\n", unit)
        with tempfile.TemporaryDirectory() as temp:
            projected = Path(temp) / UNIT.name
            projected.write_text(unit.replace("/usr/local/libexec/rog5-healthd", str(TARGET)))
            subprocess.run(
                ["systemd-analyze", "verify", str(projected)], check=True, timeout=10
            )

    def test_source_has_no_credentials_or_storage_surface(self) -> None:
        source = TARGET.read_text() + UNIT.read_text()
        self.assertIsNone(
            re.search(
                r"(?i)(token|password|private[_ -]?key|/dev/(?:sd|block|disk)|"
                r"fastboot|adb|reboot|poweroff|mkfs|sgdisk|tune2fs)",
                source,
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
