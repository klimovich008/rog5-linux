#!/usr/bin/env python3
"""Offline lifecycle tests for the minimal-headless one-shot controller."""

from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import tempfile
import textwrap
import time
import unittest


REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "scripts/host/run-minimal-headless-live-cycle.py"
NETWORK_LAUNCHER = (
    REPO / "scripts/host/run-headless-network-root-server.sh"
)
NETWORK_SERVER = REPO / "scripts/host/serve-network-root.sh"
INSTALLER = REPO / "scripts/host/install-recovery-host-controller.sh"
RUNTIME_ACCEPTANCE = (
    REPO / "scripts/host/run-minimal-headless-runtime-acceptance.sh"
)
MANIFEST = "a" * 64
CONSUMED_MANIFEST = (
    "457273993a9ce3cb0a9c735ef29e96101c1303720cafefc774aed12972a6926e"
)
PACKAGE_SHA256 = "2" * 64
CANDIDATE_SHA256 = "3" * 64
CANDIDATE = "headless-ssh-network-root-v3"
BUNDLE = "headless-ssh-network-root-v3-r2"
RECOVERY_PROFILE = "headless-ssh-deployment-v3"
SESSION = "1" * 32
PREPARE = "2" * 32
REQUEST = "3" * 32
TARGET_BOOT_ID = "11111111-2222-4333-8444-555555555555"
FALLBACK_BOOT_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
GUARDS = (
    "ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE",
    "ALLOW_HEADLESS_SSH_KEY_ADMISSION",
    "ALLOW_TEMPORARY_BOOT",
    "ALLOW_HEADLESS_LIVE_GATE",
    "ALLOW_STABLE_RECOVERY_CONTROL",
    "ALLOW_ATTENDED_KEXEC",
    "ALLOW_NETWORK_ROOT_NFS_HANDOFF",
    "ALLOW_HEADLESS_NETWORK_ROOT_SERVER",
    "ALLOW_MINIMAL_HEADLESS_HOST_KEY_BOOTSTRAP",
    "ALLOW_MINIMAL_HEADLESS_RUNTIME_ACCEPTANCE",
    "ALLOW_PHONE_CREDENTIAL_USE",
    "ALLOW_FALLBACK_SSH_CONTROL",
    "ALLOW_FALLBACK_SSH_ATIME_EFFECTS",
)


class Fixture:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="rog5-live-cycle-"
        )
        self.root = Path(self.temporary.name)
        self.state = self.root / "state"
        self.state.mkdir()
        self.nfs_exports = self.state / "nfs-exports"
        self.nfs_exports.write_bytes(b"")
        self.nfs_exports.chmod(0o644)
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
        self.package = self.root / "headless-root.package"
        self.candidate = self.root / "candidate.json"
        for path in (self.package, self.candidate):
            path.write_bytes(b"offline-admission-fixture\n")
            path.chmod(0o400)
        self.bundle_root = self.root / "bundle-root"
        self.bundle_root.mkdir(mode=0o700)
        self.bundle = self.bundle_root / BUNDLE
        self.bundle.mkdir(mode=0o700)
        self.bundle_manifest = self.bundle / "manifest"
        self.bundle_manifest.write_bytes(b"offline-runtime-manifest\n")
        self.bundle_manifest.chmod(0o400)
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
            if [ -e "$MOCK_ROOT/fallback-proved" ]; then
              if [ "${MOCK_UDEV_HANG_AFTER_FALLBACK:-0}" = 1 ]; then
                sleep 5
              fi
              if [ "${MOCK_UDEV_MISSING_AFTER_FALLBACK:-0}" = 1 ]; then
                exit 0
              fi
              if [ "${MOCK_UDEV_GAP_AFTER_FALLBACK:-0}" = 1 ] &&
                 [ ! -e "$MOCK_ROOT/udev-gap-consumed" ]; then
                : >"$MOCK_ROOT/udev-gap-consumed"
                exit 0
              fi
              if [ "${MOCK_UDEV_FLAP_AFTER_FALLBACK:-0}" = 1 ]; then
                if [ -e "$MOCK_ROOT/udev-clean-consumed" ]; then
                  exit 0
                fi
                : >"$MOCK_ROOT/udev-clean-consumed"
              fi
            fi
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
                echo '9: usbmock0 inet 169.254.77.1/30 scope global usbmock0'
                if { [ "${MOCK_ADDRESS_RESIDUE_AFTER_BUNDLE:-0}" = 1 ] &&
                     [ -e "$MOCK_ROOT/bundle-consumed" ]; } ||
                   { [ "${MOCK_ADDRESS_RESIDUE_AFTER_NFS:-0}" = 1 ] &&
                     [ -e "$MOCK_ROOT/target-departed" ]; }; then
                  echo '9: usbmock0 inet 169.254.77.9/30 scope global usbmock0'
                fi
                ;;
              *" -4 -o address show "*)
                echo '9: usbmock0 inet 169.254.77.1/30 scope global usbmock0'
                if [ "${MOCK_ADDRESS_GAP_AFTER_FALLBACK:-0}" = 1 ] &&
                   [ -e "$MOCK_ROOT/fallback-proved" ] &&
                   [ ! -e "$MOCK_ROOT/address-gap-consumed" ]; then
                  : >"$MOCK_ROOT/address-gap-consumed"
                  echo '10: pending0 inet 169.254.77.1/30 scope global pending0'
                fi
                if [ "${MOCK_ADDRESS_RESIDUE_AFTER_NFS:-0}" = 1 ] &&
                   [ -e "$MOCK_ROOT/target-departed" ]; then
                  echo '9: usbmock0 inet 169.254.77.9/30 scope global usbmock0'
                elif [ "${MOCK_ADDRESS_RESIDUE_AFTER_BUNDLE:-0}" = 1 ] &&
                     [ -e "$MOCK_ROOT/bundle-consumed" ]; then
                  echo '9: usbmock0 inet 169.254.77.9/30 scope global usbmock0'
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
                elif [ "${MOCK_TRANSIENT_FIREWALL_AFTER_FALLBACK:-0}" = 1 ] &&
                     [ -e "$MOCK_ROOT/fallback-proved" ] &&
                     [ ! -e "$MOCK_ROOT/firewall-gap-consumed" ] &&
                     [ "${1:-}" = "--zone=public" ]; then
                  : >"$MOCK_ROOT/firewall-gap-consumed"
                  echo 'rule family="ipv4" priority="-300" destination address="169.254.77.1/32" port port="2049" protocol="tcp" drop'
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
            "verify-headless-ssh-v2-key-admission.py",
            f"""\
            #!/bin/sh
            set -eu
            [ -z "${{SSH_KEY+x}}" ]
            [ -z "${{UNRELATED_CREDENTIAL+x}}" ]
            [ "$1" = --private-key ]
            [ "$2" = "{self.ssh_key}" ]
            [ "$3" = --package ]
            [ "$4" = "{self.package}" ]
            [ "$5" = --candidate ]
            [ "$6" = "{self.candidate}" ]
            [ "$7" = --manifest ]
            [ "$8" = "{self.bundle_manifest}" ]
            [ "$9" = --manifest-sha256 ]
            [ "${{10}}" = "{MANIFEST}" ]
            printf 'key-admission:verify\\n' >>"{self.calls}"
            printf '%s\\n' \
              'format=rog5-headless-ssh-v2-key-admission-v1' \
              'candidate={CANDIDATE}' \
              'bundle={BUNDLE}' \
              'profile=network-root-v1' \
              'build_profile=headless-ssh-v2' \
              'target_id=headless-ssh-network-root' \
              'authorized_key_fingerprint=SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' \
              'public_key_sha256={'1' * 64}' \
              'package_sha256={PACKAGE_SHA256}' \
              'candidate_sha256={CANDIDATE_SHA256}' \
              'manifest_sha256={MANIFEST}' \
              'root_tree_sha256={'4' * 64}' \
              'root_seal_sha256={'5' * 64}' \
              'root_tree_entries=37736' \
              'authority=none'
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
            f"""\
            #!/bin/sh
            set -eu
            if [ "$1" = preflight ]; then
              [ "$2" = "{RECOVERY_PROFILE}" ]
              [ "$3" = "{PACKAGE_SHA256}" ]
              [ "$#" = 3 ]
              printf 'nfs:preflight\n' >>"$MOCK_CALLS"
              echo 'PASS NFS preflight'
              exit 0
            fi
            if [ "$1" = cancel ]; then
              [ "$#" = 2 ]
              [ "${{ALLOW_HEADLESS_NETWORK_ROOT_CANCEL:-}}" = 1 ]
              if [ "${{MOCK_CANCEL_FAIL:-0}}" = 1 ]; then
                echo 'FAIL injected privileged cancellation failure'
                exit 1
              fi
              read -r server_pid server_token <"$MOCK_ROOT/nfs-state"
              [ "$server_token" = "$2" ]
              kill -TERM "$server_pid"
              printf 'nfs:cancel\n' >>"$MOCK_CALLS"
              exit 0
            fi
            [ "$1" = serve ]
            [ "$2" = "{RECOVERY_PROFILE}" ]
            [ "$3" = "{PACKAGE_SHA256}" ]
            [ "$#" = 4 ]
            [ "${{ALLOW_HEADLESS_NETWORK_ROOT_SERVER:-}}" = 1 ]
            [ -z "${{ALLOW_TEMPORARY_BOOT+x}}" ]
            printf 'nfs:start\n' >>"$MOCK_CALLS"
            : >"$MOCK_ROOT/nfs-started"
            printf '%s %s\n' "$$" "$4" >"$MOCK_ROOT/nfs-state"
            echo 'PASS restricted NFSv4.2 export ready; waiting for exact USB gadget'
            trap 'rm -f "$MOCK_ROOT/nfs-state"; printf "nfs:terminated\\n" >>"$MOCK_CALLS"; exit 130' TERM INT
            while [ ! -e "$MOCK_ROOT/target-departed" ]; do
              sleep 0.01
            done
            echo 'PASS network-root gadget departed; ending attended export'
            echo 'INFO network-root NFS and runtime firewall state removed'
            printf 'nfs:clean\n' >>"$MOCK_CALLS"
            rm -f "$MOCK_ROOT/nfs-state"
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
                [ "${{ROG5_NFS_PROFILE:-}}" = "{RECOVERY_PROFILE}" ]
                [ "${{ROG5_NFS_PACKAGE_SHA256:-}}" = "{PACKAGE_SHA256}" ]
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
                  '{{"session":"{SESSION}","request":"{REQUEST}","manifest_sha256":"{MANIFEST}","target":"{BUNDLE}","state":"TRANSMITTED","outcome":"UNKNOWN"}}' \
                  >"$intent_root/{SESSION}.json"
                if [ "${{MOCK_CONTROL_UNKNOWN:-0}}" = 1 ]; then
                  echo 'FAIL transport lost; commit intent remains UNKNOWN session={SESSION} request={REQUEST}'
                  exit 1
                fi
                if [ "${{MOCK_CONTROL_SILENT_UNKNOWN:-0}}" = 1 ]; then
                  echo 'FAIL injected silent post-arm transport loss'
                  exit 1
                fi
                if [ "${{MOCK_CONTROL_MALFORMED_SUCCESS:-0}}" = 1 ]; then
                  echo 'malformed successful control output'
                  exit 0
                fi
                if [ "${{MOCK_CONTROL_HANG_AFTER_ARM:-0}}" = 1 ]; then
                  : >"$MOCK_ROOT/ledger-armed"
                  while :; do sleep 1; done
                fi
                printf '%s\n' \
                  '{{"session":"{SESSION}","request":"{PREPARE}","result":"PREPARED","state":"PREPARED","prepared_bundle":"{BUNDLE}","manifest_sha256":"{MANIFEST}","watchdog":"ARMED"}}' \
                  '{{"session":"{SESSION}","request":"{REQUEST}","commit_request":"{REQUEST}","result":"CLAIMED","state":"CLAIMED","manifest_sha256":"{MANIFEST}","watchdog":"ARMED","execution_started":"NO"}}' \
                  '{{"session":"{SESSION}","request":"{REQUEST}","manifest_sha256":"{MANIFEST}","target":"{BUNDLE}","state":"TRANSMITTED","outcome":"UNKNOWN"}}'
                echo 'PASS recovery accepted one commit; outcome remains UNKNOWN'
                ;;
              show)
                printf 'control:show\n' >>"$MOCK_CALLS"
                printf '%s\n' \
                  '{{"session":"{SESSION}","request":"{REQUEST}","manifest_sha256":"{MANIFEST}","target":"{BUNDLE}","state":"TRANSMITTED","outcome":"UNKNOWN"}}'
                ;;
              resolve)
                printf 'control:resolve:%s\n' "$4" >>"$MOCK_CALLS"
                printf '%s\n' \
                  '{{"session":"{SESSION}","request":"{REQUEST}","manifest_sha256":"{MANIFEST}","target":"{BUNDLE}","state":"RESOLVED","outcome":"'"$4"'"}}'
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
                printf '%s\n' \
                  'format=rog5-minimal-headless-usb-anchor-v1' \
                  'host_boot_id=11111111-2222-4333-8444-555555555555' \
                  'created_unix=2000000000' \
                  'usb_location=pci/usb1/1-1/1-1.2' \
                  'recovery_vendor=1d6b' \
                  'recovery_product_id=0104' \
                  'recovery_product=ROG5 recovery' \
                  >"$2"
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
            [ "$1" = "{RECOVERY_PROFILE}" ]
            [ "$2" = "{self.candidate}" ]
            [ "$3" = "{CANDIDATE_SHA256}" ]
            [ "$#" = 3 ]
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
            "fallback-acm-control.py",
            f"""\
            #!/bin/sh
            set -eu
            if [ "$1" = ssh-host-preflight ]; then
              [ "$#" = 6 ]
              [ "$2" = "{self.known_hosts}" ]
              [ "$3" = "{self.ssh_key}" ]
              [ "$4" = "{'1' * 64}" ]
              [ "$5" = 750 ]
              [ "$6" = 3600 ]
              [ "${{ALLOW_FALLBACK_SSH_CONTROL:-}}" = 1 ]
              [ "${{ALLOW_PHONE_CREDENTIAL_USE:-}}" = 1 ]
              [ -z "${{ALLOW_FALLBACK_SSH_ATIME_EFFECTS+x}}" ]
              [ -z "${{ALLOW_TEMPORARY_BOOT+x}}" ]
              printf 'fallback:ssh-host-preflight\n' >>"$MOCK_CALLS"
              echo 'PASS fallback SSH host preflight'
              exit 0
            fi
            [ "$1" = wait-ssh-preflight ]
            [ "$2" = "{self.known_hosts}" ]
            [ "$3" = "{self.ssh_key}" ]
            [ "$4" = "{'1' * 64}" ]
            [ "$5" = "{self.evidence / 'recovery-usb.anchor'}" ]
            [ -f "$5" ]
            grep -Fxq 'format=rog5-minimal-headless-usb-anchor-v1' "$5"
            [ "$6" = 750 ]
            [ "$7" = "{self.evidence / 'fallback-identity.record'}" ]
            [ "$#" = 7 ]
            [ "${{ALLOW_FALLBACK_SSH_CONTROL:-}}" = 1 ]
            [ "${{ALLOW_FALLBACK_SSH_ATIME_EFFECTS:-}}" = 1 ]
            [ "${{ALLOW_PHONE_CREDENTIAL_USE:-}}" = 1 ]
            [ -z "${{ALLOW_TEMPORARY_BOOT+x}}" ]
            printf 'fallback:ssh-preflight\n' >>"$MOCK_CALLS"
            if [ "${{MOCK_FALLBACK_FAIL:-0}}" = 1 ]; then
              echo 'FAIL injected fallback SSH rejection'
              exit 1
            fi
            : >"$MOCK_ROOT/fallback-proved"
            : >"$MOCK_ROOT/target-departed"
            umask 077
            printf '%s\n' \
              'format=rog5-fallback-identity-v2' \
              'kernel_release=5.4.134-qgki-perf-00001-g6c308144c23e' \
              'boot_id={FALLBACK_BOOT_ID}' \
              'usb_location=pci/usb1/1-1/1-1.2' \
              'nonce={'6' * 32}' \
              'thermal_max=61400' \
              'record_sha256={'7' * 64}' \
              'signature_sha256={'8' * 64}' \
              'host_pin_sha256={'9' * 64}' \
              'result=PASS' \
              >"$7"
            echo 'PASS pinned exact Alpine fallback returned over strict SSH on the recovery USB port'
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
                "BUNDLE": BUNDLE,
                "MANIFEST_SHA256": MANIFEST,
                "ROG5_STABLE_RECOVERY_PROFILE": RECOVERY_PROFILE,
                "SSH_KEY": str(self.ssh_key),
                "HEADLESS_ROOT_PACKAGE": str(self.package),
                "RECOVERY_CANDIDATE_RECORD": str(self.candidate),
                "BUNDLE_ROOT": str(self.bundle_root),
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

    def test_key_preflight_guards_fail_before_credentials(self):
        result = self.fixture.run(
            "key-preflight",
            guards=False,
            SSH_KEY="/absent/guard-must-win",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "deployment-key admission requires exact fresh guards",
            result.stderr,
        )
        self.assertEqual(self.fixture.call_lines(), [])

    def test_key_preflight_stops_before_phone_and_privilege(self):
        result = self.fixture.run("key-preflight")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "no phone or privileged host action occurred",
            result.stdout,
        )
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("key-admission:verify"), 1)
        self.assertFalse(any(line.startswith("live:") for line in calls))
        self.assertFalse(any(line.startswith("bundle:") for line in calls))
        self.assertFalse(any(line.startswith("nfs:") for line in calls))

    def test_consumed_manifest_fails_before_private_key_inspection(self):
        result = self.fixture.run(
            "key-preflight",
            MANIFEST_SHA256=CONSUMED_MANIFEST,
            SSH_KEY="/absent/consumed-manifest-must-win",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("consumed live payload", result.stderr)
        self.assertNotIn("SSH_KEY", result.stderr)
        self.assertFalse(
            any(
                line.startswith("key-admission:")
                for line in self.fixture.call_lines()
            )
        )

    def test_preflight_admits_key_and_stops_before_phone_boot_or_ssh(self):
        result = self.fixture.run("preflight")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("deployment key was admitted locally", result.stdout)
        calls = self.fixture.call_lines()
        self.assertIn("key-admission:verify", calls)
        self.assertIn("bundle:preflight", calls)
        self.assertIn("nfs:preflight", calls)
        self.assertIn("live:preflight", calls)
        self.assertIn("fallback:ssh-host-preflight", calls)
        self.assertNotIn("live:boot", calls)
        self.assertNotIn("fallback:ssh-preflight", calls)
        self.assertFalse(any(line.startswith("host-key:") for line in calls))
        self.assertFalse(any(self.fixture.evidence.iterdir()))

        self.fixture.nfs_exports.write_text(
            "/export 169.254.77.2(sync)\n",
            encoding="ascii",
        )
        rejected = self.fixture.run("preflight")
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("host retains an NFS export", rejected.stderr)
        self.assertEqual(
            self.fixture.call_lines().count("bundle:preflight"),
            1,
        )

        self.fixture.nfs_exports.write_bytes(b"")
        self.fixture.nfs_exports.chmod(0o666)
        unsafe = self.fixture.run("preflight")
        self.assertNotEqual(unsafe.returncode, 0)
        self.assertIn("export table metadata is unsafe", unsafe.stderr)

        self.fixture.nfs_exports.unlink()
        self.fixture.nfs_exports.symlink_to(self.fixture.package)
        linked = self.fixture.run("preflight")
        self.assertNotEqual(linked.returncode, 0)
        self.assertIn("cannot inspect host NFS exports", linked.stderr)
        self.assertEqual(
            self.fixture.call_lines().count("bundle:preflight"),
            1,
        )

    def test_historical_recovery_profile_fails_before_credential_paths(self):
        result = self.fixture.run(
            "preflight",
            ROG5_STABLE_RECOVERY_PROFILE="historical-2026-07-29",
            SSH_KEY="/absent/profile-must-win",
            FALLBACK_KNOWN_HOSTS="/absent/profile-must-win",
            EVIDENCE_DIR="/absent/profile-must-win",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "must select the headless SSH deployment profile",
            result.stderr,
        )
        self.assertTrue(
            all(
                line.startswith("git:")
                for line in self.fixture.call_lines()
            )
        )

    def test_success_orders_cleanup_before_nfs_and_resolves_after_fallback(self):
        result = self.fixture.run("run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS one minimal-headless lifecycle", result.stdout)
        calls = self.fixture.call_lines()
        self.assertLess(
            calls.index("fallback:ssh-host-preflight"),
            calls.index("live:boot"),
        )
        self.assertLess(
            calls.index("key-admission:verify"),
            calls.index("live:preflight"),
        )
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
            calls.index("fallback:ssh-preflight"),
            calls.index("control:resolve:TARGET_ACCEPTED"),
        )
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)
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
        self.assertNotIn("fallback:ssh-preflight", calls)
        self.assertEqual(calls.count("nfs:cancel"), 1)
        self.assertEqual(calls.count("nfs:terminated"), 1)
        self.assertFalse((self.fixture.root / "nfs-state").exists())

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

    def test_cancel_failure_does_not_skip_fallback_or_resolution(self):
        result = self.fixture.run(
            "run",
            MOCK_CONTROL_UNKNOWN="1",
            MOCK_CANCEL_FAIL="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "privileged network-root cancellation failed",
            result.stderr,
        )
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)
        self.assertEqual(
            calls.count("control:resolve:FALLBACK_RETURNED"),
            1,
        )

    def test_silent_post_arm_failure_uses_new_durable_ledger(self):
        for variable in (
            "MOCK_CONTROL_SILENT_UNKNOWN",
            "MOCK_CONTROL_MALFORMED_SUCCESS",
        ):
            with self.subTest(variable=variable):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run("run", **{variable: "1"})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "resolved as FALLBACK_RETURNED",
                    result.stderr,
                )
                calls = self.fixture.call_lines()
                self.assertEqual(
                    calls.count("control:prepare-commit"),
                    1,
                )
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
        self.assertEqual(
            self.fixture.call_lines().count("fallback:ssh-preflight"),
            1,
        )
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
        self.assertEqual(
            self.fixture.call_lines().count("fallback:ssh-preflight"),
            1,
        )
        self.assertFalse(
            any(
                line.startswith("control:resolve:")
                for line in self.fixture.call_lines()
            )
        )

    def test_final_cleanup_waits_for_fallback_udev_identity(self):
        result = self.fixture.run(
            "run",
            MOCK_RUNTIME_FAIL="1",
            MOCK_UDEV_GAP_AFTER_FALLBACK="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resolved as FALLBACK_RETURNED", result.stderr)
        self.assertTrue(
            (self.fixture.root / "udev-gap-consumed").is_file()
        )
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)
        self.assertEqual(
            calls.count("control:resolve:FALLBACK_RETURNED"),
            1,
        )

    def test_final_cleanup_rejects_persistent_udev_identity_gap(self):
        result = self.fixture.run(
            "run",
            MOCK_RUNTIME_FAIL="1",
            MOCK_UDEV_MISSING_AFTER_FALLBACK="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("intent remains UNKNOWN", result.stderr)
        self.assertEqual(
            self.fixture.call_lines().count("fallback:ssh-preflight"),
            1,
        )
        self.assertEqual(
            self.fixture.call_lines().count("control:prepare-commit"),
            1,
        )
        self.assertFalse(
            any(
                line.startswith("control:resolve:")
                for line in self.fixture.call_lines()
            )
        )

    def test_target_acceptance_waits_for_fallback_udev_identity(self):
        result = self.fixture.run(
            "run",
            MOCK_UDEV_GAP_AFTER_FALLBACK="1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)
        self.assertEqual(calls.count("control:resolve:TARGET_ACCEPTED"), 1)

    def test_final_cleanup_requires_continuous_usb_identity(self):
        result = self.fixture.run(
            "run",
            MOCK_RUNTIME_FAIL="1",
            MOCK_UDEV_FLAP_AFTER_FALLBACK="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("intent remains UNKNOWN", result.stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)
        self.assertFalse(
            any(line.startswith("control:resolve:") for line in calls)
        )

    def test_final_cleanup_waits_for_address_observation_race(self):
        result = self.fixture.run(
            "run",
            MOCK_RUNTIME_FAIL="1",
            MOCK_ADDRESS_GAP_AFTER_FALLBACK="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resolved as FALLBACK_RETURNED", result.stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)
        self.assertEqual(
            calls.count("control:resolve:FALLBACK_RETURNED"),
            1,
        )

    def test_nonidentity_cleanup_failure_is_not_retried(self):
        result = self.fixture.run(
            "run",
            MOCK_RUNTIME_FAIL="1",
            MOCK_TRANSIENT_FIREWALL_AFTER_FALLBACK="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("intent remains UNKNOWN", result.stderr)
        self.assertTrue(
            (self.fixture.root / "firewall-gap-consumed").is_file()
        )
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)
        self.assertFalse(
            any(line.startswith("control:resolve:") for line in calls)
        )

    def test_final_cleanup_subprocesses_share_one_deadline(self):
        started = time.monotonic()
        result = self.fixture.run(
            "run",
            MOCK_RUNTIME_FAIL="1",
            MOCK_UDEV_HANG_AFTER_FALLBACK="1",
        )
        elapsed = time.monotonic() - started
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("intent remains UNKNOWN", result.stderr)
        self.assertLess(elapsed, 2.0)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)
        self.assertFalse(
            any(line.startswith("control:resolve:") for line in calls)
        )

    def test_failed_fallback_proof_leaves_intent_unknown(self):
        result = self.fixture.run(
            "run",
            MOCK_RUNTIME_FAIL="1",
            MOCK_FALLBACK_FAIL="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("intent remains UNKNOWN", result.stderr)
        self.assertEqual(
            self.fixture.call_lines().count("fallback:ssh-preflight"),
            1,
        )
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
        runtime_acceptance = RUNTIME_ACCEPTANCE.read_text(encoding="utf-8")
        for token in GUARDS:
            self.assertIn(token, runner)
        for token in (
            "fallback-acm-control.py",
            "ALLOW_FALLBACK_SSH_CONTROL",
            "ALLOW_FALLBACK_SSH_ATIME_EFFECTS",
            "wait-ssh-preflight",
            "PASS one recovery bundle transfer completed",
            "INFO recovery bundle host network state removed",
            "TARGET_ACCEPTED",
            "FALLBACK_RETURNED",
            "outcome remains UNKNOWN",
            "FALLBACK_CONTROL_MARGIN_SECONDS = 120",
        ):
            self.assertIn(token, runner)
        self.assertLess(
            runner.index("control_attempted = True"),
            runner.index("control_process = start_logged"),
        )
        self.assertEqual(runner.count('"prepare-commit",'), 1)
        for token in (
            "StrictHostKeyChecking=yes",
            "ConnectionAttempts=3",
            "UserKnownHostsFile=",
            "HostKeyAlias=rog5-minimal-headless-v1",
            "remote_stage_verify_and_collect",
        ):
            self.assertIn(token, runtime_acceptance)
        for token in (
            "installed_root=/usr/libexec/rog5-recovery-host",
            "installed_server=$installed_root/serve-network-root.sh",
            "installed_verifier=$installed_root/headless-network-root.py",
            "installed_root_tool=$installed_root/persistent-root-tool.py",
            'exec pkexec "$installed_server"',
            '"$installed_server" preflight',
            '"$installed_server" serve',
            '"$installed_server" cancel',
            "ALLOW_HEADLESS_NETWORK_ROOT_CANCEL",
        ):
            self.assertIn(token, launcher)
        self.assertIn(
            "installed server accepts only the minimal headless root",
            server,
        )
        self.assertIn("installed_action == preflight", server)
        self.assertIn("installed_action == cancel", server)
        self.assertIn("rog5-network-root-server.state", server)
        self.assertIn("process_start_time", server)
        self.assertIn("process_state", server)
        self.assertIn("$state == Z", server)
        self.assertIn("os.pidfd_open(pid, 0)", server)
        self.assertIn("signal.pidfd_send_signal(pidfd, signal.SIGSTOP)", server)
        self.assertIn("os.killpg(pid, signal.SIGTERM)", server)
        self.assertIn("requires an isolated process group", server)
        self.assertIn("PKEXEC_UID", server)
        self.assertIn("start_new_session=True", runner)
        self.assertLess(
            launcher.index("if [[ $action == cancel ]]"),
            launcher.index("ROG5_NFS_TIMEOUT must be between"),
        )
        self.assertLess(
            server.index(
                "if [[ $installed_mode == 1 && "
                "$installed_action == cancel ]]"
            ),
            server.index("for command in awk date exportfs"),
        )
        for token in (
            "network_server_source",
            "headless_verifier_source",
            "persistent_root_tool_source",
            "install -o root -g root -m 0555",
            "export_storage_root=/home/rog5-linux",
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
