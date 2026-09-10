#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

output=${1:?usage: build-persistent-root-verifier-static.sh OUTPUT}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
source_file=$repo/tools/persistent-root-verify.c
compiler=${CC:-aarch64-linux-musl-gcc}
epoch=1681862400

case $output in
	/*) ;;
	*) fail 'output path must be absolute' ;;
esac
case $compiler in
	''|*[!A-Za-z0-9_+./-]*) fail 'CC must be one command path or name' ;;
esac
for command in cmp cut dirname grep install ln mktemp readelf rm \
	sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing static verifier build command: $command"
done
command -v "$compiler" >/dev/null ||
	fail 'AArch64 musl C compiler is unavailable'
[ -f "$source_file" ] && [ ! -L "$source_file" ] ||
	fail 'persistent-root verifier source is absent or linked'
output_parent=$(dirname -- "$output")
[ -d "$output_parent" ] && [ ! -L "$output_parent" ] ||
	fail 'output parent is absent or linked'
[ ! -e "$output" ] && [ ! -L "$output" ] ||
	fail 'output already exists'

build_root=$(mktemp -d)
output_stage=
cleanup() {
	[ -z "$output_stage" ] || rm -f -- "$output_stage"
	rm -rf -- "$build_root"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
export LC_ALL=C
export SOURCE_DATE_EPOCH=$epoch
export TZ=UTC

build_one() {
	target=$1
	"$compiler" \
		-static -std=c11 -O2 -fstack-protector-strong \
		-Wall -Wextra -Werror \
		-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none \
		"$source_file" -o "$target"
}

build_one "$build_root/first"
build_one "$build_root/second"
cmp "$build_root/first" "$build_root/second" ||
	fail 'two clean static verifier builds differ'
readelf -h "$build_root/first" | grep -q 'Machine:.*AArch64' ||
	fail 'static verifier is not AArch64'
if readelf -l "$build_root/first" |
	grep -q 'Requesting program interpreter'; then
	fail 'static verifier has a program interpreter'
fi
if readelf -d "$build_root/first" 2>/dev/null |
	grep -q 'Shared library:'; then
	fail 'static verifier has a shared-library dependency'
fi

output_stage=$(mktemp "$output_parent/.persistent-root-verify.XXXXXX")
install -m 0755 "$build_root/first" "$output_stage"
ln "$output_stage" "$output" 2>/dev/null ||
	fail 'output appeared during build'
rm -f -- "$output_stage"
output_stage=
printf 'format=rog5-persistent-root-verifier-static-v1\n'
printf 'size=%s\n' "$(stat -c %s "$output")"
printf 'sha256=%s\n' "$(sha256sum "$output" | cut -d ' ' -f 1)"
