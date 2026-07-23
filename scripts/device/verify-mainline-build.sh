#!/bin/sh
set -eu

output_dir=${OUTPUT_DIR:-/root/build/rog5-linux-7.1.4}
expected_commit=${LINUX_COMMIT:-7a5cef0db4795d9d453a12e0f61b5b7634fc4d40}
meta="$output_dir/build-meta.txt"
image="$output_dir/arch/arm64/boot/Image.gz"
modules="$output_dir/modules.tar.gz"

[ -r "$meta" ] || { echo "FAIL missing $meta" >&2; exit 1; }
grep -qx "kernel_commit=$expected_commit" "$meta" || { echo 'FAIL wrong build commit' >&2; exit 1; }
[ -s "$image" ] || { echo 'FAIL missing Image.gz' >&2; exit 1; }
gzip -t "$image"
[ -s "$modules" ] || { echo 'FAIL missing modules.tar.gz' >&2; exit 1; }
tar -tzf "$modules" | grep -q '/ath11k.ko$' || { echo 'FAIL ath11k module missing' >&2; exit 1; }
tar -tzf "$modules" | grep -q '/ath11k_pci.ko$' || { echo 'FAIL ath11k PCI module missing' >&2; exit 1; }
tar -tzf "$modules" | grep -q '/modules.dep$' || { echo 'FAIL module dependency metadata missing' >&2; exit 1; }

hash_lines=$(grep '  /' "$meta")
[ -n "$hash_lines" ] || { echo 'FAIL no artifact hashes' >&2; exit 1; }
printf '%s\n' "$hash_lines" | sha256sum -c -

dtb_count=0
for dtb in "$output_dir"/arch/arm64/boot/dts/qcom/sm8350-*.dtb; do
    [ -s "$dtb" ] || continue
    dtc -q -I dtb -O dts -o /dev/null "$dtb"
    dtb_count=$((dtb_count + 1))
done
[ "$dtb_count" -eq 5 ] || { echo "FAIL expected 5 comparison DTBs, found $dtb_count" >&2; exit 1; }

for symbol in \
    CONFIG_ARCH_QCOM=y \
    CONFIG_SCSI_UFS_QCOM=y \
    CONFIG_USB_CONFIGFS_NCM=y \
    CONFIG_DRM_MSM=y \
    CONFIG_DEBUG_INFO_BTF=y \
    CONFIG_BPF_SYSCALL=y \
    CONFIG_WIREGUARD=y \
    CONFIG_NF_TABLES=y \
    CONFIG_NFT_MASQ=y \
    CONFIG_IP_MULTIPLE_TABLES=y \
    CONFIG_IPV6_MULTIPLE_TABLES=y; do
    grep -qx "$symbol" "$output_dir/.config" || { echo "FAIL final config: $symbol" >&2; exit 1; }
done

echo 'PASS compile-only Image.gz, hashes, final config, and five upstream SM8350 DTBs'
