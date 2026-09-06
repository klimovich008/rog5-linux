#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

output_dir=${1:?usage: verify-mainline-network-root-thermal-pmic-build.sh BUILD_DIR}
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd -P)
base_verifier=$repo/scripts/device/verify-mainline-network-root-build.sh
accepted_config=$repo/artifacts/network-root-v3/config-7.1.4-network-root
feature_fragment=$repo/configs/kernel/rog5-thermal-pmic-critical.fragment
config=$output_dir/.config
meta=$output_dir/build-meta.txt
state=$output_dir/.rog5-kbuild-inputs-v1
modules_builtin=$output_dir/modules.builtin
modules=$output_dir/modules.tar.gz
vmlinux=$output_dir/vmlinux
work=$(mktemp -d)
trap 'rm -rf -- "$work"' 0 HUP INT TERM

for file in "$base_verifier" "$accepted_config" "$feature_fragment" \
	"$config" "$meta" "$state" "$modules_builtin" "$modules" "$vmlinux"; do
	[ -f "$file" ] && [ ! -L "$file" ] && [ -r "$file" ] ||
		fail "unsafe or missing candidate input: $file"
done
[ -x "$base_verifier" ] || fail 'base network-root verifier is not executable'
[ -s "$config" ] && [ -s "$meta" ] && [ -s "$state" ] &&
	[ -s "$modules_builtin" ] && [ -s "$modules" ] && [ -s "$vmlinux" ] ||
	fail 'thermal-PMIC candidate contains an empty required artifact'

"$base_verifier" "$output_dir"

[ "$(grep -Fxc 'CONFIG_QCOM_SPMI_TEMP_ALARM=y' "$config")" -eq 1 ] ||
	fail 'PMIC temperature alarm is not built in'
[ "$(grep -Fxc 'CONFIG_THERMAL_EMERGENCY_POWEROFF_DELAY_MS=0' "$config")" -eq 1 ] ||
	fail 'emergency poweroff delay changed before hardware measurement'
sed 's/^CONFIG_QCOM_SPMI_TEMP_ALARM=y$/CONFIG_QCOM_SPMI_TEMP_ALARM=m/' \
	"$config" >"$work/baseline-normalized.config"
cmp -s "$accepted_config" "$work/baseline-normalized.config" ||
	fail 'candidate config differs beyond the PMIC built-in transition'

feature_sha256=$(sha256sum "$feature_fragment" | cut -d ' ' -f 1)
meta_feature=$(sed -n 's/^feature_fragment_sha256=//p' "$meta")
[ "$(printf '%s\n' "$meta_feature" | awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] &&
	[ "$meta_feature" = "$feature_sha256" ] ||
	fail 'feature metadata does not identify the repository fragment'
state_feature=$(sed -n 's/^feature_fragment_sha256=//p' "$state")
[ "$(printf '%s\n' "$state_feature" | awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] &&
	[ "$state_feature" = "$feature_sha256" ] ||
	fail 'build state does not identify the thermal-PMIC feature fragment'
state_path=$(sed -n 's/^feature_fragment_path=//p' "$state")
[ "$(printf '%s\n' "$state_path" | awk 'NF { count++ } END { print count + 0 }')" -eq 1 ] ||
	fail 'build state does not identify the thermal-PMIC feature fragment'
case $state_path in
	*/configs/kernel/rog5-thermal-pmic-critical.fragment) ;;
	*) fail 'build state does not identify the thermal-PMIC feature fragment' ;;
esac

grep -Fxq 'kernel/drivers/thermal/qcom/qcom-spmi-temp-alarm.ko' \
	"$modules_builtin" ||
	fail 'PMIC temperature-alarm driver is absent from modules.builtin'
tar -tzf "$modules" >"$work/modules.list" ||
	fail 'candidate module archive is invalid'
if grep -Eq '/qcom-spmi-temp-alarm\.ko$' "$work/modules.list"; then
	fail 'PMIC temperature-alarm driver remains a loadable module'
fi

nm "$vmlinux" >"$work/vmlinux.nm" || fail 'cannot inspect candidate vmlinux'
for symbol in qpnp_tm_probe qpnp_tm_isr qpnp_tm_driver_init; do
	grep -Eq "[[:space:]][A-Za-z] ${symbol}$" "$work/vmlinux.nm" ||
		fail 'vmlinux omits built-in PMIC temperature-alarm symbols'
done

printf '%s\n' \
	'status=compatible-not-accepted' \
	'hardware_acceptance=unproven' \
	'authority=none'
echo 'PASS network-root thermal-PMIC driver is a compile-only built-in candidate'
