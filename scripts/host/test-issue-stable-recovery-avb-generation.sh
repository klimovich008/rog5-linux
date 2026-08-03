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
"$issuer" "$source_root" "$tmp/gen3" 3 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen3.out"

# Generation four is the first production candidate issued after the nested
# recovery/host deadline fix. Exercise its exact generation record twice before
# any real artifact is issued so a stale or nondeterministic encoder fails
# without involving the phone.
"$issuer" "$source_root" "$tmp/gen4-a" 4 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen4-a.out"
"$issuer" "$source_root" "$tmp/gen4-b" 4 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen4-b.out"
cmp "$tmp/gen4-a/repack/stable-recovery-a.avb.img" \
	"$tmp/gen4-b/repack/stable-recovery-a.avb.img"
cmp "$tmp/gen4-a/repack/stable-recovery-b.avb.img" \
	"$tmp/gen4-b/repack/stable-recovery-b.avb.img"
cmp "$tmp/gen4-a/avb-generation.txt" "$tmp/gen4-b/avb-generation.txt"
for predecessor in gen1-a gen2 gen3; do
	! cmp -s "$tmp/$predecessor/repack/stable-recovery-a.avb.img" \
		"$tmp/gen4-a/repack/stable-recovery-a.avb.img" ||
		fail "generation four reused the $predecessor AVB wrapper"
done
expected_gen4_salt=$(
	printf 'format=rog5-stable-recovery-avb-generation-v1\nraw_sha256=%s\ngeneration=4\n' \
		"$raw_sha" | sha256sum | cut -d ' ' -f 1
)
grep -Fxq 'generation=4' "$tmp/gen4-a/avb-generation.txt"
grep -Fxq "salt=$expected_gen4_salt" "$tmp/gen4-a/avb-generation.txt"
grep -Fxq 'authority=none' "$tmp/gen4-a/avb-generation.txt"
gen4_info=$(python3 "$avbtool" info_image \
	--image "$tmp/gen4-a/repack/stable-recovery-a.avb.img")
[[ $(awk '/^      Salt:/ { print $2; exit }' <<<"$gen4_info") == \
	"$expected_gen4_salt" ]] || fail 'generation-four descriptor salt changed'
gen4_digest=$(awk '/^      Digest:/ { print $2; exit }' <<<"$gen4_info")
grep -Fxq "digest=$gen4_digest" "$tmp/gen4-a/avb-generation.txt"

# Generation five is the first candidate issued after the host-side
# pre-commit fallback and transfer-observability correction. Prove its exact
# deterministic identity twice and keep it distinct from every predecessor
# before creating either production output.
"$issuer" "$source_root" "$tmp/gen5-a" 5 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen5-a.out"
"$issuer" "$source_root" "$tmp/gen5-b" 5 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen5-b.out"
cmp "$tmp/gen5-a/repack/stable-recovery-a.avb.img" \
	"$tmp/gen5-b/repack/stable-recovery-a.avb.img"
cmp "$tmp/gen5-a/repack/stable-recovery-b.avb.img" \
	"$tmp/gen5-b/repack/stable-recovery-b.avb.img"
cmp "$tmp/gen5-a/avb-generation.txt" "$tmp/gen5-b/avb-generation.txt"
for predecessor in gen1-a gen2 gen3 gen4-a; do
	! cmp -s "$tmp/$predecessor/repack/stable-recovery-a.avb.img" \
		"$tmp/gen5-a/repack/stable-recovery-a.avb.img" ||
		fail "generation five reused the $predecessor AVB wrapper"
done
expected_gen5_salt=$(
	printf 'format=rog5-stable-recovery-avb-generation-v1\nraw_sha256=%s\ngeneration=5\n' \
		"$raw_sha" | sha256sum | cut -d ' ' -f 1
)
grep -Fxq 'generation=5' "$tmp/gen5-a/avb-generation.txt"
grep -Fxq "salt=$expected_gen5_salt" "$tmp/gen5-a/avb-generation.txt"
grep -Fxq 'authority=none' "$tmp/gen5-a/avb-generation.txt"
gen5_info=$(python3 "$avbtool" info_image \
	--image "$tmp/gen5-a/repack/stable-recovery-a.avb.img")
[[ $(awk '/^      Salt:/ { print $2; exit }' <<<"$gen5_info") == \
	"$expected_gen5_salt" ]] || fail 'generation-five descriptor salt changed'
gen5_digest=$(awk '/^      Digest:/ { print $2; exit }' <<<"$gen5_info")
grep -Fxq "digest=$gen5_digest" "$tmp/gen5-a/avb-generation.txt"

# Generation six is the first candidate issued after correcting and installing
# the recovery-host broker's inherited signal mask. Keep the recovery payload
# unchanged, prove the new wrapper twice, and reject identity reuse from every
# earlier nonzero generation before any production output is created.
"$issuer" "$source_root" "$tmp/gen6-a" 6 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen6-a.out"
"$issuer" "$source_root" "$tmp/gen6-b" 6 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen6-b.out"
cmp "$tmp/gen6-a/repack/stable-recovery-a.avb.img" \
	"$tmp/gen6-b/repack/stable-recovery-a.avb.img"
cmp "$tmp/gen6-a/repack/stable-recovery-b.avb.img" \
	"$tmp/gen6-b/repack/stable-recovery-b.avb.img"
cmp "$tmp/gen6-a/avb-generation.txt" "$tmp/gen6-b/avb-generation.txt"
for predecessor in gen1-a gen2 gen3 gen4-a gen5-a; do
	for suffix in a b; do
		! cmp -s "$tmp/$predecessor/repack/stable-recovery-$suffix.avb.img" \
			"$tmp/gen6-a/repack/stable-recovery-$suffix.avb.img" ||
			fail "generation six reused the $predecessor twin-$suffix AVB wrapper"
	done
done
expected_gen6_salt=$(
	printf 'format=rog5-stable-recovery-avb-generation-v1\nraw_sha256=%s\ngeneration=6\n' \
		"$raw_sha" | sha256sum | cut -d ' ' -f 1
)
grep -Fxq 'generation=6' "$tmp/gen6-a/avb-generation.txt"
grep -Fxq "salt=$expected_gen6_salt" "$tmp/gen6-a/avb-generation.txt"
grep -Fxq 'authority=none' "$tmp/gen6-a/avb-generation.txt"
gen6_info=$(python3 "$avbtool" info_image \
	--image "$tmp/gen6-a/repack/stable-recovery-a.avb.img")
[[ $(awk '/^      Salt:/ { print $2; exit }' <<<"$gen6_info") == \
	"$expected_gen6_salt" ]] || fail 'generation-six descriptor salt changed'
gen6_digest=$(awk '/^      Digest:/ { print $2; exit }' <<<"$gen6_info")
grep -Fxq "digest=$gen6_digest" "$tmp/gen6-a/avb-generation.txt"

# Generation seven is the first candidate issued after the host verifier began
# accepting only the exact deferred fallback-profile association. Prove the
# issuer remains deterministic and distinct before that artifact can acquire
# a separate live profile or temporary-boot policy row.
"$issuer" "$source_root" "$tmp/gen7-a" 7 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen7-a.out"
"$issuer" "$source_root" "$tmp/gen7-b" 7 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen7-b.out"
cmp "$tmp/gen7-a/repack/stable-recovery-a.avb.img" \
	"$tmp/gen7-b/repack/stable-recovery-a.avb.img"
cmp "$tmp/gen7-a/repack/stable-recovery-b.avb.img" \
	"$tmp/gen7-b/repack/stable-recovery-b.avb.img"
cmp "$tmp/gen7-a/repack/stable-recovery-a.raw.img" \
	"$tmp/gen7-b/repack/stable-recovery-a.raw.img"
cmp "$tmp/gen7-a/repack/stable-recovery-b.raw.img" \
	"$tmp/gen7-b/repack/stable-recovery-b.raw.img"
cmp "$tmp/gen7-a/avb-generation.txt" "$tmp/gen7-b/avb-generation.txt"
cmp "$tmp/gen7-a.out" "$tmp/gen7-b.out"
for predecessor in gen1-a gen2 gen3 gen4-a gen5-a gen6-a; do
	for suffix in a b; do
		! cmp -s "$tmp/$predecessor/repack/stable-recovery-$suffix.avb.img" \
			"$tmp/gen7-a/repack/stable-recovery-$suffix.avb.img" ||
			fail "generation seven reused the $predecessor twin-$suffix AVB wrapper"
	done
done
expected_gen7_salt=$(
	printf 'format=rog5-stable-recovery-avb-generation-v1\nraw_sha256=%s\ngeneration=7\n' \
		"$raw_sha" | sha256sum | cut -d ' ' -f 1
)
grep -Fxq 'generation=7' "$tmp/gen7-a/avb-generation.txt"
grep -Fxq "salt=$expected_gen7_salt" "$tmp/gen7-a/avb-generation.txt"
grep -Fxq 'authority=none' "$tmp/gen7-a/avb-generation.txt"
gen7_info=$(python3 "$avbtool" info_image \
	--image "$tmp/gen7-a/repack/stable-recovery-a.avb.img")
[[ $(awk '/^      Salt:/ { print $2; exit }' <<<"$gen7_info") == \
	"$expected_gen7_salt" ]] || fail 'generation-seven descriptor salt changed'
gen7_digest=$(awk '/^      Digest:/ { print $2; exit }' <<<"$gen7_info")
grep -Fxq "digest=$gen7_digest" "$tmp/gen7-a/avb-generation.txt"

# Generation eight is the first candidate eligible for issuance after the
# host verifier learned NetworkManager 1.52.1's exact one-empty-field NULL
# rendering. Prove deterministic twins and non-reuse through Generation 7
# before any production output is created.
"$issuer" "$source_root" "$tmp/gen8-a" 8 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen8-a.out"
"$issuer" "$source_root" "$tmp/gen8-b" 8 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen8-b.out"
cmp "$tmp/gen8-a/repack/stable-recovery-a.avb.img" \
	"$tmp/gen8-b/repack/stable-recovery-a.avb.img"
cmp "$tmp/gen8-a/repack/stable-recovery-b.avb.img" \
	"$tmp/gen8-b/repack/stable-recovery-b.avb.img"
cmp "$tmp/gen8-a/repack/stable-recovery-a.avb.img" \
	"$tmp/gen8-a/repack/stable-recovery-b.avb.img"
cmp "$tmp/gen8-a/repack/stable-recovery-a.raw.img" \
	"$tmp/gen8-b/repack/stable-recovery-a.raw.img"
cmp "$tmp/gen8-a/repack/stable-recovery-b.raw.img" \
	"$tmp/gen8-b/repack/stable-recovery-b.raw.img"
cmp "$tmp/gen8-a/repack/stable-recovery-a.raw.img" \
	"$tmp/gen8-a/repack/stable-recovery-b.raw.img"
cmp "$tmp/gen8-a/avb-generation.txt" "$tmp/gen8-b/avb-generation.txt"
cmp "$tmp/gen8-a.out" "$tmp/gen8-b.out"
for predecessor in gen1-a gen2 gen3 gen4-a gen5-a gen6-a gen7-a; do
	for suffix in a b; do
		! cmp -s "$tmp/$predecessor/repack/stable-recovery-$suffix.avb.img" \
			"$tmp/gen8-a/repack/stable-recovery-$suffix.avb.img" ||
			fail "generation eight reused the $predecessor twin-$suffix AVB wrapper"
	done
done
expected_gen8_salt=$(
	printf 'format=rog5-stable-recovery-avb-generation-v1\nraw_sha256=%s\ngeneration=8\n' \
		"$raw_sha" | sha256sum | cut -d ' ' -f 1
)
grep -Fxq 'generation=8' "$tmp/gen8-a/avb-generation.txt"
grep -Fxq "salt=$expected_gen8_salt" "$tmp/gen8-a/avb-generation.txt"
grep -Fxq 'authority=none' "$tmp/gen8-a/avb-generation.txt"
gen8_info=$(python3 "$avbtool" info_image \
	--image "$tmp/gen8-a/repack/stable-recovery-a.avb.img")
[[ $(awk '/^      Salt:/ { print $2; exit }' <<<"$gen8_info") == \
	"$expected_gen8_salt" ]] || fail 'generation-eight descriptor salt changed'
gen8_digest=$(awk '/^      Digest:/ { print $2; exit }' <<<"$gen8_info")
grep -Fxq "digest=$gen8_digest" "$tmp/gen8-a/avb-generation.txt"

# Generation nine is the first candidate eligible for issuance after adding
# bounded, non-sensitive recovery ACM stability classification. Prove two
# disposable runs are byte-identical, preserve both raw twins, and cannot
# reuse any predecessor before retained output is created.
"$issuer" "$source_root" "$tmp/gen9-a" 9 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen9-a.out"
"$issuer" "$source_root" "$tmp/gen9-b" 9 "$source_avb_sha" "$raw_sha" \
	>"$tmp/gen9-b.out"
for suffix in a b; do
	cmp "$tmp/gen9-a/repack/stable-recovery-$suffix.avb.img" \
		"$tmp/gen9-b/repack/stable-recovery-$suffix.avb.img"
	cmp "$tmp/gen9-a/repack/stable-recovery-$suffix.raw.img" \
		"$tmp/gen9-b/repack/stable-recovery-$suffix.raw.img"
	cmp "$tmp/gen9-a/repack/stable-recovery-$suffix.raw.img" \
		"$source_root/repack/stable-recovery-$suffix.raw.img"
done
cmp "$tmp/gen9-a/repack/stable-recovery-a.avb.img" \
	"$tmp/gen9-a/repack/stable-recovery-b.avb.img"
cmp "$tmp/gen9-a/repack/stable-recovery-a.raw.img" \
	"$tmp/gen9-a/repack/stable-recovery-b.raw.img"
cmp "$tmp/gen9-a/avb-generation.txt" "$tmp/gen9-b/avb-generation.txt"
cmp "$tmp/gen9-a.out" "$tmp/gen9-b.out"
for predecessor in gen1-a gen2 gen3 gen4-a gen5-a gen6-a gen7-a gen8-a; do
	for suffix in a b; do
		! cmp -s "$tmp/$predecessor/repack/stable-recovery-$suffix.avb.img" \
			"$tmp/gen9-a/repack/stable-recovery-$suffix.avb.img" ||
			fail "generation nine reused the $predecessor twin-$suffix AVB wrapper"
	done
done
expected_gen9_salt=$(
	printf 'format=rog5-stable-recovery-avb-generation-v1\nraw_sha256=%s\ngeneration=9\n' \
		"$raw_sha" | sha256sum | cut -d ' ' -f 1
)
grep -Fxq 'generation=9' "$tmp/gen9-a/avb-generation.txt"
grep -Fxq "salt=$expected_gen9_salt" "$tmp/gen9-a/avb-generation.txt"
grep -Fxq 'authority=none' "$tmp/gen9-a/avb-generation.txt"
gen9_info=$(python3 "$avbtool" info_image \
	--image "$tmp/gen9-a/repack/stable-recovery-a.avb.img")
[[ $(awk '/^      Salt:/ { print $2; exit }' <<<"$gen9_info") == \
	"$expected_gen9_salt" ]] || fail 'generation-nine descriptor salt changed'
gen9_digest=$(awk '/^      Digest:/ { print $2; exit }' <<<"$gen9_info")
grep -Fxq "digest=$gen9_digest" "$tmp/gen9-a/avb-generation.txt"

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
