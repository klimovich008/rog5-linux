#!/bin/sh
set -eu

export PATH=/sbin:/bin:/usr/sbin:/usr/bin

fail() {
	printf 'rog5-usb-liveness: FAIL %s\n' "$*" >&2
	exit 1
}

[ "$#" -eq 1 ] && [ "$1" = observe ] ||
	fail 'usage: observe-persistent-usb-liveness.sh observe'
[ "$(id -u)" -eq 0 ] || fail 'observer requires root'

state_mount=/persist
log_dir=$state_mount/var/log/rog5-usb-observer
udc=/sys/class/udc/a600000.usb
net=/sys/class/net/usb0
max_samples=7200
sync_interval=10

awk '$2 == "/persist" && $3 == "ext4" && $4 ~ /(^|,)rw(,|$)/ {
	found++
} END { exit found != 1 }' /proc/mounts ||
	fail 'exact persistent state mount is unavailable'

boot_id=$(cat /proc/sys/kernel/random/boot_id) || fail 'boot ID unavailable'
printf '%s\n' "$boot_id" |
	grep -Eq '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' ||
	fail 'boot ID is invalid'

if [ -e "$log_dir" ] || [ -L "$log_dir" ]; then
	[ -d "$log_dir" ] && [ ! -L "$log_dir" ] &&
		[ "$(stat -c '%u:%g:%a' "$log_dir")" = 0:0:700 ] ||
		fail 'observer log directory metadata changed'
else
	mkdir -m 0700 "$log_dir" || fail 'cannot create observer log directory'
	chown 0:0 "$log_dir"
fi

log=$log_dir/$boot_id.log
[ ! -e "$log" ] && [ ! -L "$log" ] || fail 'observer log already exists'
set -C
: >"$log"
set +C
chown 0:0 "$log"
chmod 0600 "$log"

numeric_or_state() {
	path=$1
	if [ ! -e "$path" ]; then
		printf absent
		return
	fi
	if [ ! -r "$path" ]; then
		printf error
		return
	fi
	value=$(cat "$path" 2>/dev/null) || {
		printf error
		return
	}
	case $value in
		''|*[!A-Za-z0-9_.-]*) printf error ;;
		*) printf '%s' "$value" ;;
	esac
}

printf 'format=rog5-persistent-usb-liveness-v1 boot_id=%s max_samples=%s sync_interval=%s\n' \
	"$boot_id" "$max_samples" "$sync_interval" >>"$log"
sync -f "$log"
printf 'format=rog5-persistent-usb-liveness-start-v1\nboot_id=%s\nlog=%s\nmax_samples=%s\nresult=PASS\n' \
	"$boot_id" "$log" "$max_samples"

sample=0
while [ "$sample" -lt "$max_samples" ]; do
	sample=$((sample + 1))
	uptime=$(cut -d ' ' -f 1 /proc/uptime 2>/dev/null) || uptime=error
	realtime=$(date +%s 2>/dev/null) || realtime=error
	carrier=$(numeric_or_state "$net/carrier")
	rx_packets=$(numeric_or_state "$net/statistics/rx_packets")
	tx_packets=$(numeric_or_state "$net/statistics/tx_packets")
	rx_errors=$(numeric_or_state "$net/statistics/rx_errors")
	tx_errors=$(numeric_or_state "$net/statistics/tx_errors")
	rx_dropped=$(numeric_or_state "$net/statistics/rx_dropped")
	tx_dropped=$(numeric_or_state "$net/statistics/tx_dropped")
	udc_state=$(numeric_or_state "$udc/state")
	udc_speed=$(numeric_or_state "$udc/current_speed")
	dwc_runtime=$(numeric_or_state "$udc/device/power/runtime_status")
	printf 'sample=%s realtime=%s uptime=%s carrier=%s rx_packets=%s tx_packets=%s rx_errors=%s tx_errors=%s rx_dropped=%s tx_dropped=%s udc_state=%s udc_speed=%s dwc_runtime=%s\n' \
		"$sample" "$realtime" "$uptime" "$carrier" "$rx_packets" \
		"$tx_packets" "$rx_errors" "$tx_errors" "$rx_dropped" \
		"$tx_dropped" "$udc_state" "$udc_speed" "$dwc_runtime" >>"$log"
	if [ $((sample % sync_interval)) -eq 0 ]; then
		sync -f "$log"
	fi
	sleep 1
done
sync -f "$log"
