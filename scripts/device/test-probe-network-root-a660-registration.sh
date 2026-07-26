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
	'7.1.4-rog5-a660reg1' \
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
	'registration module set is not exact' \
	'thermal_count'
do
	grep -Fq "$contract" "$baseline" || {
		echo "FAIL A660 registration baseline omits: $contract" >&2
		exit 1
	}
done

for contract in \
	'ALLOW_MAINLINE_A660_REGISTRATION' \
	'smmu_acceptance_sha=NOT_ACCEPTED' \
	'/run/rog5-adreno-smmu-live.accepted' \
	'7.1.4-rog5-a660reg1' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'gpucc-sm8350.ko' \
	'msm.ko' \
	c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563 \
	71c32424623f826bb6b7f217fb84f624721d90e53eb89cc9d205af66aca9f886 \
	981d3f322e18c3b815de7dcba0f829d2ca36f25c85347bb233e7e1baa73386f8 \
	f53fba10fe10cfeca45abc6d808ca2f5a116832b9595de8f09af66206204b1f4 \
	001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3 \
	4220552fbf17562128c956c3cfdbb8abd22e26f2c6a7f22e94422ef34b10e587 \
	f7c69c399dea567ad8a1f0ecc10c61259dd76052230f61ae69165c711e24ac24 \
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

if grep -Eq '(^|[;&|[:space:]])(rmmod|modprobe|udevadm|glx|vulkan|drm_info|kmscube|fastboot|adb)([[:space:]]|$)|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
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

watchdog_line=$(grep -n 'setsid sh -c' "$probe" | cut -d: -f1)
# The module variables are intentionally matched as source literals.
# shellcheck disable=SC2016
gpucc_line=$(grep -n 'insmod "$gpucc_module" probe_trace=1' "$probe" |
	cut -d: -f1)
# shellcheck disable=SC2016
msm_line=$(grep -n 'insmod "$msm_module" separate_gpu_kms=1' "$probe" |
	cut -d: -f1)
fd_line=$(grep -n '^check_no_drm_fds ||' "$probe" | head -n 1 |
	cut -d: -f1)
safe_line=$(grep -n '^registration_safe=1$' "$probe" | cut -d: -f1)
[ "$watchdog_line" -lt "$gpucc_line" ]
[ "$gpucc_line" -lt "$msm_line" ]
[ "$msm_line" -lt "$fd_line" ]
[ "$fd_line" -lt "$safe_line" ]
[ "$(grep -Ec '^[[:space:]]*(if ! )?insmod ' "$probe")" -eq 7 ]
[ "$(grep -c '^smmu_acceptance_sha=NOT_ACCEPTED$' "$probe")" -eq 1 ]

if [ -n "${BUILD_DIR:-}" ]; then
	[ -d "$BUILD_DIR" ]
	check_module() {
		file=$BUILD_DIR/$1
		hash=$2
		name=$3
		[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$hash" ]
		[ "$(modinfo -F name "$file")" = "$name" ]
		[ "$(modinfo -F vermagic "$file")" = \
			'7.1.4-rog5-a660reg1 SMP preempt mod_unload aarch64' ]
	}
	check_module drivers/clk/qcom/gpucc-sm8350.ko \
		c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563 \
		gpucc_sm8350
	check_module drivers/gpu/drm/drm_exec.ko \
		71c32424623f826bb6b7f217fb84f624721d90e53eb89cc9d205af66aca9f886 \
		drm_exec
	check_module drivers/gpu/drm/drm_gpuvm.ko \
		981d3f322e18c3b815de7dcba0f829d2ca36f25c85347bb233e7e1baa73386f8 \
		drm_gpuvm
	check_module drivers/gpu/drm/scheduler/gpu-sched.ko \
		f53fba10fe10cfeca45abc6d808ca2f5a116832b9595de8f09af66206204b1f4 \
		gpu_sched
	check_module drivers/soc/qcom/mdt_loader.ko \
		001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3 \
		mdt_loader
	check_module drivers/soc/qcom/ubwc_config.ko \
		4220552fbf17562128c956c3cfdbb8abd22e26f2c6a7f22e94422ef34b10e587 \
		ubwc_config
	check_module drivers/gpu/drm/msm/msm.ko \
		f7c69c399dea567ad8a1f0ecc10c61259dd76052230f61ae69165c711e24ac24 \
		msm
	[ "$(modinfo -F depends \
		"$BUILD_DIR/drivers/gpu/drm/msm/msm.ko")" = \
		'drm_exec,drm_gpuvm,gpu-sched,mdt_loader,ubwc_config' ]
fi

echo 'PASS attended A660 registration gate is SMMU-locked, manual, no-open, watchdog-bounded, firmware-free, and zero-storage'
