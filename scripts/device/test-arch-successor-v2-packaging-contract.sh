#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
stage=$repo/scripts/device/stage-arch-rootfs.sh
host_stage=$repo/scripts/host/stage-arch-rootfs.sh
verifier=$repo/scripts/device/verify-staged-arch-rootfs-v2.sh
v1_target=$repo/scripts/device/vpn-hotspot.sh
v1_service=$repo/packaging/arch/rog5-vpn-hotspot.service
v1_verifier=$repo/scripts/device/verify-staged-arch-rootfs.sh
v2_target=$repo/scripts/device/vpn-hotspot-v2.sh
v2_service=$repo/packaging/arch/rog5-vpn-hotspot-v2.service

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for input in "$stage" "$host_stage" "$verifier" "$v1_target" \
	"$v1_service" "$v1_verifier" "$v2_target" "$v2_service"; do
	[ -f "$input" ] && [ ! -L "$input" ] ||
		fail "missing or linked packaging input: $input"
done
for script in "$host_stage" "$verifier" "$v2_target"; do
	[ -x "$script" ] || fail "packaging script is not executable: $script"
done
bash -n "$stage"
bash -n "$host_stage"
bash -n "$verifier"

check_hash() {
	file=$1
	expected=$2
	label=$3
	actual=$(sha256sum "$file" | cut -d ' ' -f 1)
	[ "$actual" = "$expected" ] ||
		fail "$label changed: expected $expected, got $actual"
}

check_hash "$v1_target" \
	f270cc05ebf2776179f9eb7e5f1f96d3ce76f5b144c30b961cff26f923fe849d \
	'accepted v1 hotspot control'
check_hash "$v1_service" \
	4c29a2cb097a081b9dc4b18abc330d5f6401211cad4178de2b77eb73f0dd5525 \
	'accepted v1 hotspot service'
check_hash "$v1_verifier" \
	e8ab452b1994ffbffe0a0e1db32e3b2f66866d813e8f32b03713fb4f2545e87f \
	'accepted v1 staged-root verifier'

for contract in \
	'install -Dm0755 "$repo/scripts/device/vpn-hotspot-v2.sh" /usr/local/sbin/rog5-vpn-hotspot.sh' \
	'install -Dm0644 "$repo/packaging/arch/rog5-vpn-hotspot-v2.service" /etc/systemd/system/rog5-vpn-hotspot.service' \
	'scripts/device/verify-staged-arch-rootfs-v2.sh'
do
	grep -Fq "$contract" "$stage" "$host_stage" ||
		fail "successor v2 staging omits: $contract"
done

for contract in \
	'cmp /usr/local/sbin/rog5-vpn-hotspot.sh' \
	'/workspace/repo/scripts/device/vpn-hotspot-v2.sh' \
	'cmp /etc/systemd/system/rog5-vpn-hotspot.service' \
	'/workspace/repo/packaging/arch/rog5-vpn-hotspot-v2.service' \
	'e8ab452b1994ffbffe0a0e1db32e3b2f66866d813e8f32b03713fb4f2545e87f' \
	'scripts/device/verify-staged-arch-rootfs.sh' \
	'scripts/device/test-vpn-hotspot-transition-v2.sh'
do
	grep -Fq "$contract" "$verifier" ||
		fail "successor v2 verifier omits: $contract"
done

for inherited_contract in \
	'systemd-analyze verify' \
	'[[ ! -e /etc/wireguard/wg0.conf ]]' \
	'[[ -z $(find /etc/NetworkManager/system-connections'
do
	grep -Fq "$inherited_contract" "$v1_verifier" ||
		fail "accepted full-root verifier omits: $inherited_contract"
done

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/' \
	"$stage" "$host_stage" "$verifier"
then
	fail 'successor v2 packaging controls the phone or storage'
fi

echo 'PASS successor v2 packaging installs exact hardened hotspot controls, preserves v1 evidence, verifies the full root, and embeds no secret'
