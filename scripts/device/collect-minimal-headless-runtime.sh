#!/bin/sh
set -eu
LC_ALL=C
export LC_ALL

fail() {
	echo "FAIL $*" >&2
	exit 1
}

runtime_root=${ROG5_RUNTIME_ROOT:-}
test_mode=${ROG5_RUNTIME_TEST_MODE:-0}
runtime_candidate=${ROG5_RUNTIME_CANDIDATE:-headless-network-root-v1}
case $runtime_candidate in
	headless-network-root-v1|headless-ssh-network-root-v3|\
		headless-power-usb-observer-v1|headless-power-usb-observer-v2|\
		headless-power-usb-observer-v3)
		expected_usb_product='ROG5 network root'
		expected_usb_configuration='NFS root over NCM'
		expected_usb_function_count=1
		expected_usb_functions='ncm.usb0'
		;;
	headless-netroot-early-diag-v2)
		expected_usb_product='ROG5 diagnostic network root'
		expected_usb_configuration='Diagnostic NFS root over NCM and ACM'
		expected_usb_function_count=2
		expected_usb_functions='acm.usb0,ncm.usb0'
		;;
	*) fail 'runtime candidate identity is unsupported' ;;
esac
case $test_mode:$runtime_root in
	0:) execution_mode=live ;;
	1:/*)
	[ "$runtime_root" != / ] ||
			fail 'test runtime root must not be the host root'
		[ -d "$runtime_root" ] && [ ! -L "$runtime_root" ] ||
			fail 'test runtime root is unsafe'
		execution_mode='test'
		;;
	*) fail 'runtime fixture mode is invalid' ;;
esac

runtime_path() {
	printf '%s%s' "$runtime_root" "$1"
}

for command in awk cat dmesg find findmnt grep id ip nproc readlink sed sort \
	sha256sum ss ssh-keygen sshd stat systemctl tr uname wc; do
	command -v "$command" >/dev/null ||
		fail "missing runtime probe command: $command"
done

owner_uid=$(id -u)
owner_gid=$(id -g)
if [ "$execution_mode" = live ]; then
	[ "$owner_uid:$owner_gid" = 0:0 ] ||
		fail 'live runtime probe requires root'
fi

unsigned_integer() {
	case $1 in
		''|*[!0-9]*) return 1 ;;
	esac
	[ "$1" = 0 ] || [ "${1#0}" = "$1" ]
}

signed_integer() {
	value=$1
	case $value in
		-*) value=${value#-} ;;
	esac
	unsigned_integer "$value" || return 1
	[ "$1" != -0 ]
}

sha256_value() {
	case $1 in
		''|*[!0-9a-f]*) return 1 ;;
	esac
	[ "${#1}" -eq 64 ] &&
		[ "$1" != \
		0000000000000000000000000000000000000000000000000000000000000000 ]
}

record_value() {
	file=$1
	line_number=$2
	expected_key=$3
	awk -F= -v line_number="$line_number" -v expected_key="$expected_key" '
		NR == line_number {
			if (NF != 2 || $1 != expected_key || $2 == "")
				exit 1
			print $2
			found = 1
		}
		END {
			if (!found)
				exit 1
		}
	' "$file"
}

regular_metadata() {
	file=$1
	mode=$2
	label=$3
	[ -f "$file" ] && [ ! -L "$file" ] ||
		fail "$label is absent or linked"
	[ "$(stat -c '%u:%g:%a:%F' "$file")" = \
		"$owner_uid:$owner_gid:$mode:regular file" ] ||
		fail "$label metadata is unsafe"
}

optional_class_count() {
	class_root=$1
	[ ! -L "$class_root" ] || return 1
	if [ ! -e "$class_root" ]; then
		printf '0\n'
		return
	fi
	[ -d "$class_root" ] || return 1
	find "$class_root" -mindepth 1 -maxdepth 1 -print |
		awk 'NF { count++ } END { print count + 0 }'
}

ssh_ed25519_identity() {
	key_file=$1
	ssh-keygen -l -E sha256 -f "$key_file" 2>/dev/null |
		awk '
			{
				total++
				if ($1 == "256" &&
					index($2, "SHA256:") == 1 &&
					length($2) > 7 &&
					$NF == "(ED25519)") {
					valid++
					fingerprint=$2
				}
			}
			END {
				if (total != 1 || valid != 1)
					exit 1
				print "ssh-ed25519:256:" fingerprint
			}'
}

ssh_ed25519_public_material() {
	awk '
		NF {
			total++
			if (NF < 2 || $1 != "ssh-ed25519")
				invalid=1
			material=$1 " " $2
		}
		END {
			if (total != 1 || invalid)
				exit 1
			print material
		}'
}

mount_option_value() {
	options=$1
	expected_name=$2
	printf '%s\n' "$options" | tr ',' '\n' |
		awk -F= -v expected_name="$expected_name" '
			$1 == expected_name {
				count++
				if (NF != 2 || $2 == "")
					invalid = 1
				value=$2
			}
			END {
				if (count != 1 || invalid)
					exit 1
				print value
			}'
}

process_start_time_ticks() (
	process_pid=$1
	process_stat=$(cat "$(runtime_path "/proc/$process_pid/stat")" 2>/dev/null) ||
		exit 1
	process_fields=${process_stat#*) }
	[ "$process_fields" != "$process_stat" ] || exit 1
	set -f
	# The proc stat fields are intentionally split after globbing is disabled.
	# shellcheck disable=SC2086
	set -- $process_fields
	[ "$#" -ge 20 ] || exit 1
	shift 19
	unsigned_integer "$1" || exit 1
	printf '%s\n' "$1"
)

process_parent_pid() (
	process_pid=$1
	process_stat=$(cat "$(runtime_path "/proc/$process_pid/stat")" 2>/dev/null) ||
		exit 1
	process_fields=${process_stat#*) }
	[ "$process_fields" != "$process_stat" ] || exit 1
	set -f
	# The proc stat fields are intentionally split after globbing is disabled.
	# shellcheck disable=SC2086
	set -- $process_fields
	[ "$#" -ge 2 ] || exit 1
	unsigned_integer "$2" || exit 1
	printf '%s\n' "$2"
)

process_alive() {
	process_pid=$1
	[ -d "$(runtime_path "/proc/$process_pid")" ] || return 1
	if [ "$execution_mode" = live ]; then
		kill -0 "$process_pid" 2>/dev/null
	fi
}

probe_path=$0
[ -f "$probe_path" ] && [ ! -L "$probe_path" ] ||
	fail 'runtime probe source is absent or linked'
probe_sha256=$(sha256sum "$probe_path" | awk '{ print $1 }')
sha256_value "$probe_sha256" || fail 'runtime probe hash is invalid'

kernel_release=$(uname -r)
machine=$(uname -m)
[ "$kernel_release" = 7.1.4-g7a5cef0db479 ] ||
	fail 'unexpected target kernel'
[ "$machine" = aarch64 ] || fail 'target machine is not AArch64'

pid1=$(cat "$(runtime_path /proc/1/comm)")
[ "$pid1" = systemd ] || fail 'PID 1 is not systemd'
system_state=$(systemctl is-system-running 2>/dev/null || true)
[ "$system_state" = running ] || fail 'systemd is not running'
default_target=$(systemctl get-default 2>/dev/null || true)
[ "$default_target" = multi-user.target ] ||
	fail 'default target is not headless'
sshd_state=$(systemctl is-active sshd.service 2>/dev/null || true)
[ "$sshd_state" = active ] || fail 'SSH service is not active'
server_inhibitor_state=$(
	systemctl is-active rog5-server-inhibit.service 2>/dev/null || true
)
[ "$server_inhibitor_state" = active ] ||
	fail 'server sleep inhibitor is not active'
failed_units=$(
	systemctl --failed --no-legend --plain 2>/dev/null |
		awk 'NF { count++ } END { print count + 0 }'
)
[ "$failed_units" -eq 0 ] || fail 'systemd has failed units'

boot_id=$(cat "$(runtime_path /proc/sys/kernel/random/boot_id)")
printf '%s\n' "$boot_id" |
	grep -Eq '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' ||
	fail 'boot identity is invalid'

cpu_online_count=$(nproc)
unsigned_integer "$cpu_online_count" && [ "$cpu_online_count" -gt 0 ] ||
	fail 'online CPU count is invalid'
cpu_online_set=$(cat "$(runtime_path /sys/devices/system/cpu/online)")
cpu_present_set=$(cat "$(runtime_path /sys/devices/system/cpu/present)")
[ "$cpu_online_count" = 8 ] && [ "$cpu_online_set" = 0-7 ] ||
	fail 'online CPU topology is not exact'
[ "$cpu_present_set" = 0-7 ] ||
	fail 'present CPU topology is not exact'

cpufreq_root=$(runtime_path /sys/devices/system/cpu/cpufreq)
[ -d "$cpufreq_root" ] && [ ! -L "$cpufreq_root" ] ||
	fail 'CPU frequency policy root is absent or linked'
cpufreq_policy_count=$(
	find "$cpufreq_root" -mindepth 1 -maxdepth 1 -name 'policy*' -print |
		awk 'NF { count++ } END { print count + 0 }'
)
[ "$cpufreq_policy_count" = 3 ] ||
	fail 'CPU frequency policy count is not exact'
cpufreq_policy_names=
cpufreq_policy_cpu_sets=
cpufreq_policy_drivers=
cpufreq_policy_governors=
separator=
for policy_name in policy0 policy4 policy7; do
	policy_path=$cpufreq_root/$policy_name
	[ -d "$policy_path" ] && [ ! -L "$policy_path" ] ||
		fail "CPU frequency policy is absent or linked: $policy_name"
	case $policy_name in
		policy0) expected_related_cpus='0 1 2 3' ;;
		policy4) expected_related_cpus='4 5 6' ;;
		policy7) expected_related_cpus=7 ;;
	esac
	related_cpus=$(cat "$policy_path/related_cpus")
	scaling_driver=$(cat "$policy_path/scaling_driver")
	scaling_governor=$(cat "$policy_path/scaling_governor")
	[ "$related_cpus" = "$expected_related_cpus" ] ||
		fail "CPU frequency policy topology changed: $policy_name"
	[ "$scaling_driver" = qcom-cpufreq-hw ] ||
		fail "CPU frequency policy driver changed: $policy_name"
	[ "$scaling_governor" = schedutil ] ||
		fail "CPU frequency policy governor changed: $policy_name"
	cpufreq_policy_names=$cpufreq_policy_names$separator$policy_name
	cpufreq_policy_cpu_sets=$cpufreq_policy_cpu_sets$separator$related_cpus
	cpufreq_policy_drivers=$cpufreq_policy_drivers$separator$scaling_driver
	cpufreq_policy_governors=$cpufreq_policy_governors$separator$scaling_governor
	separator=';'
done
memory_total_kib=$(
	awk '$1 == "MemTotal:" { print $2; found=1; exit }
		END { if (!found) exit 1 }' "$(runtime_path /proc/meminfo)"
)
memory_available_kib=$(
	awk '$1 == "MemAvailable:" { print $2; found=1; exit }
		END { if (!found) exit 1 }' "$(runtime_path /proc/meminfo)"
)
unsigned_integer "$memory_total_kib" &&
	unsigned_integer "$memory_available_kib" &&
	[ "$memory_total_kib" -gt 0 ] &&
	[ "$memory_available_kib" -le "$memory_total_kib" ] ||
	fail 'runtime memory accounting is invalid'

overlay_mount_id=$(findmnt -n -o ID /)
overlay_lower_mount_id=$(findmnt -n -o ID /.rog5/root-ro)
state_mount_id=$(findmnt -n -o ID /.rog5/state)
for mount_id in \
	"$overlay_mount_id" "$overlay_lower_mount_id" "$state_mount_id"; do
	unsigned_integer "$mount_id" && [ "$mount_id" -gt 0 ] ||
		fail 'storage mount identity is invalid'
done
[ "$overlay_mount_id" != "$overlay_lower_mount_id" ] &&
	[ "$overlay_mount_id" != "$state_mount_id" ] &&
	[ "$overlay_lower_mount_id" != "$state_mount_id" ] ||
	fail 'storage mount identities are not distinct'

root_fstype=$(findmnt -n -o FSTYPE /)
[ "$root_fstype" = overlay ] || fail 'root is not OverlayFS'
root_options=$(findmnt -n -o OPTIONS /)
overlay_lowerdir=$(
	mount_option_value "$root_options" lowerdir
) || fail 'OverlayFS lower directory is absent or ambiguous'
[ "$overlay_lowerdir" = /mnt/root-ro ] ||
	fail 'OverlayFS lower directory is not exact'
overlay_upperdir=$(
	mount_option_value "$root_options" upperdir
) || fail 'OverlayFS upper directory is absent or ambiguous'
[ "$overlay_upperdir" = /mnt/state/upper ] ||
	fail 'OverlayFS upper directory is not exact'
overlay_workdir=$(
	mount_option_value "$root_options" workdir
) || fail 'OverlayFS work directory is absent or ambiguous'
[ "$overlay_workdir" = /mnt/state/work ] ||
	fail 'OverlayFS work directory is not exact'
lower_fstype=$(findmnt -n -o FSTYPE /.rog5/root-ro)
[ "$lower_fstype" = nfs4 ] || fail 'NFS lower filesystem type changed'
lower_source=$(findmnt -n -o SOURCE /.rog5/root-ro)
[ "$lower_source" = 169.254.77.1:/ ] ||
	fail 'NFS lower source is not exact'
lower_options=$(findmnt -n -o OPTIONS /.rog5/root-ro)
printf '%s\n' "$lower_options" | tr ',' '\n' | grep -qx ro ||
	fail 'NFS lower is not read-only'
lower_nfs_version=$(
	mount_option_value "$lower_options" vers
) || fail 'NFS lower version is absent or ambiguous'
[ "$lower_nfs_version" = 4.2 ] ||
	fail 'NFS lower is not version 4.2'
lower_transport=$(
	mount_option_value "$lower_options" proto
) || fail 'NFS lower transport is absent or ambiguous'
[ "$lower_transport" = tcp ] ||
	fail 'NFS lower transport is not TCP'
state_fstype=$(findmnt -n -o FSTYPE /.rog5/state)
[ "$state_fstype" = tmpfs ] || fail 'writable state is not tmpfs'
state_options=$(findmnt -n -o OPTIONS /.rog5/state)
printf '%s\n' "$state_options" | tr ',' '\n' | grep -qx nodev ||
	fail 'tmpfs state lacks nodev'
printf '%s\n' "$state_options" | tr ',' '\n' | grep -qx nosuid ||
	fail 'tmpfs state lacks nosuid'

block_class=$(runtime_path /sys/class/block)
[ -d "$block_class" ] && [ ! -L "$block_class" ] ||
	fail 'block device class is absent or linked'
block_device_names=$(
	find "$block_class" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort
) || fail 'block device inventory is unreadable'
expected_block_device_names='loop0
loop1
loop2
loop3
loop4
loop5
loop6
loop7
zram0'
[ "$block_device_names" = "$expected_block_device_names" ] ||
	fail 'virtual block device inventory is not exact'
block_device_count=9
loop_index=0
while [ "$loop_index" -lt 8 ]; do
	loop_path=$block_class/loop$loop_index
	[ -L "$loop_path" ] || fail 'inert loop device is not a class link'
	[ "$(readlink -f "$loop_path")" = \
		"$(runtime_path "/sys/devices/virtual/block/loop$loop_index")" ] ||
		fail 'inert loop device escaped the virtual block topology'
	[ ! -e "$loop_path/device" ] && [ ! -e "$loop_path/partition" ] &&
		[ ! -e "$loop_path/loop" ] ||
		fail 'loop device is active or physically backed'
	loop_index=$((loop_index + 1))
done
zram_path=$block_class/zram0
[ -L "$zram_path" ] || fail 'inert zram device is not a class link'
[ "$(readlink -f "$zram_path")" = \
	"$(runtime_path /sys/devices/virtual/block/zram0)" ] ||
	fail 'inert zram device escaped the virtual block topology'
[ ! -e "$zram_path/device" ] && [ ! -e "$zram_path/partition" ] ||
	fail 'zram device is physically backed'
[ "$(cat "$zram_path/disksize")" = 0 ] ||
	fail 'zram device is active'
block_listing=$(
	find "$block_class" -mindepth 1 -maxdepth 1 \
		-type l -exec test -e {}/device \; -print
) || fail 'physical block topology is unreadable'
physical_block_devices=$(
	printf '%s' "$block_listing" |
		awk 'NF { count++ } END { print count + 0 }'
)
[ "$physical_block_devices" -eq 0 ] ||
	fail 'physical block device is present'
scsi_host_count=$(
	optional_class_count "$(runtime_path /sys/class/scsi_host)"
) || fail 'SCSI host topology is unsafe'
[ "$scsi_host_count" -eq 0 ] || fail 'SCSI host is present'
rpmb_device_count=$(
	optional_class_count "$(runtime_path /sys/class/rpmb)"
) || fail 'RPMB topology is unsafe'
[ "$rpmb_device_count" -eq 0 ] || fail 'RPMB device is present'
platform_devices=$(runtime_path /sys/bus/platform/devices)
[ -d "$platform_devices" ] && [ ! -L "$platform_devices" ] ||
	fail 'platform device topology is absent or linked'
ufs_platform_device_count=$(
	find "$platform_devices" -mindepth 1 -maxdepth 1 \
		-name '1d84000.ufshc' -print |
		awk 'NF { count++ } END { print count + 0 }'
)
[ "$ufs_platform_device_count" -eq 0 ] ||
	fail 'UFS platform device is present'
block_backed_mounts=0
while read -r _ _ device _ _ _ rest; do
	[ -e "$(runtime_path "/sys/dev/block/$device")" ] || continue
	block_backed_mounts=$((block_backed_mounts + 1))
done <"$(runtime_path /proc/self/mountinfo)"
[ "$block_backed_mounts" -eq 0 ] ||
	fail 'block-backed mount is present'
[ "$(cat "$(runtime_path /run/rog5-physical-block-count)")" = 0 ] ||
	fail 'initramfs physical-block handoff changed'
[ "$(cat "$(runtime_path /run/rog5-network-root-source)")" = \
	169.254.77.1:/ ] ||
	fail 'initramfs network-root source changed'
[ -f "$(runtime_path /run/rog5-network-root-mounted)" ] ||
	fail 'network-root handoff marker is absent'

gadget_root=$(runtime_path /sys/kernel/config/usb_gadget)
[ -d "$gadget_root" ] && [ ! -L "$gadget_root" ] ||
	fail 'USB gadget inventory root is absent or linked'
usb_gadget_count=$(
	find "$gadget_root" -mindepth 1 -maxdepth 1 -type d -print |
		awk 'NF { count++ } END { print count + 0 }'
)
[ "$usb_gadget_count" -eq 1 ] ||
	fail 'USB gadget inventory is not exact'
gadget=$gadget_root/rog5-network-root
[ -d "$gadget" ] && [ ! -L "$gadget" ] ||
	fail 'USB gadget root is absent or linked'
for attribute in idVendor idProduct bDeviceClass bDeviceSubClass \
	bDeviceProtocol UDC; do
	[ -r "$gadget/$attribute" ] && [ ! -L "$gadget/$attribute" ] ||
		fail "USB gadget attribute is absent or linked: $attribute"
done
[ "$(cat "$gadget/idVendor")" = 0x1d6b ] &&
	[ "$(cat "$gadget/idProduct")" = 0x0104 ] &&
	[ "$(cat "$gadget/bDeviceClass")" = 0xef ] &&
	[ "$(cat "$gadget/bDeviceSubClass")" = 0x02 ] &&
	[ "$(cat "$gadget/bDeviceProtocol")" = 0x01 ] ||
	fail 'USB gadget descriptor identity changed'
usb_strings=$gadget/strings/0x409
usb_config=$gadget/configs/c.1
[ -d "$usb_strings" ] && [ ! -L "$usb_strings" ] &&
	[ -d "$usb_config" ] && [ ! -L "$usb_config" ] ||
	fail 'USB gadget strings or configuration are absent or linked'
usb_string_language_count=$(
	find "$gadget/strings" -mindepth 1 -maxdepth 1 -type d -print |
		awk 'NF { count++ } END { print count + 0 }'
)
usb_config_count=$(
	find "$gadget/configs" -mindepth 1 -maxdepth 1 -type d -print |
		awk 'NF { count++ } END { print count + 0 }'
)
usb_config_string_language_count=$(
	find "$usb_config/strings" -mindepth 1 -maxdepth 1 -type d -print |
		awk 'NF { count++ } END { print count + 0 }'
)
[ "$usb_string_language_count" -eq 1 ] &&
	[ "$usb_config_count" -eq 1 ] &&
	[ "$usb_config_string_language_count" -eq 1 ] ||
	fail 'USB gadget configuration or language inventory is not exact'
[ "$(cat "$usb_strings/manufacturer")" = Linux ] &&
	[ "$(cat "$usb_strings/product")" = "$expected_usb_product" ] &&
	[ "$(cat "$usb_config/strings/0x409/configuration")" = \
	"$expected_usb_configuration" ] ||
	fail 'USB gadget string identity changed'
usb_function_count=$(
	find "$gadget/functions" -mindepth 1 -maxdepth 1 -type d -print |
		awk 'NF { count++ } END { print count + 0 }'
)
[ "$usb_function_count" -eq "$expected_usb_function_count" ] &&
	[ -d "$gadget/functions/ncm.usb0" ] &&
	[ ! -L "$gadget/functions/ncm.usb0" ] ||
	fail 'USB gadget function inventory is not exact'
if [ "$runtime_candidate" = headless-netroot-early-diag-v2 ]; then
	[ -d "$gadget/functions/acm.usb0" ] &&
		[ ! -L "$gadget/functions/acm.usb0" ] ||
		fail 'USB gadget function inventory is not exact'
fi
usb_config_link_count=$(
	find "$usb_config" -mindepth 1 -maxdepth 1 -type l -print |
		awk 'NF { count++ } END { print count + 0 }'
)
[ "$usb_config_link_count" -eq "$expected_usb_function_count" ] &&
	[ "$(readlink "$usb_config/ncm.usb0")" = \
	../../../../usb_gadget/rog5-network-root/functions/ncm.usb0 ] ||
	fail 'USB gadget NCM configuration link is not exact'
if [ "$runtime_candidate" = headless-netroot-early-diag-v2 ]; then
	[ "$(readlink "$usb_config/acm.usb0")" = \
	../../../../usb_gadget/rog5-network-root/functions/acm.usb0 ] ||
		fail 'USB gadget ACM configuration link is not exact'
fi
usb_udc=$(cat "$gadget/UDC")
case $usb_udc in
	''|*[!A-Za-z0-9._:-]*) fail 'USB UDC name is noncanonical' ;;
	a600000.usb) ;;
	*) fail 'USB gadget is not bound to the primary controller' ;;
esac
usb_current_speed=$(
	cat "$(runtime_path "/sys/class/udc/$usb_udc/current_speed")"
) || fail 'USB current speed is unreadable'
[ "$usb_current_speed" = high-speed ] ||
	fail 'USB gadget current speed is not high-speed'

usb_carrier=$(cat "$(runtime_path /sys/class/net/usb0/carrier)")
[ "$usb_carrier" = 1 ] || fail 'USB network carrier is down'
usb_operstate=$(cat "$(runtime_path /sys/class/net/usb0/operstate)")
[ "$usb_operstate" = up ] || fail 'USB network interface is not operational'
usb_mtu=$(cat "$(runtime_path /sys/class/net/usb0/mtu)")
[ "$usb_mtu" = 1500 ] || fail 'USB network MTU changed'
usb_ipv4_counts=$(
	ip -4 -o address show dev usb0 |
		awk '{ total++ }
			$4 == "169.254.77.2/30" { exact++ }
			END { print total + 0, exact + 0 }'
)
[ "$usb_ipv4_counts" = '1 1' ] ||
	fail 'USB network address is not exact'
usb_ipv4_routes=$(ip -4 -o route show table main)
usb_ipv4_route_count=$(
	printf '%s\n' "$usb_ipv4_routes" |
		awk 'NF { count++ } END { print count + 0 }'
)
[ "$usb_ipv4_route_count" -eq 1 ] ||
	fail 'USB network route count is not exact'
printf '%s\n' "$usb_ipv4_routes" |
	awk 'NF == 9 &&
		$1 == "169.254.77.0/30" &&
		$2 == "dev" && $3 == "usb0" &&
		$4 == "proto" && $5 == "kernel" &&
		$6 == "scope" && $7 == "link" &&
		$8 == "src" && $9 == "169.254.77.2" { exact++ }
		END { exit exact != 1 }' ||
	fail 'USB network route is not exact'
usb_default_route_count=$(
	ip -4 -o route show table all default |
		awk 'NF { count++ } END { print count + 0 }'
)
[ "$usb_default_route_count" -eq 0 ] ||
	fail 'an IPv4 default route is present'
usb_ipv4_rules=$(ip -4 -o rule show)
[ "$usb_ipv4_rules" = '0:	from all lookup local
32766:	from all lookup main
32767:	from all lookup default' ] ||
	fail 'IPv4 policy-routing rules are not the kernel defaults'

ssh_session_counts=$(
	ss -H -n -t state established |
		awk '
			$3 ~ /:22$/ {
				total++
				if ($3 == "169.254.77.2:22" &&
					$4 ~ /^169[.]254[.]77[.]1:[1-9][0-9]*$/)
					exact++
			}
			END { print total + 0, exact + 0 }'
)
[ "$ssh_session_counts" = '1 1' ] ||
	fail 'SSH observation is not on one exact USB peer session'

authorized_keys=$(runtime_path /root/.ssh/authorized_keys)
regular_metadata "$authorized_keys" 600 'authorized keys'
[ "$(awk 'NF { count++ } END { print count + 0 }' "$authorized_keys")" -eq 1 ] ||
	fail 'authorized-key count changed'
[ "$(awk 'NF { print $1 }' "$authorized_keys")" = ssh-ed25519 ] ||
	fail 'authorized key is not Ed25519'
ssh_ed25519_identity "$authorized_keys" >/dev/null ||
	fail 'authorized Ed25519 key identity is invalid'
shadow=$(runtime_path /etc/shadow)
awk -F: '$1 == "root" { found=1; exit substr($2, 1, 1) != "!" }
	END { if (!found) exit 1 }' "$shadow" ||
	fail 'root password is not locked'
host_key=$(runtime_path /etc/ssh/ssh_host_ed25519_key)
regular_metadata "$host_key" 600 'SSH host key'
regular_metadata "$host_key.pub" 644 'SSH public host key'
ssh_ed25519_identity "$host_key.pub" >/dev/null ||
	fail 'SSH public host-key identity is invalid'
host_private_public=$(
	ssh-keygen -y -f "$host_key" 2>/dev/null |
		ssh_ed25519_public_material
) || fail 'SSH private host-key public material is invalid'
host_public_material=$(
	ssh_ed25519_public_material <"$host_key.pub"
) || fail 'SSH public host-key material is noncanonical'
[ "$host_private_public" = "$host_public_material" ] ||
	fail 'SSH host private and public keys do not match'
[ "$(awk 'NF { print $1; exit }' "$host_key.pub")" = ssh-ed25519 ] ||
	fail 'SSH public host key is not Ed25519'
effective_sshd=$(
	sshd -T -C \
		user=root,host=169.254.77.1,addr=169.254.77.1,laddr=169.254.77.2,lport=22
)
printf '%s\n' "$effective_sshd" |
	grep -Fixq 'passwordauthentication no' ||
	fail 'SSH password authentication is enabled'
printf '%s\n' "$effective_sshd" |
	grep -Fixq 'kbdinteractiveauthentication no' ||
	fail 'SSH keyboard-interactive authentication is enabled'
printf '%s\n' "$effective_sshd" |
	grep -Fixq 'pubkeyauthentication yes' ||
	fail 'SSH public-key authentication is disabled'
printf '%s\n' "$effective_sshd" |
	grep -Eiq '^permitrootlogin (without-password|prohibit-password)$' ||
	fail 'SSH root login policy is not key-only'
printf '%s\n' "$effective_sshd" |
	grep -Fixq 'port 22' ||
	fail 'SSH port changed'
printf '%s\n' "$effective_sshd" |
	grep -Fixq 'hostkey /etc/ssh/ssh_host_ed25519_key' ||
	fail 'SSH effective host-key path changed'

identity=$(runtime_path /run/rog5-network-root-identity)
regular_metadata "$identity" 400 'network-root identity'
[ "$(wc -l <"$identity")" -eq 11 ] ||
	fail 'network-root identity field count changed'
network_root_identity_format=$(record_value "$identity" 1 format)
[ "$network_root_identity_format" = rog5-network-root-identity-v1 ] ||
	fail 'network-root identity format changed'
identity_overlay_mount_id=$(record_value "$identity" 2 overlay_mount_id)
identity_overlay_lower_mount_id=$(
	record_value "$identity" 3 overlay_lower_mount_id
)
identity_state_mount_id=$(record_value "$identity" 4 state_mount_id)
[ "$identity_overlay_mount_id" = "$overlay_mount_id" ] &&
	[ "$identity_overlay_lower_mount_id" = "$overlay_lower_mount_id" ] &&
	[ "$identity_state_mount_id" = "$state_mount_id" ] ||
	fail 'network-root mount identity does not match runtime'
[ "$(record_value "$identity" 5 overlay_lower_path)" = /mnt/root-ro ] ||
	fail 'network-root lower identity changed'
command_manifest_sha256=$(
	record_value "$identity" 6 command_manifest_sha256
)
root_generation=$(record_value "$identity" 7 root_generation)
root_tree_sha256=$(record_value "$identity" 8 root_tree_sha256)
root_seal_sha256=$(record_value "$identity" 9 root_seal_sha256)
root_tree_entries=$(record_value "$identity" 10 root_tree_entries)
root_subtree=$(record_value "$identity" 11 root_subtree)
if ! sha256_value "$command_manifest_sha256" ||
	! sha256_value "$root_tree_sha256" ||
	! sha256_value "$root_seal_sha256"; then
	fail 'network-root identity hash is invalid'
fi
unsigned_integer "$root_tree_entries" && [ "$root_tree_entries" -gt 0 ] ||
	fail 'network-root tree entry count is invalid'

root_seal=$(runtime_path /.rog5/root-ro/.rog5-persistent-seal)
[ -f "$root_seal" ] && [ ! -L "$root_seal" ] ||
	fail 'network-root seal is absent or linked'
root_seal_file_sha256=$(sha256sum "$root_seal" | awk '{ print $1 }')
[ "$root_seal_file_sha256" = "$root_seal_sha256" ] ||
	fail 'network-root seal hash changed after handoff'
command_manifest=$(
	runtime_path /.rog5/root-ro/etc/rog5/a660-command-manifest
)
[ -f "$command_manifest" ] && [ ! -L "$command_manifest" ] ||
	fail 'headless command manifest is absent or linked'
[ "$(sha256sum "$command_manifest" | awk '{ print $1 }')" = \
	"$command_manifest_sha256" ] ||
	fail 'headless command manifest hash changed after handoff'
[ "$(wc -l <"$command_manifest")" -eq 2 ] &&
	[ "$(record_value "$command_manifest" 1 format)" = \
	rog5-headless-command-manifest-v1 ] &&
	[ "$(record_value "$command_manifest" 2 workload)" = none ] ||
	fail 'headless command manifest changed'

thermal_zone_count=0
thermal_min_millidegree_c=
thermal_max_millidegree_c=
for thermal_path in "$(runtime_path /sys/class/thermal)"/thermal_zone*/temp; do
	[ -r "$thermal_path" ] || continue
	thermal_value=$(cat "$thermal_path")
	signed_integer "$thermal_value" ||
		fail 'thermal zone returned a noncanonical value'
	[ "$thermal_value" -ge -40000 ] && [ "$thermal_value" -le 150000 ] ||
		fail 'thermal zone returned an implausible value'
	thermal_zone_count=$((thermal_zone_count + 1))
	if [ -z "$thermal_min_millidegree_c" ] ||
		[ "$thermal_value" -lt "$thermal_min_millidegree_c" ]; then
		thermal_min_millidegree_c=$thermal_value
	fi
	if [ -z "$thermal_max_millidegree_c" ] ||
		[ "$thermal_value" -gt "$thermal_max_millidegree_c" ]; then
		thermal_max_millidegree_c=$thermal_value
	fi
done
[ "$thermal_zone_count" -gt 0 ] ||
	fail 'no readable thermal zones are present'

fatal_pattern='(^|[^[:alnum:]_])(Kernel panic|Oops:|BUG:|watchdog[[:space:]_-]+bite|Kernel fault|Unable to handle kernel|Synchronous External Abort)([^[:alnum:]_]|$)'
fatal_kernel_signatures=$(
	dmesg | grep -Eic "$fatal_pattern" || true
)
[ "$fatal_kernel_signatures" -eq 0 ] ||
	fail 'fatal kernel signature is present'

watchdog_pid_file=$(runtime_path /run/rog5-network-root-watchdog.pid)
watchdog_lease=$(runtime_path /run/rog5-network-root-watchdog.lease)
watchdog_marker=$(runtime_path /run/rog5-network-root-watchdog.disarmed.pid)
regular_metadata "$watchdog_pid_file" 400 'watchdog PID file'
regular_metadata "$watchdog_lease" 400 'watchdog lease'
[ ! -e "$watchdog_marker" ] || fail 'rollback watchdog is disarmed'
[ "$(wc -l <"$watchdog_lease")" -eq 8 ] ||
	fail 'watchdog lease field count changed'
[ "$(record_value "$watchdog_lease" 1 format)" = \
	rog5-network-root-watchdog-v1 ] ||
	fail 'watchdog lease format changed'
watchdog_pid=$(record_value "$watchdog_lease" 2 pid)
watchdog_start=$(record_value "$watchdog_lease" 3 start_time_ticks)
timer_pid=$(record_value "$watchdog_lease" 4 timer_pid)
timer_start=$(record_value "$watchdog_lease" 5 timer_start_time_ticks)
armed_boottime=$(record_value "$watchdog_lease" 6 armed_boottime_seconds)
deadline_boottime=$(record_value "$watchdog_lease" 7 deadline_boottime_seconds)
watchdog_timeout_seconds=$(record_value "$watchdog_lease" 8 timeout_seconds)
for value in "$watchdog_pid" "$watchdog_start" "$timer_pid" "$timer_start" \
	"$armed_boottime" "$deadline_boottime" "$watchdog_timeout_seconds"; do
	unsigned_integer "$value" || fail 'watchdog lease integer is invalid'
done
[ "$(cat "$watchdog_pid_file")" = "$watchdog_pid" ] ||
	fail 'watchdog PID and lease disagree'
[ "$watchdog_pid" -ne 1 ] && [ "$timer_pid" -ne 1 ] &&
	[ "$watchdog_pid" -ne "$timer_pid" ] ||
	fail 'watchdog process identity is invalid'
if ! process_alive "$watchdog_pid" || ! process_alive "$timer_pid"; then
	fail 'watchdog process is absent'
fi
[ "$(cat "$(runtime_path "/proc/$watchdog_pid/comm")")" = init ] &&
	[ "$(cat "$(runtime_path "/proc/$timer_pid/comm")")" = sleep ] ||
	fail 'watchdog process name changed'
[ "$(process_parent_pid "$watchdog_pid")" = 1 ] &&
	[ "$(process_parent_pid "$timer_pid")" = "$watchdog_pid" ] ||
	fail 'watchdog process ancestry changed'
[ "$(process_start_time_ticks "$watchdog_pid")" = "$watchdog_start" ] &&
	[ "$(process_start_time_ticks "$timer_pid")" = "$timer_start" ] ||
	fail 'watchdog process start identity changed'
[ "$(readlink "$(runtime_path "/proc/$watchdog_pid/fd/8")")" = \
	/dev/kmsg ] &&
	[ "$(readlink "$(runtime_path "/proc/$watchdog_pid/fd/9")")" = \
	/proc/sysrq-trigger ] ||
	fail 'watchdog emergency descriptors changed'
[ "$deadline_boottime" -eq \
	"$((armed_boottime + watchdog_timeout_seconds))" ] ||
	fail 'watchdog lease deadline is inconsistent'
current_boottime=$(
	awk 'NR == 1 { split($1, fields, "."); print fields[1] }' \
		"$(runtime_path /proc/uptime)"
)
unsigned_integer "$current_boottime" ||
	fail 'current boot time is invalid'
watchdog_remaining_seconds=$((deadline_boottime - current_boottime))
[ "$watchdog_remaining_seconds" -gt 0 ] ||
	fail 'rollback watchdog deadline has expired'

printf 'format=rog5-minimal-headless-runtime-v1\n'
printf 'profile=minimal-headless-v1\n'
printf 'execution_mode=%s\n' "$execution_mode"
printf 'probe_sha256=%s\n' "$probe_sha256"
printf 'active_capabilities=cpu-ram,init-key-only-ssh,read-only-network-root,thermal-readonly,usb-ncm-network,watchdog-rollback-reboot\n'
printf 'candidate=%s\n' "$runtime_candidate"
printf 'boot_id=%s\n' "$boot_id"
printf 'kernel_release=%s\n' "$kernel_release"
printf 'machine=%s\n' "$machine"
printf 'pid1=%s\n' "$pid1"
printf 'system_state=%s\n' "$system_state"
printf 'default_target=%s\n' "$default_target"
printf 'cpu_online_count=%s\n' "$cpu_online_count"
printf 'cpu_online_set=%s\n' "$cpu_online_set"
printf 'cpu_present_set=%s\n' "$cpu_present_set"
printf 'cpufreq_policy_count=%s\n' "$cpufreq_policy_count"
printf 'cpufreq_policy_names=%s\n' "$cpufreq_policy_names"
printf 'cpufreq_policy_cpu_sets=%s\n' "$cpufreq_policy_cpu_sets"
printf 'cpufreq_policy_drivers=%s\n' "$cpufreq_policy_drivers"
printf 'cpufreq_policy_governors=%s\n' "$cpufreq_policy_governors"
printf 'memory_total_kib=%s\n' "$memory_total_kib"
printf 'memory_available_kib=%s\n' "$memory_available_kib"
printf 'overlay_mount_id=%s\n' "$overlay_mount_id"
printf 'overlay_lower_mount_id=%s\n' "$overlay_lower_mount_id"
printf 'state_mount_id=%s\n' "$state_mount_id"
printf 'overlay_lowerdir=%s\n' "$overlay_lowerdir"
printf 'overlay_upperdir=%s\n' "$overlay_upperdir"
printf 'overlay_workdir=%s\n' "$overlay_workdir"
printf 'root_fstype=%s\n' "$root_fstype"
printf 'lower_fstype=%s\n' "$lower_fstype"
printf 'lower_source=%s\n' "$lower_source"
printf 'lower_nfs_version=%s\n' "$lower_nfs_version"
printf 'lower_transport=%s\n' "$lower_transport"
printf 'lower_read_only=1\n'
printf 'state_fstype=%s\n' "$state_fstype"
printf 'state_nodev=1\n'
printf 'state_nosuid=1\n'
printf 'block_device_count=%s\n' "$block_device_count"
printf 'physical_block_devices=%s\n' "$physical_block_devices"
printf 'scsi_host_count=%s\n' "$scsi_host_count"
printf 'rpmb_device_count=%s\n' "$rpmb_device_count"
printf 'ufs_platform_device_count=%s\n' "$ufs_platform_device_count"
printf 'block_backed_mounts=%s\n' "$block_backed_mounts"
printf 'usb_gadget=rog5-network-root\n'
printf 'usb_vid_pid=1d6b:0104\n'
printf 'usb_product=%s\n' "$expected_usb_product"
printf 'usb_configuration=%s\n' "$expected_usb_configuration"
printf 'usb_function=%s\n' "$expected_usb_functions"
printf 'usb_udc_controller=a600000\n'
printf 'usb_current_speed=%s\n' "$usb_current_speed"
printf 'usb_interface=usb0\n'
printf 'usb_carrier=%s\n' "$usb_carrier"
printf 'usb_operstate=%s\n' "$usb_operstate"
printf 'usb_mtu=%s\n' "$usb_mtu"
printf 'usb_ipv4_cidr=169.254.77.2/30\n'
printf 'usb_route_cidr=169.254.77.0/30\n'
printf 'usb_default_route_count=%s\n' "$usb_default_route_count"
printf 'sshd_state=%s\n' "$sshd_state"
printf 'ssh_port=22\n'
printf 'ssh_session_count=1\n'
printf 'ssh_session_local=169.254.77.2:22\n'
printf 'ssh_session_peer=169.254.77.1\n'
printf 'ssh_authorized_key_type=ssh-ed25519\n'
printf 'ssh_authorized_key_bits=256\n'
printf 'ssh_host_key_type=ssh-ed25519\n'
printf 'ssh_host_key_bits=256\n'
printf 'ssh_host_key_pair_match=1\n'
printf 'ssh_auth=key-only\n'
printf 'server_inhibitor_state=%s\n' "$server_inhibitor_state"
printf 'failed_units=%s\n' "$failed_units"
printf 'fatal_kernel_signatures=%s\n' "$fatal_kernel_signatures"
printf 'thermal_zone_count=%s\n' "$thermal_zone_count"
printf 'thermal_min_millidegree_c=%s\n' "$thermal_min_millidegree_c"
printf 'thermal_max_millidegree_c=%s\n' "$thermal_max_millidegree_c"
printf 'watchdog_state=armed\n'
printf 'watchdog_timeout_seconds=%s\n' "$watchdog_timeout_seconds"
printf 'watchdog_remaining_seconds=%s\n' "$watchdog_remaining_seconds"
printf 'network_root_identity_format=%s\n' \
	"$network_root_identity_format"
printf 'root_generation=%s\n' "$root_generation"
printf 'root_tree_sha256=%s\n' "$root_tree_sha256"
printf 'root_seal_sha256=%s\n' "$root_seal_sha256"
printf 'root_seal_file_sha256=%s\n' "$root_seal_file_sha256"
printf 'root_tree_entries=%s\n' "$root_tree_entries"
printf 'root_subtree=%s\n' "$root_subtree"
printf 'command_manifest_sha256=%s\n' "$command_manifest_sha256"
printf 'command_manifest_format=rog5-headless-command-manifest-v1\n'
printf 'workload=none\n'
printf 'result=PASS\n'
