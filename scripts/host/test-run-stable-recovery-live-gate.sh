#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
gate=$repo/scripts/host/run-stable-recovery-live-gate.sh
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM

if env -i PATH="$PATH" HOME="$HOME" bash "$gate" boot \
	>"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL unguarded stable-recovery boot passed' >&2
	exit 1
fi
grep -Fq 'ALLOW_TEMPORARY_BOOT=1' "$tmp/err"
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL unguarded boot reached host inspection' >&2
	exit 1
fi

# shellcheck disable=SC2016
for required in \
	'ALLOW_HEADLESS_LIVE_GATE' \
	'cmp "$image" "$twin_image"' \
	'verify-stable-recovery-initramfs.sh' \
	'--bundle-root "$bundle_root"' \
	'verify_image --image "$inspection/recovery.img"' \
	'cp --reflink=never -- "$raw" "$inspection/boot.img"' \
	'getvar product' \
	'verified-fastboot-boot.py' \
	'cmp -n "$raw_size" "$raw" "$image"' \
	'find_rog5_acm ROG5_recovery' \
	'stop ModemManager'
do
	grep -Fq -- "$required" "$gate"
done

# The final pattern is intentionally literal shell source, not an expansion here.
# shellcheck disable=SC2016
for forbidden in ' fastboot flash ' ' fastboot erase ' ' fastboot format ' \
	' fastboot set_active ' '"$fastboot" -s "$fastboot_serial" boot' \
	' adb ' ' ssh '; do
	! grep -Fq -- "$forbidden" "$gate" ||
		{ echo "FAIL live gate contains forbidden action: $forbidden" >&2; exit 1; }
done

echo 'PASS stable-recovery live gate is exact, twin-built, guarded, and boot-only'
