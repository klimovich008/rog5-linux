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

if [[ $action == reboot ]]; then
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

deadline=$(( $(date +%s) + 45 ))
while (( $(date +%s) < deadline )); do
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
	(( device_count == 0 )) ||
		fail "expected at most one fastboot device, found $device_count"
	sleep 1
done

[[ $restart_marker == 1 ]] ||
	fail 'fallback restart2 marker was absent and exact fastboot did not appear'
fail 'fastboot did not appear after the guarded fallback reboot'
