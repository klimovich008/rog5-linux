#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
probe=$repo/scripts/device/probe-network-root-battery-telemetry.sh

[ -x "$probe" ]
sh -n "$probe"

for contract in \
	'ALLOW_NETWORK_ROOT_BATTERY_PROBE' \
	'ROG5_ADSP_SCM_TRACE' \
	'7.1.4-g7a5cef0db479' \
	'systemd-udev-trigger.service' \
	'systemd-modules-load.service' \
	'/run/rog5-network-root-watchdog.disarmed.pid' \
	'169.254.77.1:/' \
	'physical block device is present' \
	'block-backed mount is present' \
	'/sys/class/net/usb0/carrier' \
	'/reserved-memory/memory@cbc00000' \
	'/reserved-memory/memory@d8000000' \
	'/reserved-memory/memory@edc00000' \
	'/soc@0/remoteproc@3000000' \
	'remoteproc@4080000' \
	'remoteproc@5c00000' \
	'remoteproc@a300000' \
	'qcom,sm8350-pmic-glink qcom,pmic-glink' \
	'30889541' \
	'fa38f4f8d4ab428bd828601dc0c9805fcabe3d265afe3cdb0ba6ed977ac9c666' \
	'firmware_class/parameters/path' \
	'udevadm control --stop-exec-queue' \
	'p:rog5_adsp/pas_outer qcom_scm_pas_init_image' \
	'p:rog5_adsp/pas_smc __qcom_scm_pas_init_image' \
	'r:rog5_adsp/pas_smc_ret __qcom_scm_pas_init_image' \
	'EVIDENCE scm_trace_begin' \
	'modprobe --first-time qcom_q6v5_pas' \
	'qcom_glink_smem qrtr pdr_interface' \
	'qcom_glink_smem qrtr' \
	'insmod "$pmic_module" battery_only=1' \
	'modprobe --first-time pdr_interface' \
	'modprobe --first-time qcom_battmgr' \
	'pmic_glink.power-supply.*' \
	'pmic_glink.ucsi.*' \
	'pmic_glink.altmode.*' \
	'charge_control_start_threshold' \
	'charge_control_end_threshold' \
	'stat -c %a "$usb/input_current_limit"' \
	'exec 9>/proc/sysrq-trigger' \
	'echo b >&9' \
	'kill -STOP -- "-$watchdog_pid"' \
	'kill -KILL -- "-$watchdog_pid"' \
	'Kernel panic|Oops:|BUG:' \
	'probe_safe=1'
do
	grep -Fq "$contract" "$probe" || {
		echo "FAIL battery probe contract missing: $contract" >&2
		exit 1
	}
done

guard_line=$(grep -n 'ALLOW_NETWORK_ROOT_BATTERY_PROBE' "$probe" |
	head -n1 | cut -d: -f1)
watchdog_line=$(grep -n '^setsid sh -c' "$probe" | cut -d: -f1)
udev_line=$(grep -n '^udevadm control --stop-exec-queue' "$probe" | cut -d: -f1)
adsp_line=$(grep -n 'modprobe --first-time qcom_q6v5_pas' "$probe" |
	head -n1 | cut -d: -f1)
evidence_line=$(grep -n '^post_fail()' "$probe" | cut -d: -f1)
pmic_line=$(grep -n '^[[:space:]]*insmod "$pmic_module"' "$probe" | cut -d: -f1)
battmgr_line=$(grep -n '^[[:space:]]*modprobe --first-time qcom_battmgr' "$probe" |
	cut -d: -f1)
settle_line=$(grep -n '^sleep "$settle_seconds"' "$probe" | cut -d: -f1)
safe_line=$(grep -n '^probe_safe=1$' "$probe" | cut -d: -f1)
[ "$guard_line" -lt "$watchdog_line" ]
[ "$watchdog_line" -lt "$udev_line" ]
[ "$evidence_line" -lt "$udev_line" ]
[ "$udev_line" -lt "$adsp_line" ]
[ "$adsp_line" -lt "$pmic_line" ]
[ "$pmic_line" -lt "$battmgr_line" ]
[ "$battmgr_line" -lt "$settle_line" ]
[ "$settle_line" -lt "$safe_line" ]

grep -Fq "post_fail 'ADSP module load failed'" "$probe"
grep -Fq "post_fail 'ADSP remoteproc did not register'" "$probe"
grep -Fq "post_fail 'ADSP did not reach running state'" "$probe"
[ "$(grep -c "^qrtr'\$" "$probe")" -eq 1 ]

if grep -Eq 'udevadm control --start-exec-queue|rmmod|modprobe[[:space:]].*(-r|--remove)|fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|hwclock|/dev/rtc' \
	"$probe"; then
	echo 'FAIL probe resumes udev, unloads a driver, flashes, or writes storage/RTC' >&2
	exit 1
fi

set +e
"$probe" adsp >/dev/null 2>&1
missing_guard=$?
ALLOW_NETWORK_ROOT_BATTERY_PROBE=1 "$probe" invalid >/dev/null 2>&1
invalid_mode=$?
ALLOW_NETWORK_ROOT_BATTERY_PROBE=1 ROG5_ADSP_SCM_TRACE=1 \
	"$probe" telemetry >/dev/null 2>&1
trace_telemetry=$?
set -e
[ "$missing_guard" -ne 0 ]
[ "$invalid_mode" -ne 0 ]
[ "$trace_telemetry" -ne 0 ]

echo 'PASS battery-telemetry probe is two-tiered, explicit, volatile-firmware-only, USB-C-control-free, and rollback-guarded'
