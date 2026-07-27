#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
v2_stage=$repo/scripts/device/stage-arch-rootfs.sh
v3_stage=$repo/scripts/device/stage-arch-rootfs-v3.sh
v2_verifier=$repo/scripts/device/verify-staged-arch-rootfs-v2.sh
v3_verifier=$repo/scripts/device/verify-staged-arch-rootfs-v3.sh
v3_runner=$repo/scripts/device/run-arch-rootfs-v3-stage.sh
host_stage=$repo/scripts/host/stage-arch-rootfs.sh
host_v3=$repo/scripts/host/stage-arch-successor-v3-rootfs.sh
button=$repo/scripts/device/power-buttond.py
button_test=$repo/scripts/device/test-power-buttond.sh
button_unit=$repo/packaging/arch/rog5-power-button.service

fail() {
	echo "FAIL $*" >&2
	exit 1
}

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

for input in "$v2_stage" "$v3_stage" "$v2_verifier" "$v3_verifier" \
	"$v3_runner" "$host_stage" "$host_v3" "$button" "$button_test" \
	"$button_unit"; do
	[ -f "$input" ] && [ ! -L "$input" ] ||
		fail "missing or linked successor-v3 input: $input"
done
for script in "$v3_stage" "$v2_verifier" "$v3_verifier" \
	"$v3_runner" "$host_stage" "$host_v3" "$button" "$button_test"; do
	[ -x "$script" ] ||
		fail "successor-v3 input is not executable: $script"
done
bash -n "$v2_stage" "$v3_stage" "$v2_verifier" "$v3_verifier" \
	"$v3_runner" "$host_stage" "$host_v3"

[ "$(sha256sum "$v2_verifier" | cut -d ' ' -f 1)" = \
	5137868d14400815e99ee642d78ccd125196ce811238120836c59cce92abe44e ] ||
	fail 'accepted successor-v2 verifier changed'

for contract in \
	'/bin/bash "$repo/scripts/device/stage-arch-rootfs.sh"' \
	'install -Dm0755 "$repo/scripts/device/power-buttond.py"' \
	'/usr/local/libexec/rog5-power-buttond' \
	'install -Dm0644 "$repo/packaging/arch/rog5-power-button.service"' \
	'/etc/systemd/system/rog5-power-button.service' \
	'systemctl enable rog5-power-button.service' \
	'scripts/device/verify-staged-arch-rootfs-v3.sh'
do
	grep -Fq "$contract" "$v3_stage" ||
		fail "successor-v3 stage omits: $contract"
done

for contract in \
	'5137868d14400815e99ee642d78ccd125196ce811238120836c59cce92abe44e' \
	'scripts/device/verify-staged-arch-rootfs-v2.sh' \
	'cmp /usr/local/libexec/rog5-power-buttond' \
	'cmp /etc/systemd/system/rog5-power-button.service' \
	'systemctl is-enabled rog5-power-button.service' \
	'TARGET=/usr/local/libexec/rog5-power-buttond' \
	'UNIT=/etc/systemd/system/rog5-power-button.service' \
	'scripts/device/test-power-buttond.sh'
do
	grep -Fq "$contract" "$v3_verifier" ||
		fail "successor-v3 verifier omits: $contract"
done

for contract in \
	'ARCH_ROOTFS_GENERATION' \
	'scripts/device/run-arch-rootfs-v3-stage.sh' \
	'scripts/device/verify-staged-arch-rootfs-v3.sh'
do
	grep -Fq "$contract" "$host_stage" ||
		fail "host staging selector omits: $contract"
done

for contract in \
	'ARCH_DEVICE_STAGE=scripts/device/stage-arch-rootfs-v3.sh' \
	'exec /workspace/repo/scripts/device/run-arch-rootfs-stage.sh'
do
	grep -Fq "$contract" "$v3_runner" ||
		fail "successor-v3 stage runner omits: $contract"
done

for contract in \
	'ARCH_ROOTFS_GENERATION=v3' \
	'rog5-arch-plasma-network-root-7.1.4-successor-v3.tar.gz' \
	'exec "$repo/scripts/host/stage-arch-rootfs.sh"'
do
	grep -Fq "$contract" "$host_v3" ||
		fail "successor-v3 host wrapper omits: $contract"
done

if ARCH_ROOTFS_GENERATION=invalid "$host_stage" "$repo/missing.pub" \
	>"$work/invalid.out" 2>&1
then
	fail 'host stage accepted an unknown rootfs generation'
fi
grep -Fq 'unsupported Arch rootfs generation: invalid' \
	"$work/invalid.out" ||
	fail 'unknown rootfs generation rejection was not explicit'

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/' \
	"$v3_stage" "$v3_verifier" "$v3_runner" "$host_v3"
then
	fail 'successor-v3 staging can control the phone or write storage'
fi

echo 'PASS successor v3 layers the confined power-button toggle over byte-exact v2 evidence without a phone command'
