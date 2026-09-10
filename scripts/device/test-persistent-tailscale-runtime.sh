#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
helper=$repo/initramfs/persistent-tailscale-runtime
init=$repo/initramfs/persistent-root-init

[ -f "$helper" ] && [ ! -L "$helper" ] && [ -x "$helper" ]
sh -n "$helper" "$init"

for contract in \
	'/persist/opt/tailscale/1.102.3/dist' \
	'a0fa1b154af8c61f862a2259f559f7396d96c0225f4a863eae2333e1546bbe25' \
	'a14b94589c2630eb68ba7f7651ede226d2976708760ef3460556a00cf1aa4bab' \
	'dda710b5bed9fbf87efc0126b614ed8f0e9f4a43b2265486bc6ad7eb0570f226' \
	'service_address=10.77.0.2/30' \
	'service_gateway=10.77.0.1' \
	"[ \"\$(stat -c '%t:%T:%a' /dev/net/tun)\" = a:c8:666 ]" \
	'findmnt -n -o OPTIONS --target /persist' \
	'ip -4 route replace default via "$service_gateway" dev "$interface"' \
	'format=rog5-persistent-tailscale-runtime-v1'
do
	grep -Fq "$contract" "$helper"
done

for contract in \
	'cp -p /usr/local/sbin/rog5-persistent-tailscale' \
	'ExecStartPre=/run/rog5-persistent-tailscale prepare' \
	'ExecStart=/run/rog5-tailscale/tailscaled --state=/persist/var/lib/tailscale/tailscaled.state' \
	'ExecStopPost=/run/rog5-persistent-tailscale cleanup' \
	'RuntimeDirectoryMode=0700' \
	'Environment=TS_DEBUG_FIREWALL_MODE=nftables' \
	'sysinit.target.wants/rog5-tailscaled.service'
do
	grep -Fq "$contract" "$init"
done

! grep -Eq 'ROG5_.*OVERRIDE|TAILSCALE_(ROOT|PATH|STATE)=' "$helper"
[ "$(grep -c '^exact_file ' "$helper")" -eq 5 ]

# Execute the helper in POSIX sh with fixture-only paths and mocked device
# commands. Never invoke host ip, inspect credentials, or require root.
work=$(mktemp -d "${ROG5_TEST_TMP_PARENT:-${TMPDIR:-/tmp}}/rog5-tailscale-test.XXXXXX")
trap 'rm -rf -- "$work"' 0
trap 'exit 1' HUP INT TERM
failures=0
check() {
	if "$@"; then return; fi
	echo "FAIL $case_name: $*" >&2
	failures=$((failures + 1))
}
new_case() {
	case_name=$1
	fixture=$work/$case_name
	mkdir -p "$fixture/run/rog5-native-wifi" "$fixture/run/rog5-tailscale" \
		"$fixture/persist/opt/tailscale/1.102.3/dist" \
		"$fixture/persist/var/lib/tailscale" "$fixture/sys/class/net/usb0"
	for file in run/rog5-persistent-state.runtime \
		persist/opt/tailscale/1.102.3/tailscale_1.102.3_arm64.tgz \
		persist/opt/tailscale/1.102.3/dist/tailscale \
		persist/opt/tailscale/1.102.3/dist/tailscaled; do
		: >"$fixture/$file"
	done
	printf 'up\n' >"$fixture/sys/class/net/usb0/operstate"
	printf '2: usb0 inet 169.254.77.2/30 scope global usb0\n' >"$fixture/addresses"
	printf '%s\n' 'default via 192.0.2.1 dev wlan0 proto dhcp metric 100' \
		'default via 198.51.100.1 dev eth0 metric 200' >"$fixture/routes"
	marker=$fixture/run/rog5-native-wifi/automatic
	marker_owner=0:0 mount_options=rw,nodev,nosuid,noexec bad_digest=0
}
seal_marker() {
	printf 'rog5-native-wifi-boot-v1\n' >"$marker"
	chmod 0444 "$marker"
}
run_runtime() {
	: >"$fixture/calls"
	{
		cat <<'MOCKS'
test_root=$1 test_owner=$3 test_options=$4 test_bad_digest=$5
set -- "$2"
findmnt() {
	case $3 in
		TARGET) printf '%s/persist\n' "$test_root" ;;
		FSTYPE) echo ext4 ;;
		OPTIONS) echo "$test_options" ;;
		*) exit 91 ;;
	esac
}
stat() {
	case $2 in
		'%u:%g:%a') echo 0:0:700 ;;
		'%t:%T:%a') echo a:c8:666 ;;
		'%u:%g:%a:%h') echo 0:0:600:1 ;;
		'%u:%g:%a:%s:%h')
			case $3 in
				*/automatic)
					printf '%s:%s\n' "$test_owner" "$(command stat -c '%a:%s:%h' "$3")" ;;
				*.tgz) echo 0:0:600:35733085:1 ;;
				*/tailscale) echo 0:0:500:30825755:1 ;;
				*/tailscaled) echo 0:0:500:40133368:1 ;;
				*) exit 92 ;;
			esac ;;
		*) exit 93 ;;
	esac
}
sha256sum() {
	case $1 in
		*/automatic) command sha256sum "$@" ;;
		*.tgz)
			if [ "$test_bad_digest" = 1 ]; then echo invalid; else
				echo a0fa1b154af8c61f862a2259f559f7396d96c0225f4a863eae2333e1546bbe25
			fi ;;
		*/tailscale) echo a14b94589c2630eb68ba7f7651ede226d2976708760ef3460556a00cf1aa4bab ;;
		*/tailscaled) echo dda710b5bed9fbf87efc0126b614ed8f0e9f4a43b2265486bc6ad7eb0570f226 ;;
		*) exit 94 ;;
	esac
}
ip() {
	printf 'ip %s\n' "$*" >>"$test_root/calls"
	case $* in
		'-4 -o address show dev usb0') cat "$test_root/addresses" ;;
		'-4 route show exact default') cat "$test_root/routes" ;;
		'-4 address add 10.77.0.2/30 dev usb0'|\
		'-4 address del 10.77.0.2/30 dev usb0'|\
		'-4 route replace default via 10.77.0.1 dev usb0'|\
		'-4 route del default via 10.77.0.1 dev usb0') : ;;
		*) echo "FAIL unexpected mocked ip: $*" >&2; exit 95 ;;
	esac
}
install() { cp "$7" "$8"; }
chown() { :; }
MOCKS
		# Only absolute filesystem locations change; all checks/control flow run.
		sed -e "s@/persist@$fixture/persist@g" -e "s@/run/@$fixture/run/@g" \
			-e "s@/sys/class/net/@$fixture/sys/class/net/@g" \
			-e 's@/dev/net/tun@/dev/null@g' "$helper"
	} | sh -s -- "$fixture" "$1" "$marker_owner" "$mount_options" "$bad_digest" \
		>"$fixture/output" 2>&1
}
expect_pass() {
	if run_runtime "$1"; then return; fi
	cat "$fixture/output" >&2
	check false
}
expect_failure() {
	if run_runtime "$1"; then check false; fi
	check grep -Fq "$2" "$fixture/output"
}
no_network_writes() {
	! grep -Eq '^ip -4 (address (add|del|flush)|route (add|del|replace|flush)) ' "$fixture/calls"
}
no_route_writes() {
	! grep -Eq '^ip -4 route (add|del|replace|flush) ' "$fixture/calls"
}

for carrier in down up; do
	new_case "wifi-$carrier"
	seal_marker
	printf '%s\n' "$carrier" >"$fixture/sys/class/net/usb0/operstate"
	expect_pass prepare
	check grep -Fxq 'ip -4 address add 10.77.0.2/30 dev usb0' "$fixture/calls"
	check no_route_writes
	check test "$(grep -c '^ip -4 address ' "$fixture/calls")" -eq 1
	check test -f "$fixture/run/rog5-tailscale-prepared.record"
done

new_case wifi-existing-rescue
seal_marker
printf 'down\n' >"$fixture/sys/class/net/usb0/operstate"
printf '2: usb0 inet 10.77.0.2/30 scope global usb0\n' >>"$fixture/addresses"
# Even a pre-existing USB default is not this Wi-Fi runtime's route to delete.
printf 'default via 10.77.0.1 dev usb0\n' >>"$fixture/routes"
expect_pass prepare
check no_network_writes
expect_pass cleanup
check no_network_writes
check test ! -e "$fixture/run/rog5-tailscale-prepared.record"
check test ! -e "$fixture/run/rog5-tailscale/tailscale"
check test ! -e "$fixture/run/rog5-tailscale/tailscaled"

new_case legacy-up
expect_pass prepare
check grep -Fxq 'ip -4 address add 10.77.0.2/30 dev usb0' "$fixture/calls"
check grep -Fxq 'ip -4 route replace default via 10.77.0.1 dev usb0' "$fixture/calls"
printf '2: usb0 inet 10.77.0.2/30 scope global usb0\n' >>"$fixture/addresses"
expect_pass cleanup
check no_route_writes
printf 'default via 10.77.0.1 dev usb0\n' >>"$fixture/routes"
expect_pass cleanup
check grep -Fxq 'ip -4 route del default via 10.77.0.1 dev usb0' "$fixture/calls"
check grep -Fxq 'ip -4 address del 10.77.0.2/30 dev usb0' "$fixture/calls"

new_case legacy-down
printf 'down\n' >"$fixture/sys/class/net/usb0/operstate"
expect_failure prepare 'USB network interface is not up'
check no_network_writes

# Metadata uses the real fixture's mode, size and link count; only UID/GID
# are simulated so these checks also run unprivileged. Content is really hashed.
for invalid in symlink dangling directory fifo hardlink owner group writable \
	executable missing-newline extra-newline wrong-payload nul; do
	new_case "invalid-$invalid"
	case $invalid in
		symlink) seal_marker; mv "$marker" "$fixture/target"; ln -s "$fixture/target" "$marker" ;;
		dangling) ln -s "$fixture/missing" "$marker" ;;
		directory) mkdir "$marker" ;;
		fifo) mkfifo "$marker" ;;
		*)
			seal_marker
			chmod 0644 "$marker"
			case $invalid in
				hardlink) ln "$marker" "$fixture/alias" ;;
				owner) marker_owner=1000:0 ;;
				group) marker_owner=0:1000 ;;
				missing-newline) printf 'rog5-native-wifi-boot-v1' >"$marker" ;;
				extra-newline) printf 'rog5-native-wifi-boot-v1\n\n' >"$marker" ;;
				wrong-payload) printf 'rog5-native-wifi-boot-v2\n' >"$marker" ;;
				nul) printf 'rog5-native-wifi-boot-v1\000' >"$marker" ;;
			esac
			case $invalid in
				writable) chmod 0644 "$marker" ;;
				executable) chmod 0544 "$marker" ;;
				*) chmod 0444 "$marker" ;;
			esac ;;
	esac
	for action in prepare cleanup; do
		expect_failure "$action" 'automatic Wi-Fi marker identity changed'
		check no_network_writes
	done
done

# A valid marker changes only network ownership, not preparation safety gates.
for invalid in noexec digest recovery-address ambiguous-address; do
	new_case "wifi-invalid-$invalid"
	seal_marker
	printf 'down\n' >"$fixture/sys/class/net/usb0/operstate"
	case $invalid in
		noexec) mount_options=rw,nodev,nosuid; reason='persistent state lost noexec' ;;
		digest) bad_digest=1; reason='Tailscale archive identity changed' ;;
		recovery-address) : >"$fixture/addresses"; reason='fixed recovery-compatible address is absent' ;;
		ambiguous-address)
			printf '2: usb0 inet 10.77.0.3/30 scope global usb0\n' >>"$fixture/addresses"
			reason='standalone service address is ambiguous' ;;
	esac
	expect_failure prepare "$reason"
	check no_network_writes
done

[ "$failures" -eq 0 ] || exit 1
echo 'PASS persistent Tailscale: sealed Wi-Fi uplink/rescue, unchanged legacy network, p23/noexec/hash guards'
