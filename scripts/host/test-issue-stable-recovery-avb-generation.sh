#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
issuer=$repo/scripts/host/issue-stable-recovery-avb-generation.sh
avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
mkdir -p "$repo/build"
tmp=$(mktemp -d "$repo/build/avb-generation-test.XXXXXX")
cleanup() {
	rm -rf -- "$tmp"
}
trap cleanup EXIT HUP INT TERM

source_root=$tmp/source
mkdir -p "$source_root/repack"
for suffix in a b; do
	mkdir -p "$source_root/wrapper-$suffix/asus-kexec-stage/arch/arm64/boot"
	printf 'config-%s\n' "$suffix" \
		>"$source_root/wrapper-$suffix/asus-kexec-stage/.config"
	printf 'kernel-%s\n' "$suffix" \
		>"$source_root/wrapper-$suffix/asus-kexec-stage/arch/arm64/boot/Image"
	printf 'initramfs-%s\n' "$suffix" \
		>"$source_root/wrapper-$suffix/rog5-kexec-stage-initramfs.cpio.gz"
	printf '0123456789abcdef%.0s' {1..256} \
		>"$source_root/repack/stable-recovery-$suffix.raw.img"
done
raw_sha=$(sha256sum "$source_root/repack/stable-recovery-a.raw.img" | cut -d ' ' -f 1)
for suffix in a b; do
	cp "$source_root/repack/stable-recovery-$suffix.raw.img" \
		"$source_root/repack/stable-recovery-$suffix.avb.img"
	python3 "$avbtool" add_hash_footer \
		--image "$source_root/repack/stable-recovery-$suffix.avb.img" \
		--partition_name boot --partition_size 131072 \
		--algorithm NONE --salt "$raw_sha"
done
source_avb_sha=$(sha256sum "$source_root/repack/stable-recovery-a.avb.img" | cut -d ' ' -f 1)

"$issuer" "$source_root" "$tmp/gen0" 0 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen0.out"
grep -Fxq 'generation=0' "$tmp/gen0.out"
grep -Fxq 'authority=none' "$tmp/gen0.out"
cmp "$tmp/gen0/repack/stable-recovery-a.avb.img" \
	"$source_root/repack/stable-recovery-a.avb.img"

"$issuer" "$source_root" "$tmp/gen1-a" 1 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen1-a.out"
"$issuer" "$source_root" "$tmp/gen1-b" 1 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen1-b.out"
cmp "$tmp/gen1-a/repack/stable-recovery-a.avb.img" \
	"$tmp/gen1-b/repack/stable-recovery-a.avb.img"
cmp "$tmp/gen1-a/avb-generation.txt" "$tmp/gen1-b/avb-generation.txt"
! cmp -s "$tmp/gen1-a/repack/stable-recovery-a.avb.img" \
	"$source_root/repack/stable-recovery-a.avb.img" ||
	fail 'generation one did not change the AVB wrapper'
for suffix in a b; do
	cmp "$tmp/gen1-a/repack/stable-recovery-$suffix.raw.img" \
		"$source_root/repack/stable-recovery-$suffix.raw.img"
	cmp "$tmp/gen1-a/wrapper-$suffix/asus-kexec-stage/.config" \
		"$source_root/wrapper-$suffix/asus-kexec-stage/.config"
	cmp "$tmp/gen1-a/wrapper-$suffix/asus-kexec-stage/arch/arm64/boot/Image" \
		"$source_root/wrapper-$suffix/asus-kexec-stage/arch/arm64/boot/Image"
	cmp "$tmp/gen1-a/wrapper-$suffix/rog5-kexec-stage-initramfs.cpio.gz" \
		"$source_root/wrapper-$suffix/rog5-kexec-stage-initramfs.cpio.gz"
done

expected_salt=$(
	printf 'format=rog5-stable-recovery-avb-generation-v1\nraw_sha256=%s\ngeneration=1\n' \
		"$raw_sha" | sha256sum | cut -d ' ' -f 1
)
grep -Fxq "salt=$expected_salt" "$tmp/gen1-a/avb-generation.txt"
mkdir "$tmp/verify"
cp "$tmp/gen1-a/repack/stable-recovery-a.raw.img" "$tmp/verify/boot.img"
cp "$tmp/gen1-a/repack/stable-recovery-a.avb.img" "$tmp/verify/recovery.img"
python3 "$avbtool" verify_image \
	--image "$tmp/verify/recovery.img" >/dev/null
info=$(python3 "$avbtool" info_image \
	--image "$tmp/gen1-a/repack/stable-recovery-a.avb.img")
[[ $(awk '/^      Salt:/ { print $2; exit }' <<<"$info") == \
	"$expected_salt" ]] || fail 'generation-one descriptor salt changed'
observed_digest=$(awk '/^      Digest:/ { print $2; exit }' <<<"$info")
grep -Fxq "digest=$observed_digest" "$tmp/gen1-a/avb-generation.txt"

"$issuer" "$source_root" "$tmp/gen2" 2 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen2.out"
! cmp -s "$tmp/gen1-a/repack/stable-recovery-a.avb.img" \
	"$tmp/gen2/repack/stable-recovery-a.avb.img" ||
	fail 'distinct nonzero generations produced the same AVB wrapper'

expected_files=$(cat <<'EOF'
avb-generation.txt
repack/stable-recovery-a.avb.img
repack/stable-recovery-a.raw.img
repack/stable-recovery-b.avb.img
repack/stable-recovery-b.raw.img
wrapper-a/asus-kexec-stage/.config
wrapper-a/asus-kexec-stage/arch/arm64/boot/Image
wrapper-a/rog5-kexec-stage-initramfs.cpio.gz
wrapper-b/asus-kexec-stage/.config
wrapper-b/asus-kexec-stage/arch/arm64/boot/Image
wrapper-b/rog5-kexec-stage-initramfs.cpio.gz
EOF
)
observed_files=$(find "$tmp/gen1-a" -type f -printf '%P\n' | sort)
[[ $observed_files == "$expected_files" ]] ||
	fail 'AVB-generation output file set changed'

if "$issuer" "$source_root" "$tmp/wrong-hash" 1 \
	ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff \
	"$raw_sha" >"$tmp/wrong.out" 2>"$tmp/wrong.err"; then
	fail 'wrong source AVB identity was accepted'
fi
grep -Fq 'source AVB wrapper identity changed' "$tmp/wrong.err"
[[ ! -e $tmp/wrong-hash ]] || fail 'rejected build left an output root'

if "$issuer" "$source_root" "$tmp/wrong-raw" 1 \
	"$source_avb_sha" \
	ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff \
	>"$tmp/wrong-raw.out" 2>"$tmp/wrong-raw.err"; then
	fail 'wrong source raw identity was accepted'
fi
grep -Fq 'source raw wrapper identity changed' "$tmp/wrong-raw.err"
[[ ! -e $tmp/wrong-raw ]] || fail 'raw-identity rejection left an output root'

if "$issuer" "$source_root" "$tmp/invalid-generation" 01 \
	"$source_avb_sha" "$raw_sha" >"$tmp/invalid.out" 2>"$tmp/invalid.err"; then
	fail 'noncanonical generation was accepted'
fi
grep -Fq 'canonical nonnegative integer' "$tmp/invalid.err"

mkdir "$tmp/preexisting"
if "$issuer" "$source_root" "$tmp/preexisting" 1 \
	"$source_avb_sha" "$raw_sha" >"$tmp/preexisting.out" \
	2>"$tmp/preexisting.err"; then
	fail 'pre-existing output root was accepted'
fi
grep -Fq 'refusing an existing AVB-generation output root' \
	"$tmp/preexisting.err"

noncanonical=$tmp/noncanonical-source
cp -a "$source_root" "$noncanonical"
for suffix in a b; do
	cp "$noncanonical/repack/stable-recovery-$suffix.raw.img" \
		"$noncanonical/repack/stable-recovery-$suffix.avb.img"
	python3 "$avbtool" add_hash_footer \
		--image "$noncanonical/repack/stable-recovery-$suffix.avb.img" \
		--partition_name boot --partition_size 131072 --algorithm NONE \
		--salt ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff
done
noncanonical_sha=$(sha256sum \
	"$noncanonical/repack/stable-recovery-a.avb.img" | cut -d ' ' -f 1)
if "$issuer" "$noncanonical" "$tmp/noncanonical-output" 1 \
	"$noncanonical_sha" "$raw_sha" >"$tmp/noncanonical.out" \
	2>"$tmp/noncanonical.err"; then
	fail 'noncanonical generation-zero source was accepted'
fi
grep -Fq 'not the canonical generation-zero encoding' \
	"$tmp/noncanonical.err"
[[ ! -e $tmp/noncanonical-output ]] ||
	fail 'canonicality rejection left an output root'

ln -s stable-recovery-a.raw.img \
	"$source_root/repack/stable-recovery-b.raw.img.link"
mv "$source_root/repack/stable-recovery-b.raw.img" \
	"$source_root/repack/stable-recovery-b.raw.img.real"
mv "$source_root/repack/stable-recovery-b.raw.img.link" \
	"$source_root/repack/stable-recovery-b.raw.img"
if "$issuer" "$source_root" "$tmp/symlink" 1 \
	"$source_avb_sha" "$raw_sha" >"$tmp/symlink.out" 2>"$tmp/symlink.err"; then
	fail 'symlinked source input was accepted'
fi
grep -Fq 'unsafe source wrapper input' "$tmp/symlink.err"

echo 'PASS stable-recovery AVB generation issuance is deterministic, legacy-reproducing, descriptor-bound, and fail-closed'
