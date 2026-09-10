#!/bin/sh
set -eu

guard=rog5-physical-keys-v1
expected_kernel=7.1.4-g7a5cef0db479
expected_udc=a600000.usb
expected_address=169.254.77.2/30
host_address=169.254.77.1
fatal_pattern='(^|[^[:alnum:]_])(Kernel panic|Oops:|BUG:|Unable to handle kernel|Synchronous External Abort|watchdog[[:space:]_-]+bite)([^[:alnum:]_]|$)'

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_ROG5_PHYSICAL_KEYS:-}" = "$guard" ] ||
	fail 'set the exact physical-key execution guard'
rollback_contract=${ROG5_PHYSICAL_KEYS_ROLLBACK_CONTRACT:-disarmed-v1}
case $rollback_contract in
	disarmed-v1) ;;
	armed-v1)
		[ "${ALLOW_ROG5_PHYSICAL_KEYS_ARMED_ROLLBACK:-}" = \
			rog5-physical-keys-armed-rollback-v1 ] ||
			fail 'set the exact armed-rollback physical-key guard'
		;;
	*) fail 'unsupported physical-key rollback contract' ;;
esac

monitor_timeout=${1:-180}
case $monitor_timeout in
	*[!0-9]*|'') fail 'timeout must be an integer' ;;
esac
[ "$monitor_timeout" -ge 30 ] && [ "$monitor_timeout" -le 300 ] ||
	fail 'timeout must be between 30 and 300 seconds'

backend=target
fixture_root=
if [ "${ROG5_PHYSICAL_KEYS_TESTING:-}" = 1 ]; then
	backend=fixture
	fixture_root=${ROG5_PHYSICAL_KEYS_FIXTURE_ROOT:-}
	[ "$(id -u)" -ne 0 ] || fail 'fixture backend is forbidden as root'
	[ -n "$fixture_root" ] || fail 'fixture root is required'
	case $fixture_root in
		/*) ;;
		*) fail 'fixture root must be absolute' ;;
	esac
	[ -d "$fixture_root" ] && [ ! -L "$fixture_root" ] ||
		fail 'fixture root must be a non-linked directory'
	[ "$(readlink -f -- "$fixture_root")" = "$fixture_root" ] ||
		fail 'fixture root contains a linked path component'
	[ "$(stat -c '%u:%a' -- "$fixture_root")" = "$(id -u):700" ] ||
		fail 'fixture root must be caller-owned mode 0700'
elif [ -n "${ROG5_PHYSICAL_KEYS_TESTING:-}" ] ||
	[ -n "${ROG5_PHYSICAL_KEYS_FIXTURE_ROOT:-}" ]; then
	fail 'partial fixture configuration is forbidden'
else
	[ "$(id -u)" -eq 0 ] || fail 'target physical-key gate requires root'
fi

for command in awk basename cat chmod date dd dmesg find findmnt grep id ip \
	mktemp od readlink rm sha256sum sort stat systemctl timeout tr uname; do
	command -v "$command" >/dev/null || fail "missing command: $command"
done

safe_fixture_read() {
	path=$1
	[ -f "$path" ] && [ ! -L "$path" ] ||
		fail "fixture field is unsafe or absent: ${path#"$fixture_root"/}"
	[ "$(readlink -f -- "$path")" = "$path" ] ||
		fail "fixture field contains a linked component: ${path#"$fixture_root"/}"
	[ "$(stat -c %s -- "$path")" -le 65536 ] ||
		fail "fixture field is oversized: ${path#"$fixture_root"/}"
	cat -- "$path"
}

target_field() {
	name=$1
	case $name in
		kernel_release) uname -r ;;
		pid1) cat /proc/1/comm ;;
		cmdline) cat /proc/cmdline ;;
		system_state) systemctl is-system-running 2>/dev/null || true ;;
		server_inhibitor)
			systemctl is-active rog5-server-inhibit.service 2>/dev/null || true
			;;
		failed_units)
			systemctl --failed --no-legend --plain |
				awk 'NF { count++ } END { print count + 0 }'
			;;
		root_fstype) findmnt -n -o FSTYPE / 2>/dev/null || true ;;
		run_fstype) findmnt -n -o FSTYPE /run 2>/dev/null || true ;;
		nfs_source) findmnt -n -o SOURCE /.rog5/root-ro 2>/dev/null || true ;;
		nfs_options) findmnt -n -o OPTIONS /.rog5/root-ro 2>/dev/null || true ;;
		physical_blocks)
			if [ ! -d /sys/class/block ]; then
				echo invalid
			else
				find /sys/class/block -mindepth 1 -maxdepth 1 -type l \
					-exec test -e {}/device \; -print 2>/dev/null |
					awk 'END { print NR + 0 }'
			fi
			;;
		block_mounts)
			findmnt -rn -o SOURCE |
				awk '/^\/dev\// { count++ } END { print count + 0 }'
			;;
		watchdog_pid)
			if [ -e /run/rog5-network-root-watchdog.pid ]; then
				echo 1
			else
				echo 0
			fi
			;;
		watchdog_disarmed)
			if [ -s /run/rog5-network-root-watchdog.disarmed.pid ]; then
				echo 1
			else
				echo 0
			fi
			;;
		udcs)
			if [ -d /sys/class/udc ]; then
				find /sys/class/udc -mindepth 1 -maxdepth 1 \
					-printf '%f\n' 2>/dev/null | sort
			fi
			;;
		bound_udc)
			path=/sys/kernel/config/usb_gadget/rog5-network-root/UDC
			if [ -r "$path" ]; then cat "$path"; else echo absent; fi
			;;
		usb0_present)
			if [ -d /sys/class/net/usb0 ]; then echo 1; else echo 0; fi
			;;
		carrier)
			if [ -r /sys/class/net/usb0/carrier ]; then
				cat /sys/class/net/usb0/carrier
			else
				echo absent
			fi
			;;
		addresses)
			ip -4 -o address show dev usb0 2>/dev/null |
				awk '{ print $4 }' || true
			;;
		route) ip -4 route get "$host_address" 2>/dev/null || true ;;
		fatal_count)
			dmesg | grep -Ec "$fatal_pattern" || true
			;;
		warning_digest)
			dmesg --level=emerg,alert,crit,err,warn | sha256sum |
				awk '{ print $1 }'
			;;
		*) fail "unsupported runtime field: $name" ;;
	esac
}

field() {
	phase=$1
	name=$2
	if [ "$backend" = fixture ]; then
		path=$fixture_root/$phase/$name
		if [ ! -e "$path" ]; then
			path=$fixture_root/pre/$name
		fi
		safe_fixture_read "$path"
	else
		target_field "$name"
	fi
}

route_is_exact() {
	printf '%s\n' "$1" | awk -v host="$host_address" '
		$1 != host { bad = 1; exit }
		{
			for (i = 1; i <= NF; i++) {
				if ($i == "via") { bad = 1; exit }
				if ($i == "dev") {
					dev_count++
					if ($(i + 1) != "usb0") { bad = 1; exit }
				}
				if ($i == "src") {
					src_count++
					if ($(i + 1) != "169.254.77.2") { bad = 1; exit }
				}
			}
		}
		END { exit (bad || dev_count != 1 || src_count != 1) }
	'
}

check_link() {
	phase=$1
	udcs=$(field "$phase" udcs)
	if [ "$udcs" != "$expected_udc" ]; then
		[ "$phase" = pre ] && fail 'expected exactly one expected UDC'
		fail 'post-return UDC loss'
	fi
	if [ "$(field "$phase" bound_udc)" != "$expected_udc" ]; then
		[ "$phase" = pre ] &&
			fail 'network-root gadget is not bound to the expected UDC'
		fail 'post-return UDC binding loss'
	fi
	if [ "$(field "$phase" usb0_present)" != 1 ]; then
		[ "$phase" = pre ] && fail 'usb0 is absent'
		fail 'post-return interface loss'
	fi
	if [ "$(field "$phase" carrier)" != 1 ]; then
		[ "$phase" = pre ] && fail 'USB network carrier is down'
		fail 'post-return carrier loss'
	fi
	if [ "$(field "$phase" addresses)" != "$expected_address" ]; then
		[ "$phase" = pre ] && fail 'USB network address is not exact'
		fail 'post-return address loss'
	fi
	if ! route_is_exact "$(field "$phase" route)"; then
		[ "$phase" = pre ] && fail 'direct USB route is not exact'
		fail 'post-return route loss'
	fi
}

check_preconditions() {
	[ "$(field pre kernel_release)" = "$expected_kernel" ] ||
		fail 'unexpected kernel'
	[ "$(field pre pid1)" = systemd ] || fail 'PID 1 is not systemd'
	case $(field pre cmdline) in
		*systemd.mask=*) fail 'physical input acceptance requires normal unmasked mode' ;;
	esac
	[ "$(field pre system_state)" = running ] || fail 'systemd is not running'
	[ "$(field pre server_inhibitor)" = active ] ||
		fail 'server inhibitor is not active'
	[ "$(field pre failed_units)" = 0 ] || fail 'systemd has failed units'
	[ "$(field pre root_fstype)" = overlay ] || fail 'root is not OverlayFS'
	[ "$(field pre run_fstype)" = tmpfs ] || fail '/run is not tmpfs'
	[ "$(field pre nfs_source)" = 169.254.77.1:/ ] ||
		fail 'unexpected NFS lower source'
	printf '%s\n' "$(field pre nfs_options)" | tr ',' '\n' | grep -qx ro ||
		fail 'NFS lower is not read-only'
	[ "$(field pre physical_blocks)" = 0 ] ||
		fail 'physical block device is present'
	[ "$(field pre block_mounts)" = 0 ] || fail 'block-backed mount is present'
	if [ "$rollback_contract" = armed-v1 ]; then
		[ "$(field pre watchdog_pid)" = 1 ] ||
			fail 'network-root rollback watchdog is not armed'
		[ "$(field pre watchdog_disarmed)" = 0 ] ||
			fail 'network-root rollback has a premature disarm marker'
	else
		[ "$(field pre watchdog_pid)" = 0 ] ||
			fail 'network-root rollback watchdog is still armed'
		[ "$(field pre watchdog_disarmed)" = 1 ] ||
			fail 'network-root rollback has no disarm marker'
	fi
	[ "$(field pre fatal_count)" = 0 ] ||
		fail 'fatal kernel signature is present before the key test'
	check_link pre
}

fixture_key_field() {
	key=$1
	name=$2
	safe_fixture_read "$fixture_root/keys/$key/$name"
}

discover_target_key() {
	key=$1
	case $key in
		power) expected_name=pmic_pwrkey ;;
		volume-down) expected_name=pmic_resin ;;
		volume-up) expected_name=gpio-keys ;;
		*) fail "unsupported key: $key" ;;
	esac

	discovered_count=0
	discovered_event=
	discovered_name=
	discovered_driver=
	discovered_of_node=
	discovered_compatible=
	discovered_wakeup=
	discovered_key_bitmap=
	for event in /sys/class/input/event*; do
		[ -r "$event/device/name" ] || continue
		[ "$(cat "$event/device/name")" = "$expected_name" ] || continue
		discovered_count=$((discovered_count + 1))
		discovered_event=/dev/input/${event##*/}
		discovered_name=$(cat "$event/device/name")
		parent=$event/device/device
		driver_path=$(readlink -f "$parent/driver" 2>/dev/null || true)
		if [ -n "$driver_path" ]; then
			discovered_driver=$(basename "$driver_path")
		else
			discovered_driver=absent
		fi
		discovered_of_node=$(readlink -f "$parent/of_node" 2>/dev/null || true)
		if [ -r "$parent/of_node/compatible" ]; then
			discovered_compatible=$(tr '\000' '\n' \
				<"$parent/of_node/compatible")
		else
			discovered_compatible=absent
		fi
		if [ -r "$parent/power/wakeup" ]; then
			discovered_wakeup=$(cat "$parent/power/wakeup")
		else
			discovered_wakeup=absent
		fi
		if [ -r "$event/device/capabilities/key" ]; then
			discovered_key_bitmap=$(awk '{$1=$1; print}' \
				"$event/device/capabilities/key")
		else
			discovered_key_bitmap=absent
		fi
	done
}

load_key() {
	key=$1
	if [ "$backend" = fixture ]; then
		key_count=$(fixture_key_field "$key" count)
		key_name=$(fixture_key_field "$key" name)
		key_driver=$(fixture_key_field "$key" driver)
		key_of_node=$(fixture_key_field "$key" of_node)
		key_compatible=$(fixture_key_field "$key" compatible)
		key_wakeup=$(fixture_key_field "$key" wakeup)
		key_bitmap=$(fixture_key_field "$key" key_bitmap)
		key_event=$fixture_root/events/$key
	else
		discover_target_key "$key"
		key_count=$discovered_count
		key_name=$discovered_name
		key_driver=$discovered_driver
		key_of_node=$discovered_of_node
		key_compatible=$discovered_compatible
		key_wakeup=$discovered_wakeup
		key_bitmap=$discovered_key_bitmap
		key_event=$discovered_event
	fi
}

validate_key() {
	key=$1
	load_key "$key"
	case $key in
		power)
			expected_name=pmic_pwrkey
			expected_driver=pm8941-pwrkey
			expected_suffix=/soc@0/spmi@c440000/pmic@0/pon@1300/pwrkey
			expected_compatible=qcom,pmk8350-pwrkey
			expected_wakeup=enabled
			expected_bitmap='10000000000000 0'
			;;
		volume-down)
			expected_name=pmic_resin
			expected_driver=pm8941-pwrkey
			expected_suffix=/soc@0/spmi@c440000/pmic@0/pon@1300/resin
			expected_compatible=qcom,pmk8350-resin
			expected_wakeup=absent
			expected_bitmap='4000000000000 0'
			;;
		volume-up)
			expected_name=gpio-keys
			expected_driver=gpio-keys
			expected_suffix=/gpio-keys
			expected_compatible=gpio-keys
			expected_wakeup=enabled
			expected_bitmap='8000000000000 0'
			;;
	esac
	[ "$key_count" = 1 ] || fail "expected exactly one $key input"
	[ "$key_name" = "$expected_name" ] || fail "$key input name changed"
	[ "$key_driver" = "$expected_driver" ] || fail "$key driver changed"
	case $key_of_node in
		*"$expected_suffix") ;;
		*) fail "$key OF node changed" ;;
	esac
	[ "$key_compatible" = "$expected_compatible" ] ||
		fail "$key compatible changed"
	[ "$key_wakeup" = "$expected_wakeup" ] ||
		fail "$key wake policy changed"
	[ "$key_bitmap" = "$expected_bitmap" ] ||
		fail "$key key capability changed"
	if [ "$backend" = fixture ]; then
		[ -f "$key_event" ] && [ ! -L "$key_event" ] ||
			fail "$key fixture event stream is unsafe"
	else
		[ -c "$key_event" ] && [ -r "$key_event" ] ||
			fail "$key input event is not a readable character device"
	fi
	case $key in
		power)
			power_event=$key_event
			;;
		volume-down)
			volume_down_event=$key_event
			;;
		volume-up)
			volume_up_event=$key_event
			;;
	esac
}

irq_count() {
	key=$1
	phase=$2
	if [ "$backend" = fixture ]; then
		fixture_key_field "$key" "irq_$phase"
		return
	fi
	case $key in
		power) label=pmic_pwrkey ;;
		volume-down) label=pmic_resin ;;
		volume-up) label=volume_up ;;
	esac
	awk -v label="$label" '
		$NF == label {
			matches++
			for (i = 2; i < NF; i++)
				if ($i ~ /^[0-9]+$/) total += $i
		}
		END {
			if (matches != 1) exit 1
			printf "%.0f\n", total
		}
	' /proc/interrupts || fail "$key IRQ identity changed"
}

accept_event() {
	event_type=$1
	event_code=$2
	event_value=$3
	[ "$event_type" = 1 ] || return 0
	[ "$event_code" = "$current_code" ] ||
		fail "$current_key emitted an unexpected key code"
	case $event_value in
		1)
			[ "$pressed" -eq 0 ] || fail "$current_key emitted a duplicate press"
			pressed=1
			press_count=$((press_count + 1))
			echo "PASS key=$current_key phase=press code=$current_code"
			;;
		0)
			[ "$pressed" -eq 1 ] ||
				fail "$current_key release arrived before its press"
			release_count=$((release_count + 1))
			complete=1
			echo "PASS key=$current_key phase=release code=$current_code"
			;;
		2) fail "$current_key autorepeat is forbidden" ;;
		*) fail "$current_key emitted an invalid key value" ;;
	esac
}

capture_fixture_key() {
	while IFS=' ' read -r event_type event_code event_value extra; do
		[ -z "${extra:-}" ] && [ -n "${event_type:-}" ] &&
			[ -n "${event_code:-}" ] && [ -n "${event_value:-}" ] ||
			fail "$current_key fixture event is malformed"
		accept_event "$event_type" "$event_code" "$event_value"
		[ "$complete" -eq 0 ] || break
	done <"$current_event"
}

capture_target_key() {
	deadline=$(( $(date +%s) + monitor_timeout ))
	while [ "$complete" -eq 0 ]; do
		now=$(date +%s)
		remaining=$((deadline - now))
		[ "$remaining" -gt 0 ] || fail "$current_key event timeout"
		record=$runtime_dir/input-event
		if ! timeout --foreground "$remaining" dd of="$record" \
			bs=24 count=1 status=none <&7; then
			fail "$current_key event timeout"
		fi
		[ "$(stat -c %s -- "$record")" = 24 ] ||
			fail "$current_key input event is truncated"
		set -- $(od -An -j 16 -N 8 -t u2 "$record")
		[ "$#" -eq 4 ] || fail "$current_key input event is malformed"
		[ "$4" = 0 ] || fail "$current_key input event value is negative"
		accept_event "$1" "$2" "$3"
	done
}

capture_key() {
	current_key=$1
	current_code=$2
	current_event=$3
	pressed=0
	complete=0
	press_count=0
	release_count=0
	if [ "$backend" = target ]; then
		exec 7<"$current_event" ||
			fail "$current_key input event cannot be opened"
	fi
	echo "READY key=$current_key code=$current_code timeout=$monitor_timeout"
	if [ "$backend" = fixture ]; then
		capture_fixture_key
	else
		capture_target_key
		exec 7<&-
	fi
	[ "$complete" -eq 1 ] && [ "$press_count" -eq 1 ] &&
		[ "$release_count" -eq 1 ] ||
		fail "$current_key event stream ended before press and release"
}

check_postconditions() {
	check_link post
	[ "$(field post kernel_release)" = "$expected_kernel" ] ||
		fail 'kernel identity changed during the key test'
	[ "$(field post system_state)" = running ] ||
		fail 'systemd did not remain running after the key test'
	[ "$(field post server_inhibitor)" = active ] ||
		fail 'server inhibitor did not remain active after the key test'
	[ "$(field post failed_units)" = 0 ] ||
		fail 'systemd gained a failed unit during the key test'
	[ "$(field post root_fstype)" = overlay ] ||
		fail 'root filesystem changed during the key test'
	[ "$(field post nfs_source)" = 169.254.77.1:/ ] ||
		fail 'NFS lower source changed during the key test'
	printf '%s\n' "$(field post nfs_options)" | tr ',' '\n' | grep -qx ro ||
		fail 'NFS lower became writable during the key test'
	[ "$(field post physical_blocks)" = 0 ] ||
		fail 'physical block device appeared during the key test'
	[ "$(field post block_mounts)" = 0 ] ||
		fail 'block-backed mount appeared during the key test'
	if [ "$rollback_contract" = armed-v1 ]; then
		[ "$(field post watchdog_pid)" = 1 ] ||
			fail 'rollback watchdog disappeared during the key test'
		[ "$(field post watchdog_disarmed)" = 0 ] ||
			fail 'rollback watchdog was disarmed during the key test'
	else
		[ "$(field post watchdog_pid)" = 0 ] ||
			fail 'rollback watchdog rearmed during the key test'
		[ "$(field post watchdog_disarmed)" = 1 ] ||
			fail 'rollback disarm evidence disappeared during the key test'
	fi
	[ "$(field post fatal_count)" = 0 ] ||
		fail 'fatal kernel signature appeared during the key test'
	[ "$(field post warning_digest)" = "$warning_before" ] ||
		fail 'kernel warning state changed during the key test'
}

check_preconditions
validate_key power
validate_key volume-down
validate_key volume-up

if [ "$backend" = fixture ]; then
	runtime_parent=$fixture_root
else
	runtime_parent=/run
fi
runtime_dir=$(mktemp -d "$runtime_parent/rog5-physical-keys.XXXXXX")
chmod 0700 "$runtime_dir"
trap 'rm -rf -- "$runtime_dir"' 0 HUP INT TERM

warning_before=$(field pre warning_digest)
power_irq_before=$(irq_count power before)
volume_down_irq_before=$(irq_count volume-down before)
volume_up_irq_before=$(irq_count volume-up before)

capture_key power 116 "$power_event"
capture_key volume-down 114 "$volume_down_event"
capture_key volume-up 115 "$volume_up_event"

power_irq_after=$(irq_count power after)
volume_down_irq_after=$(irq_count volume-down after)
volume_up_irq_after=$(irq_count volume-up after)

power_irq_delta=$((power_irq_after - power_irq_before))
volume_down_irq_delta=$((volume_down_irq_after - volume_down_irq_before))
volume_up_irq_delta=$((volume_up_irq_after - volume_up_irq_before))

for key_delta in \
	"power:$power_irq_delta" \
	"volume-down:$volume_down_irq_delta" \
	"volume-up:$volume_up_irq_delta"; do
	key=${key_delta%%:*}
	delta=${key_delta#*:}
	[ "$delta" -ge 2 ] || fail "$key IRQ did not advance twice"
	[ "$delta" -le 16 ] || fail "$key IRQ delta exceeds the bounce bound"
done

check_postconditions

echo "PASS physical keys events=power:1/1,volume-down:1/1,volume-up:1/1 irq_deltas=$power_irq_delta,$volume_down_irq_delta,$volume_up_irq_delta wake_sources=power,volume-up resin_wake=off writes=0 suspend=0 rollback=$rollback_contract backend=$backend"
