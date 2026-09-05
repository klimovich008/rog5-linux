#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
target=${TARGET:-$repo/scripts/device/collect-baseline.sh}
stage_script=$repo/scripts/device/stage-arch-rootfs.sh
verify_script=$repo/scripts/device/verify-staged-arch-rootfs.sh
fixture=$(mktemp -d)
trap 'rm -rf "$fixture"' EXIT HUP INT TERM
root=$fixture/root

mkdir -p \
	"$root/proc/101" "$root/proc/102" "$root/proc/103" \
	"$root/run" \
	"$root/sys/class/backlight/panel0-backlight" \
	"$root/sys/class/drm/card0-DSI-1" \
	"$root/sys/class/drm/renderD128" \
	"$root/sys/class/net/usb0/statistics" \
	"$root/sys/class/power_supply/test-battery" \
	"$root/sys/class/thermal/thermal_zone0" \
	"$root/sys/class/thermal/thermal_zone1" \
	"$root/sys/kernel/btf" \
	"$root/sys/devices/platform/soc/3d00000.qcom,kgsl-3d0/kgsl/kgsl-3d0/snapshot"

cat >"$root/proc/meminfo" <<'EOF'
MemTotal:       10000 kB
MemAvailable:    6000 kB
SwapTotal:       2000 kB
SwapFree:        1500 kB
EOF
printf '123.45 67.89\n' >"$root/proc/uptime"
printf '0.25 0.50 0.75 2/100 123\n' >"$root/proc/loadavg"
printf 'cpu 10 20 30 40 5 6 7 8 9 10\n' >"$root/proc/stat"
cat >"$root/proc/101/status" <<'EOF'
Name:	kwin_wayland
EOF
printf 'Pss:                1024 kB\n' >"$root/proc/101/smaps_rollup"
cat >"$root/proc/102/status" <<'EOF'
Name:	plasmashell
EOF
printf 'Pss:                2048 kB\n' >"$root/proc/102/smaps_rollup"
cat >"$root/proc/103/status" <<'EOF'
Name:	unrelated
EOF
printf 'Pss:                4096 kB\n' >"$root/proc/103/smaps_rollup"

printf 'Discharging\n' >"$root/sys/class/power_supply/test-battery/status"
printf '77\n' >"$root/sys/class/power_supply/test-battery/capacity"
printf '3900000\n' >"$root/sys/class/power_supply/test-battery/voltage_now"
printf '%s\n' '-450000' >"$root/sys/class/power_supply/test-battery/current_now"
printf '321\n' >"$root/sys/class/power_supply/test-battery/temp"
printf 'Battery\n' >"$root/sys/class/power_supply/test-battery/type"
printf '42000\n' >"$root/sys/class/thermal/thermal_zone0/temp"
printf '43000\n' >"$root/sys/class/thermal/thermal_zone1/temp"
printf '100\n' >"$root/sys/class/backlight/panel0-backlight/brightness"
printf 'connected\n' >"$root/sys/class/drm/card0-DSI-1/status"
printf '1080x2448x60\n1080x2448x90\n' >"$root/sys/class/drm/card0-DSI-1/modes"
printf 'up\n' >"$root/sys/class/net/usb0/operstate"
printf '1234\n' >"$root/sys/class/net/usb0/statistics/rx_bytes"
printf '5678\n' >"$root/sys/class/net/usb0/statistics/tx_bytes"
printf 'off\n' >"$root/run/rog5-screen-state"
printf 'Adreno 660\n' \
	>"$root/sys/devices/platform/soc/3d00000.qcom,kgsl-3d0/kgsl/kgsl-3d0/gpu_model"
printf '2\n' \
	>"$root/sys/devices/platform/soc/3d00000.qcom,kgsl-3d0/kgsl/kgsl-3d0/reset_count"
printf '0\n' \
	>"$root/sys/devices/platform/soc/3d00000.qcom,kgsl-3d0/kgsl/kgsl-3d0/snapshot/faultcount"
: >"$root/sys/kernel/btf/vmlinux"

cat >"$fixture/systemctl" <<'EOF'
#!/bin/sh
set -eu
case $1 in
	get-default)
		echo multi-user.target
		;;
	is-active)
		case $2 in
			rog5-server-inhibit.service) echo active ;;
			*) echo inactive; exit 3 ;;
		esac
		;;
	show)
		property=
		for argument in "$@"; do
			case $argument in --property=*) property=${argument#--property=} ;; esac
		done
		case $property in
			ActiveState) echo active ;;
			MemoryCurrent) echo 100000000 ;;
			MemoryPeak) echo 150000000 ;;
			TasksCurrent) echo 12 ;;
			CPUUsageNSec) echo 2000000000 ;;
			NRestarts) echo 1 ;;
			*) exit 1 ;;
		esac
		;;
	*)
		exit 2
		;;
esac
EOF
chmod +x "$fixture/systemctl"

output=$(
	ROG5_METRICS_ROOT=$root \
	ROG5_METRICS_SYSTEMCTL=$fixture/systemctl \
		sh "$target"
)

for expected in \
	'memory_used_kib=4000' \
	'swap_used_kib=500' \
	'load_1m=0.25' \
	'cpu_total_ticks=145' \
	'cpu_idle_ticks=45' \
	'battery_status=Discharging' \
	'battery_capacity_percent=77' \
	'battery_current_ua=-450000' \
	'thermal_zone_count=2' \
	'thermal_max_millidegree_c=43000' \
	'screen_state=off' \
	'backlight_brightness=100' \
	'dsi_status=connected' \
	'plasma_process_count=2' \
	'plasma_pss_kib=3072' \
	'agent_active_state=active' \
	'agent_memory_current_bytes=100000000' \
	'agent_memory_peak_bytes=150000000' \
	'agent_tasks_current=12' \
	'agent_cpu_usage_nsec=2000000000' \
	'agent_restart_count=1' \
	'usb0_present=yes' \
	'usb0_operstate=up' \
	'usb0_rx_bytes=1234' \
	'usb0_tx_bytes=5678' \
	'wlan0_present=no' \
	'wg0_present=no' \
	'default_target=multi-user.target' \
	'server_inhibitor_state=active' \
	'drm_render_node_count=1'
do
	printf '%s\n' "$output" | grep -Fqx "$expected" || {
		echo "FAIL baseline collector omits: $expected" >&2
		exit 1
	}
done

if printf '%s\n' "$output" |
	grep -Eqi '(^|_)(ip|ipv4|ipv6|mac|ssid|cmdline|serial)='; then
	echo 'FAIL baseline collector exposes a network or device identifier' >&2
	exit 1
fi
if grep -Eq '/proc/cmdline|ip[[:space:]]+-brief|nmcli|iwgetid' "$target"; then
	echo 'FAIL baseline collector reads a forbidden identifier source' >&2
	exit 1
fi

grep -Fq 'collect-baseline.sh' "$stage_script"
grep -Fq '/usr/local/bin/rog5-collect-baseline.sh' "$verify_script"

echo 'PASS redacted runtime collector covers desktop, automation, power, display, thermal, and interface counters'
