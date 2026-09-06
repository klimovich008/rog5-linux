#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
image=localhost/rog5-kernel-builder:historical-20260724
image_verifier=$repo/scripts/host/verify-historical-network-root-builder.sh
output=${1:-$repo/artifacts/host-tools/qemu-aarch64-static}
expected_size=6245816
expected_sha=bfcd46c842441912baed36158569ac29a7fb656684ca73c1b3b2f0f3971e9bec
expected_version='qemu-aarch64 version 8.2.2 (Debian 1:8.2.2+ds-0ubuntu1.17)'

for command_name in basename chmod cut dirname head mkdir mktemp mv podman \
	realpath rm sha256sum stat; do
	command -v "$command_name" >/dev/null ||
		fail "missing QEMU extraction command: $command_name"
done
[[ -f $image_verifier && ! -L $image_verifier && -x $image_verifier ]] ||
	fail 'missing historical builder verifier'

canonicalize_output() {
	output=$(realpath -m -- "$output") ||
		fail 'could not canonicalize QEMU output'
	case $output in
		"$repo"/artifacts/host-tools/*|"$repo"/build/*) ;;
		*) fail 'QEMU output must remain in an ignored project artifact directory' ;;
	esac
	output_name=$(basename -- "$output")
	output_parent=$(dirname -- "$output")
	[[ $output_name != . && $output_name != .. ]] ||
		fail 'invalid QEMU output basename'
}

revalidate_output_parent() {
	local resolved_parent
	resolved_parent=$(realpath -e -- "$output_parent") ||
		fail 'QEMU output parent disappeared'
	[[ $resolved_parent == "$output_parent" ]] ||
		fail 'QEMU output parent changed or became a symlink'
	case $resolved_parent/ in
		"$repo"/artifacts/host-tools/*|"$repo"/build/*) ;;
		*) fail 'QEMU output parent escaped the ignored project artifact directory' ;;
	esac
}

canonicalize_output

check_output() {
	[[ -f $output && ! -L $output && -x $output ]] ||
		fail 'missing, linked, or non-executable QEMU output'
	[[ $(stat -c %s "$output") == "$expected_size" ]] ||
		fail 'QEMU output size changed'
	[[ $(sha256sum "$output" | cut -d ' ' -f 1) == "$expected_sha" ]] ||
		fail 'QEMU output hash changed'
	[[ $("$output" --version | head -1) == "$expected_version" ]] ||
		fail 'QEMU output version changed'
}

if [[ -e $output || -L $output ]]; then
	check_output
	printf 'PASS retained qualified static AArch64 emulator\n'
	exit 0
fi

"$image_verifier" "$image" >/dev/null
mkdir -p "$output_parent"
output_parent=$(realpath -e -- "$output_parent") ||
	fail 'could not resolve created QEMU output parent'
output=$output_parent/$output_name
revalidate_output_parent
temporary=$(mktemp "$output_parent/.qemu-aarch64-static.tmp.XXXXXX")
container=
cleanup() {
	if [[ -n $container ]]; then
		podman rm --force "$container" >/dev/null 2>&1 || true
	fi
	[[ ! -e $temporary ]] || rm -f -- "$temporary"
}
trap cleanup EXIT HUP INT TERM

container=$(podman create --network=none "$image" /bin/true)
podman cp "$container:/usr/bin/qemu-aarch64-static" "$temporary"
chmod 0755 "$temporary"
revalidate_output_parent
[[ ! -e $output && ! -L $output ]] ||
	fail 'QEMU output appeared during extraction'
mv -T --no-clobber -- "$temporary" "$output"
[[ ! -e $temporary ]] ||
	fail 'QEMU output move was not completed'
check_output

podman rm --force "$container" >/dev/null
container=
trap - EXIT HUP INT TERM
printf 'qemu_sha256=%s\n' "$expected_sha"
printf 'PASS extracted qualified static AArch64 emulator without host install\n'
