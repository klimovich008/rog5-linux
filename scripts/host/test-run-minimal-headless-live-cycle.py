#!/usr/bin/env python3
"""Offline lifecycle tests for the minimal-headless one-shot controller."""

from __future__ import annotations

import copy
from dataclasses import replace
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
CLAIM_CONSUMER_PATH = (
    REPO / "scripts/host/consume-generation12-boot-claim.py"
)
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
DIAGNOSTIC_RECOVERY_PROFILE = "headless-diagnostic-generation12-live-v1"
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
COMMIT_FINGERPRINT = CYCLE.commit_request_fingerprint(
    SESSION,
    REQUEST,
    PREPARE,
    MANIFEST,
)


def load_claim_consumer_module():
    specification = importlib.util.spec_from_file_location(
        "rog5_generation12_claim_consumer_test",
        CLAIM_CONSUMER_PATH,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load Generation-12 claim consumer")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


CLAIM_CONSUMER = load_claim_consumer_module()


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
            "dropped_transport_snapshots": 0,
            "dropped_usb_events": 0,
            "ended_unix_ns": 300,
            "end_reason": "disconnected",
            "format": "rog5-early-target-evidence-v2",
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
            "transport_snapshot_count": 1,
            "transport_snapshots": [
                {
                    "carrier": None,
                    "host_monotonic_ns": 200,
                    "host_unix_ns": 200,
                    "interface": None,
                    "nfs_rpc_badauth": 0,
                    "nfs_rpc_badcalls": 0,
                    "nfs_rpc_badclnt": 0,
                    "nfs_rpc_calls": 0,
                    "nfs_rpc_xdrcall": 0,
                    "nfs_tcp_accept_backlog": 0,
                    "nfs_tcp_connections": 0,
                    "nfs_tcp_listener": 0,
                    "nfs_tcp_unrecovered_retransmits": 0,
                    "nfs_tcp_rx_queue": 0,
                    "nfs_tcp_states": "absent",
                    "nfs_tcp_tx_queue": 0,
                    "operstate": None,
                    "rx_bytes": None,
                    "rx_dropped": None,
                    "rx_errors": None,
                    "rx_packets": None,
                    "state": "absent",
                    "tx_bytes": None,
                    "tx_dropped": None,
                    "tx_errors": None,
                    "tx_packets": None,
                    "usb_location": "pci/usb1/1-1/1-1.2",
                }
            ],
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
              *"fetch --no-tags --prune origin refs/heads/agent/linux-recovery-host:refs/remotes/origin/agent/linux-recovery-host"*)
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
            if [ "${MOCK_SS_HANG_AFTER_RESTORE_FAILURE:-0}" = 1 ] &&
               [ -e "$MOCK_ROOT/profile-deferred" ] &&
               [ ! -e "$MOCK_ROOT/ss-cleanup-hang.pid" ]; then
              printf '%s\n' "$$" >"$MOCK_ROOT/ss-cleanup-hang.pid"
              sleep 5
            fi
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
            case ${MOCK_SS_PROGRESS_LISTENER_ADDRESS:-} in
              0.0.0.0|169.254.77.1)
                case $* in
                  *"-lnt4"*"sport = :8081 and ( src = 0.0.0.0/32 or src = 169.254.77.1/32 )"*)
                    printf 'tcp LISTEN 0 10 %s:8081 0.0.0.0:*\n' \
                      "$MOCK_SS_PROGRESS_LISTENER_ADDRESS"
                    ;;
                esac
                ;;
              ::|::ffff:0.0.0.0|::ffff:169.254.77.1)
                case $* in
                  *"-lnt6"*"sport = :8081 and ( src = ::/128 or src = ::ffff:0.0.0.0/128 or src = ::ffff:169.254.77.1/128 )"*)
                    printf 'tcp LISTEN 0 10 [%s]:8081 [::]:*\n' \
                      "$MOCK_SS_PROGRESS_LISTENER_ADDRESS"
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
            model=${MOCK_UDEV_MODEL-ROG5_recovery}
            omit_model=${MOCK_UDEV_OMIT_MODEL:-0}
            if [ -e "$MOCK_ROOT/fallback-proved" ]; then
              model=${MOCK_FALLBACK_UDEV_MODEL-ROG_Phone_5_Linux_Server}
              omit_model=${MOCK_FALLBACK_UDEV_OMIT_MODEL:-0}
            fi
            printf '%s\n' \
              'ID_VENDOR_ID=1d6b' \
              'ID_MODEL_ID=0104' \
              'ID_NET_DRIVER=cdc_ncm'
            if [ "$omit_model" != 1 ]; then
              printf 'ID_MODEL=%s\n' "$model"
            fi
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
            wrong_uuid=355ee239-f4c2-469f-a74a-6f5bc5e99650
            case "$*" in
              '-g GENERAL.CON-UUID device show usbmock0')
                if [ ! -e "$MOCK_ROOT/profile-deferred" ] ||
                   [ -e "$MOCK_ROOT/profile-restored" ]; then
                  echo "$uuid"
                elif [ "${MOCK_DEFERRED_ACTIVE_UUID:-0}" = 1 ]; then
                  echo "$wrong_uuid"
                elif [ "${MOCK_DEFERRED_STALE_UUID:-0}" = 1 ]; then
                  echo "$uuid"
                elif [ "${MOCK_DEFERRED_DUPLICATE_UUID:-0}" = 1 ]; then
                  printf '%s\n' "$uuid" "$uuid"
                elif [ "${MOCK_DEFERRED_MIXED_UUID:-0}" = 1 ]; then
                  printf '%s\n' "$uuid" "$wrong_uuid"
                elif [ "${MOCK_DEFERRED_EMPTY_LINE_UUID:-0}" = 1 ]; then
                  printf '\n'
                elif [ "${MOCK_DEFERRED_DUPLICATE_EMPTY_UUID:-0}" = 1 ]; then
                  printf '\n\n'
                elif [ "${MOCK_DEFERRED_MIXED_EMPTY_UUID:-0}" = 1 ]; then
                  printf '\n%s\n' "$wrong_uuid"
                elif [ "${MOCK_DEFERRED_PLACEHOLDER_UUID:-0}" = 1 ]; then
                  echo --
                elif [ "${MOCK_DEFERRED_PROFILE_GAP:-0}" = 1 ] &&
                     [ ! -e "$MOCK_ROOT/deferred-profile-gap-consumed" ]; then
                  : >"$MOCK_ROOT/deferred-profile-gap-consumed"
                  echo "$wrong_uuid"
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
            if [ "${MOCK_FIREWALL_DELAY:-0}" != 0 ]; then
              sleep "$MOCK_FIREWALL_DELAY"
            fi
            case " $* " in
              *" --zone=drop --list-all "*)
                drop_header=drop
                drop_interfaces=
                drop_inversion=no
                if [ "${MOCK_DROP_ACTIVE_INTERFACE:-0}" = 1 ]; then
                  drop_header='drop (active)'
                  drop_interfaces=usbmock0
                fi
                if [ "${MOCK_DROP_ICMP_INVERSION:-0}" = 1 ]; then
                  drop_inversion=yes
                fi
                printf '%s\n' \
                  "$drop_header" \
                  '  target: DROP' \
                  "  icmp-block-inversion: $drop_inversion" \
                  "  interfaces: $drop_interfaces" \
                  '  sources: ' \
                  '  services: ' \
                  '  ports: ' \
                  '  protocols: '
                if [ "${MOCK_DROP_MALFORMED_LINE:-0}" = 1 ]; then
                  echo '  malformed line'
                fi
                if [ "${MOCK_DROP_MISSING_FORWARD:-0}" != 1 ]; then
                  echo '  forward: yes'
                fi
                printf '%s\n' \
                  '  masquerade: no' \
                  '  forward-ports: ' \
                  '  source-ports: ' \
                  '  icmp-blocks: ' \
                  '  rich rules: '
                if [ "${MOCK_DROP_RICH_RULE:-0}" = 1 ]; then
                  echo '    rule family="ipv4" priority="-300" destination address="169.254.77.1/32" port port="8080" protocol="tcp" drop'
                fi
                ;;
              *" --get-zones "*) echo 'drop public trusted' ;;
              *" --get-zone-of-interface=usbmock0 "*) echo public ;;
              *" --list-all-zones "*)
                printf '%s\n' \
                  'drop' \
                  '  rich rules: ' \
                  '' \
                  'public' \
                  '  rich rules: '
                if [ "${MOCK_RESIDUAL_AFTER_BUNDLE:-0}" = 1 ] &&
                   [ -e "$MOCK_ROOT/bundle-consumed" ]; then
                  echo '    rule family="ipv4" priority="-300" destination address="169.254.77.1/32" port port="8080" protocol="tcp" drop'
                elif [ "${MOCK_TRANSIENT_FIREWALL_AFTER_FALLBACK:-0}" = 1 ] &&
                     [ -e "$MOCK_ROOT/fallback-proved" ] &&
                     [ ! -e "$MOCK_ROOT/firewall-gap-consumed" ]; then
                  : >"$MOCK_ROOT/firewall-gap-consumed"
                  echo '    rule family="ipv4" priority="-300" destination address="169.254.77.1/32" port port="2049" protocol="tcp" drop'
                elif [ "${MOCK_RESIDUAL_AFTER_NFS:-0}" = 1 ] &&
                     [ -e "$MOCK_ROOT/target-departed" ]; then
                  echo '    rule family="ipv4" priority="-300" destination address="169.254.77.1/32" port port="2049" protocol="tcp" drop'
                fi
                if [ "${MOCK_ALL_ZONES_UNKNOWN:-0}" = 1 ]; then
                  printf '%s\n' '' 'rogue' '  rich rules: '
                fi
                if [ "${MOCK_ALL_ZONES_MISSING_TRUSTED:-0}" != 1 ]; then
                  printf '%s\n' '' 'trusted' '  rich rules: '
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
              [ -f "$XDG_STATE_HOME/rog5-temporary-boot-consumption/$ROG5_STABLE_RECOVERY_PROFILE.record" ]
            fi
            if [ "$1" = preflight ] && [ "$BUNDLE" = {DIAGNOSTIC_BUNDLE} ]; then
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
              if [ "${MOCK_PROFILE_RESTORE_HANG:-0}" = 1 ]; then
                printf '%s\n' "$$" >"$MOCK_ROOT/restore-hang.pid"
                while :; do sleep 1; done
              fi
              if [ "${MOCK_PROFILE_RESTORE_FAIL:-0}" = 1 ]; then
                echo 'FAIL injected fallback profile restoration failure'
                exit 1
              fi
              : >"$MOCK_ROOT/target-departed"
              : >"$MOCK_ROOT/profile-restored"
              echo 'PASS exact Alpine fallback profile restored on usbmock0'
              exit 0
            fi
            [ "$1" = serve-progress-deferred ]
            [ "$#" = 4 ]
            bundle=$2
            manifest=$3
            output=$4
            [ "$output" = "$MOCK_ROOT/evidence" ]
            printf 'bundle:start\n' >>"$MOCK_CALLS"
            echo 'PASS recovery bundle server ready on 169.254.77.1:8080 via usb0'
            if [ "${MOCK_PROGRESS_UNAVAILABLE:-0}" != 1 ]; then
              echo 'PASS recovery progress listener ready on 169.254.77.1:8081 via usb0'
            fi
            while [ ! -e "$MOCK_ROOT/prepare-started" ]; do
              sleep 0.01
            done
            if [ "${MOCK_FETCH_CACHE_HIT:-0}" = 1 ]; then
              while :; do sleep 1; done
            fi
            : >"$MOCK_ROOT/bundle-consumed"
            printf 'bundle:transfer\n' >>"$MOCK_CALLS"
            if [ "${MOCK_PREPARED_BUNDLE_STALL:-0}" = 1 ]; then
              trap ': >"$MOCK_ROOT/profile-deferred"; printf "bundle:terminated\\n" >>"$MOCK_CALLS"; exit 130' TERM INT
              while :; do sleep 1; done
            fi
            if [ "${MOCK_BUNDLE_FORGED_RECEIPT_FAILURE:-0}" = 1 ]; then
              while [ ! -e "$MOCK_ROOT/prepare-observed" ]; do
                sleep 0.01
              done
              echo 'PASS one recovery bundle transfer completed'
              echo 'PASS bounded recovery progress capture completed'
              echo 'PASS bounded recovery progress collection concluded authority=NONE'
              echo 'INFO recovery bundle host network state removed'
              echo 'INFO fallback NetworkManager profile restoration deferred'
              exit 1
            fi
            if [ "${MOCK_PROGRESS_UNAVAILABLE:-0}" = 1 ]; then
              :
            elif [ "${MOCK_PROGRESS_WAIT_FOR_PREPARED:-0}" = 1 ]; then
              while [ ! -e "$output/recovery-progress.stop" ]; do
                sleep 0.01
              done
              session=11111111111111111111111111111111
              request=22222222222222222222222222222222
              records=1
              phases=REQUEST_ACCEPTED
              result=PARTIAL
              truncated=YES
              reason=STOP_REQUESTED
            elif [ "${MOCK_PROGRESS_COMPLETE:-0}" = 1 ]; then
              session=11111111111111111111111111111111
              request=22222222222222222222222222222222
              records=5
              phases='REQUEST_ACCEPTED>FETCH_COMPLETE>VERIFY_COMPLETE>KEXEC_LOAD_COMPLETE>PREPARED_PERSISTED'
              result=COMPLETE
              truncated=NO
              reason=CLEAN_EOF
            else
              session=00000000000000000000000000000000
              request=00000000000000000000000000000000
              records=0
              phases=none
              result=PARTIAL
              truncated=YES
              reason=NO_ADMISSION
            fi
            if [ "${MOCK_PROGRESS_UNAVAILABLE:-0}" != 1 ] &&
               [ "${MOCK_PROGRESS_MISMATCH:-0}" = 1 ]; then
              request=dddddddddddddddddddddddddddddddd
            fi
            if [ "${MOCK_PROGRESS_UNAVAILABLE:-0}" != 1 ] &&
               [ "${MOCK_PROGRESS_ZERO_ID_WITH_RECORDS:-0}" = 1 ]; then
              session=00000000000000000000000000000000
              request=00000000000000000000000000000000
              records=1
              phases=REQUEST_ACCEPTED
              result=PARTIAL
              truncated=YES
              reason=STOP_REQUESTED
            fi
            if [ "${MOCK_PROGRESS_UNAVAILABLE:-0}" != 1 ]; then
              wire_bytes=0
              wire_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
              if [ "$records" != 0 ]; then
                wire_bytes=1
                wire_sha256=2d711642b726b04401627ca9fbac32f5c8530fb1903cc4db02258717921a4881
              fi
              if [ "${MOCK_PROGRESS_IMPOSSIBLE_EMPTY:-0}" = 1 ]; then
                wire_bytes=0
                wire_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
              fi
              umask 077
              printf '%s\n' \
                'format=rog5-recovery-progress-capture-v1' \
                "session=$session" \
                "request=$request" \
                "bundle=$bundle" \
                "manifest_sha256=$manifest" \
                "records=$records" \
                "phases=$phases" \
                "wire_bytes=$wire_bytes" \
                "wire_sha256=$wire_sha256" \
                "result=$result" \
                "truncated=$truncated" \
                "reason=$reason" \
                'authority=NONE' \
                >"$output/recovery-progress.capture"
              if [ "${MOCK_PROGRESS_MALFORMED:-0}" = 1 ]; then
                printf 'malformed\n' >"$output/recovery-progress.capture"
              fi
              echo 'PASS bounded recovery progress capture completed'
              echo 'PASS bounded recovery progress collection concluded authority=NONE'
            fi
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
                if [ "${{MOCK_BUNDLE_FORGED_RECEIPT_FAILURE:-0}}" = 1 ]; then
                  while [ ! -e "$MOCK_ROOT/bundle-consumed" ]; do
                    sleep 0.01
                  done
                  : >"$MOCK_ROOT/prepare-observed"
                  printf 'control:prepared\n' >>"$MOCK_CALLS"
                fi
                if [ "${{MOCK_PREPARED_BUNDLE_STALL:-0}}" = 1 ]; then
                  while [ ! -e "$MOCK_ROOT/bundle-consumed" ]; do
                    sleep 0.01
                  done
                  printf 'control:prepared\n' >>"$MOCK_CALLS"
                  echo 'FAIL exact network-root NFSv4.2 listener was not ready before COMMIT'
                  exit 1
                fi
                printf '{{"commit_fingerprint":"{CYCLE.ZERO_SHA256}","commit_request":"{CYCLE.ZERO_ID}","execution_started":"NO","last_error":"NONE","manifest_sha256":"{MANIFEST}","postmortem_bytes":"0","postmortem_lineage_matches":"0","postmortem_lineage_sha256":"{CYCLE.ZERO_SHA256}","postmortem_lineage_state":"NONE","postmortem_records":"0","postmortem_sha256":"{CYCLE.EMPTY_SHA256}","postmortem_state":"EMPTY","postmortem_tail_hex":"none","prepare_request":"{PREPARE}","prepared_bundle":"%s","request":"{PREPARE}","result":"PREPARED","session":"{SESSION}","state":"PREPARED","verb":"PREPARE","watchdog":"ARMED"}}\n' \
                  "$BUNDLE"
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
                printf '{{"commit_fingerprint":"{COMMIT_FINGERPRINT}","commit_request":"{REQUEST}","execution_started":"NO","last_error":"NONE","manifest_sha256":"{MANIFEST}","postmortem_bytes":"0","postmortem_lineage_matches":"0","postmortem_lineage_sha256":"{CYCLE.ZERO_SHA256}","postmortem_lineage_state":"NONE","postmortem_records":"0","postmortem_sha256":"{CYCLE.EMPTY_SHA256}","postmortem_state":"EMPTY","postmortem_tail_hex":"none","prepare_request":"{PREPARE}","prepared_bundle":"%s","request":"{REQUEST}","result":"CLAIMED","session":"{SESSION}","state":"CLAIMED","verb":"COMMIT_EXEC","watchdog":"ARMED"}}\n{{"session":"{SESSION}","request":"{REQUEST}","manifest_sha256":"{MANIFEST}","target":"%s","state":"TRANSMITTED","outcome":"UNKNOWN"}}\n' \
                  "$BUNDLE" \
                  "$BUNDLE"
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
            if [ "$1" = capture-ssh-postmortem ]; then
              [ "$#" = 9 ]
              [ "$2" = "{self.known_hosts}" ]
              [ "$3" = "{self.ssh_key}" ]
              [ "$4" = "{'1' * 64}" ]
              [ "$5" = "{self.evidence / 'recovery-usb.anchor'}" ]
              [ -f "$5" ]
              [ "$6" -ge 1 ]
              [ "$6" -le 750 ]
              case "$7" in
                {CANDIDATE}|{DIAGNOSTIC_CANDIDATE}) ;;
                *) exit 1 ;;
              esac
              [ "$8" = "{TARGET_BOOT_ID}" ]
              [ "$9" = "{self.evidence / 'fallback-postmortem.record'}" ]
              [ "${{ALLOW_FALLBACK_SSH_CONTROL:-}}" = 1 ]
              [ "${{ALLOW_FALLBACK_SSH_ATIME_EFFECTS:-}}" = 1 ]
              [ "${{ALLOW_PHONE_CREDENTIAL_USE:-}}" = 1 ]
              [ -z "${{ALLOW_TEMPORARY_BOOT+x}}" ]
              [ -e "$MOCK_ROOT/profile-restored" ]
              printf 'fallback:postmortem\n' >>"$MOCK_CALLS"
              if [ "${{MOCK_POSTMORTEM_FAIL:-0}}" = 1 ]; then
                echo 'FAIL injected fallback postmortem rejection'
                exit 1
              fi
              fallback_boot_id={FALLBACK_BOOT_ID}
              if [ "${{MOCK_FALLBACK_REUSE_TARGET_BOOT:-0}}" = 1 ]; then
                fallback_boot_id={TARGET_BOOT_ID}
              fi
              state=EMPTY
              records=0
              bytes=0
              digest={CYCLE.EMPTY_SHA256}
              matches=0
              lineage_records=0
              fatal_total=0
              fatal=0
              correlation=NO_RECORDS
              fatal_state=UNCORRELATED
              if [ "${{MOCK_POSTMORTEM_PRESENT:-0}}" = 1 ]; then
                state=PRESENT
                records=1
                bytes=123
                digest={'a' * 64}
                matches=1
                lineage_records=1
                correlation=MATCH
                fatal_state=NO_FATAL_TOKEN_OBSERVED
              fi
              if [ "${{MOCK_POSTMORTEM_FATAL:-0}}" = 1 ]; then
                state=PRESENT
                records=1
                bytes=123
                digest={'a' * 64}
                matches=1
                lineage_records=1
                fatal_total=1
                fatal=1
                correlation=MATCH
                fatal_state=FATAL_TOKEN_AFTER_LINEAGE
              fi
              if [ "${{MOCK_POSTMORTEM_ORDER_UNKNOWN:-0}}" = 1 ]; then
                state=PRESENT
                records=2
                bytes=246
                digest={'a' * 64}
                matches=1
                lineage_records=1
                fatal_total=1
                correlation=MATCH
                fatal_state=FATAL_TOKEN_PRESENT_ORDER_UNKNOWN
              fi
              if [ "${{MOCK_POSTMORTEM_MULTIPLE:-0}}" = 1 ]; then
                state=PRESENT
                records=2
                bytes=246
                digest={'a' * 64}
                matches=2
                lineage_records=2
                correlation=MATCH_MULTIPLE
                fatal_state=NO_FATAL_TOKEN_OBSERVED
              fi
              candidate=$7
              if [ "${{MOCK_POSTMORTEM_WRONG_CANDIDATE:-0}}" = 1 ]; then
                candidate=wrong-candidate
              fi
              if [ "${{MOCK_POSTMORTEM_WRONG_CLASSIFICATION:-0}}" = 1 ]; then
                correlation=AMBIGUOUS
              fi
              umask 077
              printf '%s\n' \
                'format=rog5-fallback-postmortem-evidence-v2' \
                "expected_candidate=$candidate" \
                "expected_boot_id=$8" \
                "fallback_boot_id=$fallback_boot_id" \
                'usb_location=pci/usb1/1-1/1-1.2' \
                "pstore_state=$state" \
                "pstore_records=$records" \
                "pstore_bytes=$bytes" \
                "pstore_sha256=$digest" \
                'pmic_pon_state=INCONCLUSIVE' \
                'pmic_pon_records=0' \
                'pmic_pon_sha256={CYCLE.EMPTY_SHA256}' \
                'pmic_cycle_entries=0' \
                'pmic_reset_trigger=NONE' \
                'pmic_reset_type=NONE' \
                'pmic_watchdog_signal=INCONCLUSIVE' \
                "lineage_matches=$matches" \
                "lineage_records=$lineage_records" \
                "fatal_tokens_total=$fatal_total" \
                "fatal_after_lineage=$fatal" \
                "correlation=$correlation" \
                "fatal_state=$fatal_state" \
                'nonce={'5' * 32}' \
                'record_sha256={'6' * 64}' \
                'signature_sha256={'7' * 64}' \
                'host_pin_sha256={'8' * 64}' \
                'result=PASS' \
                >"$9"
              echo 'PASS bounded fallback pstore evidence captured over strict SSH correlation='$correlation' fatal_state='$fatal_state
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
            if [ "${{MOCK_FALLBACK_HEALTH_BOOT_CHANGE:-0}}" = 1 ]; then
              fallback_boot_id=bbbbbbbb-cccc-4ddd-8eee-ffffffffffff
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

    def test_repository_checkpoint_refreshes_stale_origin_before_comparison(
        self,
    ) -> None:
        fetched = False
        commands: list[tuple[str, ...]] = []

        def git_result(
            arguments: list[str],
            **_kwargs: object,
        ) -> subprocess.CompletedProcess[str]:
            nonlocal fetched
            command = tuple(arguments[3:])
            commands.append(command)
            output = ""
            if command == ("status", "--porcelain", "--untracked-files=all"):
                pass
            elif command == ("branch", "--show-current"):
                output = "agent/linux-recovery-host\n"
            elif command == (
                "rev-parse",
                "--abbrev-ref",
                "--symbolic-full-name",
                "@{u}",
            ):
                output = "origin/agent/linux-recovery-host\n"
            elif command == (
                "fetch",
                "--no-tags",
                "--prune",
                "origin",
                "refs/heads/agent/linux-recovery-host:"
                "refs/remotes/origin/agent/linux-recovery-host",
            ):
                fetched = True
            elif command == ("rev-parse", "HEAD"):
                output = "stale-checkpoint\n"
            elif command == (
                "rev-parse",
                "origin/agent/linux-recovery-host",
            ):
                output = (
                    "fresh-remote-checkpoint\n"
                    if fetched
                    else "stale-checkpoint\n"
                )
            else:
                self.fail(f"unexpected git command: {command}")
            return subprocess.CompletedProcess(arguments, 0, output, "")

        with mock.patch.object(CYCLE, "run_capture", side_effect=git_result):
            with self.assertRaisesRegex(
                CYCLE.CycleError,
                "local and remote-tracking checkpoints differ",
            ):
                CYCLE.verify_repository_checkpoint(Path("/usr/bin/git"))

        self.assertTrue(fetched)
        fetch_index = next(
            index
            for index, command in enumerate(commands)
            if command and command[0] == "fetch"
        )
        remote_index = commands.index(
            ("rev-parse", "origin/agent/linux-recovery-host")
        )
        self.assertLess(fetch_index, remote_index)

    def control_records(
        self,
        *,
        postmortem: dict[str, str] | None = None,
    ) -> tuple[dict[str, str], dict[str, str], dict[str, object]]:
        selected = postmortem or {
            "postmortem_state": "PRESENT",
            "postmortem_records": "1",
            "postmortem_bytes": "472926",
            "postmortem_sha256": "4" * 64,
            "postmortem_tail_hex": "00ff",
        }
        if selected["postmortem_state"] == "PRESENT":
            lineage = {
                "postmortem_lineage_state": "UNIQUE",
                "postmortem_lineage_matches": "1",
                "postmortem_lineage_sha256": "6" * 64,
            }
        else:
            lineage = {
                "postmortem_lineage_state": "NONE",
                "postmortem_lineage_matches": "0",
                "postmortem_lineage_sha256": CYCLE.ZERO_SHA256,
            }
        evidence = {**lineage, **selected}
        prepared = {
            "commit_fingerprint": CYCLE.ZERO_SHA256,
            "commit_request": CYCLE.ZERO_ID,
            "execution_started": "NO",
            "last_error": "NONE",
            "manifest_sha256": MANIFEST,
            **evidence,
            "prepare_request": PREPARE,
            "prepared_bundle": DIAGNOSTIC_BUNDLE,
            "request": PREPARE,
            "result": "PREPARED",
            "session": SESSION,
            "state": "PREPARED",
            "verb": "PREPARE",
            "watchdog": "ARMED",
        }
        committed = {
            "commit_fingerprint": CYCLE.commit_request_fingerprint(
                SESSION,
                REQUEST,
                PREPARE,
                MANIFEST,
            ),
            "commit_request": REQUEST,
            "execution_started": "NO",
            "last_error": "NONE",
            "manifest_sha256": MANIFEST,
            **evidence,
            "prepare_request": PREPARE,
            "prepared_bundle": DIAGNOSTIC_BUNDLE,
            "request": REQUEST,
            "result": "CLAIMED",
            "session": SESSION,
            "state": "CLAIMED",
            "verb": "COMMIT_EXEC",
            "watchdog": "ARMED",
        }
        intent: dict[str, object] = {
            "created_unix_ns": 1,
            "manifest_sha256": MANIFEST,
            "outcome": "UNKNOWN",
            "request": REQUEST,
            "session": SESSION,
            "state": "TRANSMITTED",
            "target": DIAGNOSTIC_BUNDLE,
        }
        return prepared, committed, intent

    def parse_control_records(
        self,
        prepared: dict[str, object],
        committed: dict[str, object],
        intent: dict[str, object],
    ) -> tuple[CYCLE.Intent, str]:
        path = self.fixture.root / "control-parser.log"
        path.write_text(
            "\n".join(
                (
                    json.dumps(prepared, sort_keys=True, separators=(",", ":")),
                    json.dumps(committed, sort_keys=True, separators=(",", ":")),
                    json.dumps(intent, sort_keys=True, separators=(",", ":")),
                    "PASS recovery accepted one commit; outcome remains UNKNOWN",
                    "",
                )
            ),
            encoding="utf-8",
        )
        return CYCLE.parse_control_log(
            path,
            MANIFEST,
            DIAGNOSTIC_BUNDLE,
        )

    def test_control_parser_accepts_full_correlated_postmortem_contract(self):
        states = (
            {
                "postmortem_state": "PRESENT",
                "postmortem_records": "64",
                "postmortem_bytes": "4194304",
                "postmortem_sha256": "4" * 64,
                "postmortem_tail_hex": "00" * 512,
            },
            {
                "postmortem_state": "EMPTY",
                "postmortem_records": "0",
                "postmortem_bytes": "0",
                "postmortem_sha256": CYCLE.EMPTY_SHA256,
                "postmortem_tail_hex": "none",
            },
            {
                "postmortem_state": "UNAVAILABLE",
                "postmortem_records": "0",
                "postmortem_bytes": "0",
                "postmortem_sha256": CYCLE.ZERO_SHA256,
                "postmortem_tail_hex": "none",
            },
            {
                "postmortem_state": "PRESENT",
                "postmortem_records": "1",
                "postmortem_bytes": "1",
                "postmortem_sha256": "5" * 64,
                # recovery-init tails its aggregate snapshot, which includes
                # record metadata in addition to the pstore payload bytes.
                "postmortem_tail_hex": "7265636f72643d702d31",
            },
        )
        for postmortem in states:
            with self.subTest(state=postmortem["postmortem_state"]):
                records = self.control_records(postmortem=postmortem)
                intent, prepare_request = self.parse_control_records(*records)
                self.assertEqual(intent.session, SESSION)
                self.assertEqual(intent.request, REQUEST)
                self.assertEqual(prepare_request, PREPARE)

    def test_commit_fingerprint_matches_canonical_protocol_fixture(self):
        # The same literal is independently emitted by the compiled native C
        # responder in test_commit_fingerprint_matches_canonical_wire_vector.
        self.assertEqual(
            CYCLE.commit_request_fingerprint(
                SESSION,
                REQUEST,
                PREPARE,
                MANIFEST,
            ),
            "d2552f9cc0e0f2bf67cb1f18ad01b2be3fd592a07dcdb23c49ba4d35a15b8552",
        )

    def test_control_parser_rejects_missing_or_extra_response_fields(self):
        for response_index in (0, 1):
            for field in sorted(CYCLE.CONTROL_RESPONSE_FIELDS):
                with self.subTest(response=response_index, missing=field):
                    records = list(self.control_records())
                    records[response_index] = dict(records[response_index])
                    del records[response_index][field]
                    with self.assertRaisesRegex(
                        CYCLE.CycleError,
                        "recovery (PREPARE|COMMIT) evidence is inconsistent",
                    ):
                        self.parse_control_records(*records)
            with self.subTest(response=response_index, extra="unexpected"):
                records = list(self.control_records())
                records[response_index] = dict(records[response_index])
                records[response_index]["unexpected"] = "field"
                with self.assertRaisesRegex(
                    CYCLE.CycleError,
                    "recovery (PREPARE|COMMIT) evidence is inconsistent",
                ):
                    self.parse_control_records(*records)

    def test_control_parser_rejects_malformed_postmortem_contract(self):
        mutations = (
            ("postmortem_state", "UNKNOWN"),
            ("postmortem_records", "01"),
            ("postmortem_records", "65"),
            ("postmortem_bytes", "00"),
            ("postmortem_bytes", "4194305"),
            ("postmortem_sha256", "g" * 64),
            ("postmortem_sha256", CYCLE.EMPTY_SHA256),
            ("postmortem_tail_hex", "0"),
            ("postmortem_tail_hex", "00" * 513),
            ("postmortem_lineage_state", "UNKNOWN"),
            ("postmortem_lineage_matches", "01"),
            ("postmortem_lineage_matches", "65536"),
            ("postmortem_lineage_sha256", "g" * 64),
            ("postmortem_lineage_state", "REPEATED"),
            ("postmortem_lineage_matches", "2"),
            ("postmortem_lineage_sha256", CYCLE.ZERO_SHA256),
        )
        for field, value in mutations:
            with self.subTest(field=field, value=value[:16]):
                records = list(self.control_records())
                records[0] = dict(records[0])
                records[0][field] = value
                with self.assertRaisesRegex(
                    CYCLE.CycleError,
                    "recovery PREPARE evidence is inconsistent",
                ):
                    self.parse_control_records(*records)

        inconsistent_states = (
            {
                "postmortem_state": "PRESENT",
                "postmortem_records": "0",
                "postmortem_bytes": "0",
                "postmortem_sha256": CYCLE.ZERO_SHA256,
                "postmortem_tail_hex": "none",
            },
            {
                "postmortem_state": "EMPTY",
                "postmortem_records": "0",
                "postmortem_bytes": "0",
                "postmortem_sha256": CYCLE.ZERO_SHA256,
                "postmortem_tail_hex": "none",
            },
            {
                "postmortem_state": "UNAVAILABLE",
                "postmortem_records": "0",
                "postmortem_bytes": "0",
                "postmortem_sha256": CYCLE.EMPTY_SHA256,
                "postmortem_tail_hex": "none",
            },
        )
        for postmortem in inconsistent_states:
            with self.subTest(inconsistent=postmortem["postmortem_state"]):
                records = self.control_records(postmortem=postmortem)
                with self.assertRaisesRegex(
                    CYCLE.CycleError,
                    "recovery PREPARE evidence is inconsistent",
                ):
                    self.parse_control_records(*records)

    def test_control_parser_rejects_cross_response_postmortem_change(self):
        records = list(self.control_records())
        records[1] = dict(records[1])
        records[1].update(
            {
                "postmortem_state": "EMPTY",
                "postmortem_records": "0",
                "postmortem_bytes": "0",
                "postmortem_sha256": CYCLE.EMPTY_SHA256,
                "postmortem_tail_hex": "none",
            }
        )
        with self.assertRaisesRegex(
            CYCLE.CycleError,
            "recovery COMMIT evidence is inconsistent",
        ):
            self.parse_control_records(*records)

    def test_control_parser_rejects_transaction_identity_mutations(self):
        prepared_mutations = {
            "session": CYCLE.ZERO_ID,
            "request": CYCLE.ZERO_ID,
            "verb": "STATUS",
            "result": "OK",
            "state": "CLAIMED",
            "prepared_bundle": "wrong-bundle",
            "manifest_sha256": "6" * 64,
            "prepare_request": "7" * 32,
            "commit_request": REQUEST,
            "commit_fingerprint": "8" * 64,
            "execution_started": "YES",
            "watchdog": "INVALID",
            "last_error": "FETCH_FAILED",
        }
        committed_mutations = {
            "session": CYCLE.ZERO_ID,
            "request": CYCLE.ZERO_ID,
            "verb": "STATUS",
            "result": "PREPARED",
            "state": "PREPARED",
            "prepared_bundle": "wrong-bundle",
            "manifest_sha256": "6" * 64,
            "prepare_request": "7" * 32,
            "commit_request": "8" * 32,
            "commit_fingerprint": "8" * 64,
            "execution_started": "YES",
            "watchdog": "INVALID",
            "last_error": "EXEC_FAILED",
        }
        for response_index, mutations, marker in (
            (0, prepared_mutations, "PREPARE"),
            (1, committed_mutations, "COMMIT"),
        ):
            for field, value in mutations.items():
                with self.subTest(response=marker, field=field):
                    records = list(self.control_records())
                    records[response_index] = dict(records[response_index])
                    records[response_index][field] = value
                    with self.assertRaisesRegex(
                        CYCLE.CycleError,
                        f"recovery {marker} evidence is inconsistent",
                    ):
                        self.parse_control_records(*records)

        records = list(self.control_records())
        records[1] = dict(records[1])
        records[1].update(
            {
                "request": PREPARE,
                "commit_request": PREPARE,
                "commit_fingerprint": CYCLE.commit_request_fingerprint(
                    SESSION,
                    PREPARE,
                    PREPARE,
                    MANIFEST,
                ),
            }
        )
        records[2] = dict(records[2])
        records[2]["request"] = PREPARE
        with self.assertRaisesRegex(
            CYCLE.CycleError,
            "recovery COMMIT evidence is inconsistent",
        ):
            self.parse_control_records(*records)

    def test_live_diagnostic_actions_fail_before_credentials_without_guards(
        self,
    ):
        for action in (
            "diagnostic-key-preflight",
            "diagnostic-preflight",
            "diagnostic-run",
        ):
            with self.subTest(action=action):
                result = subprocess.run(
                    [str(RUNNER), action],
                    env={
                        "PATH": os.environ["PATH"],
                        "HOME": str(self.fixture.root / "absent-home"),
                        "ROG5_DEPLOYMENT_SSH_KEY": str(
                            self.fixture.root / "poison-key"
                        ),
                    },
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                    timeout=5,
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                expected = (
                    "one-shot lifecycle requires exact fresh guards"
                    if action == "diagnostic-run"
                    else "deployment-key admission requires exact fresh guards"
                )
                self.assertIn(expected, result.stderr)
                self.assertFalse(
                    (self.fixture.root / "poison-key").exists()
                )

        for incomplete_test_environment in (
            {"ROG5_LIVE_CYCLE_OFFLINE_TEST": "1"},
            {
                "ROG5_LIVE_CYCLE_OFFLINE_TEST": "1",
                "ROG5_LIVE_CYCLE_TEST_ROOT": "relative-test-root",
            },
        ):
            with self.subTest(environment=incomplete_test_environment):
                result = subprocess.run(
                    [str(RUNNER), "diagnostic-run"],
                    env={
                        "PATH": os.environ["PATH"],
                        "HOME": str(self.fixture.root / "absent-home"),
                        **incomplete_test_environment,
                    },
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                    timeout=5,
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn(
                    "one-shot lifecycle requires exact fresh guards",
                    result.stderr,
                )

    def test_ncm_model_allowlist_is_exact(self):
        self.assertEqual(
            CYCLE.ROG5_NCM_MODELS,
            frozenset(
                {
                    "ROG5_recovery",
                    "ROG5_network_root",
                    "ROG5_diagnostic_network_root",
                    "ROG_Phone_5_Linux_Server",
                }
            ),
        )

    def test_each_exact_ncm_model_is_classified(self):
        for model in sorted(CYCLE.ROG5_NCM_MODELS):
            with self.subTest(model=model):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run(
                    "diagnostic-preflight",
                    MOCK_UDEV_MODEL=model,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_production_cleanup_uses_privileged_export_proof(self):
        with mock.patch.dict(
            os.environ,
            self.fixture.environment(),
            clear=False,
        ):
            dependencies = CYCLE.Dependencies.from_environment()
        dependencies = replace(dependencies, offline=False)
        inputs = CYCLE.Inputs(
            manifest_sha256=MANIFEST,
            ssh_key=self.fixture.ssh_key,
            ssh_public_key_sha256="4" * 64,
            root_package_sha256=PACKAGE_SHA256,
            candidate_record=self.fixture.candidate,
            candidate_sha256=CANDIDATE_SHA256,
            fallback_known_hosts=self.fixture.known_hosts,
            evidence_dir=self.fixture.evidence,
            fallback_timeout=750,
        )
        cycle = CYCLE.LiveCycle(dependencies, inputs)
        self.fixture.nfs_exports.chmod(0o000)
        export_proof = ["PASS host NFS export table is empty\n"]

        def capture(arguments, **_kwargs):
            if arguments == [
                str(dependencies.network_root_server),
                "inspect",
            ]:
                return subprocess.CompletedProcess(
                    arguments,
                    0,
                    export_proof[0],
                    "",
                )
            return subprocess.CompletedProcess(arguments, 0, "", "")

        with (
            mock.patch.object(CYCLE, "run_capture", side_effect=capture) as run,
            mock.patch.object(cycle, "rog5_ncm_interfaces", return_value=()),
            mock.patch.object(
                cycle,
                "capture_host_snapshot",
                return_value=CYCLE.HostSnapshot(False, "0"),
            ),
        ):
            cycle.verify_host_clean(deadline=time.monotonic() + 5)
            export_proof[0] += "unexpected trailing output\n"
            with self.assertRaisesRegex(
                CYCLE.CycleError,
                "host NFS export proof is not canonical",
            ):
                cycle.verify_host_clean(deadline=time.monotonic() + 5)
        self.assertIn(
            mock.call(
                [str(dependencies.network_root_server), "inspect"],
                timeout=mock.ANY,
            ),
            run.call_args_list,
        )

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

    def test_fallback_postmortem_evidence_is_exact_and_correlated(self):
        anchor = self.fixture.evidence / "postmortem.anchor"
        anchor.write_text(
            "format=rog5-minimal-headless-usb-anchor-v1\n"
            f"host_boot_id={TARGET_BOOT_ID}\n"
            f"created_unix={self.fixture.anchor_created}\n"
            "usb_location=pci/usb1/1-1/1-1.2\n"
            "recovery_vendor=1d6b\n"
            "recovery_product_id=0104\n"
            "recovery_product=ROG5 recovery\n",
            encoding="ascii",
        )
        anchor.chmod(0o600)
        with mock.patch.dict(
            os.environ,
            self.fixture.environment(),
            clear=False,
        ):
            dependencies = CYCLE.Dependencies.from_environment()

        baseline = {
            "format": "rog5-fallback-postmortem-evidence-v2",
            "expected_candidate": CANDIDATE,
            "expected_boot_id": TARGET_BOOT_ID,
            "fallback_boot_id": FALLBACK_BOOT_ID,
            "usb_location": "pci/usb1/1-1/1-1.2",
            "pstore_state": "EMPTY",
            "pstore_records": "0",
            "pstore_bytes": "0",
            "pstore_sha256": CYCLE.EMPTY_SHA256,
            "pmic_pon_state": "INCONCLUSIVE",
            "pmic_pon_records": "0",
            "pmic_pon_sha256": CYCLE.EMPTY_SHA256,
            "pmic_cycle_entries": "0",
            "pmic_reset_trigger": "NONE",
            "pmic_reset_type": "NONE",
            "pmic_watchdog_signal": "INCONCLUSIVE",
            "lineage_matches": "0",
            "lineage_records": "0",
            "fatal_tokens_total": "0",
            "fatal_after_lineage": "0",
            "correlation": "NO_RECORDS",
            "fatal_state": "UNCORRELATED",
            "nonce": "5" * 32,
            "record_sha256": "6" * 64,
            "signature_sha256": "7" * 64,
            "host_pin_sha256": "8" * 64,
            "result": "PASS",
        }

        def write(name: str, updates: dict[str, str]) -> Path:
            values = {**baseline, **updates}
            path = self.fixture.evidence / f"postmortem-{name}.record"
            path.write_text(
                "".join(
                    f"{field}={values[field]}\n"
                    for field in CYCLE.FALLBACK_POSTMORTEM_FIELDS
                ),
                encoding="ascii",
            )
            path.chmod(0o600)
            return path

        canonical = (
            ("empty", {}),
            (
                "unavailable",
                {
                    "pstore_state": "UNAVAILABLE",
                    "pstore_sha256": CYCLE.ZERO_SHA256,
                    "correlation": "UNAVAILABLE",
                },
            ),
            (
                "zero-byte-record",
                {
                    "pstore_state": "PRESENT",
                    "pstore_records": "1",
                    "pstore_bytes": "0",
                    "pstore_sha256": "a" * 64,
                    "correlation": "NO_LINEAGE",
                },
            ),
            (
                "match",
                {
                    "pstore_state": "PRESENT",
                    "pstore_records": "1",
                    "pstore_bytes": "123",
                    "pstore_sha256": "a" * 64,
                    "lineage_matches": "1",
                    "lineage_records": "1",
                    "correlation": "MATCH",
                    "fatal_state": "NO_FATAL_TOKEN_OBSERVED",
                },
            ),
            (
                "pmic-exact-watchdog",
                {
                    "pmic_pon_state": "EXACT",
                    "pmic_pon_records": "8",
                    "pmic_pon_sha256": "b" * 64,
                    "pmic_cycle_entries": "5",
                    "pmic_reset_trigger": "PMIC_WATCHDOG_S2",
                    "pmic_reset_type": "HARD_RESET",
                    "pmic_watchdog_signal": "PRESENT",
                },
            ),
            (
                "fatal",
                {
                    "pstore_state": "PRESENT",
                    "pstore_records": "1",
                    "pstore_bytes": "123",
                    "pstore_sha256": "a" * 64,
                    "lineage_matches": "1",
                    "lineage_records": "1",
                    "fatal_tokens_total": "1",
                    "fatal_after_lineage": "1",
                    "correlation": "MATCH",
                    "fatal_state": "FATAL_TOKEN_AFTER_LINEAGE",
                },
            ),
            (
                "order-unknown",
                {
                    "pstore_state": "PRESENT",
                    "pstore_records": "2",
                    "pstore_bytes": "246",
                    "pstore_sha256": "a" * 64,
                    "lineage_matches": "1",
                    "lineage_records": "1",
                    "fatal_tokens_total": "1",
                    "correlation": "MATCH",
                    "fatal_state": "FATAL_TOKEN_PRESENT_ORDER_UNKNOWN",
                },
            ),
            (
                "multiple",
                {
                    "pstore_state": "PRESENT",
                    "pstore_records": "2",
                    "pstore_bytes": "246",
                    "pstore_sha256": "a" * 64,
                    "lineage_matches": "2",
                    "lineage_records": "2",
                    "correlation": "MATCH_MULTIPLE",
                    "fatal_state": "NO_FATAL_TOKEN_OBSERVED",
                },
            ),
        )
        for name, updates in canonical:
            with self.subTest(canonical=name):
                self.assertEqual(
                    CYCLE.verify_fallback_postmortem_evidence(
                        write(name, updates),
                        anchor,
                        CANDIDATE,
                        TARGET_BOOT_ID,
                        dependencies,
                    ),
                    FALLBACK_BOOT_ID,
                )

        mutations = {
            "candidate": {"expected_candidate": "wrong"},
            "target-boot": {"expected_boot_id": FALLBACK_BOOT_ID},
            "fallback-boot": {"fallback_boot_id": TARGET_BOOT_ID},
            "location": {"usb_location": "pci/usb1/1-1/1-1.9"},
            "proof": {"record_sha256": CYCLE.ZERO_SHA256},
            "leading-zero": {"pstore_records": "00"},
            "state": {
                "pstore_state": "PRESENT",
                "pstore_sha256": "a" * 64,
            },
            "correlation": {"correlation": "MATCH"},
            "fatal": {"fatal_state": "FATAL_TOKEN_AFTER_LINEAGE"},
            "pmic-unavailable-digest": {
                "pmic_pon_state": "UNAVAILABLE",
                "pmic_pon_sha256": CYCLE.EMPTY_SHA256,
            },
            "pmic-watchdog-contradiction": {
                "pmic_pon_state": "EXACT",
                "pmic_pon_records": "8",
                "pmic_pon_sha256": "b" * 64,
                "pmic_cycle_entries": "5",
                "pmic_reset_trigger": "PMIC_WATCHDOG_S2",
                "pmic_reset_type": "HARD_RESET",
                "pmic_watchdog_signal": "ABSENT",
            },
            "pmic-unknown-is-not-exact": {
                "pmic_pon_state": "EXACT",
                "pmic_pon_records": "8",
                "pmic_pon_sha256": "b" * 64,
                "pmic_cycle_entries": "5",
                "pmic_reset_trigger": "UNKNOWN",
                "pmic_reset_type": "UNKNOWN",
                "pmic_watchdog_signal": "ABSENT",
            },
            "fatal-after-total": {
                "pstore_state": "PRESENT",
                "pstore_records": "1",
                "pstore_bytes": "123",
                "pstore_sha256": "a" * 64,
                "lineage_matches": "1",
                "lineage_records": "1",
                "fatal_after_lineage": "1",
            },
        }
        for name, updates in mutations.items():
            with self.subTest(mutation=name):
                with self.assertRaises(CYCLE.CycleError):
                    CYCLE.verify_fallback_postmortem_evidence(
                        write(f"bad-{name}", updates),
                        anchor,
                        CANDIDATE,
                        TARGET_BOOT_ID,
                        dependencies,
                    )

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

    def test_temporary_boot_claim_is_durable_and_non_retryable(self):
        with mock.patch.dict(
            os.environ,
            self.fixture.environment(),
            clear=False,
        ):
            dependencies = CYCLE.Dependencies.from_environment()
            inputs = CYCLE.Inputs(
                manifest_sha256=CLAIM_CONSUMER.MANIFEST_SHA256,
                ssh_key=self.fixture.ssh_key,
                ssh_public_key_sha256="4" * 64,
                root_package_sha256=PACKAGE_SHA256,
                candidate_record=self.fixture.candidate,
                candidate_sha256=CANDIDATE_SHA256,
                fallback_known_hosts=self.fixture.known_hosts,
                evidence_dir=self.fixture.evidence,
                fallback_timeout=750,
            )
            cycle = CYCLE.LiveCycle(
                dependencies,
                inputs,
                CYCLE.LEGACY_DIAGNOSTIC_CYCLE_PROFILE,
            )
            production_cycle = CYCLE.LiveCycle(
                replace(dependencies, offline=False),
                inputs,
                CYCLE.LEGACY_DIAGNOSTIC_CYCLE_PROFILE,
            )
            with mock.patch.dict(
                os.environ,
                {
                    "HOME": "/hostile-home",
                    "XDG_STATE_HOME": "/hostile-state",
                },
            ):
                self.assertEqual(
                    production_cycle.temporary_boot_consumption_root(),
                    CLAIM_CONSUMER.canonical_claim_root(),
                )
            cycle.assert_temporary_boot_unconsumed()
            cycle.claim_temporary_boot()
            record = cycle.temporary_boot_consumption_path()
            self.assertEqual(record.read_bytes(), CLAIM_CONSUMER.EXPECTED)
            self.assertEqual(record.parent.stat().st_mode & 0o777, 0o700)
            self.assertEqual(record.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                record.read_text(encoding="ascii"),
                "format=rog5-temporary-boot-consumption-v1\n"
                f"recovery_profile={DIAGNOSTIC_RECOVERY_PROFILE}\n"
                f"candidate={DIAGNOSTIC_CANDIDATE}\n"
                f"manifest_sha256={CLAIM_CONSUMER.MANIFEST_SHA256}\n"
                "state=BOOT_CLAIMED\n",
            )
            with self.assertRaisesRegex(
                CYCLE.CycleError,
                "already consumed on this host",
            ):
                cycle.assert_temporary_boot_unconsumed()
            with self.assertRaisesRegex(
                CYCLE.CycleError,
                "already consumed on this host",
            ):
                cycle.claim_temporary_boot()
            entered = cycle.temporary_boot_entered_path()
            record.rename(entered)
            with self.assertRaisesRegex(
                CYCLE.CycleError,
                "already consumed on this host",
            ):
                cycle.assert_temporary_boot_unconsumed()
            with self.assertRaisesRegex(
                CYCLE.CycleError,
                "already consumed on this host",
            ):
                cycle.claim_temporary_boot()
            canonical_anchor = self.fixture.root / "canonical-account-home"
            canonical_anchor.mkdir(mode=0o700)
            self.assertNotEqual(canonical_anchor, record.parent.parent)
            guard = canonical_anchor / (
                ".rog5-temporary-boot-consumption."
                f"{DIAGNOSTIC_RECOVERY_PROFILE}.entered"
            )
            guard.write_bytes(CLAIM_CONSUMER.EXPECTED)
            guard.chmod(0o600)
            with mock.patch.object(
                CYCLE.CLAIM_CONSUMER,
                "canonical_claim_anchor",
                return_value=canonical_anchor,
            ), mock.patch.dict(
                os.environ, {"ROG5_EXTERNAL_BOOT_CLAIM": "1"}
            ):
                cycle.claim_temporary_boot()

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
        self.assertFalse(
            (
                self.fixture.xdg_state
                / "rog5-temporary-boot-consumption"
                / f"{RECOVERY_PROFILE}.record"
            ).exists()
        )

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

    def test_failed_run_preflight_does_not_consume_temporary_boot(self):
        result = self.fixture.run(
            "run",
            MOCK_SS_LISTENER_ADDRESS="0.0.0.0",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("host listener remains on TCP port 8080", result.stderr)
        self.assertNotIn("live:boot", self.fixture.call_lines())
        self.assertFalse(
            (
                self.fixture.xdg_state
                / "rog5-temporary-boot-consumption"
                / f"{RECOVERY_PROFILE}.record"
            ).exists()
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

    def test_preflight_rejects_conflicting_progress_port(self):
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
                    MOCK_SS_PROGRESS_LISTENER_ADDRESS=address,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "host listener remains on TCP port 8081",
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
            calls.index("fallback:postmortem"),
        )
        self.assertLess(
            calls.index("fallback:postmortem"),
            calls.index("fallback:ssh-preflight"),
        )
        self.assertLess(
            calls.index("fallback:ssh-preflight"),
            calls.index("control:resolve:TARGET_ACCEPTED"),
        )
        self.assertEqual(calls.count("bundle:restore-fallback"), 1)
        self.assertEqual(calls.count("fallback:postmortem"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)
        self.assertTrue(
            (self.fixture.evidence / "target-known-hosts").is_file()
        )
        self.assertTrue(
            (self.fixture.evidence / "fallback-identity.record").is_file()
        )
        self.assertTrue(
            (self.fixture.evidence / "fallback-postmortem.record").is_file()
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
        progress = (
            self.fixture.evidence / "recovery-progress-assessment.record"
        ).read_text(encoding="ascii")
        self.assertIn("capture_result=PARTIAL\n", progress)
        self.assertIn("correlation=UNAVAILABLE\n", progress)
        self.assertIn("authority=NONE\n", progress)

    def test_postmortem_match_and_fatal_classifications_are_retained(self):
        cases = (
            (
                "MOCK_POSTMORTEM_PRESENT",
                "correlation=MATCH\n",
                "fatal_state=NO_FATAL_TOKEN_OBSERVED\n",
            ),
            (
                "MOCK_POSTMORTEM_FATAL",
                "correlation=MATCH\n",
                "fatal_state=FATAL_TOKEN_AFTER_LINEAGE\n",
            ),
            (
                "MOCK_POSTMORTEM_ORDER_UNKNOWN",
                "correlation=MATCH\n",
                "fatal_state=FATAL_TOKEN_PRESENT_ORDER_UNKNOWN\n",
            ),
            (
                "MOCK_POSTMORTEM_MULTIPLE",
                "correlation=MATCH_MULTIPLE\n",
                "fatal_state=NO_FATAL_TOKEN_OBSERVED\n",
            ),
        )
        for variable, correlation, fatal_state in cases:
            with self.subTest(variable=variable):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run("run", **{variable: "1"})
                self.assertEqual(result.returncode, 0, result.stderr)
                evidence = (
                    self.fixture.evidence / "fallback-postmortem.record"
                ).read_text(encoding="ascii")
                self.assertIn(correlation, evidence)
                self.assertIn(fatal_state, evidence)
                calls = self.fixture.call_lines()
                self.assertEqual(calls.count("fallback:postmortem"), 1)
                self.assertEqual(calls.count("fallback:ssh-preflight"), 1)

    def test_postmortem_failure_or_mutation_stops_before_fallback_health(self):
        cases = (
            ("MOCK_POSTMORTEM_FAIL", "fallback-postmortem failed"),
            (
                "MOCK_POSTMORTEM_WRONG_CANDIDATE",
                "postmortem evidence identity is not exact",
            ),
            (
                "MOCK_POSTMORTEM_WRONG_CLASSIFICATION",
                "postmortem evidence state is inconsistent",
            ),
        )
        for variable, message in cases:
            with self.subTest(variable=variable):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run("run", **{variable: "1"})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertIn("intent remains UNKNOWN", result.stderr)
                calls = self.fixture.call_lines()
                self.assertEqual(calls.count("fallback:postmortem"), 1)
                self.assertEqual(calls.count("fallback:ssh-preflight"), 0)

    def test_fallback_boot_identity_cannot_change_after_postmortem(self):
        result = self.fixture.run(
            "run",
            MOCK_FALLBACK_HEALTH_BOOT_CHANGE="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "fallback boot identity changed after postmortem capture",
            result.stderr,
        )
        self.assertIn("intent remains UNKNOWN", result.stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("fallback:postmortem"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)

    def test_prepared_stops_advisory_stream_before_nfs_without_authority(self):
        result = self.fixture.run(
            "run",
            MOCK_PROGRESS_WAIT_FOR_PREPARED="1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(
            (self.fixture.evidence / "recovery-progress.stop").exists()
        )
        capture = (
            self.fixture.evidence / "recovery-progress.capture"
        ).read_text(encoding="ascii")
        self.assertIn("reason=STOP_REQUESTED\n", capture)
        assessment = (
            self.fixture.evidence / "recovery-progress-assessment.record"
        ).read_text(encoding="ascii")
        self.assertIn("capture_result=PARTIAL\n", assessment)
        self.assertIn("correlation=MATCH\n", assessment)
        self.assertIn("authority=NONE\n", assessment)
        calls = self.fixture.call_lines()
        self.assertLess(calls.index("bundle:clean"), calls.index("nfs:start"))
        self.assertEqual(calls.count("control:prepare-commit"), 1)

    def test_missing_progress_listener_and_capture_do_not_gate_commit(self):
        result = self.fixture.run("run", MOCK_PROGRESS_UNAVAILABLE="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(
            (self.fixture.evidence / "recovery-progress.capture").exists()
        )
        assessment = (
            self.fixture.evidence / "recovery-progress-assessment.record"
        ).read_text(encoding="ascii")
        self.assertIn("capture_result=MISSING\n", assessment)
        self.assertIn("correlation=UNAVAILABLE\n", assessment)
        self.assertIn("reason=MISSING\n", assessment)
        self.assertIn("authority=NONE\n", assessment)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(calls.count("control:resolve:TARGET_ACCEPTED"), 1)

    def test_complete_progress_correlates_only_after_commit(self):
        result = self.fixture.run("run", MOCK_PROGRESS_COMPLETE="1")
        self.assertEqual(result.returncode, 0, result.stderr)
        assessment = (
            self.fixture.evidence / "recovery-progress-assessment.record"
        ).read_text(encoding="ascii")
        self.assertIn("capture_result=COMPLETE\n", assessment)
        self.assertIn("correlation=MATCH\n", assessment)
        self.assertIn("reason=CLEAN_EOF\n", assessment)
        self.assertIn("authority=NONE\n", assessment)

    def test_bad_progress_evidence_never_gates_or_authorizes_commit(self):
        for name, update, expected in (
            ("mismatch", "MOCK_PROGRESS_MISMATCH", "MISMATCH"),
            ("malformed", "MOCK_PROGRESS_MALFORMED", "UNAVAILABLE"),
            (
                "impossible-empty-complete",
                "MOCK_PROGRESS_IMPOSSIBLE_EMPTY",
                "UNAVAILABLE",
            ),
            (
                "impossible-zero-id-records",
                "MOCK_PROGRESS_ZERO_ID_WITH_RECORDS",
                "UNAVAILABLE",
            ),
        ):
            with self.subTest(name=name):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run("run", **{update: "1"})
                self.assertEqual(result.returncode, 0, result.stderr)
                assessment = (
                    self.fixture.evidence
                    / "recovery-progress-assessment.record"
                ).read_text(encoding="ascii")
                self.assertIn(f"correlation={expected}\n", assessment)
                self.assertIn("authority=NONE\n", assessment)
                calls = self.fixture.call_lines()
                self.assertEqual(calls.count("control:prepare-commit"), 1)
                self.assertEqual(
                    calls.count("control:resolve:TARGET_ACCEPTED"), 1
                )

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
            calls.index("live:preflight"),
            calls.index("live:boot"),
        )
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

        def boolean_carrier(document: dict[str, object]) -> None:
            snapshot = document["transport_snapshots"][0]
            snapshot.update(
                {
                    "state": "present",
                    "interface": "usb0",
                    "carrier": True,
                    "operstate": "up",
                    "rx_bytes": 0,
                    "rx_dropped": 0,
                    "rx_errors": 0,
                    "rx_packets": 0,
                    "tx_bytes": 0,
                    "tx_dropped": 0,
                    "tx_errors": 0,
                    "tx_packets": 0,
                }
            )

        def overflowing_ncm_counter(document: dict[str, object]) -> None:
            snapshot = document["transport_snapshots"][0]
            snapshot.update(
                {
                    "state": "present",
                    "interface": "usb0",
                    "carrier": 1,
                    "operstate": "up",
                    "rx_bytes": 1 << 64,
                    "rx_dropped": 0,
                    "rx_errors": 0,
                    "rx_packets": 0,
                    "tx_bytes": 0,
                    "tx_dropped": 0,
                    "tx_errors": 0,
                    "tx_packets": 0,
                }
            )

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
            "transport-count": top("transport_snapshot_count", 2),
            "transport-dropped": top("dropped_transport_snapshots", 1),
            "transport-location": lambda document: document[
                "transport_snapshots"
            ][0].__setitem__("usb_location", "pci/usb9/9-9"),
            "transport-state": lambda document: document[
                "transport_snapshots"
            ][0].__setitem__("state", "unknown"),
            "transport-boolean-carrier": boolean_carrier,
            "transport-overflowing-ncm-counter": overflowing_ncm_counter,
            "transport-absent-counter": lambda document: document[
                "transport_snapshots"
            ][0].__setitem__("rx_bytes", 1),
            "transport-overflowing-nfs-counter": lambda document: document[
                "transport_snapshots"
            ][0].__setitem__("nfs_rpc_calls", 1 << 64),
            "transport-partial-nfs": lambda document: document[
                "transport_snapshots"
            ][0].__setitem__("nfs_rpc_calls", None),
            "transport-boolean-tcp-listener": lambda document: document[
                "transport_snapshots"
            ][0].__setitem__("nfs_tcp_listener", True),
            "transport-inconsistent-tcp-absence": lambda document: document[
                "transport_snapshots"
            ][0].__setitem__("nfs_tcp_states", "established"),
            "transport-backlog-without-listener": lambda document: document[
                "transport_snapshots"
            ][0].__setitem__("nfs_tcp_accept_backlog", 1),
            "transport-noncanonical-tcp-states": lambda document: document[
                "transport_snapshots"
            ][0].update(
                {
                    "nfs_tcp_connections": 2,
                    "nfs_tcp_states": "time-wait,established",
                }
            ),
            "transport-too-many-tcp-states": lambda document: document[
                "transport_snapshots"
            ][0].update(
                {
                    "nfs_tcp_connections": 1,
                    "nfs_tcp_states": "established,time-wait",
                }
            ),
            "transport-negative-tcp-queue": lambda document: document[
                "transport_snapshots"
            ][0].__setitem__("nfs_tcp_tx_queue", -1),
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
        self.assertEqual(calls.count("fallback:postmortem"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 0)
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
        self.assertEqual(calls.count("bundle:restore-fallback"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)
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

    def test_prepared_with_failed_host_receipt_never_starts_nfs(self):
        result = self.fixture.run(
            "diagnostic-run",
            MOCK_BUNDLE_FORGED_RECEIPT_FAILURE="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bundle server failed with status 1", result.stderr)
        calls = self.fixture.call_lines()
        self.assertIn("control:prepared", calls)
        self.assertIn("bundle:transfer", calls)
        self.assertNotIn("nfs:start", calls)
        self.assertFalse(
            any(line.startswith("control:resolve:") for line in calls)
        )

    def test_prepared_bundle_stall_restores_fallback_without_commit(self):
        result = self.fixture.run(
            "diagnostic-run",
            MOCK_PREPARED_BUNDLE_STALL="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "recovery control exited before the one-transfer bundle server",
            result.stderr,
        )
        self.assertIn(
            "exact fallback returned after the pre-commit failure; no "
            "commit intent existed; host cleanup proof passed",
            result.stderr,
        )
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("control:prepare-commit"), 1)
        self.assertEqual(calls.count("control:prepared"), 1)
        self.assertEqual(calls.count("bundle:transfer"), 1)
        self.assertEqual(calls.count("bundle:terminated"), 1)
        self.assertEqual(calls.count("bundle:restore-fallback"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)
        self.assertNotIn("nfs:start", calls)
        self.assertFalse(
            any(line.startswith("control:resolve:") for line in calls)
        )

    def test_prepared_bundle_stall_still_proves_host_cleanup_if_fallback_fails(
        self,
    ):
        for variable, ssh_count in (
            ("MOCK_PROFILE_RESTORE_FAIL", 0),
            ("MOCK_FALLBACK_FAIL", 1),
        ):
            with self.subTest(variable=variable):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run(
                    "diagnostic-run",
                    MOCK_PREPARED_BUNDLE_STALL="1",
                    **{variable: "1"},
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "pre-commit fallback proof failed",
                    result.stderr,
                )
                self.assertIn("host cleanup proof passed", result.stderr)
                calls = self.fixture.call_lines()
                self.assertEqual(
                    calls.count("bundle:restore-fallback"),
                    1,
                )
                self.assertEqual(
                    calls.count("fallback:ssh-preflight"),
                    ssh_count,
                )
                self.assertNotIn("nfs:start", calls)
                self.assertFalse(
                    any(
                        line.startswith("control:resolve:")
                        for line in calls
                    )
                )

    def test_prepared_bundle_stall_reports_failed_final_host_cleanup(self):
        result = self.fixture.run(
            "diagnostic-run",
            MOCK_PREPARED_BUNDLE_STALL="1",
            MOCK_RESIDUAL_AFTER_BUNDLE="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "exact fallback returned after the pre-commit failure; no "
            "commit intent existed",
            result.stderr,
        )
        self.assertIn("host cleanup proof failed", result.stderr)
        self.assertNotIn("host cleanup proof passed", result.stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("bundle:restore-fallback"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 1)
        self.assertNotIn("nfs:start", calls)
        self.assertFalse(
            any(line.startswith("control:resolve:") for line in calls)
        )

    def test_interrupt_during_precommit_fallback_is_cleaned_then_reraised(self):
        process = subprocess.Popen(
            [str(RUNNER), "diagnostic-run"],
            env=self.fixture.environment(
                BUNDLE=DIAGNOSTIC_BUNDLE,
                ROG5_STABLE_RECOVERY_PROFILE=(
                    DIAGNOSTIC_RECOVERY_PROFILE
                ),
                MOCK_PREPARED_BUNDLE_STALL="1",
                MOCK_PROFILE_RESTORE_HANG="1",
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _attempt in range(500):
            if "bundle:restore-fallback" in self.fixture.call_lines():
                break
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.fail(
                    "lifecycle exited before fallback restoration\n"
                    f"stdout={stdout}\nstderr={stderr}"
                )
            time.sleep(0.01)
        else:
            process.kill()
            process.wait(timeout=2)
            self.fail("fallback restoration did not start")
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=15)
        self.assertNotEqual(process.returncode, 0, stdout + stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("bundle:restore-fallback"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 0)
        restore_pid = int(
            (self.fixture.root / "restore-hang.pid").read_text(
                encoding="ascii"
            )
        )
        self.assertFalse(Path(f"/proc/{restore_pid}").exists())
        restore_index = calls.index("bundle:restore-fallback")
        self.assertTrue(
            any(line.startswith("ss:") for line in calls[restore_index + 1 :])
        )
        self.assertNotIn("nfs:start", calls)
        self.assertFalse(
            any(line.startswith("control:resolve:") for line in calls)
        )

    def test_interrupt_during_precommit_host_cleanup_is_reraised(self):
        process = subprocess.Popen(
            [str(RUNNER), "diagnostic-run"],
            env=self.fixture.environment(
                BUNDLE=DIAGNOSTIC_BUNDLE,
                ROG5_STABLE_RECOVERY_PROFILE=(
                    DIAGNOSTIC_RECOVERY_PROFILE
                ),
                MOCK_PREPARED_BUNDLE_STALL="1",
                MOCK_PROFILE_RESTORE_FAIL="1",
                MOCK_SS_HANG_AFTER_RESTORE_FAILURE="1",
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        marker = self.fixture.root / "ss-cleanup-hang.pid"
        for _attempt in range(500):
            if marker.exists():
                break
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                self.fail(
                    "lifecycle exited before its cleanup interrupt seam\n"
                    f"stdout={stdout}\nstderr={stderr}"
                )
            time.sleep(0.01)
        else:
            process.kill()
            process.wait(timeout=2)
            self.fail("host cleanup interrupt seam did not start")
        cleanup_pid = int(marker.read_text(encoding="ascii"))
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate(timeout=15)
        self.assertNotEqual(process.returncode, 0, stdout + stderr)
        self.assertIn("KeyboardInterrupt", stderr)
        self.assertFalse(Path(f"/proc/{cleanup_pid}").exists())
        calls = self.fixture.call_lines()
        self.assertEqual(calls.count("bundle:restore-fallback"), 1)
        self.assertEqual(calls.count("fallback:ssh-preflight"), 0)
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

    def test_deferred_profile_rejects_unexpected_uuid_and_autoconnect_on(self):
        for variable in (
            "MOCK_DEFERRED_DUPLICATE_UUID",
            "MOCK_DEFERRED_MIXED_UUID",
            "MOCK_DEFERRED_AUTOCONNECT",
        ):
            with self.subTest(variable=variable):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run("run", **{variable: "1"})
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("nfs:start", self.fixture.call_lines())
                self.assertIn("deferred", result.stderr)

    def test_deferred_profile_rejects_one_wrong_uuid_exactly(self):
        result = self.fixture.run(
            "run",
            MOCK_DEFERRED_ACTIVE_UUID="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("nfs:start", self.fixture.call_lines())
        self.assertIn(
            "deferred recovery interface retains an unexpected profile "
            "association",
            result.stderr,
        )
        self.assertIn("class=foreign count=1", result.stderr)

    def test_deferred_profile_rejection_classifies_nonsensitive_shape(self):
        cases = {
            "MOCK_DEFERRED_PLACEHOLDER_UUID": "placeholder count=1",
            "MOCK_DEFERRED_DUPLICATE_EMPTY_UUID": (
                "duplicate-empty count=2"
            ),
            "MOCK_DEFERRED_MIXED_EMPTY_UUID": "mixed-empty count=2",
            "MOCK_DEFERRED_DUPLICATE_UUID": "duplicate-exact count=2",
            "MOCK_DEFERRED_MIXED_UUID": "mixed count=2",
        }
        for variable, classification in cases.items():
            with self.subTest(variable=variable):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run("run", **{variable: "1"})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"class={classification}", result.stderr)
                self.assertNotIn("nfs:start", self.fixture.call_lines())

    def test_firewall_snapshot_mutations_fail_closed(self):
        cases = {
            "MOCK_DROP_ACTIVE_INTERFACE": (
                "drop firewall zone retains lifecycle state"
            ),
            "MOCK_DROP_ICMP_INVERSION": (
                "drop firewall zone has ICMP block inversion enabled"
            ),
            "MOCK_DROP_MALFORMED_LINE": (
                "drop firewall zone output is not canonical"
            ),
            "MOCK_DROP_MISSING_FORWARD": (
                "drop firewall zone output is incomplete"
            ),
            "MOCK_DROP_RICH_RULE": (
                "drop firewall zone retains lifecycle state"
            ),
            "MOCK_ALL_ZONES_UNKNOWN": (
                "firewall returned an unknown zone snapshot"
            ),
            "MOCK_ALL_ZONES_MISSING_TRUSTED": (
                "firewall all-zone snapshot is not canonical"
            ),
        }
        for variable, message in cases.items():
            with self.subTest(variable=variable):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run(
                    "diagnostic-preflight",
                    **{variable: "1"},
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)

    def test_deferred_profile_accepts_empty_uuid(self):
        result = self.fixture.run("run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nfs:start", self.fixture.call_lines())

    def test_deferred_profile_accepts_nmcli_empty_field_line(self):
        result = self.fixture.run(
            "run",
            MOCK_DEFERRED_EMPTY_LINE_UUID="1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nfs:start", self.fixture.call_lines())

    def test_deferred_profile_accepts_exact_stale_uuid_when_unmanaged(self):
        result = self.fixture.run(
            "run",
            MOCK_DEFERRED_STALE_UUID="1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nfs:start", self.fixture.call_lines())

    def test_stale_uuid_never_bypasses_other_deferred_profile_checks(self):
        for variable in (
            "MOCK_ADDRESS_RESIDUE_AFTER_BUNDLE",
            "MOCK_NM_RESIDUE_AFTER_BUNDLE",
            "MOCK_DEFERRED_AUTOCONNECT",
        ):
            with self.subTest(variable=variable):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run(
                    "run",
                    MOCK_DEFERRED_STALE_UUID="1",
                    **{variable: "1"},
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("nfs:start", self.fixture.call_lines())

    def test_empty_field_never_bypasses_other_deferred_profile_checks(self):
        for variable in (
            "MOCK_ADDRESS_RESIDUE_AFTER_BUNDLE",
            "MOCK_NM_RESIDUE_AFTER_BUNDLE",
            "MOCK_DEFERRED_AUTOCONNECT",
        ):
            with self.subTest(variable=variable):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run(
                    "run",
                    MOCK_DEFERRED_EMPTY_LINE_UUID="1",
                    **{variable: "1"},
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("nfs:start", self.fixture.call_lines())

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

    def test_final_cleanup_rejects_udev_model_lookalikes(self):
        for model in (
            "",
            "ROG5_",
            "ROG5_evil",
            "XROG5_recovery",
            "ROG5_recovery_extra",
            "ROG5_network_root_extra",
            "ROG5_diagnostic_network_root_extra",
            "ROG_Phone_5_Linux_Server_extra",
            "ROG5_recovery_ROG5_network_root",
            " ROG5_recovery",
            "ROG5_recovery ",
            "ROG5_recovery\t",
            "rog_phone_5_linux_server",
        ):
            with self.subTest(model=model):
                self.fixture.close()
                self.fixture = Fixture()
                result = self.fixture.run(
                    "run",
                    MOCK_RUNTIME_FAIL="1",
                    MOCK_FALLBACK_UDEV_MODEL=model,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("intent remains UNKNOWN", result.stderr)
                self.assertIn(
                    "shared ROG5 /30 escaped the exact managed USB profile",
                    result.stderr,
                )
                self.assertFalse(
                    any(
                        line.startswith("control:resolve:")
                        for line in self.fixture.call_lines()
                    )
                )

    def test_final_cleanup_rejects_missing_udev_model(self):
        result = self.fixture.run(
            "run",
            MOCK_RUNTIME_FAIL="1",
            MOCK_FALLBACK_UDEV_OMIT_MODEL="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("intent remains UNKNOWN", result.stderr)
        self.assertIn(
            "shared ROG5 /30 escaped the exact managed USB profile",
            result.stderr,
        )
        self.assertFalse(
            any(
                line.startswith("control:resolve:")
                for line in self.fixture.call_lines()
            )
        )

    def test_exact_alpine_fallback_udev_model_cleans_and_resolves(self):
        result = self.fixture.run(
            "run",
            MOCK_RUNTIME_FAIL="1",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resolved as FALLBACK_RETURNED", result.stderr)
        self.assertNotIn("host cleanup proof failed", result.stderr)
        self.assertEqual(
            self.fixture.call_lines().count(
                "control:resolve:FALLBACK_RETURNED"
            ),
            1,
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

    def test_final_cleanup_amortizes_firewall_snapshot_cost(self):
        result = self.fixture.run(
            "run",
            MOCK_RUNTIME_FAIL="1",
            MOCK_FIREWALL_DELAY="0.02",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("resolved as FALLBACK_RETURNED", result.stderr)
        self.assertNotIn("host cleanup proof failed", result.stderr)
        calls = self.fixture.call_lines()
        self.assertEqual(
            calls.count("control:resolve:FALLBACK_RETURNED"),
            1,
        )
        self.assertIn("firewall:--list-all-zones", calls)
        self.assertFalse(
            any("--list-rich-rules" in line for line in calls)
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
            '"retention-host-rendezvous-v11-mainline-udc-execution-v2"',
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
        self.assertNotIn(
            '"headless-diagnostic-host-rendezvous-v3-live-v10"', runner
        )
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
            "network-export-state",
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
