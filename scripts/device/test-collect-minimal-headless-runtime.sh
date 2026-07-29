#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
probe=$repo/scripts/device/collect-minimal-headless-runtime.sh
[ -x "$probe" ] || {
	echo 'FAIL missing minimal-headless runtime probe' >&2
	exit 1
}
sh -n "$probe"

stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
root=$stage/root
mock_bin=$stage/bin
mkdir -p "$mock_bin" \
	"$root/etc/ssh" \
	"$root/proc/1" \
	"$root/proc/42/fd" \
	"$root/proc/43" \
	"$root/proc/self" \
	"$root/proc/sys/kernel/random" \
	"$root/root/.ssh" \
	"$root/run" \
	"$root/sys/class/block" \
	"$root/sys/class/net/usb0" \
	"$root/sys/class/thermal" \
	"$root/sys/dev/block" \
	"$root/.rog5/root-ro/etc/rog5" \
	"$root/.rog5/state"

install -m 0600 "$repo/configs/ssh/rog5-headless-build-fixture.pub" \
	"$root/root/.ssh/authorized_keys"
printf '%s\n' 'root:!:19800:0:99999:7:::' >"$root/etc/shadow"
printf '%s\n' fixture-private-host-key \
	>"$root/etc/ssh/ssh_host_ed25519_key"
printf '%s\n' fixture-public-host-key \
	>"$root/etc/ssh/ssh_host_ed25519_key.pub"
chmod 0600 "$root/etc/ssh/ssh_host_ed25519_key"
chmod 0644 "$root/etc/ssh/ssh_host_ed25519_key.pub"

printf '%s\n' systemd >"$root/proc/1/comm"
printf '%s\n' 7d9a6f34-0e4a-4d4e-9d24-0b1f6c7215a8 \
	>"$root/proc/sys/kernel/random/boot_id"
cat >"$root/proc/meminfo" <<'EOF'
MemTotal:       11900000 kB
MemAvailable:   10949632 kB
EOF
: >"$root/proc/self/mountinfo"
printf '%s\n' 200.50 >"$root/proc/uptime"

printf '%s\n' \
	'42 (init) S 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 1234' \
	>"$root/proc/42/stat"
printf '%s\n' init >"$root/proc/42/comm"
ln -s /dev/kmsg "$root/proc/42/fd/8"
ln -s /proc/sysrq-trigger "$root/proc/42/fd/9"
printf '%s\n' \
	'43 (sleep) S 42 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 5678' \
	>"$root/proc/43/stat"
printf '%s\n' sleep >"$root/proc/43/comm"

printf '%s\n' 1 >"$root/sys/class/net/usb0/carrier"
zone=0
while [ "$zone" -lt 33 ]; do
	mkdir -p "$root/sys/class/thermal/thermal_zone$zone"
	printf '%s\n' "$((32000 + zone * 100))" \
		>"$root/sys/class/thermal/thermal_zone$zone/temp"
	zone=$((zone + 1))
done

printf '%s\n' 'fixture sealed root' \
	>"$root/.rog5/root-ro/.rog5-persistent-seal"
root_seal_sha256=$(
	sha256sum "$root/.rog5/root-ro/.rog5-persistent-seal" |
		awk '{ print $1 }'
)
cat >"$root/.rog5/root-ro/etc/rog5/a660-command-manifest" <<'EOF'
format=rog5-headless-command-manifest-v1
workload=none
EOF
command_manifest_sha256=$(
	sha256sum "$root/.rog5/root-ro/etc/rog5/a660-command-manifest" |
		awk '{ print $1 }'
)
cat >"$root/run/rog5-network-root-identity" <<EOF
format=rog5-network-root-identity-v1
overlay_mount_id=101
overlay_lower_mount_id=102
state_mount_id=103
overlay_lower_path=/mnt/root-ro
command_manifest_sha256=$command_manifest_sha256
root_generation=arch-a
root_tree_sha256=1111111111111111111111111111111111111111111111111111111111111111
root_seal_sha256=$root_seal_sha256
root_tree_entries=37669
root_subtree=/
EOF
chmod 0400 "$root/run/rog5-network-root-identity"

printf '%s\n' 0 >"$root/run/rog5-physical-block-count"
printf '%s\n' 169.254.77.1:/ >"$root/run/rog5-network-root-source"
: >"$root/run/rog5-network-root-mounted"
printf '%s\n' 42 >"$root/run/rog5-network-root-watchdog.pid"
cat >"$root/run/rog5-network-root-watchdog.lease" <<'EOF'
format=rog5-network-root-watchdog-v1
pid=42
start_time_ticks=1234
timer_pid=43
timer_start_time_ticks=5678
armed_boottime_seconds=100
deadline_boottime_seconds=700
timeout_seconds=600
EOF
chmod 0400 "$root/run/rog5-network-root-watchdog.pid" \
	"$root/run/rog5-network-root-watchdog.lease"

printf '%s\n' ro,nosuid,nodev >"$root/run/mock-lower-options"
printf '%s\n' no >"$root/run/mock-password-authentication"
printf '%s\n' '2: usb0    inet 169.254.77.2/30 scope global usb0' \
	>"$root/run/mock-ip-addresses"

cat >"$mock_bin/uname" <<'EOF'
#!/bin/sh
case ${1:-} in
	-r) echo 7.1.4-g7a5cef0db479 ;;
	-m) echo aarch64 ;;
	*) exit 1 ;;
esac
EOF
cat >"$mock_bin/nproc" <<'EOF'
#!/bin/sh
echo 8
EOF
cat >"$mock_bin/systemctl" <<'EOF'
#!/bin/sh
case $* in
	"is-system-running") echo running ;;
	"get-default") echo multi-user.target ;;
	"is-active sshd.service"|"is-active rog5-server-inhibit.service")
		echo active
		;;
	"--failed --no-legend --plain") : ;;
	*) exit 1 ;;
esac
EOF
cat >"$mock_bin/findmnt" <<'EOF'
#!/bin/sh
case $* in
	"-n -o FSTYPE /") echo overlay ;;
	"-n -o SOURCE /.rog5/root-ro") echo 169.254.77.1:/ ;;
	"-n -o OPTIONS /.rog5/root-ro")
		cat "$MOCK_ROOT/run/mock-lower-options"
		;;
	"-n -o FSTYPE /.rog5/state") echo tmpfs ;;
	"-n -o OPTIONS /.rog5/state") echo rw,nodev,nosuid ;;
	*) exit 1 ;;
esac
EOF
cat >"$mock_bin/ip" <<'EOF'
#!/bin/sh
cat "$MOCK_ROOT/run/mock-ip-addresses"
EOF
cat >"$mock_bin/sshd" <<'EOF'
#!/bin/sh
echo "passwordauthentication $(cat "$MOCK_ROOT/run/mock-password-authentication")"
echo 'kbdinteractiveauthentication no'
echo 'pubkeyauthentication yes'
echo 'permitrootlogin prohibit-password'
EOF
cat >"$mock_bin/dmesg" <<'EOF'
#!/bin/sh
:
EOF
chmod 0755 "$mock_bin"/*

run_probe() {
	PATH="$mock_bin:$PATH" \
	MOCK_ROOT="$root" \
	ROG5_RUNTIME_TEST_MODE=1 \
	ROG5_RUNTIME_ROOT="$root" \
		"$probe"
}

expect_failure() {
	label=$1
	set +e
	run_probe >"$stage/rejected-record" 2>"$stage/rejected-error"
	status=$?
	set -e
	[ "$status" -ne 0 ] || {
		echo "FAIL runtime probe accepted mutation: $label" >&2
		exit 1
	}
	grep -q '^FAIL ' "$stage/rejected-error" || {
		echo "FAIL runtime probe mutation lacked refusal: $label" >&2
		exit 1
	}
}

record=$stage/runtime.record
run_probe >"$record"
[ "$(wc -l <"$record")" -eq 48 ]
grep -Fxq 'format=rog5-minimal-headless-runtime-v1' "$record"
grep -Fxq 'profile=minimal-headless-v1' "$record"
grep -Fxq 'execution_mode=test' "$record"
grep -Fxq 'cpu_online_count=8' "$record"
grep -Fxq 'memory_available_kib=10949632' "$record"
grep -Fxq 'physical_block_devices=0' "$record"
grep -Fxq 'block_backed_mounts=0' "$record"
grep -Fxq 'thermal_zone_count=33' "$record"
grep -Fxq 'watchdog_state=armed' "$record"
grep -Fxq 'watchdog_remaining_seconds=500' "$record"
grep -Fxq 'workload=none' "$record"
[ "$(tail -n 1 "$record")" = result=PASS ]

printf '%s\n' rw,nodev,nosuid >"$root/run/mock-lower-options"
expect_failure 'writable NFS lower'
printf '%s\n' ro,nodev,nosuid >"$root/run/mock-lower-options"

mkdir -p "$root/sys/devices/fake-block/device"
ln -s ../../devices/fake-block "$root/sys/class/block/sda"
expect_failure 'physical block topology'
rm -f "$root/sys/class/block/sda"

mv "$root/sys/class/block" "$root/sys/class/block.absent"
expect_failure 'absent block topology source'
mv "$root/sys/class/block.absent" "$root/sys/class/block"

printf '%s\n' \
	'2: usb0    inet 169.254.77.2/30 scope global usb0' \
	'2: usb0    inet 192.0.2.2/24 scope global usb0' \
	>"$root/run/mock-ip-addresses"
expect_failure 'additional USB IPv4 address'
printf '%s\n' '2: usb0    inet 169.254.77.2/30 scope global usb0' \
	>"$root/run/mock-ip-addresses"

printf '%s\n' 800.00 >"$root/proc/uptime"
expect_failure 'expired watchdog'
printf '%s\n' 200.50 >"$root/proc/uptime"

mv "$root/sys/class/thermal" "$root/sys/class/thermal.absent"
mkdir "$root/sys/class/thermal"
expect_failure 'absent thermal telemetry'
rm -rf "$root/sys/class/thermal"
mv "$root/sys/class/thermal.absent" "$root/sys/class/thermal"

printf '%s\n' yes >"$root/run/mock-password-authentication"
expect_failure 'password-enabled SSH'
printf '%s\n' no >"$root/run/mock-password-authentication"

printf '%s\n' 'format=rog5-headless-command-manifest-v1' 'workload=shell' \
	>"$root/.rog5/root-ro/etc/rog5/a660-command-manifest"
expect_failure 'changed command manifest'
printf '%s\n' 'format=rog5-headless-command-manifest-v1' 'workload=none' \
	>"$root/.rog5/root-ro/etc/rog5/a660-command-manifest"

: >"$root/run/rog5-network-root-watchdog.disarmed.pid"
expect_failure 'disarmed watchdog'
rm -f "$root/run/rog5-network-root-watchdog.disarmed.pid"

echo 'PASS minimal-headless runtime probe emits one canonical read-only observation and rejects nine core mutations'
