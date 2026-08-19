#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
probe=$repo/scripts/device/probe-network-root-battery-telemetry.sh

[ -x "$probe" ]
sh -n "$probe"

for contract in \
	'ALLOW_NETWORK_ROOT_BATTERY_PROBE' \
	'ALLOW_NETWORK_ROOT_CHARGING_PROBE' \
	'ALLOW_NETWORK_ROOT_EARLY_CHARGING_PROBE' \
	'"$diagnostic" emit 200 charging-probe-failed' \
	'emit_progress 142' \
	'emit_progress 143' \
	'emit_progress 144' \
	'emit_progress 145' \
	'emit_progress 151' \
	'ROG5_ADSP_SCM_TRACE' \
	'ROG5_TELEMETRY_WAIT' \
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
	'30900841' \
	'fa38f4f8d4ab428bd828601dc0c9805fcabe3d265afe3cdb0ba6ed977ac9c666' \
	'firmware_class/parameters/path' \
	'udevadm control --stop-exec-queue' \
	'p:rog5_adsp/pas_outer qcom_scm_pas_init_image' \
	'p:rog5_adsp/pas_smc __qcom_scm_pas_init_image' \
	'r:rog5_adsp/pas_smc_ret __qcom_scm_pas_init_image' \
	'EVIDENCE scm_trace_begin' \
	'modprobe --first-time qcom_q6v5_pas' \
	'qcom_glink_smem qrtr qrtr_smd pdr_interface' \
	'qcom_glink_smem qrtr' \
	'87e4797a61b75efd02cb52d47e013af5c28cee57affcf484f872ea5a1fb69178' \
	'7eac8fd204c74f0cae8d28a082dec54c8e30d55d420dfd2418052e7f5c9777f7' \
	'modprobe --first-time qrtr_smd' \
	'modprobe --first-time qcom_pd_mapper' \
	'qcom_pd_mapper.qcom-pdm-mapper' \
	'insmod "$pmic_module" battery_only=1' \
	'modprobe --first-time pdr_interface' \
	'modprobe --first-time qcom_battmgr' \
	'modprobe --first-time pmic_glink' \
	'modprobe --first-time ucsi_glink' \
	'full UCSI did not detect USB input' \
	'final_voltage_uV=' \
	'emit_typec_snapshot' \
	'typec_port_count=' \
	'typec_partner_count=' \
	'property_modes=$property_modes' \
	'usb_voltage_uV=' \
	'usb_current_max_uA=' \
	'usb_input_current_limit_uA=' \
	'usb_type=' \
	'side-port UDC identity changed after UCSI' \
	'side-port gadget binding changed after UCSI' \
	'USB network address changed after UCSI' \
	'USB network route changed after UCSI' \
	'pmic_glink.power-supply.*' \
	'pmic_glink.ucsi.*' \
	'pmic_glink.altmode.*' \
	'charge_control_start_threshold' \
	'charge_control_end_threshold' \
	'USB property is absent, linked, or writable' \
	'exec 9>/proc/sysrq-trigger' \
	'echo b >&9' \
	'kill -STOP -- "-$watchdog_pid"' \
	'kill -KILL -- "-$watchdog_pid"' \
	'Kernel panic|Oops:|BUG:' \
	'telemetry_ready=0' \
	"post_fail 'battery telemetry did not become readable'" \
	'read_telemetry_property()' \
	'post_fail "battery telemetry became unreadable: $telemetry_name"' \
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
udev_line=$(grep -n '^[[:space:]]*udevadm control --stop-exec-queue' "$probe" |
	cut -d: -f1)
adsp_line=$(grep -n 'modprobe --first-time qcom_q6v5_pas' "$probe" |
	head -n1 | cut -d: -f1)
evidence_line=$(grep -n '^post_fail()' "$probe" | cut -d: -f1)
qrtr_transport_line=$(grep -n '^[[:space:]]*if ! modprobe --first-time qrtr_smd' \
	"$probe" | cut -d: -f1)
pdm_line=$(grep -n '^[[:space:]]*if ! modprobe --first-time qcom_pd_mapper' \
	"$probe" | cut -d: -f1)
pdr_line=$(grep -n '^[[:space:]]*if ! modprobe --first-time pdr_interface' \
	"$probe" | cut -d: -f1)
pmic_line=$(grep -n '^[[:space:]]*if ! insmod "$pmic_module"' "$probe" | cut -d: -f1)
battmgr_line=$(grep -n '^[[:space:]]*if ! modprobe --first-time qcom_battmgr' "$probe" |
	cut -d: -f1)
readiness_line=$(grep -n "post_fail 'battery telemetry did not become readable'" \
	"$probe" | cut -d: -f1)
settle_line=$(grep -n '^sleep "$settle_seconds"' "$probe" | cut -d: -f1)
safe_line=$(grep -n '^probe_safe=1$' "$probe" | cut -d: -f1)
[ "$guard_line" -lt "$watchdog_line" ]
[ "$watchdog_line" -lt "$udev_line" ]
[ "$evidence_line" -lt "$udev_line" ]
[ "$udev_line" -lt "$adsp_line" ]
[ "$adsp_line" -lt "$qrtr_transport_line" ]
[ "$qrtr_transport_line" -lt "$pdm_line" ]
[ "$pdm_line" -lt "$pdr_line" ]
[ "$pdr_line" -lt "$pmic_line" ]
[ "$adsp_line" -lt "$pmic_line" ]
[ "$pmic_line" -lt "$battmgr_line" ]
[ "$battmgr_line" -lt "$readiness_line" ]
[ "$battmgr_line" -lt "$settle_line" ]
[ "$settle_line" -lt "$safe_line" ]

grep -Fq "post_fail 'ADSP module load failed'" "$probe"
grep -Fq "post_fail 'ADSP remoteproc did not register'" "$probe"
grep -Fq "post_fail 'ADSP did not reach running state'" "$probe"
[ "$(grep -c "^qrtr'\$" "$probe")" -eq 1 ]
if grep -Fq '/sys/bus/auxiliary/drivers/qcom-pdm-mapper' "$probe"; then
	echo 'FAIL probe uses the unprefixed auxiliary-driver sysfs directory' >&2
	exit 1
fi

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
ALLOW_NETWORK_ROOT_BATTERY_PROBE=1 "$probe" charging >/dev/null 2>&1
missing_charging_guard=$?
ALLOW_NETWORK_ROOT_BATTERY_PROBE=1 \
	ALLOW_NETWORK_ROOT_CHARGING_PROBE=1 \
	"$probe" charging-early >/dev/null 2>&1
missing_early_guard=$?
set -e
[ "$missing_guard" -ne 0 ]
[ "$invalid_mode" -ne 0 ]
[ "$trace_telemetry" -ne 0 ]
[ "$missing_charging_guard" -ne 0 ]
[ "$missing_early_guard" -ne 0 ]

if grep -Eq 'charge_control_(start|end)_threshold[^\n]*(>|tee)' "$probe"; then
	echo 'FAIL charging probe writes a charge-control threshold' >&2
	exit 1
fi
if grep -Eq '/sys/class/typec[^\n]*(>|tee)' "$probe"; then
	echo 'FAIL charging probe writes a Type-C role or policy attribute' >&2
	exit 1
fi

check_structured_readiness() {
	candidate=$1
	grep -Fq 'telemetry_ready=0' "$candidate" &&
		grep -Fq '[ "$telemetry_ready" -eq 1 ] ||' "$candidate" &&
		grep -Fq "post_fail 'battery telemetry did not become readable'" \
			"$candidate" &&
		grep -Fq 'read_telemetry_property()' "$candidate" &&
		grep -Fq \
			'post_fail "battery telemetry became unreadable: $telemetry_name"' \
			"$candidate"
}

check_structured_readiness "$probe"
mutation_dir=$(mktemp -d)
mutant=$mutation_dir/probe.sh
trap 'rm -f "$mutant"; rmdir "$mutation_dir"' EXIT
sed "s/post_fail 'battery telemetry did not become readable'/fail 'battery telemetry did not become readable'/" \
	"$probe" >"$mutant"
if check_structured_readiness "$mutant" >/dev/null 2>&1; then
	echo 'FAIL readiness mutation escaped the structured-failure contract' >&2
	exit 1
fi
rm -f "$mutant"
rmdir "$mutation_dir"
trap - EXIT

typec_fixture=$(mktemp -d)
typec_functions=$typec_fixture/functions.sh
sed -n '/^emit_evidence() {/,/^)$/{p}' "$probe" >"$typec_functions"
mkdir -p "$typec_fixture/typec/port0" \
	"$typec_fixture/devices/partner0"
printf '%s\n' '[device] host' >"$typec_fixture/typec/port0/data_role"
printf '%s\n' '[sink] source' >"$typec_fixture/typec/port0/power_role"
printf '%s\n' '[dual]' >"$typec_fixture/typec/port0/port_type"
printf '%s\n' default >"$typec_fixture/typec/port0/power_operation_mode"
chmod 0644 "$typec_fixture/typec/port0/data_role" \
	"$typec_fixture/typec/port0/power_role" \
	"$typec_fixture/typec/port0/port_type"
chmod 0444 "$typec_fixture/typec/port0/power_operation_mode"
ln -s "$typec_fixture/devices/partner0" \
	"$typec_fixture/typec/port0-partner"
typec_output=$(
	ROG5_TYPEC_CLASS_ROOT=$typec_fixture/typec sh -eu -c '
		post_fail() { echo "FAIL $*" >&2; exit 1; }
		. "$1"
		emit_typec_snapshot
	' sh "$typec_functions"
)
printf '%s\n' "$typec_output" | grep -Fqx \
	'EVIDENCE typec_port=port0 data_role=[device]_host power_role=[sink]_source port_type=[dual] power_operation_mode=default property_modes=data_role:644,power_role:644,port_type:644,power_operation_mode:444 partner=1'
printf '%s\n' "$typec_output" | grep -Fqx \
	'EVIDENCE typec_port_count=1 typec_partner_count=1'
chmod 0666 "$typec_fixture/typec/port0/data_role"
if ROG5_TYPEC_CLASS_ROOT=$typec_fixture/typec sh -eu -c '
	post_fail() { exit 1; }
	. "$1"
	emit_typec_snapshot
' sh "$typec_functions" >/dev/null 2>&1; then
	echo 'FAIL Type-C snapshot accepted an unsafe control mode' >&2
	exit 1
fi
find "$typec_fixture" -depth -delete

echo 'PASS battery-telemetry probe keeps historical isolated tiers and adds one explicit-write-free full-UCSI charging discriminator'
