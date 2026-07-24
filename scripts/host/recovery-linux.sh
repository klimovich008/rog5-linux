#!/bin/sh
set -eu

action=${1:-preflight}
case $action in
	preflight|boot) ;;
	*) echo 'usage: recovery-linux.sh [preflight|boot]' >&2; exit 2 ;;
esac

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd -P)
manifest=$repo/manifests/artifacts.tsv
boot_image=${BOOT_IMAGE:-$repo/artifacts/recovery-stage-v13/boot-5.4.210-kexec-stage-builtin-recovery.avb.img}
fastboot=${FASTBOOT:-fastboot}
fastboot_serial=${FASTBOOT_SERIAL:-}
acm_timeout=${ACM_TIMEOUT:-90}

[ "$(uname -s)" = Linux ] || fail 'this host workflow requires Linux'
for command in awk cut date grep realpath sed sha256sum socat stat; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
[ -r "$boot_image" ] || fail "missing recovery image: $boot_image"
boot_image=$(realpath "$boot_image")
case $boot_image in
	"$repo"/*) artifact_name=${boot_image#"$repo"/} ;;
	*) fail 'recovery image must be inside the repository artifact store' ;;
esac

entry=$(awk -F '\t' -v name="$artifact_name" '$1 == name { print $2 "\t" $3 }' "$manifest")
[ "$(printf '%s\n' "$entry" | awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] ||
	fail "expected one manifest row for $artifact_name"
expected_size=$(printf '%s\n' "$entry" | cut -f 1)
expected_hash=$(printf '%s\n' "$entry" | cut -f 2)
[ "$(stat -c %s "$boot_image")" = "$expected_size" ] ||
	fail 'recovery image size does not match the manifest'
[ "$(sha256sum "$boot_image" | cut -d ' ' -f 1)" = "$expected_hash" ] ||
	fail 'recovery image hash does not match the manifest'

command -v "$fastboot" >/dev/null || fail 'fastboot is missing; install android-tools'
"$fastboot" --version | sed -n '1p'
devices=$("$fastboot" devices 2>/dev/null) || fail 'fastboot devices failed'
if [ -n "$fastboot_serial" ]; then
	printf '%s\n' "$devices" |
		awk -v serial="$fastboot_serial" '$1 == serial && $2 == "fastboot" { found = 1 } END { exit !found }' ||
		fail 'requested fastboot device is not present'
else
	device_count=$(printf '%s\n' "$devices" |
		awk '$2 == "fastboot" { count++ } END { print count + 0 }')
	[ "$device_count" -eq 1 ] ||
		fail "expected exactly one fastboot device, found $device_count"
	fastboot_serial=$(printf '%s\n' "$devices" |
		awk '$2 == "fastboot" { print $1; exit }')
fi

product=$("$fastboot" -s "$fastboot_serial" getvar product 2>&1) ||
	fail 'unable to query the fastboot product'
product=$(printf '%s\n' "$product" |
	sed -n 's/^product:[[:space:]]*//p' | sed -n '1p')
[ -z "$product" ] || echo "INFO fastboot product=$product"

if [ "$action" = preflight ]; then
	echo "PASS Linux recovery preflight image_sha256=$expected_hash"
	exit 0
fi

[ "${ALLOW_TEMPORARY_BOOT:-}" = 1 ] ||
	fail 'set ALLOW_TEMPORARY_BOOT=1 for the attended, non-flashing boot'
command -v udevadm >/dev/null || fail 'missing host command: udevadm'
case $acm_timeout in
	*[!0-9]*|'') fail 'ACM_TIMEOUT must be an integer' ;;
esac
[ "$acm_timeout" -ge 15 ] && [ "$acm_timeout" -le 180 ] ||
	fail 'ACM_TIMEOUT must be between 15 and 180 seconds'

find_recovery_acm() {
	for device in /dev/ttyACM*; do
		[ -e "$device" ] || continue
		properties=$(udevadm info --query=property --name="$device" 2>/dev/null || true)
		printf '%s\n' "$properties" | grep -qx 'ID_VENDOR_ID=1d6b' || continue
		printf '%s\n' "$properties" | grep -qx 'ID_MODEL_ID=0104' || continue
		printf '%s\n' "$device"
		return
	done
	return 0
}

[ -z "$(find_recovery_acm)" ] ||
	fail 'recovery ACM gadget already exists before fastboot boot'
"$fastboot" -s "$fastboot_serial" boot "$boot_image"

deadline=$(( $(date +%s) + acm_timeout ))
acm=
while [ "$(date +%s)" -lt "$deadline" ]; do
	acm=$(find_recovery_acm)
	[ -z "$acm" ] || break
	sleep 1
done
[ -n "$acm" ] || fail 'recovery ACM gadget did not enumerate before timeout'
[ -r "$acm" ] && [ -w "$acm" ] ||
	fail "$acm is not accessible; log in again after joining dialout"

echo "PASS credential-free staging ACM ready at $acm"
echo "INFO rollback remains armed; open the console with:"
echo "socat -,rawer,escape=0x1d $acm,rawer,b115200"
