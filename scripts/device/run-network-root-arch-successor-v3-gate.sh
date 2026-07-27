#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_ARCH_SUCCESSOR_V3_GATE:-}" = 1 ] ||
	fail 'set ALLOW_ARCH_SUCCESSOR_V3_GATE=1 for the one-shot gate'
[ "${ALLOW_ARCH_SUCCESSOR_V3_REBOOT:-}" = 1 ] ||
	fail 'set ALLOW_ARCH_SUCCESSOR_V3_REBOOT=1 for immediate fallback'
[ "$(id -u)" -eq 0 ] || fail 'Arch successor v3 gate requires root'

for command in awk cat cut dmesg find findmnt getent grep id ip kill mktemp \
	pacman ps readlink setsid sha256sum sleep stat systemctl tr uname wait wc; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done

[ "$(uname -r)" = 7.1.4-g7a5cef0db479 ] || fail 'unexpected kernel'
[ "$(cat /proc/1/comm)" = systemd ] || fail 'PID 1 is not systemd'
system_state=
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 \
	21 22 23 24 25 26 27 28 29 30; do
	system_state=$(systemctl is-system-running 2>/dev/null || true)
	[ "$system_state" != running ] || break
	case $system_state in
		starting|initializing) sleep 1 ;;
		*) break ;;
	esac
done
[ "$system_state" = running ] || fail 'systemd is not running'
[ "$(systemctl get-default)" = multi-user.target ] ||
	fail 'default target is not headless'
for unit in NetworkManager.service rog5-power-button.service sshd.service \
	rog5-server-inhibit.service; do
	[ "$(systemctl is-active "$unit")" = active ] ||
		fail "$unit is not active"
done
[ "$(systemctl show rog5-power-button.service \
	--property=NRestarts --value)" = 0 ] ||
	fail 'power-button service restarted'
for unit in systemd-udev-trigger.service systemd-modules-load.service \
	systemd-sysusers.service systemd-tmpfiles-setup.service; do
	[ "$(systemctl show "$unit" --property=Result --value)" = success ] ||
		fail "$unit did not complete successfully"
done
[ "$(systemctl is-active greetd.service 2>/dev/null || true)" = inactive ] ||
	fail 'graphical login started in the headless target'
for unit in rog5-chromium-headless.service rog5-vpn-hotspot.service \
	rog5-ttyd.service; do
	[ "$(systemctl is-enabled "$unit" 2>/dev/null || true)" = disabled ] ||
		fail "$unit is enabled before explicit configuration"
	[ "$(systemctl is-active "$unit" 2>/dev/null || true)" = inactive ] ||
		fail "$unit is active before explicit configuration"
done

[ "$(findmnt -n -o FSTYPE /)" = overlay ] || fail 'root is not OverlayFS'
[ "$(findmnt -n -o SOURCE /.rog5/root-ro)" = 169.254.77.1:/ ] ||
	fail 'unexpected NFS lower source'
findmnt -n -o OPTIONS /.rog5/root-ro | tr ',' '\n' | grep -qx ro ||
	fail 'NFS lower is not read-only'
[ "$(findmnt -n -o FSTYPE /.rog5/state)" = tmpfs ] ||
	fail 'writable state is not tmpfs'
for option in nodev nosuid; do
	findmnt -n -o OPTIONS /.rog5/state | tr ',' '\n' |
		grep -qx "$option" || fail "tmpfs state lacks $option"
done
[ "$(find /sys/class/block -mindepth 1 -maxdepth 1 -type l \
	-exec test -e {}/device \; -print 2>/dev/null | wc -l)" -eq 0 ] ||
	fail 'physical block device is present'
[ "$(findmnt -rn -o SOURCE |
	awk '/^\/dev\// { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'block-backed mount is present'
[ "$(cat /sys/class/net/usb0/carrier)" = 1 ] ||
	fail 'USB network carrier is down'
[ "$(ip -4 -o address show dev usb0 |
	awk '$4 == "169.254.77.2/30" { count++ }
		END { print count + 0 }')" -eq 1 ] ||
	fail 'USB network address is not exact'

seal=/.rog5/root-ro/etc/rog5/arch-successor-v3-export
[ -f "$seal" ] && [ ! -L "$seal" ] ||
	fail 'successor v3 seal is absent or linked'
[ "$(stat -c '%u:%g:%a' "$seal")" = 0:0:444 ] ||
	fail 'successor v3 seal metadata changed'
[ "$(sha256sum "$seal" | cut -d ' ' -f 1)" = \
	26b4fcd8f21c5974d281d4b39386f82965265a31728c3a54877ab6717e98f2a7 ] ||
	fail 'successor v3 seal hash changed'
grep -qx 'export_generation=arch-successor-v3' "$seal"
grep -qx \
	'archive_sha256=a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7' \
	"$seal"
grep -qx 'promotion_state=UNBOOTED_HOLD' "$seal"

package_count=655
installed_packages=$(pacman -Qq | wc -l)
[ "$installed_packages" -eq "$package_count" ] ||
	fail 'installed package count changed'
grep -qx 'rog5:x:1000:1000::/home/rog5:/bin/bash' /etc/passwd
grep -qx \
	'rog5-agent:x:961:961::/var/lib/rog5-agent:/usr/bin/nologin' \
	/etc/passwd
[ "$(id -nG rog5-agent)" = rog5-agent ] ||
	fail 'agent gained a supplementary group'
[ "$(stat -c '%u:%g:%a' /var/lib/rog5-agent)" = 961:961:700 ]
[ "$(stat -c '%u:%g:%a' /var/lib/rog5-agent/private)" = 961:961:700 ]
[ ! -e /var/lib/rog5-agent/.ssh ] || fail 'agent gained SSH state'

[ ! -s /.rog5/root-ro/etc/machine-id ] ||
	fail 'protected lower contains a machine identity'
grep -Eq '^[0-9a-f]{32}$' /etc/machine-id ||
	fail 'volatile machine identity was not generated'
host_key=/etc/ssh/ssh_host_ed25519_key
[ -f "$host_key" ] && [ ! -L "$host_key" ] && [ -s "$host_key" ] ||
	fail 'persistent SSH host key is absent'
[ "$(stat -c '%u:%g:%a' "$host_key")" = 0:0:600 ] ||
	fail 'persistent SSH host key metadata changed'
[ "$(stat -c '%u:%g:%a' "$host_key.pub")" = 0:0:644 ] ||
	fail 'persistent SSH public-key metadata changed'

check_hash() {
	file=$1
	expected=$2
	label=$3
	[ -f "$file" ] && [ ! -L "$file" ] ||
		fail "$label is absent or linked"
	[ "$(sha256sum "$file" | cut -d ' ' -f 1)" = "$expected" ] ||
		fail "$label hash changed"
}
check_hash /etc/systemd/system/rog5-server-inhibit.service \
	bc2065f43e421147b2b962d981a05ee0e973f879ec40fe413905f0fc15b30a74 \
	'server inhibitor'
check_hash /etc/systemd/system/rog5-chromium-headless.service \
	6e6cfd6a3ede945f67dc9dd42650153a1abfc63651175f54868e1e394cdac8cb \
	'isolated Chromium service'
check_hash /usr/local/sbin/rog5-vpn-hotspot.sh \
	5e2b4af39227f3afd37a494474faf982f1a87f3e8807406e47196d92b3bb079d \
	'VPN hotspot v2 control'
check_hash /etc/systemd/system/rog5-vpn-hotspot.service \
	8ea3d2509bb220d200816571f379c2992c5281771be22d1b84d49d4a716cd814 \
	'VPN hotspot v2 service'
check_hash /usr/local/libexec/rog5-power-buttond \
	66b3a8bfc32434e450d10ea707e21481b991e6fc728cd7afa618664331b4298a \
	'power-button handler'
check_hash /etc/systemd/system/rog5-power-button.service \
	c617188753e17482328f69abc55c3d2b6da62dd543ecb3a14f551c4f17fb72c7 \
	'power-button service'

power_inputs=0
for name in /sys/class/input/event*/device/name; do
	[ -e "$name" ] || continue
	[ "$(cat "$name")" = pmic_pwrkey ] || continue
	event=${name%/device/name}
	event=${event##*/}
	[ -c "/dev/input/$event" ] ||
		fail 'pmic_pwrkey input is not a character device'
	power_inputs=$((power_inputs + 1))
done
[ "$power_inputs" -eq 1 ] ||
	fail 'expected exactly one pmic_pwrkey input'

screen=absent
for brightness in /sys/class/backlight/*/brightness; do
	[ -e "$brightness" ] || continue
	[ "$(cat "$brightness")" = 0 ] || fail 'screen backlight is not off'
	screen=off
done

[ "$(systemctl --failed --no-legend --plain 2>/dev/null |
	awk 'NF { count++ } END { print count + 0 }')" -eq 0 ] ||
	fail 'systemd has failed units'
fatal_pattern='Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog.*bite'
[ "$(dmesg | grep -Ec "$fatal_pattern" || true)" -eq 0 ] ||
	fail 'fatal kernel signature is present'

collector=/usr/local/bin/rog5-collect-baseline.sh
disarm=/run/rog5-arch-successor-v3-control/disarm-network-root-watchdog.sh
check_hash "$collector" \
	2726ffda517aa13d97da4c9b04712524ccded2ba6ac25f2021f337a10523b946 \
	'redacted runtime collector'
check_hash "$disarm" \
	b126182b615831e6f39784e4a2657cc60096ff906c26f1458be7d9a0d3ea065a \
	'watchdog disarm helper'
[ "$(stat -c '%u:%g:%a' "$disarm")" = 0:0:500 ] ||
	fail 'watchdog disarm helper metadata changed'

pid_file=/run/rog5-network-root-watchdog.pid
marker=/run/rog5-network-root-watchdog.disarmed.pid
[ -s "$pid_file" ] || fail 'initial rollback watchdog is absent'
[ ! -e "$marker" ] || fail 'initial rollback watchdog is already disarmed'

"$collector"

transition_timeout=240
state_dir=$(mktemp -d /run/rog5-arch-successor-v3-transition.XXXXXX)
# Positional parameters are intentionally expanded by the child shell.
# shellcheck disable=SC2016
setsid sh -c '
	set -eu
	exec 8>/dev/kmsg
	exec 9>/proc/sysrq-trigger
	printf "armed\n" >"$2"
	sleep "$1"
	echo "rog5-arch-successor-v3-transition: watchdog expired" >&8
	echo b >&9
' sh "$transition_timeout" "$state_dir/armed" \
	</dev/null >/dev/null 2>&1 &
transition_pid=$!

transition_pgid=$(ps -o pgid= -p "$transition_pid" | tr -d ' ')
[ "$transition_pgid" = "$transition_pid" ] ||
	fail 'transition watchdog is not in an independent process group'
armed=0
for _ in 1 2 3 4 5; do
	if [ -s "$state_dir/armed" ] &&
		kill -0 "$transition_pid" 2>/dev/null; then
		armed=1
		break
	fi
	sleep 1
done
[ "$armed" -eq 1 ] || fail 'transition watchdog did not arm'
trap 'exit 1' HUP INT TERM

ALLOW_NETWORK_ROOT_WATCHDOG_DISARM=1 "$disarm"
[ ! -e "$pid_file" ] && [ -s "$marker" ] ||
	fail 'initial watchdog handoff is incomplete'
kill -0 "$transition_pid" 2>/dev/null ||
	fail 'transition watchdog disappeared during handoff'

systemctl reboot --no-block
echo "PASS Arch successor v3 headless gate kernel=7.1.4-g7a5cef0db479 packages=655 systemd=running coldplug=success tmpfiles=success sysusers=success agent=isolated hotspot=fail-closed-v2 power-button=active-input-present headless=1 screen=$screen machine_id=volatile lower=sealed storage=0 mounts=0 failed_units=0 transition_watchdog=armed reboot=requested"
wait "$transition_pid"
fail 'transition watchdog returned before fallback reboot'
