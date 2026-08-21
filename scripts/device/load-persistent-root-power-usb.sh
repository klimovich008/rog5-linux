#!/bin/sh
set -eu

module_root=/rog5-power-usb-modules
firmware_source=/opt/rog5-charge-firmware
firmware_runtime=/run/rog5-charge-firmware
record=/run/rog5-power-usb-ready

fail() {
	echo "rog5-persistent-power: $*" >/dev/kmsg 2>/dev/null || true
	exit 1
}

read_integer() {
	value=$(cat "$1" 2>/dev/null) || return 1
	case $value in ''|'-'|*[!0-9-]*|*-*-) return 1 ;; esac
	printf '%s\n' "$value"
}

load_module() {
	file=$1
	name=$2
	[ -f "$module_root/$file" ] && [ ! -L "$module_root/$file" ] ||
		fail "missing module $file"
	! grep -q "^$name " /proc/modules || fail "module already loaded: $name"
	insmod "$module_root/$file" || fail "module load failed: $name"
	grep -q "^$name " /proc/modules || fail "module not observable: $name"
}

[ -d "$firmware_source" ] && [ ! -L "$firmware_source" ] ||
	fail 'firmware source is absent or linked'
[ ! -e "$firmware_runtime" ] && [ ! -L "$firmware_runtime" ] ||
	fail 'runtime firmware path already exists'
mkdir -m 0755 "$firmware_runtime"
cp -Rp "$firmware_source"/. "$firmware_runtime"/ || fail 'firmware copy failed'
[ "$(find "$firmware_runtime" -mindepth 1 -maxdepth 1 -type f | wc -l)" -eq 29 ] ||
	fail 'firmware inventory changed'
printf '%s\n' "$firmware_runtime" \
	>/sys/module/firmware_class/parameters/path || fail 'firmware path update failed'

[ "$(find "$module_root" -mindepth 1 -maxdepth 1 -type f -name '*.ko' | wc -l)" -eq 15 ] ||
	fail 'module inventory changed'
load_module qcom_q6v5.ko qcom_q6v5
load_module qcom_glink_smem.ko qcom_glink_smem
load_module qcom_common.ko qcom_common
load_module qcom_pil_info.ko qcom_pil_info
load_module qcom_q6v5_pas.ko qcom_q6v5_pas
load_module qrtr.ko qrtr
load_module qrtr-smd.ko qrtr_smd
load_module qcom_pdr_msg.ko qcom_pdr_msg
load_module qcom_pd_mapper.ko qcom_pd_mapper
load_module pdr_interface.ko pdr_interface
load_module pmic_glink.ko pmic_glink
load_module qcom_battmgr.ko qcom_battmgr
load_module typec.ko typec
load_module typec_ucsi.ko typec_ucsi
load_module ucsi_glink.ko ucsi_glink

attempt=0
while [ "$attempt" -lt 200 ]; do
	if [ -e /sys/class/power_supply/qcom-battmgr-bat ] &&
		[ -e /sys/class/power_supply/qcom-battmgr-usb ] &&
		[ -e /sys/class/typec/port0 ]; then
		break
	fi
	attempt=$((attempt + 1))
	sleep 0.1
done
[ "$attempt" -lt 200 ] || fail 'battery or UCSI telemetry did not appear'

battery=/sys/class/power_supply/qcom-battmgr-bat
usb=/sys/class/power_supply/qcom-battmgr-usb
battery_voltage=$(read_integer "$battery/voltage_now") || fail 'battery voltage unavailable'
battery_temp=$(read_integer "$battery/temp") || fail 'battery temperature unavailable'
usb_online=$(read_integer "$usb/online") || fail 'USB online state unavailable'
usb_voltage=$(read_integer "$usb/voltage_now") || fail 'USB voltage unavailable'
usb_current_max=$(read_integer "$usb/current_max") || fail 'USB current limit unavailable'
[ "$battery_voltage" -ge 5500000 ] && [ "$battery_voltage" -le 9200000 ] ||
	fail 'unsafe battery voltage'
[ "$battery_temp" -ge 0 ] && [ "$battery_temp" -lt 600 ] ||
	fail 'unsafe battery temperature'
[ "$usb_online" -eq 1 ] || fail 'side USB power is offline'
[ "$usb_voltage" -ge 4000000 ] && [ "$usb_voltage" -le 6500000 ] ||
	fail 'side USB voltage is invalid'
[ "$usb_current_max" -ge 100000 ] && [ "$usb_current_max" -le 5000000 ] ||
	fail 'side USB current limit is invalid'
[ "$(cat /sys/class/typec/port0/data_role)" = device ] || fail 'side USB is not UFP/device'
[ "$(cat /sys/class/typec/port0/power_role)" = sink ] || fail 'side USB is not a power sink'
[ "$(cat /sys/class/net/usb0/carrier)" = 1 ] || fail 'NCM carrier dropped'
[ "$(ip -4 -o address show dev usb0 | awk '$4 == "169.254.77.2/30" { count++ } END { print count + 0 }')" -eq 1 ] ||
	fail 'NCM address changed'
route=$(ip -4 route get 169.254.77.1 2>/dev/null) || fail 'NCM route unavailable'
printf '%s\n' "$route" |
	grep -Eq '^169[.]254[.]77[.]1 dev usb0 .* src 169[.]254[.]77[.]2( |$)' ||
	fail 'NCM route changed'

physical_count=0
for disk in /sys/class/block/*; do
	[ -e "$disk/device" ] || continue
	[ ! -e "$disk/partition" ] || continue
	physical_count=$((physical_count + 1))
done
[ "$physical_count" -eq 0 ] || fail 'storage appeared before the UFS stage'

[ ! -e "$record" ] && [ ! -L "$record" ] || fail 'power record already exists'
{
	printf 'format=rog5-persistent-root-power-usb-v1\n'
	printf 'battery_voltage_uv=%s\n' "$battery_voltage"
	printf 'battery_temp_decic=%s\n' "$battery_temp"
	printf 'usb_online=%s\n' "$usb_online"
	printf 'usb_voltage_uv=%s\n' "$usb_voltage"
	printf 'usb_current_max_ua=%s\n' "$usb_current_max"
	printf 'typec_data_role=device\n'
	printf 'typec_power_role=sink\n'
	printf 'ncm_route=direct\n'
} >"$record"
chmod 0444 "$record"
echo 'rog5-persistent-power: side-port charging and NCM ready' >/dev/kmsg
