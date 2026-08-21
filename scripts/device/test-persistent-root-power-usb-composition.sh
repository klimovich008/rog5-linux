#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
checker=$repo/scripts/device/check-persistent-root-power-usb-composition.sh
builder=$repo/scripts/device/build-mainline-persistent-root.sh
composed_builder=$repo/scripts/device/build-mainline-persistent-root-power-usb.sh
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM

"$checker" >/dev/null

bad=$stage/v26
mkdir -p "$bad/lib/modules/7.1.4-g7a5cef0db479"
cp "$repo/artifacts/persistent-root-p2/config-7.1.4-persistent-root" \
	"$stage/writable.config"
sed -i 's/^CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y$/# CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY is not set/' \
	"$stage/writable.config"
if ROG5_COMPOSED_MODULE_ROOT="$bad" "$checker" \
	>"$stage/out" 2>"$stage/err"; then
	echo 'FAIL composition checker accepted V26 ABI modules' >&2
	exit 1
fi
grep -Fq 'V26 ABI modules cannot be reused' "$stage/err"

if ROG5_COMPOSED_CONFIG="$stage/writable.config" "$checker" \
	>"$stage/out" 2>"$stage/err"; then
	echo 'FAIL composition checker accepted a config without read-only UFS' >&2
	exit 1
fi
grep -Fq 'kernel config lacks CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y' "$stage/err"

for symbol in CONFIG_BATTERY_QCOM_BATTMGR=m CONFIG_UCSI_PMIC_GLINK=m \
	CONFIG_QCOM_Q6V5_PAS=m CONFIG_QCOM_PMIC_GLINK=m; do
	grep -Fqx "$symbol" \
		"$repo/configs/kernel/rog5-persistent-root-power-usb.fragment"
done

for exact in \
	'POWER_USB_MODULES=1' \
	'DISCOVERY_FRAGMENT="$repo/configs/kernel/rog5-ufs-deferred-probe.fragment"' \
	'LINUX_COMMIT=ae717d919f87b47ea9ed2173ea96660186b62a66' \
	'LINUX_TREE=939729426dcfa3bd72c75d81c0a675c6f0a193da' \
	'EXPECTED_RELEASE=7.1.4-gae717d919f87' \
	'ROG5_COMPOSED_MODULE_ROOT="$output_dir/power-usb-modules"'; do
	grep -Fq "$exact" "$composed_builder"
done
[ "$(grep -Fc '.ko \' "$builder")" -ge 14 ]
grep -Fq "[ \"\$(wc -l <\"\$closure\")\" -eq 15 ]" "$builder"
grep -Fq 'power_usb_modules=%s' "$builder"
grep -Fq 'llvm-objcopy --remove-section=.BTF' "$builder"
grep -Fq 'composed PDR module retains rejected BTF' "$checker"
if POWER_USB_MODULES=2 "$builder" >"$stage/out" 2>"$stage/err"; then
	echo 'FAIL persistent-root builder accepted invalid power/USB mode' >&2
	exit 1
fi
grep -Fq 'POWER_USB_MODULES must be 0 or 1' "$stage/err"

echo 'PASS composition contract pins ae717, read-only UFS, charging symbols, and rejects V26 ABI reuse'
