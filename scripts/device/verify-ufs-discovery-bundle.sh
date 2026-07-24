#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-ufs-discovery-bundle.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing expected SHA-256 manifest}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)

[ -r "$expected_sums" ] || { echo "FAIL missing $expected_sums" >&2; exit 1; }

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
Image-5.4.210-ufs-discovery-stage
config-5.4.210-ufs-discovery-stage
embedded-kexec-stage-initramfs.cpio.gz
build-meta-5.4.210-ufs-discovery-stage.txt
Image-7.1.4-ufs-discovery
config-7.1.4-ufs-discovery
build-meta-7.1.4-ufs-discovery.txt
sm8350-asus-rog-phone5-base.dtb
sm8350-asus-rog-phone5-ufs-discovery.dtb
rog5-ufs-discovery-initramfs.cpio.gz
rog5-ufs-discovery-kexec-stage-initramfs.cpio.gz
boot-5.4.210-ufs-discovery-stage.raw.img
boot-5.4.210-ufs-discovery-stage.avb.img
'
manifest_lines=$(awk 'NF { count++ } END { print count + 0 }' "$expected_sums")
[ "$manifest_lines" -eq 13 ] || {
	echo 'FAIL expected exactly thirteen manifest entries' >&2
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
[ "$(sha256sum "$artifact_dir/sm8350-asus-rog-phone5-base.dtb" |
	cut -d ' ' -f 1)" = \
	'e1b7ec966d5ad66febaeb10e7bbff0d92b7e83ab4159d9727e5a175b719bedeb' ]

wrapper_config=$artifact_dir/config-5.4.210-ufs-discovery-stage
wrapper_image=$artifact_dir/Image-5.4.210-ufs-discovery-stage
staging_initramfs=$artifact_dir/rog5-ufs-discovery-kexec-stage-initramfs.cpio.gz
wrapper_meta=$artifact_dir/build-meta-5.4.210-ufs-discovery-stage.txt
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
check_meta_hash "$wrapper_meta" /root/build/output/.config "$wrapper_config"
check_meta_hash "$wrapper_meta" /root/build/output/arch/arm64/boot/Image "$wrapper_image"

mainline_config=$artifact_dir/config-7.1.4-ufs-discovery
mainline_image=$artifact_dir/Image-7.1.4-ufs-discovery
mainline_meta=$artifact_dir/build-meta-7.1.4-ufs-discovery.txt
grep -qx 'base_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40' "$mainline_meta"
grep -qx 'patched_commit=44fd886a77b8edd4ea2abda8f72835045d877e18' "$mainline_meta"
grep -qx 'patched_tree=c3eb1dcf56c5b2047e04fcc83a512a971c75f387' "$mainline_meta"
grep -qx 'python_hash_seed=0' "$mainline_meta"
grep -qx 'pahole_jobs=1' "$mainline_meta"
check_meta_hash "$mainline_meta" /repo/configs/kernel/rog5-mainline.fragment \
	"$repo/configs/kernel/rog5-mainline.fragment"
check_meta_hash "$mainline_meta" /repo/configs/kernel/rog5-ufs-discovery.fragment \
	"$repo/configs/kernel/rog5-ufs-discovery.fragment"
check_meta_hash "$mainline_meta" /root/build/output/.config "$mainline_config"
check_meta_hash "$mainline_meta" /root/build/output/arch/arm64/boot/Image "$mainline_image"

for symbol in \
	CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y \
	CONFIG_SCSI=y \
	CONFIG_SCSI_UFSHCD=y \
	CONFIG_SCSI_UFSHCD_PLATFORM=y \
	CONFIG_SCSI_UFS_QCOM=y \
	CONFIG_PHY_QCOM_QMP=y \
	CONFIG_PHY_QCOM_QMP_UFS=y \
	CONFIG_BLK_DEV_SD=y \
	CONFIG_EFI_PARTITION=y \
	CONFIG_PINCTRL_SM8350=y \
	CONFIG_REGULATOR_QCOM_RPMH=y \
	CONFIG_INTERCONNECT_QCOM_SM8350=y \
	CONFIG_QCOM_COMMAND_DB=y \
	CONFIG_QCOM_RPMH=y \
	CONFIG_RESET_QCOM_AOSS=y \
	CONFIG_USB=y \
	CONFIG_USB_DWC3=y \
	CONFIG_USB_DWC3_QCOM=y \
	CONFIG_USB_GADGET=y \
	CONFIG_USB_CONFIGFS=y \
	CONFIG_USB_CONFIGFS_ACM=y \
	CONFIG_USB_CONFIGFS_NCM=y \
	CONFIG_PHY_QCOM_USB_SNPS_FEMTO_V2=y \
	CONFIG_IKCONFIG=y \
	CONFIG_IKCONFIG_PROC=y; do
	grep -qx "$symbol" "$mainline_config" || {
		echo "FAIL final config: $symbol" >&2
		exit 1
	}
done
for symbol in \
	CHR_DEV_SG BLK_DEV_BSG SCSI_UFS_BSG RPMB SCSI_UFS_CRYPTO \
	SCSI_UFS_HWMON PHY_QCOM_QMP_COMBO PHY_QCOM_QMP_PCIE \
	PHY_QCOM_QMP_PCIE_8996 PHY_QCOM_QMP_USB PHY_QCOM_QMP_USB_LEGACY; do
	grep -qx "# CONFIG_$symbol is not set" "$mainline_config" || {
		echo "FAIL final config must disable CONFIG_$symbol" >&2
		exit 1
	}
done
strings "$mainline_image" | grep -q '^Linux version 7\.1\.4-g44fd886a77b8'
for marker in \
	'ROG5 UFS discovery: forced read-only before registration' \
	'ROG5 UFS discovery: blocked SCSI opcode' \
	'ROG5 UFS discovery: blocked device query' \
	'ROG5 UFS discovery: optional device writes and high-speed gear switch disabled'; do
	strings "$mainline_image" | grep -Fq "$marker" || {
		echo "FAIL compiled guard marker missing: $marker" >&2
		exit 1
	}
done

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
mkdir "$stage/target" "$stage/staging" "$stage/boot" "$stage/boot-args"

"$repo/scripts/device/build-ufs-discovery-candidate-dtb.sh" \
	"$artifact_dir/sm8350-asus-rog-phone5-base.dtb" \
	"$repo/dts/qcom/sm8350-asus-rog-phone5-ufs-discovery.dtso" \
	"$stage/rebuilt-discovery.dtb" >/dev/null
cmp "$stage/rebuilt-discovery.dtb" \
	"$artifact_dir/sm8350-asus-rog-phone5-ufs-discovery.dtb"

gzip -dc "$artifact_dir/rog5-ufs-discovery-initramfs.cpio.gz" |
	(cd "$stage/target" && cpio -idm --quiet --no-absolute-filenames)
gzip -dc "$staging_initramfs" |
	(cd "$stage/staging" && cpio -idm --quiet --no-absolute-filenames)

for root in "$stage/target" "$stage/staging"; do
	[ -x "$root/init" ]
	[ -x "$root/bin/busybox" ]
	[ "$(readlink "$root/sbin/blockdev")" = /bin/busybox ]
	[ ! -e "$root/root/.ssh/authorized_keys" ]
	[ -z "$(find "$root/etc/ssh" -maxdepth 1 -type f -name 'ssh_host_*' -print -quit)" ]
	grep -qx 'PasswordAuthentication no' "$root/etc/ssh/sshd_config"
	grep -qx 'PermitRootLogin prohibit-password' "$root/etc/ssh/sshd_config"
done
! grep -rIl 'BEGIN .*PRIVATE KEY' "$stage/target" "$stage/staging" >/dev/null

target_init=$stage/target/init
cmp "$target_init" "$repo/initramfs/recovery-init"
grep -qx 'set -u' "$target_init"
grep -Fq 'touch /run/rog5-recovery-armed' "$target_init"
grep -Fq 'CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y' "$target_init"
grep -Fq '/run/rog5-ufs-inventory.tsv' "$target_init"
grep -Fq 'UFS sysfs-only inventory ready' "$target_init"
grep -Fq '[ "$(cat /run/rog5-physical-block-count)" -gt 0 ]' "$target_init"
[ "$(grep -Fc '[ ! -e "$sys_disk/partition" ] || continue' "$target_init")" -eq 3 ]
! grep -Eq 'blkid|fsck|mount[[:space:]].*/dev/' "$target_init"

watchdog_line=$(grep -n '^touch /run/rog5-recovery-armed$' "$target_init" | cut -d: -f1)
wait_line=$(grep -n "log 'waiting for stable UFS discovery'" "$target_init" | cut -d: -f1)
storage_lines=$(grep -n '^if ! isolate_storage; then$' "$target_init" | cut -d: -f1)
[ "$(printf '%s\n' "$storage_lines" |
	awk 'NF { count++ } END { print count + 0 }')" -eq 2 ]
storage_line=$(printf '%s\n' "$storage_lines" | sed -n '1p')
post_mdev_storage_line=$(printf '%s\n' "$storage_lines" | sed -n '2p')
inventory_line=$(grep -n '^[[:space:]]*if ! write_ufs_inventory; then$' \
	"$target_init" | cut -d: -f1)
usb_line=$(grep -n '^usb_mode=' "$target_init" | cut -d: -f1)
mdev_line=$(grep -n '^if ! mdev -s; then$' "$target_init" | cut -d: -f1)
tty_line=$(grep -n '^\[ -c /dev/ttyGS0 \] || {$' "$target_init" | cut -d: -f1)
acm_line=$(grep -n '^serve_acm &$' "$target_init" | cut -d: -f1)
bind_line=$(grep -n '^[[:space:]]*echo "\$udc" >"\$gadget/UDC"$' \
	"$target_init" | cut -d: -f1)
[ "$watchdog_line" -lt "$wait_line" ]
[ "$wait_line" -lt "$storage_line" ]
[ "$storage_line" -lt "$inventory_line" ]
[ "$inventory_line" -lt "$usb_line" ]
[ "$mdev_line" -lt "$tty_line" ]
[ "$tty_line" -lt "$post_mdev_storage_line" ]
[ "$post_mdev_storage_line" -lt "$acm_line" ]
[ "$acm_line" -lt "$bind_line" ]

[ -x "$stage/staging/usr/sbin/kexec" ]
[ -x "$stage/staging/usr/local/sbin/rog5-load-mainline-recovery" ]
cmp "$stage/staging/init" "$repo/initramfs/recovery-init"
cmp "$stage/staging/usr/local/sbin/rog5-load-mainline-recovery" \
	"$repo/scripts/device/load-mainline-ufs-discovery.sh"
readelf -h "$stage/staging/usr/sbin/kexec" | grep -q 'Machine:.*AArch64'
(
	cd "$stage/staging/opt/rog5-recovery"
	sha256sum -c SHA256SUMS
)
cmp "$stage/staging/opt/rog5-recovery/Image" "$mainline_image"
cmp "$stage/staging/opt/rog5-recovery/board.dtb" \
	"$artifact_dir/sm8350-asus-rog-phone5-ufs-discovery.dtb"
cmp "$stage/staging/opt/rog5-recovery/initramfs.cpio.gz" \
	"$artifact_dir/rog5-ufs-discovery-initramfs.cpio.gz"

raw=$artifact_dir/boot-5.4.210-ufs-discovery-stage.raw.img
avb=$artifact_dir/boot-5.4.210-ufs-discovery-stage.avb.img
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
	grep -c '^rog5\.recovery_cidr=')" -eq 1 ]
[ "$(printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep -c '^rog5\.recovery_timeout=180$')" -eq 1 ]
! printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep -q '^rog5\.ufs_discovery='
printf '%s\n' "$command_line" | tr ' ' '\n' | sort >"$stage/cmdline.tokens"
cat >"$stage/expected-cmdline.tokens" <<'EOF'
init=/init
printk.devkmsg=on
ramoops.console_size=0x300000
ramoops.dump_oops=1
ramoops.ftrace_size=0
ramoops.mem_address=0x9b800000
ramoops.mem_size=0x400000
ramoops.pmsg_size=0
ramoops.record_size=0x100000
rog5.recovery_cidr=169.254.77.2/16
rog5.recovery_timeout=180
rog5linux.test=1
selinux=0
EOF
sort -o "$stage/expected-cmdline.tokens" "$stage/expected-cmdline.tokens"
cmp "$stage/cmdline.tokens" "$stage/expected-cmdline.tokens"
cmp "$stage/boot/kernel" "$wrapper_image"
cmp "$stage/boot/ramdisk" "$staging_initramfs"

[ "$(stat -c %s "$avb")" = 100663296 ]
head -c "$(stat -c %s "$raw")" "$avb" | cmp - "$raw"
python3 "$avbtool" info_image --image "$avb" >"$stage/avb-info"
grep -q '^Algorithm:[[:space:]]*NONE$' "$stage/avb-info"
grep -q 'Partition Name:[[:space:]]*boot$' "$stage/avb-info"
ln -s "$(realpath "$avb")" "$stage/boot.img"
python3 "$avbtool" verify_image --image "$stage/boot.img" >/dev/null

echo 'PASS reproducible credential-free UFS discovery bundle; offline validation only'
