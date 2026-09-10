#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
builder=$repo/scripts/host/reconstruct-recovery-base-v18r.sh
cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
gzip_shim=$repo/scripts/host/qualified-tool-shims/gzip

for path in "$builder" "$cpio_shim" "$gzip_shim"; do
	[[ -f $path && ! -L $path && -x $path ]] ||
		fail "missing executable v18r contract input: ${path#"$repo"/}"
	bash -n "$path"
done

for token in \
	e2b58d50fae31509b8cd87ed01afbf25c90d49500e3d9d9691ecd77643fd434e \
	438aaf1c99455e23ff27f758738e779b0fd318e68c58467eeae7b77c55a87520 \
	339bcfae13ca19dbcb38c1ee8f586988597355ec \
	563ba046ab6d481ec4eb425793f3df9b0d8c6ee4 \
	852b02a2cbcb2dfd43598269ff1b2b10cb1542e90ab7a7aa32d1a26c7cc645fc \
	da573d089cd617e088624b6d6bf711e193a4df5367843293e2e5ba543556e51d \
	'independent retained lineages did not converge byte-for-byte' \
	'state=reconstructed-successor' \
	'boot_authority=none' \
	'original-bytes-unrecovered-and-not-reused' \
	'qualified-tool-shims/cpio' \
	'qualified-tool-shims/gzip' \
	'verify-steam-deck-builder.sh' \
	'--reproducible' \
	'LC_ALL=C sort -z' \
	'mv -T -- "$publish" "$output_root"'; do
	grep -Fq -- "$token" "$builder" ||
		fail "v18r builder omits contract token: $token"
done

for token in \
	'--network=none' \
	'verify-steam-deck-builder.sh' \
	'"$image" gzip "$@"'; do
	grep -Fq -- "$token" "$gzip_shim" ||
		fail "qualified gzip shim omits contract token: $token"
done

if grep -Eq \
	'\b(fastboot|adb|sudo|pkexec)\b|(^|[;&|[:space:]])(ssh|scp)([[:space:]]|$)|/dev/(sd|nvme|ufs)' \
	"$builder" "$gzip_shim"; then
	fail 'v18r reconstruction contains live, privilege, or storage transport'
fi
if grep -Fq \
	'artifacts/recovery-stage-v18/rog5-recovery-initramfs.cpio.gz' \
	"$builder"; then
	fail 'v18r reconstruction overwrites the historical v18 artifact path'
fi

echo 'PASS v18r reconstruction contract is dual-lineage, successor-only, and host-isolated'
