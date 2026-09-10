#!/bin/sh
# Foreground WPA belongs to systemd; do not assume optional WPA logging flags.
set -eu
PATH=/usr/sbin:/usr/bin:/sbin:/bin
export PATH
[ "$#" = 4 ] || exit 2
boot=$1
release=$2
interface=$3
seconds=$4
root=/run/rog5-native-wifi
state=/run/rog5-wifi-association
case $interface in ''|*[!A-Za-z0-9_.:-]*) exit 2 ;; esac
case $seconds in ''|*[!0-9]*) exit 2 ;; esac
[ "$seconds" -ge 30 ] && [ "$seconds" -le 400 ] || exit 2
[ "$(id -u)" = 0 ]
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$boot" ]
[ "$(uname -r)" = "$release" ]
[ "$(tr -d '\000' </sys/firmware/devicetree/base/model)" = 'ASUS ROG Phone 5' ]
[ "$(readlink -f "/sys/class/net/$interface/device")" = "$(readlink -f /sys/bus/pci/devices/0000:01:00.0)" ]
[ -d "$state" ] && [ ! -L "$state" ]
[ "$(stat -c '%u:%g:%a' "$state")" = 0:0:700 ]
[ -f "$state/private-network.conf" ] && [ ! -L "$state/private-network.conf" ]
[ "$(stat -c '%u:%a:%h' "$state/private-network.conf")" = 0:600:1 ]
systemctl is-active --quiet rog5-wifi-outer-rollback.timer
[ "$(systemctl show -p LoadState --value rog5-wifi-wpa.service)" = not-found ]
start_wpa() {
 systemd-run --unit=rog5-wifi-wpa --collect \
  --property=Type=exec --property=Restart=no --property="RuntimeMaxSec=${seconds}s" \
  /usr/bin/env "OPENSSL_CONF=$root/wpa-userspace/openssl.cnf" \
  "$root/wpa-userspace/lib/ld-musl-aarch64.so.1" --library-path "$root/wpa-userspace/lib" \
  "$root/wpa-userspace/sbin/wpa_supplicant" -Dnl80211 -i "$interface" -c "$state/private-network.conf"
}
start_wpa
systemctl is-active --quiet rog5-wifi-wpa.service
