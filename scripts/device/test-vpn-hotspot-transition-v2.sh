#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
target=$repo/scripts/device/vpn-hotspot-v2.sh
service=$repo/packaging/arch/rog5-vpn-hotspot-v2.service

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ -x "$target" ] || fail "missing v2 VPN-hotspot control: $target"
[ -f "$service" ] && [ ! -L "$service" ] ||
	fail "missing v2 VPN-hotspot service: $service"
sh -n "$target"

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT HUP INT TERM
mkdir -p "$stage/bin" "$stage/mock" "$stage/runtime"
printf '0\n' >"$stage/mock/ipv4"
printf '0\n' >"$stage/mock/ipv6"
: >"$stage/mock/log"

cat >"$stage/bin/ip" <<'EOF'
#!/bin/sh
set -eu
[ "$#" -eq 5 ]
[ "$1" = link ]
[ "$2" = show ]
[ "$3" = dev ]
EOF

cat >"$stage/bin/wg" <<'EOF'
#!/bin/sh
set -eu
[ "$#" -eq 2 ]
[ "$1" = show ]
EOF

cat >"$stage/bin/sysctl" <<'EOF'
#!/bin/sh
set -eu
case ${1:-} in
	-n)
		[ "$#" -eq 2 ]
		case $2 in
			net.ipv4.ip_forward) cat "$MOCK_DIR/ipv4" ;;
			net.ipv6.conf.all.forwarding) cat "$MOCK_DIR/ipv6" ;;
			*) exit 2 ;;
		esac
		;;
	-qw)
		[ "$#" -eq 2 ]
		printf 'sysctl-set %s\n' "$2" >>"$MOCK_DIR/log"
		[ "${FAIL_SYSCTL_ASSIGNMENT:-}" != "$2" ] || exit 19
		case $2 in
			net.ipv4.ip_forward=*)
				printf '%s\n' "${2#*=}" >"$MOCK_DIR/ipv4"
				;;
			net.ipv6.conf.all.forwarding=*)
				printf '%s\n' "${2#*=}" >"$MOCK_DIR/ipv6"
				;;
			*) exit 2 ;;
		esac
		;;
	*) exit 2 ;;
esac
EOF

cat >"$stage/bin/nft" <<'EOF'
#!/bin/sh
set -eu
case ${1:-} in
	list)
		[ "$#" -eq 4 ]
		[ "$2" = table ] && [ "$3" = inet ]
		[ -e "$MOCK_DIR/table" ]
		;;
	-f)
		[ "$#" -eq 2 ]
		printf 'nft-load\n' >>"$MOCK_DIR/log"
		[ "${FAIL_NFT_LOAD:-0}" != 1 ] || exit 18
		printf 'v2\n' >"$MOCK_DIR/table"
		;;
	delete)
		[ "$#" -eq 5 ]
		[ "$2" = table ] && [ "$3" = inet ]
		printf 'nft-delete\n' >>"$MOCK_DIR/log"
		rm -f "$MOCK_DIR/table"
		;;
	*) exit 2 ;;
esac
EOF
chmod 0755 "$stage/bin"/*

run_target() {
	PATH="$stage/bin:$PATH" \
	MOCK_DIR="$stage/mock" \
	ROG5_VPN_HOTSPOT_RUNTIME="$stage/runtime" \
	FAIL_NFT_LOAD="${FAIL_NFT_LOAD:-0}" \
	FAIL_SYSCTL_ASSIGNMENT="${FAIL_SYSCTL_ASSIGNMENT:-}" \
	AP_IF=wlan0 VPN_IF=wg0 \
		"$target" "$@"
}

assert_clean() {
	[ "$(cat "$stage/mock/ipv4")" = 0 ]
	[ "$(cat "$stage/mock/ipv6")" = 0 ]
	[ ! -e "$stage/mock/table" ]
	[ ! -e "$stage/runtime/sysctl.state" ]
	[ ! -e "$stage/runtime/rules.nft" ]
}

: >"$stage/mock/log"
run_target up >/dev/null
run_target check >/dev/null
[ "$(cat "$stage/mock/ipv4")" = 1 ]
[ "$(cat "$stage/mock/ipv6")" = 1 ]
[ "$(cat "$stage/mock/table")" = v2 ]
load_line=$(awk '$1 == "nft-load" { print NR; exit }' "$stage/mock/log")
forward_line=$(awk '$1 == "sysctl-set" && $2 ~ /=1$/ { print NR; exit }' \
	"$stage/mock/log")
[ -n "$load_line" ] && [ -n "$forward_line" ]
[ "$load_line" -lt "$forward_line" ] ||
	fail 'forwarding changed before the kill-switch was installed'
run_target down >/dev/null
assert_clean

: >"$stage/mock/log"
FAIL_NFT_LOAD=1
export FAIL_NFT_LOAD
if run_target up >/dev/null 2>&1; then
	fail 'nftables load failure was accepted'
fi
unset FAIL_NFT_LOAD
assert_clean

: >"$stage/mock/log"
FAIL_SYSCTL_ASSIGNMENT=net.ipv6.conf.all.forwarding=1
export FAIL_SYSCTL_ASSIGNMENT
if run_target up >/dev/null 2>&1; then
	fail 'partial forwarding failure was accepted'
fi
unset FAIL_SYSCTL_ASSIGNMENT
assert_clean

: >"$stage/mock/log"
printf 'original\n' >"$stage/mock/table"
if run_target up >/dev/null 2>&1; then
	fail 'pre-existing kill-switch table was replaced'
fi
[ "$(cat "$stage/mock/table")" = original ]
[ ! -s "$stage/mock/log" ]
[ ! -e "$stage/runtime/sysctl.state" ]
[ ! -e "$stage/runtime/rules.nft" ]
rm -f "$stage/mock/table"
assert_clean

start_line=$(grep -nFx \
	'ExecStart=/usr/local/sbin/rog5-vpn-hotspot.sh up' "$service" |
	cut -d: -f1)
ap_up_line=$(grep -nFx \
	'ExecStartPost=/usr/bin/nmcli connection up rog5-hotspot' "$service" |
	cut -d: -f1)
ap_cleanup_line=$(grep -nFx \
	'ExecStopPost=-/usr/bin/nmcli connection down rog5-hotspot' "$service" |
	cut -d: -f1)
firewall_cleanup_line=$(grep -nFx \
	'ExecStopPost=/usr/local/sbin/rog5-vpn-hotspot.sh down' "$service" |
	cut -d: -f1)
for line in "$start_line" "$ap_up_line" "$ap_cleanup_line" \
	"$firewall_cleanup_line"; do
	[ -n "$line" ] || fail 'service transition line is missing'
done
[ "$start_line" -lt "$ap_up_line" ] ||
	fail 'AP starts before the kill-switch command'
[ "$ap_cleanup_line" -lt "$firewall_cleanup_line" ] ||
	fail 'failure cleanup removes the firewall before lowering the AP'
[ "$(grep -Fc 'ExecStopPost=' "$service")" -eq 2 ] ||
	fail 'service must have exactly two ordered post-stop cleanup commands'

if grep -Eq \
	'(^|[;&|[:space:]])(fastboot|adb|ssh|scp)([[:space:]]|$)|dd[[:space:]].*of=/dev/' \
	"$target" "$service"
then
	fail 'v2 hotspot transition controls the phone or storage'
fi

echo 'PASS v2 VPN-hotspot installs the kill-switch before forwarding, rejects replacement, rolls back partial failure, and lowers AP before firewall cleanup'
