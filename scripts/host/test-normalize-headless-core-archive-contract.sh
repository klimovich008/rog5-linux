#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
normalizer=$repo/scripts/host/normalize-headless-core-archive.sh
stage=$repo/scripts/host/stage-arch-rootfs.sh
comparator=$repo/scripts/host/compare-root-archives.py

for path in "$normalizer" "$stage" "$comparator"; do
	[[ -f $path && ! -L $path && -x $path ]] ||
		fail "missing executable archive-normalization input: ${path#"$repo"/}"
	case $path in
		*.sh) bash -n "$path" ;;
		*.py) python3 -m py_compile "$path" ;;
	esac
done

for token in \
	rog5-arch-headless-core-7.1.4.tar.gz \
	rog5-arch-headless-core-network-source-7.1.4.tar.gz \
	'--null --no-recursion --format pax' \
	'--acls --xattrs --fflags --no-read-sparse' \
	'compare-root-archives.py' \
	'persistent-root-tool.py' \
	'verify-staged-arch-headless-core-rootfs.sh' \
	'cmp "$work/source.tree" "$work/normalized.tree"' \
	'ln -- "$stage" "$output_archive"' \
	'trap cleanup EXIT HUP INT TERM'; do
	grep -Fq -- "$token" "$normalizer" ||
		fail "archive normalizer omits contract token: $token"
done

output_mount_count=$(grep -Fc -- \
	'--mount "type=bind,source=$work,target=/output"' "$normalizer")
[[ $output_mount_count == 1 ]] ||
	fail 'normalizer must grant output writes only to the archive encoder'

if grep -Eq \
	'\b(fastboot|adb|ssh|scp|systemctl|pkexec|sudo)\b|/dev/(sd|nvme|ufs)' \
	"$normalizer"; then
	fail 'archive normalizer contains phone, privilege, or storage transport'
fi
if grep -Eq \
	'\b(fastboot|adb|ssh|scp|systemctl|pkexec|sudo)\b|/dev/(sd|nvme|ufs)' \
	"$comparator"; then
	fail 'archive comparator contains phone, privilege, or storage transport'
fi
grep -Fq 'headless-v2)' "$stage" ||
	fail 'rootfs stage omits the headless-core generation'
if grep -Fq 'archive_sparse_policy=dense' "$stage"; then
	fail 'pinned headless-core source generation was silently re-encoded'
fi
grep -Fq 'bsdtar --acls --xattrs --fflags' "$stage" ||
	fail 'pinned headless-core source generation lost its original encoder'

echo 'PASS headless-core archive normalization is exact, dense, reproducible, and hardware-free'
