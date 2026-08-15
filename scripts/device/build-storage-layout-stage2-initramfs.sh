#!/bin/sh
set -eu

base=${1:?usage: build-storage-layout-stage2-initramfs.sh BASE INIT EXECUTOR WATCHDOG_DISARM PRIVATE_CONFIG PRIVATE_CONFIG_SHA256 NATIVE_SEAL VERIFIER SGDISK_APK POPT_APK LIBGCC_APK LIBSTDCXX_APK MUSL_APK LIBUUID_APK OUTPUT}
init=${2:?missing recovery init}
executor=${3:?missing stage-2 executor}
watchdog_disarm=${4:?missing watchdog disarm helper}
private_config=${5:?missing private stage-2 config}
private_config_sha256=${6:?missing private config SHA-256}
native_seal=${7:?missing native-root seal}
verifier=${8:?missing persistent-root verifier}
sgdisk_apk=${9:?missing sgdisk package}
popt_apk=${10:?missing popt package}
libgcc_apk=${11:?missing libgcc package}
libstdcpp_apk=${12:?missing libstdc++ package}
musl_apk=${13:?missing musl package}
libuuid_apk=${14:?missing libuuid package}
output=${15:?missing output}
epoch=1681862400
executor_sha256=2d816164f369b1ba00f16952416a80ef3bc2f427b6945d3af0702ed0035a6245
watchdog_disarm_sha256=8949398f9a6245447b3aa4626b85f3f2538e2bf060ced46952514145cb152bbe
native_seal_sha256=8dbc66163adde6919d9e48974a035e1a3d27c8d0304befbc806cd284d167be68
verifier_sha256=bc7d5c9e5a7a0ff4d46f9fc9dc1680f0d9a960bcd9b01d11fb327d407fa4ba58
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
	mkdir mktemp mv readelf readlink rm sha256sum sort stat touch; do
	command -v "$command" >/dev/null ||
		fail "missing storage-layout build command: $command"
done
for input in "$base" "$init" "$executor" "$watchdog_disarm" \
	"$private_config" "$native_seal" "$verifier" "$sgdisk_apk" "$popt_apk" \
	"$libgcc_apk" "$libstdcpp_apk" "$musl_apk" "$libuuid_apk" \
	"$readonly_builder"; do
	[ -f "$input" ] && [ -r "$input" ] && [ ! -L "$input" ] ||
		fail "unsafe storage-layout input: $(basename "$input")"
done
[ -x "$init" ] && [ -x "$executor" ] && [ -x "$watchdog_disarm" ] &&
	[ -x "$verifier" ] && [ -x "$readonly_builder" ] ||
	fail 'initramfs programs must be executable'
[ ! -e "$output" ] && [ ! -L "$output" ] ||
	fail 'storage-layout output already exists'
case $private_config_sha256 in
	????????????????????????????????????????????????????????????????) ;;
	*) fail 'private config SHA-256 is not canonical' ;;
esac
case $private_config_sha256 in
	*[!0-9a-f]*) fail 'private config SHA-256 is not canonical' ;;
esac
check_hash "$executor" "$executor_sha256"
check_hash "$watchdog_disarm" "$watchdog_disarm_sha256"
check_hash "$private_config" "$private_config_sha256"
check_hash "$native_seal" "$native_seal_sha256"
check_hash "$verifier" "$verifier_sha256"

[ "$(wc -l <"$private_config")" = 10 ] || fail 'private config line count changed'
for key in operation_id disk_guid userdata_type_guid userdata_unique_guid \
	userdata_fs_uuid arch_root_unique_guid source_image_uuid \
	source_image_sha256 target_fs_uuid; do
	[ "$(grep -c "^${key}=" "$private_config")" = 1 ] ||
		fail "private config key changed: $key"
done
[ "$(grep -c '^format=rog5-storage-layout-stage2-v1$' "$private_config")" = 1 ] ||
	fail 'private config format changed'
if awk -F= '
	BEGIN { ok=1 }
	$1 == "format" && $2 == "rog5-storage-layout-stage2-v1" { next }
	$1 == "operation_id" && $2 ~ /^[0-9a-f]{32}$/ { next }
	$1 == "source_image_sha256" && $2 ~ /^[0-9a-f]{64}$/ { next }
	$1 ~ /^(disk_guid|userdata_type_guid|userdata_unique_guid|userdata_fs_uuid|arch_root_unique_guid|source_image_uuid|target_fs_uuid)$/ &&
		$2 ~ /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/ { next }
	{ ok=0 }
	END { exit !ok }
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
printf '%s\n' storage-layout-stage2-v1 >"$stage/etc/rog5/recovery-mode"
chmod 0444 "$stage/etc/rog5/recovery-mode"
mkdir -p "$stage/usr/libexec"
install -m 0755 "$executor" "$stage/usr/libexec/rog5-storage-layout-stage2"
install -m 0755 "$watchdog_disarm" \
	"$stage/usr/libexec/rog5-disarm-recovery-layout-watchdog"
install -m 0755 "$verifier" "$stage/usr/libexec/rog5-persistent-root-verify"
install -m 0400 "$private_config" "$stage/etc/rog5/storage-layout-stage2.conf"
install -m 0444 "$native_seal" "$stage/etc/rog5/native-root-v1.seal"

[ ! -e "$stage/usr/libexec/rog5-recovery-control" ] ||
	fail 'interactive recovery control survived stage-2 packaging'
[ ! -e "$stage/usr/sbin/kexec" ] || fail 'kexec survived stage-2 packaging'
for path in init usr/libexec/rog5-storage-layout-stage2 \
	usr/libexec/rog5-disarm-recovery-layout-watchdog \
	usr/libexec/rog5-persistent-root-verify etc/rog5/native-root-v1.seal \
	usr/bin/sgdisk sbin/e2fsck usr/sbin/tune2fs usr/sbin/dumpe2fs \
	usr/sbin/resize2fs; do
	[ -e "$stage/$path" ] || fail "stage-2 initramfs lacks $path"
done
for path in bin/dd usr/bin/sha256sum sbin/blockdev usr/sbin/partprobe \
	sbin/losetup bin/mount bin/umount sbin/blkid bin/cp bin/mv bin/sync; do
	[ -L "$stage/$path" ] && [ "$(readlink "$stage/$path")" = /bin/busybox ] ||
		fail "stage-2 initramfs lacks fixed BusyBox applet: $path"
done
readelf -h "$stage/usr/libexec/rog5-persistent-root-verify" |
	grep -q 'Machine:.*AArch64' || fail 'packaged verifier is not AArch64'
if readelf -l "$stage/usr/libexec/rog5-persistent-root-verify" |
	grep -q 'Requesting program interpreter'; then
	fail 'packaged verifier is not static'
fi
cmp "$stage/init" "$init" || fail 'packaged recovery init changed'
cmp "$stage/usr/libexec/rog5-storage-layout-stage2" "$executor" ||
	fail 'packaged stage-2 executor changed'
cmp "$stage/usr/libexec/rog5-disarm-recovery-layout-watchdog" \
	"$watchdog_disarm" || fail 'packaged watchdog helper changed'
cmp "$stage/usr/libexec/rog5-persistent-root-verify" "$verifier" ||
	fail 'packaged verifier changed'
cmp "$stage/etc/rog5/storage-layout-stage2.conf" "$private_config" ||
	fail 'packaged private config changed'
cmp "$stage/etc/rog5/native-root-v1.seal" "$native_seal" ||
	fail 'packaged native-root seal changed'

find "$stage" -exec touch -h -d "@$epoch" {} +
(cd "$stage" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$temporary"
gzip -t "$temporary"
mv -T -- "$temporary" "$output"
trap - EXIT HUP INT TERM
rm -rf -- "$stage"
rm -f -- "$readonly_archive"

sha256sum "$init" "$executor" "$native_seal" "$output"
echo "PASS deterministic sealed storage-layout stage-2 initramfs; private_config_sha256=$private_config_sha256"
