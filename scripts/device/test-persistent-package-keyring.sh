#!/bin/sh
set -eu
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
helper=$repo/initramfs/persistent-package-keyring
[ -x "$helper" ] || { echo 'FAIL persistent keyring helper is absent'; exit 1; }
sh -n "$helper"
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
awk '/^initialize_keyring\(\) \{/ { copy=1 } copy { print } copy && /^}/ { exit }' \
	"$helper" >"$work/initialize.sh"
[ -s "$work/initialize.sh" ]
. "$work/initialize.sh"
keyring=$work/keyring
calls=$work/calls
ready=0
keyring_complete() { [ "$ready" = 1 ]; }
package_key() {
	printf '%s\n' "$*" >>"$calls"
	[ "${fail_operation:-}" != "$3" ] || return 1
	[ "$3" != --populate ] || ready=1
}
initialize_keyring
[ "$(wc -l <"$calls")" -eq 2 ]
grep -Fxq -- "--gpgdir $keyring --init" "$calls"
grep -Fxq -- "--gpgdir $keyring --populate archlinuxarm" "$calls"
initialize_keyring
[ "$(wc -l <"$calls")" -eq 3 ]
[ "$(grep -c -- --init "$calls")" -eq 1 ]
ready=0
fail_operation=--init
if initialize_keyring; then echo 'FAIL ignored failed initialization'; exit 1; fi
[ "$(wc -l <"$calls")" -eq 4 ]
fail_operation=--populate
if initialize_keyring; then echo 'FAIL ignored failed population'; exit 1; fi

for forbidden in 'TrustAll' 'SigLevel = Never' 'pacman.conf' 'blockdev --setrw' \
	'mkfs' 'fastboot' 'rm -rf'; do
	! grep -Fq "$forbidden" "$helper"
done
grep -Fq 'mount --bind "$keyring" "$runtime"' "$helper"
grep -Fq 'gpgconf --homedir "$keyring" --kill all' "$helper"
echo 'PASS empty-keyring bootstrap, idempotent reuse, failure propagation and unchanged signature policy'
