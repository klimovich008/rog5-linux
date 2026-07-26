#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
root=${1:?usage: verify-a660-registration-export.sh ROOT BASE_ROOT}
base_root=${2:-/var/lib/rog5-network-root-v1}
release=7.1.4-rog5-a660reg1
archive_hash=e3cb1ef31b6c1c803bee98748660f92b3b192d460cb41d5d4691f9953a91a42b

for command in cmp cut find grep mktemp modinfo readelf readlink realpath rm \
	sha256sum sort stat wc xargs; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
[[ -d $root && ! -L $root ]] || fail 'candidate export is not a directory'
[[ -d $base_root && ! -L $base_root ]] || fail 'base export is not a directory'
root=$(realpath -e "$root")
base_root=$(realpath -e "$base_root")
[[ $root != / && $base_root != / && $root != "$base_root" ]] ||
	fail 'unsafe or aliased export roots'

"$repo/scripts/host/verify-network-root-export.sh" "$base_root" >/dev/null

seal=$root/etc/rog5/a660-registration-export
[[ -f $seal && ! -L $seal ]]
[[ $(stat -c '%u:%g:%a' "$seal") == 0:0:444 ]]
grep -qx 'base_export=rog5-network-root-v1' "$seal"
grep -qx "kernel_release=$release" "$seal"
grep -qx "module_archive_sha256=$archive_hash" "$seal"
grep -qx 'smmu_acceptance=NOT_ACCEPTED' "$seal"

baseline=$root/usr/local/sbin/rog5-a660-registration-baseline
probe=$root/usr/local/sbin/rog5-a660-registration-probe
cmp "$baseline" \
	"$repo/scripts/device/check-network-root-a660-registration-baseline.sh"
cmp "$probe" "$repo/scripts/device/probe-network-root-a660-registration.sh"
[[ $(stat -c '%u:%g:%a' "$baseline") == 0:0:755 ]]
[[ $(stat -c '%u:%g:%a' "$probe") == 0:0:755 ]]
grep -qx "baseline_sha256=$(sha256sum "$baseline" | cut -d ' ' -f 1)" \
	"$seal"
grep -qx "probe_sha256=$(sha256sum "$probe" | cut -d ' ' -f 1)" \
	"$seal"
grep -qx 'smmu_acceptance_sha=NOT_ACCEPTED' "$probe"

module_root=$root/usr/lib/modules/$release
[[ -d $module_root && ! -L $module_root ]]
[[ $(find "$module_root" -type f -name '*.ko' | wc -l) == 7 ]]
[[ $(stat -c '%u:%g:%a' "$module_root/modules.dep") == 0:0:644 ]]

verify_module() {
	relative=$1
	hash=$2
	name=$3
	depends=$4
	file=$module_root/kernel/$relative
	[[ -f $file && ! -L $file ]]
	[[ $(stat -c '%u:%g:%a' "$file") == 0:0:644 ]]
	[[ $(sha256sum "$file" | cut -d ' ' -f 1) == "$hash" ]]
	[[ $(modinfo -F name "$file") == "$name" ]]
	[[ $(modinfo -F depends "$file") == "$depends" ]]
	[[ $(modinfo -F vermagic "$file") == \
		"$release SMP preempt mod_unload aarch64" ]]
	readelf -S "$file" | grep -Eq '[[:space:]][.]BTF[[:space:]]'
}

verify_module drivers/clk/qcom/gpucc-sm8350.ko \
	c4ec64279bc72ac9d524717512c94a8f5c47eba6a4cf7cadbfbc620012dac563 \
	gpucc_sm8350 ''
verify_module drivers/gpu/drm/drm_exec.ko \
	71c32424623f826bb6b7f217fb84f624721d90e53eb89cc9d205af66aca9f886 \
	drm_exec ''
verify_module drivers/gpu/drm/drm_gpuvm.ko \
	981d3f322e18c3b815de7dcba0f829d2ca36f25c85347bb233e7e1baa73386f8 \
	drm_gpuvm drm_exec
verify_module drivers/gpu/drm/scheduler/gpu-sched.ko \
	f53fba10fe10cfeca45abc6d808ca2f5a116832b9595de8f09af66206204b1f4 \
	gpu_sched ''
verify_module drivers/soc/qcom/mdt_loader.ko \
	001c1526eef5526b35663e9d3d16621e07949e3adc0ca4aa4ddd5f1f7a4e4be3 \
	mdt_loader ''
verify_module drivers/soc/qcom/ubwc_config.ko \
	4220552fbf17562128c956c3cfdbb8abd22e26f2c6a7f22e94422ef34b10e587 \
	ubwc_config ''
verify_module drivers/gpu/drm/msm/msm.ko \
	f7c69c399dea567ad8a1f0ecc10c61259dd76052230f61ae69165c711e24ac24 \
	msm 'drm_exec,drm_gpuvm,gpu-sched,mdt_loader,ubwc_config'

[[ $(grep -Ec '^[^:]+:[^:]*$' "$module_root/modules.dep") == 7 ]]
grep -Fxq \
	'kernel/drivers/gpu/drm/drm_gpuvm.ko: kernel/drivers/gpu/drm/drm_exec.ko' \
	"$module_root/modules.dep"
grep -Fxq \
	'kernel/drivers/gpu/drm/msm/msm.ko: kernel/drivers/gpu/drm/drm_exec.ko kernel/drivers/gpu/drm/drm_gpuvm.ko kernel/drivers/gpu/drm/scheduler/gpu-sched.ko kernel/drivers/soc/qcom/mdt_loader.ko kernel/drivers/soc/qcom/ubwc_config.ko' \
	"$module_root/modules.dep"

firmware_files=$(find "$root/usr/lib/firmware" -type f \
	\( -name a660_sqe.fw -o -name a660_gmu.bin -o -name a660_zap.mbn \) \
	-print)
[[ -z $firmware_files ]] || fail 'A660 firmware remains in candidate export'

for relative in \
	root/.ssh/authorized_keys \
	home/rog5/.ssh/authorized_keys \
	etc/ssh/ssh_host_ed25519_key \
	etc/ssh/ssh_host_ed25519_key.pub
do
	cmp "$root/$relative" "$base_root/$relative"
	[[ $(stat -c '%u:%g:%a' "$root/$relative") == \
		"$(stat -c '%u:%g:%a' "$base_root/$relative")" ]]
done

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
unchanged_manifest() {
	tree=$1
	find "$tree" -xdev \
		! -path "$tree/etc/rog5" \
		! -path "$tree/usr/lib/firmware/qcom/a660_sqe.fw" \
		! -path "$tree/usr/lib/firmware/qcom/a660_gmu.bin" \
		! -path "$tree/usr/lib/firmware/qcom/sm8350/a660_zap.mbn" \
		! -path "$tree/usr/lib/firmware/qcom" \
		! -path "$tree/usr/lib/firmware/qcom/sm8350" \
		! -path "$tree/usr/lib/modules" \
		! -path "$tree/usr/lib/modules/$release" \
		! -path "$tree/usr/lib/modules/$release/*" \
		! -path "$tree/usr/local/sbin" \
		! -path "$tree/usr/local/sbin/rog5-a660-registration-baseline" \
		! -path "$tree/usr/local/sbin/rog5-a660-registration-probe" \
		! -path "$tree/etc/rog5/a660-registration-export" \
		-printf '%P|%y|%m|%U|%G|%s|%l\n' | sort
}
unchanged_manifest "$base_root" >"$work/base.metadata"
unchanged_manifest "$root" >"$work/candidate.metadata"
cmp "$work/base.metadata" "$work/candidate.metadata"

unchanged_hashes() {
	tree=$1
	(
		cd "$tree"
		find . -xdev -type f \
			! -path './usr/lib/firmware/qcom/a660_sqe.fw' \
			! -path './usr/lib/firmware/qcom/a660_gmu.bin' \
			! -path './usr/lib/firmware/qcom/sm8350/a660_zap.mbn' \
			! -path "./usr/lib/modules/$release/*" \
			! -path './usr/local/sbin/rog5-a660-registration-baseline' \
			! -path './usr/local/sbin/rog5-a660-registration-probe' \
			! -path './etc/rog5/a660-registration-export' \
			-print0 | sort -z | xargs -0 sha256sum
	)
}
unchanged_hashes "$base_root" >"$work/base.sha256"
unchanged_hashes "$root" >"$work/candidate.sha256"
cmp "$work/base.sha256" "$work/candidate.sha256"

echo "PASS source-locked A660 registration export modules=7 firmware=0 credentials=preserved base=unchanged"
