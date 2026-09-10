#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-network-root-gpucc-diagnostic-bundle.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256 GPUCC_MODULE GPUCC_SHA256}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing SHA-256 manifest}
gpucc_module=${5:?missing GPUCC diagnostic module}
gpucc_sha=${6:?missing GPUCC diagnostic module SHA-256}
expected_gpucc_sha=5f7018e53eb576579fe8d199171ae6e17c4e9d31ad099a330d21e050c0ad4454
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)

"$repo/scripts/device/verify-network-root-bundle.sh" \
	"$artifact_dir" "$mkbootimg_dir" "$avbtool" "$expected_sums" okay

case $gpucc_sha in
	*[!0-9a-f]*|'') echo 'FAIL invalid GPUCC module hash' >&2; exit 1 ;;
esac
[ "${#gpucc_sha}" -eq 64 ]
[ "$gpucc_sha" = "$expected_gpucc_sha" ] || {
	echo 'FAIL GPUCC module hash is not the reviewed diagnostic build' >&2
	exit 1
}
[ -f "$gpucc_module" ] && [ ! -L "$gpucc_module" ]
[ "$(sha256sum "$gpucc_module" | cut -d ' ' -f 1)" = "$gpucc_sha" ]
[ "$(modinfo -F name "$gpucc_module")" = gpucc_sm8350 ]
[ -z "$(modinfo -F depends "$gpucc_module")" ]
[ "$(modinfo -F vermagic "$gpucc_module")" = \
	'7.1.4-g7a5cef0db479 SMP preempt mod_unload aarch64' ]
modinfo -p "$gpucc_module" |
	grep -Fxq \
	'probe_trace:Emit progress notices for attended SM8350 GPUCC diagnostics (bool)'

dtb=$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb
gpucc=/soc@0/clock-controller@3d90000
[ "$(fdtget -t s "$dtb" "$gpucc" status)" = okay ]
[ "$(fdtget -t s "$dtb" "$gpucc" compatible)" = qcom,sm8350-gpucc ]
[ "$(fdtget -t x "$dtb" "$gpucc" reg)" = '0 3d90000 0 9000' ]
for node in \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000 \
	/soc@0/iommu@3da0000 \
	/soc@0/remoteproc@3000000 \
	/soc@0/remoteproc@4080000 \
	/soc@0/remoteproc@5c00000 \
	/soc@0/remoteproc@a300000
do
	[ "$(fdtget -t s "$dtb" "$node" status)" = disabled ]
done

config=$artifact_dir/config-7.1.4-network-root
grep -qx 'CONFIG_SM_GPUCC_8350=m' "$config"
grep -qx 'CONFIG_DRM_MSM=y' "$config"
grep -qx 'CONFIG_ARM_SMMU=y' "$config"

modules=$artifact_dir/modules-7.1.4-network-root.tar.gz
module_path=$(tar -tzf "$modules" | grep -E '/gpucc-sm8350[.]ko$')
[ "$(printf '%s\n' "$module_path" | wc -l)" -eq 1 ]
[ "$(tar -xOzf "$modules" "$module_path" | sha256sum |
	cut -d ' ' -f 1)" = \
	73b419cc0b2adee00a0d2da8caa0d1292c629804b91ca629a973438653ad6717 ]
[ "$gpucc_sha" != \
	73b419cc0b2adee00a0d2da8caa0d1292c629804b91ca629a973438653ad6717 ]

for archive in \
	"$artifact_dir/rog5-network-root-initramfs.cpio.gz" \
	"$artifact_dir/rog5-network-root-kexec-stage-initramfs.cpio.gz"
do
	listing=$(gzip -dc "$archive" | cpio -t 2>/dev/null)
	! printf '%s\n' "$listing" |
		grep -Eq '(^|/)(gpucc-sm8350[.]ko|a660_sqe[.]fw|a660_gmu[.]bin|a660_zap[.]mbn)$'
done

echo 'PASS GPUCC-only bundle; traced module remains an external tmpfs input and every GPU consumer stays disabled'
