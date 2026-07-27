#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-network-root-bundle.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing expected SHA-256 manifest}
gpucc_status=${5:-disabled}
smmu_status=${6:-disabled}
expected_loader_sha=${EXPECTED_NETWORK_ROOT_LOADER_SHA256:-current}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)

case $gpucc_status in
	disabled|okay) ;;
	*) echo 'FAIL GPUCC status must be disabled or okay' >&2; exit 1 ;;
esac
case $smmu_status in
	disabled|okay) ;;
	*) echo 'FAIL Adreno SMMU status must be disabled or okay' >&2; exit 1 ;;
esac
[ -r "$expected_sums" ] || {
	echo "FAIL missing $expected_sums" >&2
	exit 1
}

check_hash() {
	file=$1
	expected=$(awk -v file="$file" '$2 == file { print $1 }' "$expected_sums")
	[ "$(printf '%s\n' "$expected" |
		awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] || {
		echo "FAIL manifest entry count for $file" >&2
		exit 1
	}
	case $expected in
		*[!0-9a-f]*|'') echo "FAIL invalid hash for $file" >&2; exit 1 ;;
	esac
	[ "${#expected}" -eq 64 ] || {
		echo "FAIL invalid hash length for $file" >&2
		exit 1
	}
	actual=$(sha256sum "$artifact_dir/$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] || {
		echo "FAIL artifact hash mismatch: $file" >&2
		exit 1
	}
}

required_files='
Image-5.4.210-network-root-stage
config-5.4.210-network-root-stage
embedded-kexec-stage-initramfs.cpio.gz
build-meta-5.4.210-network-root-stage.txt
Image-7.1.4-network-root
Image.gz-7.1.4-network-root
config-7.1.4-network-root
modules-7.1.4-network-root.tar.gz
build-meta-7.1.4-network-root.txt
sm8350-asus-rog-phone5-recovery.dtb
rog5-network-root-initramfs.cpio.gz
rog5-network-root-kexec-stage-initramfs.cpio.gz
boot-5.4.210-network-root-stage.raw.img
boot-5.4.210-network-root-stage.avb.img
'

[ "$(awk 'NF { count++ } END { print count + 0 }' "$expected_sums")" -eq 14 ] || {
	echo 'FAIL expected exactly fourteen manifest entries' >&2
	exit 1
}
for file in $required_files; do
	[ -f "$artifact_dir/$file" ] && [ ! -L "$artifact_dir/$file" ] &&
		[ -s "$artifact_dir/$file" ] || {
		echo "FAIL missing artifact: $file" >&2
		exit 1
	}
	check_hash "$file"
done

dtb=$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb
for node in /soc@0/usb@a6f8800 /soc@0/phy@88e3000; do
	[ "$(fdtget -t s "$dtb" "$node" status)" = okay ]
done
for node in \
	/soc@0/ufshc@1d84000 \
	/soc@0/phy@1d87000 \
	/soc@0/phy@88e8000 \
	/soc@0/usb@a8f8800 \
	/reserved-memory/memory@9b800000 \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000
do
	[ "$(fdtget -t s "$dtb" "$node" status)" = disabled ]
done
[ "$(fdtget -t s "$dtb" \
	/soc@0/clock-controller@3d90000 status)" = "$gpucc_status" ]
[ "$(fdtget -t s "$dtb" \
	/soc@0/iommu@3da0000 status)" = "$smmu_status" ]
usb_dwc3=/soc@0/usb@a6f8800/usb@a600000
[ "$(fdtget -t s "$dtb" "$usb_dwc3" maximum-speed)" = high-speed ]
[ "$(fdtget -t s "$dtb" "$usb_dwc3" phy-names)" = usb2-phy ]
[ "$(fdtget -t x "$dtb" "$usb_dwc3" phys | wc -w)" = 1 ]

wrapper_config=$artifact_dir/config-5.4.210-network-root-stage
wrapper_image=$artifact_dir/Image-5.4.210-network-root-stage
staging_initramfs=$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz
wrapper_meta=$artifact_dir/build-meta-5.4.210-network-root-stage.txt
grep -qx 'CONFIG_KEXEC=y' "$wrapper_config"
grep -qx '# CONFIG_KEXEC_FILE is not set' "$wrapper_config"
grep -qx 'CONFIG_BLK_DEV_INITRD=y' "$wrapper_config"
grep -qx '# CONFIG_PM_AUTOSLEEP is not set' "$wrapper_config"
grep -qx 'CONFIG_INITRAMFS_SOURCE="/root/build/rog5-kexec-stage-initramfs.cpio.gz"' \
	"$wrapper_config"
grep -qx 'CONFIG_INITRAMFS_COMPRESSION=".gz"' "$wrapper_config"
cmp "$artifact_dir/embedded-kexec-stage-initramfs.cpio.gz" "$staging_initramfs"
python3 - "$wrapper_image" "$staging_initramfs" <<'PY'
import sys

image = open(sys.argv[1], "rb").read()
initramfs = open(sys.argv[2], "rb").read()
if image.count(initramfs) != 1:
    raise SystemExit("embedded initramfs count is not one")
PY
strings "$wrapper_image" |
	grep -q 'Linux version 5.4.210.*-kexec-stage-builtin-recovery'
grep -qx 'source_sha256=3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8' \
	"$wrapper_meta"
grep -qx 'kexec_file=0' "$wrapper_meta"
grep -qx "initramfs_sha256=$(sha256sum "$staging_initramfs" | cut -d ' ' -f 1)" \
	"$wrapper_meta"

wrapper_build_root=$(awk '$2 ~ /\/[.]config$/ {
	sub("/[.]config$", "", $2)
	print $2
}' "$wrapper_meta")
[ "$(printf '%s\n' "$wrapper_build_root" |
	awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] || {
	echo 'FAIL wrapper metadata must record exactly one build root' >&2
	exit 1
}
case $wrapper_build_root in
	/root/build/asus-kexec-stage|/root/build/output) ;;
	*) echo 'FAIL unrecognized wrapper metadata build root' >&2; exit 1 ;;
esac

check_meta_hash() {
	meta=$1
	recorded_path=$2
	actual_path=$3
	expected=$(awk -v path="$recorded_path" '$2 == path { print $1 }' "$meta")
	[ "$(printf '%s\n' "$expected" |
		awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] || {
		echo "FAIL metadata entry count for $recorded_path" >&2
		exit 1
	}
	[ "$(sha256sum "$actual_path" | cut -d ' ' -f 1)" = "$expected" ] || {
		echo "FAIL metadata hash mismatch for $recorded_path" >&2
		exit 1
	}
}
check_meta_hash "$wrapper_meta" "$wrapper_build_root/.config" \
	"$wrapper_config"
check_meta_hash "$wrapper_meta" \
	"$wrapper_build_root/arch/arm64/boot/Image" "$wrapper_image"

mainline_config=$artifact_dir/config-7.1.4-network-root
mainline_image=$artifact_dir/Image-7.1.4-network-root
mainline_image_gz=$artifact_dir/Image.gz-7.1.4-network-root
mainline_modules=$artifact_dir/modules-7.1.4-network-root.tar.gz
mainline_meta=$artifact_dir/build-meta-7.1.4-network-root.txt

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir -p "$stage/mainline/arch/arm64/boot" "$stage/target" \
	"$stage/staging" "$stage/boot" "$stage/boot-args"
ln -s "$(realpath "$mainline_meta")" "$stage/mainline/build-meta.txt"
ln -s "$(realpath "$mainline_config")" "$stage/mainline/.config"
ln -s "$(realpath "$mainline_image")" \
	"$stage/mainline/arch/arm64/boot/Image"
ln -s "$(realpath "$mainline_image_gz")" \
	"$stage/mainline/arch/arm64/boot/Image.gz"
ln -s "$(realpath "$mainline_modules")" "$stage/mainline/modules.tar.gz"
"$repo/scripts/device/verify-mainline-network-root-build.sh" "$stage/mainline"
strings "$mainline_image" | grep -q '^Linux version 7\.1\.4-g7a5cef0db479'
if grep -Eq '^CONFIG_SCSI_UFSHCD=(y|m)$' "$mainline_config"; then
	echo 'FAIL CONFIG_SCSI_UFSHCD is enabled in the network-root kernel' >&2
	exit 1
fi
if tar -tzf "$mainline_modules" |
	grep -Ei '/([^/]*ufs[^/]*)\.ko$' >/dev/null; then
	echo 'FAIL UFS-named module in network-root archive' >&2
	exit 1
fi

target_initramfs=$artifact_dir/rog5-network-root-initramfs.cpio.gz
"$repo/scripts/device/verify-network-root-initramfs.sh" "$target_initramfs"
gzip -dc "$target_initramfs" |
	(cd "$stage/target" && cpio -idm --quiet --no-absolute-filenames)
gzip -dc "$staging_initramfs" |
	(cd "$stage/staging" && cpio -idm --quiet --no-absolute-filenames)

cmp "$stage/target/init" "$repo/initramfs/network-root-init"
grep -Fq 'rog5.netroot=1' "$stage/target/init"
cmp "$stage/staging/init" "$repo/initramfs/recovery-init"
embedded_loader=$stage/staging/usr/local/sbin/rog5-load-mainline-recovery
case $expected_loader_sha in
	current)
		cmp "$embedded_loader" \
			"$repo/scripts/device/load-mainline-network-root.sh"
		;;
	*[!0-9a-f]*|'')
		echo 'FAIL invalid expected embedded loader SHA-256' >&2
		exit 1
		;;
	*)
		[ "${#expected_loader_sha}" -eq 64 ]
		[ "$(sha256sum "$embedded_loader" | cut -d ' ' -f 1)" = \
			"$expected_loader_sha" ]
		;;
esac
[ ! -e "$stage/staging/root/.ssh/authorized_keys" ]
[ -z "$(find "$stage/staging/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*' -print -quit)" ]
if find "$stage/target" "$stage/staging" -type f \
	-exec grep -Il 'BEGIN .*PRIVATE KEY' {} + | grep -q .
then
	echo 'FAIL private key exists in a network-root initramfs' >&2
	exit 1
fi
(
	cd "$stage/staging/opt/rog5-recovery"
	sha256sum -c SHA256SUMS
)
cmp "$stage/staging/opt/rog5-recovery/Image" "$mainline_image"
cmp "$stage/staging/opt/rog5-recovery/board.dtb" "$dtb"
cmp "$stage/staging/opt/rog5-recovery/initramfs.cpio.gz" "$target_initramfs"

raw=$artifact_dir/boot-5.4.210-network-root-stage.raw.img
avb=$artifact_dir/boot-5.4.210-network-root-stage.avb.img
boot_info=$(python3 "$mkbootimg_dir/unpack_bootimg.py" \
	--boot_img "$raw" --out "$stage/boot")
printf '%s\n' "$boot_info" | grep -qx 'boot image header version: 3'
python3 "$mkbootimg_dir/unpack_bootimg.py" \
	--boot_img "$raw" --out "$stage/boot-args" \
	--format=mkbootimg --null >"$stage/boot.args"
tr '\000' '\n' <"$stage/boot.args" >"$stage/boot.args.lines"
[ "$(awk '$0 == "--header_version" { getline; print; exit }' \
	"$stage/boot.args.lines")" = 3 ]
[ "$(awk '$0 == "--os_version" { getline; print; exit }' \
	"$stage/boot.args.lines")" = 11.0.0 ]
[ "$(awk '$0 == "--os_patch_level" { getline; print; exit }' \
	"$stage/boot.args.lines")" = 2022-02 ]
command_line=$(awk '$0 == "--cmdline" { getline; print; exit }' \
	"$stage/boot.args.lines")
[ "$(printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep '^ramoops\.[a-z_]*=' | sort -u | wc -l)" -eq 7 ]
[ "$(printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep -c '^rog5\.recovery_cidr=169\.254\.77\.2/16$')" -eq 1 ]
[ "$(printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep -c '^rog5\.recovery_timeout=180$')" -eq 1 ]
if printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep -q '^rog5\.netroot='
then
	echo 'FAIL Android staging command line enables network root' >&2
	exit 1
fi
cmp "$stage/boot/kernel" "$wrapper_image"
cmp "$stage/boot/ramdisk" "$staging_initramfs"

[ "$(stat -c %s "$avb")" = 100663296 ]
head -c "$(stat -c %s "$raw")" "$avb" | cmp - "$raw"
python3 "$avbtool" info_image --image "$avb" >"$stage/avb-info"
grep -q '^Algorithm:[[:space:]]*NONE$' "$stage/avb-info"
grep -q 'Partition Name:[[:space:]]*boot$' "$stage/avb-info"
ln -s "$(realpath "$avb")" "$stage/boot.img"
python3 "$avbtool" verify_image --image "$stage/boot.img" >/dev/null

echo "PASS reproducible credential-free network-root bundle; GPUCC=$gpucc_status; Adreno-SMMU=$smmu_status; offline validation only"
