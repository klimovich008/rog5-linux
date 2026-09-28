#!/bin/sh
# Move the Wi-Fi client link from the kit's wpa_supplicant/dhcpcd units to
# NetworkManager, so Denial (NetworkManagerService over D-Bus) can scan,
# connect, forget and configure networks. Runs on the phone as root.
#
#   rog5-wifi-networkmanager.sh apply     configure, import, switch over
#   rog5-wifi-networkmanager.sh revert    back to rog5-wifi-wpa/-dhcp
#   rog5-wifi-networkmanager.sh status
#
# rog5-wifi-radio still powers the radio (S12 vote, PCIe, ath11k) and keeps
# its battery and thermal rules; NetworkManager only manages wlp1s0 (never the
# USB link or the hotspot's wlp1s0ap) and hands DNS to systemd-resolved. The
# network saved in /persist/secrets/wifi/network.conf (wpa_supplicant syntax)
# becomes an NM keyfile (0600) the first time; its passphrase is never printed.
# The boot health commit does not depend on Wi-Fi association.
#
# ROG5_WIFI_BACKEND picks NetworkManager's Wi-Fi backend: wpa_supplicant (the
# default) or iwd (needs CONFIG_CRYPTO_USER_API_HASH/_SKCIPHER and
# CONFIG_KEY_DH_OPERATIONS in the kernel). iwd leaves IP configuration to
# NetworkManager.
set -eu
conf=/etc/NetworkManager/conf.d/10-rog5.conf
connections=/etc/NetworkManager/system-connections
secret=/persist/secrets/wifi/network.conf
marker=/etc/rog5/wifi-backend-networkmanager
backend=${ROG5_WIFI_BACKEND:-wpa_supplicant}
case $backend in wpa_supplicant|iwd) ;; *) echo "unknown backend $backend" >&2; exit 2 ;; esac

import_network() {
	[ -f "$secret" ] || { echo 'no saved network in /persist; skipping import'; return 0; }
	python3 - "$secret" "$connections" <<'EOF'
import os, re, sys, uuid
source, target = sys.argv[1], sys.argv[2]
text = open(source).read()
block = re.search(r'network\s*=\s*\{(.*?)\}', text, re.S)
if not block:
    sys.exit('no network block in the saved config')
fields = {}
for line in block.group(1).splitlines():
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        key, value = line.split('=', 1)
        fields[key.strip()] = value.strip()
ssid = fields.get('ssid', '')
if ssid.startswith('"') and ssid.endswith('"'):
    ssid = ssid[1:-1]
else:
    # wpa_supplicant writes non-ASCII or special SSIDs as hex.
    try:
        ssid = bytes.fromhex(ssid).decode('utf-8')
    except ValueError:
        sys.exit('ssid is neither quoted nor UTF-8 hex')
if not ssid or any(c in ssid for c in '\n;'):
    sys.exit('ssid cannot be written to a keyfile safely')
psk = fields.get('psk', '')
psk = psk[1:-1] if psk.startswith('"') else psk
key_mgmt = fields.get('key_mgmt', 'WPA-PSK').split()
security = 'sae' if key_mgmt == ['SAE'] else 'wpa-psk'
name = re.sub(r'[^A-Za-z0-9._-]', '_', ssid) or 'wifi'
path = os.path.join(target, name + '.nmconnection')
if os.path.exists(path):
    print('keyfile exists, kept:', os.path.basename(path))
    sys.exit(0)
lines = ['[connection]', 'id=' + ssid, 'uuid=' + str(uuid.uuid4()), 'type=wifi', 'autoconnect=true', '',
         '[wifi]', 'mode=infrastructure', 'ssid=' + ssid,
         'hidden=true' if fields.get('scan_ssid') == '1' else 'hidden=false', '']
if psk:
    lines += ['[wifi-security]', 'key-mgmt=' + security, 'psk=' + psk]
    # A 64-hex PSK is the derived key, not the passphrase: WPA3-SAE (which NM
    # offers alongside WPA2 for wpa-psk) cannot use it and fails to
    # authenticate. SAE needs PMF, so disabling PMF keeps NM on WPA2-PSK.
    if re.fullmatch(r'[0-9a-fA-F]{64}', psk):
        lines += ['pmf=1']
    lines += ['']
lines += ['[ipv4]', 'method=auto', '', '[ipv6]', 'method=auto', '']
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as out:
    out.write('\n'.join(lines))
print('imported', 'secured' if psk else 'open', 'network as', os.path.basename(path))
EOF
}

case ${1:-status} in
apply)
	command -v NetworkManager >/dev/null || { echo 'NetworkManager is not installed' >&2; exit 1; }
	if [ "$backend" = iwd ]; then
	command -v iwctl >/dev/null || { echo 'iwd is not installed' >&2; exit 1; }
	install -d -m 0755 /etc/iwd
	cat >/etc/iwd/main.conf <<'EOF'
# ROG5: NetworkManager drives iwd and configures IP itself.
[General]
EnableNetworkConfiguration=false

[DriverQuirks]
# ath11k: keep power save off (TCP setup stalled with it on).
PowerSaveDisable=*
EOF
	fi
	install -d -m 0755 /etc/NetworkManager/conf.d /etc/rog5
	install -d -m 0700 "$connections"
	cat >"$conf" <<'EOF'
# ROG5: NetworkManager owns the Wi-Fi client interface and wired adapters
# (USB Ethernet behind a hub, enx*/eth*). The USB gadget link to a PC (usb0,
# NCM), the hotspot interface (wlp1s0ap) and Tailscale stay with their own
# services. Power save stays off: it stalled TCP setup on ath11k.
[main]
plugins=keyfile
dns=systemd-resolved

[keyfile]
# Exclusions by name; Wi-Fi stays managed whatever its name (wlp1s0 on most
# boots, the kernel name wlan0 on some, seen 2026-09-26). Wired adapters were
# unmanaged before 2026-09-28 (except:type:wifi), so a USB Ethernet adapter
# got no address.
unmanaged-devices=interface-name:usb0;interface-name:wlp1s0ap;interface-name:tailscale0

[connection]
wifi.powersave=2

[device]
wifi.scan-rand-mac-address=no
EOF
	printf 'wifi.backend=%s\n' "$backend" >>"$conf"
	import_network
	: >"$marker"
	systemctl stop rog5-wifi-dhcp.service rog5-wifi-wpa.service 2>/dev/null || true
	systemctl mask rog5-wifi-dhcp.service rog5-wifi-wpa.service
	[ "$backend" != iwd ] || systemctl enable --now iwd.service
	systemctl enable --now NetworkManager.service
	;;
revert)
	systemctl disable --now NetworkManager.service || true
	systemctl disable --now iwd.service || true
	systemctl unmask rog5-wifi-dhcp.service rog5-wifi-wpa.service
	rm -f "$marker"
	systemctl restart rog5-wifi-wpa.service rog5-wifi-dhcp.service
	;;
status)
	systemctl is-active NetworkManager.service rog5-wifi-wpa.service rog5-wifi-dhcp.service || true
	command -v nmcli >/dev/null && nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device || true
	;;
*)
	echo "usage: $0 apply|revert|status" >&2
	exit 2
	;;
esac
