#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
builder=$repo/scripts/device/build-network-root-initramfs.sh
verifier=$repo/scripts/device/verify-network-root-initramfs.sh
init=$repo/initramfs/network-root-init
probe=$repo/scripts/device/probe-network-root-battery-telemetry.sh
hash=0b7df05e9fa0bfe224fc74ac93997bb1ee74ab5371bde172c3b0a2fcfe19601b

for source in "$builder" "$verifier" "$init" "$probe"; do
	[ -f "$source" ] && [ ! -L "$source" ]
done
grep -Fq 'NETWORK_ROOT_EXPECT_PDR_MODULE="$([ -n "$pdr_module" ]' "$builder"

for contract in \
	'NETWORK_ROOT_PDR_MODULE' \
	"pdr_module_sha=$hash" \
	'$stage/opt/rog5-charge-modules/pdr_interface.ko' \
	'$exitrd/rog5-charge-inputs/modules' \
	'NETWORK_ROOT_EXPECT_PDR_MODULE' \
	'$input_dir/modules/pdr_interface.ko' \
	'no-BTF PDR override hash changed' \
	'insmod "$pdr_module"'; do
	grep -Fq "$contract" "$builder" "$verifier" "$init" "$probe" || {
		echo "FAIL missing PDR override contract: $contract" >&2
		exit 1
	}
done

pdm_line=$(grep -n 'modprobe --first-time qcom_pd_mapper' "$probe" |
	tail -n1 | cut -d: -f1)
pdr_line=$(grep -n '^[[:space:]]*if ! insmod "$pdr_module"' "$probe" |
	cut -d: -f1)
[ "$pdm_line" -lt "$pdr_line" ]
! grep -F 'insmod "$pdr_module"' "$probe" | grep -Fq 'modprobe'

echo 'PASS V18 PDR BTF failure becomes one exact no-BTF override loaded after its dependency'
