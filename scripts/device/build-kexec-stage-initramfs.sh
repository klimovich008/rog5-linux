#!/bin/sh
set -eu

base=${1:?usage: build-kexec-stage-initramfs.sh BASE INIT KEXEC_APK XZ_APK ZSTD_APK IMAGE DTB TARGET_INITRAMFS LOADER OUTPUT AUTHORIZED_KEY TARGET_INITRAMFS_SHA256 IMAGE_SHA256 DTB_SHA256}
init=${2:?missing recovery init}
kexec_apk=${3:?missing kexec package}
xz_apk=${4:?missing xz-libs package}
zstd_apk=${5:?missing zstd-libs package}
image=${6:?missing mainline Image}
dtb=${7:?missing recovery DTB}
target_initramfs=${8:?missing target initramfs}
loader=${9:?missing kexec loader}
output=${10:?missing output}
authorized_key=${11:-}
target_initramfs_sha256=${12:?missing target initramfs SHA-256}
image_sha256=${13:?missing mainline Image SHA-256}
dtb_sha256=${14:?missing recovery DTB SHA-256}
epoch=1681862400

check_hash() {
	actual=$(sha256sum "$1" | cut -d ' ' -f 1)
	[ "$actual" = "$2" ] || {
		echo "FAIL input hash mismatch: $(basename "$1")" >&2
		exit 1
	}
}

check_hash "$base" 100e33ea4bc7e2d568450418bba3617f24394e8bb122a39fd5db334555d3bdca
check_hash "$kexec_apk" bd8b6951f862af1123972b521c355c655b7a2f40c2bf9cfe700edd590a101c94
check_hash "$xz_apk" 76dce86852903fef7adba0285d816e5ce9ffbe9fb3ca86bbb349b97afaba1f63
check_hash "$zstd_apk" 2bb5136c89f5b0bbe1554c8915a3b520d5aa63ae2a51d4d821eb81698db5a818
for expected_hash in "$target_initramfs_sha256" "$image_sha256" "$dtb_sha256"; do
	case $expected_hash in *[!0-9a-f]*|'') exit 1 ;; esac
	[ "${#expected_hash}" -eq 64 ]
done
check_hash "$image" "$image_sha256"
check_hash "$dtb" "$dtb_sha256"
check_hash "$target_initramfs" "$target_initramfs_sha256"
[ -x "$init" ] && [ -x "$loader" ] && gzip -t "$target_initramfs"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
gzip -dc "$base" | (cd "$stage" && cpio -idm --quiet --no-absolute-filenames)
install -m 0755 "$init" "$stage/init"
rm -f "$stage"/etc/ssh/ssh_host_* "$stage/etc/machine-id" "$stage/var/lib/dbus/machine-id"
if [ -n "$authorized_key" ]; then
	[ -r "$authorized_key" ] &&
		grep -Eq '^(ssh-ed25519|ecdsa-sha2-nistp256|ssh-rsa) ' "$authorized_key" &&
		awk 'NF { count++ } END { exit count != 1 }' "$authorized_key"
	install -D -m 0600 "$authorized_key" "$stage/root/.ssh/authorized_keys"
fi

tar --warning=no-unknown-keyword -xf "$kexec_apk" -C "$stage" usr/sbin/kexec usr/sbin/vmcore-dmesg
tar --warning=no-unknown-keyword -xf "$xz_apk" -C "$stage" usr/lib/liblzma.so.5 usr/lib/liblzma.so.5.8.3
tar --warning=no-unknown-keyword -xf "$zstd_apk" -C "$stage" usr/lib/libzstd.so.1 usr/lib/libzstd.so.1.5.7
install -D -m 0755 "$loader" "$stage/usr/local/sbin/rog5-load-mainline-recovery"
install -D -m 0644 "$image" "$stage/opt/rog5-recovery/Image"
install -m 0644 "$dtb" "$stage/opt/rog5-recovery/board.dtb"
install -m 0644 "$target_initramfs" "$stage/opt/rog5-recovery/initramfs.cpio.gz"
(cd "$stage/opt/rog5-recovery" &&
	sha256sum Image board.dtb initramfs.cpio.gz >SHA256SUMS)

readelf -h "$stage/usr/sbin/kexec" | grep -q 'Machine:.*AArch64'
for library in libc.musl-aarch64.so.1 liblzma.so.5 libz.so.1 libzstd.so.1; do
	readelf -d "$stage/usr/sbin/kexec" | grep -q "Shared library: \[$library\]"
done
[ -e "$stage/lib/ld-musl-aarch64.so.1" ]
for library in liblzma.so.5 libz.so.1 libzstd.so.1; do
	[ -e "$stage/usr/lib/$library" ]
done

find "$stage" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output")"
(cd "$stage" && find . -mindepth 1 -print0 | sort -z | \
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) | gzip -n >"$output.tmp"
mv "$output.tmp" "$output"
gzip -t "$output"
sha256sum "$output"
echo 'PASS self-contained kexec staging initramfs; no storage-mount logic included'
