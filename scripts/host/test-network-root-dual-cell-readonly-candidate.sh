#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
preparer=$repo/scripts/device/prepare-mainline-dual-cell-readonly-source.sh
base_verifier=$repo/scripts/device/verify-mainline-network-root-build.sh
candidate_verifier=$repo/scripts/device/verify-mainline-network-root-dual-cell-readonly-build.sh
builder=$repo/scripts/host/build-network-root-dual-cell-readonly-candidate-offline.sh
source_root=$repo/build/linux-stable-v7.1.4-source
work=$(mktemp -d)
lock_probe=$repo/build/.dual-cell-release-lock-test-$$
cleanup() {
	find "$work" -depth -delete
	if [[ -e $lock_probe || -L $lock_probe ]]; then
		find "$lock_probe" -depth -delete
	fi
	if [[ -e $lock_probe.lock || -L $lock_probe.lock ]]; then
		find "$lock_probe.lock" -depth -delete
	fi
}
trap cleanup EXIT HUP INT TERM

for path in "$preparer" "$base_verifier" "$candidate_verifier" "$builder"; do
	[[ -f $path && ! -L $path && -x $path ]] ||
		fail "missing executable dual-cell release contract: ${path#"$repo"/}"
	bash -n "$path"
done

for token in \
	7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 \
	2ea2be38c5e4dc9aafffbbc0db5aae0f6513a1d9 \
	7ee91d34b5458efa0ac45d979bab82bbd2cb7ea5 \
	ef7703ecc0aad3d625cfbbef296e586d861deefe \
	7.1.4-00001-g7ee91d34b545 \
	0018-power-supply-qcom-battmgr-add-rog5-cell-voltage.patch \
	verify-qcom-battmgr-asus-cell-voltage-patch.sh \
	'git clone -q --shared --no-checkout' \
	'GIT_AUTHOR_DATE=' \
	'2026-08-09T12:00:00Z' \
	'power: supply: qcom_battmgr: add read-only ROG5 cell voltages' \
	'write-tree' \
	'setlocalversion --no-local'; do
	grep -Fq -- "$token" "$preparer" ||
		fail "dual-cell source preparer omits exact input: $token"
done

for token in \
	'dual-cell-readonly)' \
	7ee91d34b5458efa0ac45d979bab82bbd2cb7ea5 \
	7.1.4-00001-g7ee91d34b545; do
	grep -Fq -- "$token" "$base_verifier" ||
		fail "base verifier omits closed candidate profile: $token"
done

for token in \
	'verify-mainline-network-root-build.sh' \
	'dual-cell-readonly' \
	ef7703ecc0aad3d625cfbbef296e586d861deefe \
	'qcom_battmgr.ko' \
	'cell_voltages' \
	'asus,cell-voltage-readonly' \
	'authority=none' \
	'hardware_acceptance=unproven'; do
	grep -Fq -- "$token" "$candidate_verifier" ||
		fail "dual-cell build verifier omits exact gate: $token"
done

for token in \
	'bootstrap-kernel-builder.sh' \
	'localhost/rog5-kernel-builder:ubuntu-24.04' \
	'bdb4bbda79ab38a55c72d23b269f5c3f5cb14d153e373ce50932c17538e9ccaf' \
	'prepare-mainline-dual-cell-readonly-source.sh' \
	'build-mainline-network-root.sh' \
	'verify-mainline-network-root-dual-cell-readonly-build.sh' \
	'compare-mainline-network-root-builds.sh' \
	'build-dual-cell-readonly-candidate-dtb.sh' \
	'verify-dual-cell-readonly-dtb-delta.py' \
	'expected_telemetry_sha=3f4305d7fbbd2c74d15c1011bb8a2e8e24b3a5228f31ed86281917d16cf18f11' \
	'fdtoverlay -i "$base_dtb" -o "$output"' \
	'chmod 0644 -- "$candidate"/*' \
	'INCREMENTAL_BUILD=0' \
	'KBUILD_CCACHE=0' \
	'jobs=8' \
	'cmp -- "$stage/source-a.txt" "$stage/source-b.txt"' \
	'cmp -- "$stage/manifest-a.txt" "$stage/manifest-b.txt"' \
	'mkdir -- "$lock_dir"' \
	'refusing existing dual-cell candidate output root' \
	'authority=none' \
	'boot_authority=none' \
	'hardware_acceptance=unproven' \
	'find "$stage/source-a" -depth -delete' \
	'find "$stage/build-a" -depth -delete'; do
	grep -Fq -- "$token" "$builder" ||
		fail "dual-cell twin builder omits release contract: $token"
done
if grep -Fq 'build-battery-telemetry-candidate-dtb.sh' "$builder"; then
	fail 'dual-cell release still calls the obsolete power-key telemetry builder'
fi
if grep -Eq 'RESUME_EXACT_TWINS|exact-twin resume|elapsed_file_ms' "$builder"; then
	fail 'dual-cell release can publish without two fresh clean build invocations'
fi

if grep -Eq '\b(fastboot|adb|sudo|pkexec)\b|/dev/(sd|nvme|ufs)|git (push|fetch)|gh ' \
	"$preparer" "$candidate_verifier" "$builder"; then
	fail 'dual-cell release path contains phone, privilege, credential, or publication transport'
fi

mkdir -- "$lock_probe.lock"
if "$builder" "$work/missing-source" "$lock_probe" \
	>"$work/lock.out" 2>"$work/lock.err"; then
	fail 'candidate builder ignored a concurrent output lock'
fi
grep -Fq 'another dual-cell candidate build owns the output lock' \
	"$work/lock.err"
[[ ! -e $lock_probe ]]
find "$lock_probe.lock" -depth -delete

[[ -d $source_root/.git ]] || {
	echo 'PASS dual-cell clean-twin candidate contract (retained source materialization is optional in CI)'
	exit 0
}
[[ $(git -C "$source_root" rev-parse HEAD) == \
	7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 ]] ||
	fail 'retained source HEAD changed'
[[ -z $(git -C "$source_root" status --porcelain) ]] ||
	fail 'retained source is dirty'

case ${ROG5_FULL_DUAL_CELL_SOURCE_TEST:-0} in
	0)
		echo 'PASS dual-cell clean-twin candidate contract (full source materialization is exercised by candidate issuance)'
		exit 0
		;;
	1) ;;
	*) fail 'ROG5_FULL_DUAL_CELL_SOURCE_TEST must be 0 or 1' ;;
esac

"$preparer" "$source_root" "$work/source-a" >"$work/source-a.txt"
"$preparer" "$source_root" "$work/source-b" >"$work/source-b.txt"
cmp -- "$work/source-a.txt" "$work/source-b.txt"
for source in "$work/source-a" "$work/source-b"; do
	[[ $(git -C "$source" rev-parse HEAD) == \
		7ee91d34b5458efa0ac45d979bab82bbd2cb7ea5 ]]
	[[ $(git -C "$source" rev-parse 'HEAD^{tree}') == \
		ef7703ecc0aad3d625cfbbef296e586d861deefe ]]
	[[ -z $(git -C "$source" status --porcelain) ]]
done

if "$preparer" "$source_root" "$work/source-a" \
	>"$work/reuse.out" 2>"$work/reuse.err"; then
	fail 'source preparer replaced an existing candidate source'
fi
grep -Fq 'target source path already exists' "$work/reuse.err"

git clone -q --shared --no-checkout "$source_root" "$work/dirty-base"
printf '%s\n' hostile >"$work/dirty-base/untracked-hostile"
if "$preparer" "$work/dirty-base" "$work/from-dirty" \
	>"$work/dirty.out" 2>"$work/dirty.err"; then
	fail 'source preparer accepted a dirty base source'
fi
grep -Fq 'base Linux source is dirty' "$work/dirty.err"
[[ ! -e $work/from-dirty ]]

echo 'PASS deterministic dual-cell source and clean-twin offline candidate contract'
