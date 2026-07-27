#!/bin/sh
set -eu

baseline_out=${1:?usage: build-a660-gmu-resume-entry-v9-runtime.sh BASELINE_OUT PROBE_OUT}
probe_out=${2:?missing probe output}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
v8_builder=$repo/scripts/device/build-a660-gmu-resume-entry-v8-runtime.sh
v8_report=$repo/test-results/2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md
v8_consumed=$repo/scripts/host/test-consume-a660-gmu-resume-entry-v8.sh
trace_oracle=$repo/scripts/device/check-a660-gmu-resume-entry-v9-trace.sh
trace_oracle_test=$repo/scripts/device/test-a660-gmu-resume-entry-v9-trace-oracle.sh
baseline_patch=$repo/patches/runtime/a660-gmu-resume-entry-v9-baseline.patch
probe_patch=$repo/patches/runtime/a660-gmu-resume-entry-v9-probe.patch

fail() {
	echo "FAIL $*" >&2
	exit 1
}

check_hash() {
	file=$1
	expected=$2
	label=$3
	[ -f "$file" ] && [ ! -L "$file" ] && [ -r "$file" ] ||
		fail "$label is missing, linked, or unreadable"
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] ||
		fail "$label hash mismatch: expected $expected, got $actual"
}

for command in chmod cut dirname grep mktemp patch rm sed sha256sum wc; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
[ "$baseline_out" != "$probe_out" ] ||
	fail 'baseline and probe output paths alias'
[ -d "$(dirname "$baseline_out")" ] && [ -d "$(dirname "$probe_out")" ] ||
	fail 'output parent directory is absent'
[ ! -e "$baseline_out" ] && [ ! -e "$probe_out" ] ||
	fail 'runtime output already exists'

check_hash "$v8_builder" \
	95cc98935677617ddf504701858b4a068a25b71a9a9853735a26c7e590cb5a9d \
	'immutable rejected-and-consumed v8 runtime builder'
check_hash "$v8_report" \
	fe5a6130cce3063ef6a0b1093d492d2a35763781f23af029c2959548cb092a9c \
	'v8 safe live-rejection report'
check_hash "$v8_consumed" \
	efbea8d09ecf81be8df32a0aaaffc55ecdd65209ef7fc1e1d71945a7d38180ec \
	'permanent v8 consumption test'
check_hash "$trace_oracle" \
	48325037a54fe737aa4c623a1be59f644952bd21d9f13f0bba6a6563fea6f223 \
	'signed device-scoped v9 trace oracle'
check_hash "$trace_oracle_test" \
	911d0cab1a0d312c4a217953e87189c3bfbcbd8b9fe32707019a8d112ddaf82c \
	'v9 trace-oracle mutation test'
check_hash "$baseline_patch" \
	f5c996be5cccc8de45e87591ff1411ad1e6820c233bdcaadf078ecc76a0b0608 \
	'v9 baseline patch'
check_hash "$probe_patch" \
	83b1df2cd462a6ea16e5471888a8bad11b343861d441758995a5a059929be04c \
	'v9 probe patch'
"$v8_consumed" >/dev/null
"$trace_oracle_test" >/dev/null

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
"$v8_builder" "$work/baseline-v8" "$work/probe-v8" >/dev/null
check_hash "$work/baseline-v8" \
	3a4bcdcd9a96b896f22fda3be3f73c68a3b16e5d154558da9ad299c969faaf23 \
	'generated rejected-and-consumed v8 baseline'
check_hash "$work/probe-v8" \
	832a96db228a9f0771c0ff364ed943100f243fbbce51ec4c0e2532e211a9e255 \
	'generated rejected-and-consumed v8 probe'

[ "$(grep -o v8 "$work/baseline-v8" | wc -l)" -eq 9 ] ||
	fail 'v8 baseline version-token count changed'
[ "$(grep -o v8 "$work/probe-v8" | wc -l)" -eq 208 ] ||
	fail 'v8 probe version-token count changed'
sed 's/v8/v9/g' "$work/baseline-v8" >"$baseline_out"
sed 's/v8/v9/g' "$work/probe-v8" >"$probe_out"
if grep -Fq v8 "$baseline_out" || grep -Fq v8 "$probe_out"; then
	fail 'lowercase v8 token survived the version-only transform'
fi

patch --batch --fuzz=0 --no-backup-if-mismatch \
	"$baseline_out" "$baseline_patch" >/dev/null ||
	fail 'v9 baseline patch did not apply exactly'
patch --batch --fuzz=0 --no-backup-if-mismatch \
	"$probe_out" "$probe_patch" >/dev/null ||
	fail 'v9 probe patch did not apply exactly'
chmod 0755 "$baseline_out" "$probe_out"
sh -n "$baseline_out"
sh -n "$probe_out"

check_hash "$baseline_out" \
	337535cda800963bc1887203d1f60d9340b8fc5e9956f652a75bf26ada5d4ecc \
	'generated v9 baseline'
check_hash "$probe_out" \
	078bb4cb2e6e1edac0182a22023121f2f6fbef2ec02715b7f3f6a5fe9338f387 \
	'generated v9 probe'

if grep -Fq 'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V8' "$probe_out"; then
	fail 'v9 probe inherited v8 live authorization'
fi

echo 'PASS built exact A660 GMU resume-entry v9 runtime from immutable rejected-and-consumed v8 controls; kernel/module unchanged, signed-int and GPU-device trace oracles corrected'
