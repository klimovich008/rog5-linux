#!/usr/bin/env python3
"""Offline lifecycle tests for the minimal-headless one-shot controller."""

from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from unittest import mock


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
CONSUMED_R2_MANIFEST = (
    "9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630"
)
PACKAGE_SHA256 = "2" * 64
CANDIDATE_SHA256 = "3" * 64
CANDIDATE = "headless-ssh-network-root-v3"
BUNDLE = "headless-ssh-network-root-v3-r2"
DIAGNOSTIC_CANDIDATE = "headless-netroot-early-diag-v1"
DIAGNOSTIC_BUNDLE = "headless-netroot-early-diag-v1"
DIAGNOSTIC_PROFILE = "diagnostic-initramfs-v1"
RECOVERY_PROFILE = "headless-ssh-deployment-v3"
DIAGNOSTIC_RECOVERY_PROFILE = "headless-diagnostic-generation3-live-v1"
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


def load_runner_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_minimal_headless_live_cycle_test",
        RUNNER,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load lifecycle controller")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


CYCLE = load_runner_module()


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
        (self.state / "host-boot-id").write_text(
            TARGET_BOOT_ID + "\n",
            encoding="ascii",
        )
        self.anchor_created = str(int(time.time()))
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
        self.diagnostic_bundle = self.bundle_root / DIAGNOSTIC_BUNDLE
        self.diagnostic_bundle.mkdir(mode=0o700)
        self.diagnostic_manifest = self.diagnostic_bundle / "manifest"
        self.diagnostic_manifest.write_bytes(b"offline-runtime-manifest\n")
        self.diagnostic_manifest.chmod(0o400)
        self.diagnostic_evidence = {
            "candidate": DIAGNOSTIC_CANDIDATE,
            "capture_status": "valid",
            "dropped_usb_events": 0,
            "ended_unix_ns": 300,
            "end_reason": "disconnected",
            "format": "rog5-early-target-evidence-v1",
            "frame_count": 1,
            "frames": [
                {
                    "host_monotonic_ns": 200,
                    "host_unix_ns": 200,
                    "record": {
                        "boot_id": TARGET_BOOT_ID,
                        "boottime_ms": 100,
                        "candidate": DIAGNOSTIC_CANDIDATE,
                        "dropped_updates": 0,
                        "fault": "none",
                        "last_good_code": 10,
                        "sequence": 1,
                        "stage": "reporter-up",
                        "stage_code": 10,
                        "watchdog_deadline_ms": 600000,
                    },
                }
            ],
            "host_boot_id": TARGET_BOOT_ID,
            "started_unix_ns": 100,
            "target_boot_id": TARGET_BOOT_ID,
            "target_product": "ROG5 diagnostic network root",
            "usb_events": [],
            "usb_location": "pci/usb1/1-1/1-1.2",
        }
        self.diagnostic_evidence_payload = json.dumps(
            self.diagnostic_evidence,
            sort_keys=True,
            separators=(",", ":"),
        )
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
            case ${MOCK_SS_LISTENER_ADDRESS:-} in
              127.0.0.1)
                case $* in
                  *"sport = :8080 and ( src = 0.0.0.0/32 or src = 169.254.77.1/32 )"*)
                    ;;
                  *"-lnt4"*"sport = :8080"*|*"-lntu4"*"sport = :8080"*)
                    printf 'tcp LISTEN 0 10 127.0.0.1:8080 0.0.0.0:*\n'
                    ;;
                esac
                ;;
              0.0.0.0|169.254.77.1)
                case $* in
                  *"-lnt4"*"sport = :8080 and ( src = 0.0.0.0/32 or src = 169.254.77.1/32 )"*)
                    printf 'tcp LISTEN 0 10 %s:8080 0.0.0.0:*\n' \
                      "$MOCK_SS_LISTENER_ADDRESS"
                    ;;
                esac
                ;;
              ::|::ffff:0.0.0.0|::ffff:169.254.77.1)
                case $* in
                  *"-lnt6"*"sport = :8080 and ( src = ::/128 or src = ::ffff:0.0.0.0/128 or src = ::ffff:169.254.77.1/128 )"*)
                    printf 'tcp LISTEN 0 10 [%s]:8080 [::]:*\n' \
                      "$MOCK_SS_LISTENER_ADDRESS"
                    ;;
                esac
                ;;
            esac
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
                if [ ! -e "$MOCK_ROOT/profile-deferred" ] ||
                   [ -e "$MOCK_ROOT/profile-restored" ]; then
                  echo '9: usbmock0 inet 169.254.77.1/30 scope global usbmock0'
                fi
                if { [ "${MOCK_ADDRESS_RESIDUE_AFTER_BUNDLE:-0}" = 1 ] &&
                     [ -e "$MOCK_ROOT/bundle-consumed" ]; } ||
                   { [ "${MOCK_ADDRESS_RESIDUE_AFTER_NFS:-0}" = 1 ] &&
                     [ -e "$MOCK_ROOT/target-departed" ]; }; then
                  echo '9: usbmock0 inet 169.254.77.9/30 scope global usbmock0'
                fi
                ;;
              *" -4 -o address show "*)
                if [ ! -e "$MOCK_ROOT/profile-deferred" ] ||
                   [ -e "$MOCK_ROOT/profile-restored" ]; then
                  echo '9: usbmock0 inet 169.254.77.1/30 scope global usbmock0'
                fi
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
            uuid=244dd128-e3b1-458e-9639-5e4ab4d8854f
            case "$*" in
              '-g GENERAL.CON-UUID device show usbmock0')
                if [ ! -e "$MOCK_ROOT/profile-deferred" ] ||
                   [ -e "$MOCK_ROOT/profile-restored" ] ||
                   [ "${MOCK_DEFERRED_ACTIVE_UUID:-0}" = 1 ]; then
                  echo "$uuid"
                elif [ "${MOCK_DEFERRED_PROFILE_GAP:-0}" = 1 ] &&
                     [ ! -e "$MOCK_ROOT/deferred-profile-gap-consumed" ]; then
                  : >"$MOCK_ROOT/deferred-profile-gap-consumed"
                  echo "$uuid"
                fi
                ;;
              '-g connection.uuid,connection.id,connection.interface-name,connection.autoconnect connection show rog5-fallback-usb-ssh')
                printf '%s\n' "$uuid" 'rog5-fallback-usb-ssh' 'usbmock0'
                if [ "${MOCK_DEFERRED_AUTOCONNECT:-0}" = 1 ]; then
                  echo yes
                elif [ -e "$MOCK_ROOT/profile-deferred" ] &&
                     [ ! -e "$MOCK_ROOT/profile-restored" ]; then
                  echo no
                else
                  echo yes
                fi
                ;;
              *)
                if [ "${MOCK_NM_RESIDUE_AFTER_BUNDLE:-0}" = 1 ] &&
                   [ -e "$MOCK_ROOT/bundle-consumed" ]; then
                  echo yes
                elif [ -e "$MOCK_ROOT/profile-deferred" ] &&
                     [ ! -e "$MOCK_ROOT/profile-restored" ]; then
                  echo no
                else
                  echo yes
                fi
                ;;
            esac
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
            [ "$9" = --manifest-sha256 ]
            [ "${{10}}" = "{MANIFEST}" ]
            [ "${{11}}" = --admission-profile ]
            case ${{12}} in
              headless-ssh-r2)
                [ "$8" = "{self.bundle_manifest}" ]
                candidate={CANDIDATE}
                bundle={BUNDLE}
                profile=network-root-v1
                target=headless-ssh-network-root
                ;;
              early-target-diagnostic-v1)
                [ "$8" = "{self.diagnostic_manifest}" ]
                candidate={DIAGNOSTIC_CANDIDATE}
                bundle={DIAGNOSTIC_BUNDLE}
                profile={DIAGNOSTIC_PROFILE}
                target=headless-netroot-early-diag
                ;;
              *) exit 1 ;;
            esac
            printf 'key-admission:verify\\n' >>"{self.calls}"
            printf '%s\\n' \
              'format=rog5-headless-ssh-v2-key-admission-v1' \
              "candidate=$candidate" \
              "bundle=$bundle" \
              "profile=$profile" \
              'build_profile=headless-ssh-v2' \
              "target_id=$target" \
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
            f"""\
            #!/bin/sh
            set -eu
            [ -z "${{UNRELATED_CREDENTIAL+x}}" ]
            [ -z "${{SSH_KEY+x}}" ]
            [ -z "${{FALLBACK_KNOWN_HOSTS+x}}" ]
            [ -z "${{EVIDENCE_DIR+x}}" ]
            case $BUNDLE in
              {BUNDLE})
                [ "$ROG5_STABLE_RECOVERY_PROFILE" = "{RECOVERY_PROFILE}" ]
                ;;
              {DIAGNOSTIC_BUNDLE})
                [ "$ROG5_STABLE_RECOVERY_PROFILE" = "{DIAGNOSTIC_RECOVERY_PROFILE}" ]
                ;;
              *) exit 1 ;;
            esac
            if [ "$1" = boot ]; then
              [ "${{ALLOW_TEMPORARY_BOOT:-}}" = 1 ]
              [ "${{ALLOW_HEADLESS_LIVE_GATE:-}}" = 1 ]
              [ "${{ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE:-}}" = 1 ]
              [ -z "${{ALLOW_STABLE_RECOVERY_CONTROL+x}}" ]
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
            if [ "$1" = restore-fallback ]; then
              [ "$2" = "$MOCK_ROOT/evidence/recovery-usb.anchor" ]
              [ "$3" -ge 1 ]
              [ "$3" -le 750 ]
              [ "$#" = 3 ]
              [ -e "$MOCK_ROOT/profile-deferred" ]
              printf 'bundle:restore-fallback\n' >>"$MOCK_CALLS"
              if [ "${MOCK_PROFILE_RESTORE_FAIL:-0}" = 1 ]; then
                echo 'FAIL injected fallback profile restoration failure'
                exit 1
              fi
              : >"$MOCK_ROOT/target-departed"
              : >"$MOCK_ROOT/profile-restored"
              echo 'PASS exact Alpine fallback profile restored on usbmock0'
              exit 0
            fi
            [ "$1" = serve-deferred ]
            shift
            printf 'bundle:start\n' >>"$MOCK_CALLS"
            echo 'PASS recovery bundle server ready on 169.254.77.1:8080 via usb0'
            while [ ! -e "$MOCK_ROOT/prepare-started" ]; do
              sleep 0.01
            done
            if [ "${MOCK_FETCH_CACHE_HIT:-0}" = 1 ]; then
              while :; do sleep 1; done
            fi
            : >"$MOCK_ROOT/bundle-consumed"
            printf 'bundle:transfer\n' >>"$MOCK_CALLS"
            echo 'PASS one recovery bundle transfer completed'
            echo 'INFO recovery bundle host network state removed'
            echo 'INFO fallback NetworkManager profile restoration deferred'
            : >"$MOCK_ROOT/profile-deferred"
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
                : >"$MOCK_ROOT/prepare-started"
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
                printf '{{"session":"{SESSION}","request":"{REQUEST}","manifest_sha256":"{MANIFEST}","target":"%s","state":"TRANSMITTED","outcome":"UNKNOWN"}}\n' \
                  "$BUNDLE" >"$intent_root/{SESSION}.json"
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
                printf '{{"session":"{SESSION}","request":"{PREPARE}","result":"PREPARED","state":"PREPARED","prepared_bundle":"%s","manifest_sha256":"{MANIFEST}","watchdog":"ARMED"}}\n{{"session":"{SESSION}","request":"{REQUEST}","commit_request":"{REQUEST}","result":"CLAIMED","state":"CLAIMED","manifest_sha256":"{MANIFEST}","watchdog":"ARMED","execution_started":"NO"}}\n{{"session":"{SESSION}","request":"{REQUEST}","manifest_sha256":"{MANIFEST}","target":"%s","state":"TRANSMITTED","outcome":"UNKNOWN"}}\n' \
                  "$BUNDLE" "$BUNDLE"
                echo 'PASS recovery accepted one commit; outcome remains UNKNOWN'
                ;;
              show)
                printf 'control:show\n' >>"$MOCK_CALLS"
                printf '{{"session":"{SESSION}","request":"{REQUEST}","manifest_sha256":"{MANIFEST}","target":"%s","state":"TRANSMITTED","outcome":"UNKNOWN"}}\n' \
                  "$BUNDLE"
                ;;
              resolve)
                printf 'control:resolve:%s\n' "$4" >>"$MOCK_CALLS"
                printf '{{"session":"{SESSION}","request":"{REQUEST}","manifest_sha256":"{MANIFEST}","target":"%s","state":"RESOLVED","outcome":"%s"}}\n' \
                  "$BUNDLE" "$4"
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
                  "created_unix=$MOCK_ANCHOR_CREATED" \
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
            "collect-early-target-diagnostics.py",
            f"""\
            #!/bin/sh
            set -eu
            [ "$#" = 4 ]
            [ "$1" = "{self.evidence / 'recovery-usb.anchor'}" ]
            [ "$2" = "{self.evidence / 'early-target-diagnostics.json'}" ]
            [ "$3" = 120 ]
            [ "$4" = 660 ]
            [ -z "${{SSH_KEY+x}}" ]
            [ -z "${{UNRELATED_CREDENTIAL+x}}" ]
            if [ "${{MOCK_COLLECTOR_EXIT_BEFORE_READY:-0}}" = 1 ]; then
              echo 'FAIL injected collector startup failure' >&2
              exit 1
            fi
            if [ "${{MOCK_COLLECTOR_UNTERMINATED_READY:-0}}" = 1 ]; then
              printf 'READY receive-only early-target diagnostic collector'
              exit 1
            fi
            if [ "${{MOCK_COLLECTOR_PARTIAL_READY:-0}}" = 1 ]; then
              echo 'prefix READY receive-only early-target diagnostic collector suffix'
              exit 1
            fi
            printf 'collector:ready\n' >>"$MOCK_CALLS"
            echo 'READY receive-only early-target diagnostic collector'
            if [ "${{MOCK_COLLECTOR_DUPLICATE_READY:-0}}" = 1 ]; then
              echo 'READY receive-only early-target diagnostic collector'
            fi
            if [ "${{MOCK_COLLECTOR_EXIT_BEFORE_HANDOFF:-0}}" = 1 ]; then
              while [ ! -e "$MOCK_ROOT/bundle-consumed" ]; do
                sleep 0.01
              done
              echo 'FAIL injected collector pre-handoff exit' >&2
              exit 1
            fi
            if [ "${{MOCK_COLLECTOR_DELAYED_DUPLICATE_READY:-0}}" = 1 ]; then
              while [ ! -e "$MOCK_ROOT/bundle-consumed" ]; do
                sleep 0.01
              done
              echo 'READY receive-only early-target diagnostic collector'
            fi
            while [ ! -e "$MOCK_ROOT/nfs-started" ]; do
              sleep 0.01
            done
            umask 077
            printf '%s\n' '{self.diagnostic_evidence_payload}' >"$2"
            printf 'collector:capture\n' >>"$MOCK_CALLS"
            : >"$MOCK_ROOT/target-departed"
            if [ "${{MOCK_COLLECTOR_FAIL:-0}}" = 1 ]; then
              echo 'FAIL early-target diagnostic capture: invalid-stream' >&2
              exit 1
            fi
            echo 'PASS receive-only early-target diagnostic capture frames=4 last=140:ssh-active end=disconnect'
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
            [ "$6" -ge 1 ]
            [ "$6" -le 750 ]
            [ "$7" = "{self.evidence / 'fallback-identity.record'}" ]
            [ "$#" = 7 ]
            [ "${{ALLOW_FALLBACK_SSH_CONTROL:-}}" = 1 ]
            [ "${{ALLOW_FALLBACK_SSH_ATIME_EFFECTS:-}}" = 1 ]
            [ "${{ALLOW_PHONE_CREDENTIAL_USE:-}}" = 1 ]
            [ -z "${{ALLOW_TEMPORARY_BOOT+x}}" ]
            [ -e "$MOCK_ROOT/profile-restored" ]
            printf 'fallback:ssh-preflight\n' >>"$MOCK_CALLS"
            if [ "${{MOCK_FALLBACK_FAIL:-0}}" = 1 ]; then
              echo 'FAIL injected fallback SSH rejection'
              exit 1
            fi
            : >"$MOCK_ROOT/fallback-proved"
            : >"$MOCK_ROOT/target-departed"
            umask 077
            fallback_boot_id={FALLBACK_BOOT_ID}
            if [ "${{MOCK_FALLBACK_REUSE_TARGET_BOOT:-0}}" = 1 ]; then
              fallback_boot_id={TARGET_BOOT_ID}
            fi
            printf '%s\n' \
              'format=rog5-fallback-identity-v2' \
              'kernel_release=5.4.134-qgki-perf-00001-g6c308144c23e' \
              "boot_id=$fallback_boot_id" \
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
                "MOCK_ANCHOR_CREATED": self.anchor_created,
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
        if action.startswith("diagnostic-"):
            updates.setdefault("BUNDLE", DIAGNOSTIC_BUNDLE)
            updates.setdefault(
                "ROG5_STABLE_RECOVERY_PROFILE",
                DIAGNOSTIC_RECOVERY_PROFILE,
            )
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

    def test_privileged_restore_anchor_is_private_fresh_and_host_bound(self):
        anchor = self.fixture.evidence / "restore.anchor"

        def write(
            *,
            created: str | None = None,
            boot_id: str = TARGET_BOOT_ID,
            reorder: bool = False,
        ) -> None:
            fields = [
                "format=rog5-minimal-headless-usb-anchor-v1",
                f"host_boot_id={boot_id}",
                f"created_unix={created or self.fixture.anchor_created}",
                "usb_location=pci/usb1/1-1/1-1.2",
                "recovery_vendor=1d6b",
                "recovery_product_id=0104",
                "recovery_product=ROG5 recovery",
            ]
            if reorder:
                fields[2], fields[3] = fields[3], fields[2]
            anchor.write_text("\n".join((*fields, "")), encoding="ascii")
            anchor.chmod(0o600)

        with mock.patch.dict(
            os.environ,
            self.fixture.environment(),
            clear=False,
        ):
            dependencies = CYCLE.Dependencies.from_environment()
        write()
        self.assertEqual(
            CYCLE.read_recovery_anchor_location(anchor, dependencies),
            "pci/usb1/1-1/1-1.2",
        )
        mutations = (
            {"created": str(int(time.time()) - 3601)},
            {"boot_id": FALLBACK_BOOT_ID},
            {"reorder": True},
        )
        for values in mutations:
            with self.subTest(values=values):
                write(**values)
                with self.assertRaises(CYCLE.CycleError):
                    CYCLE.read_recovery_anchor_location(
                        anchor,
                        dependencies,
                    )
        write()
        anchor.chmod(0o644)
        with self.assertRaises(CYCLE.CycleError):
            CYCLE.read_recovery_anchor_location(anchor, dependencies)

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
        for manifest in (CONSUMED_MANIFEST, CONSUMED_R2_MANIFEST):
            with self.subTest(manifest=manifest):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run(
                    "key-preflight",
                    MANIFEST_SHA256=manifest,
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

    def test_diagnostic_preflight_stops_before_collector_and_phone(self):
        result = self.fixture.run("diagnostic-preflight")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(DIAGNOSTIC_CANDIDATE, result.stdout)
        calls = self.fixture.call_lines()
        self.assertIn("key-admission:verify", calls)
        self.assertIn("bundle:preflight", calls)
        self.assertIn("nfs:preflight", calls)
        self.assertIn("live:preflight", calls)
        self.assertNotIn("live:boot", calls)
        self.assertNotIn("collector:ready", calls)
        self.assertNotIn("control:prepare-commit", calls)
        self.assertFalse(any(self.fixture.evidence.iterdir()))

    def test_preflight_allows_unrelated_loopback_bundle_port(self):
        result = self.fixture.run(
            "diagnostic-preflight",
            MOCK_SS_LISTENER_ADDRESS="127.0.0.1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.fixture.call_lines()
        self.assertIn(
            "ss:-H -lnt4 sport = :8080 and ( src = 0.0.0.0/32 or "
            "src = 169.254.77.1/32 )",
            calls,
        )
        self.assertIn(
            "ss:-H -lnt6 sport = :8080 and ( src = ::/128 or "
            "src = ::ffff:0.0.0.0/128 or "
            "src = ::ffff:169.254.77.1/128 )",
            calls,
        )

    def test_preflight_rejects_conflicting_bundle_port(self):
        for address in (
            "0.0.0.0",
            "169.254.77.1",
            "::",
            "::ffff:0.0.0.0",
            "::ffff:169.254.77.1",
        ):
            with self.subTest(address=address):
                result = self.fixture.run(
                    "diagnostic-preflight",
                    MOCK_SS_LISTENER_ADDRESS=address,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "host listener remains on TCP port 8080",
                    result.stderr,
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
            "must select the exact lifecycle deployment profile",
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
            calls.index("bundle:restore-fallback"),
            calls.index("fallback:ssh-preflight"),
        )
        self.assertLess(
            calls.index("fallback:ssh-preflight"),
            calls.index("control:resolve:TARGET_ACCEPTED"),
        )
        self.assertEqual(calls.count("bundle:restore-fallback"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)
        self.assertTrue(
            (self.fixture.evidence / "target-known-hosts").is_file()
        )
        self.assertTrue(
            (self.fixture.evidence / "fallback-identity.record").is_file()
        )
        self.assertTrue(
            (
                self.fixture.evidence
                / "fallback-profile-restore.log"
            ).is_file()
        )
        resolution = (
            self.fixture.evidence / "intent-resolution.log"
        ).read_text(encoding="utf-8")
        self.assertIn('"outcome":"TARGET_ACCEPTED"', resolution)

    def test_diagnostic_collector_is_ready_before_commit_and_resolves_fallback(self):
        result = self.fixture.run("diagnostic-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "PASS one early-target diagnostic lifecycle captured bounded "
            "evidence",
            result.stdout,
        )
        calls = self.fixture.call_lines()
        self.assertLess(
            calls.index("collector:ready"),
            calls.index("control:prepare-commit"),
        )
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(calls.count("collector:capture"), 1)
        self.assertNotIn("host-key:pin", calls)
        self.assertNotIn("runtime:start", calls)
        self.assertEqual(
            calls.count("control:resolve:FALLBACK_RETURNED"),
            1,
        )
        evidence = self.fixture.evidence / "early-target-diagnostics.json"
        self.assertTrue(evidence.is_file())
        self.assertEqual(evidence.stat().st_mode & 0o777, 0o600)

    def test_diagnostic_evidence_binds_every_lifecycle_identity(self):
        anchor = self.fixture.evidence / "anchor-fixture"
        anchor.write_text(
            "format=rog5-minimal-headless-usb-anchor-v1\n"
            f"host_boot_id={TARGET_BOOT_ID}\n"
            "created_unix=2000000000\n"
            "usb_location=pci/usb1/1-1/1-1.2\n"
            "recovery_vendor=1d6b\n"
            "recovery_product_id=0104\n"
            "recovery_product=ROG5 recovery\n",
            encoding="ascii",
        )
        anchor.chmod(0o600)

        def write_document(name: str, document: dict[str, object]) -> Path:
            path = self.fixture.evidence / f"evidence-{name}.json"
            path.write_text(
                json.dumps(document, sort_keys=True, separators=(",", ":"))
                + "\n",
                encoding="ascii",
            )
            path.chmod(0o600)
            return path

        baseline = write_document("baseline", self.fixture.diagnostic_evidence)
        self.assertEqual(
            CYCLE.verify_diagnostic_evidence(
                baseline,
                anchor,
                DIAGNOSTIC_CANDIDATE,
            ),
            TARGET_BOOT_ID,
        )

        def top(name: str, value: object):
            return lambda document: document.__setitem__(name, value)

        mutations = {
            "format": top("format", "wrong-format"),
            "candidate": top("candidate", "wrong-candidate"),
            "capture-status": top("capture_status", "rejected"),
            "host-boot": top("host_boot_id", FALLBACK_BOOT_ID),
            "usb-location": top("usb_location", "pci/usb9/9-9"),
            "target-boot": top("target_boot_id", FALLBACK_BOOT_ID),
            "target-product": top("target_product", "wrong product"),
            "end-reason": top("end_reason", "rejected"),
            "frame-count": top("frame_count", 2),
            "frame-candidate": lambda document: document["frames"][0][
                "record"
            ].__setitem__("candidate", "wrong-candidate"),
            "frame-boot": lambda document: document["frames"][0][
                "record"
            ].__setitem__("boot_id", FALLBACK_BOOT_ID),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                document = copy.deepcopy(self.fixture.diagnostic_evidence)
                mutate(document)
                path = write_document(name, document)
                with self.assertRaises(CYCLE.CycleError):
                    CYCLE.verify_diagnostic_evidence(
                        path,
                        anchor,
                        DIAGNOSTIC_CANDIDATE,
                    )

    def test_diagnostic_collector_rejection_preserves_fallback_and_no_retry(self):
        result = self.fixture.run(
            "diagnostic-run",
            MOCK_COLLECTOR_FAIL="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resolved as FALLBACK_RETURNED", result.stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("collector:ready"), 1)
        self.assertEqual(calls.count("collector:capture"), 1)
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(
            calls.count("control:resolve:FALLBACK_RETURNED"),
            1,
        )
        self.assertTrue(
            (
                self.fixture.evidence / "early-target-diagnostics.json"
            ).is_file()
        )

    def test_diagnostic_target_and_fallback_boot_ids_must_differ(self):
        result = self.fixture.run(
            "diagnostic-run",
            MOCK_FALLBACK_REUSE_TARGET_BOOT="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("intent remains UNKNOWN", result.stderr)
        self.assertIn(
            "fallback retained the minimal-headless boot identity",
            result.stderr,
        )
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)
        self.assertFalse(
            any(line.startswith("control:resolve:") for line in calls)
        )

    def test_diagnostic_collector_must_be_ready_before_commit(self):
        result = self.fixture.run(
            "diagnostic-run",
            MOCK_COLLECTOR_EXIT_BEFORE_READY="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("before its ready marker", result.stderr)
        calls = self.fixture.call_lines()
        self.assertNotIn("control:prepare-commit", calls)
        self.assertNotIn("bundle:start", calls)
        self.assertFalse(
            any(line.startswith("control:resolve:") for line in calls)
        )

    def test_diagnostic_readiness_marker_is_one_exact_line(self):
        cases = {
            "MOCK_COLLECTOR_PARTIAL_READY": "before its ready marker",
            "MOCK_COLLECTOR_UNTERMINATED_READY": "before its ready marker",
            "MOCK_COLLECTOR_DUPLICATE_READY": "duplicate ready markers",
            "MOCK_COLLECTOR_DELAYED_DUPLICATE_READY": (
                "lacks one exact newline-terminated marker"
            ),
        }
        for variable, message in cases.items():
            with self.subTest(variable=variable):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run(
                    "diagnostic-run",
                    **{variable: "1"},
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                calls = self.fixture.call_lines()
                if variable == "MOCK_COLLECTOR_DELAYED_DUPLICATE_READY":
                    self.assertEqual(
                        calls.count("control:prepare-commit"),
                        1,
                    )
                    self.assertIn("bundle:start", calls)
                    self.assertNotIn("nfs:start", calls)
                else:
                    self.assertNotIn("control:prepare-commit", calls)
                    self.assertNotIn("bundle:start", calls)

    def test_diagnostic_collector_must_remain_alive_before_handoff(self):
        result = self.fixture.run(
            "diagnostic-run",
            MOCK_COLLECTOR_EXIT_BEFORE_HANDOFF="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("before the commit handoff", result.stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertNotIn("nfs:start", calls)
        self.assertFalse(
            any(line.startswith("control:resolve:") for line in calls)
        )

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

    def test_cache_hit_without_transfer_never_starts_nfs_or_commit(self):
        result = self.fixture.run(
            "diagnostic-run",
            MOCK_FETCH_CACHE_HIT="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "one-transfer bundle server exceeded its bounded window",
            result.stderr,
        )
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertNotIn("bundle:transfer", calls)
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

    def test_deferred_profile_requires_inactive_uuid_and_autoconnect_off(self):
        for variable in (
            "MOCK_DEFERRED_ACTIVE_UUID",
            "MOCK_DEFERRED_AUTOCONNECT",
        ):
            with self.subTest(variable=variable):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run("run", **{variable: "1"})
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("nfs:start", self.fixture.call_lines())
                self.assertIn("deferred", result.stderr)

    def test_bundle_cleanup_waits_for_deferred_profile_observation_race(self):
        result = self.fixture.run(
            "run",
            MOCK_DEFERRED_PROFILE_GAP="1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            (
                self.fixture.root
                / "deferred-profile-gap-consumed"
            ).is_file()
        )
        self.assertIn("nfs:start", self.fixture.call_lines())

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

    def test_failed_profile_restore_is_not_retried_or_exposed_to_ssh(self):
        result = self.fixture.run(
            "run",
            MOCK_RUNTIME_FAIL="1",
            MOCK_PROFILE_RESTORE_FAIL="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("intent remains UNKNOWN", result.stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("bundle:restore-fallback"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 0)
        self.assertFalse(
            any(line.startswith("control:resolve:") for line in calls)
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
            "installed_client=$installed_root/rog5-recovery-host-client.py",
            'exec python3 -B "$installed_client"',
            "network-preflight-v3",
            "network-serve-v3",
            "network-cancel",
            "ALLOW_HEADLESS_NETWORK_ROOT_CANCEL",
        ):
            self.assertIn(token, launcher)
        self.assertNotIn("exec pkexec", launcher)
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
            "steamos_readonly=/usr/bin/steamos-readonly",
            "steamos_readonly_fd_path=/proc/self/fd/",
            "trap 'cleanup_signal_received=1' HUP INT TERM",
            "FAIL could not restore SteamOS read-only mode",
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
