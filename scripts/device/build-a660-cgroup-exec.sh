#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

output=${1:?usage: build-a660-cgroup-exec.sh OUTPUT}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
source_file=$repo/tools/a660/rog5-cgroup-exec.c
compiler=${CC:-cc}
epoch=1681862400

case $output in
	/*) ;;
	*) fail 'output path must be absolute' ;;
esac
case $compiler in
	''|*[!A-Za-z0-9_+./-]*) fail 'CC must be one command path or name' ;;
esac
for command in cmp cut id install ln mktemp readelf rm sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing cgroup-exec build command: $command"
done
command -v "$compiler" >/dev/null || fail 'C compiler is unavailable'
[ -f "$source_file" ] && [ ! -L "$source_file" ] ||
	fail 'cgroup-exec source is absent or linked'

output_parent=$(dirname -- "$output")
output_name=$(basename -- "$output")
case $output_name in ''|.|..) fail 'output name is invalid' ;; esac
[ -d "$output_parent" ] && [ ! -L "$output_parent" ] ||
	fail 'output parent is absent or linked'
output_parent=$(CDPATH='' cd -- "$output_parent" && pwd -P)
[ "$output" = "$output_parent/$output_name" ] ||
	fail 'output path is not canonical'
exec 7<"$output_parent" || fail 'cannot pin output parent'
[ "$(stat -Lc %u /proc/self/fd/7)" = "$(id -u)" ] ||
	fail 'output parent is not owned by the caller'
parent_mode=$(stat -Lc %a /proc/self/fd/7)
case $parent_mode in *[!0-7]*|'') fail 'output parent mode is invalid' ;; esac
[ $(((0$parent_mode) & 022)) -eq 0 ] ||
	fail 'output parent is group- or world-writable'
parent_identity=$(stat -Lc '%d:%i' /proc/self/fd/7)
[ "$(stat -Lc '%d:%i' "$output_parent")" = "$parent_identity" ] ||
	fail 'output parent identity changed'
output_anchor=/proc/self/fd/7/$output_name
[ ! -e "$output_anchor" ] && [ ! -L "$output_anchor" ] ||
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
	fail 'two clean cgroup-exec builds differ'
readelf -h "$build_root/first" | grep -q 'Machine:.*AArch64' ||
	fail 'cgroup-exec is not AArch64'
if readelf -l "$build_root/first" |
	grep -q 'Requesting program interpreter'; then
	fail 'cgroup-exec has a program interpreter'
fi
if readelf -d "$build_root/first" 2>/dev/null |
	grep -q 'Shared library:'; then
	fail 'cgroup-exec has a shared-library dependency'
fi

output_stage=$(mktemp "/proc/self/fd/7/.rog5-cgroup-exec.XXXXXX")
install -m 0755 "$build_root/first" "$output_stage"
ln "$output_stage" "$output_anchor" 2>/dev/null ||
	fail 'output appeared during cgroup-exec build'
exec 8<"$output_anchor" || fail 'cannot pin published cgroup-exec'
published_identity=$(stat -Lc '%d:%i' /proc/self/fd/8)
[ "$(stat -Lc '%d:%i' "$output_stage")" = "$published_identity" ] ||
	fail 'published cgroup-exec identity changed'
rm -f -- "$output_stage"
output_stage=
[ "$(stat -Lc '%d:%i' "$output_anchor")" = "$published_identity" ] ||
	fail 'published cgroup-exec path changed'

printf 'format=rog5-a660-cgroup-exec-build-v1\n'
printf 'size=%s\n' "$(stat -Lc %s /proc/self/fd/8)"
printf 'sha256=%s\n' \
	"$(sha256sum /proc/self/fd/8 | cut -d ' ' -f 1)"
