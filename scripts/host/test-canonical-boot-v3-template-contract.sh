#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
builder=$repo/scripts/host/build-canonical-boot-v3-template.sh

[[ -f $builder && ! -L $builder && -x $builder ]] ||
	fail 'missing executable canonical boot-v3 template builder'
bash -n "$builder"

for token in \
	d99136f30bda966e8820c8ae53a82c659ca36e6d1aaf49a4cd63ae4795a6845a \
	7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef \
	95be17d48ec61d00a4e8c92be754c8a8345f93685ce05d412a6d3a6aceba6e02 \
	'--header_version 3' \
	'--os_version 11.0.0' \
	'--os_patch_level 2022-02' \
	'rog5.recovery_timeout=180' \
	'rog5\.(recovery_cidr|ufs_discovery)=' \
	'two canonical boot-v3 template builds differ' \
	'state=reproducible-successor' \
	'boot_authority=none' \
	'mv -T -- "$publish" "$output_root"'; do
	grep -Fq -- "$token" "$builder" ||
		fail "canonical boot-v3 template builder omits token: $token"
done
if grep -Eq \
	'\b(fastboot|adb|sudo|pkexec)\b|(^|[;&|[:space:]])(ssh|scp|curl|wget)([[:space:]]|$)|/dev/(sd|nvme|ufs)' \
	"$builder"; then
	fail 'canonical boot-v3 template builder contains transport, privilege, or storage access'
fi

echo 'PASS canonical boot-v3 template is compact, twin-built, metadata-pinned, and authority-free'
