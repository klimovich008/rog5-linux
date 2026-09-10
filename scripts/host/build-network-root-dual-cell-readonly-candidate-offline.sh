#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
base_source=${1:-$repo/build/linux-stable-v7.1.4-source}
output_root=${2:-$repo/build/network-root-dual-cell-readonly-candidate-v1}
bootstrap=$repo/scripts/host/bootstrap-kernel-builder.sh
source_preparer=$repo/scripts/device/prepare-mainline-dual-cell-readonly-source.sh
kernel_builder=$repo/scripts/device/build-mainline-network-root.sh
kernel_verifier=$repo/scripts/device/verify-mainline-network-root-dual-cell-readonly-build.sh
kernel_comparator=$repo/scripts/device/compare-mainline-network-root-builds.sh
dual_cell_dtb_builder=$repo/scripts/device/build-dual-cell-readonly-candidate-dtb.sh
dual_cell_dtb_verifier=$repo/scripts/device/verify-dual-cell-readonly-dtb-delta.py
base_dtb=$repo/artifacts/network-root-v3/sm8350-asus-rog-phone5-recovery.dtb
adsp_overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-adsp.dtso
pmic_overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-pmic-glink.dtso
dual_cell_overlay=$repo/dts/qcom/sm8350-asus-rog-phone5-dual-cell-readonly.dtso
patch=$repo/patches/linux-7.1.4/0018-power-supply-qcom-battmgr-add-rog5-cell-voltage.patch
builder_image=localhost/rog5-kernel-builder:ubuntu-24.04
expected_image_id=bdb4bbda79ab38a55c72d23b269f5c3f5cb14d153e373ce50932c17538e9ccaf
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_base_tree=2ea2be38c5e4dc9aafffbbc0db5aae0f6513a1d9
expected_commit=7ee91d34b5458efa0ac45d979bab82bbd2cb7ea5
expected_tree=ef7703ecc0aad3d625cfbbef296e586d861deefe
expected_release=7.1.4-00001-g7ee91d34b545
expected_telemetry_sha=3f4305d7fbbd2c74d15c1011bb8a2e8e24b3a5228f31ed86281917d16cf18f11
jobs=8

for command_name in cmp cut date dtc fdtoverlay find git grep ln mkdir podman realpath \
	sha256sum stat tar; do
	command -v "$command_name" >/dev/null ||
		fail "missing dual-cell release command: $command_name"
done
for input in "$bootstrap" "$source_preparer" "$kernel_builder" \
	"$kernel_verifier" "$kernel_comparator" "$dual_cell_dtb_builder" \
	"$dual_cell_dtb_verifier" "$base_dtb" \
	"$adsp_overlay" "$pmic_overlay" "$dual_cell_overlay" "$patch"; do
	[[ -f $input && ! -L $input && -r $input ]] ||
		fail "unsafe or missing dual-cell release input: $input"
done
for executable in "$bootstrap" "$source_preparer" "$kernel_builder" \
	"$kernel_verifier" "$kernel_comparator" "$dual_cell_dtb_builder" \
	"$dual_cell_dtb_verifier"; do
	[[ -x $executable ]] || fail "release input is not executable: $executable"
done

output_root=$(realpath -m -- "$output_root")
case $output_root in
	"$repo"/build/*) ;;
	*) fail 'dual-cell candidate output must be below the ignored build directory' ;;
esac
git -C "$repo" check-ignore -q "$output_root" ||
	fail 'dual-cell candidate output is not ignored by Git'
[[ ! -e $output_root && ! -L $output_root ]] ||
	fail 'refusing existing dual-cell candidate output root'
mkdir -p -- "$(dirname -- "$output_root")"
lock_dir=$output_root.lock
[[ ! -e $lock_dir && ! -L $lock_dir ]] ||
	fail 'another dual-cell candidate build owns the output lock'
mkdir -- "$lock_dir" ||
	fail 'another dual-cell candidate build owns the output lock'
cleanup_lock() {
	rmdir -- "$lock_dir" 2>/dev/null || true
}
trap cleanup_lock EXIT HUP INT TERM

base_source=$(realpath -e -- "$base_source")
[[ -d $base_source/.git && ! -L $base_source ]] ||
	fail 'missing ordinary accepted Linux source'
[[ $(git -C "$base_source" rev-parse HEAD) == "$expected_base" &&
	$(git -C "$base_source" rev-parse 'HEAD^{tree}') == "$expected_base_tree" ]] ||
	fail 'accepted Linux source commit or tree changed'
[[ -z $(git -C "$base_source" status --porcelain --untracked-files=all) ]] ||
	fail 'accepted Linux source is dirty'

[[ ! -e $output_root && ! -L $output_root ]] ||
	fail 'dual-cell candidate output appeared after locking'
mkdir -- "$output_root"
stage=$output_root
started_ns=$(date +%s%N)

"$bootstrap" verify "$builder_image" >"$stage/builder.txt"
actual_image_id=$(podman image inspect --format '{{.Id}}' "$builder_image")
[[ $actual_image_id == "$expected_image_id" ]] ||
	fail "qualified kernel builder image changed: $actual_image_id"

build_one() {
	local suffix=$1
	local source=$stage/source-$suffix
	local output=$stage/build-$suffix
	mkdir -- "$output"
	podman run --rm --pull=never --network=none --security-opt label=disable \
		-v "$repo:/workspace/repo:ro" \
		-v "$source:/root/src/linux-7.1.4:ro" \
		-v "$output:/root/build/rog5-linux-7.1.4-network-root" \
		-e LINUX_COMMIT="$expected_commit" \
		-e EXPECTED_RELEASE="$expected_release" \
		-e INCREMENTAL_BUILD=0 \
		-e KBUILD_CCACHE=0 \
		-e JOBS="$jobs" \
		"$builder_image" \
		/workspace/repo/scripts/device/build-mainline-network-root.sh
	podman run --rm --pull=never --network=none --security-opt label=disable \
		-v "$repo:/workspace/repo:ro" \
		-v "$output:/root/build/rog5-linux-7.1.4-network-root:ro" \
		"$builder_image" \
		/workspace/repo/scripts/device/verify-mainline-network-root-dual-cell-readonly-build.sh \
		/root/build/rog5-linux-7.1.4-network-root
}

prepare_started=$(date +%s%N)
"$source_preparer" "$base_source" "$stage/source-a" >"$stage/source-a.txt"
prepare_a_ms=$((($(date +%s%N) - prepare_started) / 1000000))
prepare_started=$(date +%s%N)
"$source_preparer" "$base_source" "$stage/source-b" >"$stage/source-b.txt"
prepare_b_ms=$((($(date +%s%N) - prepare_started) / 1000000))
cmp -- "$stage/source-a.txt" "$stage/source-b.txt"
build_started=$(date +%s%N)
build_one a 2>&1 | tee "$stage/build-a.log"
build_a_ms=$((($(date +%s%N) - build_started) / 1000000))
build_started=$(date +%s%N)
build_one b 2>&1 | tee "$stage/build-b.log"
build_b_ms=$((($(date +%s%N) - build_started) / 1000000))
"$kernel_comparator" "$stage/build-a" "$stage/build-b"

build_telemetry_dtb() {
	local suffix=$1
	local output=$stage/telemetry-$suffix.dtb
	for fresh in "$stage/adsp-$suffix.dtbo" "$stage/pmic-$suffix.dtbo" "$output"; do
		[[ ! -e $fresh && ! -L $fresh ]] ||
			fail "refusing existing telemetry twin output: $fresh"
	done
	dtc -q -@ -I dts -O dtb -o "$stage/adsp-$suffix.dtbo" "$adsp_overlay"
	dtc -q -@ -I dts -O dtb -o "$stage/pmic-$suffix.dtbo" "$pmic_overlay"
	fdtoverlay -i "$base_dtb" -o "$output" \
		"$stage/adsp-$suffix.dtbo" "$stage/pmic-$suffix.dtbo"
	dtc -q -I dtb -O dts -o /dev/null "$output"
	[[ $(sha256sum "$output" | cut -d ' ' -f 1) == "$expected_telemetry_sha" ]] ||
		fail "current telemetry DTB identity changed: $suffix"
}

build_telemetry_dtb a
build_telemetry_dtb b
cmp -- "$stage/telemetry-a.dtb" "$stage/telemetry-b.dtb"
"$dual_cell_dtb_builder" "$stage/telemetry-a.dtb" "$dual_cell_overlay" \
	"$stage/dual-cell-a.dtb" >/dev/null
"$dual_cell_dtb_builder" "$stage/telemetry-b.dtb" "$dual_cell_overlay" \
	"$stage/dual-cell-b.dtb" >/dev/null
cmp -- "$stage/dual-cell-a.dtb" "$stage/dual-cell-b.dtb"
"$dual_cell_dtb_verifier" "$stage/telemetry-a.dtb" \
	"$stage/dual-cell-a.dtb" >/dev/null

module_member=lib/modules/$expected_release/kernel/drivers/power/supply/qcom_battmgr.ko
tar --warning=no-timestamp -xOf "$stage/build-a/modules.tar.gz" "$module_member" \
	>"$stage/qcom-battmgr-a.ko"
tar --warning=no-timestamp -xOf "$stage/build-b/modules.tar.gz" "$module_member" \
	>"$stage/qcom-battmgr-b.ko"
cmp -- "$stage/qcom-battmgr-a.ko" "$stage/qcom-battmgr-b.ko"

manifest_one() {
	local build=$1
	local telemetry=$2
	local dtb=$3
	local module=$4
	local output=$5
	local logical actual
	{
		printf '%s\n' \
			'format=rog5-network-root-dual-cell-readonly-candidate-v1' \
			'status=compile-only-clean-twins' \
			'execution_state=unbooted' \
			'authority=none' \
			'boot_authority=none' \
			'hardware_acceptance=unproven' \
			'incremental_build=disabled' \
			'compiler_cache=disabled' \
			"jobs=$jobs" \
			"builder_image=$builder_image" \
			"builder_image_id=$expected_image_id" \
			"source_parent=$expected_base" \
			"source_commit=$expected_commit" \
			"source_tree=$expected_tree" \
			"kernel_release=$expected_release" \
			"patch_sha256=$(sha256sum "$patch" | cut -d ' ' -f 1)" \
			"adsp_overlay_sha256=$(sha256sum "$adsp_overlay" | cut -d ' ' -f 1)" \
			"pmic_overlay_sha256=$(sha256sum "$pmic_overlay" | cut -d ' ' -f 1)" \
			"dual_cell_overlay_sha256=$(sha256sum "$dual_cell_overlay" | cut -d ' ' -f 1)" \
			"telemetry_base_sha256=$(sha256sum "$telemetry" | cut -d ' ' -f 1)"
		for logical in config Image Image.gz modules.tar.gz Module.symvers \
			build-meta.txt qcom_battmgr.ko rog5-dual-cell-readonly.dtb; do
			case $logical in
				config) actual=$build/.config ;;
				Image) actual=$build/arch/arm64/boot/Image ;;
				Image.gz) actual=$build/arch/arm64/boot/Image.gz ;;
				modules.tar.gz) actual=$build/modules.tar.gz ;;
				Module.symvers) actual=$build/Module.symvers ;;
				build-meta.txt) actual=$build/build-meta.txt ;;
				qcom_battmgr.ko) actual=$module ;;
				rog5-dual-cell-readonly.dtb) actual=$dtb ;;
			esac
			printf 'artifact=%s size=%s sha256=%s\n' "$logical" \
				"$(stat -c %s "$actual")" \
				"$(sha256sum "$actual" | cut -d ' ' -f 1)"
		done
	} >"$output"
}

manifest_one "$stage/build-a" "$stage/telemetry-a.dtb" \
	"$stage/dual-cell-a.dtb" "$stage/qcom-battmgr-a.ko" \
	"$stage/manifest-a.txt"
manifest_one "$stage/build-b" "$stage/telemetry-b.dtb" \
	"$stage/dual-cell-b.dtb" "$stage/qcom-battmgr-b.ko" \
	"$stage/manifest-b.txt"
cmp -- "$stage/manifest-a.txt" "$stage/manifest-b.txt"

candidate=$stage/candidate
mkdir -- "$candidate"
ln -- "$stage/build-a/.config" "$candidate/config"
ln -- "$stage/build-a/arch/arm64/boot/Image" "$candidate/Image"
ln -- "$stage/build-a/arch/arm64/boot/Image.gz" "$candidate/Image.gz"
ln -- "$stage/build-a/modules.tar.gz" "$candidate/modules.tar.gz"
ln -- "$stage/build-a/Module.symvers" "$candidate/Module.symvers"
ln -- "$stage/build-a/build-meta.txt" "$candidate/build-meta.txt"
ln -- "$stage/qcom-battmgr-a.ko" "$candidate/qcom_battmgr.ko"
ln -- "$stage/dual-cell-a.dtb" "$candidate/rog5-dual-cell-readonly.dtb"
ln -- "$stage/manifest-a.txt" "$candidate/manifest.txt"
chmod 0644 -- "$candidate"/*

for artifact in config Image Image.gz modules.tar.gz Module.symvers \
	build-meta.txt qcom_battmgr.ko rog5-dual-cell-readonly.dtb; do
	line=$(grep -E "^artifact=$artifact " "$candidate/manifest.txt")
	[[ $(grep -Ec "^artifact=$artifact " "$candidate/manifest.txt") == 1 ]] ||
		fail "candidate manifest has a non-unique artifact: $artifact"
	expected_size=$(sed -n "s/^artifact=$artifact size=\([0-9][0-9]*\) sha256=.*/\1/p" \
		<<<"$line")
	expected_hash=$(sed -n "s/^artifact=$artifact size=[0-9][0-9]* sha256=\([0-9a-f]\{64\}\)$/\1/p" \
		<<<"$line")
	[[ $(stat -c %s "$candidate/$artifact") == "$expected_size" &&
		$(sha256sum "$candidate/$artifact" | cut -d ' ' -f 1) == "$expected_hash" ]] ||
		fail "published candidate artifact changed: $artifact"
done
grep -Fxq 'authority=none' "$candidate/manifest.txt"
grep -Fxq 'boot_authority=none' "$candidate/manifest.txt"
grep -Fxq 'hardware_acceptance=unproven' "$candidate/manifest.txt"

finished_ns=$(date +%s%N)
printf '%s\n' \
	"source_prepare_a_ms=$prepare_a_ms" \
	"source_prepare_b_ms=$prepare_b_ms" \
	"clean_build_a_ms=$build_a_ms" \
	"clean_build_b_ms=$build_b_ms" \
	"total_before_prune_ms=$(((finished_ns - started_ns) / 1000000))" \
	>"$stage/timings.txt"

# Retain only the release products and compact evidence after every twin,
# semantic, DT-delta, manifest, and publication gate has passed.
find "$stage/source-a" -depth -delete
find "$stage/source-b" -depth -delete
find "$stage/build-a" -depth -delete
find "$stage/build-b" -depth -delete
for disposable in adsp-a.dtbo adsp-b.dtbo pmic-a.dtbo pmic-b.dtbo \
	telemetry-a.dtb telemetry-b.dtb dual-cell-a.dtb \
	dual-cell-b.dtb qcom-battmgr-a.ko qcom-battmgr-b.ko manifest-a.txt \
	manifest-b.txt; do
	rm -f -- "$stage/$disposable"
done

cat "$stage/timings.txt"
sha256sum "$candidate/manifest.txt"
echo 'authority=none'
echo 'boot_authority=none'
echo 'PASS clean twin network-root dual-cell candidate assembled offline; no phone boot is authorized'
