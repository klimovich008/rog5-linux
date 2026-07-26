#!/bin/sh
set -eu

base=${1:?usage: build-a660-registration-kexec-stage-initramfs.sh BASE_STAGE IMAGE CANDIDATE_DTB OUTPUT}
image_input=${2:?missing A660 registration Image}
dtb_input=${3:?missing A660 registration DTB}
output=${4:?missing output}
base_sha=85f764dd206afd3a2b652c7119eb266f62d687a02b1c32a5d303a51d012157b4
old_image_sha=d30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b
old_dtb_sha=da471966073cfb26581b4a5224218904162c5925155b0aa8c24a2b3e4ad0526f
target_initramfs_sha=4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac
new_image_sha=52624d3fc8d51234ff4f4d4c31f302d2e031c736997dd9645e96e89b4fcd00db
new_dtb_sha=b96f4350b35ff3bfc987ce97828e22bd7136100323752c2ac68c537580bd35d6
epoch=1681862400

for input in "$base" "$image_input" "$dtb_input"; do
	[ -f "$input" ] && [ ! -L "$input" ]
done
[ "$(sha256sum "$base" | cut -d ' ' -f 1)" = "$base_sha" ]
[ "$(sha256sum "$image_input" | cut -d ' ' -f 1)" = "$new_image_sha" ]
[ "$(sha256sum "$dtb_input" | cut -d ' ' -f 1)" = "$new_dtb_sha" ]
gzip -t "$base"

base_real=$(readlink -f -- "$base")
image_real=$(readlink -f -- "$image_input")
dtb_real=$(readlink -f -- "$dtb_input")
output_real=$(readlink -m -- "$output")
for input_real in "$base_real" "$image_real" "$dtb_real"; do
	[ "$output_real" != "$input_real" ] || {
		echo 'FAIL stage output aliases an input' >&2
		exit 1
	}
done

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
firmware_pattern='a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn'
if find "$root" -type f -printf '%f\n' | grep -Eq "$firmware_pattern"; then
	echo 'FAIL accepted stage contains A660 firmware' >&2
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
	echo 'FAIL derivative stage contains a private key' >&2
	exit 1
fi
if find "$verify" -type f -printf '%f\n' |
	grep -Eq "$firmware_pattern"
then
	echo 'FAIL derivative stage contains A660 firmware' >&2
	exit 1
fi
if find "$verify" -type f -name '*.ko' | grep -q .; then
	echo 'FAIL derivative stage embeds a kernel module' >&2
	exit 1
fi

sha256sum "$output_real"
echo 'PASS deterministic credential-free A660 registration stage; only Image, board.dtb, and SHA256SUMS changed from accepted v18'
