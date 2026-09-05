#!/bin/sh
set -eu

source_dir=${1:-/root/src/linux-7.1.4}
repository=${LINUX_REPOSITORY:-https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git}
tag=${LINUX_TAG:-v7.1.4}
expected_tag_object=${LINUX_TAG_OBJECT:-114456a9c542d933387517bb22561668c25a5b59}
expected_commit=${LINUX_COMMIT:-7a5cef0db4795d9d453a12e0f61b5b7634fc4d40}
expected_tree=${LINUX_TREE:-2ea2be38c5e4dc9aafffbbc0db5aae0f6513a1d9}

mkdir -p "$(dirname "$source_dir")"
if [ ! -d "$source_dir/.git" ]; then
    git init -q "$source_dir"
    git -C "$source_dir" remote add origin "$repository"
fi
actual_repository=$(git -C "$source_dir" remote get-url origin 2>/dev/null) || {
    echo "ERROR missing source remote in $source_dir" >&2
    exit 1
}
[ "$actual_repository" = "$repository" ] || {
    echo "ERROR source remote is $actual_repository, expected $repository" >&2
    exit 1
}

source_status=$(git -C "$source_dir" status --porcelain) || {
    echo "ERROR cannot inspect source status in $source_dir" >&2
    exit 1
}
[ -z "$source_status" ] || {
    echo "ERROR refusing to replace changes in $source_dir" >&2
    exit 1
}

git -C "$source_dir" fetch --depth 1 origin "refs/tags/$tag"
actual_tag_object=$(git -C "$source_dir" rev-parse FETCH_HEAD)
[ "$(git -C "$source_dir" cat-file -t FETCH_HEAD)" = tag ] || {
    echo "ERROR $tag is not an annotated tag object" >&2
    exit 1
}
[ "$actual_tag_object" = "$expected_tag_object" ] || {
    echo "ERROR $tag has unexpected tag object $actual_tag_object" >&2
    exit 1
}
actual_commit=$(git -C "$source_dir" rev-parse 'FETCH_HEAD^{}')
[ "$actual_commit" = "$expected_commit" ] || {
    echo "ERROR $tag resolved to unexpected commit $actual_commit" >&2
    exit 1
}
actual_tree=$(git -C "$source_dir" rev-parse 'FETCH_HEAD^{tree}')
[ "$actual_tree" = "$expected_tree" ] || {
    echo "ERROR $tag resolved to unexpected tree $actual_tree" >&2
    exit 1
}
git -C "$source_dir" checkout -B rog5-build "$actual_commit"

printf 'PASS source_tag=%s tag_object=%s commit=%s tree=%s\n' \
    "$tag" "$actual_tag_object" "$actual_commit" "$actual_tree"
