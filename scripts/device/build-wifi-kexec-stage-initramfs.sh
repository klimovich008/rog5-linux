#!/bin/sh
set -eu

base=${1:?usage: build-wifi-kexec-stage-initramfs.sh BASE_STAGE IMAGE WIFI_DTB OUTPUT}
image_input=${2:?missing WCN6855 Image}
dtb_input=${3:?missing WCN6855 DTB}
output=${4:?missing output}
base_sha=eba1c3b862a47f75fbbcca8baed064baa5ebad37f4f138094a143eef7d062863
old_image_sha=349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf
old_dtb_sha=0fb6d415597630508779263693803af40f35496adee17e82995b0189b2aa9c78
target_initramfs_sha=4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
new_image_sha=a4edaee34dca66534cf886fd0daa6068273d4fd722b63960d517ef17699af43e
new_dtb_sha=15acdcd6fad910f105047ef53de08b47cafadbbf94827e123931408d92310d89
epoch=1681862400

for tool in cpio cut find gzip install mkdir mv readlink sha256sum sort; do
	command -v "$tool" >/dev/null
done
for input in "$base" "$image_input" "$dtb_input"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] || {
		echo "FAIL missing or linked Wi-Fi stage input: $input" >&2
		exit 1
	}
done
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$base_sha" ]
[ "$(sha256sum "$image_input" | cut -d ' ' -f 1)" = "$new_image_sha" ]
[ "$(sha256sum "$dtb_input" | cut -d ' ' -f 1)" = "$new_dtb_sha" ]
gzip -t "$base"

output_real=$(readlink -m -- "$output")
for input in "$base" "$image_input" "$dtb_input"; do
	[ "$output_real" != "$(readlink -f -- "$input")" ] || {
		echo 'FAIL Wi-Fi stage output aliases an input' >&2
		exit 1
	}
done
[ ! -e "$output_real" ] || {
	echo "FAIL refusing existing Wi-Fi stage output: $output_real" >&2
	exit 1
}

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT INT TERM
root=$work/root
verify=$work/verify
mkdir -p "$root" "$verify"
gzip -dc "$base" |
	(cd "$root" && cpio -idm --quiet --no-absolute-filenames)

payload=$root/opt/rog5-recovery
image=$payload/Image
dtb=$payload/board.dtb
target_initramfs=$payload/initramfs.cpio.gz
sums=$payload/SHA256SUMS
[ "$(sha256sum "$image" | cut -d ' ' -f 1)" = "$old_image_sha" ]
[ "$(sha256sum "$dtb" | cut -d ' ' -f 1)" = "$old_dtb_sha" ]
[ "$(sha256sum "$target_initramfs" | cut -d ' ' -f 1)" = \
	"$target_initramfs_sha" ]
(cd "$payload" && sha256sum -c SHA256SUMS >/dev/null)

[ ! -e "$root/root/.ssh/authorized_keys" ]
[ -z "$(find "$root/etc/ssh" -maxdepth 1 -type f -name 'ssh_host_*' \
	-print -quit)" ]
if find "$root" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .
then
	echo 'FAIL accepted stage contains a private key' >&2
	exit 1
fi
if find "$root" -type f -name '*.ko' | grep -q .; then
	echo 'FAIL accepted stage embeds a kernel module' >&2
	exit 1
fi

(cd "$root" && find . -type f \
	! -path ./opt/rog5-recovery/Image \
	! -path ./opt/rog5-recovery/board.dtb \
	! -path ./opt/rog5-recovery/SHA256SUMS \
	-print0 | sort -z | xargs -0 sha256sum) >"$work/before"

install -m 0644 "$image_input" "$image"
install -m 0644 "$dtb_input" "$dtb"
(cd "$payload" && sha256sum Image board.dtb initramfs.cpio.gz >SHA256SUMS)
[ "$(stat -c %a "$image")" = 644 ]
[ "$(stat -c %a "$dtb")" = 644 ]
[ "$(stat -c %a "$sums")" = 644 ]
[ "$(awk 'NF { count++ } END { print count + 0 }' "$sums")" -eq 3 ]
(cd "$payload" && sha256sum -c SHA256SUMS >/dev/null)

(cd "$root" && find . -type f \
	! -path ./opt/rog5-recovery/Image \
	! -path ./opt/rog5-recovery/board.dtb \
	! -path ./opt/rog5-recovery/SHA256SUMS \
	-print0 | sort -z | xargs -0 sha256sum) >"$work/after"
cmp "$work/before" "$work/after"

find "$root" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output_real")"
(cd "$root" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$output_real.tmp"
mv "$output_real.tmp" "$output_real"
gzip -t "$output_real"

gzip -dc "$output_real" |
	(cd "$verify" && cpio -idm --quiet --no-absolute-filenames)
cmp "$verify/opt/rog5-recovery/Image" "$image_input"
cmp "$verify/opt/rog5-recovery/board.dtb" "$dtb_input"
[ "$(sha256sum \
	"$verify/opt/rog5-recovery/initramfs.cpio.gz" | cut -d ' ' -f 1)" = \
	"$target_initramfs_sha" ]
(cd "$verify/opt/rog5-recovery" &&
	sha256sum -c SHA256SUMS >/dev/null)
[ ! -e "$verify/root/.ssh/authorized_keys" ]
if find "$verify" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .
then
	echo 'FAIL derivative Wi-Fi stage contains a private key' >&2
	exit 1
fi
if find "$verify" -type f -name '*.ko' | grep -q .; then
	echo 'FAIL derivative Wi-Fi stage embeds a kernel module' >&2
	exit 1
fi

sha256sum "$output_real"
echo 'PASS deterministic credential-free WCN6855 stage; only Image, board.dtb, and SHA256SUMS changed from accepted v8'
