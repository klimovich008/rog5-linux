#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-kexec-recovery-stage.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256 ACCESS_MODE [AUTHORIZED_KEY]}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing expected SHA-256 manifest}
access_mode=${5:?missing access mode}
authorized_key=${6:-}
[ -r "$expected_sums" ] || { echo "FAIL missing $expected_sums" >&2; exit 1; }
case $access_mode in
	acm-only)
		[ -z "$authorized_key" ] || {
			echo 'FAIL acm-only mode cannot include an authorized key' >&2
			exit 1
		}
		;;
	ssh)
		[ -r "$authorized_key" ] ||
			{ echo 'FAIL authorized key is not readable' >&2; exit 1; }
		grep -Eq '^(ssh-ed25519|ecdsa-sha2-nistp256|ssh-rsa) ' "$authorized_key" ||
			{ echo 'FAIL invalid authorized key format' >&2; exit 1; }
		awk 'NF { count++ } END { exit count != 1 }' "$authorized_key" ||
			{ echo 'FAIL expected exactly one authorized key' >&2; exit 1; }
		;;
	*)
		echo 'FAIL access mode must be acm-only or ssh' >&2
		exit 1
		;;
esac

check_hash() {
	file=$1
	expected=$(awk -v file="$file" '$2 == file { print $1 }' "$expected_sums")
	[ "$(printf '%s\n' "$expected" | awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] || {
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
Image-5.4.210-kexec-stage-builtin-recovery
config-5.4.210-kexec-stage-builtin-recovery
embedded-kexec-stage-initramfs.cpio.gz
Image-7.1.4
sm8350-asus-rog-phone5-recovery.dtb
rog5-recovery-initramfs.cpio.gz
rog5-kexec-stage-initramfs.cpio.gz
boot-5.4.210-kexec-stage-builtin-recovery.raw.img
boot-5.4.210-kexec-stage-builtin-recovery.avb.img
'
manifest_lines=$(awk 'NF { count++ } END { print count + 0 }' "$expected_sums")
[ "$manifest_lines" -eq 9 ] || {
	echo 'FAIL expected exactly nine manifest entries' >&2
	exit 1
}
for file in $required_files; do
	check_hash "$file"
done

config=$artifact_dir/config-5.4.210-kexec-stage-builtin-recovery
grep -qx 'CONFIG_KEXEC=y' "$config"
grep -qx '# CONFIG_KEXEC_FILE is not set' "$config"
grep -qx 'CONFIG_BLK_DEV_INITRD=y' "$config"
grep -qx 'CONFIG_PM_WAKELOCKS=y' "$config"
grep -qx 'CONFIG_INITRAMFS_SOURCE="/root/build/rog5-kexec-stage-initramfs.cpio.gz"' "$config"
grep -qx 'CONFIG_INITRAMFS_COMPRESSION=".gz"' "$config"
cmp "$artifact_dir/embedded-kexec-stage-initramfs.cpio.gz" \
	"$artifact_dir/rog5-kexec-stage-initramfs.cpio.gz"
python3 - "$artifact_dir/Image-5.4.210-kexec-stage-builtin-recovery" \
	"$artifact_dir/embedded-kexec-stage-initramfs.cpio.gz" <<'PY'
import sys

image = open(sys.argv[1], "rb").read()
initramfs = open(sys.argv[2], "rb").read()
if image.count(initramfs) != 1:
    raise SystemExit("embedded initramfs count is not one")
PY
strings "$artifact_dir/Image-5.4.210-kexec-stage-builtin-recovery" |
	grep -q 'Linux version 5.4.210.*-kexec-stage-builtin-recovery'

dtb=$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb
for node in /soc@0/usb@a6f8800 /soc@0/phy@88e3000; do
	[ "$(fdtget -t s "$dtb" "$node" status)" = okay ]
done
for node in \
	/soc@0/ufshc@1d84000 \
	/soc@0/phy@1d87000 \
	/soc@0/phy@88e8000 \
	/soc@0/usb@a8f8800
do
	[ "$(fdtget -t s "$dtb" "$node" status)" = disabled ]
done
usb_dwc3=/soc@0/usb@a6f8800/usb@a600000
[ "$(fdtget -t s "$dtb" "$usb_dwc3" maximum-speed)" = high-speed ]
[ "$(fdtget -t s "$dtb" "$usb_dwc3" phy-names)" = usb2-phy ]
[ "$(fdtget -t x "$dtb" "$usb_dwc3" phys | wc -w)" = 1 ]

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
mkdir "$stage/target" "$stage/staging" "$stage/boot"
gzip -dc "$artifact_dir/rog5-recovery-initramfs.cpio.gz" | \
	(cd "$stage/target" && cpio -idm --quiet --no-absolute-filenames)
gzip -dc "$artifact_dir/rog5-kexec-stage-initramfs.cpio.gz" | \
	(cd "$stage/staging" && cpio -idm --quiet --no-absolute-filenames)

[ -x "$stage/target/init" ]
[ ! -e "$stage/target/opt/rog5-recovery" ]
! grep -q 'mount.*\(userdata\|rootdev\)' "$stage/target/init"
grep -qx 'set -u' "$stage/target/init"
cmp "$stage/target/init" "$(dirname "$0")/../../initramfs/recovery-init"
grep -Fq 'rog5-recovery-rollback' "$stage/target/init"
grep -Fq '>/sys/power/wake_lock' "$stage/target/init"
grep -Fq 'rog5-recovery-acm.pid' "$stage/target/init"
grep -Fq '</proc/self/mountinfo' "$stage/target/init"
grep -Fq 'blockdev --setro' "$stage/target/init"
grep -Fq 'blockdev --getro' "$stage/target/init"
grep -Fq '[ -e "$sys_disk/device" ] || continue' "$stage/target/init"
grep -Fq '[ -e "$sys_block/partition" ] || continue' "$stage/target/init"
grep -Fq 'storage_failure_delay=30' "$stage/target/init"
grep -Fq 'sleep "$storage_failure_delay"' "$stage/target/init"
storage_line=$(grep -n '^if ! isolate_storage; then$' "$stage/target/init" | cut -d: -f1)
usb_line=$(grep -n '^usb_mode=' "$stage/target/init" | cut -d: -f1)
[ "$storage_line" -lt "$usb_line" ]
[ -x "$stage/staging/usr/sbin/kexec" ]
[ -x "$stage/staging/usr/local/sbin/rog5-load-mainline-recovery" ]
grep -qx 'set -u' "$stage/staging/init"
cmp "$stage/staging/init" "$(dirname "$0")/../../initramfs/recovery-init"
cmp "$stage/staging/usr/local/sbin/rog5-load-mainline-recovery" \
	"$(dirname "$0")/load-mainline-recovery.sh"
for root in "$stage/target" "$stage/staging"; do
	[ -x "$root/bin/busybox" ]
	[ "$(readlink "$root/sbin/blockdev")" = /bin/busybox ]
	if [ "$access_mode" = ssh ]; then
		[ -s "$root/root/.ssh/authorized_keys" ]
		[ "$(stat -c %a "$root/root/.ssh/authorized_keys")" = 600 ]
		cmp "$root/root/.ssh/authorized_keys" "$authorized_key"
	else
		[ ! -e "$root/root/.ssh/authorized_keys" ]
	fi
	grep -qx 'PasswordAuthentication no' "$root/etc/ssh/sshd_config"
	grep -qx 'PermitRootLogin prohibit-password' "$root/etc/ssh/sshd_config"
done
! grep -rIl 'BEGIN .*PRIVATE KEY' "$stage/target" "$stage/staging" >/dev/null
readelf -h "$stage/staging/usr/sbin/kexec" | grep -q 'Machine:.*AArch64'

(
	cd "$stage/staging/opt/rog5-recovery"
	sha256sum -c SHA256SUMS
)
[ "$(sha256sum "$stage/staging/opt/rog5-recovery/Image" | cut -d ' ' -f 1)" = \
	"$(sha256sum "$artifact_dir/Image-7.1.4" | cut -d ' ' -f 1)" ]
[ "$(sha256sum "$stage/staging/opt/rog5-recovery/board.dtb" | cut -d ' ' -f 1)" = \
	"$(sha256sum "$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb" | cut -d ' ' -f 1)" ]
[ "$(sha256sum "$stage/staging/opt/rog5-recovery/initramfs.cpio.gz" | cut -d ' ' -f 1)" = \
	"$(sha256sum "$artifact_dir/rog5-recovery-initramfs.cpio.gz" | cut -d ' ' -f 1)" ]

python3 "$mkbootimg_dir/unpack_bootimg.py" \
	--boot_img "$artifact_dir/boot-5.4.210-kexec-stage-builtin-recovery.raw.img" \
	--out "$stage/boot" >/dev/null
python3 "$mkbootimg_dir/unpack_bootimg.py" \
	--boot_img "$artifact_dir/boot-5.4.210-kexec-stage-builtin-recovery.raw.img" \
	--out "$stage/boot-args" --format=mkbootimg --null >"$stage/boot.args"
tr '\000' '\n' <"$stage/boot.args" >"$stage/boot.args.lines"
command_line=$(awk '$0 == "--cmdline" { getline; print; exit }' "$stage/boot.args.lines")
[ "$(printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep '^ramoops\.[a-z_]*=' | sort -u | wc -l)" -eq 7 ]
[ "$(printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep -c '^rog5\.recovery_cidr=')" -eq 1 ]
[ "$(printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep -c '^rog5\.recovery_timeout=')" -eq 1 ]
[ "$(printf '%s\n' "$command_line" | tr ' ' '\n' |
	grep -c '^rog5\.recovery_timeout=180$')" -eq 1 ]
cmp "$stage/boot/kernel" \
	"$artifact_dir/Image-5.4.210-kexec-stage-builtin-recovery"
cmp "$stage/boot/ramdisk" \
	"$artifact_dir/rog5-kexec-stage-initramfs.cpio.gz"

[ "$(stat -c %s "$artifact_dir/boot-5.4.210-kexec-stage-builtin-recovery.avb.img")" = 100663296 ]
raw=$artifact_dir/boot-5.4.210-kexec-stage-builtin-recovery.raw.img
avb=$artifact_dir/boot-5.4.210-kexec-stage-builtin-recovery.avb.img
head -c "$(stat -c %s "$raw")" "$avb" | cmp - "$raw"
python3 "$avbtool" info_image \
	--image "$avb" >"$stage/avb-info"
grep -q '^Algorithm:[[:space:]]*NONE$' "$stage/avb-info"
grep -q 'Partition Name:[[:space:]]*boot$' "$stage/avb-info"
ln -s "$(realpath "$avb")" "$stage/boot.img"
python3 "$avbtool" verify_image --image "$stage/boot.img" >/dev/null

echo 'PASS self-contained two-stage kexec recovery bundle; offline validation only'
