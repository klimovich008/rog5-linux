#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
root=${1:?usage: verify-a660-runtime-root.sh ROOT IDENTITY}
identity=${2:?usage: verify-a660-runtime-root.sh ROOT IDENTITY}
verifier=$repo/scripts/host/a660-runtime-root.py

[[ $EUID == 0 ]] ||
	fail 'A660 runtime-root verification requires root to read the complete tree'
for command in btrfs findmnt python3 realpath stat; do
	command -v "$command" >/dev/null ||
		fail "missing A660 runtime-root verification command: $command"
done
case $root:$identity in
	/*:/*) ;;
	*) fail 'A660 runtime-root paths must be absolute' ;;
esac
[[ -d $root && ! -L $root ]] ||
	fail 'A660 runtime root is absent, linked, or not a directory'
[[ -f $identity && ! -L $identity ]] ||
	fail 'A660 runtime-root identity is absent or linked'
root=$(realpath -e "$root")
identity=$(realpath -e "$identity")
[[ $root != / ]] || fail 'refusing the host root filesystem'
[[ $(findmnt -n -o FSTYPE --target "$root") == btrfs ]] ||
	fail 'A660 runtime root is not on Btrfs'
btrfs subvolume show "$root" >/dev/null 2>&1 ||
	fail 'A660 runtime root is not a Btrfs subvolume'
[[ $(btrfs property get -ts "$root" ro) == ro=true ]] ||
	fail 'A660 runtime-root subvolume is writable'
[[ $(stat -c '%u:%g:%a' "$root") == 0:0:555 ]] ||
	fail 'A660 runtime-root top-level metadata changed'
[[ $(stat -c '%u:%g:%a' "$identity") == 0:0:444 ]] ||
	fail 'A660 runtime-root sidecar metadata changed'

exec python3 "$verifier" verify --root "$root" --identity "$identity"
