#!/bin/sh
set -eu

base_source=${1:?usage: prepare-mainline-discovery.sh BASE_SOURCE TARGET_SOURCE}
target_source=${2:?missing target source}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch_dir=$repo/patches/linux-7.1.4
expected_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_patched=cfd385a1c754684dd28b63a4559e04baa5e902b1
expected_tree=d2f03d2055227b8b72ab41be949847a066924c5a

[ -d "$base_source/.git" ] || { echo 'FAIL missing pinned Linux source' >&2; exit 1; }
[ "$(git -C "$base_source" rev-parse HEAD)" = "$expected_commit" ]
[ -z "$(git -C "$base_source" status --porcelain)" ]
[ ! -e "$target_source" ] || {
	echo 'FAIL target source path already exists' >&2
	exit 1
}

patches=$(find "$patch_dir" -maxdepth 1 -type f -name '*.patch' -print | sort)
[ "$(printf '%s\n' "$patches" | awk 'NF { count++ } END { print count + 0 }')" -eq 3 ]

mkdir -p "$(dirname "$target_source")"
git clone -q --no-hardlinks "$base_source" "$target_source"
git -C "$target_source" checkout -q --detach "$expected_commit"
for patch in $patches; do
	git -C "$target_source" apply --check "$patch"
	git -C "$target_source" apply "$patch"
done
git -C "$target_source" diff --check

git -C "$target_source" add \
	drivers/scsi/sd.c \
	drivers/ufs/core/Kconfig \
	drivers/ufs/core/ufshcd.c
[ "$(git -C "$target_source" write-tree)" = "$expected_tree" ] || {
	echo 'FAIL patched source tree hash mismatch' >&2
	exit 1
}

export GIT_AUTHOR_NAME='ROG5 Linux Project'
export GIT_AUTHOR_EMAIL='rog5-linux@localhost'
export GIT_COMMITTER_NAME=$GIT_AUTHOR_NAME
export GIT_COMMITTER_EMAIL=$GIT_AUTHOR_EMAIL
export GIT_AUTHOR_DATE='2026-07-24T00:00:00Z'
export GIT_COMMITTER_DATE=$GIT_AUTHOR_DATE
git -C "$target_source" commit -q -m 'ufs: add read-only discovery mode'

[ "$(git -C "$target_source" rev-parse HEAD^)" = "$expected_commit" ]
[ "$(git -C "$target_source" rev-parse HEAD)" = "$expected_patched" ]
[ "$(git -C "$target_source" rev-parse HEAD^{tree})" = "$expected_tree" ]
[ -z "$(git -C "$target_source" status --porcelain)" ]

printf 'base_commit=%s\n' "$expected_commit"
printf 'patched_commit=%s\n' "$(git -C "$target_source" rev-parse HEAD)"
printf 'patched_tree=%s\n' "$expected_tree"
sha256sum $patches
echo 'PASS deterministic patched Linux 7.1.4 discovery source'
