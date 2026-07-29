#!/usr/bin/env python3
"""Offline lifecycle tests for the minimal-headless one-shot controller."""

from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import tempfile
import textwrap
import unittest


REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "scripts/host/run-minimal-headless-live-cycle.py"
NETWORK_LAUNCHER = (
    REPO / "scripts/host/run-headless-network-root-server.sh"
)
NETWORK_SERVER = REPO / "scripts/host/serve-network-root.sh"
INSTALLER = REPO / "scripts/host/install-recovery-host-controller.sh"
MANIFEST = "a" * 64
SESSION = "1" * 32
PREPARE = "2" * 32
REQUEST = "3" * 32
TARGET_BOOT_ID = "11111111-2222-4333-8444-555555555555"
FALLBACK_BOOT_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
GUARDS = (
    "ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE",
    "ALLOW_TEMPORARY_BOOT",
    "ALLOW_HEADLESS_LIVE_GATE",
    "ALLOW_STABLE_RECOVERY_CONTROL",
    "ALLOW_ATTENDED_KEXEC",
    "ALLOW_NETWORK_ROOT_NFS_HANDOFF",
    "ALLOW_HEADLESS_NETWORK_ROOT_SERVER",
    "ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP",
    "ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE",
    "ALLOW_PHONE_CREDENTIAL_USE",
)


class Fixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-live-cycle-"
        )
        self.root = Path(self.temporary.name)
        self.state = self.root / "state"
        self.state.mkdir()
        (self.state / "nfs-threads").write_text("0\n", encoding="ascii")
        (self.state / "ip-nonlocal-bind").write_text(
            "0\n",
            encoding="ascii",
        )
        self.sys_class_net = self.state / "sys-class-net"
        (self.sys_class_net / "usbmock0").mkdir(parents=True)
        self.xdg_state = self.root / "xdg-state"
        self.xdg_state.mkdir(mode=0o700)
        self.evidence = self.root / "evidence"
        self.evidence.mkdir(mode=0o700)
        self.evidence.chmod(0o700)
        self.ssh_key = self.root / "ssh-key"
        self.known_hosts = self.root / "fallback-known-hosts"
        for path in (self.ssh_key, self.known_hosts):
            path.write_bytes(b"offline-test\n")
            path.chmod(0o600)
        self.calls = self.root / "calls"
        self._write_mocks()

    def close(self) -> None:
        self.temporary.cleanup()

    def executable(self, name: str, payload: str) -> None:
        path = self.root / name
        path.write_text(
            textwrap.dedent(payload).lstrip(),
            encoding="utf-8",
        )
        path.chmod(0o755)

    def _write_mocks(self) -> None:
        self.executable(
            "git",
            """\
            #!/bin/sh
            set -eu
            printf 'git:%s\n' "$*" >>"$MOCK_CALLS"
            case $* in
              *"status --porcelain --untracked-files=all"*) ;;
              *"branch --show-current"*)
                echo agent/linux-recovery-host
                ;;
              *"rev-parse --abbrev-ref --symbolic-full-name @{u}"*)
                echo origin/agent/linux-recovery-host
                ;;
              *"rev-parse HEAD"*|*"rev-parse origin/agent/linux-recovery-host"*)
                echo synchronized-checkpoint
                ;;
              *) exit 1 ;;
            esac
            """,
        )
        self.executable(
            "ss",
            """\
            #!/bin/sh
            printf 'ss:%s\n' "$*" >>"$MOCK_CALLS"
            """,
        )
        self.executable(
            "udevadm",
            """\
            #!/bin/sh
            printf 'udevadm:%s\n' "$*" >>"$MOCK_CALLS"
            printf '%s\n' \
              'ID_VENDOR_ID=1d6b' \
              'ID_MODEL_ID=0104' \
              'ID_MODEL=ROG5_recovery' \
              'ID_NET_DRIVER=cdc_ncm'
            """,
        )
        self.executable(
            "ip",
            """\
            #!/bin/sh
            printf 'ip:%s\n' "$*" >>"$MOCK_CALLS"
            case " $* " in
              *" -4 -o address show dev usbmock0 "*)
                if { [ "${MOCK_ADDRESS_RESIDUE_AFTER_BUNDLE:-0}" = 1 ] &&
                     [ -e "$MOCK_ROOT/bundle-consumed" ]; } ||
                   { [ "${MOCK_ADDRESS_RESIDUE_AFTER_NFS:-0}" = 1 ] &&
                     [ -e "$MOCK_ROOT/target-departed" ]; }; then
                  echo '9: usbmock0 inet 169.254.77.1/30 scope global usbmock0'
                fi
                ;;
              *" -4 -o address show "*)
                if [ "${MOCK_ADDRESS_RESIDUE_AFTER_NFS:-0}" = 1 ] &&
                   [ -e "$MOCK_ROOT/target-departed" ]; then
                  echo '9: usbmock0 inet 169.254.77.1/30 scope global usbmock0'
                elif [ "${MOCK_ADDRESS_RESIDUE_AFTER_BUNDLE:-0}" = 1 ] &&
                     [ -e "$MOCK_ROOT/bundle-consumed" ]; then
                  echo '9: usbmock0 inet 169.254.77.1/30 scope global usbmock0'
                fi
                ;;
            esac
            """,
        )
        self.executable(
            "nmcli",
            """\
            #!/bin/sh
            printf 'nmcli:%s\n' "$*" >>"$MOCK_CALLS"
            if [ "${MOCK_NM_RESIDUE_AFTER_BUNDLE:-0}" = 1 ] &&
               [ -e "$MOCK_ROOT/bundle-consumed" ]; then
              echo no
            else
              echo yes
            fi
            """,
        )
        self.executable(
            "firewall-cmd",
            """\
            #!/bin/sh
            printf 'firewall:%s\n' "$*" >>"$MOCK_CALLS"
            case " $* " in
              *" --zone=drop --list-all "*)
                printf '%s\n' 'drop' '  target: DROP'
                ;;
              *" --get-zones "*) echo 'drop public trusted' ;;
              *" --get-zone-of-interface=usbmock0 "*) echo public ;;
              *" --query-masquerade "*) exit 1 ;;
              *" --query-forward "*) exit 0 ;;
              *" --list-rich-rules "*)
                if [ "${MOCK_RESIDUAL_AFTER_BUNDLE:-0}" = 1 ] &&
                   [ -e "$MOCK_ROOT/bundle-consumed" ] &&
                   [ "${1:-}" = "--zone=public" ]; then
                  echo 'rule family="ipv4" priority="-300" destination address="169.254.77.1/32" port port="8080" protocol="tcp" drop'
                elif [ "${MOCK_RESIDUAL_AFTER_NFS:-0}" = 1 ] &&
                     [ -e "$MOCK_ROOT/target-departed" ] &&
                     [ "${1:-}" = "--zone=public" ]; then
                  echo 'rule family="ipv4" priority="-300" destination address="169.254.77.1/32" port port="2049" protocol="tcp" drop'
                fi
                ;;
            esac
            """,
        )
        self.executable(
            "exportfs",
            """\
            #!/bin/sh
            printf 'exportfs:%s\n' "$*" >>"$MOCK_CALLS"
            """,
        )
        self.executable(
            "run-stable-recovery-live-gate.sh",
            """\
            #!/bin/sh
            set -eu
            [ -z "${UNRELATED_CREDENTIAL+x}" ]
            [ -z "${SSH_KEY+x}" ]
            [ -z "${FALLBACK_KNOWN_HOSTS+x}" ]
            [ -z "${EVIDENCE_DIR+x}" ]
            if [ "$1" = boot ]; then
              [ "${ALLOW_TEMPORARY_BOOT:-}" = 1 ]
              [ "${ALLOW_HEADLESS_LIVE_GATE:-}" = 1 ]
              [ -z "${ALLOW_STABLE_RECOVERY_CONTROL+x}" ]
            fi
            printf 'live:%s\n' "$1" >>"$MOCK_CALLS"
            echo "PASS live $1"
            """,
        )
        self.executable(
            "run-recovery-bundle-server.sh",
            """\
            #!/bin/sh
            set -eu
            if [ "$1" = preflight ]; then
              printf 'bundle:preflight\n' >>"$MOCK_CALLS"
              echo 'PASS bundle preflight'
              exit 0
            fi
            printf 'bundle:start\n' >>"$MOCK_CALLS"
            echo 'PASS recovery bundle server ready on 169.254.77.1:8080 via usb0'
            while [ ! -e "$MOCK_ROOT/bundle-consumed" ]; do
              sleep 0.01
            done
            printf 'bundle:transfer\n' >>"$MOCK_CALLS"
            echo 'PASS one recovery bundle transfer completed'
            echo 'INFO recovery bundle host network state removed'
            printf 'bundle:clean\n' >>"$MOCK_CALLS"
            """,
        )
        self.executable(
            "run-headless-network-root-server.sh",
            """\
            #!/bin/sh
            set -eu
            if [ "$1" = preflight ]; then
              printf 'nfs:preflight\n' >>"$MOCK_CALLS"
              echo 'PASS NFS preflight'
              exit 0
            fi
            [ "$1" = serve ]
            [ "${ALLOW_HEADLESS_NETWORK_ROOT_SERVER:-}" = 1 ]
            [ -z "${ALLOW_TEMPORARY_BOOT+x}" ]
            printf 'nfs:start\n' >>"$MOCK_CALLS"
            : >"$MOCK_ROOT/nfs-started"
            echo 'PASS restricted NFSv4.2 export ready; waiting for exact USB gadget'
            trap 'printf "nfs:terminated\\n" >>"$MOCK_CALLS"; exit 130' TERM INT
            while [ ! -e "$MOCK_ROOT/target-departed" ]; do
              sleep 0.01
            done
            echo 'PASS network-root gadget departed; ending attended export'
            echo 'INFO network-root NFS and runtime firewall state removed'
            printf 'nfs:clean\n' >>"$MOCK_CALLS"
            """,
        )
        self.executable(
            "stable-recovery-control.py",
            f"""\
            #!/bin/sh
            set -eu
            case $1 in
              prepare-commit)
                [ "${{ALLOW_STABLE_RECOVERY_CONTROL:-}}" = 1 ]
                [ "${{ALLOW_ATTENDED_KEXEC:-}}" = 1 ]
                [ "${{ALLOW_NETWORK_ROOT_NFS_HANDOFF:-}}" = 1 ]
                [ -z "${{ALLOW_TEMPORARY_BOOT+x}}" ]
                printf 'control:prepare-commit\n' >>"$MOCK_CALLS"
                : >"$MOCK_ROOT/bundle-consumed"
                while [ ! -e "$MOCK_ROOT/nfs-started" ]; do
                  sleep 0.01
                done
                if [ "${{MOCK_CONTROL_FAIL:-0}}" = 1 ]; then
                  echo 'FAIL injected control failure'
                  exit 1
                fi
                intent_root=$XDG_STATE_HOME/rog5-recovery-intents
                install -d -m 0700 "$intent_root"
                umask 077
                printf '%s\n' \
                  '{{"session":"{SESSION}","request":"{REQUEST}","manifest_sha256":"{MANIFEST}","target":"headless-network-root-v1","state":"TRANSMITTED","outcome":"UNKNOWN"}}' \
                  >"$intent_root/{SESSION}.json"
                if [ "${{MOCK_CONTROL_UNKNOWN:-0}}" = 1 ]; then
                  echo 'FAIL transport lost; commit intent remains UNKNOWN session={SESSION} request={REQUEST}'
                  exit 1
                fi
                if [ "${{MOCK_CONTROL_SILENT_UNKNOWN:-0}}" = 1 ]; then
                  echo 'FAIL injected silent post-arm transport loss'
                  exit 1
                fi
                if [ "${{MOCK_CONTROL_HANG_AFTER_ARM:-0}}" = 1 ]; then
                  : >"$MOCK_ROOT/ledger-armed"
                  while :; do sleep 1; done
                fi
                printf '%s\n' \
                  '{{"session":"{SESSION}","request":"{PREPARE}","result":"PREPARED","state":"PREPARED","prepared_bundle":"headless-network-root-v1","manifest_sha256":"{MANIFEST}","watchdog":"ARMED"}}' \
                  '{{"session":"{SESSION}","request":"{REQUEST}","commit_request":"{REQUEST}","result":"CLAIMED","state":"CLAIMED","manifest_sha256":"{MANIFEST}","watchdog":"ARMED","execution_started":"NO"}}' \
                  '{{"session":"{SESSION}","request":"{REQUEST}","manifest_sha256":"{MANIFEST}","target":"headless-network-root-v1","state":"TRANSMITTED","outcome":"UNKNOWN"}}'
                echo 'PASS recovery accepted one commit; outcome remains UNKNOWN'
                ;;
              show)
                printf 'control:show\n' >>"$MOCK_CALLS"
                printf '%s\n' \
                  '{{"session":"{SESSION}","request":"{REQUEST}","manifest_sha256":"{MANIFEST}","target":"headless-network-root-v1","state":"TRANSMITTED","outcome":"UNKNOWN"}}'
                ;;
              resolve)
                printf 'control:resolve:%s\n' "$4" >>"$MOCK_CALLS"
                printf '%s\n' \
                  '{{"session":"{SESSION}","request":"{REQUEST}","manifest_sha256":"{MANIFEST}","target":"headless-network-root-v1","state":"RESOLVED","outcome":"'"$4"'"}}'
                ;;
              *) exit 1 ;;
            esac
            """,
        )
        self.executable(
            "pin-minimal-headless-host-key.py",
            """\
            #!/bin/sh
            set -eu
            case $1 in
              capture-recovery)
                [ "${ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP:-}" = 1 ]
                [ -z "${ALLOW_TEMPORARY_BOOT+x}" ]
                printf 'host-key:capture\n' >>"$MOCK_CALLS"
                umask 077
                printf 'format=offline-anchor\n' >"$2"
                echo 'PASS captured anchor'
                ;;
              pin-target)
                [ "${ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP:-}" = 1 ]
                [ -z "${ALLOW_TEMPORARY_BOOT+x}" ]
                printf 'host-key:pin\n' >>"$MOCK_CALLS"
                umask 077
                printf 'rog5-minimal-headless-v1 ssh-ed25519 offline\n' >"$3"
                echo 'PASS pinned key'
                ;;
              *) exit 1 ;;
            esac
            """,
        )
        self.executable(
            "run-minimal-headless-runtime-acceptance.sh",
            f"""\
            #!/bin/sh
            set -eu
            [ "${{ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE:-}}" = 1 ]
            [ -z "${{ALLOW_TEMPORARY_BOOT+x}}" ]
            [ -z "${{ALLOW_PHONE_CREDENTIAL_USE+x}}" ]
            printf 'runtime:start\n' >>"$MOCK_CALLS"
            if [ "${{MOCK_RUNTIME_FAIL:-0}}" = 1 ]; then
              echo 'FAIL injected runtime rejection'
              exit 1
            fi
            umask 077
            printf '%s\n' \
              'format=rog5-minimal-headless-runtime-v1' \
              'boot_id={TARGET_BOOT_ID}' \
              'result=PASS' \
              >"$EVIDENCE_DIR/minimal-headless-runtime.record"
            : >"$MOCK_ROOT/target-departed"
            echo 'PASS runtime'
            """,
        )
        self.executable(
            "ssh",
            f"""\
            #!/bin/sh
            printf 'ssh:fallback\n' >>"$MOCK_CALLS"
            if [ "${{MOCK_FALLBACK_FAIL:-0}}" = 1 ]; then
              exit 255
            fi
            echo {FALLBACK_BOOT_ID}
            """,
        )
        self.executable(
            "reboot-fallback-to-fastboot.sh",
            """\
            #!/bin/sh
            set -eu
            [ "$1" = preflight ]
            printf 'fallback:preflight\n' >>"$MOCK_CALLS"
            echo 'PASS exact persistent fallback ready for guarded bootloader reboot'
            """,
        )

    def environment(self, *, guards: bool = True, **updates: str) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "ROG5_LIVE_CYCLE_OFFLINE_TEST": "1",
                "ROG5_LIVE_CYCLE_TEST_ROOT": str(self.root),
                "MOCK_ROOT": str(self.root),
                "MOCK_CALLS": str(self.calls),
                "BUNDLE": "headless-network-root-v1",
                "MANIFEST_SHA256": MANIFEST,
                "SSH_KEY": str(self.ssh_key),
                "FALLBACK_KNOWN_HOSTS": str(self.known_hosts),
                "EVIDENCE_DIR": str(self.evidence),
                "XDG_STATE_HOME": str(self.xdg_state),
                "UNRELATED_CREDENTIAL": "must-not-reach-a-child",
            }
        )
        if guards:
            environment.update({name: "1" for name in GUARDS})
        environment.update(updates)
        return environment

    def run(
        self,
        action: str,
        *,
        guards: bool = True,
        **updates: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(RUNNER), action],
            env=self.environment(guards=guards, **updates),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=15,
        )

    def call_lines(self) -> list[str]:
        if not self.calls.exists():
            return []
        return self.calls.read_text(encoding="utf-8").splitlines()


class MinimalHeadlessLiveCycleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = Fixture()

    def tearDown(self) -> None:
        self.fixture.close()

    def test_guards_fail_before_any_dependency_or_credential_use(self):
        result = self.fixture.run(
            "run",
            guards=False,
            SSH_KEY="/absent/guard-must-win",
            FALLBACK_KNOWN_HOSTS="/absent/guard-must-win",
            EVIDENCE_DIR="/absent/guard-must-win",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires exact fresh guards", result.stderr)
        self.assertEqual(self.fixture.call_lines(), [])
        self.assertFalse(any(self.fixture.evidence.iterdir()))

    def test_preflight_is_read_only_and_stops_before_phone_or_credentials(self):
        result = self.fixture.run("preflight", guards=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no phone boot, credential use", result.stdout)
        calls = self.fixture.call_lines()
        self.assertIn("bundle:preflight", calls)
        self.assertIn("nfs:preflight", calls)
        self.assertIn("live:preflight", calls)
        self.assertNotIn("live:boot", calls)
        self.assertFalse(any(line.startswith("ssh:") for line in calls))
        self.assertFalse(any(line.startswith("host-key:") for line in calls))
        self.assertFalse(any(self.fixture.evidence.iterdir()))

    def test_success_orders_cleanup_before_nfs_and_resolves_after_fallback(self):
        result = self.fixture.run("run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS one minimal-headless lifecycle", result.stdout)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertLess(
            calls.index("bundle:clean"),
            calls.index("nfs:start"),
        )
        self.assertLess(
            calls.index("runtime:start"),
            calls.index("nfs:clean"),
        )
        self.assertLess(
            calls.index("fallback:preflight"),
            calls.index("control:resolve:TARGET_ACCEPTED"),
        )
        self.assertTrue(
            (self.fixture.evidence / "target-known-hosts").is_file()
        )
        self.assertTrue(
            (self.fixture.evidence / "fallback-identity.record").is_file()
        )
        resolution = (
            self.fixture.evidence / "intent-resolution.log"
        ).read_text(encoding="utf-8")
        self.assertIn('"outcome":"TARGET_ACCEPTED"', resolution)

    def test_runtime_rejection_returns_to_fallback_without_commit_retry(self):
        result = self.fixture.run("run", MOCK_RUNTIME_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resolved as FALLBACK_RETURNED", result.stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(
            calls.count("control:resolve:FALLBACK_RETURNED"),
            1,
        )
        self.assertNotIn("control:resolve:TARGET_ACCEPTED", calls)

    def test_control_failure_without_intent_is_never_resolved_or_retried(self):
        result = self.fixture.run("run", MOCK_CONTROL_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertFalse(
            any(line.startswith("control:resolve:") for line in calls)
        )
        self.assertFalse(any(line.startswith("ssh:") for line in calls))

    def test_transport_loss_uses_durable_ledger_without_commit_retry(self):
        result = self.fixture.run("run", MOCK_CONTROL_UNKNOWN="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resolved as FALLBACK_RETURNED", result.stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(calls.count("control:show"), 0)
        self.assertEqual(
            calls.count("control:resolve:FALLBACK_RETURNED"),
            1,
        )

    def test_silent_post_arm_failure_uses_new_durable_ledger(self):
        result = self.fixture.run(
            "run",
            MOCK_CONTROL_SILENT_UNKNOWN="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resolved as FALLBACK_RETURNED", result.stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(calls.count("control:show"), 0)
        self.assertEqual(
            calls.count("control:resolve:FALLBACK_RETURNED"),
            1,
        )

    def test_parent_interrupt_after_ledger_arm_resolves_without_retry(self):
        process = subprocess.Popen(
            [str(RUNNER), "run"],
            env=self.fixture.environment(
                MOCK_CONTROL_HANG_AFTER_ARM="1"
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        marker = self.fixture.root / "ledger-armed"
        for _attempt in range(300):
            if marker.exists():
                break
            if process.poll() is not None:
                self.fail("lifecycle exited before its ledger-arm marker")
            __import__("time").sleep(0.01)
        else:
            process.kill()
            self.fail("control child never armed its durable ledger")
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=15)
        self.assertNotEqual(process.returncode, 0, stdout + stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(
            calls.count("control:resolve:FALLBACK_RETURNED"),
            1,
        )

    def test_bundle_cleanup_residue_blocks_nfs_and_commit(self):
        result = self.fixture.run(
            "run",
            MOCK_RESIDUAL_AFTER_BUNDLE="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("retains a lifecycle drop rule", result.stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertNotIn("nfs:start", calls)
        self.assertFalse(
            any(line.startswith("control:resolve:") for line in calls)
        )

    def test_bundle_address_or_networkmanager_residue_blocks_nfs(self):
        for variable in (
            "MOCK_ADDRESS_RESIDUE_AFTER_BUNDLE",
            "MOCK_NM_RESIDUE_AFTER_BUNDLE",
        ):
            with self.subTest(variable=variable):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run("run", **{variable: "1"})
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("nfs:start", self.fixture.call_lines())
                self.assertFalse(
                    any(
                        line.startswith("control:resolve:")
                        for line in self.fixture.call_lines()
                    )
                )

    def test_final_address_residue_prevents_intent_resolution(self):
        result = self.fixture.run(
            "run",
            MOCK_ADDRESS_RESIDUE_AFTER_NFS="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("intent remains UNKNOWN", result.stderr)
        self.assertFalse(
            any(
                line.startswith("control:resolve:")
                for line in self.fixture.call_lines()
            )
        )

    def test_final_cleanup_residue_prevents_intent_resolution(self):
        result = self.fixture.run(
            "run",
            MOCK_RESIDUAL_AFTER_NFS="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("intent remains UNKNOWN", result.stderr)
        self.assertFalse(
            any(
                line.startswith("control:resolve:")
                for line in self.fixture.call_lines()
            )
        )

    def test_failed_fallback_proof_leaves_intent_unknown(self):
        result = self.fixture.run(
            "run",
            MOCK_RUNTIME_FAIL="1",
            MOCK_FALLBACK_FAIL="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("intent remains UNKNOWN", result.stderr)
        self.assertFalse(
            any(
                line.startswith("control:resolve:")
                for line in self.fixture.call_lines()
            )
        )

    def test_installed_nfs_surface_is_fixed_and_exact(self):
        runner = RUNNER.read_text(encoding="utf-8")
        launcher = NETWORK_LAUNCHER.read_text(encoding="utf-8")
        server = NETWORK_SERVER.read_text(encoding="utf-8")
        installer = INSTALLER.read_text(encoding="utf-8")
        for token in GUARDS:
            self.assertIn(token, runner)
        for token in (
            "StrictHostKeyChecking=yes",
            "ConnectionAttempts=1",
            "HostKeyAlias={FALLBACK_ALIAS}",
            "PASS one recovery bundle transfer completed",
            "INFO recovery bundle host network state removed",
            "TARGET_ACCEPTED",
            "FALLBACK_RETURNED",
            "outcome remains UNKNOWN",
        ):
            self.assertIn(token, runner)
        self.assertEqual(runner.count('"prepare-commit",'), 1)
        for token in (
            "installed_root=/usr/libexec/rog5-recovery-host",
            "installed_server=$installed_root/serve-network-root.sh",
            "installed_verifier=$installed_root/headless-network-root.py",
            "installed_root_tool=$installed_root/persistent-root-tool.py",
            'exec pkexec "$installed_server"',
            '"$installed_server" preflight',
            '"$installed_server" serve',
        ):
            self.assertIn(token, launcher)
        self.assertIn(
            "installed server accepts only the minimal headless root",
            server,
        )
        self.assertIn("installed_action == preflight", server)
        self.assertIn("PKEXEC_UID", server)
        for token in (
            "network_server_source",
            "headless_verifier_source",
            "persistent_root_tool_source",
            "install -o root -g root -m 0555",
        ):
            self.assertIn(token, installer)
        for forbidden in (
            "StrictHostKeyChecking=accept-new",
            "StrictHostKeyChecking=no",
            "UserKnownHostsFile=/dev/null",
            "fastboot flash",
            "fastboot erase",
            "dd if=",
            "sudo ",
            "shell=True",
        ):
            self.assertNotIn(forbidden, runner)
            self.assertNotIn(forbidden, launcher)


if __name__ == "__main__":
    unittest.main(verbosity=2)
