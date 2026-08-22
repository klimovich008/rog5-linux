#!/bin/sh
set -eu

base=${1:?usage: build-storage-layout-stage1-initramfs.sh BASE INIT EXECUTOR WATCHDOG_DISARM PRIVATE_CONFIG PRIVATE_CONFIG_SHA256 SGDISK_APK POPT_APK LIBGCC_APK LIBSTDCXX_APK MUSL_APK LIBUUID_APK OUTPUT}
init=${2:?missing recovery init}
executor=${3:?missing stage-1 executor}
watchdog_disarm=${4:?missing watchdog disarm helper}
private_config=${5:?missing private stage-1 config}
private_config_sha256=${6:?missing private config SHA-256}
sgdisk_apk=${7:?missing sgdisk package}
popt_apk=${8:?missing popt package}
libgcc_apk=${9:?missing libgcc package}
libstdcpp_apk=${10:?missing libstdc++ package}
musl_apk=${11:?missing musl package}
libuuid_apk=${12:?missing libuuid package}
output=${13:?missing output}
epoch=1681862400
executor_sha256=c31ab14e2cc584c0311ad8f271e4544ee7443de80b2677b8922a341e9cc92950
watchdog_disarm_sha256=8949398f9a6245447b3aa4626b85f3f2538e2bf060ced46952514145cb152bbe
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
readonly_builder=$script_dir/build-storage-preflight-initramfs.sh
export LC_ALL=C
export TZ=UTC

fail() {
	echo "FAIL $*" >&2
	exit 1
}

check_hash() {
	actual=$(sha256sum "$1" | cut -d ' ' -f 1)
	[ "$actual" = "$2" ] || fail "input hash mismatch: $(basename "$1")"
}

for command in awk basename chmod cpio cut dirname find grep gzip install \
	mkdir mktemp mv readlink rm sha256sum sort stat touch; do
	command -v "$command" >/dev/null ||
		fail "missing storage-layout build command: $command"
done
for input in "$base" "$init" "$executor" "$watchdog_disarm" "$private_config" "$sgdisk_apk" \
	"$popt_apk" "$libgcc_apk" "$libstdcpp_apk" "$musl_apk" "$libuuid_apk" \
	"$readonly_builder"; do
	[ -f "$input" ] && [ -r "$input" ] && [ ! -L "$input" ] ||
		fail "unsafe storage-layout input: $(basename "$input")"
done
[ -x "$init" ] && [ -x "$executor" ] && [ -x "$watchdog_disarm" ] &&
	[ -x "$readonly_builder" ] ||
	fail 'initramfs programs must be executable'
[ ! -e "$output" ] && [ ! -L "$output" ] ||
	fail 'storage-layout output already exists'
case $private_config_sha256 in
	????????????????????????????????????????????????????????????????) ;;
	*) fail 'private config SHA-256 is not canonical' ;;
esac
case $private_config_sha256 in *[!0-9a-f]*) fail 'private config SHA-256 is not canonical' ;; esac
check_hash "$executor" "$executor_sha256"
check_hash "$watchdog_disarm" "$watchdog_disarm_sha256"
check_hash "$private_config" "$private_config_sha256"

for key in format operation_id disk_guid userdata_type_guid \
	userdata_unique_guid userdata_fs_uuid; do
	[ "$(grep -c "^${key}=" "$private_config")" = 1 ] ||
		fail "private config key changed: $key"
done
if awk -F= '
	BEGIN { ok=1 }
	$1 == "format" && $2 ~ /^rog5-(storage-layout-stage1|userdata-ext4-reset)-v1$/ { format=$2; next }
	$1 == "operation_id" && $2 ~ /^[0-9a-f]{32}$/ { next }
	$1 ~ /^(disk_guid|userdata_type_guid|userdata_unique_guid|userdata_fs_uuid)$/ &&
		$2 ~ /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/ { next }
	$1 == "arch_root_unique_guid" &&
		$2 ~ /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/ { root=1; next }
	{ ok=0 }
	END {
		if (format == "rog5-storage-layout-stage1-v1")
			exit !(ok && NR == 7 && root == 1)
		if (format == "rog5-userdata-ext4-reset-v1")
			exit !(ok && NR == 6 && root == 0)
		exit 1
	}
' "$private_config"; then
	:
else
	fail 'private config contains a non-canonical record'
fi

stage=$(mktemp -d)
output_directory=$(dirname "$output")
mkdir -p "$output_directory"
output_name=$(basename "$output")
temporary=$(mktemp "$output_directory/.${output_name}.tmp.XXXXXX")
readonly_archive=$(mktemp "$output_directory/.${output_name}.readonly.XXXXXX")
rm -f -- "$readonly_archive"
cleanup() {
	rm -rf -- "$stage"
	rm -f -- "$temporary" "$readonly_archive"
}
trap cleanup EXIT HUP INT TERM

"$readonly_builder" "$base" "$init" "$sgdisk_apk" "$popt_apk" \
	"$libgcc_apk" "$libstdcpp_apk" "$musl_apk" "$libuuid_apk" \
	"$readonly_archive" >/dev/null
gzip -dc "$readonly_archive" |
	(cd "$stage" && cpio -idm --quiet --no-absolute-filenames)

chmod 0644 "$stage/etc/rog5/recovery-mode"
printf '%s\n' storage-layout-stage1-v1 >"$stage/etc/rog5/recovery-mode"
chmod 0444 "$stage/etc/rog5/recovery-mode"
mkdir -p "$stage/usr/libexec"
install -m 0755 "$executor" "$stage/usr/libexec/rog5-storage-layout-stage1"
install -m 0755 "$watchdog_disarm" \
	"$stage/usr/libexec/rog5-disarm-recovery-layout-watchdog"
install -m 0400 "$private_config" "$stage/etc/rog5/storage-layout-stage1.conf"
chmod 0400 "$stage/etc/rog5/storage-layout-stage1.conf"

[ ! -e "$stage/usr/libexec/rog5-recovery-control" ] ||
	fail 'interactive recovery control survived stage-1 packaging'
[ ! -e "$stage/usr/sbin/kexec" ] || fail 'kexec survived stage-1 packaging'
for path in init usr/libexec/rog5-storage-layout-stage1 \
	usr/libexec/rog5-disarm-recovery-layout-watchdog usr/bin/sgdisk \
	sbin/e2fsck usr/sbin/dumpe2fs usr/sbin/resize2fs sbin/mkfs.ext4; do
	[ -e "$stage/$path" ] || fail "stage-1 initramfs lacks $path"
done
for path in bin/dd usr/bin/sha256sum sbin/blockdev usr/sbin/partprobe; do
	[ -L "$stage/$path" ] &&
		[ "$(readlink "$stage/$path")" = /bin/busybox ] ||
		fail "stage-1 initramfs lacks fixed BusyBox applet: $path"
done
cmp "$stage/init" "$init" || fail 'packaged recovery init changed'
cmp "$stage/usr/libexec/rog5-storage-layout-stage1" "$executor" ||
	fail 'packaged stage-1 executor changed'
cmp "$stage/usr/libexec/rog5-disarm-recovery-layout-watchdog" "$watchdog_disarm" ||
	fail 'packaged watchdog disarm helper changed'
cmp "$stage/etc/rog5/storage-layout-stage1.conf" "$private_config" ||
	fail 'packaged private config changed'

find "$stage" -exec touch -h -d "@$epoch" {} +
(cd "$stage" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$temporary"
gzip -t "$temporary"
mv -T -- "$temporary" "$output"
trap - EXIT HUP INT TERM
rm -rf -- "$stage"
rm -f -- "$readonly_archive"

sha256sum "$init" "$executor" "$output"
echo "PASS deterministic sealed storage-layout stage-1 initramfs; private_config_sha256=$private_config_sha256"
