#!/bin/sh
set -eu
LC_ALL=C
export LC_ALL

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_DUAL_CELL_READONLY_SNAPSHOT:-}" = 1 ] ||
	fail 'set ALLOW_DUAL_CELL_READONLY_SNAPSHOT=1 for one read-only snapshot'

runtime_root=${ROG5_DUAL_CELL_RUNTIME_ROOT:-}
test_mode=${ROG5_DUAL_CELL_TEST_MODE:-0}
case $test_mode:$runtime_root in
	0:) execution_mode=live ;;
	1:/*)
		[ "$runtime_root" != / ] ||
			fail 'test dual-cell root must not be the host root'
		[ -d "$runtime_root" ] && [ ! -L "$runtime_root" ] ||
			fail 'test dual-cell root is unsafe'
		execution_mode=test
		;;
	*) fail 'dual-cell fixture mode is invalid' ;;
esac

runtime_path() {
	printf '%s%s' "$runtime_root" "$1"
}

unsigned_integer() {
	case $1 in
		''|*[!0-9]*) return 1 ;;
	esac
	[ "$1" = 0 ] || [ "${1#0}" = "$1" ]
}

for command in awk cat find grep id readlink sha256sum sort stat uname; do
	command -v "$command" >/dev/null ||
		fail "missing dual-cell snapshot command: $command"
done

collector_path=$0
[ -f "$collector_path" ] && [ ! -L "$collector_path" ] ||
	fail 'dual-cell collector source is absent or linked'
collector_sha256=$(sha256sum "$collector_path" | awk '{ print $1 }')
case $collector_sha256 in
	*[!0-9a-f]*|'') fail 'dual-cell collector hash is invalid' ;;
esac
[ "${#collector_sha256}" -eq 64 ] ||
	fail 'dual-cell collector hash width changed'

if [ "$execution_mode" = live ]; then
	[ "$(id -u):$(id -g)" = 0:0 ] ||
		fail 'live dual-cell collection requires root'
	kernel_release=$(uname -r)
else
	kernel_release=${ROG5_DUAL_CELL_TEST_KERNEL_RELEASE:-}
fi
[ "$kernel_release" = 7.1.4-g7a5cef0db479 ] ||
	fail 'unexpected dual-cell kernel'

candidate=${ROG5_RUNTIME_CANDIDATE:-headless-dual-cell-network-root-v1}
[ "$candidate" = headless-dual-cell-network-root-v1 ] ||
	fail 'dual-cell candidate identity is unsupported'

boot_id=$(cat "$(runtime_path /proc/sys/kernel/random/boot_id)")
printf '%s\n' "$boot_id" |
	grep -Eq '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' ||
	fail 'dual-cell boot identity is invalid'

power_root=$(runtime_path /sys/class/power_supply)
device_root=$(runtime_path /sys/devices)
[ -d "$power_root" ] && [ ! -L "$power_root" ] ||
	fail 'power-supply class is absent or linked'
[ -d "$device_root" ] && [ ! -L "$device_root" ] ||
	fail 'device root is absent or linked'

expected_supplies='qcom-battmgr-bat
qcom-battmgr-usb
qcom-battmgr-wls'
actual_supplies=$(
	find "$power_root" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort
)
[ "$actual_supplies" = "$expected_supplies" ] ||
	fail 'dual-cell supply inventory changed'

resolve_supply() {
	name=$1
	entry=$power_root/$name
	[ -L "$entry" ] ||
		fail "dual-cell supply is not one sysfs class link: $name"
	resolved=$(readlink -f "$entry") ||
		fail "dual-cell supply cannot be resolved: $name"
	case $resolved in
		"$device_root"/*) ;;
		*) fail "dual-cell supply escapes the device root: $name" ;;
	esac
	[ -d "$resolved" ] && [ ! -L "$resolved" ] ||
		fail "dual-cell supply target is unsafe: $name"
	printf '%s\n' "$entry"
}

battery=$(resolve_supply qcom-battmgr-bat)
usb=$(resolve_supply qcom-battmgr-usb)
wireless=$(resolve_supply qcom-battmgr-wls)

property_mode() {
	path=$1
	label=$2
	[ -f "$path" ] && [ ! -L "$path" ] ||
		fail "dual-cell property is absent or linked: $label"
	mode=$(stat -c %a "$path")
	[ "$mode" = 444 ] ||
		fail "dual-cell property is not read-only: $label"
}

property_mode "$battery/voltage_now" battery/voltage_now
property_mode "$battery/cell_voltages" battery/cell_voltages

charge_control_surface_count=0
for supply in "$battery" "$usb" "$wireless"; do
	for property in \
		charge_control_start_threshold \
		charge_control_end_threshold \
		charge_limit
	do
		if [ -e "$supply/$property" ] || [ -L "$supply/$property" ]; then
			charge_control_surface_count=$((charge_control_surface_count + 1))
		fi
	done
done
[ "$charge_control_surface_count" -eq 0 ] ||
	fail 'dual-cell charge-control surface appeared'

aggregate_voltage_uv=$(cat "$battery/voltage_now")
cell_line=$(cat "$battery/cell_voltages")
unsigned_integer "$aggregate_voltage_uv" ||
	fail 'aggregate voltage is not a canonical integer'

case $cell_line in
	cell1_voltage_mv=*' cell2_voltage_mv='*) ;;
	*) fail 'cell-voltage response is not canonical' ;;
esac
cell_fields=${cell_line#cell1_voltage_mv=}
cell1_voltage_mv=${cell_fields%% *}
cell2_voltage_mv=${cell_fields#"$cell1_voltage_mv cell2_voltage_mv="}
unsigned_integer "$cell1_voltage_mv" &&
	unsigned_integer "$cell2_voltage_mv" &&
	[ "$cell_line" = \
		"cell1_voltage_mv=$cell1_voltage_mv cell2_voltage_mv=$cell2_voltage_mv" ] ||
	fail 'cell-voltage response is not canonical'

[ "$aggregate_voltage_uv" -ge 5000000 ] &&
	[ "$aggregate_voltage_uv" -le 10000000 ] ||
	fail 'aggregate voltage is outside the dual-cell diagnostic range'
for cell_voltage_mv in "$cell1_voltage_mv" "$cell2_voltage_mv"; do
	[ "$cell_voltage_mv" -ge 2500 ] && [ "$cell_voltage_mv" -le 5000 ] ||
		fail 'cell voltage is outside the diagnostic range'
done

cell_sum_uv=$(((cell1_voltage_mv + cell2_voltage_mv) * 1000))
if [ "$aggregate_voltage_uv" -ge "$cell_sum_uv" ]; then
	aggregate_delta_uv=$((aggregate_voltage_uv - cell_sum_uv))
else
	aggregate_delta_uv=$((cell_sum_uv - aggregate_voltage_uv))
fi
[ "$aggregate_delta_uv" -le 300000 ] ||
	fail 'aggregate does not match cell sum within 300000 uV'

if [ "$cell1_voltage_mv" -ge "$cell2_voltage_mv" ]; then
	cell_imbalance_mv=$((cell1_voltage_mv - cell2_voltage_mv))
else
	cell_imbalance_mv=$((cell2_voltage_mv - cell1_voltage_mv))
fi

printf '%s\n' \
	'format=rog5-dual-cell-snapshot-v1' \
	'profile=battery-dual-cell-readonly-v1' \
	"execution_mode=$execution_mode" \
	"collector_sha256=$collector_sha256" \
	"candidate=$candidate" \
	"boot_id=$boot_id" \
	"kernel_release=$kernel_release" \
	'battery_supply=qcom-battmgr-bat' \
	'battery_property_modes=voltage_now:444,cell_voltages:444' \
	"charge_control_surface_count=$charge_control_surface_count" \
	"aggregate_voltage_uv=$aggregate_voltage_uv" \
	"cell1_voltage_mv=$cell1_voltage_mv" \
	"cell2_voltage_mv=$cell2_voltage_mv" \
	"cell_sum_uv=$cell_sum_uv" \
	"aggregate_delta_uv=$aggregate_delta_uv" \
	"cell_imbalance_mv=$cell_imbalance_mv" \
	'result=OBSERVED_NOT_HEALTH_ASSESSMENT'
