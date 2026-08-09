#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

base_source=${1:?usage: prepare-mainline-dual-cell-readonly-source.sh BASE_SOURCE TARGET_SOURCE}
target_source=${2:?missing target source}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd -P)
patch=$repo/patches/linux-7.1.4/0018-power-supply-qcom-battmgr-add-rog5-cell-voltage.patch
verifier=$repo/scripts/device/verify-qcom-battmgr-asus-cell-voltage-patch.sh
expected_base=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_base_tree=2ea2be38c5e4dc9aafffbbc0db5aae0f6513a1d9
expected_patched=7ee91d34b5458efa0ac45d979bab82bbd2cb7ea5
expected_tree=ef7703ecc0aad3d625cfbbef296e586d861deefe
expected_release=7.1.4-00001-g7ee91d34b545

for input in "$patch" "$verifier"; do
	[ -f "$input" ] && [ ! -L "$input" ] && [ -r "$input" ] ||
		fail "unsafe or missing source input: $input"
done
[ -x "$verifier" ] || fail 'cell-voltage patch verifier is not executable'
[ -d "$base_source/.git" ] && [ ! -L "$base_source" ] ||
	fail 'missing ordinary pinned Linux source'
base_source=$(realpath -e -- "$base_source")
[ "$(git -C "$base_source" rev-parse HEAD)" = "$expected_base" ] &&
	[ "$(git -C "$base_source" rev-parse 'HEAD^{tree}')" = "$expected_base_tree" ] ||
	fail 'base Linux source commit or tree changed'
[ -z "$(git -C "$base_source" status --porcelain --untracked-files=all)" ] ||
	fail 'base Linux source is dirty'
[ ! -e "$target_source" ] && [ ! -L "$target_source" ] ||
	fail 'target source path already exists'
"$verifier" >/dev/null
SOURCE_DIR="$base_source" "$verifier" >/dev/null

mkdir -p -- "$(dirname -- "$target_source")"
git clone -q --shared --no-checkout "$base_source" "$target_source"
git -C "$target_source" -c advice.detachedHead=false \
	checkout -q --detach "$expected_base"
git -C "$target_source" apply --check "$patch"
git -C "$target_source" apply "$patch"
git -C "$target_source" diff --check
git -C "$target_source" add drivers/power/supply/qcom_battmgr.c
[ "$(git -C "$target_source" write-tree)" = "$expected_tree" ] ||
	fail 'patched cell-voltage source tree hash mismatch'

export GIT_AUTHOR_NAME='ROG5 Linux Project'
export GIT_AUTHOR_EMAIL='rog5-linux@localhost'
export GIT_COMMITTER_NAME=$GIT_AUTHOR_NAME
export GIT_COMMITTER_EMAIL=$GIT_AUTHOR_EMAIL
export GIT_AUTHOR_DATE='2026-08-09T12:00:00Z'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE
git -C "$target_source" commit -q \
	-m 'power: supply: qcom_battmgr: add read-only ROG5 cell voltages'

[ "$(git -C "$target_source" rev-parse 'HEAD^')" = "$expected_base" ] &&
	[ "$(git -C "$target_source" rev-parse HEAD)" = "$expected_patched" ] &&
	[ "$(git -C "$target_source" rev-parse 'HEAD^{tree}')" = "$expected_tree" ] ||
	fail 'deterministic cell-voltage source identity changed'
[ -z "$(git -C "$target_source" status --porcelain --untracked-files=all)" ] ||
	fail 'prepared cell-voltage source is dirty'
actual_release=$(
	cd "$target_source"
	KERNELVERSION=7.1.4 ./scripts/setlocalversion --no-local .
)
[ "$actual_release" = "$expected_release" ] ||
	fail "prepared cell-voltage kernel release changed: $actual_release"

printf 'base_commit=%s\n' "$expected_base"
printf 'patched_commit=%s\n' "$expected_patched"
printf 'patched_tree=%s\n' "$expected_tree"
printf 'kernel_release=%s\n' "$expected_release"
printf 'patch_sha256=%s\n' "$(sha256sum "$patch" | cut -d ' ' -f 1)"
echo 'PASS deterministic Linux 7.1.4 read-only dual-cell source'
