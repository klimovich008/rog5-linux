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
	'expected_source_sha256=93d09cca8ad8dc573b1aa25c2fba5cc027d1ba901adb6c9e2643f97287387f9a' \
	'expected_output_size=67288' \
	'expected_output_sha256=26249252916cf0f2cfba1547a845ef15caa07f6abc77c5149f1662f0a168bafa' \
	'[ "$(uname -m)" = aarch64 ]' \
	'[ "$(cc -dumpfullversion)" = 15.2.0 ]' \
	'-static -fPIE -pie -fstack-protector-strong' \
	'-z,noexecstack,--build-id=none' \
	'ROG5_DIAG_TEST_' \
	'host-port-timeout' \
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
	'for fault in host-port-probe-failed host-port-unreachable host-port-timeout' \
	'cmp "$work/native-frame" "$work/oracle-frame"'; do
	grep -Fq -- "$token" "$host_gate" || {
		echo "FAIL AArch64 reporter gate contract missing: $token" >&2
		exit 1
	}
done

echo 'PASS early-target reporter builder is sealed, static, reproducible, and oracle-checked'
