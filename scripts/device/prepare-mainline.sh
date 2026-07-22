#!/bin/sh
set -eu

source_dir=${1:-/root/src/linux-7.1.4}
repository=${LINUX_REPOSITORY:-https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git}
tag=${LINUX_TAG:-v7.1.4}
expected_commit=${LINUX_COMMIT:-7a5cef0db4795d9d453a12e0f61b5b7634fc4d40}

mkdir -p "$(dirname "$source_dir")"
if [ ! -d "$source_dir/.git" ]; then
    git init -q "$source_dir"
    git -C "$source_dir" remote add origin "$repository"
fi

[ -z "$(git -C "$source_dir" status --porcelain 2>/dev/null)" ] || {
    echo "ERROR refusing to replace changes in $source_dir" >&2
    exit 1
}

git -C "$source_dir" fetch --depth 1 origin "refs/tags/$tag"
git -C "$source_dir" checkout -B rog5-build FETCH_HEAD
actual_commit=$(git -C "$source_dir" rev-parse HEAD)
[ "$actual_commit" = "$expected_commit" ] || {
    echo "ERROR $tag resolved to unexpected commit $actual_commit" >&2
    exit 1
}

printf 'PASS source_tag=%s commit=%s\n' "$tag" "$actual_commit"
