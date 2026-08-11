#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
probe=$repo/scripts/device/collect-minimal-headless-runtime.sh
[ -x "$probe" ] || {
	echo 'FAIL missing minimal-headless runtime probe' >&2
	exit 1
}
sh -n "$probe"

target_config=$repo/artifacts/network-root-v3/config-7.1.4-network-root
[ -f "$target_config" ] || {
	echo 'FAIL missing pinned network-root kernel configuration' >&2
	exit 1
}
grep -Fxq 'CONFIG_BLK_DEV_LOOP=y' "$target_config" || {
	echo 'FAIL pinned network-root kernel does not build the loop driver in' >&2
	exit 1
}
grep -Fxq 'CONFIG_BLK_DEV_LOOP_MIN_COUNT=8' "$target_config" || {
	echo 'FAIL pinned network-root loop-device inventory changed' >&2
	exit 1
}
grep -Fxq 'CONFIG_ZRAM=y' "$target_config" || {
	echo 'FAIL pinned network-root kernel does not build zram in' >&2
	exit 1
}

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
	"$root/sys/bus/platform/devices" \
	"$root/sys/class/block" \
	"$root/sys/class/net/usb0" \
	"$root/sys/class/rpmb" \
	"$root/sys/class/scsi_host" \
	"$root/sys/class/thermal" \
	"$root/sys/class/udc/a600000.usb" \
	"$root/sys/devices/virtual/block/zram0" \
	"$root/sys/devices/system/cpu/cpufreq/policy0" \
	"$root/sys/devices/system/cpu/cpufreq/policy4" \
	"$root/sys/devices/system/cpu/cpufreq/policy7" \
	"$root/sys/dev/block" \
	"$root/sys/kernel/config/usb_gadget/rog5-network-root/configs/c.1/strings/0x409" \
	"$root/sys/kernel/config/usb_gadget/rog5-network-root/functions/ncm.usb0" \
	"$root/sys/kernel/config/usb_gadget/rog5-network-root/strings/0x409" \
	"$root/.rog5/root-ro/etc/rog5" \
	"$root/.rog5/state"

loop_index=0
while [ "$loop_index" -lt 8 ]; do
	mkdir -p "$root/sys/devices/virtual/block/loop$loop_index"
	ln -s "../../devices/virtual/block/loop$loop_index" \
		"$root/sys/class/block/loop$loop_index"
	loop_index=$((loop_index + 1))
done
ln -s ../../devices/virtual/block/zram0 "$root/sys/class/block/zram0"
printf '%s\n' 0 >"$root/sys/devices/virtual/block/zram0/disksize"

install -m 0600 "$repo/configs/ssh/rog5-headless-build-fixture.pub" \
	"$root/root/.ssh/authorized_keys"
printf '%s\n' 'root:!:19800:0:99999:7:::' >"$root/etc/shadow"
ssh-keygen -q -t ed25519 -N '' \
	-f "$root/etc/ssh/ssh_host_ed25519_key"
chmod 0600 "$root/etc/ssh/ssh_host_ed25519_key"
chmod 0644 "$root/etc/ssh/ssh_host_ed25519_key.pub"

gadget=$root/sys/kernel/config/usb_gadget/rog5-network-root
printf '%s\n' 0x1d6b >"$gadget/idVendor"
printf '%s\n' 0x0104 >"$gadget/idProduct"
printf '%s\n' 0xef >"$gadget/bDeviceClass"
printf '%s\n' 0x02 >"$gadget/bDeviceSubClass"
printf '%s\n' 0x01 >"$gadget/bDeviceProtocol"
printf '%s\n' a600000.usb >"$gadget/UDC"
printf '%s\n' Linux >"$gadget/strings/0x409/manufacturer"
printf '%s\n' 'ROG5 network root' >"$gadget/strings/0x409/product"
printf '%s\n' 'NFS root over NCM' \
	>"$gadget/configs/c.1/strings/0x409/configuration"
ln -s /sys/kernel/config/usb_gadget/rog5-network-root/functions/ncm.usb0 \
	"$gadget/configs/c.1/ncm.usb0"
printf '%s\n' high-speed \
	>"$root/sys/class/udc/a600000.usb/current_speed"

printf '%s\n' systemd >"$root/proc/1/comm"
printf '%s\n' 7d9a6f34-0e4a-4d4e-9d24-0b1f6c7215a8 \
	>"$root/proc/sys/kernel/random/boot_id"
cat >"$root/proc/meminfo" <<'EOF'
MemTotal:       11900000 kB
MemAvailable:   10949632 kB
EOF
cat >"$root/proc/self/mountinfo" <<'EOF'
101 1 0:101 / / rw - overlay overlay rw,lowerdir=/mnt/root-ro,upperdir=/mnt/state/upper,workdir=/mnt/state/work
102 1 0:102 / /.rog5/root-ro ro - nfs4 169.254.77.1:/ ro,vers=4.2,proto=tcp
103 1 0:103 / /.rog5/state rw,nodev,nosuid - tmpfs tmpfs rw,size=2097152k
EOF
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
printf '%s\n' up >"$root/sys/class/net/usb0/operstate"
printf '%s\n' 1500 >"$root/sys/class/net/usb0/mtu"
printf '%s\n' 0-7 >"$root/sys/devices/system/cpu/online"
printf '%s\n' 0-7 >"$root/sys/devices/system/cpu/present"
printf '%s\n' '0 1 2 3' \
	>"$root/sys/devices/system/cpu/cpufreq/policy0/related_cpus"
printf '%s\n' '4 5 6' \
	>"$root/sys/devices/system/cpu/cpufreq/policy4/related_cpus"
printf '%s\n' 7 \
	>"$root/sys/devices/system/cpu/cpufreq/policy7/related_cpus"
for policy in policy0 policy4 policy7; do
	printf '%s\n' qcom-cpufreq-hw \
		>"$root/sys/devices/system/cpu/cpufreq/$policy/scaling_driver"
	printf '%s\n' schedutil \
		>"$root/sys/devices/system/cpu/cpufreq/$policy/scaling_governor"
done
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

printf '%s\n' nfs4 >"$root/run/mock-lower-fstype"
printf '%s\n' ro,nosuid,nodev,vers=4.2,proto=tcp \
	>"$root/run/mock-lower-options"
printf '%s\n' \
	'rw,lowerdir=/mnt/root-ro,upperdir=/mnt/state/upper,workdir=/mnt/state/work' \
	>"$root/run/mock-root-options"
printf '%s\n' no >"$root/run/mock-password-authentication"
printf '%s\n' 22 >"$root/run/mock-ssh-port"
printf '%s\n' /etc/ssh/ssh_host_ed25519_key \
	>"$root/run/mock-ssh-host-key"
printf '%s\n' '2: usb0    inet 169.254.77.2/30 scope global usb0' \
	>"$root/run/mock-ip-addresses"
printf '%s\n' \
	'169.254.77.0/30 dev usb0 proto kernel scope link src 169.254.77.2' \
	>"$root/run/mock-ip-routes"
: >"$root/run/mock-ip-default-routes"
cat >"$root/run/mock-ip-rules" <<'EOF'
0:	from all lookup local
32766:	from all lookup main
32767:	from all lookup default
EOF
printf '%s\n' \
	'0 0 169.254.77.2:22 169.254.77.1:49152' \
	>"$root/run/mock-ss-sessions"

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
	"-n -o ID /") echo 101 ;;
	"-n -o ID /.rog5/root-ro") echo 102 ;;
	"-n -o ID /.rog5/state") echo 103 ;;
	"-n -o FSTYPE /") echo overlay ;;
	"-n -o OPTIONS /") cat "$MOCK_ROOT/run/mock-root-options" ;;
	"-n -o FSTYPE /.rog5/root-ro")
		cat "$MOCK_ROOT/run/mock-lower-fstype"
		;;
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
case $* in
	"-4 -o address show dev usb0")
		cat "$MOCK_ROOT/run/mock-ip-addresses"
		;;
	"-4 -o route show table main")
		cat "$MOCK_ROOT/run/mock-ip-routes"
		;;
	"-4 -o route show table all default")
		cat "$MOCK_ROOT/run/mock-ip-default-routes"
		;;
	"-4 -o rule show") cat "$MOCK_ROOT/run/mock-ip-rules" ;;
	*) exit 1 ;;
esac
EOF
cat >"$mock_bin/ss" <<'EOF'
#!/bin/sh
case $* in
	"-H -n -t state established")
		cat "$MOCK_ROOT/run/mock-ss-sessions"
		;;
	*) exit 1 ;;
esac
EOF
cat >"$mock_bin/sshd" <<'EOF'
#!/bin/sh
[ "$*" = \
	"-T -C user=root,host=169.254.77.1,addr=169.254.77.1,laddr=169.254.77.2,lport=22" ] ||
	exit 1
echo "passwordauthentication $(cat "$MOCK_ROOT/run/mock-password-authentication")"
echo 'kbdinteractiveauthentication no'
echo 'pubkeyauthentication yes'
echo 'permitrootlogin prohibit-password'
echo "port $(cat "$MOCK_ROOT/run/mock-ssh-port")"
echo "hostkey $(cat "$MOCK_ROOT/run/mock-ssh-host-key")"
EOF
cat >"$mock_bin/dmesg" <<'EOF'
#!/bin/sh
:
EOF
chmod 0755 "$mock_bin"/*

run_probe() {
	runtime_candidate=${1:-headless-network-root-v1}
	PATH="$mock_bin:$PATH" \
	MOCK_ROOT="$root" \
	ROG5_RUNTIME_TEST_MODE=1 \
	ROG5_RUNTIME_ROOT="$root" \
	ROG5_RUNTIME_CANDIDATE="$runtime_candidate" \
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
[ "$(wc -l <"$record")" -eq 88 ]
grep -Fxq 'format=rog5-minimal-headless-runtime-v1' "$record"
grep -Fxq 'profile=minimal-headless-v1' "$record"
grep -Fxq 'execution_mode=test' "$record"
grep -Fxq 'candidate=headless-network-root-v1' "$record"
grep -Fxq 'cpu_online_count=8' "$record"
grep -Fxq 'cpu_online_set=0-7' "$record"
grep -Fxq 'cpu_present_set=0-7' "$record"
grep -Fxq 'cpufreq_policy_count=3' "$record"
grep -Fxq 'cpufreq_policy_names=policy0;policy4;policy7' "$record"
grep -Fxq 'cpufreq_policy_cpu_sets=0 1 2 3;4 5 6;7' "$record"
grep -Fxq \
	'cpufreq_policy_drivers=qcom-cpufreq-hw;qcom-cpufreq-hw;qcom-cpufreq-hw' \
	"$record"
grep -Fxq \
	'cpufreq_policy_governors=schedutil;schedutil;schedutil' "$record"
grep -Fxq 'memory_available_kib=10949632' "$record"
grep -Fxq 'overlay_mount_id=101' "$record"
grep -Fxq 'overlay_lower_mount_id=102' "$record"
grep -Fxq 'state_mount_id=103' "$record"
grep -Fxq 'overlay_lowerdir=/mnt/root-ro' "$record"
grep -Fxq 'overlay_upperdir=/mnt/state/upper' "$record"
grep -Fxq 'overlay_workdir=/mnt/state/work' "$record"
grep -Fxq 'lower_fstype=nfs4' "$record"
grep -Fxq 'lower_nfs_version=4.2' "$record"
grep -Fxq 'lower_transport=tcp' "$record"
grep -Fxq 'block_device_count=9' "$record"
grep -Fxq 'physical_block_devices=0' "$record"
grep -Fxq 'scsi_host_count=0' "$record"
grep -Fxq 'rpmb_device_count=0' "$record"
grep -Fxq 'ufs_platform_device_count=0' "$record"
grep -Fxq 'block_backed_mounts=0' "$record"
grep -Fxq 'usb_gadget=rog5-network-root' "$record"
grep -Fxq 'usb_vid_pid=1d6b:0104' "$record"
grep -Fxq 'usb_product=ROG5 network root' "$record"
grep -Fxq 'usb_configuration=NFS root over NCM' "$record"
grep -Fxq 'usb_function=ncm.usb0' "$record"
grep -Fxq 'usb_udc_controller=a600000' "$record"
grep -Fxq 'usb_current_speed=high-speed' "$record"
grep -Fxq 'usb_operstate=up' "$record"
grep -Fxq 'usb_mtu=1500' "$record"
grep -Fxq 'usb_route_cidr=169.254.77.0/30' "$record"
grep -Fxq 'usb_default_route_count=0' "$record"
grep -Fxq 'ssh_port=22' "$record"
grep -Fxq 'ssh_session_count=1' "$record"
grep -Fxq 'ssh_session_local=169.254.77.2:22' "$record"
grep -Fxq 'ssh_session_peer=169.254.77.1' "$record"
grep -Fxq 'ssh_authorized_key_type=ssh-ed25519' "$record"
grep -Fxq 'ssh_authorized_key_bits=256' "$record"
grep -Fxq 'ssh_host_key_type=ssh-ed25519' "$record"
grep -Fxq 'ssh_host_key_bits=256' "$record"
grep -Fxq 'ssh_host_key_pair_match=1' "$record"
grep -Fxq 'thermal_zone_count=33' "$record"
grep -Fxq 'watchdog_state=armed' "$record"
grep -Fxq 'watchdog_remaining_seconds=500' "$record"
grep -Fxq 'workload=none' "$record"
[ "$(tail -n 1 "$record")" = result=PASS ]

printf '%s\n' rw,nodev,nosuid >"$root/run/mock-lower-options"
expect_failure 'writable NFS lower'
printf '%s\n' ro,nodev,nosuid,vers=4.2,proto=tcp \
	>"$root/run/mock-lower-options"

printf '%s\n' nfs >"$root/run/mock-lower-fstype"
expect_failure 'changed NFS filesystem type'
printf '%s\n' nfs4 >"$root/run/mock-lower-fstype"

printf '%s\n' ro,nodev,nosuid,vers=4.1,proto=tcp \
	>"$root/run/mock-lower-options"
expect_failure 'changed NFS version'
printf '%s\n' ro,nodev,nosuid,vers=4.2,proto=udp \
	>"$root/run/mock-lower-options"
expect_failure 'changed NFS transport'
printf '%s\n' ro,nodev,nosuid,vers=4.2,proto=tcp \
	>"$root/run/mock-lower-options"

sed -i 's/^overlay_mount_id=101$/overlay_mount_id=104/' \
	"$root/run/rog5-network-root-identity"
expect_failure 'changed storage mount identity'
sed -i 's/^overlay_mount_id=104$/overlay_mount_id=101/' \
	"$root/run/rog5-network-root-identity"

printf '%s\n' \
	'rw,lowerdir=/mnt/untrusted-root,upperdir=/mnt/state/upper,workdir=/mnt/state/work' \
	>"$root/run/mock-root-options"
expect_failure 'changed OverlayFS lower directory'
printf '%s\n' \
	'rw,lowerdir=/mnt/root-ro=untrusted,upperdir=/mnt/state/upper,workdir=/mnt/state/work' \
	>"$root/run/mock-root-options"
expect_failure 'suffixed OverlayFS lower directory'
printf '%s\n' \
	'rw,lowerdir=/mnt/root-ro,upperdir=/mnt/untrusted-state,workdir=/mnt/state/work' \
	>"$root/run/mock-root-options"
expect_failure 'changed OverlayFS upper directory'
printf '%s\n' \
	'rw,lowerdir=/mnt/root-ro,upperdir=/mnt/state/upper,workdir=/mnt/untrusted-work' \
	>"$root/run/mock-root-options"
expect_failure 'changed OverlayFS work directory'
printf '%s\n' \
	'rw,lowerdir=/mnt/root-ro,upperdir=/mnt/state/upper,workdir=/mnt/state/work' \
	>"$root/run/mock-root-options"

mkdir -p "$root/sys/devices/fake-block/device"
ln -s ../../devices/fake-block "$root/sys/class/block/sda"
expect_failure 'physical block topology'
rm -f "$root/sys/class/block/sda"

mkdir "$root/sys/devices/virtual/block/loop8"
ln -s ../../devices/virtual/block/loop8 "$root/sys/class/block/loop8"
expect_failure 'additional inert loop device'
rm -f "$root/sys/class/block/loop8"
rmdir "$root/sys/devices/virtual/block/loop8"

rm "$root/sys/class/block/loop7"
expect_failure 'missing inert loop device'
ln -s ../../devices/virtual/block/loop7 "$root/sys/class/block/loop7"

rm "$root/sys/class/block/loop0"
ln -s ../../devices/virtual/block/loop1 "$root/sys/class/block/loop0"
expect_failure 'loop device alias'
rm "$root/sys/class/block/loop0"
ln -s ../../devices/virtual/block/loop0 "$root/sys/class/block/loop0"

mkdir "$root/sys/devices/virtual/block/loop0/loop"
expect_failure 'active loop device'
rmdir "$root/sys/devices/virtual/block/loop0/loop"

printf '%s\n' 4096 >"$root/sys/devices/virtual/block/zram0/disksize"
expect_failure 'active zram device'
printf '%s\n' 0 >"$root/sys/devices/virtual/block/zram0/disksize"

mv "$root/sys/class/block" "$root/sys/class/block.absent"
expect_failure 'absent block topology source'
mv "$root/sys/class/block.absent" "$root/sys/class/block"

mv "$root/sys/class/block" "$root/sys/class/block.real"
ln -s block.real "$root/sys/class/block"
expect_failure 'linked block topology source'
rm -f "$root/sys/class/block"
mv "$root/sys/class/block.real" "$root/sys/class/block"

touch "$root/sys/dev/block/8:0"
printf '%s\n' \
	'104 1 8:0 / /mnt/unexpected rw - ext4 /dev/sda rw' \
	>>"$root/proc/self/mountinfo"
expect_failure 'block-backed mount'
sed -i '$d' "$root/proc/self/mountinfo"
rm -f "$root/sys/dev/block/8:0"

touch "$root/sys/class/scsi_host/host0"
expect_failure 'SCSI host topology'
rm -f "$root/sys/class/scsi_host/host0"

mv "$root/sys/class/scsi_host" "$root/sys/class/scsi_host.real"
ln -s missing-scsi-host-class "$root/sys/class/scsi_host"
expect_failure 'linked SCSI host topology'
rm -f "$root/sys/class/scsi_host"
mv "$root/sys/class/scsi_host.real" "$root/sys/class/scsi_host"

touch "$root/sys/class/rpmb/rpmb0"
expect_failure 'RPMB topology'
rm -f "$root/sys/class/rpmb/rpmb0"

touch "$root/sys/bus/platform/devices/1d84000.ufshc"
expect_failure 'UFS platform device'
rm -f "$root/sys/bus/platform/devices/1d84000.ufshc"

printf '%s\n' \
	'2: usb0    inet 169.254.77.2/30 scope global usb0' \
	'2: usb0    inet 192.0.2.2/24 scope global usb0' \
	>"$root/run/mock-ip-addresses"
expect_failure 'additional USB IPv4 address'
printf '%s\n' '2: usb0    inet 169.254.77.2/30 scope global usb0' \
	>"$root/run/mock-ip-addresses"

printf '%s\n' 0x9999 >"$gadget/idVendor"
expect_failure 'changed USB gadget descriptor'
printf '%s\n' 0x1d6b >"$gadget/idVendor"

mkdir "$root/sys/kernel/config/usb_gadget/unexpected"
expect_failure 'additional USB gadget'
rmdir "$root/sys/kernel/config/usb_gadget/unexpected"

mkdir "$gadget/configs/c.2"
expect_failure 'additional USB gadget configuration'
rmdir "$gadget/configs/c.2"

mkdir "$gadget/functions/acm.usb0"
expect_failure 'additional USB gadget function'
rmdir "$gadget/functions/acm.usb0"

rm "$gadget/configs/c.1/ncm.usb0"
ln -s /sys/kernel/config/usb_gadget/rog5-network-root/functions/acm.usb0 \
	"$gadget/configs/c.1/ncm.usb0"
expect_failure 'changed USB gadget configuration link'
rm "$gadget/configs/c.1/ncm.usb0"
ln -s /sys/kernel/config/usb_gadget/rog5-network-root/functions/ncm.usb0 \
	"$gadget/configs/c.1/ncm.usb0"

printf '%s\n' a800000.dwc3 >"$gadget/UDC"
expect_failure 'changed USB gadget controller'
printf '%s\n' a600000.usb >"$gadget/UDC"

printf '%s\n' a600000.dwc3 >"$gadget/UDC"
expect_failure 'downstream wrapper USB controller name'
printf '%s\n' a600000.usb >"$gadget/UDC"

printf '%s\n' full-speed \
	>"$root/sys/class/udc/a600000.usb/current_speed"
expect_failure 'changed USB gadget speed'
printf '%s\n' high-speed \
	>"$root/sys/class/udc/a600000.usb/current_speed"

printf '%s\n' down >"$root/sys/class/net/usb0/operstate"
expect_failure 'down USB network interface'
printf '%s\n' up >"$root/sys/class/net/usb0/operstate"

printf '%s\n' 9000 >"$root/sys/class/net/usb0/mtu"
expect_failure 'changed USB network MTU'
printf '%s\n' 1500 >"$root/sys/class/net/usb0/mtu"

printf '%s\n' \
	'default via 169.254.77.1 dev usb0' \
	>"$root/run/mock-ip-routes"
expect_failure 'changed USB connected route'
printf '%s\n' \
	'169.254.77.0/30 dev usb0 proto kernel scope link src 169.254.77.2' \
	>"$root/run/mock-ip-routes"

printf '%s\n' 'default via 169.254.77.1 dev usb0' \
	>"$root/run/mock-ip-default-routes"
expect_failure 'alternate-table IPv4 default route'
: >"$root/run/mock-ip-default-routes"

cat >>"$root/run/mock-ip-rules" <<'EOF'
100:	from all lookup 100
EOF
expect_failure 'additional IPv4 policy-routing rule'
sed -i '$d' "$root/run/mock-ip-rules"

printf '%s\n' \
	'0 0 169.254.77.2:22 169.254.77.3:49152' \
	>"$root/run/mock-ss-sessions"
expect_failure 'changed SSH session peer'
printf '%s\n' \
	'0 0 169.254.77.2:22 169.254.77.1:49152' \
	'0 0 169.254.77.2:22 169.254.77.1:49153' \
	>"$root/run/mock-ss-sessions"
expect_failure 'additional SSH server session'
printf '%s\n' \
	'0 0 169.254.77.2:22 169.254.77.1:49152' \
	>"$root/run/mock-ss-sessions"

sed -i 's/^ssh-ed25519 /ssh-rsa /' "$root/root/.ssh/authorized_keys"
expect_failure 'non-Ed25519 authorized key'
install -m 0600 "$repo/configs/ssh/rog5-headless-build-fixture.pub" \
	"$root/root/.ssh/authorized_keys"

cp "$root/etc/ssh/ssh_host_ed25519_key.pub" "$stage/host-key.pub"
ssh-keygen -q -t ed25519 -N '' -f "$stage/alternate-host-key"
cp "$stage/alternate-host-key.pub" \
	"$root/etc/ssh/ssh_host_ed25519_key.pub"
chmod 0644 "$root/etc/ssh/ssh_host_ed25519_key.pub"
expect_failure 'mismatched SSH host key pair'
cp "$stage/host-key.pub" "$root/etc/ssh/ssh_host_ed25519_key.pub"
chmod 0644 "$root/etc/ssh/ssh_host_ed25519_key.pub"

printf '%s\n' 2222 >"$root/run/mock-ssh-port"
expect_failure 'changed SSH port'
printf '%s\n' 22 >"$root/run/mock-ssh-port"

printf '%s\n' /etc/ssh/ssh_host_rsa_key \
	>"$root/run/mock-ssh-host-key"
expect_failure 'changed effective SSH host key'
printf '%s\n' /etc/ssh/ssh_host_ed25519_key \
	>"$root/run/mock-ssh-host-key"

printf '%s\n' 800.00 >"$root/proc/uptime"
expect_failure 'expired watchdog'
printf '%s\n' 200.50 >"$root/proc/uptime"

printf '%s\n' 0-6 >"$root/sys/devices/system/cpu/online"
expect_failure 'offline CPU'
printf '%s\n' 0-7 >"$root/sys/devices/system/cpu/online"

mkdir "$root/sys/devices/system/cpu/cpufreq/policy1"
expect_failure 'additional CPU frequency policy'
rmdir "$root/sys/devices/system/cpu/cpufreq/policy1"

printf '%s\n' '4 5 6 7' \
	>"$root/sys/devices/system/cpu/cpufreq/policy4/related_cpus"
expect_failure 'changed CPU frequency domain'
printf '%s\n' '4 5 6' \
	>"$root/sys/devices/system/cpu/cpufreq/policy4/related_cpus"

printf '%s\n' performance \
	>"$root/sys/devices/system/cpu/cpufreq/policy7/scaling_governor"
expect_failure 'changed CPU frequency governor'
printf '%s\n' schedutil \
	>"$root/sys/devices/system/cpu/cpufreq/policy7/scaling_governor"

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

deployment_record=$stage/deployment-runtime.record
run_probe headless-ssh-network-root-v3 >"$deployment_record"
grep -Fxq 'candidate=headless-ssh-network-root-v3' "$deployment_record"

set +e
run_probe unsupported-candidate >"$stage/unsupported-record" \
	2>"$stage/unsupported-error"
unsupported_candidate_status=$?
set -e
[ "$unsupported_candidate_status" -ne 0 ]
grep -Fxq 'FAIL runtime candidate identity is unsupported' \
	"$stage/unsupported-error"

echo 'PASS minimal-headless runtime probe emits one canonical read-only observation, selects only fixed candidate identities, and rejects fifty-two core mutations'
