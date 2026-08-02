#!/usr/bin/env bash
set -euo pipefail
set -f
umask 077

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
source_root=${1:?usage: issue-stable-recovery-avb-generation.sh SOURCE_WRAPPER_ROOT OUTPUT_WRAPPER_ROOT GENERATION EXPECTED_SOURCE_AVB_SHA256 EXPECTED_RAW_SHA256}
output_root=${2:?missing output wrapper root}
generation=${3:?missing AVB generation}
expected_source_avb=${4:?missing source AVB SHA-256}
expected_raw=${5:?missing raw wrapper SHA-256}
avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py

for command in awk cmp cp cut dirname git grep mkdir mktemp mv python3 \
	realpath rm sed sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing AVB-generation command: $command"
done
[[ $generation =~ ^(0|[1-9][0-9]*)$ ]] ||
	fail 'AVB generation must be a canonical nonnegative integer'
[[ $expected_source_avb =~ ^[0-9a-f]{64}$ &&
	$expected_raw =~ ^[0-9a-f]{64}$ ]] ||
	fail 'expected wrapper identities must be lowercase SHA-256 values'
[[ -f $avbtool && ! -L $avbtool ]] || fail 'pinned avbtool is unavailable'
[[ $(sha256sum "$avbtool" | cut -d ' ' -f 1) == \
	6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff ]] ||
	fail 'pinned avbtool identity changed'

source_root=$(realpath -e "$source_root")
output_root=$(realpath -m "$output_root")
case $source_root in
	"$repo"/build/*) ;;
	*) fail 'source wrapper root must remain below the ignored build directory' ;;
esac
case $output_root in
	"$repo"/build/*) ;;
	*) fail 'output wrapper root must remain below the ignored build directory' ;;
esac
git -C "$repo" check-ignore -q "$source_root" ||
	fail 'source wrapper root is not ignored by Git'
git -C "$repo" check-ignore -q "$output_root" ||
	fail 'output wrapper root is not ignored by Git'
case $output_root in
	"$source_root"|"$source_root"/*) fail 'output overlaps source wrapper root' ;;
esac
case $source_root in
	"$output_root"|"$output_root"/*) fail 'source overlaps output wrapper root' ;;
esac
[[ ! -e $output_root && ! -L $output_root ]] ||
	fail 'refusing an existing AVB-generation output root'
output_parent=$(dirname -- "$output_root")
[[ -d $output_parent && ! -L $output_parent &&
	$(realpath -e "$output_parent") == "$output_parent" ]] ||
	fail 'AVB-generation output parent is unsafe or absent'

relative_inputs=(
	repack/stable-recovery-a.raw.img
	repack/stable-recovery-b.raw.img
	repack/stable-recovery-a.avb.img
	repack/stable-recovery-b.avb.img
	wrapper-a/asus-kexec-stage/.config
	wrapper-b/asus-kexec-stage/.config
	wrapper-a/asus-kexec-stage/arch/arm64/boot/Image
	wrapper-b/asus-kexec-stage/arch/arm64/boot/Image
	wrapper-a/rog5-kexec-stage-initramfs.cpio.gz
	wrapper-b/rog5-kexec-stage-initramfs.cpio.gz
)
for relative in "${relative_inputs[@]}"; do
	input=$source_root/$relative
	[[ -f $input && ! -L $input && $(realpath -e "$input") == "$input" ]] ||
		fail "unsafe source wrapper input: $relative"
done

raw_a=$source_root/repack/stable-recovery-a.raw.img
raw_b=$source_root/repack/stable-recovery-b.raw.img
avb_a=$source_root/repack/stable-recovery-a.avb.img
avb_b=$source_root/repack/stable-recovery-b.avb.img
cmp "$raw_a" "$raw_b" || fail 'source twin raw wrappers differ'
cmp "$avb_a" "$avb_b" || fail 'source twin AVB wrappers differ'
raw_sha=$(sha256sum "$raw_a" | cut -d ' ' -f 1)
source_avb_sha=$(sha256sum "$avb_a" | cut -d ' ' -f 1)
[[ $raw_sha == "$expected_raw" ]] || fail 'source raw wrapper identity changed'
[[ $source_avb_sha == "$expected_source_avb" ]] ||
	fail 'source AVB wrapper identity changed'
partition_size=$(stat -c %s "$avb_a")
raw_size=$(stat -c %s "$raw_a")
[[ $partition_size =~ ^[0-9]+$ && $raw_size =~ ^[0-9]+$ &&
	$raw_size -gt 0 && $raw_size -lt $partition_size ]] ||
	fail 'source AVB partition geometry is invalid'

stage=$(mktemp -d "$output_parent/.rog5-avb-generation.XXXXXX")
candidate_root=$stage/output
cleanup() {
	rm -rf -- "$stage"
}
trap cleanup EXIT HUP INT TERM

add_footer() {
	local raw=$1 output=$2 salt=$3
	cp --reflink=auto -- "$raw" "$output.tmp"
	python3 "$avbtool" add_hash_footer \
		--image "$output.tmp" \
		--partition_name boot \
		--partition_size "$partition_size" \
		--algorithm NONE \
		--salt "$salt"
	mv "$output.tmp" "$output"
}

# Prove that the default generation reproduces the consumed source wrapper.
add_footer "$raw_a" "$stage/legacy.avb.img" "$raw_sha"
cmp "$stage/legacy.avb.img" "$avb_a" ||
	fail 'source AVB wrapper is not the canonical generation-zero encoding'

if [[ $generation == 0 ]]; then
	salt=$raw_sha
else
	salt=$(
		printf 'format=rog5-stable-recovery-avb-generation-v1\nraw_sha256=%s\ngeneration=%s\n' \
			"$raw_sha" "$generation" | sha256sum | cut -d ' ' -f 1
	)
fi

mkdir -m 0700 -p \
	"$candidate_root/repack" \
	"$candidate_root/wrapper-a/asus-kexec-stage/arch/arm64/boot" \
	"$candidate_root/wrapper-b/asus-kexec-stage/arch/arm64/boot"
for suffix in a b; do
	cp --reflink=auto -- "$source_root/repack/stable-recovery-$suffix.raw.img" \
		"$candidate_root/repack/stable-recovery-$suffix.raw.img"
	cp --reflink=auto -- "$source_root/wrapper-$suffix/asus-kexec-stage/.config" \
		"$candidate_root/wrapper-$suffix/asus-kexec-stage/.config"
	cp --reflink=auto -- \
		"$source_root/wrapper-$suffix/asus-kexec-stage/arch/arm64/boot/Image" \
		"$candidate_root/wrapper-$suffix/asus-kexec-stage/arch/arm64/boot/Image"
	cp --reflink=auto -- \
		"$source_root/wrapper-$suffix/rog5-kexec-stage-initramfs.cpio.gz" \
		"$candidate_root/wrapper-$suffix/rog5-kexec-stage-initramfs.cpio.gz"
	add_footer "$candidate_root/repack/stable-recovery-$suffix.raw.img" \
		"$candidate_root/repack/stable-recovery-$suffix.avb.img" "$salt"
done

output_avb_a=$candidate_root/repack/stable-recovery-a.avb.img
output_avb_b=$candidate_root/repack/stable-recovery-b.avb.img
cmp "$output_avb_a" "$output_avb_b" || fail 'successor twin AVB wrappers differ'
cmp "$candidate_root/repack/stable-recovery-a.raw.img" "$raw_a" ||
	fail 'successor slot A raw payload changed'
cmp "$candidate_root/repack/stable-recovery-b.raw.img" "$raw_b" ||
	fail 'successor slot B raw payload changed'
if [[ $generation == 0 ]]; then
	cmp "$output_avb_a" "$avb_a"
else
	! cmp -s "$output_avb_a" "$avb_a" ||
		fail 'nonzero generation reproduced the consumed source AVB wrapper'
fi

cp --reflink=auto -- "$raw_a" "$stage/boot.img"
cp --reflink=auto -- "$output_avb_a" "$stage/recovery.img"
python3 "$avbtool" verify_image --image "$stage/recovery.img" >/dev/null
avb_info=$(python3 "$avbtool" info_image --image "$stage/recovery.img")
source_avb_info=$(python3 "$avbtool" info_image --image "$avb_a")
grep -q '^Algorithm:[[:space:]]*NONE$' <<<"$avb_info" ||
	fail 'successor AVB algorithm is not NONE'
grep -q '^      Partition Name:[[:space:]]*boot$' <<<"$avb_info" ||
	fail 'successor AVB partition name is not boot'
observed_salt=$(awk '/^      Salt:/ { print $2; exit }' <<<"$avb_info")
observed_digest=$(awk '/^      Digest:/ { print $2; exit }' <<<"$avb_info")
[[ $observed_salt == "$salt" ]] || fail 'AVB descriptor salt changed'
observed_image_size=$(awk '/^      Image Size:/ { print $3; exit }' <<<"$avb_info")
[[ $observed_image_size == "$raw_size" ]] ||
	fail 'AVB descriptor image size changed'
[[ $(stat -c %s "$output_avb_a") == "$partition_size" ]] ||
	fail 'successor AVB partition size changed'
cmp -n "$raw_size" "$output_avb_a" "$raw_a" ||
	fail 'successor AVB prefix differs from the raw recovery payload'
printf '%s\n' "$source_avb_info" |
	sed -E 's/^(      (Salt|Digest):).*/\1 <generation-dependent>/' \
		>"$stage/source-info.normalized"
printf '%s\n' "$avb_info" |
	sed -E 's/^(      (Salt|Digest):).*/\1 <generation-dependent>/' \
		>"$stage/output-info.normalized"
cmp "$stage/source-info.normalized" "$stage/output-info.normalized" ||
	fail 'successor AVB structure changed beyond salt and digest'
expected_digest=$(python3 -I -S - "$salt" "$raw_a" <<'PY'
import hashlib
import sys

digest = hashlib.sha256()
digest.update(bytes.fromhex(sys.argv[1]))
with open(sys.argv[2], "rb", buffering=0) as source:
    while block := source.read(1024 * 1024):
        digest.update(block)
print(digest.hexdigest())
PY
)
[[ $observed_digest == "$expected_digest" ]] ||
	fail 'AVB descriptor digest does not bind salt plus raw image'

output_avb_sha=$(sha256sum "$output_avb_a" | cut -d ' ' -f 1)
cat >"$candidate_root/avb-generation.txt" <<EOF
format=rog5-stable-recovery-avb-generation-v1
generation=$generation
raw_sha256=$raw_sha
source_avb_sha256=$source_avb_sha
salt=$salt
digest=$expected_digest
output_avb_sha256=$output_avb_sha
partition_size=$partition_size
authority=none
EOF
chmod 0444 "$candidate_root/avb-generation.txt"
[[ ! -e $output_root && ! -L $output_root ]] ||
	fail 'AVB-generation output appeared before atomic publication'
mv -T -- "$candidate_root" "$output_root"

printf 'generation=%s\nraw_sha256=%s\nsalt=%s\noutput_avb_sha256=%s\nauthority=none\n' \
	"$generation" "$raw_sha" "$salt" "$output_avb_sha"
echo 'PASS stable-recovery AVB generation is twin-reproducible; raw recovery payload is unchanged and no boot is authorized'
