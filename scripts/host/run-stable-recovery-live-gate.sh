#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

action=${1:-preflight}
case $action in
	policy-preflight) ;;
	artifact-preflight) ;;
	preflight) ;;
	boot)
		[[ ${ALLOW_TEMPORARY_BOOT:-} == 1 ]] ||
			fail 'set ALLOW_TEMPORARY_BOOT=1 for one non-flashing boot'
		[[ ${ALLOW_HEADLESS_LIVE_GATE:-} == 1 ]] ||
			fail 'set ALLOW_HEADLESS_LIVE_GATE=1 for this attended candidate'
		;;
	*)
		fail 'usage: run-stable-recovery-live-gate.sh [policy-preflight|artifact-preflight|preflight|boot]'
		;;
esac

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
profile=${ROG5_STABLE_RECOVERY_PROFILE:-}
[[ -n $profile ]] ||
	fail 'set ROG5_STABLE_RECOVERY_PROFILE explicitly'
if [[ $action == policy-preflight &&
	$profile != headless-diagnostic-deployment-v1 ]]; then
	fail 'policy preflight requires the fully pinned diagnostic profile'
fi
live_root=${LIVE_BUILD_ROOT:-}
component_root=${RECOVERY_COMPONENT_ROOT:-}
trust_key=${TRUST_KEY:-}
bundle_root=${BUNDLE_ROOT:-}
bundle=${BUNDLE:-}
expected_image=${RECOVERY_SHA256:-}
expected_trust=${TRUST_KEY_SHA256:-}
expected_manifest=${MANIFEST_SHA256:-}
expected_host_verifier=${HOST_VERIFIER_SHA256:-}
fastboot=/usr/bin/fastboot
fastboot_serial=${FASTBOOT_SERIAL:-}
acm_timeout=${ACM_TIMEOUT:-90}
component_layout=
expected_kernel=
expected_raw=
expected_initramfs=
expected_target_id=
expected_bundle=
expected_bundle_profile=network-root-v1
consumed_deployment_manifest=457273993a9ce3cb0a9c735ef29e96101c1303720cafefc774aed12972a6926e
consumed_r2_manifest=9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630
requires_qualified_cpio=0
expected_control=c1e1b7b58f36b9ff091bed3b5de463d6239031729a49e12c07064c410de43fd0
expected_fetcher=becc3fc1442823118fa75e79a9b756395df9f1b5b7df37440d4e2c8c5b4ef89c
expected_verifier=374900be5769eee074820007ab2e335d4c033c500da7a480cc88f9a70137029b
expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
avbtool=
unpack=
initramfs_path=$PATH
qualified_cpio=
qualified_cpio_shim=

[[ -n $bundle ]] || fail 'set the exact bundle input'
if [[ $action != policy-preflight ]]; then
	[[ -n $live_root && -n $component_root && -n $trust_key &&
		-n $bundle_root ]] ||
		fail 'set live-build, component, trust-key, and bundle inputs'
fi
for value in "$expected_image" "$expected_trust" "$expected_manifest" \
	"$expected_host_verifier"; do
	[[ $value =~ ^[0-9a-f]{64}$ &&
		$value != 0000000000000000000000000000000000000000000000000000000000000000 ]] ||
		fail 'every expected identity must be one nonzero SHA-256'
done
[[ $bundle =~ ^[a-z0-9][a-z0-9._-]{0,63}$ &&
	$bundle != *..* && $bundle != none ]] ||
	fail 'invalid bundle identity'
if [[ $action == boot &&
	( $expected_manifest == "$consumed_deployment_manifest" ||
	$expected_manifest == "$consumed_r2_manifest" ) ]]; then
	fail 'refusing a consumed deployment manifest'
fi

case $profile in
	historical-2026-07-29)
		component_layout=flat
		expected_kernel=91732d1bdbf73c5f574d87eb0d07b5394db2889e4c0dc4b258577a0bcdb0101f
		expected_raw=854c48adb4316bc8496579ebab78cfbbd3e0550fe0c5204ae3c5661187818fb4
		expected_initramfs=6245147d464985df3d861d2b177ea39f6132767b45c07e39a131fecf3bf69aa2
		expected_target_id=headless-network-root
		avbtool=$repo/../work/linux-server/avb/avbtool.py
		unpack=$repo/../work/linux-server/mkbootimg/unpack_bootimg.py
		;;
	corrected-headless-successor-2026-07-30)
		component_layout=structured
		expected_kernel=bc42d9ffc78ed88c5e8f597905844e472a5681c57caab020ce88c1eae1b706da
		expected_raw=157da94bf50635099c571ce97d3e3c797c22eb66e3b9730b4ea332d952a9261c
		expected_initramfs=ac5fd5169be86a44b01e8e2d5d5343feddf9ffdc34ea3581a430c5cbc2962c04
		expected_target_id=headless-network-root
		[[ $expected_image == \
			416d62e4f0d89e9184d8a362c8c9e5091bd265f4c48504916920706f08611430 ]] ||
			fail 'successor recovery image identity is not allowlisted'
		[[ $expected_trust == \
			ce9f89c9c1859a3239615932da36617f3436f9a0355c8db9c852a1b764f2dfeb ]] ||
			fail 'successor recovery trust root is not allowlisted'
		[[ $expected_manifest == \
			d7a02a2403caf885a015060a8361019936e86efafde44f3bb7e6bdd48d2ee32d ]] ||
			fail 'successor runtime manifest is not allowlisted'
		[[ $expected_host_verifier == \
			9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b ]] ||
			fail 'successor host verifier is not allowlisted'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-ssh-deployment-v3 | headless-diagnostic-deployment-v1)
		component_layout=structured
		expected_kernel=1a8bac7a2b016dc7d63d22f09d0872b9c3f251952b7627c68f7c387f386b0068
		expected_raw=a937b03b54c01c6240cff45aa243632827d0c9d328e6f285ae489c973a6213a9
		expected_initramfs=f414d0ea26ee3aa6cca5c3aa12c1601934294c0207fc2709ebbae305bb3642e0
		expected_control=f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77
		expected_fetcher=677fa731b1bd9fd11efc46aabeb32e7a725725483c86a2f58d417f482c27f392
		if [[ $profile == headless-ssh-deployment-v3 ]]; then
			expected_target_id=headless-ssh-network-root
			expected_bundle=headless-ssh-network-root-v3-r2
			[[ $expected_manifest == \
				9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630 ]] ||
				fail 'deployment runtime manifest is not allowlisted'
		else
			expected_target_id=headless-netroot-early-diag
			expected_bundle=headless-netroot-early-diag-v1
			expected_bundle_profile=diagnostic-initramfs-v1
			[[ $expected_manifest == \
				4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 ]] ||
				fail 'diagnostic runtime manifest is not allowlisted'
		fi
		[[ $expected_image == \
			11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c ]] ||
			fail 'deployment recovery image identity is not allowlisted'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'deployment recovery trust root is not allowlisted'
		[[ $expected_host_verifier == \
			9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b ]] ||
			fail 'deployment host verifier is not allowlisted'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	*) fail "unsupported stable-recovery live profile: $profile" ;;
esac
[[ -z $expected_bundle || $bundle == "$expected_bundle" ]] ||
	fail "profile requires bundle=$expected_bundle"

if [[ $action == policy-preflight ]]; then
	printf '%s\n' \
		'format=rog5-stable-recovery-policy-v1' \
		"recovery_profile=$profile" \
		"bundle=$bundle" \
		"manifest_sha256=$expected_manifest" \
		"bundle_profile=$expected_bundle_profile" \
		"target_id=$expected_target_id" \
		"recovery_sha256=$expected_image" \
		"trust_key_sha256=$expected_trust" \
		"host_verifier_sha256=$expected_host_verifier" \
		'authority=none' \
		'result=PASS'
	exit 0
fi

for command in awk cmp cp cut find git grep mktemp python3 realpath sha256sum \
	stat tr; do
	command -v "$command" >/dev/null ||
		fail "missing live-gate command: $command"
done
[[ $(uname -s) == Linux ]] || fail 'the live gate requires Linux'
if [[ $action != artifact-preflight ]]; then
	for command in sed systemctl; do
		command -v "$command" >/dev/null ||
			fail "missing live-gate command: $command"
	done
	[[ -f $fastboot && ! -L $fastboot && -x $fastboot &&
		$(stat -Lc '%u:%g:%a:%F' "$fastboot") == \
		'0:0:755:regular file' ]] ||
		fail 'fixed root-owned fastboot executable is unavailable'
	systemctl is-active --quiet ModemManager.service &&
		fail 'stop ModemManager before the recovery ACM is exposed'
fi
if [[ $action == boot ]]; then
	for command in date sleep udevadm wc; do
		command -v "$command" >/dev/null ||
			fail "missing live-gate command: $command"
	done
fi

live_root=$(realpath -e "$live_root")
component_root=$(realpath -e "$component_root")
trust_key=$(realpath -e "$trust_key")
bundle_root=$(realpath -e "$bundle_root")
case $live_root in
	"$repo"/build/*) ;;
	*) fail 'live build root must be below the ignored build directory' ;;
esac
git -C "$repo" check-ignore -q "$live_root" ||
	fail 'live build root is not ignored by Git'
case $component_root in
	"$repo"/build/*) ;;
	*) fail 'recovery component root must be below the ignored build directory' ;;
esac
git -C "$repo" check-ignore -q "$component_root" ||
	fail 'recovery component root is not ignored by Git'
if [[ $action == artifact-preflight ]]; then
	case $bundle_root in
		"$repo"/build/*) ;;
		*) fail 'artifact-preflight bundle root must remain below build' ;;
	esac
	git -C "$repo" check-ignore -q "$bundle_root" ||
		fail 'artifact-preflight bundle root is not ignored by Git'
else
	[[ $bundle_root == /var/lib/rog5-recovery-bundles ]] ||
		fail 'unexpected recovery bundle root'
fi

image=$live_root/repack/stable-recovery-a.avb.img
twin_image=$live_root/repack/stable-recovery-b.avb.img
raw=$live_root/repack/stable-recovery-a.raw.img
twin_raw=$live_root/repack/stable-recovery-b.raw.img
kernel=$live_root/wrapper-a/asus-kexec-stage/arch/arm64/boot/Image
twin_kernel=$live_root/wrapper-b/asus-kexec-stage/arch/arm64/boot/Image
ramdisk=$live_root/wrapper-a/rog5-kexec-stage-initramfs.cpio.gz
twin_ramdisk=$live_root/wrapper-b/rog5-kexec-stage-initramfs.cpio.gz
config=$live_root/wrapper-a/asus-kexec-stage/.config
twin_config=$live_root/wrapper-b/asus-kexec-stage/.config
case $component_layout in
	flat)
		control=$component_root/rog5-recovery-control
		fetcher=$component_root/rog5-bundle-fetch
		verifier=$component_root/rog5-bundle-verify
		host_verifier=$component_root/rog5-bundle-verify-host-test
		source_initramfs=$component_root/stable-recovery-a.cpio.gz
		twin_source_initramfs=$component_root/stable-recovery-b.cpio.gz
		;;
	structured)
		control=$component_root/components/rog5-recovery-control
		fetcher=$component_root/components/rog5-bundle-fetch
		verifier=$component_root/components/rog5-bundle-verify
		host_verifier=$component_root/components/rog5-bundle-verify-host-test
		source_initramfs=$component_root/initramfs-a/rog5-stable-recovery.cpio.gz
		twin_source_initramfs=$component_root/initramfs-b/rog5-stable-recovery.cpio.gz
		;;
esac
manifest=$bundle_root/$bundle/manifest

for input in "$image" "$twin_image" "$raw" "$twin_raw" "$kernel" \
	"$twin_kernel" "$ramdisk" "$twin_ramdisk" "$config" "$twin_config" \
	"$control" "$fetcher" "$verifier" "$host_verifier" \
	"$source_initramfs" "$twin_source_initramfs" "$trust_key" "$manifest" \
	"$avbtool" "$unpack"; do
	[[ -f $input && ! -L $input && -r $input ]] ||
		fail "unsafe or missing live input: $input"
done
if [[ $requires_qualified_cpio == 1 ]]; then
	for input in "$qualified_cpio" "$qualified_cpio_shim"; do
		[[ -f $input && ! -L $input && -x $input ]] ||
			fail "unsafe or missing qualified cpio input: $input"
	done
	mapfile -d '' -t qualified_cpio_entries < <(
		find "$repo/scripts/host/qualified-cpio-path" \
			-mindepth 1 -maxdepth 1 -print0
	)
	[[ ${#qualified_cpio_entries[@]} -eq 1 &&
		${qualified_cpio_entries[0]} == "$qualified_cpio" ]] ||
		fail 'qualified cpio path must contain only the pinned cpio'
fi
[[ $(stat -c %s "$image") == 100663296 &&
	$(stat -c %s "$twin_image") == 100663296 ]] ||
	fail 'temporary AVB wrapper has the wrong partition size'
[[ $(stat -c %s "$trust_key") == 32 ]] ||
	fail 'recovery trust root is not a raw Ed25519 public key'
cmp "$image" "$twin_image"
cmp "$raw" "$twin_raw"
cmp "$kernel" "$twin_kernel"
cmp "$ramdisk" "$twin_ramdisk"
cmp "$config" "$twin_config"
cmp "$source_initramfs" "$twin_source_initramfs"
cmp "$ramdisk" "$source_initramfs"

check_hash() {
	local input=$1 expected=$2
	[[ $(sha256sum "$input" | cut -d ' ' -f 1) == "$expected" ]] ||
		fail "identity mismatch: $input"
}
check_hash "$image" "$expected_image"
check_hash "$trust_key" "$expected_trust"
check_hash "$manifest" "$expected_manifest"
check_hash "$host_verifier" "$expected_host_verifier"
check_hash "$kernel" "$expected_kernel"
check_hash "$raw" "$expected_raw"
check_hash "$source_initramfs" "$expected_initramfs"
check_hash "$control" "$expected_control"
check_hash "$fetcher" "$expected_fetcher"
check_hash "$verifier" "$expected_verifier"
check_hash "$config" "$expected_config"
if [[ $requires_qualified_cpio == 1 ]]; then
	check_hash "$qualified_cpio" \
		7520899a405e1fc698875e047d8671c9415116e944831135a8e8eb6a93a21580
	check_hash "$qualified_cpio_shim" \
		a0a0a1d5b134d18470cc2fc55b0220fa464057e95ba05145e3dde6338ed59b58
fi

env PATH="$initramfs_path" \
	"$repo/scripts/device/verify-stable-recovery-initramfs.sh" \
	"$source_initramfs" "$repo/initramfs/recovery-init" \
	"$control" "$fetcher" "$verifier" "$trust_key"

verified_plan=$(
	"$host_verifier" --bundle-root "$bundle_root" \
		--trust-key "$trust_key" "$bundle" "$expected_manifest"
)
grep -Fxq "bundle=$bundle" <<<"$verified_plan"
grep -Fxq "manifest_sha256=$expected_manifest" <<<"$verified_plan"
grep -Fxq "profile=$expected_bundle_profile" <<<"$verified_plan"
grep -Fxq "target_id=$expected_target_id" <<<"$verified_plan"
grep -Fxq 'target_release=7.1.4-g7a5cef0db479' <<<"$verified_plan"
grep -Fxq 'target_timeout=480' <<<"$verified_plan"

check_hash "$avbtool" \
	6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff
check_hash "$unpack" \
	7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef

inspection=$(mktemp -d)
trap 'rm -rf -- "$inspection"' EXIT HUP INT TERM
# avbtool resolves a "boot" hash descriptor as boot.img beside the wrapper.
# Private copies prevent an unrelated sibling from satisfying that descriptor.
cp --reflink=never -- "$image" "$inspection/recovery.img"
cp --reflink=never -- "$raw" "$inspection/boot.img"
cmp "$inspection/recovery.img" "$image"
cmp "$inspection/boot.img" "$raw"
check_hash "$inspection/recovery.img" "$expected_image"
python3 "$avbtool" verify_image --image "$inspection/recovery.img"
avb_info=$(python3 "$avbtool" info_image --image "$inspection/recovery.img")
grep -q '^Algorithm:[[:space:]]*NONE$' <<<"$avb_info"
grep -q '^      Partition Name:[[:space:]]*boot$' <<<"$avb_info"
cmp "$inspection/recovery.img" "$image"
cmp "$inspection/boot.img" "$raw"

python3 "$unpack" --boot_img "$raw" --out "$inspection" \
	--format=mkbootimg --null >"$inspection/args.nul"
raw_size=$(stat -c %s "$raw")
[[ $raw_size -gt 0 && $raw_size -lt 100663296 ]] ||
	fail 'raw wrapper size is invalid'
cmp -n "$raw_size" "$raw" "$image" ||
	fail 'raw wrapper is not the exact AVB image prefix'
python3 "$unpack" --boot_img "$image" --out "$inspection/booted" \
	--format=mkbootimg --null >"$inspection/booted-args.nul"
tr '\000' '\n' <"$inspection/booted-args.nul" \
	>"$inspection/booted-args.lines"
cmp "$inspection/booted/kernel" "$kernel"
cmp "$inspection/booted/ramdisk" "$ramdisk"
cmp "$inspection/kernel" "$inspection/booted/kernel"
cmp "$inspection/ramdisk" "$inspection/booted/ramdisk"
cmp "$inspection/kernel" "$kernel"
cmp "$inspection/ramdisk" "$ramdisk"
tr '\000' '\n' <"$inspection/args.nul" >"$inspection/args.lines"
command_line=$(
	awk '$0 == "--cmdline" { getline; print; exit }' \
		"$inspection/booted-args.lines"
)
for token in init=/init selinux=0 rog5linux.test=1 rog5.recovery_timeout=180; do
	[[ $(tr ' ' '\n' <<<"$command_line" | grep -Fxc "$token" || true) == 1 ]] ||
		fail "missing or duplicate wrapper token: $token"
done
if tr ' ' '\n' <<<"$command_line" |
	grep -Eq '^(root=|resume=|rog5\.recovery_cidr=|rog5\.ufs_discovery=)'
then
	fail 'physical-storage or legacy network input reached the recovery wrapper'
fi

if [[ $action == artifact-preflight ]]; then
	echo "PASS stable-recovery artifact preflight profile=$profile image_sha256=$expected_image"
	exit 0
fi

devices=$("$fastboot" devices 2>/dev/null) ||
	fail 'fastboot devices failed'
if [[ -n $fastboot_serial ]]; then
	awk -v serial="$fastboot_serial" \
		'$1 == serial && $2 == "fastboot" { found=1 } END { exit !found }' \
		<<<"$devices" ||
		fail 'requested fastboot device is not present'
else
	count=$(awk '$2 == "fastboot" { count++ } END { print count + 0 }' \
		<<<"$devices")
	[[ $count == 1 ]] ||
		fail "expected exactly one fastboot device, found $count"
	fastboot_serial=$(awk '$2 == "fastboot" { print $1; exit }' <<<"$devices")
fi
product=$("$fastboot" -s "$fastboot_serial" getvar product 2>&1) ||
	fail 'unable to query fastboot product'
product=$(sed -n \
	's/^(bootloader)[[:space:]]*//; s/^product:[[:space:]]*//p' \
	<<<"$product" | sed -n '1p')
[[ $product == lahaina ]] ||
	fail "unexpected fastboot product: ${product:-missing}"

if [[ $action == preflight ]]; then
	echo "PASS exact boot-only live gate profile=$profile image_sha256=$expected_image"
	exit 0
fi

[[ $acm_timeout =~ ^[0-9]+$ && $acm_timeout -ge 15 &&
	$acm_timeout -le 180 ]] ||
	fail 'ACM_TIMEOUT must be between 15 and 180 seconds'

find_rog5_acm() {
	local expected=$1 device properties
	for device in /dev/ttyACM*; do
		[[ -e $device ]] || continue
		properties=$(udevadm info --query=property --name="$device" 2>/dev/null ||
			true)
		grep -qx 'ID_VENDOR_ID=1d6b' <<<"$properties" || continue
		grep -qx 'ID_MODEL_ID=0104' <<<"$properties" || continue
		grep -qx "ID_MODEL=$expected" <<<"$properties" || continue
		printf '%s\n' "$device"
	done
}

[[ -z $(find_rog5_acm ROG5_recovery) ]] ||
	fail 'recovery ACM already exists before temporary boot'
python3 "$repo/scripts/host/verified-fastboot-boot.py" \
	"$image" "$expected_image" "$fastboot_serial"

deadline=$(( $(date +%s) + acm_timeout ))
acm=
while (( $(date +%s) < deadline )); do
	acm=$(find_rog5_acm ROG5_recovery)
	[[ -z $acm ]] || break
	sleep 1
done
[[ $(wc -w <<<"$acm") == 1 && -r $acm && -w $acm ]] ||
	fail 'exact recovery ACM did not enumerate uniquely'
echo "PASS temporary stable recovery ready at $acm"
echo "INFO profile=$profile; no payload has been committed; rollback remains armed"
