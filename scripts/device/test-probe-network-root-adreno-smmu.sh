#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
probe=$repo/scripts/device/probe-network-root-adreno-smmu.sh

[ -x "$probe" ] || {
	echo 'FAIL missing executable attended Adreno SMMU probe' >&2
	exit 1
}
sh -n "$probe"
fault_pattern='(IOMMU|arm-smmu).*[^[:alnum:]_]fault([^[:alnum:]_]|$)|(context|global)[[:space:]]+fault([^[:alnum:]_]|$)'

for contract in \
	'ALLOW_MAINLINE_ADRENO_SMMU_PROBE' \
	'7.1.4-g7a5cef0db479' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'/run/rog5-gpucc-diagnostic/gpucc-sm8350.ko' \
	'9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a' \
	'7.1.4-g7a5cef0db479 SMP preempt mod_unload aarch64' \
	'probe_trace:Emit progress notices for attended SM8350 GPUCC diagnostics (bool)' \
	'/soc@0/clock-controller@3d90000' \
	'/soc@0/iommu@3da0000' \
	'/soc@0/gpu@3d00000' \
	'/soc@0/gmu@3d6a000' \
	'qcom,sm8350-smmu-500' \
	'qcom,adreno-smmu' \
	'/sys/bus/platform/drivers/sm8350-gpucc' \
	'/sys/bus/platform/drivers/arm-smmu' \
	'/sys/module/gpucc_sm8350/parameters/probe_trace' \
	'insmod "$module_file" probe_trace=1' \
	'power/runtime_status' \
	'suspended' \
	'/sys/kernel/iommu_groups' \
	'/dev/dri' \
	'a660_sqe.fw|a660_gmu.bin|a660_zap.mbn' \
	"$fault_pattern" \
	'exec 9>/proc/sysrq-trigger' \
	'echo b >&9' \
	'setsid sh -c' \
	'kill -STOP -- "-$watchdog_pid"' \
	'kill -KILL -- "-$watchdog_pid"' \
	'physical block device appeared' \
	'block-backed mount appeared' \
	'/sys/class/net/usb0/carrier' \
	'thermal_max' \
	'probe_safe=1'
do
	grep -Fq "$contract" "$probe" || {
		echo "FAIL attended Adreno SMMU probe omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'rmmod|modprobe[[:space:]].*(-r|--remove)|fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/' \
	"$probe"
then
	echo 'FAIL attended Adreno SMMU probe unloads a driver or writes storage' >&2
	exit 1
fi

set +e
"$probe" >/dev/null 2>&1
missing_guard=$?
ALLOW_MAINLINE_ADRENO_SMMU_PROBE=unsafe "$probe" >/dev/null 2>&1
invalid_guard=$?
set -e
[ "$missing_guard" -ne 0 ]
[ "$invalid_guard" -ne 0 ]

echo 'PASS attended Adreno SMMU probe is one-shot, watchdog-bounded, firmware-free, and zero-storage'
