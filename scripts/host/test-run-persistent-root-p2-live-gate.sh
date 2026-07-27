#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
runner=$repo/scripts/host/run-persistent-root-p2-live-gate.sh

[[ -x $runner ]] || {
	echo "FAIL missing executable P2 live-gate runner: $runner" >&2
	exit 1
}
bash -n "$runner"
syntax_stage=$(mktemp -d)
trap 'rm -rf -- "$syntax_stage"' EXIT
python3 - "$runner" "$syntax_stage" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text()
output = Path(sys.argv[2])
for name in ("remote_target", "remote_fallback"):
    start = source.index(f"{name}='\n") + len(name) + 3
    end = source.index("\n'\n\nset +e", start)
    (output / f"{name}.sh").write_text(source[start:end] + "\n")
PY
sh -n "$syntax_stage/remote_target.sh" "$syntax_stage/remote_fallback.sh"
shellcheck -s sh -S warning \
	"$syntax_stage/remote_target.sh" \
	"$syntax_stage/remote_fallback.sh"
rm -rf -- "$syntax_stage"
trap - EXIT

for contract in \
	'ALLOW_PERSISTENT_ROOT_P2_LIVE_GATE' \
	'ALLOW_TEMPORARY_BOOT' \
	'ALLOW_ATTENDED_KEXEC' \
	'SSH_KEY' \
	'KNOWN_HOSTS' \
	'EVIDENCE_DIR' \
	'boot-5.4.210-persistent-root.avb.img' \
	'recovery-linux.sh' \
	'persistent-root-acm.py' \
	'reboot-fallback-to-fastboot.sh' \
	'HostKeyAlias=rog5-persistent-root' \
	'HostKeyAlias=rog5-fallback' \
	'StrictHostKeyChecking=accept-new' \
	'StrictHostKeyChecking=yes' \
	'7.1.4-gcfd385a1c754' \
	'5.4.134-qgki-perf-00001-g6c308144c23e' \
	'/run/rog5-p2-ready' \
	'e201955dead61a04ca0e70d67fcea18750940330421334c91cfe2c760e7fb3ff' \
	'b71eccbe5275f8d125a6d3251fff166b57f196c23984b845e31666ecaaea9a8c' \
	'/run/rog5-p2-watchdog.pid' \
	'/rog5/state/good' \
	'/rog5/state/next' \
	'UNBOOTED' \
	'PASS P2 target acceptance' \
	'PASS P2 fallback acceptance' \
	'systemctl stop ModemManager.service' \
	'systemctl start ModemManager.service'
do
	grep -Fq "$contract" "$runner" || {
		echo "FAIL P2 live runner omits: $contract" >&2
		exit 1
	}
done

if grep -Eq \
	'fastboot[[:space:]]+(flash|erase)|adb[[:space:]]|dd[[:space:]].*of=/dev/|mkfs|fsck|parted|sgdisk|state/(good|next).*>' \
	"$runner"
then
	echo 'FAIL P2 live runner contains a flash, storage-write, or promotion path' >&2
	exit 1
fi

set +e
"$runner" >/dev/null 2>&1
missing_guards=$?
ALLOW_PERSISTENT_ROOT_P2_LIVE_GATE=1 \
	ALLOW_TEMPORARY_BOOT=unsafe \
	ALLOW_ATTENDED_KEXEC=1 \
	"$runner" >/dev/null 2>&1
invalid_boot_guard=$?
ALLOW_PERSISTENT_ROOT_P2_LIVE_GATE=1 \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_ATTENDED_KEXEC=unsafe \
	"$runner" >/dev/null 2>&1
invalid_kexec_guard=$?
set -e

[[ $missing_guards -ne 0 ]]
[[ $invalid_boot_guard -ne 0 ]]
[[ $invalid_kexec_guard -ne 0 ]]

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
mock_repo=$stage/repo
install -d -m 0755 \
	"$mock_repo/scripts/host" \
	"$mock_repo/artifacts/persistent-root-p2" \
	"$stage/bin"
install -d -m 0700 "$stage/evidence"
install -m 0600 /dev/null "$stage/ssh-key"
install -m 0600 /dev/null "$stage/known-hosts"
install -m 0644 /dev/null \
	"$mock_repo/artifacts/persistent-root-p2/boot-5.4.210-persistent-root.avb.img"
install -m 0755 "$runner" \
	"$mock_repo/scripts/host/run-persistent-root-p2-live-gate.sh"
calls=$stage/calls
mm_state=$stage/modem-manager-active
: >"$mm_state"

cat >"$mock_repo/scripts/host/recovery-linux.sh" <<'MOCK'
#!/bin/sh
set -eu
[ "$BOOT_IMAGE" = \
	"$MOCK_REPO/artifacts/persistent-root-p2/boot-5.4.210-persistent-root.avb.img" ]
case $1 in
	preflight) ;;
	boot) [ "${ALLOW_TEMPORARY_BOOT:-}" = 1 ] ;;
	*) exit 1 ;;
esac
printf 'recovery-%s\n' "$1" >>"$MOCK_CALLS"
MOCK
cat >"$mock_repo/scripts/host/persistent-root-acm.py" <<'MOCK'
#!/bin/sh
set -eu
[ "${ALLOW_PERSISTENT_ROOT_ACM:-}" = 1 ]
case $1 in
	load|preflight) ;;
	execute) [ "${ALLOW_ATTENDED_KEXEC:-}" = 1 ] ;;
	*) exit 1 ;;
esac
printf 'acm-%s\n' "$1" >>"$MOCK_CALLS"
MOCK
cat >"$mock_repo/scripts/host/reboot-fallback-to-fastboot.sh" <<'MOCK'
#!/bin/sh
set -eu
[ "$1" = preflight ]
[ -n "${SSH_KEY:-}" ] && [ -n "${KNOWN_HOSTS:-}" ]
echo fallback-preflight >>"$MOCK_CALLS"
echo 'PASS exact persistent fallback ready for guarded bootloader reboot'
MOCK
cat >"$stage/bin/git" <<'MOCK'
#!/bin/sh
set -eu
case $* in
	*"status --porcelain"*) exit 0 ;;
	*"branch --show-current"*) echo agent/linux-recovery-host ;;
	*"rev-parse HEAD"*|*"rev-parse origin/agent/linux-recovery-host"*)
		echo synchronized-checkpoint
		;;
	*) exit 1 ;;
esac
MOCK
cat >"$stage/bin/systemctl" <<'MOCK'
#!/bin/sh
set -eu
case $* in
	"is-active --quiet ModemManager.service")
		[ -e "$MOCK_MM_STATE" ]
		;;
	"stop ModemManager.service")
		rm -f -- "$MOCK_MM_STATE"
		echo modem-stop >>"$MOCK_CALLS"
		;;
	"start ModemManager.service")
		: >"$MOCK_MM_STATE"
		echo modem-start >>"$MOCK_CALLS"
		;;
	*) exit 1 ;;
esac
MOCK
cat >"$stage/bin/ssh" <<'MOCK'
#!/bin/sh
set -eu
known_hosts=
for argument in "$@"; do
	case $argument in
		UserKnownHostsFile=*) known_hosts=${argument#*=} ;;
	esac
done
case $* in
	*"HostKeyAlias=rog5-persistent-root"*"/proc/sys/kernel/random/boot_id"*)
		[ -n "$known_hosts" ]
		echo 'mock target host key' >"$known_hosts"
		echo target-boot-id >>"$MOCK_CALLS"
		echo 11111111-1111-4111-8111-111111111111
		;;
	*"HostKeyAlias=rog5-persistent-root"*"test -r /run/rog5-p2-ready"*)
		echo target-ready >>"$MOCK_CALLS"
		;;
	*"HostKeyAlias=rog5-persistent-root"*"PASS P2 target acceptance"*)
		echo target-attest >>"$MOCK_CALLS"
		if [ "${MOCK_FAIL_TARGET_ATTEST:-0}" = 1 ]; then
			echo 'synthetic target rejection' >&2
			exit 1
		fi
		echo 'kernel=7.1.4-gcfd385a1c754'
		echo 'physical_blocks=116'
		echo 'backlights=0'
		echo 'failed_units=0'
		echo 'watchdog=armed'
		echo 'PASS P2 target acceptance kernel=7.1.4-gcfd385a1c754 storage=ro overlay=tmpfs watchdog=armed'
		;;
	*"HostKeyAlias=rog5-fallback"*"/proc/sys/kernel/random/boot_id"*)
		echo fallback-boot-id >>"$MOCK_CALLS"
		echo 22222222-2222-4222-8222-222222222222
		;;
	*"HostKeyAlias=rog5-fallback"*"PASS P2 fallback acceptance"*)
		echo fallback-state >>"$MOCK_CALLS"
		echo 'root_state=UNBOOTED'
		echo 'selectors=absent'
		echo 'screen=off-or-absent'
		echo 'PASS P2 fallback acceptance kernel=5.4.134-qgki-perf-00001-g6c308144c23e root=UNBOOTED selectors=absent'
		;;
	*) exit 1 ;;
esac
MOCK
chmod 0755 "$mock_repo/scripts/host/"*.sh \
	"$mock_repo/scripts/host/persistent-root-acm.py" \
	"$stage/bin/git" "$stage/bin/ssh" "$stage/bin/systemctl"

PATH="$stage/bin:$PATH" \
MOCK_CALLS=$calls \
MOCK_MM_STATE=$mm_state \
MOCK_REPO=$mock_repo \
ALLOW_PERSISTENT_ROOT_P2_LIVE_GATE=1 \
ALLOW_TEMPORARY_BOOT=1 \
ALLOW_ATTENDED_KEXEC=1 \
SSH_KEY=$stage/ssh-key \
KNOWN_HOSTS=$stage/known-hosts \
EVIDENCE_DIR=$stage/evidence \
	"$mock_repo/scripts/host/run-persistent-root-p2-live-gate.sh" >/dev/null

cat >"$stage/expected-calls" <<'EXPECTED'
recovery-preflight
modem-stop
recovery-boot
acm-load
acm-preflight
acm-execute
target-boot-id
target-ready
target-ready
target-attest
fallback-boot-id
fallback-preflight
fallback-state
modem-start
EXPECTED
cmp "$stage/expected-calls" "$calls"
[[ -e $mm_state ]]
[[ $(stat -c %a "$stage/evidence/persistent-root-p2-target.log") == 600 ]]
[[ $(stat -c %a "$stage/evidence/persistent-root-p2-fallback.log") == 600 ]]
grep -Fxq \
	'PASS P2 target acceptance kernel=7.1.4-gcfd385a1c754 storage=ro overlay=tmpfs watchdog=armed' \
	"$stage/evidence/persistent-root-p2-target.log"
grep -Fxq \
	'PASS P2 fallback acceptance kernel=5.4.134-qgki-perf-00001-g6c308144c23e root=UNBOOTED selectors=absent' \
	"$stage/evidence/persistent-root-p2-fallback.log"
[[ $(grep -Fxc acm-execute "$calls") == 1 ]]

install -d -m 0700 "$stage/evidence-rejected"
: >"$calls"
: >"$mm_state"
set +e
PATH="$stage/bin:$PATH" \
MOCK_CALLS=$calls \
MOCK_MM_STATE=$mm_state \
MOCK_REPO=$mock_repo \
MOCK_FAIL_TARGET_ATTEST=1 \
ALLOW_PERSISTENT_ROOT_P2_LIVE_GATE=1 \
ALLOW_TEMPORARY_BOOT=1 \
ALLOW_ATTENDED_KEXEC=1 \
SSH_KEY=$stage/ssh-key \
KNOWN_HOSTS=$stage/known-hosts \
EVIDENCE_DIR=$stage/evidence-rejected \
	"$mock_repo/scripts/host/run-persistent-root-p2-live-gate.sh" \
	>/dev/null 2>&1
rejected_status=$?
set -e
[[ $rejected_status -ne 0 ]]
[[ -e $mm_state ]]
[[ $(grep -Fxc acm-execute "$calls") == 1 ]]
[[ $(grep -Fxc target-attest "$calls") == 1 ]]
! grep -Fq fallback-boot-id "$calls"
! grep -Fq fallback-preflight "$calls"
! grep -Fq fallback-state "$calls"
[[ $(grep -Fxc modem-start "$calls") == 1 ]]

echo 'PASS P2 live runner is guard-first, temporary-boot-only, target-attesting, watchdog-preserving, and fallback-verifying'
