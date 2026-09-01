#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
target=${TARGET:-$repo/scripts/device/status-screen.sh}
unit=${UNIT:-$repo/packaging/arch/rog5-status-screen.service}
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

sh -n "$target"
mkdir -p "$work/net/wlp1s0/wireless" "$work/battery" "$work/bin" "$work/run"
printf '1\n' >"$work/net/wlp1s0/carrier"
printf '100\n' >"$work/battery/capacity"
printf 'Full\n' >"$work/battery/status"
printf '8573000\n' >"$work/battery/voltage_now"
printf '299\n' >"$work/battery/temp"
: >"$work/tty"
printf 'on\n' >"$work/run/state"
cat >"$work/bin/ip" <<'EOF'
#!/bin/sh
printf '3: wlp1s0 inet 192.168.1.154/24 brd 192.168.1.255 scope global wlp1s0\n'
EOF
cat >"$work/bin/date" <<'EOF'
#!/bin/sh
printf '2026-09-01 13:45:00 UTC\n'
EOF
chmod 0755 "$work/bin/ip" "$work/bin/date"

ROG5_STATUS_TESTING=1 STATE_FILE="$work/run/state" STATUS_TTY="$work/tty" \
	NET_CLASS="$work/net" BATTERY_DIR="$work/battery" \
	IP_COMMAND="$work/bin/ip" DATE_COMMAND="$work/bin/date" \
	"$target" render
for expected in \
	'ROG Phone 5 Linux' \
	'Time:    2026-09-01 13:45:00 UTC' \
	'Wi-Fi:  wlp1s0 192.168.1.154/24' \
	'Battery: 100% Full  8573 mV  29.9 C' \
	'Server services remain running'; do
	grep -Fq "$expected" "$work/tty"
done
! grep -Eqi 'ssid|mac|00:03:7f' "$work/tty"

printf '0\n' >"$work/net/wlp1s0/carrier"
ROG5_STATUS_TESTING=1 STATUS_TTY="$work/tty" NET_CLASS="$work/net" \
	BATTERY_DIR="$work/missing-battery" IP_COMMAND="$work/bin/ip" \
	DATE_COMMAND="$work/bin/date" "$target" render
grep -Fq 'Wi-Fi:  offline' "$work/tty"
grep -Fq 'Battery: ?% unknown  ? mV  ?' "$work/tty"

mkdir -p "$work/net/wlan1/wireless"
printf '1\n' >"$work/net/wlp1s0/carrier"
printf '1\n' >"$work/net/wlan1/carrier"
ROG5_STATUS_TESTING=1 STATUS_TTY="$work/tty" NET_CLASS="$work/net" \
	BATTERY_DIR="$work/battery" IP_COMMAND="$work/bin/ip" \
	DATE_COMMAND="$work/bin/date" "$target" render
grep -Fq 'Wi-Fi:  multiple-active' "$work/tty"

for marker in \
	'ExecStart=/usr/local/libexec/rog5-status-screen watch' \
	'DeviceAllow=/dev/tty1 rw' \
	'ProtectSystem=strict' \
	'CapabilityBoundingSet=' \
	'RestrictAddressFamilies=AF_UNIX AF_NETLINK AF_INET AF_INET6' \
	'WantedBy=multi-user.target'; do
	grep -Fqx "$marker" "$unit"
done
mkdir "$work/systemd"
sed "s|^ExecStart=/usr/local/libexec/rog5-status-screen watch$|ExecStart=$target watch|" \
	"$unit" >"$work/systemd/rog5-status-screen.service"
systemd-analyze verify "$work/systemd/rog5-status-screen.service"

if grep -Eq 'ssid|/dev/(block|disk)|fastboot|adb|reboot|poweroff|mkfs|sgdisk' \
	"$target" "$unit"; then
	echo 'FAIL status screen exposes private Wi-Fi or storage/boot operations' >&2
	exit 1
fi
echo 'PASS minimal status screen reports time, active Wi-Fi/IP and battery without desktop or private network data'
