#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
verifier=$repo/scripts/device/verify-mainline-network-root-thermal-pmic-build.sh
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

[[ -f $verifier && ! -L $verifier && -x $verifier ]] ||
	fail 'missing executable thermal-PMIC candidate verifier'

fixture_repo=$work/repo
fixture_verifier=$fixture_repo/scripts/device/verify-mainline-network-root-thermal-pmic-build.sh
output=$work/output
accepted=$fixture_repo/artifacts/network-root-v3/config-7.1.4-network-root
feature=$fixture_repo/configs/kernel/rog5-thermal-pmic-critical.fragment
mkdir -p "$fixture_repo/scripts/device" \
	"$fixture_repo/artifacts/network-root-v3" \
	"$fixture_repo/configs/kernel" "$output/arch/arm64/boot"
cp -- "$verifier" "$fixture_verifier"
cp -- "$repo/artifacts/network-root-v3/config-7.1.4-network-root" "$accepted"
cp -- "$repo/configs/kernel/rog5-thermal-pmic-critical.fragment" "$feature"

printf '%s\n' '#!/bin/sh' 'exit 0' \
	>"$fixture_repo/scripts/device/verify-mainline-network-root-build.sh"
chmod 0755 "$fixture_repo/scripts/device/verify-mainline-network-root-build.sh"

sed 's/^CONFIG_QCOM_SPMI_TEMP_ALARM=m$/CONFIG_QCOM_SPMI_TEMP_ALARM=y/' \
	"$accepted" >"$output/.config"
printf '%s\n' \
	'kernel/drivers/thermal/qcom/qcom-spmi-temp-alarm.ko' \
	>"$output/modules.builtin"
printf '%s\n' 'fake image' >"$output/arch/arm64/boot/Image"
mkdir -p "$work/modules/lib/modules/7.1.4-gfake"
printf '%s\n' 'kernel/fake.ko:' \
	>"$work/modules/lib/modules/7.1.4-gfake/modules.dep"
tar -C "$work/modules" -czf "$output/modules.tar.gz" lib
printf '%s\n' \
	'void qpnp_tm_probe(void) {}' \
	'void qpnp_tm_isr(void) {}' \
	'void qpnp_tm_driver_init(void) {}' \
	'int main(void) { qpnp_tm_probe(); qpnp_tm_isr(); qpnp_tm_driver_init(); return 0; }' \
	>"$work/vmlinux.c"
gcc -o "$output/vmlinux" "$work/vmlinux.c"

feature_sha=$(sha256sum "$feature" | cut -d' ' -f1)
printf 'feature_fragment_sha256=%s\n' "$feature_sha" \
	>"$output/build-meta.txt"
printf '%s\n' \
	'format=rog5-kbuild-inputs-v1' \
	'feature_fragment_path=/workspace/repo/configs/kernel/rog5-thermal-pmic-critical.fragment' \
	"feature_fragment_sha256=$feature_sha" \
	>"$output/.rog5-kbuild-inputs-v1"
chmod 0600 "$output/.rog5-kbuild-inputs-v1"

expect_failure() {
	expected=$1
	shift
	if "$@" >"$work/failure.out" 2>"$work/failure.err"; then
		fail "unexpected success: $*"
	fi
	grep -Fq "$expected" "$work/failure.err" || {
		cat "$work/failure.err" >&2
		fail "wrong refusal; expected: $expected"
	}
}

"$fixture_verifier" "$output" >"$work/pass.out"
for marker in \
	'status=compatible-not-accepted' \
	'hardware_acceptance=unproven' \
	'authority=none'; do
	grep -Fxq "$marker" "$work/pass.out" ||
		fail "candidate verifier omits result marker: $marker"
done

cp -- "$output/.config" "$work/config.good"
printf '%s\n' 'CONFIG_HOSTILE_EXTRA=y' >>"$output/.config"
expect_failure 'candidate config differs beyond the PMIC built-in transition' \
	"$fixture_verifier" "$output"
cp -- "$work/config.good" "$output/.config"

sed -i \
	's/^CONFIG_THERMAL_EMERGENCY_POWEROFF_DELAY_MS=0$/CONFIG_THERMAL_EMERGENCY_POWEROFF_DELAY_MS=10000/' \
	"$output/.config"
expect_failure 'emergency poweroff delay changed before hardware measurement' \
	"$fixture_verifier" "$output"
cp -- "$work/config.good" "$output/.config"

sed -i 's/^CONFIG_QCOM_SPMI_TEMP_ALARM=y$/CONFIG_QCOM_SPMI_TEMP_ALARM=m/' \
	"$output/.config"
expect_failure 'PMIC temperature alarm is not built in' \
	"$fixture_verifier" "$output"
cp -- "$work/config.good" "$output/.config"

cp -- "$output/build-meta.txt" "$work/meta.good"
printf '%s\n' 'feature_fragment_sha256=hostile' >"$output/build-meta.txt"
expect_failure 'feature metadata does not identify the repository fragment' \
	"$fixture_verifier" "$output"
cp -- "$work/meta.good" "$output/build-meta.txt"

cp -- "$output/.rog5-kbuild-inputs-v1" "$work/state.good"
sed -i 's#feature_fragment_path=.*#feature_fragment_path=/tmp/hostile.fragment#' \
	"$output/.rog5-kbuild-inputs-v1"
expect_failure 'build state does not identify the thermal-PMIC feature fragment' \
	"$fixture_verifier" "$output"
cp -- "$work/state.good" "$output/.rog5-kbuild-inputs-v1"
chmod 0600 "$output/.rog5-kbuild-inputs-v1"

cp -- "$output/modules.builtin" "$work/modules.builtin.good"
printf '%s\n' 'kernel/drivers/thermal/qcom/other-driver.ko' \
	>"$output/modules.builtin"
expect_failure 'PMIC temperature-alarm driver is absent from modules.builtin' \
	"$fixture_verifier" "$output"
cp -- "$work/modules.builtin.good" "$output/modules.builtin"

mkdir -p "$work/hostile-modules/lib/modules/7.1.4-gfake/kernel/drivers/thermal/qcom"
printf '%s\n' hostile \
	>"$work/hostile-modules/lib/modules/7.1.4-gfake/kernel/drivers/thermal/qcom/qcom-spmi-temp-alarm.ko"
tar -C "$work/hostile-modules" -czf "$output/modules.tar.gz" lib
expect_failure 'PMIC temperature-alarm driver remains a loadable module' \
	"$fixture_verifier" "$output"
tar -C "$work/modules" -czf "$output/modules.tar.gz" lib

cp -- "$output/vmlinux" "$work/vmlinux.good"
printf '%s\n' 'int main(void) { return 0; }' >"$work/vmlinux-hostile.c"
gcc -o "$output/vmlinux" "$work/vmlinux-hostile.c"
expect_failure 'vmlinux omits built-in PMIC temperature-alarm symbols' \
	"$fixture_verifier" "$output"
cp -- "$work/vmlinux.good" "$output/vmlinux"

echo 'PASS thermal-PMIC candidate verifier proves the one-line built-in transition and rejects hostile artifacts'
