#!/bin/sh
set -eu

baseline_out=${1:?usage: build-a660-gmu-resume-entry-v8-runtime.sh BASELINE_OUT PROBE_OUT}
probe_out=${2:?missing probe output}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
v7_builder=$repo/scripts/device/build-a660-ucode-allocation-v7-runtime.sh
patch_verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-patch.sh
relocation_verifier=$repo/scripts/device/verify-a660-gmu-resume-entry-vmap-relocations.sh
live_report=$repo/test-results/2026-07-26-a660-ucode-allocation-v7-live-accepted.md
boundary_report=$repo/test-results/2026-07-26-a660-gmu-resume-entry-boundary.md
build_report=$repo/test-results/2026-07-26-a660-gmu-resume-entry-v8-offline.md
kernel_patch=$repo/patches/linux-7.1.4/0015-drm-msm-add-a660-gmu-resume-entry-diagnostic.patch
baseline_patch=$repo/patches/runtime/a660-gmu-resume-entry-v8-baseline.patch
probe_patch=$repo/patches/runtime/a660-gmu-resume-entry-v8-probe.patch

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

for command in chmod cp cut dirname mktemp patch rm sha256sum; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done
[ "$baseline_out" != "$probe_out" ] ||
	fail 'baseline and probe output paths alias'
[ -d "$(dirname "$baseline_out")" ] && [ -d "$(dirname "$probe_out")" ] ||
	fail 'output parent directory is absent'
[ ! -e "$baseline_out" ] && [ ! -e "$probe_out" ] ||
	fail 'runtime output already exists'

check_hash "$v7_builder" \
	ac4412f6710b1c6bb1d6f87bb6850157aa136a55301db84884843784bae6bf7c \
	'immutable accepted v7 runtime builder'
check_hash "$patch_verifier" \
	a380016efd29dd23d6037b2dbbfefef1fb9687860a63355d3a09e3477bbd7c49 \
	'verify-a660-gmu-resume-entry-patch.sh'
check_hash "$relocation_verifier" \
	e602f61702093050f5faba7a28c8efe54f50bf74a68369aa6096c94427389bf1 \
	'v8 compiler-relocation verifier'
check_hash "$live_report" \
	ea4a4a87a264728be3bfcd86a2f12888496dd51c7421cbee166ad19afdb5ee6a \
	'accepted and consumed v7 live report'
check_hash "$boundary_report" \
	41c06dcd895fcc873638ddf40dce0b0d5dd5bbf9e148f5d3abd5521b072c320d \
	'GMU resume-entry source boundary report'
check_hash "$build_report" \
	6c50a822d30368bba4564daa77633b6e22ae1e167cd3486670b786e430153b7c \
	'reproducible v8 kernel build report'
check_hash "$kernel_patch" \
	a179ff9e31792238a3bd254297008d805e6a37b5d08125712c0151b1f39b3051 \
	'accepted GMU resume-entry kernel patch'
check_hash "$baseline_patch" \
	fe3355d5dcb8a4f16b15ac5a3554b00ab8c5477d619eb7466edcdb0b2cf95e2d \
	'v8 baseline patch'
check_hash "$probe_patch" \
	fa6f8d984595fa4fb399404108b431b14e299287357cf98a6aef30ec67f2aece \
	'v8 probe patch'
"$relocation_verifier" >/dev/null

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
"$v7_builder" "$work/baseline-v7" "$work/probe-v7" >/dev/null
check_hash "$work/baseline-v7" \
	d8c2d697d20c213f3528d6a4cf99ca7d0243bf83222a34ff6f665ab22fc27386 \
	'generated accepted v7 baseline'
check_hash "$work/probe-v7" \
	01a681bdf9fc17b3c676797cafadc43338eee49f2a5e3b7c6789edc1c7056cf0 \
	'generated accepted v7 probe'

cp "$work/baseline-v7" "$baseline_out"
cp "$work/probe-v7" "$probe_out"
patch --batch --fuzz=0 --no-backup-if-mismatch \
	"$baseline_out" "$baseline_patch" >/dev/null ||
	fail 'v8 baseline patch did not apply exactly'
patch --batch --fuzz=0 --no-backup-if-mismatch \
	"$probe_out" "$probe_patch" >/dev/null ||
	fail 'v8 probe patch did not apply exactly'
chmod 0755 "$baseline_out" "$probe_out"
sh -n "$baseline_out"
sh -n "$probe_out"

check_hash "$baseline_out" \
	3a4bcdcd9a96b896f22fda3be3f73c68a3b16e5d154558da9ad299c969faaf23 \
	'generated v8 baseline'
check_hash "$probe_out" \
	832a96db228a9f0771c0ff364ed943100f243fbbce51ec4c0e2532e211a9e255 \
	'generated v8 probe'

echo 'PASS built exact A660 GMU resume-entry v8 runtime from immutable accepted v7 evidence plus two pinned zero-fuzz patches; v8 retained accepted v7 allocation and rollback state'
