#!/bin/sh
set -eu
LC_ALL=C
export LC_ALL

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_HEADLESS_BATTERY_SERIES:-}" = 1 ] ||
	fail 'set ALLOW_HEADLESS_BATTERY_SERIES=1 for one read-only series'

phase=${1:-}
case $phase in
	unplugged|usb-online|wireless-online) ;;
	*) fail 'usage: collect-headless-battery-series.sh unplugged|usb-online|wireless-online' ;;
esac

runtime_root=${ROG5_BATTERY_RUNTIME_ROOT:-}
test_mode=${ROG5_BATTERY_TEST_MODE:-0}
case $test_mode:$runtime_root in
	0:)
		execution_mode=live
		sample_count=21
		interval_seconds=30
		;;
	1:/*)
		[ "$runtime_root" != / ] ||
			fail 'test battery root must not be the host root'
		[ -d "$runtime_root" ] && [ ! -L "$runtime_root" ] ||
			fail 'test battery root is unsafe'
		execution_mode=test
		sample_count=${ROG5_BATTERY_TEST_SAMPLE_COUNT:-3}
		interval_seconds=${ROG5_BATTERY_TEST_INTERVAL_SECONDS:-0}
		;;
	*) fail 'battery-series fixture mode is invalid' ;;
esac

unsigned_integer() {
	case $1 in
		''|*[!0-9]*) return 1 ;;
	esac
	[ "$1" = 0 ] || [ "${1#0}" = "$1" ]
}

signed_integer() {
	value=$1
	case $value in
		-*) value=${value#-} ;;
	esac
	unsigned_integer "$value" || return 1
	[ "$1" != -0 ]
}

unsigned_integer "$sample_count" &&
	unsigned_integer "$interval_seconds" ||
	fail 'battery-series schedule is not canonical'
if [ "$execution_mode" = live ]; then
	[ "$sample_count" = 21 ] && [ "$interval_seconds" = 30 ] ||
		fail 'live battery-series schedule changed'
else
	[ "$sample_count" -ge 1 ] && [ "$sample_count" -le 5 ] &&
		[ "$interval_seconds" -ge 0 ] &&
		[ "$interval_seconds" -le 1 ] ||
		fail 'test battery-series schedule is out of bounds'
fi

runtime_path() {
	printf '%s%s' "$runtime_root" "$1"
}

for command in awk cat find grep id readlink sha256sum sleep sort stat uname; do
	command -v "$command" >/dev/null ||
		fail "missing battery-series command: $command"
done

collector_path=$0
[ -f "$collector_path" ] && [ ! -L "$collector_path" ] ||
	fail 'battery-series collector source is absent or linked'
collector_sha256=$(sha256sum "$collector_path" | awk '{ print $1 }')
case $collector_sha256 in
	*[!0-9a-f]*|'') fail 'battery-series collector hash is invalid' ;;
esac
[ "${#collector_sha256}" -eq 64 ] ||
	fail 'battery-series collector hash width changed'

owner_uid=$(id -u)
owner_gid=$(id -g)
if [ "$execution_mode" = live ]; then
	[ "$owner_uid:$owner_gid" = 0:0 ] ||
		fail 'live battery-series collection requires root'
	kernel_release=$(uname -r)
else
	kernel_release=${ROG5_BATTERY_TEST_KERNEL_RELEASE:-}
fi
[ "$kernel_release" = 7.1.4-g7a5cef0db479 ] ||
	fail 'unexpected battery-series kernel'

candidate=${ROG5_RUNTIME_CANDIDATE:-headless-ssh-network-root-v3}
[ "$candidate" = headless-ssh-network-root-v3 ] ||
	fail 'battery-series candidate identity is unsupported'

boot_id=$(cat "$(runtime_path /proc/sys/kernel/random/boot_id)")
printf '%s\n' "$boot_id" |
	grep -Eq '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' ||
	fail 'battery-series boot identity is invalid'

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
	fail 'battery-series supply inventory changed'

resolve_supply() {
	name=$1
	entry=$power_root/$name
	[ -L "$entry" ] ||
		fail "battery-series supply is not one sysfs class link: $name"
	resolved=$(readlink -f "$entry") ||
		fail "battery-series supply cannot be resolved: $name"
	case $resolved in
		"$device_root"/*) ;;
		*) fail "battery-series supply escapes the device root: $name" ;;
	esac
	[ -d "$resolved" ] && [ ! -L "$resolved" ] ||
		fail "battery-series supply target is unsafe: $name"
	printf '%s\n' "$entry"
}

battery=$(resolve_supply qcom-battmgr-bat)
usb=$(resolve_supply qcom-battmgr-usb)
wireless=$(resolve_supply qcom-battmgr-wls)

property_mode() {
	path=$1
	label=$2
	[ -f "$path" ] && [ ! -L "$path" ] ||
		fail "battery-series property is absent or linked: $label"
	mode=$(stat -c %a "$path")
	[ "$mode" = 444 ] ||
		fail "battery-series property is not read-only: $label"
	printf '%s\n' "$mode"
}

for property in capacity voltage_now current_now temp status; do
	property_mode "$battery/$property" "battery/$property" >/dev/null
done
property_mode "$usb/online" usb/online >/dev/null
property_mode "$wireless/online" wireless/online >/dev/null
input_current_limit_mode=$(
	property_mode "$usb/input_current_limit" usb/input_current_limit
)

charge_control_surface_count=0
for supply in "$battery" "$usb" "$wireless"; do
	for property in \
		charge_control_start_threshold \
		charge_control_end_threshold
	do
		if [ -e "$supply/$property" ] || [ -L "$supply/$property" ]; then
			charge_control_surface_count=$((charge_control_surface_count + 1))
		fi
	done
done
[ "$charge_control_surface_count" -eq 0 ] ||
	fail 'battery-series charge-control surface appeared'

typec_root=$(runtime_path /sys/class/typec)
if [ -e "$typec_root" ] || [ -L "$typec_root" ]; then
	[ -d "$typec_root" ] && [ ! -L "$typec_root" ] ||
		fail 'battery-series Type-C class is unsafe'
	typec_device_count=$(
		find "$typec_root" -mindepth 1 -maxdepth 1 -print |
			awk 'NF { count++ } END { print count + 0 }'
	)
else
	typec_device_count=0
fi
[ "$typec_device_count" -eq 0 ] ||
	fail 'battery-series Type-C control device appeared'

printf '%s\n' \
	'format=rog5-headless-battery-series-v1' \
	'profile=battery-readonly-v1' \
	"execution_mode=$execution_mode" \
	"collector_sha256=$collector_sha256" \
	"candidate=$candidate" \
	"boot_id=$boot_id" \
	"kernel_release=$kernel_release" \
	"phase=$phase" \
	"interval_seconds=$interval_seconds" \
	"sample_count=$sample_count" \
	'battery_supply=qcom-battmgr-bat' \
	'usb_supply=qcom-battmgr-usb' \
	'wireless_supply=qcom-battmgr-wls' \
	'battery_property_modes=capacity:444,voltage_now:444,current_now:444,temp:444,status:444' \
	"usb_input_current_limit_mode=$input_current_limit_mode" \
	"charge_control_surface_count=$charge_control_surface_count" \
	"typec_device_count=$typec_device_count"

index=0
while [ "$index" -lt "$sample_count" ]; do
	capacity=$(cat "$battery/capacity")
	voltage_uv=$(cat "$battery/voltage_now")
	current_ua=$(cat "$battery/current_now")
	temp_dc=$(cat "$battery/temp")
	status=$(cat "$battery/status")
	usb_online=$(cat "$usb/online")
	wireless_online=$(cat "$wireless/online")

	unsigned_integer "$capacity" &&
		unsigned_integer "$voltage_uv" &&
		signed_integer "$current_ua" &&
		signed_integer "$temp_dc" &&
		unsigned_integer "$usb_online" &&
		unsigned_integer "$wireless_online" ||
		fail 'battery-series sample contains a noncanonical integer'
	[ "$capacity" -le 100 ] ||
		fail 'battery-series capacity is outside 0..100 percent'
	[ "$voltage_uv" -ge 2500000 ] && [ "$voltage_uv" -le 10000000 ] ||
		fail 'battery-series voltage is outside the diagnostic range'
	[ "$current_ua" -ge -20000000 ] &&
		[ "$current_ua" -le 20000000 ] ||
		fail 'battery-series current is outside the diagnostic range'
	[ "$temp_dc" -ge -200 ] && [ "$temp_dc" -le 1000 ] ||
		fail 'battery-series temperature is outside the diagnostic range'
	[ "$usb_online" -le 1 ] && [ "$wireless_online" -le 1 ] ||
		fail 'battery-series online state is not boolean'

	case $status in
		Unknown|Charging|Discharging|Full) status_token=$status ;;
		'Not charging') status_token=Not_charging ;;
		*) fail 'battery-series status is unsupported' ;;
	esac
	case $phase:$usb_online:$wireless_online in
		unplugged:0:0|usb-online:1:0|wireless-online:0:1) ;;
		*) fail 'battery-series physical phase does not match online state' ;;
	esac

	elapsed_seconds=$((index * interval_seconds))
	printf 'sample_%03d=%s,%s,%s,%s,%s,%s,%s,%s\n' \
		"$index" "$elapsed_seconds" "$capacity" "$voltage_uv" \
		"$current_ua" "$temp_dc" "$status_token" "$usb_online" \
		"$wireless_online"
	index=$((index + 1))
	if [ "$index" -lt "$sample_count" ]; then
		sleep "$interval_seconds"
	fi
done

echo 'result=OBSERVED'
