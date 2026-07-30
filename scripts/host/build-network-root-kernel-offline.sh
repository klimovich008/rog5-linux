#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
source_root=${1:-$repo/build/linux-stable-v7.1.4-network-root-source}
output_root=${2:-$repo/build/network-root-kernel-rebuild-v1}
artifact_root=$repo/artifacts/network-root-v1
builder_image=localhost/rog5-kernel-builder:historical-20260724
builder_verifier=$repo/scripts/host/verify-historical-network-root-builder.sh
expected_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
expected_tree=2ea2be38c5e4dc9aafffbbc0db5aae0f6513a1d9
expected_branch=rog5-build
expected_release=7.1.4-g7a5cef0db479

for command_name in cmp cut find git grep install mkdir podman \
	realpath sha256sum stat; do
	command -v "$command_name" >/dev/null ||
		fail "missing network-root kernel build command: $command_name"
done
[[ -x $builder_verifier && -f $builder_verifier &&
	! -L $builder_verifier ]] ||
	fail 'missing qualified historical network-root builder verifier'
"$builder_verifier" "$builder_image" >/dev/null

source_root=$(realpath -e "$source_root")
[[ -d $source_root/.git && ! -L $source_root ]] ||
	fail 'missing exact Linux source worktree'
[[ $(git -C "$source_root" rev-parse HEAD) == "$expected_commit" &&
	$(git -C "$source_root" rev-parse HEAD^{tree}) == "$expected_tree" ]] ||
	fail 'Linux source commit or tree changed'
[[ $(git -C "$source_root" symbolic-ref --short HEAD) == "$expected_branch" &&
	$(git -C "$source_root" rev-parse --is-shallow-repository) == true ]] ||
	fail 'Linux historical source branch or shallow state changed'
if git -C "$source_root" show-ref --verify --quiet refs/tags/v7.1.4; then
	fail 'Linux historical source unexpectedly retains the release tag ref'
fi
actual_release=$(
	cd "$source_root"
	KERNELVERSION=7.1.4 ./scripts/setlocalversion --no-local .
)
[[ $actual_release == "$expected_release" ]] ||
	fail "Linux historical source release changed: $actual_release"
[[ -z $(git -C "$source_root" status --porcelain --untracked-files=all) ]] ||
	fail 'Linux source worktree is dirty'

output_root=$(realpath -m "$output_root")
case $output_root in
	"$repo"/build/*) ;;
	*) fail 'kernel output root must be below the ignored build directory' ;;
esac
git -C "$repo" check-ignore -q "$output_root" ||
	fail 'kernel output root is not ignored by Git'
[[ ! -e $output_root && ! -L $output_root ]] ||
	fail 'refusing existing network-root kernel output root'
mkdir -p "$output_root/a" "$output_root/b"

{
	grep -E '^(NAME|VERSION_ID|BUILD_ID)=' /etc/os-release || true
	printf 'architecture=%s\n' "$(uname -m)"
	podman version --format 'podman={{.Client.Version}}'
	"$builder_verifier" "$builder_image"
} >"$output_root/host-and-builder.txt"

# The accepted pair both used six jobs. Scheduling is part of this historical
# reconstruction profile even though later builds proved other job counts
# deterministic.
jobs_a=6
jobs_b=6

build_one() {
	suffix=$1
	jobs=$2
	host_output=$output_root/$suffix
	podman run --rm --network=none --security-opt label=disable \
		-v "$repo:/workspace/repo:ro" \
		-v "$source_root:/root/src/linux-7.1.4:ro" \
		-v "$host_output:/root/build/rog5-linux-7.1.4-network-root" \
		-e JOBS="$jobs" \
		"$builder_image" \
		/workspace/repo/scripts/device/build-mainline-network-root.sh
	podman run --rm --network=none --security-opt label=disable \
		-v "$repo:/workspace/repo:ro" \
		-v "$host_output:/root/build/rog5-linux-7.1.4-network-root:ro" \
		"$builder_image" \
		/workspace/repo/scripts/device/verify-mainline-network-root-build.sh \
		/root/build/rog5-linux-7.1.4-network-root
	[[ $(<"$host_output/include/config/kernel.release") == \
		"$expected_release" ]] ||
		fail "network-root kernel release changed in build $suffix"
}

build_one a "$jobs_a"
build_one b "$jobs_b"

for relative in \
	.config \
	arch/arm64/boot/Image \
	arch/arm64/boot/Image.gz \
	modules.tar.gz \
	build-meta.txt; do
	cmp "$output_root/a/$relative" "$output_root/b/$relative" ||
		fail "independent network-root kernel builds differ: $relative"
done

check_exact() {
	path=$1
	size=$2
	hash=$3
	label=$4
	[[ -f $path && ! -L $path && $(stat -c %s "$path") == "$size" ]] ||
		fail "$label size or file type changed"
	[[ $(sha256sum "$path" | cut -d ' ' -f 1) == "$hash" ]] ||
		fail "$label hash changed"
}

check_exact "$output_root/a/arch/arm64/boot/Image" 40049152 \
	349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf \
	'accepted network-root Image'
check_exact "$output_root/a/arch/arm64/boot/Image.gz" 14751785 \
	a1756e36f42a57c90bd85ef33d68aa1424768a45f272cc0514c2992ace0ae6e5 \
	'accepted compressed network-root Image'
check_exact "$output_root/a/.config" 239677 \
	68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f \
	'accepted network-root config'
check_exact "$output_root/a/modules.tar.gz" 300439504 \
	5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9 \
	'accepted network-root modules'
check_exact "$output_root/a/build-meta.txt" 629 \
	1cd315745755394ffceea7a2124800c63f8f67ca776fe4bdf47f9b296e1a4ecf \
	'accepted network-root build metadata'

publish_exact() {
	input=$1
	output=$2
	size=$3
	hash=$4
	label=$5
	if [[ -e $output || -L $output ]]; then
		check_exact "$output" "$size" "$hash" "$label published artifact"
		cmp "$input" "$output"
		return
	fi
	install -D -m 0644 "$input" "$output"
	check_exact "$output" "$size" "$hash" "$label published artifact"
}

publish_exact "$output_root/a/arch/arm64/boot/Image" \
	"$artifact_root/Image-7.1.4-network-root" 40049152 \
	349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf \
	'network-root Image'
publish_exact "$output_root/a/arch/arm64/boot/Image.gz" \
	"$artifact_root/Image.gz-7.1.4-network-root" 14751785 \
	a1756e36f42a57c90bd85ef33d68aa1424768a45f272cc0514c2992ace0ae6e5 \
	'compressed network-root Image'
publish_exact "$output_root/a/.config" \
	"$artifact_root/config-7.1.4-network-root" 239677 \
	68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f \
	'network-root config'
publish_exact "$output_root/a/modules.tar.gz" \
	"$artifact_root/modules-7.1.4-network-root.tar.gz" 300439504 \
	5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9 \
	'network-root modules'
publish_exact "$output_root/a/build-meta.txt" \
	"$artifact_root/build-meta-7.1.4-network-root.txt" 629 \
	1cd315745755394ffceea7a2124800c63f8f67ca776fe4bdf47f9b296e1a4ecf \
	'network-root build metadata'

printf 'source_commit=%s\nsource_tree=%s\njobs_a=%s\njobs_b=%s\n' \
	"$expected_commit" "$expected_tree" "$jobs_a" "$jobs_b" \
	>"$output_root/acceptance.txt"
sha256sum \
	"$artifact_root/Image-7.1.4-network-root" \
	"$artifact_root/Image.gz-7.1.4-network-root" \
	"$artifact_root/config-7.1.4-network-root" \
	"$artifact_root/modules-7.1.4-network-root.tar.gz" \
	"$artifact_root/build-meta-7.1.4-network-root.txt"

# The canonical artifacts and compact reports are retained. The two disposable
# object trees are deleted only after every twin-build and publication gate.
find "$output_root/a" -depth -delete
find "$output_root/b" -depth -delete
echo 'PASS twin network-disabled Linux 7.1.4 network-root rebuild matches every historical identity'
