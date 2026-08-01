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

if env -i PATH="$PATH" HOME="$HOME" \
	ROG5_STABLE_RECOVERY_PROFILE=historical-2026-07-29 \
	bash "$gate" policy-preflight >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL policy preflight accepted a profile without complete pins' >&2
	exit 1
fi
grep -Fq 'policy preflight requires the fully pinned diagnostic profile' \
	"$tmp/err"

if env -i PATH="$PATH" HOME="$HOME" \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_HEADLESS_LIVE_GATE=1 \
	ROG5_STABLE_RECOVERY_PROFILE=headless-ssh-deployment-v3 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-ssh-network-root-v3-r2 \
	RECOVERY_SHA256=11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=457273993a9ce3cb0a9c735ef29e96101c1303720cafefc774aed12972a6926e \
	HOST_VERIFIER_SHA256=9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b \
	bash "$gate" boot >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL consumed deployment manifest reached boot admission' >&2
	exit 1
fi
grep -Fq 'refusing a consumed deployment manifest' "$tmp/err"

run_diagnostic_policy() {
	local selected_bundle=$1 selected_image=$2 selected_manifest=$3
	env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-deployment-v1 \
		BUNDLE="$selected_bundle" \
		RECOVERY_SHA256="$selected_image" \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256="$selected_manifest" \
		HOST_VERIFIER_SHA256=9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b \
		bash "$gate" policy-preflight
}

if run_diagnostic_policy \
	headless-netroot-early-diag-v1 \
	11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c \
	9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630 \
	>"$tmp/out" 2>"$tmp/err"; then
	echo 'FAIL diagnostic artifact policy accepted the normal r2 manifest' >&2
	exit 1
fi
grep -Fq 'diagnostic runtime manifest is not allowlisted' "$tmp/err"

if run_diagnostic_policy \
	headless-ssh-network-root-v3-r2 \
	11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c \
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	>"$tmp/out" 2>"$tmp/err"; then
	echo 'FAIL diagnostic artifact policy accepted the normal r2 bundle' >&2
	exit 1
fi
grep -Fq 'profile requires bundle=headless-netroot-early-diag-v1' "$tmp/err"

if run_diagnostic_policy \
	headless-netroot-early-diag-v1 \
	ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff \
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	>"$tmp/out" 2>"$tmp/err"; then
	echo 'FAIL diagnostic artifact policy accepted a wrong recovery image' >&2
	exit 1
fi
grep -Fq 'deployment recovery image identity is not allowlisted' "$tmp/err"

if ! run_diagnostic_policy \
	headless-netroot-early-diag-v1 \
	11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c \
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	>"$tmp/out" 2>"$tmp/err"; then
	echo 'FAIL exact diagnostic policy preflight was rejected' >&2
	exit 1
fi
cat >"$tmp/expected-policy" <<'EOF'
format=rog5-stable-recovery-policy-v1
recovery_profile=headless-diagnostic-deployment-v1
bundle=headless-netroot-early-diag-v1
manifest_sha256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76
bundle_profile=diagnostic-initramfs-v1
target_id=headless-netroot-early-diag
recovery_sha256=11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c
trust_key_sha256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
host_verifier_sha256=9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b
authority=none
result=PASS
EOF
cmp "$tmp/expected-policy" "$tmp/out" || {
	echo 'FAIL diagnostic policy record is not exact and canonical' >&2
	exit 1
}

if env -i PATH="$PATH" HOME="$HOME" \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_HEADLESS_LIVE_GATE=1 \
	ROG5_STABLE_RECOVERY_PROFILE=headless-ssh-deployment-v3 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-ssh-network-root-v3-r2 \
	RECOVERY_SHA256=11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630 \
	HOST_VERIFIER_SHA256=9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b \
	bash "$gate" boot >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL consumed r2 manifest reached direct boot admission' >&2
	exit 1
fi
grep -Fq 'refusing a consumed deployment manifest' "$tmp/err"

# shellcheck disable=SC2016
for required in \
	'ALLOW_HEADLESS_LIVE_GATE' \
	'artifact-preflight' \
	'policy-preflight' \
	'ROG5_STABLE_RECOVERY_PROFILE' \
	'set ROG5_STABLE_RECOVERY_PROFILE explicitly' \
	'corrected-headless-successor-2026-07-30' \
	'headless-ssh-deployment-v3' \
	'headless-diagnostic-deployment-v1' \
	'416d62e4f0d89e9184d8a362c8c9e5091bd265f4c48504916920706f08611430' \
	'bc42d9ffc78ed88c5e8f597905844e472a5681c57caab020ce88c1eae1b706da' \
	'157da94bf50635099c571ce97d3e3c797c22eb66e3b9730b4ea332d952a9261c' \
	'ac5fd5169be86a44b01e8e2d5d5343feddf9ffdc34ea3581a430c5cbc2962c04' \
	'11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c' \
	'expected_kernel=1a8bac7a2b016dc7d63d22f09d0872b9c3f251952b7627c68f7c387f386b0068' \
	'expected_raw=a937b03b54c01c6240cff45aa243632827d0c9d328e6f285ae489c973a6213a9' \
	'expected_initramfs=f414d0ea26ee3aa6cca5c3aa12c1601934294c0207fc2709ebbae305bb3642e0' \
	'expected_control=f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77' \
	'expected_fetcher=677fa731b1bd9fd11efc46aabeb32e7a725725483c86a2f58d417f482c27f392' \
	'expected_target_id=headless-ssh-network-root' \
	'expected_target_id=headless-netroot-early-diag' \
	'f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b' \
	'457273993a9ce3cb0a9c735ef29e96101c1303720cafefc774aed12972a6926e' \
	'9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630' \
	'4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76' \
	'9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b' \
	'expected_bundle=headless-ssh-network-root-v3-r2' \
	'expected_bundle=headless-netroot-early-diag-v1' \
	'expected_bundle_profile=diagnostic-initramfs-v1' \
	'profile requires bundle=$expected_bundle' \
	'profile=$expected_bundle_profile' \
	'target_id=$expected_target_id' \
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
