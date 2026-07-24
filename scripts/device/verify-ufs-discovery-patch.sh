#!/bin/sh
set -eu

source_dir=${1:?usage: verify-ufs-discovery-patch.sh PINNED_LINUX_SOURCE}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch_dir=$repo/patches/linux-7.1.4
base_fragment=$repo/configs/kernel/rog5-mainline.fragment
discovery_fragment=$repo/configs/kernel/rog5-ufs-discovery.fragment
expected_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40

[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_commit" ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]
[ -r "$base_fragment" ] && [ -r "$discovery_fragment" ]

patches=$(find "$patch_dir" -maxdepth 1 -type f -name '*.patch' -print | sort)
[ "$(printf '%s\n' "$patches" | awk 'NF { count++ } END { print count + 0 }')" -eq 3 ] || {
	echo 'FAIL expected exactly three Linux 7.1.4 discovery patches' >&2
	exit 1
}

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM
git clone -q --no-hardlinks "$source_dir" "$stage/linux"
git -C "$stage/linux" checkout -q --detach "$expected_commit"
for patch in $patches; do
	git -C "$stage/linux" apply --check "$patch"
	git -C "$stage/linux" apply "$patch"
done
git -C "$stage/linux" diff --check

actual_files=$stage/actual-files
expected_files=$stage/expected-files
git -C "$stage/linux" diff --name-only | sort >"$actual_files"
cat >"$expected_files" <<'EOF'
drivers/scsi/sd.c
drivers/ufs/core/Kconfig
drivers/ufs/core/ufshcd.c
EOF
cmp "$actual_files" "$expected_files"

grep -q '^config SCSI_UFS_DISCOVERY_READ_ONLY$' "$stage/linux/drivers/ufs/core/Kconfig"
grep -Fq 'ROG5 UFS discovery: forced read-only before registration' \
	"$stage/linux/drivers/scsi/sd.c"
grep -Fq 'ROG5 UFS discovery: blocked SCSI opcode' \
	"$stage/linux/drivers/ufs/core/ufshcd.c"
grep -Fq 'ROG5 UFS discovery: blocked device query' \
	"$stage/linux/drivers/ufs/core/ufshcd.c"
grep -Fq 'ROG5 UFS discovery: auto-hibern8 disabled; link remains active' \
	"$stage/linux/drivers/ufs/core/ufshcd.c"
grep -Fq 'ROG5 UFS discovery: host runtime PM forbidden; active reference retained' \
	"$stage/linux/drivers/ufs/core/ufshcd.c"
grep -Fq 'ROG5 UFS discovery: WL power transition rejected' \
	"$stage/linux/drivers/ufs/core/ufshcd.c"
grep -Fq 'ROG5 UFS discovery: host power transition rejected' \
	"$stage/linux/drivers/ufs/core/ufshcd.c"
grep -Fq 'ROG5 UFS discovery: shutdown power transition skipped' \
	"$stage/linux/drivers/ufs/core/ufshcd.c"
grep -Fq 'ROG5 UFS discovery: WLUN runtime PM forbidden' \
	"$stage/linux/drivers/ufs/core/ufshcd.c"
grep -Fq 'QUERY_FLAG_IDN_FDEVICEINIT' "$stage/linux/drivers/ufs/core/ufshcd.c"
grep -Fq 'QUERY_FLAG_IDN_FDEVICEINIT && !index && !selector' \
	"$stage/linux/drivers/ufs/core/ufshcd.c"
grep -Fq 'cmd->sc_data_direction == DMA_TO_DEVICE' \
	"$stage/linux/drivers/ufs/core/ufshcd.c"
grep -Fq 'cmd->sc_data_direction == DMA_BIDIRECTIONAL' \
	"$stage/linux/drivers/ufs/core/ufshcd.c"
! grep -Fq 'case START_STOP:' "$stage/linux/drivers/ufs/core/ufshcd.c"
grep -Fq 'CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY' "$stage/linux/drivers/ufs/core/ufshcd.c"
[ "$(grep -c '^[[:space:]]*cmd = ufshcd_get_dev_mgmt_cmd(hba);' \
	"$stage/linux/drivers/ufs/core/ufshcd.c")" -ge 2 ]
! grep -Fq 'struct scsi_cmnd *cmd = ufshcd_get_dev_mgmt_cmd(hba);' \
	"$stage/linux/drivers/ufs/core/ufshcd.c"

assert_before() {
	file=$1
	earlier=$2
	later=$3
	earlier_line=$(grep -nF "$earlier" "$file" | head -1 | cut -d: -f1)
	later_line=$(grep -nF "$later" "$file" | head -1 | cut -d: -f1)
	[ -n "$earlier_line" ] && [ -n "$later_line" ]
	[ "$earlier_line" -lt "$later_line" ]
}

core=$stage/linux/drivers/ufs/core/ufshcd.c
sed -n '/^static int __ufshcd_wl_suspend(/,/^}/p' "$core" \
	>"$stage/wl-suspend"
assert_before "$stage/wl-suspend" \
	'ROG5 UFS discovery: WL power transition rejected' \
	'hba->pm_op_in_progress = true;'
grep -Fq 'return -EBUSY;' "$stage/wl-suspend"

sed -n '/^static int ufshcd_suspend(/,/^}/p' "$core" \
	>"$stage/host-suspend"
assert_before "$stage/host-suspend" \
	'ROG5 UFS discovery: host power transition rejected' \
	'if (!hba->is_powered)'
grep -Fq 'return -EBUSY;' "$stage/host-suspend"

sed -n '/^static void ufshcd_wl_shutdown(/,/^}/p' "$core" \
	>"$stage/wl-shutdown"
assert_before "$stage/wl-shutdown" \
	'ROG5 UFS discovery: shutdown power transition skipped' \
	'ufshcd_rpm_get_sync(hba);'
grep -Fq 'return;' "$stage/wl-shutdown"

sed -n '/^static void ufshcd_async_scan(/,/^}/p' "$core" \
	>"$stage/async-scan"
grep -Fq 'pm_runtime_forbid(hba->dev);' "$stage/async-scan"
grep -Fq 'ROG5 UFS discovery: host runtime PM forbidden; active reference retained' \
	"$stage/async-scan"
grep -Fq '} else {' "$stage/async-scan"
[ "$(grep -Fc 'pm_runtime_put_sync(hba->dev);' "$stage/async-scan")" -eq 1 ]

sed -n '/^static int ufshcd_wl_probe(/,/^}/p' "$core" \
	>"$stage/wl-probe"
grep -Fq 'pm_runtime_forbid(dev);' "$stage/wl-probe"
grep -Fq 'ROG5 UFS discovery: WLUN runtime PM forbidden' "$stage/wl-probe"
grep -Fq '} else {' "$stage/wl-probe"
[ "$(grep -Fc 'pm_runtime_allow(dev);' "$stage/wl-probe")" -eq 1 ]

sed -n '/^static bool ufshcd_discovery_query_allowed(/,/^}/p' \
	"$stage/linux/drivers/ufs/core/ufshcd.c" |
	sed -n 's/^[[:space:]]*case \([^:]*\):.*/\1/p' >"$stage/query-cases"
cat >"$stage/expected-query-cases" <<'EOF'
UPIU_QUERY_OPCODE_READ_DESC
UPIU_QUERY_OPCODE_READ_ATTR
UPIU_QUERY_OPCODE_READ_FLAG
UPIU_QUERY_OPCODE_SET_FLAG
EOF
cmp "$stage/query-cases" "$stage/expected-query-cases"

sed -n '/^static bool ufshcd_discovery_scsi_allowed(/,/^}/p' \
	"$stage/linux/drivers/ufs/core/ufshcd.c" |
	sed -n 's/^[[:space:]]*case \([^:]*\):.*/\1/p' >"$stage/scsi-cases"
cat >"$stage/expected-scsi-cases" <<'EOF'
TEST_UNIT_READY
REQUEST_SENSE
INQUIRY
MODE_SENSE
MODE_SENSE_10
READ_FORMAT_CAPACITIES
READ_CAPACITY
READ_6
READ_10
READ_12
READ_16
REPORT_LUNS
SECURITY_PROTOCOL_IN
LOG_SENSE
SERVICE_ACTION_IN_16
ZBC_IN
EOF
cmp "$stage/scsi-cases" "$stage/expected-scsi-cases"

make -s -C "$stage/linux" O="$stage/build" ARCH=arm64 LLVM=1 defconfig
"$stage/linux/scripts/kconfig/merge_config.sh" -m -O "$stage/build" \
	"$stage/build/.config" "$base_fragment" "$discovery_fragment" >/dev/null
make -s -C "$stage/linux" O="$stage/build" ARCH=arm64 LLVM=1 olddefconfig
for symbol in \
	CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y \
	CONFIG_SCSI=y \
	CONFIG_SCSI_UFSHCD=y \
	CONFIG_SCSI_UFSHCD_PLATFORM=y \
	CONFIG_SCSI_UFS_QCOM=y \
	CONFIG_PHY_QCOM_QMP=y \
	CONFIG_PHY_QCOM_QMP_UFS=y \
	CONFIG_BLK_DEV_SD=y \
	CONFIG_EFI_PARTITION=y \
	CONFIG_PINCTRL_SM8350=y \
	CONFIG_REGULATOR_QCOM_RPMH=y \
	CONFIG_INTERCONNECT_QCOM_SM8350=y \
	CONFIG_QCOM_COMMAND_DB=y \
	CONFIG_QCOM_RPMH=y \
	CONFIG_RESET_QCOM_AOSS=y \
	CONFIG_USB=y \
	CONFIG_USB_DWC3=y \
	CONFIG_USB_DWC3_QCOM=y \
	CONFIG_USB_GADGET=y \
	CONFIG_USB_CONFIGFS=y \
	CONFIG_USB_CONFIGFS_ACM=y \
	CONFIG_USB_CONFIGFS_NCM=y \
	CONFIG_PHY_QCOM_USB_SNPS_FEMTO_V2=y \
	CONFIG_IKCONFIG=y \
	CONFIG_IKCONFIG_PROC=y; do
	grep -qx "$symbol" "$stage/build/.config"
done
for symbol in \
	CHR_DEV_SG BLK_DEV_BSG SCSI_UFS_BSG RPMB SCSI_UFS_CRYPTO \
	SCSI_UFS_HWMON PHY_QCOM_QMP_COMBO PHY_QCOM_QMP_PCIE \
	PHY_QCOM_QMP_PCIE_8996 PHY_QCOM_QMP_USB PHY_QCOM_QMP_USB_LEGACY; do
	grep -qx "# CONFIG_$symbol is not set" "$stage/build/.config"
done

make -s -C "$stage/linux" O="$stage/build" ARCH=arm64 LLVM=1 -j "${JOBS:-2}" \
	drivers/scsi/sd.o drivers/ufs/core/ufshcd.o

echo 'PASS Linux 7.1.4 discovery patch applies cleanly and guarded objects compile'
