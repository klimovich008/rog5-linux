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
	'fallback USB disconnected but no anchored-port USB re-enumeration was observed' \
	'exact fastboot USB re-enumerated but fastboot userspace discovery did not succeed' \
	'fastboot escaped the exact fallback USB device' \
	'fastboot serial changed at the anchored USB device' \
	'fallback serial changed at the anchored USB device' \
	'a non-fastboot USB mode was observed at the anchored port' \
	'fallback Linux USB returned at the anchored port instead of fastboot' \
	'fallback USB never disconnected after the acknowledged bootloader reboot' \
	'expected one exact fallback USB device, found' \
	'one fastboot device is present in an unexpected state' \
	'fallback dmesg is unavailable' \
	'fallback kernel log is unreadable' \
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
	'StrictHostKeyChecking=(no|accept-new)|UserKnownHostsFile=/dev/null|fastboot[[:space:]]+(boot|flash|erase)([[:space:]]|$)|/dev/(mem|kmem)|nvmem|sysrq-trigger|dd[[:space:]].*of=|ROG5_FALLBACK_REBOOT_(OFFLINE_TEST|SYS_BUS_USB|SYS_DEVICES|TIMEOUT)' \
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
usb_restore=$stage/usb-restore
usb_device=$stage/sys/devices/pci0000:00/usb1/1-1/1-1.2
install -d -m 0755 "$stage/sys/bus/usb/devices" "$usb_device"
ln -s "$usb_device" "$stage/sys/bus/usb/devices/1-1.2"

set_usb_identity() {
	printf '%s\n' "$1" >"$usb_device/idVendor"
	printf '%s\n' "$2" >"$usb_device/idProduct"
	printf '%s\n' "$3" >"$usb_device/serial"
}

set_usb_identity 1d6b 0104 ROG5LINUX
fixture_helper=$stage/reboot-fallback-to-fastboot.sh
cp "$helper" "$fixture_helper"
sed -i \
	-e "s|^sys_bus_usb=/sys/bus/usb/devices$|sys_bus_usb=$stage/sys/bus/usb/devices|" \
	-e "s|^sys_devices=/sys/devices$|sys_devices=$stage/sys/devices|" \
	-e 's/^fastboot_timeout=45$/fastboot_timeout=3/' \
	"$fixture_helper"
helper=$fixture_helper
export MOCK_USB_DEVICE=$usb_device

cat >"$stage/bin/ssh" <<'MOCK'
#!/bin/sh
set -eu
case " $* " in
	*" reboot "*)
		printf '%s\n' reboot >>"$MOCK_CALLS"
		case "${MOCK_USB_MODE:-fastboot}" in
			absent)
				rm -f "$MOCK_USB_DEVICE/idVendor" \
					"$MOCK_USB_DEVICE/idProduct" \
					"$MOCK_USB_DEVICE/serial"
				;;
			fallback) ;;
			fastboot)
				printf '%s\n' 0b05 >"$MOCK_USB_DEVICE/idVendor"
				printf '%s\n' 4daf >"$MOCK_USB_DEVICE/idProduct"
				printf '%s\n' "${MOCK_USB_SERIAL:-${MOCK_FASTBOOT_SERIAL:-test-device}}" \
					>"$MOCK_USB_DEVICE/serial"
				;;
			fallback-return)
				rm -f "$MOCK_USB_DEVICE/idVendor" \
					"$MOCK_USB_DEVICE/idProduct" \
					"$MOCK_USB_DEVICE/serial"
				printf '%s\n' ROG5LINUX >"$MOCK_USB_RESTORE"
				;;
			fallback-wrong-serial)
				rm -f "$MOCK_USB_DEVICE/idVendor" \
					"$MOCK_USB_DEVICE/idProduct" \
					"$MOCK_USB_DEVICE/serial"
				printf '%s\n' other >"$MOCK_USB_RESTORE"
				;;
			other)
				printf '%s\n' 1234 >"$MOCK_USB_DEVICE/idVendor"
				printf '%s\n' 5678 >"$MOCK_USB_DEVICE/idProduct"
				printf '%s\n' other >"$MOCK_USB_DEVICE/serial"
				;;
			*) exit 90 ;;
		esac
		if [ "${MOCK_NO_FASTBOOT_USERSPACE:-0}" != 1 ]; then
			: >"$MOCK_FASTBOOT_READY"
		fi
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
if [ -f "${MOCK_USB_RESTORE:-}" ]; then
	IFS= read -r restore_serial <"$MOCK_USB_RESTORE"
	rm -f "$MOCK_USB_RESTORE"
	printf '%s\n' "$restore_serial" >"$MOCK_USB_DEVICE/serial"
	printf '%s\n' 0104 >"$MOCK_USB_DEVICE/idProduct"
	printf '%s\n' 1d6b >"$MOCK_USB_DEVICE/idVendor"
fi
if [ "${1:-}" = devices ] && [ -e "$MOCK_FASTBOOT_READY" ]; then
	printf '%s\t%s\n' "${MOCK_FASTBOOT_SERIAL:-test-device}" \
		"${MOCK_FASTBOOT_STATE:-fastboot}"
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

acknowledged_output=$(PATH="$stage/bin:$PATH" \
MOCK_CALLS=$calls \
MOCK_FASTBOOT_READY=$ready \
ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 \
FASTBOOT_SERIAL=test-device \
SSH_KEY=$stage/ssh-key \
KNOWN_HOSTS=$stage/known-hosts \
	"$helper" reboot)
grep -Fxq \
	'PASS exact lahaina fastboot device reached after acknowledged restart2' \
	<<<"$acknowledged_output"

rm -f "$ready"
set_usb_identity 1d6b 0104 ROG5LINUX
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
set_usb_identity 1d6b 0104 ROG5LINUX
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
	set_usb_identity 1d6b 0104 ROG5LINUX
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
set_usb_identity 1d6b 0104 ROG5LINUX
disconnect_output=$(PATH="$stage/bin:$PATH" \
MOCK_CALLS=$calls \
MOCK_FASTBOOT_READY=$ready \
MOCK_DROP_RESTART_MARKER=1 \
ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 \
FASTBOOT_SERIAL=test-device \
SSH_KEY=$stage/ssh-key \
KNOWN_HOSTS=$stage/known-hosts \
	"$helper" reboot)
grep -Fxq \
	'PASS exact lahaina fastboot device proves restart2 despite SSH disconnect before acknowledgement' \
	<<<"$disconnect_output"

preflight_calls=$(grep -Fxc preflight "$calls" || true)
reboot_calls=$(grep -Fxc reboot "$calls" || true)
fastboot_calls=$(grep -Fxc fastboot "$calls" || true)
[[ $preflight_calls == 1 && $reboot_calls == 6 && $fastboot_calls -ge 12 ]] || {
	echo "FAIL call ledger: preflight=$preflight_calls reboot=$reboot_calls fastboot=$fastboot_calls" >&2
	exit 1
}

for case_name in no-disconnect no-reenumeration fastboot-userspace \
	other-mode fallback-return fallback-wrong-serial; do
	rm -f "$ready" "$usb_restore"
	set_usb_identity 1d6b 0104 ROG5LINUX
	case $case_name in
		no-disconnect)
			usb_mode=fallback
			expected='fallback USB never disconnected after the acknowledged bootloader reboot'
			;;
		no-reenumeration)
			usb_mode=absent
			expected='fallback USB disconnected but no anchored-port USB re-enumeration was observed'
			;;
		fastboot-userspace)
			usb_mode=fastboot
			expected='exact fastboot USB re-enumerated but fastboot userspace discovery did not succeed'
			;;
		other-mode)
			usb_mode=other
			expected='a non-fastboot USB mode was observed at the anchored port'
			;;
		fallback-return)
			usb_mode=fallback-return
			expected='fallback Linux USB returned at the anchored port instead of fastboot'
			;;
		fallback-wrong-serial)
			usb_mode=fallback-wrong-serial
			expected='fallback serial changed at the anchored USB device'
			;;
	esac
	set +e
	output=$(PATH="$stage/bin:$PATH" \
		MOCK_CALLS=$calls MOCK_FASTBOOT_READY=$ready \
		MOCK_USB_RESTORE=$usb_restore \
		MOCK_USB_MODE=$usb_mode MOCK_NO_FASTBOOT_USERSPACE=1 \
		ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 \
		FASTBOOT_SERIAL=test-device SSH_KEY=$stage/ssh-key \
		KNOWN_HOSTS=$stage/known-hosts \
			"$helper" reboot 2>&1)
	status=$?
	set -e
	[[ $status -ne 0 ]] || {
		echo "FAIL $case_name: helper unexpectedly succeeded" >&2
		exit 1
	}
	grep -Fq "$expected" <<<"$output" || {
		printf 'FAIL %s: expected %s\n--- output ---\n%s\n' \
			"$case_name" "$expected" "$output" >&2
		exit 1
	}
done

for boundary in wrong-port wrong-sysfs-serial; do
	rm -f "$ready"
	set_usb_identity 1d6b 0104 ROG5LINUX
	case $boundary in
		wrong-port)
			usb_mode=other
			usb_serial=
			expected='fastboot escaped the exact fallback USB device'
			;;
		wrong-sysfs-serial)
			usb_mode=fastboot
			usb_serial=other-device
			expected='fastboot serial changed at the anchored USB device'
			;;
	esac
	set +e
	output=$(PATH="$stage/bin:$PATH" \
		MOCK_CALLS=$calls MOCK_FASTBOOT_READY=$ready \
		MOCK_USB_MODE=$usb_mode MOCK_USB_SERIAL=$usb_serial \
		ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 \
		FASTBOOT_SERIAL=test-device SSH_KEY=$stage/ssh-key \
		KNOWN_HOSTS=$stage/known-hosts \
			"$helper" reboot 2>&1)
	status=$?
	set -e
	[[ $status -ne 0 ]] || {
		echo "FAIL $boundary: helper unexpectedly succeeded" >&2
		exit 1
	}
	grep -Fq "$expected" <<<"$output" || {
		printf 'FAIL %s: expected %s\n--- output ---\n%s\n' \
			"$boundary" "$expected" "$output" >&2
		exit 1
	}
done

for fallback_count in zero duplicate; do
	rm -f "$ready"
	set_usb_identity 1d6b 0104 ROG5LINUX
	case $fallback_count in
		zero)
			printf '%s\n' NOMATCH >"$usb_device/serial"
			expected='expected one exact fallback USB device, found 0'
			;;
		duplicate)
			second_usb=$stage/sys/devices/pci0000:00/usb1/1-1/1-1.3
			install -d -m 0755 "$second_usb"
			printf '%s\n' 1d6b >"$second_usb/idVendor"
			printf '%s\n' 0104 >"$second_usb/idProduct"
			printf '%s\n' ROG5LINUX >"$second_usb/serial"
			ln -s "$second_usb" "$stage/sys/bus/usb/devices/1-1.3"
			expected='expected one exact fallback USB device, found 2'
			;;
	esac
	set +e
	output=$(PATH="$stage/bin:$PATH" \
		MOCK_CALLS=$calls MOCK_FASTBOOT_READY=$ready \
		ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 \
		FASTBOOT_SERIAL=test-device SSH_KEY=$stage/ssh-key \
		KNOWN_HOSTS=$stage/known-hosts \
			"$helper" reboot 2>&1)
	status=$?
	set -e
	[[ $status -ne 0 ]] || {
		echo "FAIL fallback-count-$fallback_count: helper unexpectedly succeeded" >&2
		exit 1
	}
	grep -Fq "$expected" <<<"$output" || {
		printf 'FAIL fallback-count-%s: expected %s\n--- output ---\n%s\n' \
			"$fallback_count" "$expected" "$output" >&2
		exit 1
	}
	if [[ $fallback_count == duplicate ]]; then
		rm -f "$stage/sys/bus/usb/devices/1-1.3"
	fi
done

rm -f "$ready"
set_usb_identity 1d6b 0104 ROG5LINUX
set +e
output=$(PATH="$stage/bin:$PATH" \
	MOCK_CALLS=$calls MOCK_FASTBOOT_READY=$ready \
	MOCK_FASTBOOT_STATE=unexpected \
	ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 \
	FASTBOOT_SERIAL=test-device SSH_KEY=$stage/ssh-key \
	KNOWN_HOSTS=$stage/known-hosts \
		"$helper" reboot 2>&1)
status=$?
set -e
[[ $status -ne 0 ]]
grep -Fq 'one fastboot device is present in an unexpected state' \
	<<<"$output"

echo 'PASS fallback reboot helper is identity-pinned, restart2-only, guarded, fastboot-verifying, and tolerant only of a proven post-disconnect reboot'
