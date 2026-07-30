#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
output=${1:-$repo/build/linux-stable-v7.1.4-network-root-source}
source_url=https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
tag=v7.1.4
expected_tag=114456a9c542d933387517bb22561668c25a5b59
expected_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_tree=2ea2be38c5e4dc9aafffbbc0db5aae0f6513a1d9
expected_branch=rog5-build
expected_release=7.1.4-g7a5cef0db479

for command_name in dirname find git mkdir mktemp mv realpath; do
	command -v "$command_name" >/dev/null ||
		fail "missing Linux source-fetch command: $command_name"
done

verify_source() {
	source_root=$1
	[[ -d $source_root/.git && ! -L $source_root ]] ||
		fail 'missing regular Linux source worktree'
	[[ $(git -C "$source_root" cat-file -t "$expected_tag") == tag ]] ||
		fail 'Linux v7.1.4 reference is not an annotated tag'
	[[ $(git -C "$source_root" rev-parse "$expected_tag^{}") == \
		"$expected_commit" ]] ||
		fail 'Linux tag peeled commit changed'
	[[ $(git -C "$source_root" rev-parse HEAD) == "$expected_commit" ]] ||
		fail 'Linux source HEAD changed'
	[[ $(git -C "$source_root" rev-parse HEAD^{tree}) == "$expected_tree" ]] ||
		fail 'Linux source tree changed'
	[[ $(git -C "$source_root" symbolic-ref --short HEAD) == \
		"$expected_branch" ]] ||
		fail 'Linux historical build branch changed'
	[[ $(git -C "$source_root" rev-parse --is-shallow-repository) == true ]] ||
		fail 'Linux historical source is not shallow'
	if git -C "$source_root" show-ref --verify --quiet "refs/tags/$tag"; then
		fail 'Linux historical source unexpectedly retains the release tag ref'
	fi
	[[ $(git -C "$source_root" remote get-url origin) == "$source_url" ]] ||
		fail 'Linux source origin changed'
	actual_release=$(
		cd "$source_root"
		KERNELVERSION=7.1.4 ./scripts/setlocalversion --no-local .
	)
	[[ $actual_release == "$expected_release" ]] ||
		fail "Linux historical source release changed: $actual_release"
	git -C "$source_root" diff --quiet
	git -C "$source_root" diff --cached --quiet
	[[ -z $(git -C "$source_root" status --porcelain --untracked-files=all) ]] ||
		fail 'Linux source worktree is dirty'
	git -C "$source_root" fsck --strict --no-dangling >/dev/null
}

output=$(realpath -m "$output")
case $output in
	"$repo"/build/*) ;;
	*) fail 'Linux source output must be below the ignored build directory' ;;
esac
git -C "$repo" check-ignore -q "$output" ||
	fail 'Linux source output is not ignored by Git'
if [[ -e $output || -L $output ]]; then
	verify_source "$output"
	echo "PASS exact Linux $tag source already present"
	echo "OUTPUT $output"
	exit 0
fi

parent=$(dirname "$output")
mkdir -p "$parent"
temporary=$(mktemp -d "$parent/.linux-stable-v7.1.4.fetch.XXXXXX")
cleanup() {
	if [[ -n ${temporary:-} && -e $temporary ]]; then
		find "$temporary" -depth -delete 2>/dev/null || true
	fi
}
trap cleanup EXIT HUP INT TERM

git -C "$temporary" init --quiet
git -C "$temporary" remote add origin "$source_url"
git -C "$temporary" -c protocol.version=2 fetch \
	--depth=1 --no-tags origin "refs/tags/$tag"
git -C "$temporary" checkout --quiet -B "$expected_branch" FETCH_HEAD
verify_source "$temporary"

mv -T -- "$temporary" "$output"
temporary=
trap - EXIT HUP INT TERM
verify_source "$output"

printf 'tag=%s\ntag_object=%s\ncommit=%s\ntree=%s\n' \
	"$tag" "$expected_tag" "$expected_commit" "$expected_tree"
printf 'branch=%s\nkernel_release=%s\n' \
	"$expected_branch" "$expected_release"
echo 'PASS fetched exact official Linux stable source'
echo "OUTPUT $output"
