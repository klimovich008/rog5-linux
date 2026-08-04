#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
builder=$repo/scripts/device/build-early-target-diag.sh
source_file=$repo/tools/early_target_diag/rog5-early-target-diag.c
host_gate=$repo/scripts/host/test-early-target-diag-aarch64.sh

for path in "$builder" "$source_file" "$host_gate"; do
	[ -f "$path" ] && [ ! -L "$path" ] || {
		echo "FAIL missing or linked reporter build source: $path" >&2
		exit 1
	}
done
sh -n "$builder"
bash -n "$host_gate"

for token in \
	'expected_source_sha256=2f8a3bc21a43b415f08a341d01179603401842df25da0b3ce17a67f5cdbd8a65' \
	'expected_output_size=67288' \
	'expected_output_sha256=dc53932d6275180fa71972ceed0ae409bd4ae1604fca8befd9f030d476583a10' \
	'[ "$(uname -m)" = aarch64 ]' \
	'[ "$(cc -dumpfullversion)" = 15.2.0 ]' \
	'-static -fPIE -pie -fstack-protector-strong' \
	'-z,noexecstack,--build-id=none' \
	'ROG5_DIAG_TEST_' \
	'/dev/ttyGS0'; do
	grep -Fq -- "$token" "$builder" || {
		echo "FAIL reporter builder contract missing: $token" >&2
		exit 1
	}
done
for token in \
	'--network=none' \
	'--pull=never' \
	'run-private-arm64-binfmt.sh' \
	'cmp "$work/reporter-a" "$work/reporter-b"' \
	'"$runner" "$work/reporter-a" frame' \
	'cmp "$work/native-frame" "$work/oracle-frame"'; do
	grep -Fq -- "$token" "$host_gate" || {
		echo "FAIL AArch64 reporter gate contract missing: $token" >&2
		exit 1
	}
done

echo 'PASS early-target reporter builder is sealed, static, reproducible, and oracle-checked'
