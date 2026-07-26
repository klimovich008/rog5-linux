#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
baseline=$repo/scripts/device/check-network-root-a660-registration-baseline.sh
probe=$repo/scripts/device/probe-network-root-a660-registration.sh

[ -x "$baseline" ] || {
	echo 'FAIL missing executable A660 registration baseline' >&2
	exit 1
}
[ -x "$probe" ] || {
	echo 'FAIL missing executable attended A660 registration probe' >&2
	exit 1
}
sh -n "$baseline"
sh -n "$probe"

for contract in \
	'/run/rog5-network-root-watchdog.pid' \
	'systemd-udev-trigger.service' \
	'systemd-modules-load.service' \
	'/soc@0/clock-controller@3d90000' \
	'/soc@0/iommu@3da0000' \
	'/soc@0/gpu@3d00000' \
	'/soc@0/gmu@3d6a000' \
	'/sys/module/gpucc_sm8350' \
	'/sys/module/msm' \
	'/dev/dri/renderD' \
	'a660_sqe.fw|a660_gmu.bin|a660_zap.mbn' \
	'physical block device is present' \
	'block-backed mount is present' \
	'IOMMU.*fault|arm-smmu.*fault|context fault|global fault' \
	'thermal_count'
do
	grep -Fq "$contract" "$baseline" || {
		echo "FAIL A660 registration baseline omits: $contract" >&2
		exit 1
	}
done

for contract in \
	'ALLOW_MAINLINE_A660_REGISTRATION' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'gpucc-sm8350.ko' \
	'msm.ko' \
	"insmod \"\$gpucc_module\" probe_trace=1" \
	"insmod \"\$msm_module\" separate_gpu_kms=1" \
	'/sys/module/msm/parameters/separate_gpu_kms' \
	'/sys/bus/platform/drivers/sm8350-gpucc' \
	'/sys/bus/platform/drivers/arm-smmu' \
	'/sys/bus/platform/drivers/adreno' \
	'/sys/kernel/iommu_groups' \
	'/dev/dri/renderD' \
	'/proc/[0-9]*/fd/*' \
	'a660_sqe.fw|a660_gmu.bin|a660_zap.mbn' \
	'exec 9>/proc/sysrq-trigger' \
	'echo b >&9' \
	'setsid sh -c' \
	"kill -STOP -- \"-\$watchdog_pid\"" \
	"kill -KILL -- \"-\$watchdog_pid\"" \
	'physical block device appeared' \
	'block-backed mount appeared' \
	'IOMMU.*fault|arm-smmu.*fault|context fault|global fault' \
	'registration_safe=1'
do
	grep -Fq "$contract" "$probe" || {
		echo "FAIL attended A660 registration probe omits: $contract" >&2
		exit 1
	}
done

if grep -Eq 'rmmod|modprobe|udevadm|glx|vulkan|drm_info|kmscube|fastboot|adb|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$baseline" "$probe"
then
	echo 'FAIL A660 registration gate can unload, coldplug, open DRM, or write storage' >&2
	exit 1
fi

set +e
"$probe" >/dev/null 2>&1
missing_guard=$?
ALLOW_MAINLINE_A660_REGISTRATION=unsafe "$probe" >/dev/null 2>&1
invalid_guard=$?
set -e
[ "$missing_guard" -ne 0 ]
[ "$invalid_guard" -ne 0 ]

echo 'PASS attended A660 registration gate is manual, no-open, watchdog-bounded, firmware-free, and zero-storage'
