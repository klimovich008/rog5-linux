#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
profile=$repo/configs/recovery-wrapper-cache/asus-5.4-stable-recovery-v1.json
cache_tool=$repo/scripts/host/stable-recovery-wrapper-cache.py
cache_test=$repo/scripts/host/test-stable-recovery-wrapper-cache.py
source_seal_tool=$repo/scripts/host/kernel-source-seal.py
source_seal_test=$repo/scripts/host/test-kernel-source-seal.py
materializer=$repo/scripts/host/materialize-stable-recovery-wrapper-cache.sh
full_gate=$repo/scripts/host/test-stable-recovery-wrapper-offline.sh

for path in "$cache_tool" "$cache_test" "$source_seal_tool" \
	"$source_seal_test" "$materializer" "$full_gate"; do
	[[ -f $path && ! -L $path && -x $path ]] ||
		fail "missing executable wrapper-cache input: ${path#"$repo"/}"
	case $path in
		*.py) python3 -m py_compile "$path" ;;
		*) bash -n "$path" ;;
	esac
done
[[ -f $profile && ! -L $profile ]] ||
	fail 'missing stable-recovery wrapper-cache profile'

for token in \
	rog5-stable-recovery-wrapper-cache-profile-v1 \
	rog5-kernel-source-tree-v1 \
	592aefb37589f9f9483b43677e29702ed927fc56a251616e33e81f2645e9c35a \
	b5ed3261a858680b05a3a7247e2d7948e722f71be812fcdc66972594d22c097a \
	df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f \
	c5b80647ddd7fb29464b4735abbe27012ee4dc89be559b44b25c9b1ff59c9cec \
	sha256:8513960144bb1ca77878a1364c03fb100c8b87fffb8440fd37a6cc4fc0043b41 \
	aaaa423aefc9b90dd30738bf42a0209574437599da2062b9dd8cc685d6e15b94 \
	d098fb07c4c0d1ac984add4685924d9139473f3bd39f9198cb78a791f4d1b116; do
	grep -Fq "$token" "$profile" ||
		fail "wrapper-cache profile omits identity: $token"
done

for token in \
	'rog5-kernel-source-tree-v1' \
	'O_NOFOLLOW' \
	'kernel source crosses a filesystem boundary' \
	'kernel source file changed while hashing'; do
	grep -Fq "$token" "$source_seal_tool" ||
		fail "kernel source seal omits contract: $token"
done

for token in \
	RENAME_NOREPLACE \
	'expected cache entry ID is not SHA-256' \
	'ASUS source tree changed across the twin build' \
	'cache input binding changed' \
	'wrapper Image does not embed the initramfs exactly once' \
	'refusing an existing materialization output'; do
	grep -Fq "$token" "$cache_tool" ||
		fail "wrapper-cache implementation omits contract: $token"
done

for token in \
	'--expected-entry-id' \
	'wrapper cache must be below the ignored repository build directory' \
	'materialized wrapper output overlaps the cache' \
	'authority=none' \
	'--network=none'; do
	grep -Fq -- "$token" "$materializer" ||
		fail "wrapper-cache materializer omits contract: $token"
done

python3 - "$full_gate" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
tokens = (
    'seal_source >"$source_seal_before"',
    'python3 "$cache_tool" input-key',
    'build_wrapper a "$initramfs_a"',
    'build_wrapper b "$initramfs_b"',
    'python3 "$avbtool" verify_image',
    'seal_source >"$source_seal_after"',
    'python3 "$cache_tool" publish',
    "PASS two clean stable-recovery wrapper/raw/AVB builds",
)
positions = [text.index(token) for token in tokens]
if positions != sorted(positions):
    raise SystemExit("wrapper cache is published before its complete twin gate")
PY

if grep -Eq \
	'\b(fastboot|adb|ssh|scp|systemctl|pkexec|sudo)\b|/dev/(sd|nvme|ufs)' \
	"$cache_tool" "$materializer"; then
	fail 'wrapper cache contains phone, privilege, or storage transport'
fi
if grep -Eq \
	'\b(subprocess|socket|requests|urllib)\b' "$cache_tool"; then
	fail 'wrapper cache unexpectedly exposes a process or network client'
fi

echo 'PASS stable-recovery wrapper cache is source-sealed, content-addressed, no-replace, output-pinned, and hardware-free'
