#!/bin/sh
set -u

kv() { printf '%s=%s\n' "$1" "$2"; }
read_file() { cat "$1" 2>/dev/null || printf 'unavailable'; }

kv kernel "$(uname -r)"
kv machine "$(uname -m)"
kv uptime_seconds "$(cut -d' ' -f1 /proc/uptime)"
kv memory_total_kib "$(awk '/MemTotal:/ {print $2}' /proc/meminfo)"
kv memory_available_kib "$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
kv swap_total_kib "$(awk '/SwapTotal:/ {print $2}' /proc/meminfo)"
kv battery_status "$(read_file /sys/class/power_supply/battery/status)"
kv battery_capacity "$(read_file /sys/class/power_supply/battery/capacity)"
kv battery_voltage_now "$(read_file /sys/class/power_supply/battery/voltage_now)"
kv battery_current_now "$(read_file /sys/class/power_supply/battery/current_now)"
kv battery_temp "$(read_file /sys/class/power_supply/battery/temp)"
kv screen_state "$(read_file /run/rog5-screen-state)"
kv backlight "$(read_file /sys/class/backlight/panel0-backlight/brightness)"
kv dsi_status "$(read_file /sys/class/drm/card0-DSI-1/status)"
kv dsi_modes "$(tr '\n' ',' < /sys/class/drm/card0-DSI-1/modes 2>/dev/null | sed 's/,$//')"
kv usb0 "$(ip -brief address show usb0 2>/dev/null | tr -s ' ')"
kv wlan0 "$([ -e /sys/class/net/wlan0 ] && echo present || echo absent)"
kv ap0 "$([ -e /sys/class/net/ap0 ] && echo present || echo absent)"
kv btf "$([ -e /sys/kernel/btf/vmlinux ] && echo yes || echo no)"

kgsl=/sys/devices/platform/soc/3d00000.qcom,kgsl-3d0/kgsl/kgsl-3d0
kv gpu_model "$(read_file "$kgsl/gpu_model")"
kv gpu_reset_count "$(read_file "$kgsl/reset_count")"
kv gpu_fault_count "$(read_file "$kgsl/snapshot/faultcount")"

# Deliberately omit /proc/cmdline: it contains device identifiers.
