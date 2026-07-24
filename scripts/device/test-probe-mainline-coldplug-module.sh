#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
probe=$repo/scripts/device/probe-mainline-coldplug-module.sh

[ -x "$probe" ] || {
	echo "FAIL missing executable coldplug probe: $probe" >&2
	exit 1
}
sh -n "$probe"

modules='
authenc
gpucc_sm8350
libdes
nvmem_qcom_spmi_sdam
nvmem_reboot_mode
pinctrl_lpass_lpi
pinctrl_sc7280_lpass_lpi
qcom_pon
qcom_refgen_regulator
qcom_rng
qcom_spmi_adc5
qcom_spmi_temp_alarm
qcom_stats
qcom_vadc_common
qcomtee
qcrypto
rmtfs_mem
sha1
sha256
socinfo
'
for module in $modules; do
	grep -Fq "$module" "$probe" || {
		echo "FAIL coldplug allowlist omits $module" >&2
		exit 1
	}
done
[ "$(printf '%s\n' "$modules" | awk 'NF { count++ } END { print count }')" -eq 20 ]

for contract in \
	'ALLOW_MAINLINE_COLDPLUG_PROBE' \
	'7.1.4-g7a5cef0db479' \
	'systemd-udev-trigger.service' \
	'systemd-modules-load.service' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'findmnt -n -o SOURCE /.rog5/root-ro' \
	'169.254.77.1:/' \
	'physical block device is present' \
	'block-backed mount is present' \
	'/sys/class/net/usb0/carrier' \
	'exec 9>/proc/sysrq-trigger' \
	'echo b >&9' \
	'setsid sh -c' \
	'</dev/null >/dev/null 2>&1 &' \
	'kill -STOP -- "-$watchdog_pid"' \
	'kill -KILL -- "-$watchdog_pid"' \
	'dependency_parent=' \
	'modprobe --first-time "$module"' \
	'rog5-coldplug-probe: begin module=$module' \
	'rog5-coldplug-probe: modprobe returned module=$module' \
	'Kernel panic|Oops:|BUG:' \
	'starting|initializing' \
	'EVIDENCE thermal_zones_begin' \
	'EVIDENCE new_dmesg_begin' \
	'probe_safe=1' \
	'watchdog was disarmed'; do
	grep -Fq "$contract" "$probe" || {
		echo "FAIL coldplug probe contract missing: $contract" >&2
		exit 1
	}
done

guard_line=$(grep -n 'ALLOW_MAINLINE_COLDPLUG_PROBE' "$probe" |
	head -n1 | cut -d: -f1)
watchdog_line=$(grep -n '^setsid sh -c' "$probe" | cut -d: -f1)
module_line=$(grep -n '^modprobe --first-time ' "$probe" | cut -d: -f1)
settle_line=$(grep -n '^sleep "\$settle_seconds"' "$probe" | cut -d: -f1)
safe_line=$(grep -n '^probe_safe=1$' "$probe" | cut -d: -f1)
[ "$guard_line" -lt "$watchdog_line" ]
[ "$watchdog_line" -lt "$module_line" ]
[ "$module_line" -lt "$settle_line" ]
[ "$settle_line" -lt "$safe_line" ]

if grep -Eq 'rmmod|modprobe[[:space:]].*(-r|--remove)|fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/' \
	"$probe"; then
	echo 'FAIL coldplug probe unloads a driver or writes persistent storage' >&2
	exit 1
fi

set +e
"$probe" socinfo >/dev/null 2>&1
missing_guard=$?
ALLOW_MAINLINE_COLDPLUG_PROBE=1 "$probe" not-reviewed >/dev/null 2>&1
invalid_module=$?
set -e
[ "$missing_guard" -ne 0 ]
[ "$invalid_module" -ne 0 ]

echo 'PASS coldplug probe is explicit, allowlisted, storage-safe, and rollback-guarded'
