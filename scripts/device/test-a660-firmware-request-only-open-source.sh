#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
source_file=$repo/tools/diagnostics/a660-firmware-request-only-open.c
verifier=$repo/scripts/device/verify-a660-firmware-request-only-open-source.sh

[ -x "$verifier" ] || {
	echo 'FAIL missing executable A660 open-helper source verifier' >&2
	exit 1
}
sh -n "$verifier"
"$verifier" "$source_file" >/dev/null

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT INT TERM

expect_rejected() {
	name=$1
	mutated=$2
	if ALLOW_UNPINNED_A660_OPEN_SOURCE=1 \
		"$verifier" "$mutated" >"$work/$name.log" 2>&1
	then
		echo "FAIL open-helper source mutation passed: $name" >&2
		exit 1
	fi
}

sed 's/SYS_OPENAT = 56,/SYS_OPENAT = 57,/' "$source_file" \
	>"$work/wrong-syscall.c"
expect_rejected wrong-syscall "$work/wrong-syscall.c"

sed 's#/dev/dri/renderD128#/dev/dri/renderD129#' "$source_file" \
	>"$work/wrong-node.c"
expect_rejected wrong-node "$work/wrong-node.c"

sed 's/EUCLEAN = 117,/EUCLEAN = 116,/' "$source_file" \
	>"$work/wrong-errno.c"
expect_rejected wrong-errno "$work/wrong-errno.c"

sed 's/OPEN_ERRNO=117/OPEN_ERRNO=116/' "$source_file" \
	>"$work/wrong-output.c"
expect_rejected wrong-output "$work/wrong-output.c"

sed '/result = syscall4(SYS_OPENAT/a\
	result = syscall4(SYS_OPENAT, AT_FDCWD, (long)render_node, O_RDWR, 0);' \
	"$source_file" >"$work/second-open.c"
expect_rejected second-open "$work/second-open.c"

sed '/long error;/a\
	while (1) { }' "$source_file" >"$work/retry-loop.c"
expect_rejected retry-loop "$work/retry-loop.c"

echo 'PASS A660 open-helper source rejects wrong syscall, node, errno, output, second open, and retry loop'
