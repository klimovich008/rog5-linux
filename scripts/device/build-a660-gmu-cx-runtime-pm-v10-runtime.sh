#!/bin/sh
set -eu

baseline_out=${1:?usage: build-a660-gmu-cx-runtime-pm-v10-runtime.sh BASELINE_OUT PROBE_OUT}
probe_out=${2:?missing probe output}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
v9_builder=$repo/scripts/device/build-a660-gmu-resume-entry-v9-runtime.sh
v9_verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-v9-runtime-sources.sh
v9_report=$repo/test-results/2026-07-27-a660-gmu-resume-entry-v9-live-accepted.md
v9_consumed=$repo/scripts/host/test-consume-a660-gmu-resume-entry-v9.sh
offline_report=$repo/test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-offline.md
kernel_patch=$repo/patches/linux-7.1.4/0016-drm-msm-add-a660-gmu-cx-runtime-pm-diagnostic.patch
trace_oracle=$repo/scripts/device/check-a660-gmu-cx-runtime-pm-v10-trace.sh
trace_oracle_test=$repo/scripts/device/test-a660-gmu-cx-runtime-pm-v10-trace-oracle.sh
baseline_patch=$repo/patches/runtime/a660-gmu-cx-runtime-pm-v10-baseline.patch
probe_patch=$repo/patches/runtime/a660-gmu-cx-runtime-pm-v10-probe.patch

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

check_hash "$v9_builder" \
	da8b18e6c995bbc2b7402b7be6d38577911c2258c2b131304865ab55ada0cafb \
	'immutable accepted-and-consumed v9 runtime builder'
check_hash "$v9_verifier" \
	9e3f39e60d5edb06ea50ff2673bd818029274960af0e95c84f3e438a3d1c5ef1 \
	'immutable v9 runtime verifier'
check_hash "$v9_report" \
	57af6b4d0ddf6faaa708e7b409197dcf7aa8fcdb52a5a9612b59094aebc9dd2c \
	'accepted v9 live report'
check_hash "$v9_consumed" \
	e876ff87452aa02e60f3135801a3f6d2da0042c680fd14bf0ae7319e9adc4a7f \
	'permanent v9 consumption test'
check_hash "$offline_report" \
	9ae66678340437c4a38b2d6ee390cc375e661548be97cb108bb8f891a418dee4 \
	'accepted v10 offline report'
check_hash "$kernel_patch" \
	5eef04eb711443acaaf4295e926577f90073b8ab62414cff3d18de2272d3a152 \
	'accepted v10 kernel patch'
check_hash "$trace_oracle" \
	33ccadc6ae1e5f6f12ed83de0ddc192d30d204e229ec1b97aa813e1d0ac9c7e6 \
	'exact GMU/linked-CX v10 trace oracle'
check_hash "$trace_oracle_test" \
	ca942002debee58a0437218ba4b49410c2a50d7a5d93a9d6872890a8c565f915 \
	'v10 trace-oracle mutation test'
check_hash "$baseline_patch" \
	5732f9b170aa133d00a2eafd7b2fab2c262c1e98765ba05c8a848e3e5b85f674 \
	'v10 baseline patch'
check_hash "$probe_patch" \
	e8ab58ac1efab6441500532574f34b8fe55734b6c0816b3cc28fc977eb9547e4 \
	'v10 probe patch'
"$v9_consumed" >/dev/null
"$trace_oracle_test" >/dev/null

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
"$v9_builder" "$work/baseline-v9" "$work/probe-v9" >/dev/null
"$v9_verifier" "$work/baseline-v9" "$work/probe-v9" >/dev/null
check_hash "$work/baseline-v9" \
	337535cda800963bc1887203d1f60d9340b8fc5e9956f652a75bf26ada5d4ecc \
	'generated accepted-and-consumed v9 baseline'
check_hash "$work/probe-v9" \
	078bb4cb2e6e1edac0182a22023121f2f6fbef2ec02715b7f3f6a5fe9338f387 \
	'generated accepted-and-consumed v9 probe'
[ "$(grep -o v9 "$work/baseline-v9" | wc -l)" -eq 11 ] ||
	fail 'v9 baseline version-token count changed'
[ "$(grep -o v9 "$work/probe-v9" | wc -l)" -eq 206 ] ||
	fail 'v9 probe version-token count changed'

transform() {
	sed \
		-e 's/a660-gmu-resume-entry-v9/a660-gmu-cx-runtime-pm-v10/g' \
		-e 's/A660 GMU resume-entry v9/A660 GMU\/CX runtime-PM v10/g' \
		-e 's/GMU resume-entry v9/GMU\/CX runtime-PM v10/g' \
		-e 's/rog5_gmu_v9/rog5_gmu_v10/g' \
		-e 's/ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9/ALLOW_MAINLINE_A660_GMU_CX_RUNTIME_PM_V10/g' \
		-e 's/diagnostic_generation=v9/diagnostic_generation=v10/g' \
		"$1"
}
transform "$work/baseline-v9" >"$baseline_out"
transform "$work/probe-v9" >"$probe_out"
[ "$(grep -o v10 "$baseline_out" | wc -l)" -eq 8 ] ||
	fail 'v10 baseline transformed-token count changed'
[ "$(grep -o v10 "$probe_out" | wc -l)" -eq 204 ] ||
	fail 'v10 probe transformed-token count changed'

patch --batch --fuzz=0 --no-backup-if-mismatch \
	"$baseline_out" "$baseline_patch" >/dev/null ||
	fail 'v10 baseline patch did not apply exactly'
patch --batch --fuzz=0 --no-backup-if-mismatch \
	"$probe_out" "$probe_patch" >/dev/null ||
	fail 'v10 probe patch did not apply exactly'
chmod 0755 "$baseline_out" "$probe_out"
sh -n "$baseline_out"
sh -n "$probe_out"

check_hash "$baseline_out" \
	a68960aa1ac84dbc6f3b469d8369d1c66dcd343f9adfc0a9f4e9909e9ee4245d \
	'generated v10 baseline'
check_hash "$probe_out" \
	f28b1c28ec43da21747ce7e17247d33074bfa01f7c9c6171e80806a98eb70b36 \
	'generated v10 probe'
if grep -Fq 'ALLOW_MAINLINE_A660_GMU_RESUME_ENTRY_V9' "$probe_out"; then
	fail 'v10 probe inherited v9 live authorization'
fi

echo 'PASS built exact A660 GMU/CX runtime-PM v10 runtime from immutable accepted-and-consumed v9 controls; kernel/module delta=v10-msm-only, exact GMU/CX PM and zero-GX trace oracle added'
