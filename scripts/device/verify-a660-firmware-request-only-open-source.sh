#!/bin/sh
set -eu

source_file=${1:?usage: verify-a660-firmware-request-only-open-source.sh SOURCE}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
accepted=$repo/tools/diagnostics/a660-firmware-request-only-open.c
expected_hash=68f7dbb0669b2b386fba2434c58aeb039917ba1ca229479c53a1d729f124f3ef

fail() {
	echo "FAIL $*" >&2
	exit 1
}

line_once() {
	text=$1
	needle=$2
	label=$3
	stats=$(printf '%s\n' "$text" |
		awk -v needle="$needle" '
			index($0, needle) { count++; line = NR }
			END { print count + 0 ":" line + 0 }
		')
	count=${stats%%:*}
	line=${stats#*:}
	[ "$count" -eq 1 ] ||
		fail "$label count is $count, expected 1"
	printf '%s\n' "$line"
}

for command in awk cut grep sed sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing command: $command"
done
[ -f "$source_file" ] && [ ! -L "$source_file" ] &&
	[ -r "$source_file" ] ||
	fail 'helper source is missing, linked, or unreadable'

if [ "${ALLOW_UNPINNED_A660_OPEN_SOURCE:-0}" != 1 ]; then
	[ "$source_file" = "$accepted" ] ||
		fail 'helper source path is not accepted'
	[ "$(sha256sum "$source_file" | cut -d ' ' -f 1)" = \
		"$expected_hash" ] ||
		fail 'helper source hash mismatch'
fi

for exact in \
	'SYS_OPENAT = 56,' \
	'SYS_WRITE = 64,' \
	'SYS_EXIT = 93,' \
	'AT_FDCWD = -100,' \
	'O_RDWR = 2,' \
	'O_CLOEXEC = 0x80000,' \
	'EUCLEAN = 117,' \
	'static const char render_node[] = "/dev/dri/renderD128";' \
	'static const char expected[] = "OPEN_ERRNO=117\n";' \
	'result = syscall4(SYS_OPENAT, AT_FDCWD, (long)render_node,' \
	'if (error == EUCLEAN) {' \
	'exit_with(EUCLEAN);'
do
	[ "$(grep -Fc "$exact" "$source_file")" -eq 1 ] ||
		fail "helper source contract is not exact: $exact"
done

start=$(sed -n '/^void _start(void)$/,/^}$/p' "$source_file")
[ -n "$start" ] || fail 'helper _start body is absent'
open_line=$(line_once "$start" \
	'result = syscall4(SYS_OPENAT, AT_FDCWD, (long)render_node,' \
	'openat invocation')
error_line=$(line_once "$start" 'error = -result;' 'raw errno capture')
expected_line=$(line_once "$start" 'if (error == EUCLEAN) {' \
	'EUCLEAN branch')
exit_line=$(line_once "$start" 'exit_with(EUCLEAN);' 'EUCLEAN exit')
[ "$open_line" -lt "$error_line" ] &&
	[ "$error_line" -lt "$expected_line" ] &&
	[ "$expected_line" -lt "$exit_line" ] ||
	fail 'one-open errno-check order changed'

[ "$(grep -Fc 'syscall4(SYS_OPENAT' "$source_file")" -eq 1 ] ||
	fail 'helper does not contain exactly one openat invocation'
[ "$(grep -Fc '"/dev/dri/' "$source_file")" -eq 1 ] ||
	fail 'helper contains more than one DRM path'
if printf '%s\n' "$start" |
	grep -Eq \
		'(^|[[:space:]])(for|while)[[:space:]]*\(|(^|[[:space:]])goto[[:space:]]'
then
	fail 'helper gained retry or control-flow loop'
fi
if grep -Eq '/dev/(block|disk|mapper|mmc|sd[a-z]|ufs)|fastboot|adb|mount' \
	"$source_file"
then
	fail 'helper source contains a storage or device-control path'
fi

echo 'PASS A660 open helper is freestanding, exact-render-node, one-open, no-retry, and EUCLEAN-reporting'
