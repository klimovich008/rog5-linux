#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

action=${1:-preflight}
case $action in
	preflight) ;;
	reboot)
		[[ ${ALLOW_FALLBACK_BOOTLOADER_REBOOT:-} == 1 ]] ||
			fail 'set ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 for one guarded reboot'
		;;
	*) fail 'usage: reboot-fallback-to-fastboot.sh [preflight|reboot]' ;;
esac

ssh_key=${SSH_KEY:-}
known_hosts=${KNOWN_HOSTS:-}
[[ -n $ssh_key && -n $known_hosts ]] ||
	fail 'set SSH_KEY and KNOWN_HOSTS to the dedicated phone credentials'
sys_bus_usb=/sys/bus/usb/devices
sys_devices=/sys/devices
fastboot_timeout=45
for command in realpath ssh stat; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
if [[ $action == reboot ]]; then
	for command in date fastboot sleep; do
		command -v "$command" >/dev/null ||
			fail "missing host command: $command"
	done
	fastboot_serial=${FASTBOOT_SERIAL:-}
	[[ $fastboot_serial =~ ^[A-Za-z0-9._:-]{1,128}$ ]] ||
		fail 'set FASTBOOT_SERIAL to the exact expected device'
fi

ssh_key=$(realpath -e "$ssh_key")
known_hosts=$(realpath -e "$known_hosts")
case $ssh_key:$known_hosts in
	*%*|*[[:space:]]*)
		fail 'credential paths must not contain whitespace or OpenSSH percent tokens'
		;;
esac
[[ -f $ssh_key && ! -L $ssh_key && -r $ssh_key ]] ||
	fail 'SSH_KEY is not a readable regular file'
[[ -f $known_hosts && ! -L $known_hosts && -r $known_hosts ]] ||
	fail 'KNOWN_HOSTS is not a readable regular file'
[[ $(stat -c %u "$ssh_key") == "$EUID" &&
	$(stat -c %u "$known_hosts") == "$EUID" ]] ||
	fail 'credential files must be owned by the caller'
key_mode=$(stat -c %a "$ssh_key")
known_hosts_mode=$(stat -c %a "$known_hosts")
[[ $key_mode =~ ^[0-7]{3,4}$ && $known_hosts_mode =~ ^[0-7]{3,4}$ ]] ||
	fail 'credential modes are invalid'
(( (8#$key_mode & 077) == 0 )) ||
	fail 'SSH_KEY must not be accessible by group or other users'
(( (8#$known_hosts_mode & 022) == 0 )) ||
	fail 'KNOWN_HOSTS must not be writable by group or other users'

target=root@169.254.77.2
ssh_options=(
	-F /dev/null
	-i "$ssh_key"
	-o IdentitiesOnly=yes
	-o BatchMode=yes
	-o StrictHostKeyChecking=yes
	-o UserKnownHostsFile="$known_hosts"
	-o GlobalKnownHostsFile=/dev/null
	-o HostKeyAlias=rog5-fallback
	-o ConnectTimeout=8
	-o ConnectionAttempts=1
	-o ServerAliveInterval=5
	-o ServerAliveCountMax=2
	-o LogLevel=ERROR
)

read_usb_field() {
	local path=$1 value
	[[ -f $path && ! -L $path ]] || return 1
	IFS= read -r value <"$path" || return 1
	[[ $value =~ ^[A-Za-z0-9._:-]{1,128}$ ]] || return 1
	printf '%s\n' "$value"
}

usb_identity_at() {
	local location=$1 raw vendor product
	raw=$sys_devices/$location
	[[ -d $raw ]] || return 1
	vendor=$(read_usb_field "$raw/idVendor") || return 1
	product=$(read_usb_field "$raw/idProduct") || return 1
	vendor=${vendor,,}
	product=${product,,}
	[[ $vendor =~ ^[0-9a-f]{4}$ && $product =~ ^[0-9a-f]{4}$ ]] ||
		return 1
	printf '%s:%s\n' "$vendor" "$product"
}

find_fallback_usb_location() {
	local candidate resolved vendor product serial location=
	local count=0
	for candidate in "$sys_bus_usb"/*; do
		[[ -e $candidate ]] || continue
		vendor=$(read_usb_field "$candidate/idVendor" 2>/dev/null || true)
		product=$(read_usb_field "$candidate/idProduct" 2>/dev/null || true)
		serial=$(read_usb_field "$candidate/serial" 2>/dev/null || true)
		[[ ${vendor,,}:${product,,}:$serial == 1d6b:0104:ROG5LINUX ]] ||
			continue
		resolved=$(realpath -e "$candidate") || continue
		case $resolved in
			"$sys_devices"/*) ;;
			*) continue ;;
		esac
		location=${resolved#"$sys_devices"/}
		[[ -n $location && $location != "$resolved" ]] || continue
		count=$((count + 1))
	done
	[[ $count == 1 ]] ||
		fail "expected one exact fallback USB device, found $count"
	printf '%s\n' "$location"
}

require_fastboot_usb_at() {
	local location=$1 expected_serial=$2 raw serial
	[[ $(usb_identity_at "$location" 2>/dev/null || true) == 0b05:4daf ]] ||
		fail 'fastboot escaped the exact fallback USB device'
	raw=$sys_devices/$location
	serial=$(read_usb_field "$raw/serial" 2>/dev/null || true)
	[[ $serial == "$expected_serial" ]] ||
		fail 'fastboot serial changed at the anchored USB device'
}

if [[ $action == reboot ]]; then
	fallback_usb_location=$(find_fallback_usb_location)
	initial_count=$(fastboot devices 2>/dev/null |
		awk '$2 == "fastboot" { count++ } END { print count + 0 }')
	[[ $initial_count == 0 ]] ||
		fail 'refusing reboot request while a fastboot device already exists'
fi

set +e
output=$(ssh "${ssh_options[@]}" "$target" sh -se -- "$action" <<'REMOTE'
action=$1

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "$action" = preflight ] || [ "$action" = reboot ] ||
	fail 'unexpected remote action'
[ "$(uname -r)" = 5.4.134-qgki-perf-00001-g6c308144c23e ] ||
	fail 'unexpected fallback kernel'
[ "$(readlink /proc/1/exe)" = /bin/busybox ] ||
	fail 'unexpected fallback init'
tr '\000' '\n' </proc/device-tree/compatible |
	grep -Fxq qcom,lahaina-mtp ||
	fail 'unexpected fallback compatible'
awk '$2 == "/" && $3 == "ext4" { found=1 }
	END { exit !found }' /proc/mounts ||
	fail 'fallback root is not ext4'
[ ! -e /run/rog5-gpucc-diagnostic ] ||
	fail 'a diagnostic stage is still present'
awk '$1 ~ /^rog5_/ { found=1 } END { exit found }' /proc/modules ||
	fail 'a project diagnostic module is loaded'

pstore_records=0
for directory in /sys/fs/pstore /mnt/pstore; do
	[ -d "$directory" ] || continue
	for file in "$directory"/*; do
		[ -f "$file" ] || continue
		pstore_records=$((pstore_records + 1))
	done
done
[ "$pstore_records" -eq 0 ] || fail 'fallback pstore is not empty'
fatal_pattern='(^|[^[:alnum:]_])(Kernel panic|Oops:|BUG:|watchdog[[:space:]_-]+bite|Kernel fault|Unable to handle kernel|Synchronous External Abort)([^[:alnum:]_]|$)'
command -v dmesg >/dev/null || fail 'fallback dmesg is unavailable'
dmesg >/dev/null 2>&1 || fail 'fallback kernel log is unreadable'
fatal_lines=$(dmesg 2>/dev/null |
	grep -Eic "$fatal_pattern" || true)
[ "$fatal_lines" -eq 0 ] || fail 'fallback kernel log has a fatal signature'

thermal_zones=0
thermal_max=0
for file in /sys/class/thermal/thermal_zone*/temp; do
	value=$(sed -n '1p' "$file" 2>/dev/null || true)
	case $value in ''|*[!0-9-]*) continue ;; esac
	[ "$value" -ge 0 ] 2>/dev/null || continue
	thermal_zones=$((thermal_zones + 1))
	[ "$value" -le "$thermal_max" ] || thermal_max=$value
done
[ "$thermal_zones" -gt 0 ] || fail 'fallback thermal telemetry is absent'
[ "$thermal_max" -le 60000 ] || fail 'fallback temperature is unsafe'
command -v python3 >/dev/null || fail 'fallback Python is unavailable'

if [ "$action" = preflight ]; then
	echo 'PASS exact persistent fallback ready for guarded bootloader reboot'
	exit 0
fi

echo 'PASS authenticated fallback reboot session'
python3 - <<'PY'
import ctypes
import os
import platform

LINUX_REBOOT_MAGIC1 = 0xFEE1DEAD
LINUX_REBOOT_MAGIC2 = 672274793
LINUX_REBOOT_CMD_RESTART2 = 0xA1B2C3D4
SYS_REBOOT = 142

if os.geteuid() != 0:
    raise SystemExit("FAIL reboot syscall requires root")
if platform.machine() != "aarch64":
    raise SystemExit("FAIL reboot syscall is pinned to aarch64")

libc = ctypes.CDLL(None, use_errno=True)
syscall = libc.syscall
syscall.restype = ctypes.c_long
os.sync()
print("PASS guarded fallback RESTART2 bootloader request sent", flush=True)
result = syscall(
    ctypes.c_long(SYS_REBOOT),
    ctypes.c_ulong(LINUX_REBOOT_MAGIC1),
    ctypes.c_ulong(LINUX_REBOOT_MAGIC2),
    ctypes.c_ulong(LINUX_REBOOT_CMD_RESTART2),
    ctypes.c_char_p(b"bootloader"),
)
error = ctypes.get_errno()
raise SystemExit(f"FAIL reboot syscall returned result={result} errno={error}")
PY
REMOTE
)
ssh_status=$?
set -e
printf '%s\n' "$output"

if [[ $action == preflight ]]; then
	[[ $ssh_status == 0 ]] || fail 'fallback preflight SSH failed'
	grep -Fxq \
		'PASS exact persistent fallback ready for guarded bootloader reboot' \
		<<<"$output" ||
		fail 'fallback preflight marker is absent'
	exit 0
fi

restart_marker=0
authenticated_marker=0
if grep -Fxq 'PASS authenticated fallback reboot session' \
	<<<"$output"; then
	authenticated_marker=1
fi
[[ $authenticated_marker == 1 ]] ||
	fail 'authenticated fallback reboot-session marker is absent'
if grep -Fxq 'PASS guarded fallback RESTART2 bootloader request sent' \
	<<<"$output"; then
	restart_marker=1
	[[ $ssh_status == 0 || $ssh_status == 255 ]] ||
		fail "fallback restart2 SSH failed with status $ssh_status"
fi
if [[ $restart_marker == 0 && $ssh_status != 255 ]]; then
	fail "fallback restart2 acknowledgement is absent and SSH exited with status $ssh_status"
fi

fallback_identity=1d6b:0104
fastboot_identity=0b05:4daf
saw_disconnect=0
saw_reenumeration=0
saw_fastboot_usb=0
saw_fallback_return=0
deadline=$(( $(date +%s) + fastboot_timeout ))
while (( $(date +%s) < deadline )); do
	usb_identity=$(usb_identity_at "$fallback_usb_location" 2>/dev/null || true)
	if [[ -z $usb_identity ]]; then
		saw_disconnect=1
	elif [[ $usb_identity != "$fallback_identity" ]]; then
		saw_disconnect=1
		saw_reenumeration=1
		if [[ $usb_identity == "$fastboot_identity" ]]; then
			saw_fastboot_usb=1
			observed_usb_serial=$(read_usb_field \
				"$sys_devices/$fallback_usb_location/serial" \
				2>/dev/null || true)
			if [[ -n $observed_usb_serial &&
				$observed_usb_serial != "$fastboot_serial" ]]; then
				fail 'fastboot serial changed at the anchored USB device'
			fi
		fi
	elif [[ $saw_disconnect == 1 ]]; then
		observed_usb_serial=$(read_usb_field \
			"$sys_devices/$fallback_usb_location/serial" \
			2>/dev/null || true)
		[[ $observed_usb_serial == ROG5LINUX ]] ||
			fail 'fallback serial changed at the anchored USB device'
		saw_reenumeration=1
		saw_fallback_return=1
	fi
	devices=$(fastboot devices 2>/dev/null || true)
	device_count=$(awk 'NF { count++ } END { print count + 0 }' \
		<<<"$devices")
	fastboot_count=$(awk '$2 == "fastboot" { count++ }
		END { print count + 0 }' <<<"$devices")
	if [[ $device_count == 1 && $fastboot_count == 1 ]]; then
		read -r observed_serial observed_state <<<"$devices"
		[[ $observed_serial == "$fastboot_serial" &&
			$observed_state == fastboot ]] ||
			fail 'fastboot device identity does not match the expected serial'
		require_fastboot_usb_at "$fallback_usb_location" "$fastboot_serial"
		set +e
		product_output=$(fastboot -s "$fastboot_serial" \
			getvar product 2>&1)
		product_status=$?
		set -e
		[[ $product_status == 0 ]] ||
			fail 'cannot verify the expected fastboot product'
		product_count=$(grep -Ec \
			'^[[:space:]]*product:[[:space:]]*lahaina[[:space:]]*$' \
			<<<"$product_output" || true)
		product_lines=$(grep -Ec \
			'^[[:space:]]*product:' <<<"$product_output" || true)
		[[ $product_count == 1 && $product_lines == 1 ]] ||
			fail 'fastboot product is not exactly lahaina'
		if [[ $restart_marker == 1 ]]; then
			echo 'PASS exact lahaina fastboot device reached after acknowledged restart2'
		else
			echo 'PASS exact lahaina fastboot device proves restart2 despite SSH disconnect before acknowledgement'
		fi
		exit 0
		fi
	if (( device_count == 1 )); then
		fail 'one fastboot device is present in an unexpected state'
	fi
	(( device_count == 0 )) ||
		fail "expected at most one fastboot device, found $device_count"
	sleep 1
done

[[ $restart_marker == 1 ]] ||
	fail 'fallback restart2 marker was absent and exact fastboot did not appear'
if [[ $saw_disconnect == 0 ]]; then
	fail 'fallback USB never disconnected after the acknowledged bootloader reboot'
fi
if [[ $saw_reenumeration == 0 ]]; then
	fail 'fallback USB disconnected but no anchored-port USB re-enumeration was observed'
fi
if [[ $saw_fallback_return == 1 ]]; then
	fail 'fallback Linux USB returned at the anchored port instead of fastboot'
fi
if [[ $saw_fastboot_usb == 1 ]]; then
	fail 'exact fastboot USB re-enumerated but fastboot userspace discovery did not succeed'
fi
fail 'a non-fastboot USB mode was observed at the anchored port'
