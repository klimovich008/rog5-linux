#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
qemu=$repo/artifacts/host-tools/qemu-aarch64-static
sealed_runner=$repo/scripts/host/run-sealed-arm64-binfmt.py
expected_size=6245816
expected_sha=bfcd46c842441912baed36158569ac29a7fb656684ca73c1b3b2f0f3971e9bec
expected_sealed_runner=354ea9b62a7ec9f19501858e3e0d2c4f848faa93e639dccc36bb23f5a016c301

check_sealed_runner() {
	[[ -f $sealed_runner && ! -L $sealed_runner && -x $sealed_runner ]] ||
		fail 'missing sealed ARM64 binfmt runner'
	[[ $(sha256sum "$sealed_runner" | cut -d ' ' -f 1) == \
		"$expected_sealed_runner" ]] ||
		fail 'sealed ARM64 binfmt runner changed'
}

check_qemu() {
	[[ -f $qemu && ! -L $qemu && -x $qemu ]] ||
		fail 'missing qualified QEMU artifact; run extract-qualified-qemu-aarch64-static.sh'
	[[ $(stat -c %s "$qemu") == "$expected_size" ]] ||
		fail 'qualified QEMU size changed'
	[[ $(sha256sum "$qemu" | cut -d ' ' -f 1) == "$expected_sha" ]] ||
		fail 'qualified QEMU hash changed'
}

if [[ ${1:-} == --inside-private-mount ]]; then
	shift
	namespace_guard=${1:-}
	shift || true
	[[ -n ${ROG5_PRIVATE_BINFMT_GUARD:-} &&
		$namespace_guard == "$ROG5_PRIVATE_BINFMT_GUARD" ]] ||
		fail 'private ARM64 branch lacks its outer-runner guard'
	[[ $# -gt 0 ]] || fail 'missing command inside private ARM64 namespace'
	for command_name in cut findmnt id mount python3 sha256sum stat; do
		command -v "$command_name" >/dev/null ||
			fail "missing private ARM64 namespace command: $command_name"
	done
	check_sealed_runner
	[[ $(id -u) == 0 ]] ||
		fail 'private ARM64 branch requires root inside a rootless user namespace'
	read -r inside_id outside_id map_length _ </proc/self/uid_map ||
		fail 'could not read private ARM64 user-namespace mapping'
	[[ $inside_id == 0 && $outside_id != 0 && $map_length -gt 0 ]] ||
		fail 'private ARM64 branch is not inside a rootless user namespace'
	case $(findmnt -n -o PROPAGATION /) in
		private|private,*) ;;
		*) fail 'private ARM64 branch requires private mount propagation' ;;
	esac
	mount --make-rprivate /
	mount -t binfmt_misc none /proc/sys/fs/binfmt_misc
	exec python3 "$sealed_runner" "$qemu" "$expected_size" "$expected_sha" \
		-- "$@"
fi

for command_name in cut findmnt grep head id mount podman sha256sum stat \
	unshare python3; do
	command -v "$command_name" >/dev/null ||
		fail "missing private ARM64 namespace command: $command_name"
done
check_sealed_runner
[[ $# -gt 0 ]] || fail 'usage: run-private-arm64-binfmt.sh COMMAND [ARG...]'
[[ ! -e /proc/sys/fs/binfmt_misc/qemu-aarch64 ]] ||
	fail 'host ARM64 binfmt handler must be absent for private-runner proof'
check_qemu

namespace_guard=$(head -c 32 /dev/urandom | sha256sum | cut -d ' ' -f 1)
export ROG5_PRIVATE_BINFMT_GUARD=$namespace_guard
exec podman unshare unshare --mount "$0" --inside-private-mount \
	"$namespace_guard" "$@"
