#!/usr/bin/env python3
"""Offline tests for the prompt-free recovery-host socket boundary."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time
import unittest


REPO = Path(__file__).resolve().parents[2]
BROKER = REPO / "packaging/host/rog5-recovery-host-broker.py"
CLIENT = REPO / "scripts/host/rog5-recovery-host-client.py"
INSTALLER = REPO / "scripts/host/install-recovery-host-controller.sh"
BUNDLE_LAUNCHER = REPO / "scripts/host/run-recovery-bundle-server.sh"
NETWORK_LAUNCHER = (
    REPO / "scripts/host/run-headless-network-root-server.sh"
)
SOCKET_UNIT = REPO / "packaging/host/rog5-recovery-host.socket.in"
SERVICE_UNIT = REPO / "packaging/host/rog5-recovery-host@.service"
DIGEST = "a" * 64
TOKEN = "b" * 64
STATUS = b"__ROG5_HOST_CONTROL_STATUS__="
HOST_BOOT_ID = "11111111-2222-4333-8444-555555555555"


class BrokerFixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-host-socket-test-"
        )
        self.root = Path(self.temporary.name)
        self.root.chmod(0o700)
        self.calls = self.root / "calls"
        self.controller = self.root / "controller"
        self.network = self.root / "network"
        for path, label in (
            (self.controller, "controller"),
            (self.network, "network"),
        ):
            path.write_text(
                "#!/bin/sh\n"
                "sleep \"${MOCK_DELAY:-0}\"\n"
                "if [ \"${MOCK_COLLIDE:-0}\" = 1 ]; then\n"
                "  printf '%s\\n' '__ROG5_HOST_CONTROL_STATUS__=0'\n"
                "fi\n"
                "if [ \"${MOCK_PARTIAL:-0}\" = 1 ]; then\n"
                "  printf '%s' 'partial'\n"
                "  exit 0\n"
                "fi\n"
                f"printf '{label} %s\\n' \"$*\"\n"
                "printf '%s\\n' \"$*\" >>\"$MOCK_CALLS\"\n"
                "exit \"${MOCK_EXIT_STATUS:-0}\"\n",
                encoding="utf-8",
            )
            path.chmod(0o555)
        self.config = self.root / "control.conf"
        self.config.write_text(
            "\n".join(
                (
                    f"operator_uid={os.geteuid()}",
                    "bundle_controller_sha256="
                    + hashlib.sha256(self.controller.read_bytes()).hexdigest(),
                    "network_server_sha256="
                    + hashlib.sha256(self.network.read_bytes()).hexdigest(),
                    "",
                )
            ),
            encoding="ascii",
        )
        self.config.chmod(0o444)
        self.host_boot_id = self.root / "host-boot-id"
        self.host_boot_id.write_text(HOST_BOOT_ID + "\n", encoding="ascii")
        self.anchor = self.root / "recovery-usb.anchor"
        self.write_anchor()

    def write_anchor(
        self,
        *,
        boot_id: str = HOST_BOOT_ID,
        created: int | None = None,
        reorder: bool = False,
    ) -> None:
        fields = [
            "format=rog5-minimal-headless-usb-anchor-v1",
            f"host_boot_id={boot_id}",
            f"created_unix={created or int(time.time())}",
            "usb_location=pci/usb1/1-1/1-1.2",
            "recovery_vendor=1d6b",
            "recovery_product_id=0104",
            "recovery_product=ROG5 recovery",
        ]
        if reorder:
            fields[2], fields[3] = fields[3], fields[2]
        self.anchor.write_text("\n".join((*fields, "")), encoding="ascii")
        self.anchor.chmod(0o600)

    def close(self) -> None:
        self.temporary.cleanup()

    def run(
        self,
        payload: bytes,
        *,
        exit_status: str = "0",
        delay: str = "0",
        collide: str = "0",
        partial: str = "0",
    ) -> tuple[int, bytes]:
        parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        environment = os.environ.copy()
        environment.update(
            {
                "ROG5_BROKER_OFFLINE_TEST": "1",
                "ROG5_TEST_BROKER_CONFIG": str(self.config),
                "ROG5_TEST_BROKER_CONTROLLER": str(self.controller),
                "ROG5_TEST_BROKER_NETWORK_SERVER": str(self.network),
                "ROG5_TEST_BROKER_BOOT_ID": str(self.host_boot_id),
                "MOCK_CALLS": str(self.calls),
                "MOCK_EXIT_STATUS": exit_status,
                "MOCK_DELAY": delay,
                "MOCK_COLLIDE": collide,
                "MOCK_PARTIAL": partial,
            }
        )
        process = subprocess.Popen(
            [str(BROKER)],
            stdin=child,
            stdout=child,
            stderr=child,
            env=environment,
            close_fds=True,
        )
        child.close()
        parent.sendall(payload)
        parent.shutdown(socket.SHUT_WR)
        response = b""
        while True:
            try:
                chunk = parent.recv(65536)
            except ConnectionResetError:
                break
            if not chunk:
                break
            response += chunk
        parent.close()
        return process.wait(timeout=5), response


class RecoveryHostSocketTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = BrokerFixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_broker_dispatches_only_fixed_commands_and_returns_status(self):
        cases = (
            (
                f"bundle arch-test-v1 {DIGEST}\n".encode(),
                f"controller arch-test-v1 {DIGEST}\n".encode(),
            ),
            (
                f"bundle-deferred arch-test-v1 {DIGEST}\n".encode(),
                f"controller serve-deferred arch-test-v1 {DIGEST}\n".encode(),
            ),
            (
                f"fallback-profile-restore {self.fixture.anchor} 750\n".encode(),
                b"controller restore-fallback "
                b"pci/usb1/1-1/1-1.2 750\n",
            ),
            (
                b"network-preflight-v1\n",
                b"network preflight "
                b"/var/lib/rog5-headless-network-root-v1/root\n",
            ),
            (
                f"network-preflight-v3 {DIGEST}\n".encode(),
                b"network preflight "
                b"/home/rog5-linux/exports/headless-ssh-network-root-v3/root "
                + DIGEST.encode()
                + b"\n",
            ),
            (
                f"network-serve-v1 {TOKEN} 720\n".encode(),
                b"network serve /var/lib/rog5-headless-network-root-v1/root "
                + TOKEN.encode()
                + b" 720\n",
            ),
            (
                f"network-serve-v3 {DIGEST} {TOKEN} 720\n".encode(),
                b"network serve "
                b"/home/rog5-linux/exports/headless-ssh-network-root-v3/root "
                + DIGEST.encode()
                + b" "
                + TOKEN.encode()
                + b" 720\n",
            ),
            (
                f"network-cancel {TOKEN}\n".encode(),
                b"network cancel " + TOKEN.encode() + b"\n",
            ),
        )
        for payload, expected in cases:
            with self.subTest(action=payload.split(b" ", 1)[0]):
                status, response = self.fixture.run(payload)
                self.assertEqual(status, 0, response)
                self.assertEqual(response, expected + STATUS + b"0\n")

    def test_broker_propagates_fixed_program_failure(self):
        status, response = self.fixture.run(
            f"bundle arch-test-v1 {DIGEST}\n".encode(),
            exit_status="17",
        )
        self.assertEqual(status, 0, response)
        self.assertTrue(response.endswith(STATUS + b"17\n"))

    def test_request_timeout_is_cleared_before_bounded_child(self):
        status, response = self.fixture.run(
            f"bundle arch-test-v1 {DIGEST}\n".encode(),
            delay="5.2",
        )
        self.assertEqual(status, 0, response)
        self.assertTrue(response.endswith(STATUS + b"0\n"))

    def test_child_cannot_collide_with_status_framing(self):
        status, response = self.fixture.run(
            f"bundle arch-test-v1 {DIGEST}\n".encode(),
            collide="1",
        )
        self.assertEqual(status, 1, response)
        self.assertIn(b"child output collides with framing", response)
        self.assertTrue(response.endswith(STATUS + b"1\n"))

    def test_partial_child_line_is_not_promoted_into_protocol_output(self):
        status, response = self.fixture.run(
            f"bundle arch-test-v1 {DIGEST}\n".encode(),
            partial="1",
        )
        self.assertEqual(status, 1, response)
        self.assertNotIn(b"partial", response)
        self.assertIn(b"not newline terminated", response)
        self.assertTrue(response.endswith(STATUS + b"1\n"))

    def test_broker_rejects_noncanonical_and_hostile_requests(self):
        for payload in (
            b"bundle ../escape " + DIGEST.encode() + b"\n",
            b"bundle test " + b"0" * 64 + b"\n",
            b"network-cancel " + TOKEN.encode() + b"\nextra\n",
            b"network-serve-v3 "
            + DIGEST.encode()
            + b" "
            + TOKEN.encode()
            + b" 901\n",
            b"bundle  test " + DIGEST.encode() + b"\n",
            b"fallback-profile-restore relative-anchor 750\n",
            b"fallback-profile-restore /tmp/../escape 750\n",
            f"fallback-profile-restore {self.fixture.anchor} 0\n".encode(),
            f"fallback-profile-restore {self.fixture.anchor} 901\n".encode(),
            b"shell /bin/sh\n",
        ):
            with self.subTest(payload=payload[:40]):
                if self.fixture.calls.exists():
                    self.fixture.calls.unlink()
                _status, response = self.fixture.run(payload)
                self.assertIn(b"FAIL ", response)
                self.assertTrue(response.endswith(STATUS + b"1\n"))
                self.assertFalse(self.fixture.calls.exists())

    def test_broker_rejects_changed_fixed_executable(self):
        self.fixture.controller.chmod(0o755)
        with self.fixture.controller.open("a", encoding="utf-8") as output:
            output.write("# changed\n")
        self.fixture.controller.chmod(0o555)
        _status, response = self.fixture.run(
            f"bundle arch-test-v1 {DIGEST}\n".encode()
        )
        self.assertIn(b"fixed host-control executable changed", response)
        self.assertFalse(self.fixture.calls.exists())

    def test_unauthorized_peer_gets_no_request_or_configuration_detail(self):
        payload = self.fixture.config.read_text(encoding="ascii")
        payload = payload.replace(
            f"operator_uid={os.geteuid()}",
            f"operator_uid={os.geteuid() + 1}",
        )
        self.fixture.config.chmod(0o644)
        self.fixture.config.write_text(payload, encoding="ascii")
        self.fixture.config.chmod(0o444)
        self.fixture.controller.chmod(0o755)
        with self.fixture.controller.open("a", encoding="utf-8") as output:
            output.write("# changed but not hashed for wrong peer\n")
        self.fixture.controller.chmod(0o555)
        _status, response = self.fixture.run(
            f"bundle arch-test-v1 {DIGEST}\n".encode()
        )
        self.assertEqual(response, b"")
        self.assertFalse(self.fixture.calls.exists())

    def test_client_streams_output_and_propagates_status(self):
        socket_path = self.fixture.root / "host.sock"
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(socket_path))
        socket_path.chmod(0o600)
        server.listen(1)
        observed: list[bytes] = []

        def serve() -> None:
            connection, _address = server.accept()
            payload = b""
            while True:
                chunk = connection.recv(1024)
                if not chunk:
                    break
                payload += chunk
            observed.append(payload)
            connection.sendall(b"READY fixed test server\n")
            connection.sendall(STATUS + b"23\n")
            connection.close()
            server.close()

        thread = threading.Thread(target=serve)
        thread.start()
        environment = os.environ.copy()
        environment.update(
            {
                "ROG5_HOST_CONTROL_OFFLINE_TEST": "1",
                "ROG5_HOST_CONTROL_SOCKET": str(socket_path),
            }
        )
        result = subprocess.run(
            [
                str(CLIENT),
                "fallback-profile-restore",
                str(self.fixture.anchor),
                "750",
            ],
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
        thread.join(timeout=5)
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertEqual(result.stdout, "READY fixed test server\n")
        self.assertEqual(
            observed,
            [
                b"fallback-profile-restore "
                + str(self.fixture.anchor).encode()
                + b" 750\n"
            ],
        )

    def test_privileged_restore_requires_exact_private_fresh_anchor(self):
        mutations = (
            ("stale", lambda: self.fixture.write_anchor(
                created=int(time.time()) - 3601
            )),
            ("wrong-boot", lambda: self.fixture.write_anchor(
                boot_id="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
            )),
            ("reordered", lambda: self.fixture.write_anchor(reorder=True)),
            ("loose-mode", lambda: self.fixture.anchor.chmod(0o644)),
        )
        for name, mutate in mutations:
            with self.subTest(name=name):
                self.fixture.write_anchor()
                mutate()
                if self.fixture.calls.exists():
                    self.fixture.calls.unlink()
                _status, response = self.fixture.run(
                    f"fallback-profile-restore "
                    f"{self.fixture.anchor} 750\n".encode()
                )
                self.assertIn(b"FAIL ", response)
                self.assertTrue(response.endswith(STATUS + b"1\n"))
                self.assertFalse(self.fixture.calls.exists())

    def test_installed_surface_has_no_policykit_hot_path(self):
        installer = INSTALLER.read_text(encoding="utf-8")
        broker = BROKER.read_text(encoding="utf-8")
        bundle = BUNDLE_LAUNCHER.read_text(encoding="utf-8")
        network = NETWORK_LAUNCHER.read_text(encoding="utf-8")
        socket_unit = SOCKET_UNIT.read_text(encoding="utf-8")
        service_unit = SERVICE_UNIT.read_text(encoding="utf-8")
        for source in (bundle, network):
            self.assertNotIn("exec pkexec", source)
            self.assertIn("rog5-recovery-host-client.py", source)
        for contract in (
            "SocketMode=0600",
            "Accept=yes",
            "MaxConnections=2",
            "RemoveOnStop=yes",
            "@ROG5_OPERATOR_USER@",
            "@ROG5_OPERATOR_GROUP@",
        ):
            self.assertIn(contract, socket_unit)
        for contract in (
            "User=root",
            "Group=root",
            "StandardInput=socket",
            "StandardOutput=socket",
            "StandardError=socket",
            "RuntimeMaxSec=1000",
        ):
            self.assertIn(contract, service_unit)
        for contract in (
            "configuration_destination=",
            "operator_uid=$PKEXEC_UID",
            "systemctl enable --now rog5-recovery-host.socket",
            "rog5-recovery-host-broker.py",
            "rog5-recovery-host-client.py",
            "SocketMode=0600",
        ):
            self.assertIn(contract, installer + socket_unit)
        for contract in (
            'Path("/usr/libexec")',
            "network.parent",
            "signal.pthread_sigmask",
            "child.poll() is not None",
            "child output collides with framing",
            "channel.settimeout(None)",
            "SO_PEERCRED",
        ):
            self.assertIn(contract, broker)
        for forbidden in ("/bin/sh", "command_line", "polkit.addRule"):
            self.assertNotIn(forbidden, socket_unit + service_unit)


if __name__ == "__main__":
    unittest.main(verbosity=2)
