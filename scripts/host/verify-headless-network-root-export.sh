#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
root=${1:?usage: verify-headless-network-root-export.sh ROOT}
expected=/var/lib/rog5-headless-network-root-v1/root
package=/var/lib/rog5-headless-network-root-v1/manifest

for command in python3 realpath stat; do
	command -v "$command" >/dev/null ||
		fail "missing headless export verifier command: $command"
done
[[ -d $root && ! -L $root ]] || fail 'headless export root is unsafe'
[[ $(realpath -e "$root") == "$expected" ]] ||
	fail 'unexpected headless export root'
[[ -f $package && ! -L $package &&
	$(stat -Lc '%u:%g:%a:%F' "$package") == \
	'0:0:444:regular file' ]] ||
	fail 'installed headless package manifest is unsafe'

python3 "$repo/scripts/host/headless-network-root.py" \
	verify-root "$expected" "$package"
