#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
helper=$repo/scripts/host/reboot-fallback-to-fastboot.sh

[[ -x $helper ]] || {
	echo 'FAIL missing executable guarded fallback-to-fastboot helper' >&2
	exit 1
}
bash -n "$helper"
python3 - "$helper" <<'PY'
import pathlib
import sys

source = pathlib.Path(sys.argv[1]).read_text()
embedded = source.split("python3 - <<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
compile(embedded, "fallback-restart2.py", "exec")
PY
fatal_pattern='(^|[^[:alnum:]_])(Kernel panic|Oops:|BUG:|watchdog[[:space:]_-]+bite|Kernel fault|Unable to handle kernel|Synchronous External Abort)([^[:alnum:]_]|$)'

for contract in \
	'ALLOW_FALLBACK_BOOTLOADER_REBOOT' \
	'FASTBOOT_SERIAL' \
	'SSH_KEY' \
	'KNOWN_HOSTS' \
	'HostKeyAlias=rog5-fallback' \
	'StrictHostKeyChecking=yes' \
	'GlobalKnownHostsFile=/dev/null' \
	'ConnectionAttempts=1' \
	'ServerAliveInterval=5' \
	'ServerAliveCountMax=2' \
	'5.4.134-qgki-perf-00001-g6c308144c23e' \
	'qcom,lahaina-mtp' \
	'/bin/busybox' \
	'LINUX_REBOOT_MAGIC1 = 0xFEE1DEAD' \
	'LINUX_REBOOT_MAGIC2 = 672274793' \
	'LINUX_REBOOT_CMD_RESTART2 = 0xA1B2C3D4' \
	'SYS_REBOOT = 142' \
	'b"bootloader"' \
	'os.sync()' \
	"$fatal_pattern" \
	'PASS guarded fallback RESTART2 bootloader request sent' \
	'PASS authenticated fallback reboot session' \
	'^[[:space:]]*product:[[:space:]]*lahaina[[:space:]]*$' \
	'PASS exact lahaina fastboot device proves restart2 despite SSH disconnect before acknowledgement'
do
	grep -Fq "$contract" "$helper" || {
		echo "FAIL fallback-to-fastboot helper omits: $contract" >&2
		exit 1
	}
done

if printf '%s\n' \
	'dynamic_debug: Ignore empty _ddebug table' \
	'evtlog_status: enable:11, panic:1, dump:2' |
	grep -Ei "$fatal_pattern" >/dev/null
then
	echo 'FAIL fallback fatal detector accepts benign debug configuration' >&2
	exit 1
fi
for line in \
	'Kernel panic - not syncing' \
	'Oops: fatal exception' \
	'BUG: unable to handle page fault' \
	'watchdog bite detected' \
	'Kernel fault at address 0' \
	'Unable to handle kernel paging request' \
	'Synchronous External Abort'
do
	printf '%s\n' "$line" | grep -Ei "$fatal_pattern" >/dev/null || {
		echo "FAIL fallback fatal detector misses: $line" >&2
		exit 1
	}
done

if grep -Eq \
	'StrictHostKeyChecking=(no|accept-new)|UserKnownHostsFile=/dev/null|fastboot[[:space:]]+(boot|flash|erase)([[:space:]]|$)|/dev/(mem|kmem)|nvmem|sysrq-trigger|dd[[:space:]].*of=' \
	"$helper"
then
	echo 'FAIL fallback-to-fastboot helper bypasses identity or writes outside restart2' >&2
	exit 1
fi

set +e
"$helper" reboot >/dev/null 2>&1
missing_inputs=$?
ALLOW_FALLBACK_BOOTLOADER_REBOOT=unsafe \
	"$helper" reboot >/dev/null 2>&1
invalid_guard=$?
set -e
[[ $missing_inputs -ne 0 ]]
[[ $invalid_guard -ne 0 ]]

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
install -d -m 0755 "$stage/bin"
install -m 0600 /dev/null "$stage/ssh-key"
install -m 0600 /dev/null "$stage/known-hosts"
calls=$stage/calls
ready=$stage/fastboot-ready

cat >"$stage/bin/ssh" <<'MOCK'
#!/bin/sh
set -eu
case " $* " in
	*" reboot "*)
		printf '%s\n' reboot >>"$MOCK_CALLS"
		: >"$MOCK_FASTBOOT_READY"
	if [ "${MOCK_DROP_RESTART_MARKER:-0}" != 1 ]; then
		echo 'PASS authenticated fallback reboot session'
		echo 'PASS guarded fallback RESTART2 bootloader request sent'
	elif [ "${MOCK_DROP_AUTH_MARKER:-0}" != 1 ]; then
		echo 'PASS authenticated fallback reboot session'
	fi
		exit "${MOCK_SSH_STATUS:-255}"
		;;
	*)
		printf '%s\n' preflight >>"$MOCK_CALLS"
		echo 'PASS exact persistent fallback ready for guarded bootloader reboot'
		;;
esac
MOCK
cat >"$stage/bin/fastboot" <<'MOCK'
#!/bin/sh
set -eu
printf '%s\n' fastboot >>"$MOCK_CALLS"
if [ "${1:-}" = devices ] && [ -e "$MOCK_FASTBOOT_READY" ]; then
	printf '%s\tfastboot\n' "${MOCK_FASTBOOT_SERIAL:-test-device}"
	exit 0
fi
if [ "${1:-}" = -s ] && [ "${2:-}" = test-device ] &&
	[ "${3:-}" = getvar ] && [ "${4:-}" = product ]; then
	printf '%s\n' 'product: lahaina' >&2
	if [ "${MOCK_CONFLICTING_PRODUCT:-0}" = 1 ]; then
		printf '%s\n' 'product: other' >&2
	fi
	exit 0
fi
MOCK
chmod 0755 "$stage/bin/ssh" "$stage/bin/fastboot"

PATH="$stage/bin:$PATH" \
MOCK_CALLS=$calls \
MOCK_FASTBOOT_READY=$ready \
SSH_KEY=$stage/ssh-key \
KNOWN_HOSTS=$stage/known-hosts \
	"$helper" preflight >/dev/null

PATH="$stage/bin:$PATH" \
MOCK_CALLS=$calls \
MOCK_FASTBOOT_READY=$ready \
ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 \
FASTBOOT_SERIAL=test-device \
SSH_KEY=$stage/ssh-key \
KNOWN_HOSTS=$stage/known-hosts \
	"$helper" reboot >/dev/null

rm -f "$ready"
set +e
PATH="$stage/bin:$PATH" \
MOCK_CALLS=$calls \
MOCK_FASTBOOT_READY=$ready \
MOCK_DROP_RESTART_MARKER=1 \
MOCK_SSH_STATUS=1 \
ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 \
FASTBOOT_SERIAL=test-device \
SSH_KEY=$stage/ssh-key \
KNOWN_HOSTS=$stage/known-hosts \
	"$helper" reboot >/dev/null 2>&1
unproved_status=$?
set -e
[[ $unproved_status -ne 0 ]]

rm -f "$ready"
set +e
PATH="$stage/bin:$PATH" \
MOCK_CALLS=$calls \
MOCK_FASTBOOT_READY=$ready \
MOCK_DROP_RESTART_MARKER=1 \
MOCK_DROP_AUTH_MARKER=1 \
ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 \
FASTBOOT_SERIAL=test-device \
SSH_KEY=$stage/ssh-key \
KNOWN_HOSTS=$stage/known-hosts \
	"$helper" reboot >/dev/null 2>&1
unauthenticated_status=$?
set -e
[[ $unauthenticated_status -ne 0 ]]

for mutation in wrong-serial conflicting-product; do
	rm -f "$ready"
	set +e
	case $mutation in
		wrong-serial)
			PATH="$stage/bin:$PATH" \
			MOCK_CALLS=$calls MOCK_FASTBOOT_READY=$ready \
			MOCK_FASTBOOT_SERIAL=other-device \
			ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 \
			FASTBOOT_SERIAL=test-device SSH_KEY=$stage/ssh-key \
			KNOWN_HOSTS=$stage/known-hosts \
				"$helper" reboot >/dev/null 2>&1
			;;
		conflicting-product)
			PATH="$stage/bin:$PATH" \
			MOCK_CALLS=$calls MOCK_FASTBOOT_READY=$ready \
			MOCK_CONFLICTING_PRODUCT=1 \
			ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 \
			FASTBOOT_SERIAL=test-device SSH_KEY=$stage/ssh-key \
			KNOWN_HOSTS=$stage/known-hosts \
				"$helper" reboot >/dev/null 2>&1
			;;
	esac
	mutation_status=$?
	set -e
	[[ $mutation_status -ne 0 ]]
done

rm -f "$ready"
PATH="$stage/bin:$PATH" \
MOCK_CALLS=$calls \
MOCK_FASTBOOT_READY=$ready \
MOCK_DROP_RESTART_MARKER=1 \
ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 \
FASTBOOT_SERIAL=test-device \
SSH_KEY=$stage/ssh-key \
KNOWN_HOSTS=$stage/known-hosts \
	"$helper" reboot >/dev/null

[[ $(grep -Fxc preflight "$calls") == 1 ]]
[[ $(grep -Fxc reboot "$calls") == 6 ]]
[[ $(grep -Fxc fastboot "$calls") -ge 12 ]]

echo 'PASS fallback reboot helper is identity-pinned, restart2-only, guarded, fastboot-verifying, and tolerant only of a proven post-disconnect reboot'
