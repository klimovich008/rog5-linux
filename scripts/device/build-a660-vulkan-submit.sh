#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

output=${1:?usage: build-a660-vulkan-submit.sh OUTPUT}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
source_file=$repo/tools/a660/rog5-vulkan-submit.c
compiler=${CC:-cc}

case $output in
	/*) ;;
	*) fail 'output path must be absolute' ;;
esac
case $compiler in
	''|*[!A-Za-z0-9_+./-]*) fail 'CC must be one command path or name' ;;
esac
command -v "$compiler" >/dev/null || fail 'C compiler is unavailable'
command -v cmp >/dev/null || fail 'cmp is unavailable'
command -v id >/dev/null || fail 'id is unavailable'
command -v install >/dev/null || fail 'install is unavailable'
command -v ln >/dev/null || fail 'ln is unavailable'
command -v mktemp >/dev/null || fail 'mktemp is unavailable'
command -v pkg-config >/dev/null || fail 'pkg-config is unavailable'
command -v sha256sum >/dev/null || fail 'sha256sum is unavailable'
command -v stat >/dev/null || fail 'stat is unavailable'
output_parent=$(dirname -- "$output")
output_name=$(basename -- "$output")
case $output_name in ''|.|..) fail 'output name is invalid' ;; esac
[ -d "$output_parent" ] && [ ! -L "$output_parent" ] ||
	fail 'output parent is absent or linked'
output_parent_canonical=$(CDPATH='' cd -- "$output_parent" && pwd -P)
[ "$output" = "$output_parent_canonical/$output_name" ] ||
	fail 'output path is not canonical'
exec 7<"$output_parent_canonical" ||
	fail 'cannot pin output parent'
current_uid=$(id -u)
parent_uid=$(stat -Lc %u /proc/self/fd/7)
parent_mode=$(stat -Lc %a /proc/self/fd/7)
case $parent_mode in *[!0-7]*|'') fail 'output parent mode is invalid' ;; esac
parent_permissions=$((0$parent_mode))
[ "$parent_uid" = "$current_uid" ] ||
	fail 'output parent is not owned by the caller'
[ $((parent_permissions & 022)) -eq 0 ] ||
	fail 'output parent is group- or world-writable'
parent_identity=$(stat -Lc '%d:%i' /proc/self/fd/7)
[ "$(stat -Lc '%d:%i' -- "$output_parent_canonical")" = "$parent_identity" ] ||
	fail 'output parent identity changed'
output_anchor=/proc/self/fd/7/$output_name

[ -f "$source_file" ] && [ ! -L "$source_file" ] ||
	fail 'Vulkan submit source is absent or linked'
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
export TZ=UTC
export SOURCE_DATE_EPOCH=1681862400
pkg-config --exists vulkan || fail 'Vulkan development package is unavailable'
vulkan_cflags=$(pkg-config --cflags vulkan) ||
	fail 'cannot resolve Vulkan compiler flags'
vulkan_libraries=$(pkg-config --libs vulkan) ||
	fail 'cannot resolve Vulkan linker flags'
set -f

build_one() {
	target=$1
	# pkg-config output is word-split without evaluation; pathname globbing is
	# disabled above.
	# shellcheck disable=SC2086
	"$compiler" \
		-std=c11 -O2 -fPIE -pie -fstack-protector-strong \
		-Wall -Wextra -Werror \
		-Wl,-z,relro,-z,now,-z,noexecstack,--build-id=none \
		$vulkan_cflags "$source_file" -o "$target" $vulkan_libraries
}

build_one "$build_root/first"
build_one "$build_root/second"
cmp "$build_root/first" "$build_root/second" ||
	fail 'two clean helper builds differ'
output_stage=$(mktemp "/proc/self/fd/7/.rog5-vulkan-submit.XXXXXX")
install -m 0755 "$build_root/first" "$output_stage"
ln "$output_stage" "$output_anchor" 2>/dev/null ||
	fail 'output appeared during build'
exec 8<"$output_anchor" ||
	fail 'cannot pin published output'
published_identity=$(stat -Lc '%d:%i' /proc/self/fd/8)
[ "$(stat -Lc '%d:%i' -- "$output_stage")" = "$published_identity" ] ||
	fail 'published output identity changed'
rm -f -- "$output_stage"
output_stage=

[ "$(stat -Lc '%d:%i' -- "$output_anchor")" = "$published_identity" ] ||
	fail 'published output path changed'
size=$(stat -Lc %s /proc/self/fd/8)
digest=$(sha256sum /proc/self/fd/8 | cut -d ' ' -f 1)
[ "$(stat -Lc '%d:%i' -- "$output_anchor")" = "$published_identity" ] ||
	fail 'published output path changed'
printf 'format=rog5-vulkan-submit-build-v1\n'
printf 'size=%s\n' "$size"
printf 'sha256=%s\n' "$digest"
