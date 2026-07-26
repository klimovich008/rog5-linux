#!/bin/sh
set -eu

base=${1:?usage: build-adreno-smmu-kexec-stage-initramfs.sh BASE_STAGE CANDIDATE_DTB OUTPUT}
dtb=${2:?missing candidate DTB}
output=${3:?missing output}
base_sha=68b8729c5aef7f9a3eacba07685fe952f4df6cac29eb8c35d9559fda98722fab
image_sha=d30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b
old_dtb_sha=e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5
new_dtb_sha=da471966073cfb26581b4a5224218904162c5925155b0aa8c24a2b3e4ad0526f
initramfs_sha=4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
epoch=1681862400

[ -f "$base" ] && [ ! -L "$base" ] && [ -f "$dtb" ] && [ ! -L "$dtb" ]
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$base_sha" ]
[ "$(sha256sum "$dtb" | cut -d ' ' -f 1)" = "$new_dtb_sha" ]
gzip -t "$base"

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT INT TERM
root=$work/root
verify=$work/verify
mkdir -p "$root" "$verify"
gzip -dc "$base" |
	(cd "$root" && cpio -idm --quiet --no-absolute-filenames)

payload=$root/opt/rog5-recovery
image=$payload/Image
old_dtb=$payload/board.dtb
target_initramfs=$payload/initramfs.cpio.gz
sums=$payload/SHA256SUMS
[ "$(sha256sum "$image" | cut -d ' ' -f 1)" = "$image_sha" ]
[ "$(sha256sum "$old_dtb" | cut -d ' ' -f 1)" = "$old_dtb_sha" ]
[ "$(sha256sum "$target_initramfs" | cut -d ' ' -f 1)" = \
	"$initramfs_sha" ]
(cd "$payload" && sha256sum -c SHA256SUMS >/dev/null)

[ ! -e "$root/root/.ssh/authorized_keys" ]
[ -z "$(find "$root/etc/ssh" -maxdepth 1 -type f -name 'ssh_host_*' \
	-print -quit)" ]
if find "$root" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .
then
	echo 'FAIL accepted staging archive contains a private key' >&2
	exit 1
fi
firmware_pattern='a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
if find "$root" -type f -printf '%f\n' | grep -Eq "$firmware_pattern"; then
	echo 'FAIL accepted staging archive contains A660 firmware' >&2
	exit 1
fi

(cd "$root" && find . -type f \
	! -path ./opt/rog5-recovery/board.dtb \
	! -path ./opt/rog5-recovery/SHA256SUMS \
	-print0 | sort -z | xargs -0 sha256sum) >"$work/before"

install -m 0644 "$dtb" "$old_dtb"
(cd "$payload" && sha256sum Image board.dtb initramfs.cpio.gz >SHA256SUMS)
[ "$(stat -c %a "$old_dtb")" = 644 ]
[ "$(stat -c %a "$sums")" = 644 ]
[ "$(awk 'NF { count++ } END { print count + 0 }' "$sums")" -eq 3 ]
(cd "$payload" && sha256sum -c SHA256SUMS >/dev/null)

(cd "$root" && find . -type f \
	! -path ./opt/rog5-recovery/board.dtb \
	! -path ./opt/rog5-recovery/SHA256SUMS \
	-print0 | sort -z | xargs -0 sha256sum) >"$work/after"
cmp "$work/before" "$work/after"

find "$root" -exec touch -h -d "@$epoch" {} +
mkdir -p "$(dirname "$output")"
(cd "$root" && find . -mindepth 1 -print0 | sort -z |
	cpio --null -o --quiet --format=newc --owner=0:0 --reproducible) |
	gzip -n >"$output.tmp"
mv "$output.tmp" "$output"
gzip -t "$output"

gzip -dc "$output" |
	(cd "$verify" && cpio -idm --quiet --no-absolute-filenames)
cmp "$verify/opt/rog5-recovery/Image" "$image"
cmp "$verify/opt/rog5-recovery/board.dtb" "$dtb"
cmp "$verify/opt/rog5-recovery/initramfs.cpio.gz" "$target_initramfs"
(cd "$verify/opt/rog5-recovery" &&
	sha256sum -c SHA256SUMS >/dev/null)
[ ! -e "$verify/root/.ssh/authorized_keys" ]
if find "$verify" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .
then
	echo 'FAIL derivative staging archive contains a private key' >&2
	exit 1
fi
if find "$verify" -type f -printf '%f\n' | grep -Eq "$firmware_pattern"; then
	echo 'FAIL derivative staging archive contains A660 firmware' >&2
	exit 1
fi

sha256sum "$output"
echo 'PASS deterministic credential-free staging initramfs; only board.dtb and SHA256SUMS changed from accepted v15'
