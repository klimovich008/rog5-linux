#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
baseline=$repo/scripts/device/check-network-root-adreno-smmu-baseline.sh

[ -x "$baseline" ] || {
	echo 'FAIL missing executable Adreno SMMU baseline' >&2
	exit 1
}
sh -n "$baseline"
fault_pattern='(IOMMU|arm-smmu).*[^[:alnum:]_]fault([^[:alnum:]_]|$)|(context|global)[[:space:]]+fault([^[:alnum:]_]|$)'

for contract in \
	'7.1.4-g7a5cef0db479' \
	'systemd-udev-trigger.service' \
	'systemd-modules-load.service' \
	'/run/rog5-network-root-watchdog.pid' \
	'rog5_qcom_cc_probe_trace' \
	'rog5_ccf_register_trace' \
	'rog5_rcg2_parent_trace' \
	'[ "$(cat "$trace_path")" = N ]' \
	'findmnt -n -o SOURCE /.rog5/root-ro' \
	'169.254.77.1:/' \
	'physical block device is present' \
	'block-backed mount is present' \
	'/sys/class/net/usb0/carrier' \
	'/soc@0/clock-controller@3d90000' \
	'/soc@0/iommu@3da0000' \
	'qcom,sm8350-smmu-500' \
	'qcom,adreno-smmu' \
	'soc@0/gpu@3d00000' \
	'soc@0/gmu@3d6a000' \
	'/sys/module/gpucc_sm8350' \
	'/sys/bus/platform/drivers/arm-smmu' \
	'/dev/dri' \
	'a660_sqe.fw|a660_gmu.bin|a660_zap.mbn' \
	'Kernel panic|Oops:|BUG:' \
	"$fault_pattern" \
	'thermal_count' \
	'sleep 12'
do
	grep -Fq "$contract" "$baseline" || {
		echo "FAIL Adreno SMMU baseline omits: $contract" >&2
		exit 1
	}
done

if printf '%s\n' 'iommu: Default domain type: Translated' |
	grep -Ei "$fault_pattern" >/dev/null
then
	echo 'FAIL Adreno SMMU fault detector accepts the normal Default line' >&2
	exit 1
fi
for line in \
	'arm-smmu 3da0000.iommu: Unhandled context fault' \
	'IOMMU page fault at address 0' \
	'arm-smmu: global fault'
do
	printf '%s\n' "$line" | grep -Ei "$fault_pattern" >/dev/null || {
		echo "FAIL Adreno SMMU fault detector misses: $line" >&2
		exit 1
	}
done

if grep -Eq '^[[:space:]]*(fastboot|mount|umount|modprobe|insmod|rmmod)([[:space:]]|$)|fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|echo[[:space:]].*>[[:space:]]*/(sys|proc|dev)/|tee[[:space:]].*/(sys|proc|dev)/' \
	"$baseline"
then
	echo 'FAIL Adreno SMMU baseline contains a control or persistent-write path' >&2
	exit 1
fi

echo 'PASS Adreno SMMU baseline is read-only, watchdog-first, firmware-free, and zero-storage'
