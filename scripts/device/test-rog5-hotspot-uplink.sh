#!/bin/sh
# rog5-hotspot finds the Wi-Fi client interface at run time instead of
# assuming wlp1s0 (NetworkManager names it wlan0). Offline: a fake iw.
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
target=${TARGET:-$repo/scripts/device/rog5-hotspot}
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

sh -n "$target"
mkdir -p "$work/bin"
cat >"$work/bin/iw" <<'FAKE'
#!/bin/sh
case "$*" in
dev) cat "$IW_DEV" ;;
"dev $IW_LINK_IF link") printf 'Connected to 00:11:22:33:44:55 (on %s)\n\tfreq: %s\n' "$IW_LINK_IF" "$IW_FREQ" ;;
*) exit 1 ;;
esac
FAKE
chmod 0755 "$work/bin/iw"

nm='phy#0
	Unnamed/non-netdev interface
		wdev 0x2
		addr 02:03:7f:00:00:00
		type P2P-device
	Interface wlan0
		ifindex 4
		wdev 0x1
		addr 00:03:7f:00:00:00
		ssid example
		type managed
		channel 36 (5180 MHz), width: 80 MHz, center1: 5210 MHz'
udev='phy#0
	Interface wlp1s0
		ifindex 3
		wdev 0x1
		addr 00:03:7f:00:00:00
		type managed'
# The AP already up (a restart): it must never be picked as the uplink, and
# an associated client wins over an idle one.
both='phy#0
	Interface wlp1s0ap
		ifindex 5
		addr 06:03:7f:00:00:00
		ssid ROG5-hotspot
		type AP
	Interface wlan1
		ifindex 6
		type managed
	Interface wlan0
		ifindex 4
		ssid example
		type managed'
monitor='phy#0
	Interface mon0
		type monitor'

plan() {
	printf '%s\n' "$1" >"$work/iw-dev"
	env PATH="$work/bin:$PATH" IW_DEV="$work/iw-dev" IW_LINK_IF="$2" IW_FREQ="$3" \
		ROG5_HOTSPOT_CONF="$work/hotspot.conf" ROG5_HOTSPOT_RUN="$work/run" ${4:+ROG5_HOTSPOT_UPLINK=$4} \
		sh "$target" config 2>&1
}

expect() {
	case $1 in *"$2"*) ;; *) printf 'FAIL: expected %s in: %s\n' "$2" "$1" >&2; exit 1 ;; esac
}

out=$(plan "$nm" wlan0 5180); expect "$out" 'uplink=wlan0'; expect "$out" 'channel=6 '
out=$(plan "$nm" wlan0 2437); expect "$out" 'uplink=wlan0'; expect "$out" 'channel=6 interface=wlp1s0ap'
out=$(plan "$nm" wlan0 2462); expect "$out" 'channel=11 '
out=$(plan "$udev" wlp1s0 2412); expect "$out" 'uplink=wlp1s0'; expect "$out" 'channel=1 '
out=$(plan "$both" wlan0 5180); expect "$out" 'uplink=wlan0'
out=$(plan "$nm" wlan9 2412 wlan9); expect "$out" 'uplink=wlan9'; expect "$out" 'channel=1 '
if out=$(plan "$monitor" x 0); then
	printf 'FAIL: no client interface must fail: %s\n' "$out" >&2; exit 1
fi
expect "$out" 'no Wi-Fi client interface'
grep -q '^ssid=ROG5-hotspot$' "$work/hotspot.conf"
echo 'PASS rog5-hotspot uplink discovery'
