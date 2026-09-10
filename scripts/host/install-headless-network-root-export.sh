#!/usr/bin/env bash
set -euo pipefail
umask 077

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
archive=$repo/artifacts/arch/rog5-arch-headless-network-root-7.1.4/root.tar.gz
package=$repo/configs/network-roots/headless-network-root-v1.package
destination=/var/lib/rog5-headless-network-root-v1
stage=$destination.partial.$$

(( EUID == 0 )) || fail 'run through PolicyKit; do not share a sudo password'
for command in awk bsdtar install mv python3 realpath sha256sum stat; do
	command -v "$command" >/dev/null ||
		fail "missing headless export installer command: $command"
done
for input in "$archive" "$package"; do
	[[ -f $input && ! -L $input ]] ||
		fail "missing fixed headless export input: $input"
done
[[ ! -e $destination && ! -L $destination ]] ||
	fail "refusing existing headless export: $destination"
[[ ! -e $stage && ! -L $stage ]] ||
	fail "refusing existing headless export stage: $stage"

package_value() {
	local name=$1
	awk -F= -v name="$name" '
		$1 == name { count++; value=$2 }
		END { if (count == 1) print value }
	' "$package"
}

expected_size=$(package_value sealed_archive_size)
expected_hash=$(package_value sealed_archive_sha256)
[[ $expected_size =~ ^[1-9][0-9]*$ &&
	$expected_hash =~ ^[0-9a-f]{64}$ ]] ||
	fail 'tracked headless package identity is invalid'
[[ $(stat -c %s "$archive") == "$expected_size" ]] ||
	fail 'headless archive size changed'
[[ $(sha256sum "$archive" | awk '{ print $1 }') == "$expected_hash" ]] ||
	fail 'headless archive hash changed'

succeeded=0
cleanup() {
	if [[ $succeeded != 1 && -e $stage ]]; then
		echo "INFO retained failed headless export stage: $stage" >&2
	fi
}
trap cleanup EXIT
trap 'exit 130' HUP INT TERM

install -d -o root -g root -m 0700 "$stage"
bsdtar --numeric-owner --same-permissions --acls --xattrs --fflags \
	-xpf "$archive" -C "$stage"
[[ -d $stage/root && ! -L $stage/root ]] ||
	fail 'headless archive lacks its fixed root directory'
install -o root -g root -m 0444 "$package" "$stage/manifest"
python3 "$repo/scripts/host/headless-network-root.py" \
	verify-root "$stage/root" "$stage/manifest"
mv -T -- "$stage" "$destination"
succeeded=1
echo "PASS installed sealed headless export at $destination/root"
