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

if env -i PATH="$PATH" HOME="$HOME" bash "$gate" artifact-preflight \
	>"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL stable-recovery profile defaulted implicitly' >&2
	exit 1
fi
grep -Fq 'set ROG5_STABLE_RECOVERY_PROFILE explicitly' "$tmp/err"
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL absent profile reached host inspection' >&2
	exit 1
fi

# shellcheck disable=SC2016
for required in \
	'ALLOW_HEADLESS_LIVE_GATE' \
	'artifact-preflight' \
	'ROG5_STABLE_RECOVERY_PROFILE' \
	'set ROG5_STABLE_RECOVERY_PROFILE explicitly' \
	'corrected-headless-successor-2026-07-30' \
	'416d62e4f0d89e9184d8a362c8c9e5091bd265f4c48504916920706f08611430' \
	'bc42d9ffc78ed88c5e8f597905844e472a5681c57caab020ce88c1eae1b706da' \
	'157da94bf50635099c571ce97d3e3c797c22eb66e3b9730b4ea332d952a9261c' \
	'ac5fd5169be86a44b01e8e2d5d5343feddf9ffdc34ea3581a430c5cbc2962c04' \
	'9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b' \
	'artifacts/android-boot-tools-v1/avbtool.py' \
	'qualified-cpio-path/cpio' \
	'7520899a405e1fc698875e047d8671c9415116e944831135a8e8eb6a93a21580' \
	'qualified cpio path must contain only the pinned cpio' \
	'component_layout=structured' \
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

artifact_exit=$(
	grep -n 'if \[\[ \$action == artifact-preflight \]\]' "$gate" |
		tail -1 | cut -d: -f1
)
fastboot_devices=$(
	grep -n 'devices 2>/dev/null' "$gate" | cut -d: -f1
)
[[ $artifact_exit =~ ^[0-9]+$ && $fastboot_devices =~ ^[0-9]+$ &&
	$artifact_exit -lt $fastboot_devices ]] ||
	{ echo 'FAIL artifact preflight can reach fastboot inspection' >&2; exit 1; }

# The final pattern is intentionally literal shell source, not an expansion here.
# shellcheck disable=SC2016
for forbidden in ' fastboot flash ' ' fastboot erase ' ' fastboot format ' \
	' fastboot set_active ' '"$fastboot" -s "$fastboot_serial" boot' \
	' adb ' ' ssh '; do
	! grep -Fq -- "$forbidden" "$gate" ||
		{ echo "FAIL live gate contains forbidden action: $forbidden" >&2; exit 1; }
done

echo 'PASS stable-recovery live gate is exact, twin-built, guarded, and boot-only'
