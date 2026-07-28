#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
artifact_relative=artifacts/persistent-root-entry-v1
artifact_dir=$repo/$artifact_relative
manifest=$repo/manifests/artifacts.tsv
mkbootimg_dir=$repo/../work/linux-server/mkbootimg
avbtool=$repo/../work/linux-server/avb/avbtool.py
target_image=$repo/artifacts/persistent-root-p2/Image-7.1.4-persistent-root
target_dtb=$repo/artifacts/persistent-root-p2/sm8350-asus-rog-phone5-persistent-root.dtb
target_init_source=$repo/initramfs/persistent-root-entry-init
loader=$repo/scripts/device/load-mainline-persistent-root-entry.sh

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in awk cmp cpio find gzip head python3 readelf \
	sha256sum stat strings; do
	command -v "$command" >/dev/null ||
		fail "missing P2 entry verifier command: $command"
done
[ -r "$manifest" ] || fail 'missing artifact manifest'
[ "$(sha256sum "$mkbootimg_dir/mkbootimg.py" | cut -d ' ' -f 1)" = \
	d99136f30bda966e8820c8ae53a82c659ca36e6d1aaf49a4cd63ae4795a6845a ]
[ "$(sha256sum "$mkbootimg_dir/unpack_bootimg.py" | cut -d ' ' -f 1)" = \
	7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef ]
[ "$(sha256sum "$avbtool" | cut -d ' ' -f 1)" = \
	6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff ]

check_artifact() {
	name=$1
	expected_size=$2
	expected_hash=$3
	path=$artifact_dir/$name
	relative=$artifact_relative/$name
	[ -f "$path" ] && [ ! -L "$path" ] ||
		fail "missing or linked P2 entry artifact: $name"
	[ "$(stat -c %s "$path")" = "$expected_size" ] ||
		fail "P2 entry artifact size changed: $name"
	[ "$(stat -c %a "$path")" = 644 ] ||
		fail "P2 entry artifact mode changed: $name"
	[ "$(sha256sum "$path" | cut -d ' ' -f 1)" = "$expected_hash" ] ||
		fail "P2 entry artifact hash changed: $name"
	rows=$(awk -F '\t' -v name="$relative" '$1 == name { count++ }
		END { print count + 0 }' "$manifest")
	[ "$rows" -eq 1 ] ||
		fail "expected one manifest row for P2 entry artifact: $name"
	awk -F '\t' -v name="$relative" -v size="$expected_size" \
		-v hash="$expected_hash" \
		'$1 == name && $2 == size && $3 == hash { found++ }
		END { exit found != 1 }' "$manifest" ||
		fail "manifest identity changed for P2 entry artifact: $name"
}

check_artifact rog5-persistent-root-entry-initramfs.cpio.gz \
	5839811 09f7e69daf270c584b1947f41872a9af512c47e26fb2e8a30d3cdfb2fcc5d7a5
check_artifact rog5-persistent-root-entry-kexec-stage.cpio.gz \
	26674329 3360abb8b47cdc5ffd5be59664b979fad186611442bd8224ced225084a4ecc73
check_artifact Image-5.4.210-persistent-root-entry-wrapper \
	69372416 5171ab75e55dc2de330f126dbffc42fc380a4fc04f623368e775375d48cc8fbc
check_artifact config-5.4.210-persistent-root-entry-wrapper \
	185763 df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
check_artifact build-meta-5.4.210-persistent-root-entry-wrapper.txt \
	442 36ef17a26a65f9a78a72469f7b44391da0d3a1b77491c5dcb96f662ba5a1f0c6
check_artifact boot-5.4.210-persistent-root-entry.raw.img \
	96055296 36455b88ac36bc88b449893096bba839ac12fe229065b4a23d55687a3b9c8079
check_artifact boot-5.4.210-persistent-root-entry.avb.img \
	100663296 5489638517ebd83684702e6197ea459d890c6274b328cc6a3373b65a05442b3e

[ "$(sha256sum "$target_image" | cut -d ' ' -f 1)" = \
	832757fc6b97554813a14049123667bc6f5b225e6204ca048d73c3a36c76469f ]
[ "$(sha256sum "$target_dtb" | cut -d ' ' -f 1)" = \
	36802458928e2970a0043f6a27d106e6aa4911fd89b2f548e7c08275d164aaf0 ]
[ "$(sha256sum "$target_init_source" | cut -d ' ' -f 1)" = \
	26117ef6ebefb718ceda7f843f2ab826381134a8e109297be1836d70c0219393 ]
[ "$(sha256sum "$loader" | cut -d ' ' -f 1)" = \
	a21f2a653c6237253cd0039fec2e15c9348afe714ec3e77b9e2c7b5baf78f8af ]

cmp "$artifact_dir/rog5-persistent-root-entry-initramfs.cpio.gz" \
	"$artifact_dir/rog5-persistent-root-entry-initramfs.a.cpio.gz"
cmp "$artifact_dir/rog5-persistent-root-entry-initramfs.cpio.gz" \
	"$artifact_dir/rog5-persistent-root-entry-initramfs.b.cpio.gz"
cmp "$artifact_dir/rog5-persistent-root-entry-kexec-stage.cpio.gz" \
	"$artifact_dir/rog5-persistent-root-entry-kexec-stage.a.cpio.gz"
cmp "$artifact_dir/rog5-persistent-root-entry-kexec-stage.cpio.gz" \
	"$artifact_dir/rog5-persistent-root-entry-kexec-stage.b.cpio.gz"
for stem in \
	Image-5.4.210-persistent-root-entry-wrapper \
	config-5.4.210-persistent-root-entry-wrapper; do
	cmp "$artifact_dir/$stem" "$artifact_dir/$stem.a"
	cmp "$artifact_dir/$stem" "$artifact_dir/$stem.b"
done
cmp "$artifact_dir/build-meta-5.4.210-persistent-root-entry-wrapper.txt" \
	"$artifact_dir/build-meta-5.4.210-persistent-root-entry-wrapper.a.txt"
cmp "$artifact_dir/build-meta-5.4.210-persistent-root-entry-wrapper.txt" \
	"$artifact_dir/build-meta-5.4.210-persistent-root-entry-wrapper.b.txt"
for kind in raw avb; do
	cmp "$artifact_dir/boot-5.4.210-persistent-root-entry.$kind.img" \
		"$artifact_dir/boot-5.4.210-persistent-root-entry.a.$kind.img"
	cmp "$artifact_dir/boot-5.4.210-persistent-root-entry.$kind.img" \
		"$artifact_dir/boot-5.4.210-persistent-root-entry.b.$kind.img"
done

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
target_initramfs=$artifact_dir/rog5-persistent-root-entry-initramfs.cpio.gz
staging_initramfs=$artifact_dir/rog5-persistent-root-entry-kexec-stage.cpio.gz
wrapper_image=$artifact_dir/Image-5.4.210-persistent-root-entry-wrapper
wrapper_config=$artifact_dir/config-5.4.210-persistent-root-entry-wrapper
wrapper_meta=$artifact_dir/build-meta-5.4.210-persistent-root-entry-wrapper.txt
raw=$artifact_dir/boot-5.4.210-persistent-root-entry.raw.img
avb=$artifact_dir/boot-5.4.210-persistent-root-entry.avb.img

mkdir "$stage/target" "$stage/staging"
gzip -t "$target_initramfs"
gzip -dc "$target_initramfs" |
	(cd "$stage/target" && cpio -idm --quiet --no-absolute-filenames)
cmp "$stage/target/init" "$target_init_source"
[ -x "$stage/target/init" ]
[ ! -e "$stage/target/root/.ssh/authorized_keys" ]
[ -z "$(find "$stage/target/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*' -print -quit)" ]
! find "$stage/target" -type f \
	-exec grep -Il 'BEGIN .*PRIVATE KEY' {} + | grep -q .
grep -Fq 'ROG5 P2 entry oracle' "$stage/target/init"
grep -Fq 'rog5.p2_entry_diag=1' "$stage/target/init"
if grep -Eq \
	'/dev/(sd|mmcblk|nvme)|mount[[:space:]].*(ext[234]|f2fs|btrfs)|blockdev|fsck|mkfs|/rog5/|authorized_keys|dropbear|sshd' \
	"$stage/target/init"; then
	fail 'P2 entry target contains a storage or credential path'
fi

gzip -t "$staging_initramfs"
gzip -dc "$staging_initramfs" |
	(cd "$stage/staging" && cpio -idm --quiet --no-absolute-filenames)
cmp "$stage/staging/opt/rog5-recovery/Image" "$target_image"
cmp "$stage/staging/opt/rog5-recovery/board.dtb" "$target_dtb"
cmp "$stage/staging/opt/rog5-recovery/initramfs.cpio.gz" \
	"$target_initramfs"
cmp "$stage/staging/usr/local/sbin/rog5-load-mainline-recovery" \
	"$loader"
(cd "$stage/staging/opt/rog5-recovery" &&
	sha256sum -c SHA256SUMS >/dev/null)
[ ! -e "$stage/staging/root/.ssh/authorized_keys" ]
[ -z "$(find "$stage/staging/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*' -print -quit)" ]
! find "$stage/staging" -type f \
	-exec grep -Il 'BEGIN .*PRIVATE KEY' {} + | grep -q .

for setting in \
	'CONFIG_KEXEC=y' \
	'# CONFIG_KEXEC_FILE is not set' \
	'CONFIG_INITRAMFS_SOURCE="/root/build/rog5-kexec-stage-initramfs.cpio.gz"' \
	'CONFIG_INITRAMFS_COMPRESSION=".gz"' \
	'CONFIG_LOCALVERSION="-qgki-perf-kexec-stage-builtin-recovery"'; do
	grep -Fqx "$setting" "$wrapper_config"
done
grep -qx \
	'source_sha256=3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8' \
	"$wrapper_meta"
grep -qx 'kexec_file=0' "$wrapper_meta"
grep -qx \
	'initramfs_sha256=3360abb8b47cdc5ffd5be59664b979fad186611442bd8224ced225084a4ecc73' \
	"$wrapper_meta"
grep -qx 'compiler=Ubuntu clang version 18.1.3 (1ubuntu1)' "$wrapper_meta"
grep -Fq \
	'df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f  /root/build/asus-kexec-stage/.config' \
	"$wrapper_meta"
grep -Fq \
	'5171ab75e55dc2de330f126dbffc42fc380a4fc04f623368e775375d48cc8fbc  /root/build/asus-kexec-stage/arch/arm64/boot/Image' \
	"$wrapper_meta"
strings "$wrapper_image" |
	grep -q 'Linux version 5.4.210.*-qgki-perf-kexec-stage-builtin-recovery'
python3 - "$wrapper_image" "$staging_initramfs" <<'PY'
import sys

image = open(sys.argv[1], "rb").read()
initramfs = open(sys.argv[2], "rb").read()
if image.count(initramfs) != 1:
    raise SystemExit("embedded P2 entry stage count is not one")
PY

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
for forbidden in \
	rog5.ufs_discovery= \
	rog5.persistent_ro= \
	rog5.p2_entry_diag=; do
	! printf '%s\n' "$command_line" | tr ' ' '\n' |
		grep -q "^$forbidden"
done
printf '%s\n' "$command_line" | tr ' ' '\n' | sort \
	>"$stage/cmdline.tokens"
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

"$repo/scripts/device/test-persistent-root-entry-initramfs.sh" >/dev/null
"$repo/scripts/device/test-load-mainline-persistent-root-entry.sh" >/dev/null
"$repo/scripts/device/test-persistent-root-entry-kexec-stage-initramfs.sh" \
	>/dev/null
"$repo/scripts/device/test-persistent-root-entry-asus-kexec-stage-build-contract.sh" \
	>/dev/null
python3 "$repo/scripts/host/test-persistent-root-entry-acm.py" >/dev/null

echo 'PASS reproducible credential-free RAM-only P2 early-entry bundle; offline validation only'
