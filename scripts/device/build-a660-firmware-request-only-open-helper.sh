#!/bin/sh
set -eu

repo=${REPO_ROOT:-/workspace/repo}
output_dir=${OUTPUT_DIR:-/root/build/a660-firmware-request-only-open}
source_file=$repo/tools/diagnostics/a660-firmware-request-only-open.c
source_verifier=$repo/scripts/device/verify-a660-firmware-request-only-open-source.sh
expected_output=/root/build/a660-firmware-request-only-open
expected_source=68f7dbb0669b2b386fba2434c58aeb039917ba1ca229479c53a1d729f124f3ef
binary=$output_dir/rog5-a660-firmware-request-only-open
meta=$output_dir/build-meta.txt

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "$output_dir" = "$expected_output" ] ||
	fail "OUTPUT_DIR must be $expected_output"
[ -x "$source_verifier" ] || fail 'missing source verifier'
[ -f "$source_file" ] && [ ! -L "$source_file" ] ||
	fail 'missing helper source'
[ "$(sha256sum "$source_file" | cut -d ' ' -f 1)" = \
	"$expected_source" ] ||
	fail 'helper source hash mismatch'
[ ! -d "$output_dir" ] ||
	[ -z "$(find "$output_dir" -mindepth 1 -maxdepth 1 -print -quit)" ] ||
	fail 'helper output directory is not empty'

for command in cat chmod clang cut find head mkdir mv sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing build command: $command"
done

"$source_verifier" "$source_file" >/dev/null
umask 022
mkdir -p "$output_dir"

clang --target=aarch64-linux-gnu -std=c11 -Oz \
	-ffreestanding -fno-builtin -fno-stack-protector \
	-fno-asynchronous-unwind-tables -fno-unwind-tables -fno-ident \
	-fno-pic -fno-pie -nostdlib -static -fuse-ld=lld \
	-Wl,-e,_start -Wl,--build-id=none -Wl,--no-dynamic-linker \
	-Wl,-z,noexecstack -Wl,-s \
	-o "$binary.tmp" "$source_file"
chmod 0755 "$binary.tmp"
mv "$binary.tmp" "$binary"

{
	printf 'format=rog5-a660-firmware-request-only-open-v1\n'
	printf 'source_sha256=%s\n' "$expected_source"
	printf 'compiler=%s\n' "$(clang --version | head -1)"
	printf 'binary_sha256=%s\n' \
		"$(sha256sum "$binary" | cut -d ' ' -f 1)"
} >"$meta"
chmod 0644 "$meta"

cat "$meta"
echo 'PASS built freestanding AArch64 one-open EUCLEAN helper'
