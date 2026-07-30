#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
builder=$repo/scripts/host/reconstruct-network-root-v3.sh

[[ -f $builder && ! -L $builder && -x $builder ]] ||
	fail 'missing executable network-root-v3 reconstruction builder'
bash -n "$builder"

for token in \
	da573d089cd617e088624b6d6bf711e193a4df5367843293e2e5ba543556e51d \
	1cc4bc1e4a9e3be19e9c7c669cebee24b508fd68 \
	260e386875d2677b77667c38f39eb1b3be2db9e9 \
	df1d0cdb95513d7ef6d772a3a6165d37b3b226682d92e30a2143409341bbefb1 \
	adb50a98fe5fe79453d9adfb0b49f0c5bad4f617 \
	a2c9753310c4f5dbb801bd0b0c655f3d0b860647 \
	56c4a643e66fdc96b8754c46bcd8af0bb2f1da47 \
	4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac \
	'expected P2-created usr/local/sbin directory is absent or linked' \
	'P2-created usr/local/sbin directory is not empty' \
	'accepted UFS-v2 intermediate archive' \
	'state=exact-historical-bytes-recovered' \
	'boot_authority=none' \
	'qualified-tool-shims/cpio' \
	'qualified-tool-shims/gzip' \
	'--reproducible' \
	'LC_ALL=C sort -z' \
	'ln "$archive_stage" "$output_archive"'; do
	grep -Fq -- "$token" "$builder" ||
		fail "network-root-v3 builder omits contract token: $token"
done

if grep -Eq \
	'\b(fastboot|adb|sudo|pkexec)\b|(^|[;&|[:space:]])(ssh|scp)([[:space:]]|$)|/dev/(sd|nvme|ufs)' \
	"$builder"; then
	fail 'network-root-v3 reconstruction contains live, privilege, or storage transport'
fi

echo 'PASS network-root-v3 reconstruction is exact-parent-gated, credential-free, and host-isolated'
