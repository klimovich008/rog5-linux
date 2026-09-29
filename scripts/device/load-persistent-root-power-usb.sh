#!/bin/sh
set -eu

module_root=/rog5-power-usb-modules
firmware_source=/opt/rog5-charge-firmware
firmware_runtime=/run/rog5-charge-firmware
record=/run/rog5-power-usb-ready
# A production ramdisk (it carries the platform kit) is a daily phone: it must
# boot on battery or on a wall charger. There the USB power, Type-C role and
# NCM checks only describe what is attached; the battery checks stay strict.
# Development and storage-writing archives keep every check (2026-09-24: two
# unplugged r26/r27 boots failed here with power-usb-usb-offline).
production=0
[ ! -d "${ROG5_POWER_PLATFORM_KIT:-/rog5-platform}" ] || production=1
# A production ramdisk carries one depmod tree for the running release instead
# of the legacy loose-module directory. Modules are still named one at a time in
# the historical order, so every per-step check below keeps its meaning.
module_release=
{ IFS= read -r module_release </proc/sys/kernel/osrelease; } 2>/dev/null ||
	module_release=
module_tree=/lib/modules/$module_release
module_mode=legacy
if [ -n "$module_release" ] && [ ! -e "$module_root" ] && [ ! -L "$module_root" ] &&
	[ -f "$module_tree/modules.dep" ] && [ ! -L "$module_tree/modules.dep" ]; then
	module_mode=tree
fi

fail() {
	code=$1
	shift
	printf 'power-usb-%s\n' "$code"
	echo "rog5-persistent-power: $*" >/dev/kmsg 2>/dev/null || true
	exit 1
}

data_role_is_device() {
	case $1 in
		device|'host [device]') return 0 ;;
		*) return 1 ;;
	esac
}

power_role_is_sink() {
	case $1 in
		sink|'source [sink]') return 0 ;;
		*) return 1 ;;
	esac
}

require_ncm_carrier() {
	marker=/run/rog5-native-wifi/automatic
	if [ -e "$marker" ] || [ -L "$marker" ]; then
		[ -f "$marker" ] && [ ! -L "$marker" ] &&
			[ "$(stat -c '%u:%g:%a:%s:%h' "$marker")" = 0:0:444:25:1 ] &&
			[ "$(cat "$marker")" = rog5-native-wifi-boot-v1 ] ||
			fail wifi-mode-invalid 'invalid signed Wi-Fi boot mode'
		return 0
	fi
	[ "$(cat /sys/class/net/usb0/carrier)" = 1 ] ||
		fail ncm-carrier 'NCM carrier dropped'
}

read_integer() {
	value=$(cat "$1" 2>/dev/null) || return 1
	case $value in ''|'-'|*[!0-9-]*|*-*-) return 1 ;; esac
	printf '%s\n' "$value"
}

load_module() {
	file=$1
	name=$2
	detail=$3
	if [ "$module_mode" = tree ]; then
		# The last line of the plan must be this module's own file; anything
		# else means the tree does not provide it under this name.
		plan=$(modprobe -D "$name" 2>/dev/null) ||
			fail "module-$detail-missing" "missing module $file"
		case $(printf '%s\n' "$plan" | tail -n 1) in
			*/"$file" | */"$file "*) ;;
			*) fail "module-$detail-missing" "missing module $file" ;;
		esac
	else
		[ -f "$module_root/$file" ] && [ ! -L "$module_root/$file" ] ||
			fail "module-$detail-missing" "missing module $file"
	fi
	if grep -q "^$name " /proc/modules; then
		# With a depmod tree the kernel's own request_module works: on the
		# phone, ADSP start makes the built-in sysmon open a QMI socket, which
		# requests net-pf-42 and loads qrtr before its step (trial r2). A module
		# of this closure loaded that way is accepted and still verified
		# below. Legacy archives have no tree, so any early load is an error.
		[ "$module_mode" = tree ] ||
			fail "module-$detail-already-loaded" "module already loaded: $name"
		echo "rog5-persistent-power: $name was autoloaded before its step" \
			>/dev/kmsg 2>/dev/null || true
	elif [ "$module_mode" = tree ]; then
		modprobe "$name" ||
			fail "module-$detail-load" "module load failed: $name"
	else
		insmod "$module_root/$file" ||
			fail "module-$detail-load" "module load failed: $name"
	fi
	grep -q "^$name " /proc/modules ||
		fail "module-$detail-unobservable" "module not observable: $name"
}

telemetry_seconds() {
	read -r uptime unused </proc/uptime ||
		fail telemetry-timeout 'monotonic clock unavailable'
	printf '%s\n' "${uptime%%.*}"
}

power_observation() {
	echo "rog5-power-readiness: $1 attempt=$attempt battery_uv=${battery_voltage:-absent} battery_temp=${battery_temp:-absent} usb_online=${usb_online:-absent}" \
		2>/dev/null >/dev/kmsg || true
}

wait_for_usb_online() {
	# A registered power_supply is not proof that its first online update has
	# arrived. Share the original node-wait budget; never accept late readiness.
	observed_offline=0
	while [ "$attempt" -lt 200 ] &&
		[ "$(telemetry_seconds)" -lt "$telemetry_deadline" ]; do
		battery_health=$(cat "$battery/health" 2>/dev/null) ||
			fail battery-health-unavailable 'battery health unavailable'
		[ "$battery_health" = Good ] ||
			fail battery-health-unsafe 'battery health is not Good'
		battery_voltage=$(read_integer "$battery/voltage_now") ||
			fail battery-voltage-unavailable 'battery voltage unavailable'
		battery_temp=$(read_integer "$battery/temp") ||
			fail battery-temperature-unavailable 'battery temperature unavailable'
		[ "$battery_voltage" -ge 5500000 ] && [ "$battery_voltage" -le 9200000 ] ||
			fail battery-voltage-unsafe 'unsafe battery voltage'
		[ "$battery_temp" -ge 0 ] && [ "$battery_temp" -lt 600 ] ||
			fail battery-temperature-unsafe 'unsafe battery temperature'
		usb_online=$(read_integer "$usb/online") ||
			fail usb-online-unavailable 'USB online state unavailable'
		case $usb_online in
			0|1) ;;
			*) fail usb-online-unavailable 'invalid USB online state' ;;
		esac
		[ "$(telemetry_seconds)" -lt "$telemetry_deadline" ] || break
		if [ "$usb_online" -eq 1 ]; then
			power_observation ready
			return 0
		fi
		if [ "${production:-0}" = 1 ] && [ "$observed_offline" -eq 1 ] &&
			[ "$attempt" -ge "$((offline_since + 15))" ]; then
			power_observation battery
			return 0
		fi
		if [ "$observed_offline" -eq 0 ]; then
			power_observation waiting
			observed_offline=1
			offline_since=$attempt
		fi
		attempt=$((attempt + 1))
		sleep 0.1
	done
	power_observation deadline
	fail usb-offline 'side USB power is offline'
}

[ -d "$firmware_source" ] && [ ! -L "$firmware_source" ] ||
	fail firmware-source 'firmware source is absent or linked'
[ ! -e "$firmware_runtime" ] && [ ! -L "$firmware_runtime" ] ||
	fail firmware-runtime-exists 'runtime firmware path already exists'
mkdir -m 0755 "$firmware_runtime" ||
	fail firmware-runtime-create 'runtime firmware path creation failed'
cp -Rp "$firmware_source"/. "$firmware_runtime"/ ||
	fail firmware-copy 'firmware copy failed'
[ "$(find "$firmware_runtime" -mindepth 1 -maxdepth 1 -type f | wc -l)" -eq 29 ] ||
	fail firmware-inventory 'firmware inventory changed'
printf '%s\n' "$firmware_runtime" \
	>/sys/module/firmware_class/parameters/path ||
	fail firmware-path 'firmware path update failed'

if [ "$module_mode" = legacy ]; then
	[ "$(find "$module_root" -mindepth 1 -maxdepth 1 -type f -name '*.ko' | wc -l)" -eq 15 ] ||
		fail module-inventory 'module inventory changed'
else
	# Production builds mdt_loader as a module (DRM_MSM=m); PAS needs it first.
	load_module mdt_loader.ko mdt_loader mdt-loader
fi
load_module qcom_q6v5.ko qcom_q6v5 qcom-q6v5
load_module qcom_glink_smem.ko qcom_glink_smem qcom-glink-smem
load_module qcom_common.ko qcom_common qcom-common
load_module qcom_pil_info.ko qcom_pil_info qcom-pil-info
load_module qcom_q6v5_pas.ko qcom_q6v5_pas qcom-q6v5-pas
load_module qrtr.ko qrtr qrtr
load_module qrtr-smd.ko qrtr_smd qrtr-smd
load_module qcom_pdr_msg.ko qcom_pdr_msg qcom-pdr-msg
load_module qcom_pd_mapper.ko qcom_pd_mapper qcom-pd-mapper
load_module pdr_interface.ko pdr_interface pdr-interface
load_module pmic_glink.ko pmic_glink pmic-glink
load_module qcom_battmgr.ko qcom_battmgr qcom-battmgr
load_module typec.ko typec typec
load_module typec_ucsi.ko typec_ucsi typec-ucsi
# DisplayPort DT (dp feature): the side connector's graph carries the
# gpio-sbu-mux and the combo PHY as orientation switches, and UCSI's
# typec_register_port() defers until they are bound (it gives up after 10 s:
# r129/r131 failed telemetry-timeout). Load them first, only with that DT.
if [ "$module_mode" = tree ] && [ -d /proc/device-tree/typec-sbu-mux ]; then
	load_module gpio-sbu-mux.ko gpio_sbu_mux gpio-sbu-mux
	load_module phy-qcom-qmp-combo.ko phy_qcom_qmp_combo phy-qcom-qmp-combo
fi
load_module ucsi_glink.ko ucsi_glink ucsi-glink

attempt=0
telemetry_deadline=$(( $(telemetry_seconds) + 20 ))
while [ "$attempt" -lt 200 ] &&
	[ "$(telemetry_seconds)" -lt "$telemetry_deadline" ]; do
	if [ -e /sys/class/power_supply/qcom-battmgr-bat ] &&
		[ -e /sys/class/power_supply/qcom-battmgr-usb ] &&
		[ -e /sys/class/typec/port0 ]; then
		break
	fi
	attempt=$((attempt + 1))
	sleep 0.1
done
[ "$attempt" -lt 200 ] &&
	[ "$(telemetry_seconds)" -lt "$telemetry_deadline" ] ||
	fail telemetry-timeout 'battery or UCSI telemetry did not appear'

battery=/sys/class/power_supply/qcom-battmgr-bat
usb=/sys/class/power_supply/qcom-battmgr-usb
wait_for_usb_online
usb_voltage=0
usb_current_max=0
typec_data=none
typec_power=none
ncm_route=none
if [ "$production" = 1 ]; then
	if [ "$usb_online" -eq 1 ]; then
		# Charging input must still be sane; the partner may be a charger
		# (no host, no NCM), a PC, or a USB-PD source: fast chargers, docks
		# and monitors negotiate 9-20 V, and a 5-6.5 V window made a boot on
		# a PD source fail and fall back (2026-09-28).
		usb_voltage=$(read_integer "$usb/voltage_now") ||
			fail usb-voltage-unavailable 'USB voltage unavailable'
		usb_current_max=$(read_integer "$usb/current_max") ||
			fail usb-current-limit-unavailable 'USB current limit unavailable'
		[ "$usb_voltage" -ge 4000000 ] && [ "$usb_voltage" -le 21000000 ] ||
			fail usb-voltage-invalid 'side USB voltage is invalid'
		[ "$usb_current_max" -ge 100000 ] && [ "$usb_current_max" -le 5000000 ] ||
			fail usb-current-limit-invalid 'side USB current limit is invalid'
		data_role=$(cat /sys/class/typec/port0/data_role 2>/dev/null) || data_role=
		power_role=$(cat /sys/class/typec/port0/power_role 2>/dev/null) || power_role=
		! data_role_is_device "$data_role" || typec_data=device
		! power_role_is_sink "$power_role" || typec_power=sink
		[ "$(cat /sys/class/net/usb0/carrier 2>/dev/null)" != 1 ] || ncm_route=direct
	fi
	echo "rog5-persistent-power: production boot usb_online=$usb_online typec=$typec_data/$typec_power ncm=$ncm_route" \
		>/dev/kmsg 2>/dev/null || true
else
	usb_voltage=$(read_integer "$usb/voltage_now") ||
		fail usb-voltage-unavailable 'USB voltage unavailable'
	usb_current_max=$(read_integer "$usb/current_max") ||
		fail usb-current-limit-unavailable 'USB current limit unavailable'
	[ "$usb_voltage" -ge 4000000 ] && [ "$usb_voltage" -le 6500000 ] ||
		fail usb-voltage-invalid 'side USB voltage is invalid'
	[ "$usb_current_max" -ge 100000 ] && [ "$usb_current_max" -le 5000000 ] ||
		fail usb-current-limit-invalid 'side USB current limit is invalid'
	data_role=$(cat /sys/class/typec/port0/data_role 2>/dev/null) ||
		fail typec-data-role 'side USB data role is unavailable'
	data_role_is_device "$data_role" ||
		fail typec-data-role 'side USB is not UFP/device'
	power_role=$(cat /sys/class/typec/port0/power_role 2>/dev/null) ||
		fail typec-power-role 'side USB power role is unavailable'
	power_role_is_sink "$power_role" ||
		fail typec-power-role 'side USB is not a power sink'
	require_ncm_carrier
	[ "$(ip -4 -o address show dev usb0 | awk '$4 == "169.254.77.2/30" { count++ } END { print count + 0 }')" -eq 1 ] ||
		fail ncm-address 'NCM address changed'
	route=$(ip -4 route get 169.254.77.1 2>/dev/null) ||
		fail ncm-route-unavailable 'NCM route unavailable'
	printf '%s\n' "$route" |
		grep -Eq '^169[.]254[.]77[.]1 dev usb0 .* src 169[.]254[.]77[.]2( |$)' ||
		fail ncm-route 'NCM route changed'
	typec_data=device
	typec_power=sink
	ncm_route=direct
fi

physical_count=0
for disk in /sys/class/block/*; do
	[ -e "$disk/device" ] || continue
	[ ! -e "$disk/partition" ] || continue
	# USB mass storage on the side port (resolved sysfs path under a usbN
	# bus) is not the UFS; UCSI can switch the port to host above. Only a
	# non-USB disk before the UFS stage is unexpected.
	case $(readlink -f "$disk") in */usb[0-9]*/*) continue ;; esac
	physical_count=$((physical_count + 1))
done
[ "$physical_count" -eq 0 ] ||
	fail storage-before-ufs 'storage appeared before the UFS stage'

[ ! -e "$record" ] && [ ! -L "$record" ] ||
	fail ready-record-exists 'power record already exists'
{
	printf 'format=rog5-persistent-root-power-usb-v1\n'
	printf 'battery_voltage_uv=%s\n' "$battery_voltage"
	printf 'battery_temp_decic=%s\n' "$battery_temp"
	printf 'usb_online=%s\n' "$usb_online"
	printf 'usb_voltage_uv=%s\n' "$usb_voltage"
	printf 'usb_current_max_ua=%s\n' "$usb_current_max"
	printf 'typec_data_role=%s\n' "$typec_data"
	printf 'typec_power_role=%s\n' "$typec_power"
	printf 'ncm_route=%s\n' "$ncm_route"
} >"$record" || fail ready-record-write 'power record write failed'
chmod 0444 "$record" || fail ready-record-mode 'power record mode update failed'
echo 'rog5-persistent-power: side-port charging and NCM ready' >/dev/kmsg 2>/dev/null || true
