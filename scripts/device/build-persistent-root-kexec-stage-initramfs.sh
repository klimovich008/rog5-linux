#!/bin/sh
set -eu

base=${1:?usage: build-persistent-root-kexec-stage-initramfs.sh BASE_STAGE IMAGE DTB INITRAMFS LOADER OUTPUT}
image_input=${2:?missing P2 Image}
dtb_input=${3:?missing P2 DTB}
initramfs_input=${4:?missing P2 target initramfs}
loader_input=${5:?missing P2 loader}
output=${6:?missing output}
base_sha=fcf147c4dc91323caaed4be8767545441f9df31323e4513e62c99ac20ac789e9
old_image_sha=bdc72155b4ff2de3a655f53e0570a18690778025cac86425fccd5d3b9699ac8c
old_dtb_sha=36802458928e2970a0043f6a27d106e6aa4911fd89b2f548e7c08275d164aaf0
old_initramfs_sha=df1d0cdb95513d7ef6d772a3a6165d37b3b226682d92e30a2143409341bbefb1
old_loader_sha=321386f972e0a8da9cbb0e744419c072effd764dd7b2f4fe8d4f24d203134444
image_sha=832757fc6b97554813a14049123667bc6f5b225e6204ca048d73c3a36c76469f
dtb_sha=36802458928e2970a0043f6a27d106e6aa4911fd89b2f548e7c08275d164aaf0
initramfs_sha=e2b58d50fae31509b8cd87ed01afbf25c90d49500e3d9d9691ecd77643fd434e
loader_sha=7a05fdbf513e845ec7baff7ed5324d8e6564901d3e9b21fb1a95caf2a7633177
epoch=1681862400

check_hash() {
	[ -f "$1" ] && [ ! -L "$1" ] && [ -r "$1" ] || {
		echo "FAIL missing or linked P2 stage input: $1" >&2
		exit 1
	}
	[ "$(sha256sum "$1" | cut -d ' ' -f 1)" = "$2" ] || {
		echo "FAIL P2 stage input hash changed: $(basename "$1")" >&2
		exit 1
	}
}

check_hash "$base" "$base_sha"
check_hash "$image_input" "$image_sha"
check_hash "$dtb_input" "$dtb_sha"
check_hash "$initramfs_input" "$initramfs_sha"
check_hash "$loader_input" "$loader_sha"
[ -x "$loader_input" ]
gzip -t "$base"
gzip -t "$initramfs_input"

output_real=$(readlink -m -- "$output")
for input in "$base" "$image_input" "$dtb_input" \
	"$initramfs_input" "$loader_input"; do
	[ "$output_real" != "$(readlink -f -- "$input")" ] || {
		echo 'FAIL P2 stage output aliases an input' >&2
		exit 1
	}
done
[ ! -e "$output_real" ] || {
	echo "FAIL refusing existing P2 stage output: $output_real" >&2
	exit 1
}

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
root=$work/root
verify=$work/verify
mkdir -p "$root" "$verify"
gzip -dc "$base" |
	(cd "$root" && cpio -idm --quiet --no-absolute-filenames)

payload=$root/opt/rog5-recovery
embedded_loader=$root/usr/local/sbin/rog5-load-mainline-recovery
check_hash "$payload/Image" "$old_image_sha"
check_hash "$payload/board.dtb" "$old_dtb_sha"
check_hash "$payload/initramfs.cpio.gz" "$old_initramfs_sha"
check_hash "$embedded_loader" "$old_loader_sha"
(cd "$payload" && sha256sum -c SHA256SUMS >/dev/null)

[ ! -e "$root/root/.ssh/authorized_keys" ]
[ -z "$(find "$root/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*' -print -quit)" ]
! find "$root" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .
! find "$root" -type f -name '*.ko' | grep -q .

(cd "$root" && find . -type f \
	! -path ./opt/rog5-recovery/Image \
	! -path ./opt/rog5-recovery/board.dtb \
	! -path ./opt/rog5-recovery/initramfs.cpio.gz \
	! -path ./opt/rog5-recovery/SHA256SUMS \
	! -path ./usr/local/sbin/rog5-load-mainline-recovery \
	-print0 | sort -z | xargs -0 sha256sum) >"$work/before"

install -m 0644 "$image_input" "$payload/Image"
install -m 0644 "$dtb_input" "$payload/board.dtb"
install -m 0644 "$initramfs_input" "$payload/initramfs.cpio.gz"
install -m 0755 "$loader_input" "$embedded_loader"
(cd "$payload" &&
	sha256sum Image board.dtb initramfs.cpio.gz >SHA256SUMS)

(cd "$root" && find . -type f \
	! -path ./opt/rog5-recovery/Image \
	! -path ./opt/rog5-recovery/board.dtb \
	! -path ./opt/rog5-recovery/initramfs.cpio.gz \
	! -path ./opt/rog5-recovery/SHA256SUMS \
	! -path ./usr/local/sbin/rog5-load-mainline-recovery \
	-print0 | sort -z | xargs -0 sha256sum) >"$work/after"
cmp "$work/before" "$work/after"

find "$root" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output_real")"
(cd "$root" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$output_real.tmp"
mv -T -- "$output_real.tmp" "$output_real"
gzip -t "$output_real"

gzip -dc "$output_real" |
	(cd "$verify" && cpio -idm --quiet --no-absolute-filenames)
check_hash "$verify/opt/rog5-recovery/Image" "$image_sha"
check_hash "$verify/opt/rog5-recovery/board.dtb" "$dtb_sha"
check_hash "$verify/opt/rog5-recovery/initramfs.cpio.gz" "$initramfs_sha"
check_hash \
	"$verify/usr/local/sbin/rog5-load-mainline-recovery" "$loader_sha"
(cd "$verify/opt/rog5-recovery" &&
	sha256sum -c SHA256SUMS >/dev/null)

sha256sum "$output_real"
echo 'PASS deterministic credential-free P2 kexec stage from accepted UFS wrapper'
