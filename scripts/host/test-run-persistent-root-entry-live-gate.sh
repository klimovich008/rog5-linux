#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
runner=$repo/scripts/host/run-persistent-root-entry-live-gate.sh

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[[ -x $runner ]] || fail "missing executable entry live-gate runner: $runner"
bash -n "$runner"
shellcheck -S warning "$runner"

for contract in \
	'ALLOW_PERSISTENT_ROOT_ENTRY_LIVE_GATE' \
	'ALLOW_TEMPORARY_BOOT' \
	'ALLOW_ATTENDED_KEXEC' \
	'ALLOW_PERSISTENT_ROOT_ENTRY_ACM' \
	'ALLOW_PERSISTENT_ROOT_ACM' \
	'SSH_KEY' \
	'KNOWN_HOSTS' \
	'EVIDENCE_DIR' \
	'boot-5.4.210-persistent-root-entry.avb.img' \
	'recovery-linux.sh' \
	'persistent-root-acm.py' \
	'persistent-root-entry-acm.py' \
	'reboot-fallback-to-fastboot.sh' \
	'HostKeyAlias=rog5-fallback' \
	'StrictHostKeyChecking=yes' \
	'7.1.4-gcfd385a1c754' \
	'5.4.134-qgki-perf-00001-g6c308144c23e' \
	'e201955dead61a04ca0e70d67fcea18750940330421334c91cfe2c760e7fb3ff' \
	'b71eccbe5275f8d125a6d3251fff166b57f196c23984b845e31666ecaaea9a8c' \
	'd42215d6a619d21b41e890b4c7f622284bd33cb360c122c71aca5c5ffc5435a6' \
	'/rog5/state/good' \
	'/rog5/state/next' \
	'/rog5/roots/arch-a.partial' \
	'UNBOOTED' \
	'qpnp_pon' \
	'unexpected_evtests' \
	'PASS P2 early-entry oracle init=entered storage=untouched watchdog=armed' \
	'PASS receive-only P2 early-entry ACM marker' \
	'PASS P2 early-entry fallback acceptance' \
	'systemctl stop ModemManager.service' \
	'systemctl start ModemManager.service'
do
	grep -Fq "$contract" "$runner" ||
		fail "entry live runner omits: $contract"
done

if grep -Eq \
	'fastboot[[:space:]]+(flash|erase)|adb[[:space:]]|dd[[:space:]].*of=/dev/|mkfs|fsck|parted|sgdisk|state/(good|next).*>' \
	"$runner"
then
	fail 'entry live runner contains a flash, storage-write, or promotion path'
fi

set +e
"$runner" >/dev/null 2>&1
missing_guards=$?
ALLOW_PERSISTENT_ROOT_ENTRY_LIVE_GATE=1 \
	ALLOW_TEMPORARY_BOOT=unsafe \
	ALLOW_ATTENDED_KEXEC=1 \
	"$runner" >/dev/null 2>&1
invalid_boot_guard=$?
ALLOW_PERSISTENT_ROOT_ENTRY_LIVE_GATE=1 \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_ATTENDED_KEXEC=unsafe \
	"$runner" >/dev/null 2>&1
invalid_kexec_guard=$?
set -e
[[ $missing_guards -ne 0 ]]
[[ $invalid_boot_guard -ne 0 ]]
[[ $invalid_kexec_guard -ne 0 ]]

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
mock_repo=$stage/repo
install -d -m 0755 \
	"$mock_repo/scripts/host" \
	"$mock_repo/scripts/device" \
	"$mock_repo/packaging/alpine" \
	"$mock_repo/artifacts/persistent-root-entry-v1" \
	"$stage/bin"
install -m 0755 "$runner" \
	"$mock_repo/scripts/host/run-persistent-root-entry-live-gate.sh"
for file in \
	scripts/device/screen-toggle.sh \
	scripts/device/alpine-screen-button-daemon.sh \
	scripts/device/alpine-screen-button-openrc-start.sh \
	scripts/device/alpine-phone-start-wrapper.sh \
	packaging/alpine/rog5-screen-button
do
	install -m 0755 /dev/null "$mock_repo/$file"
done
install -m 0644 /dev/null \
	"$mock_repo/artifacts/persistent-root-entry-v1/boot-5.4.210-persistent-root-entry.avb.img"

cat >"$mock_repo/scripts/host/recovery-linux.sh" <<'MOCK'
#!/bin/sh
set -eu
[ "$BOOT_IMAGE" = \
	"$MOCK_REPO/artifacts/persistent-root-entry-v1/boot-5.4.210-persistent-root-entry.avb.img" ]
case $1 in
	preflight) ;;
	boot) [ "${ALLOW_TEMPORARY_BOOT:-}" = 1 ] ;;
	*) exit 2 ;;
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
	*) exit 2 ;;
esac
printf 'staging-%s\n' "$1" >>"$MOCK_CALLS"
MOCK
cat >"$mock_repo/scripts/host/persistent-root-entry-acm.py" <<'MOCK'
#!/bin/sh
set -eu
[ "${ALLOW_PERSISTENT_ROOT_ENTRY_ACM:-}" = 1 ]
[ "$1" = read ]
printf 'entry-read\n' >>"$MOCK_CALLS"
if [ "${MOCK_ENTRY_REJECTED:-0}" = 1 ]; then
	echo 'FAIL complete P2 early-entry marker was not received' >&2
	exit 1
fi
cat <<'MARKER'
status=PASS
mode=early-entry
init=entered
kernel_release_read_status=0
kernel_release=7.1.4-gcfd385a1c754
kernel_expected=7.1.4-gcfd385a1c754
persistent_tokens=1
persistent_invalid_tokens=0
discovery_tokens=1
discovery_invalid_tokens=0
entry_tokens=1
entry_invalid_tokens=0
block_backed_mounts=0
watchdog_seconds=120
PASS P2 early-entry oracle init=entered storage=untouched watchdog=armed
PASS receive-only P2 early-entry ACM marker
MARKER
MOCK
cat >"$mock_repo/scripts/host/reboot-fallback-to-fastboot.sh" <<'MOCK'
#!/bin/sh
set -eu
[ "$1" = preflight ]
[ -n "${SSH_KEY:-}" ] && [ -n "${KNOWN_HOSTS:-}" ]
printf 'fallback-preflight\n' >>"$MOCK_CALLS"
echo 'PASS exact persistent fallback ready for guarded bootloader reboot'
MOCK
chmod 0755 "$mock_repo/scripts/host/"*

cat >"$stage/bin/git" <<'MOCK'
#!/bin/sh
set -eu
case $* in
	*"status --porcelain"*) exit 0 ;;
	*"branch --show-current"*) echo agent/linux-recovery-host ;;
	*"rev-parse HEAD"*|*"rev-parse origin/agent/linux-recovery-host"*)
		echo synchronized-checkpoint
		;;
	*) exit 2 ;;
esac
MOCK
cat >"$stage/bin/fastboot" <<'MOCK'
#!/bin/sh
set -eu
[ "$1" = devices ]
printf 'mock-device\tfastboot\n'
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
		printf 'modem-stop\n' >>"$MOCK_CALLS"
		;;
	"start ModemManager.service")
		: >"$MOCK_MM_STATE"
		printf 'modem-start\n' >>"$MOCK_CALLS"
		;;
	*) exit 2 ;;
esac
MOCK
cat >"$stage/bin/ssh" <<'MOCK'
#!/bin/sh
set -eu
case $* in
	*"/proc/sys/kernel/random/boot_id"*)
		printf 'fallback-probe\n' >>"$MOCK_CALLS"
		echo 22222222-2222-4222-8222-222222222222
		;;
	*"PASS P2 early-entry fallback acceptance"*)
		printf 'fallback-attest\n' >>"$MOCK_CALLS"
		echo 'root_state=UNBOOTED'
		echo 'selectors=absent'
		echo 'screen=off'
		echo 'screen_service=active'
		echo 'PASS P2 early-entry fallback acceptance kernel=5.4.134-qgki-perf-00001-g6c308144c23e root=UNBOOTED screen=off'
		;;
	*) exit 2 ;;
esac
MOCK
chmod 0755 "$stage/bin/git" "$stage/bin/fastboot" \
	"$stage/bin/systemctl" "$stage/bin/ssh"

run_mock() {
	evidence=$1
	shift
	install -d -m 0700 "$evidence"
	: >"$stage/mm-active"
	PATH="$stage/bin:$PATH" \
	MOCK_REPO=$mock_repo \
	MOCK_CALLS=$stage/calls \
	MOCK_MM_STATE=$stage/mm-active \
	ALLOW_PERSISTENT_ROOT_ENTRY_LIVE_GATE=1 \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_ATTENDED_KEXEC=1 \
	SSH_KEY=$stage/ssh-key \
	KNOWN_HOSTS=$stage/known-hosts \
	EVIDENCE_DIR=$evidence \
		"$@" "$mock_repo/scripts/host/run-persistent-root-entry-live-gate.sh"
}

install -m 0600 /dev/null "$stage/ssh-key"
install -m 0600 /dev/null "$stage/known-hosts"
: >"$stage/calls"
run_mock "$stage/evidence" env >/dev/null

cat >"$stage/expected-calls" <<'EXPECTED'
recovery-preflight
modem-stop
recovery-boot
staging-load
staging-preflight
staging-execute
entry-read
fallback-probe
fallback-preflight
fallback-attest
modem-start
EXPECTED
cmp "$stage/expected-calls" "$stage/calls"
[[ -e $stage/mm-active ]]
[[ $(grep -Fxc staging-execute "$stage/calls") == 1 ]]
[[ $(stat -c %a "$stage/evidence/persistent-root-entry-target.log") == 600 ]]
[[ $(stat -c %a "$stage/evidence/persistent-root-entry-fallback.log") == 600 ]]
grep -Fxq \
	'PASS receive-only P2 early-entry ACM marker' \
	"$stage/evidence/persistent-root-entry-target.log"
grep -Fxq \
	'PASS P2 early-entry fallback acceptance kernel=5.4.134-qgki-perf-00001-g6c308144c23e root=UNBOOTED screen=off' \
	"$stage/evidence/persistent-root-entry-fallback.log"

: >"$stage/calls"
set +e
run_mock "$stage/evidence-rejected" env MOCK_ENTRY_REJECTED=1 \
	>/dev/null 2>&1
rejected_status=$?
set -e
[[ $rejected_status -ne 0 ]]
[[ -e $stage/mm-active ]]
[[ $(grep -Fxc staging-execute "$stage/calls") == 1 ]]
[[ $(grep -Fxc entry-read "$stage/calls") == 1 ]]
[[ $(grep -Fxc fallback-probe "$stage/calls") == 1 ]]
[[ $(grep -Fxc fallback-preflight "$stage/calls") == 1 ]]
[[ $(grep -Fxc fallback-attest "$stage/calls") == 1 ]]
[[ $(grep -Fxc modem-start "$stage/calls") == 1 ]]
grep -Fq \
	'FAIL complete P2 early-entry marker was not received' \
	"$stage/evidence-rejected/persistent-root-entry-target.log"
grep -Fxq \
	'PASS P2 early-entry fallback acceptance kernel=5.4.134-qgki-perf-00001-g6c308144c23e root=UNBOOTED screen=off' \
	"$stage/evidence-rejected/persistent-root-entry-fallback.log"

echo 'PASS early-entry live runner is guard-first, non-flashing, receive-only, one-execute, rollback-verifying, screen-verifying, and ModemManager-restoring'
