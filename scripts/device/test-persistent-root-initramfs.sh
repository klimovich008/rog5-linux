#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/persistent-root-init
attest=$repo/initramfs/persistent-root-attest
shutdown=$repo/initramfs/persistent-root-shutdown
builder=$repo/scripts/device/build-persistent-root-initramfs.sh
power_loader=$repo/scripts/device/load-persistent-root-power-usb.sh
reboot_source=$repo/tools/reboot_bootloader/rog5-reboot-bootloader.c
base=${1:-$repo/artifacts/ufs-discovery-v2/rog5-ufs-discovery-initramfs.cpio.gz}
verifier=${2:-$repo/artifacts/persistent-root-verifier-build-a/persistent-root-verify}
config=${3:-$repo/artifacts/persistent-root-p2/config-7.1.4-persistent-root}
ufs_modules=${4:-}
storage_mode=${UFS_STORAGE_MODE:-read-only}
writer_boot_id=7c3afb64-8e84-4f4b-87f4-88d19c2646de
case $storage_mode in
	read-only) sealed_probe_boot_id=${EXPECTED_PROBE_BOOT_ID:-$writer_boot_id} ;;
	local-write) sealed_probe_boot_id=current ;;
	*) sealed_probe_boot_id=$writer_boot_id ;;
esac

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in cpio gzip grep mktemp sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing P2 initramfs test command: $command"
done
for path in "$init" "$attest" "$shutdown" "$builder" "$power_loader"; do
	[ -x "$path" ] || fail "missing executable P2 source: $path"
done
[ -f "$reboot_source" ] && [ ! -L "$reboot_source" ] ||
	fail 'missing persistent-root restart2 helper source'
for reboot_contract in \
	'LINUX_REBOOT_CMD_RESTART2' \
	'static const char command[] = "bootloader"' \
	'NR_REBOOT 142UL' \
	'Success never returns'; do
	grep -Fq "$reboot_contract" "$reboot_source" ||
		fail 'persistent-root restart2 helper contract changed'
done
binary_integration=0
if [ -s "$base" ] && [ -x "$verifier" ] && [ -s "$config" ]; then
	binary_integration=1
	config_sha256=$(sha256sum "$config" | cut -d ' ' -f 1)
	if [ -n "${PERSISTENT_ROOT_POWER_MODULES_ROOT:-}" ]; then
		expected_config_sha256=15e1ea493ac1e654ef9f162ec9134207522ead67660dc16ab62771d9a9e638d6
	elif [ -n "$ufs_modules" ]; then
		case $storage_mode in
			read-only)
				expected_config_sha256=b959774825e2bca7c634e55cd00e838121fde8d95fd214ffeead732ce92e35e6
				;;
			local-write)
				expected_config_sha256=bfa2588e8994b4ce24f79975d9e85ee6102268e089e143e0bc316b193a8b50c7
				;;
			*) fail 'invalid UFS storage mode for config verification' ;;
		esac
		[ "$config_sha256" = "$expected_config_sha256" ]
	else
		[ "$config_sha256" = \
			8a7fabffa076a65d09529ef1004c315e1296e547a02d08c362031d0363ba63c3 ]
	fi || fail 'P2 input does not match the pinned target config'
else
	echo 'SKIP retained persistent-root binary integration; source contract remains active' >&2
fi

for script in "$init" "$attest" "$shutdown" "$builder"; do
	sh -n "$script"
done

grep -Fq 'rog5.persistent_ro=1' "$init"
grep -Fq 'expected_kernel_release=@EXPECTED_KERNEL_RELEASE@' \
	"$init"
grep -Fq 'release_file=/proc/sys/kernel/osrelease' "$init"
release_read='IFS= read -r running_kernel_release <"$release_file"'
grep -Fq "$release_read" "$init"
release_check='if [ "$running_kernel_release" != "$expected_kernel_release" ]; then'
grep -Fqx "$release_check" "$init"
! grep -Fq 'uname -r' "$init" ||
	fail 'P2 target must read the kernel release directly from procfs'
! grep -Fq '/proc/config.gz' "$init" ||
	fail 'P2 target must not depend on procfs IKCONFIG during live boot'
grep -Fqx 'expected_ufs_storage_mode=@EXPECTED_UFS_STORAGE_MODE@' "$init" ||
	fail 'P2 target lacks the sealed UFS storage-mode placeholder'
grep -Fqx 'expected_probe_boot_id=@EXPECTED_PROBE_BOOT_ID@' "$init" ||
	fail 'P2 target lacks the sealed write-probe producer placeholder'
grep -Fqx 'expected_ufs_storage_mode=@EXPECTED_UFS_STORAGE_MODE@' "$attest" ||
	fail 'P2 attestation lacks the sealed UFS storage-mode placeholder'
grep -Fqx 'expected_probe_boot_id=@EXPECTED_PROBE_BOOT_ID@' "$attest" ||
	fail 'P2 attestation lacks the sealed write-probe producer placeholder'
grep -Fq '[ "$expected_ufs_storage_mode" = local-write ]' "$init" ||
	fail 'P2 target lacks the local-write UFS policy branch'
grep -Fq "'ROG5 UFS discovery: forced read-only before registration'" "$init" ||
	fail 'local-write policy does not reject the discovery-only disk guard'
grep -Fq 'UFS_STORAGE_MODE must be read-only or local-write' "$builder" ||
	fail 'P2 builder does not fail closed on the storage mode'
grep -Fq 'EXPECTED_PROBE_BOOT_ID must be current for local-write' "$builder" ||
	fail 'P2 builder does not preserve current-boot write semantics'
grep -Fq 'EXPECTED_PROBE_BOOT_ID must pin a writer UUID for read-only' \
	"$builder" || fail 'P2 builder does not pin read-only marker lineage'
grep -Fq '[ "$probe_boot_id" = any-prior ]' "$builder" ||
	fail 'P2 builder lacks the sealed prior-writer discovery policy'
grep -Fq '[ "$expected_probe_boot_id" = any-prior ]' "$init" "$attest" ||
	fail 'P2 runtime lacks exact prior-writer discovery policy'
grep -Fq 'read-only:any-prior) ;;' "$init" ||
	fail 'P2 early boot policy rejects the sealed prior-writer mode'
grep -Fq 'read-only:staged-seal) ;;' "$init" ||
	fail 'P2 early boot policy rejects a host-sealed staged image'
grep -Fq '[ "$expected_probe_boot_id" = staged-seal ]' \
	"$builder" "$init" "$attest" ||
	fail 'P2 staged-image policy is incomplete'
grep -Fqx 'reboot_helper=/usr/libexec/rog5-reboot-bootloader' \
	"$init" "$shutdown" || fail 'P2 rollback lacks the fixed restart2 helper path'
grep -Fq '"$reboot_helper" || true' "$init" "$shutdown" ||
	fail 'P2 rollback does not request restart2'
grep -Fq 'bootloader restart returned; forcing emergency reset' "$init" ||
	fail 'P2 target does not retain a last-resort reset after restart2'
grep -Fq 'bootloader restart returned; triggering emergency reset' "$shutdown" ||
	fail 'P2 shutdown does not retain a last-resort reset after restart2'
for reboot_mode_contract in \
	'reboot_mode_driver=/sys/bus/platform/drivers/nvmem-reboot-mode' \
	'[ -L "$reboot_mode_driver/reboot-mode" ]' \
	'/sys/devices/platform/reboot-mode/of_node/compatible' \
	'nvmem-reboot-mode' \
	"fail_stage 'Qualcomm reboot-mode path is unavailable' reboot-mode 15"; do
	grep -Fq "$reboot_mode_contract" "$init" ||
		fail 'P2 target does not prove early Qualcomm reboot-mode readiness'
done
python3 - "$init" "$shutdown" <<'PY'
from pathlib import Path
import sys

for name in sys.argv[1:]:
    source = Path(name).read_text(encoding="ascii")
    helper = source.index('"$reboot_helper" || true')
    reset = source.index('printf b >/proc/sysrq-trigger')
    assert helper < reset, f"{name}: emergency reset precedes restart2"
PY
grep -Fq 'expected_ufs_storage_mode=$storage_mode' "$builder" ||
	fail 'P2 builder does not seal the selected storage mode'
grep -Fq 'expected_physical_count=116' "$init"
grep -Fq "'format=rog5-persistent-root-stage-v2'" "$init" ||
	fail 'P2 target lacks bounded stage-detail framing'
grep -Fq 'stage_detail=${3:-none}' "$init" ||
	fail 'P2 target lacks a default fail-closed stage detail'
grep -Fq '"detail=$stage_detail"' "$init" ||
	fail 'P2 target does not publish the bounded stage detail'
grep -Fq 'publish_stage ufs-ready FAIL "$ufs_discovery_detail"' "$init" ||
	fail 'P2 target does not retain the UFS discovery discriminator'
grep -Fq 'ufs-discovery-p${count}-a${auto_count}-h${host_count}-w${wlun_count}-e${error_count}' \
	"$init" || fail 'P2 UFS discriminator lacks exact counters'
grep -Fq 'expected_seal_sha256=02231e86746fbc656090f52c96d7e0c968c7ca86ba7449c306f611ea20c6a876' \
	"$init"
grep -Fq 'expected_tree_sha256=4701c23b93624bf894bb76331c165b650c9a2aecb99273a4e6d37c20ac3ef167' \
	"$init"
grep -Fq 'expected_image_bytes=17179869184' "$init" "$attest"
grep -Fq 'expected_image_uuid=598a876b-a8db-4859-a01a-1b864b0a87f4' \
	"$init" "$attest"
grep -Fq 'mount -t ext4 -o ro,noload "$userdata" /mnt/userdata' "$init"
grep -Fq '1 32 1086 8224 8225 9278 14680096 14688288 14688289' "$init" ||
	fail 'P2 sparse diagnostic does not cover source, alias, and high metadata blocks'
grep -Fq 'dd if="$userdata" bs=4096 skip="$probe_block" count=1' "$init" ||
	fail 'P2 sparse diagnostic does not read one exact block'
grep -Fq '"raw-b${probe_block}-${probe_hash}"' "$init" ||
	fail 'P2 sparse diagnostic does not publish bounded block hashes'
grep -Fq '[ "$mount_persistent_root_failure" = rog5-directory ]' "$init" ||
	fail 'P2 sparse diagnostic is not limited to the repeated directory failure'
for mount_detail in mkdir mount-call mountpoint mount-table mount-inventory \
	storage-read-only rog5-directory selector-absence; do
	grep -Fq "mount_persistent_root_failure=$mount_detail" "$init" ||
		fail "P2 target lacks userdata mount discriminator: $mount_detail"
done
grep -Fq '"userdata-$mount_persistent_root_failure"' "$init" ||
	fail 'P2 target does not publish the userdata mount discriminator'
for mount_probe_marker in \
	'blkid "$userdata"' \
	'dd if="$userdata" bs=1 skip=1024 count=64' \
	'od -An -v -tx1' \
	'dumpe2fs -h "$userdata"' \
	'casefold feature cannot be mounted without CONFIG_UNICODE' \
	'unsupported optional features' \
	'mount-call-s${mount_status}-${userdata_filesystem_detail}-${mount_kernel_detail}'; do
	grep -Fq "$mount_probe_marker" "$init" ||
		fail "P2 target lacks mount-call classifier: $mount_probe_marker"
done
filesystem_classifiers=$(mktemp)
awk '
	/^blkid_filesystem_type\(\) \{/ { copy=1 }
	/^classify_userdata_filesystem\(\) \{/ { copy=0 }
	copy { print }
' "$init" >"$filesystem_classifiers"
# shellcheck disable=SC1090
. "$filesystem_classifiers"
rm -f -- "$filesystem_classifiers"
[ "$(blkid_filesystem_type '/dev/sda23: LABEL="rog5-linux" UUID="15b5649a" TYPE="ext4"')" = ext4 ]
[ "$(blkid_filesystem_type '/dev/sda23: UUID="abcd" TYPE="f2fs"')" = f2fs ]
for hostile_blkid in \
	'/dev/sda23: LABEL="TYPE=ext4"' \
	'/dev/sda23: TYPE=ext4' \
	'/dev/sda23: TYPE="ext4"suffix' \
	'/dev/sda23: UUID="abcd"'; do
	[ "$(blkid_filesystem_type "$hostile_blkid")" = unknown ] ||
		fail 'P2 target accepts a malformed blkid type token'
done
ext4_magic=$(printf '%0112d' 0)53ef$(printf '%012d' 0)
f2fs_magic=1020f5f2$(printf '%0120d' 0)
[ "$(filesystem_magic_type "$ext4_magic")" = ext4 ]
[ "$(filesystem_magic_type "$f2fs_magic")" = f2fs ]
for hostile_magic in '' 53ef "${ext4_magic}00" "g${ext4_magic#?}"; do
	[ "$(filesystem_magic_type "$hostile_magic")" = unknown ] ||
		fail 'P2 target accepts malformed filesystem magic'
done
grep -Fq 'find_exact_userdata /sys/class/block /dev' "$init"
grep -Fq 'userdata_record=/run/rog5-p2-userdata-device' "$attest"
grep -Fq 'runtime_loader=/run/initramfs/lib/ld-musl-aarch64.so.1' "$attest"
grep -Fq '"$runtime_loader" "$runtime_busybox" blockdev "$@"' "$attest"
[ "$(grep -Fc '"$runtime_busybox" blockdev' "$attest")" -eq 1 ]
! grep -Fq '/dev/sda23' "$init" "$attest"
! grep -Fq '/sys/class/block/sda23' "$init" "$attest"
grep -Fq 'expected_udc=a600000.usb' "$init"
grep -Fq 'select_expected_udc' "$init"
! grep -Fq '*a600000*' "$init"
grep -Fq 'root_image=/mnt/userdata/rog5/images/arch-local-a.ext4' "$init"
grep -Fq 'losetup -r "$root_loop" "$root_image"' "$init"
grep -Fq 'mount -t ext4 -o ro,noload,nodev,nosuid,noatime' "$init"
grep -Fq 'blockdev --setrw "$userdata"' "$init"
grep -Fq 'blockdev --setrw "$userdata_disk"' "$init"
[ "$(grep -Fc 'blockdev --setrw' "$init")" -eq 2 ]
grep -Fq 'blockdev --setro "$userdata_disk"' "$init"
grep -Fq 'blockdev --setro "$userdata"' "$init"
grep -Fq 'format=rog5-local-image-write-probe-v1' "$init" "$attest"
grep -Fq 'expected_probe_bytes=132' "$init" "$attest"
[ "$(grep -Ec '^[[:space:]]*sync \|\| probe_status=1$' "$init")" -eq 1 ]
grep -Fq 'lowerdir=/mnt/root-ro' "$init"
grep -Fq 'upperdir=/mnt/state/upper,workdir=/mnt/state/work' "$init"
! grep -Fq '/usr/local/sbin/persistent-root-verify' "$init"
grep -Fq \
	'PASS sealed local image matches exact boot-critical identities' \
	"$init" "$attest"
grep -Fq 'handoff_persistent_root() {' "$init"
grep -Fq 'move_handoff_mount "$handoff_userdata"' "$init"
grep -Fq 'move_handoff_mount "$handoff_state"' "$init"
grep -Fq 'move_handoff_mount "$handoff_root"' "$init"
grep -Fq 'rollback_handoff_mounts || true' "$init"
grep -Fq 'trap switch_root_failure EXIT' "$init"
grep -Fq 'publish_stage switch-root PASS' "$init"
grep -Fq 'stage_record=$handoff_newroot/run/rog5-persistent-root-stage.record' \
	"$init"
grep -Fq 'stage_record=/run/rog5-persistent-root-stage.record' "$init"
grep -Fq 'report_current_stage_once || true' "$init"
grep -Fq 'boot_id=$target_boot_id' "$init"
grep -Fq 'exec switch_root /newroot /sbin/init' "$init"
[ "$(grep -Ec '^[[:space:]]*mount --move ' "$init")" -eq 1 ] ||
	fail 'persistent-root handoff has a direct or missing mount move'
grep -Fq 'unmanaged-devices=interface-name:usb0' "$init"
grep -Fq 'WantedBy=sysinit.target' "$init"
grep -Fq 'DefaultDependencies=no' "$init"
grep -Fq 'Requires=rog5-early-sshd.service' "$init"
grep -Fq 'sysinit.target.wants/rog5-p2-ready.service' "$init"
for timing_marker in \
	'cmdline:5' \
	'kernel-release-file:20' \
	'kernel-release-identity:25' \
	'ufs-discovery:35' \
	'ufs-power:50' \
	'storage-lock:65' \
	'userdata:80' \
	'inventory:95' \
	'usb:15' \
	'ufs-rendezvous:15' \
	'ufs-module:20'; do
	grep -Fq "$timing_marker" "$init"
done
grep -Fq 'failure timing marker stage=$stage delay=${delay}s' "$init"
grep -Fq 'sleep "$delay"' "$init"
grep -Fq 'ufs_modules=${4:-}' "$builder"
grep -Fq 'require_deferred_ufs_modules=${REQUIRE_DEFERRED_UFS_MODULES:-0}' \
	"$builder" || fail 'P2 builder does not expose the deferred-module contract'
for module in phy-qcom-qmp-ufs.ko ufshcd-core.ko ufshcd-pltfrm.ko \
	ufs-qcom.ko; do
	grep -Fq "$module" "$builder"
done
grep -Fq 'modinfo -F vermagic' "$builder"
grep -Fq 'rog5-ufs-modules' "$builder"
grep -Fq 'PERSISTENT_ROOT_POWER_MODULES_ROOT' "$builder"
grep -Fq 'PERSISTENT_ROOT_CHARGE_FIRMWARE_DIR' "$builder"
grep -Fq '52442f69be8a91347499bc7a5c45060ad2458bb711cf51f8a7fdd64c5d2d412b' \
	"$builder"
grep -Fq '/sbin/rog5-load-persistent-power-usb' "$init"
[ "$(grep -c '^load_module ' "$power_loader")" -eq 15 ]
grep -Fq "printf 'power-usb-%s\\n' \"\$code\"" "$power_loader"
grep -Fq 'fail "module-$detail-load" "module load failed: $name"' \
	"$power_loader"
grep -Fq 'load_module pdr_interface.ko pdr_interface pdr-interface' \
	"$power_loader"
grep -Fq 'power_usb_failure=power-usb-invalid-failure-record' "$init"
grep -Fq 'publish_stage ufs-ready FAIL "$power_usb_failure"' "$init"
grep -Fq 'side USB power is offline' "$power_loader"
grep -Fq 'storage appeared before the UFS stage' "$power_loader"
grep -Fq 'typec_data_role=device' "$power_loader"
grep -Fq 'typec_power_role=sink' "$power_loader"
grep -Fq 'NCM route changed' "$power_loader"
grep -Fq 'persistent-root PDR override retains rejected BTF' "$builder"
! grep -Eq 'charge_control|input_current_limit|constant_charge|charge_behaviour' \
	"$power_loader" || fail 'persistent-root loader exposes a charging-control write'
q6=$(grep -n '^load_module qcom_q6v5[.]ko ' "$power_loader" | cut -d: -f1)
pas=$(grep -n '^load_module qcom_q6v5_pas[.]ko ' "$power_loader" | cut -d: -f1)
qrtr=$(grep -n '^load_module qrtr[.]ko ' "$power_loader" | cut -d: -f1)
pdr=$(grep -n '^load_module pdr_interface[.]ko ' "$power_loader" | cut -d: -f1)
pmic=$(grep -n '^load_module pmic_glink[.]ko ' "$power_loader" | cut -d: -f1)
battery=$(grep -n '^load_module qcom_battmgr[.]ko ' "$power_loader" | cut -d: -f1)
ucsi=$(grep -n '^load_module ucsi_glink[.]ko ' "$power_loader" | cut -d: -f1)
[ "$q6" -lt "$pas" ] && [ "$pas" -lt "$qrtr" ] &&
	[ "$qrtr" -lt "$pdr" ] && [ "$pdr" -lt "$pmic" ] &&
	[ "$pmic" -lt "$battery" ] && [ "$battery" -lt "$ucsi" ] ||
	fail 'persistent-root power module order changed'
grep -Fq 's/@EXPECTED_KERNEL_RELEASE@/$expected_release/' "$builder"
for obsolete in \
	'deliver_readonly_ufs_proof' \
	'format=rog5-readonly-ufs-enumeration-proof-v1' \
	'nc -n -w 1 -s 169.254.77.2 169.254.77.1 8079' \
	'ufs-readonly-control'; do
	if grep -Fq "$obsolete" "$init"; then
		fail "local-root initramfs retained the obsolete enumeration terminal: $obsolete"
	fi
done
! grep -Fq 'stage/lib/modules' "$builder" ||
	fail 'deferred UFS modules must remain outside automatic module lookup'

release_read_line=$(grep -Fn "$release_read" "$init" | cut -d: -f1)
release_line=$(grep -Fn "$release_check" "$init" | cut -d: -f1)
cmdline_line=$(grep -n '^if \[ "$persistent_count" -ne 1 \]' "$init" |
	cut -d: -f1)
watchdog_line=$(grep -n '^arm_watchdog$' "$init" | cut -d: -f1)
wait_line=$(grep -n "log 'waiting for stable UFS discovery'" "$init" |
	cut -d: -f1)
lock_line=$(grep -n '^if ! lock_physical_storage; then$' "$init" |
	cut -d: -f1)
usb_line=$(grep -n '^if ! configure_usb; then$' "$init" | cut -d: -f1)
mount_line=$(grep -n '^if ! mount_persistent_root; then$' "$init" |
	cut -d: -f1)
verify_line=$(grep -n '^if ! verify_persistent_root; then$' "$init" |
	cut -d: -f1)
switch_line=$(grep -n '^exec switch_root /newroot /sbin/init$' "$init" |
	cut -d: -f1)
[ "$watchdog_line" -lt "$usb_line" ]
[ "$usb_line" -lt "$cmdline_line" ]
[ "$cmdline_line" -lt "$release_read_line" ]
[ "$release_read_line" -lt "$release_line" ]
[ "$usb_line" -lt "$wait_line" ]
[ "$wait_line" -lt "$lock_line" ]
[ "$lock_line" -lt "$mount_line" ]
[ "$mount_line" -lt "$verify_line" ]
[ "$verify_line" -lt "$switch_line" ]

failure_validator=$(mktemp)
awk '
	/^valid_power_usb_failure\(\) \{/ { copy=1 }
	/^publish_or_rollback\(\) \{/ { copy=0 }
	copy { print }
' "$init" >"$failure_validator"
# shellcheck disable=SC1090
. "$failure_validator"
rm -f -- "$failure_validator"
for valid_failure in \
	power-usb-module-pdr-interface-load \
	power-usb-telemetry-timeout \
	power-usb-ncm-carrier; do
	valid_power_usb_failure "$valid_failure" ||
		fail "power/USB failure validator rejected $valid_failure"
done
long_failure=power-usb-$(printf '%0130d' 0)
for invalid_failure in \
	'' power-usb- power-usb-UPPER power_usb_bad power-usb-trailing- \
	"power-usb-two
lines" "$long_failure"; do
	if valid_power_usb_failure "$invalid_failure"; then
		fail "power/USB failure validator accepted hostile input"
	fi
done

role_validator=$(mktemp)
awk '
	/^data_role_is_device\(\) \{/ { copy=1 }
	/^read_integer\(\) \{/ { copy=0 }
	copy { print }
' "$power_loader" >"$role_validator"
# shellcheck disable=SC1090
. "$role_validator"
rm -f -- "$role_validator"
for valid_data_role in device 'host [device]'; do
	data_role_is_device "$valid_data_role" ||
		fail "power/USB loader rejected valid data role: $valid_data_role"
done
for invalid_data_role in host '[host] device' 'host device' 'host [device] extra'; do
	if data_role_is_device "$invalid_data_role"; then
		fail "power/USB loader accepted inactive or malformed data role"
	fi
done
for valid_power_role in sink 'source [sink]'; do
	power_role_is_sink "$valid_power_role" ||
		fail "power/USB loader rejected valid power role: $valid_power_role"
done
for invalid_power_role in source '[source] sink' 'source sink' 'source [sink] extra'; do
	if power_role_is_sink "$invalid_power_role"; then
		fail "power/USB loader accepted inactive or malformed power role"
	fi
done

grep -Fq '/.rog5/userdata-ro' "$attest"
grep -Fq '/.rog5/root-ro' "$attest"
grep -Fq '/.rog5/state' "$attest"
grep -Fq 'findmnt' "$attest" ||
	grep -Fq '/proc/self/mountinfo' "$attest"
grep -Fq 'systemctl is-active --quiet rog5-early-sshd.service' "$attest"
grep -Fq '169.254.77.2/30' "$attest"
grep -Fq 'rog5-p2-ready' "$attest"
grep -Fq 'blocked device query' "$attest"
grep -Fq 'blocked SCSI opcode' "$attest"
grep -Eq 'journal.*recover|recovery.*journal' "$attest"

grep -Fq 'printf b >/proc/sysrq-trigger' "$shutdown"
grep -Fq '/oldsys/userdata-ro' "$shutdown"
grep -Fq '/oldsys/root-ro' "$shutdown"
grep -Fq '/oldsys/state' "$shutdown"
grep -Fq 'losetup -d "$loop_device"' "$shutdown"

if grep -Eq \
	'(^|[[:space:]])(fsck|e2fsck|tune2fs|mkfs|blkdiscard|reboot|poweroff|halt)([[:space:]]|$)|mount[[:space:]].*-o[[:space:]]+rw.*(/dev/|userdata)' \
	"$init" "$attest" "$shutdown"
then
	fail 'P2 target exposes an unreviewed repair, selector, or shutdown path'
fi
if grep -Eq \
	'(touch|install|mv|cp|ln|mkdir|printf|echo).*state/(good|next)|>[[:space:]]*[^[:space:]]*state/(good|next)' \
	"$init" "$attest" "$shutdown"
then
	fail 'P2 target writes a persistent root selector'
fi

if [ "$binary_integration" -eq 0 ]; then
	echo 'PASS persistent-root initramfs source, power/USB order, and storage-safety contract'
	exit 0
fi

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
if UFS_STORAGE_MODE=invalid "$builder" "$base" "$verifier" \
	"$work/invalid.cpio.gz" >"$work/invalid.out" 2>"$work/invalid.err"; then
	fail 'P2 builder accepted an invalid UFS storage mode'
fi
grep -Fxq 'FAIL UFS_STORAGE_MODE must be read-only or local-write' \
	"$work/invalid.err"
if UFS_STORAGE_MODE=read-only EXPECTED_PROBE_BOOT_ID=current \
	"$builder" "$base" "$verifier" "$work/read-only-current.cpio.gz" \
	>"$work/read-only-current.out" 2>"$work/read-only-current.err"; then
	fail 'P2 builder accepted current-boot marker binding for read-only mode'
fi
grep -Fxq \
	'FAIL EXPECTED_PROBE_BOOT_ID must pin a writer UUID for read-only' \
	"$work/read-only-current.err"
if [ -n "$ufs_modules" ]; then
	UFS_STORAGE_MODE=read-only EXPECTED_PROBE_BOOT_ID=any-prior \
		"$builder" "$base" "$verifier" \
		"$work/read-only-any-prior.cpio.gz" "$ufs_modules" >/dev/null
else
	UFS_STORAGE_MODE=read-only EXPECTED_PROBE_BOOT_ID=any-prior \
		"$builder" "$base" "$verifier" \
		"$work/read-only-any-prior.cpio.gz" >/dev/null
fi
gzip -dc "$work/read-only-any-prior.cpio.gz" |
	cpio -i --quiet --to-stdout init |
	grep -Fxq 'expected_probe_boot_id=any-prior'
if [ -n "$ufs_modules" ]; then
	UFS_STORAGE_MODE=read-only EXPECTED_PROBE_BOOT_ID=staged-seal \
		"$builder" "$base" "$verifier" \
		"$work/read-only-staged-seal.cpio.gz" "$ufs_modules" >/dev/null
else
	UFS_STORAGE_MODE=read-only EXPECTED_PROBE_BOOT_ID=staged-seal \
		"$builder" "$base" "$verifier" \
		"$work/read-only-staged-seal.cpio.gz" >/dev/null
fi
gzip -dc "$work/read-only-staged-seal.cpio.gz" |
	cpio -i --quiet --to-stdout init |
	grep -Fxq 'expected_probe_boot_id=staged-seal'
if PERSISTENT_ROOT_POWER_MODULES_ROOT="$work/missing-modules" \
	PERSISTENT_ROOT_CHARGE_FIRMWARE_DIR= \
	REQUIRE_DEFERRED_UFS_MODULES=0 \
	"$builder" "$base" "$verifier" "$work/missing-firmware.cpio.gz" \
	>"$work/missing-firmware.out" 2>"$work/missing-firmware.err"; then
	fail 'P2 builder accepted power modules without charging firmware'
fi
grep -Fxq 'FAIL power modules and charging firmware must be supplied together' \
	"$work/missing-firmware.err"
if UFS_STORAGE_MODE=local-write EXPECTED_PROBE_BOOT_ID="$writer_boot_id" \
	"$builder" "$base" "$verifier" "$work/local-write-pinned.cpio.gz" \
	>"$work/local-write-pinned.out" 2>"$work/local-write-pinned.err"; then
	fail 'P2 builder accepted pinned stale marker binding for local-write mode'
fi
grep -Fxq 'FAIL EXPECTED_PROBE_BOOT_ID must be current for local-write' \
	"$work/local-write-pinned.err"
if REQUIRE_DEFERRED_UFS_MODULES=1 "$builder" "$base" "$verifier" \
	"$work/missing-required-modules.cpio.gz" \
	>"$work/missing-required-modules.out" \
	2>"$work/missing-required-modules.err"; then
	fail 'P2 builder accepted a module-less image under the required contract'
fi
grep -Fxq 'FAIL deferred UFS modules are required for this kernel' \
	"$work/missing-required-modules.err"
if [ -n "$ufs_modules" ]; then
	UFS_STORAGE_MODE=$storage_mode \
	"$builder" "$base" "$verifier" "$work/a.cpio.gz" \
		"$ufs_modules" >/dev/null
	UFS_STORAGE_MODE=$storage_mode \
	"$builder" "$base" "$verifier" "$work/b.cpio.gz" \
		"$ufs_modules" >/dev/null
else
	UFS_STORAGE_MODE=$storage_mode \
	"$builder" "$base" "$verifier" "$work/a.cpio.gz" >/dev/null
	UFS_STORAGE_MODE=$storage_mode \
	"$builder" "$base" "$verifier" "$work/b.cpio.gz" >/dev/null
fi
cmp "$work/a.cpio.gz" "$work/b.cpio.gz"

mkdir "$work/root"
gzip -dc "$work/a.cpio.gz" |
	(cd "$work/root" && cpio -idm --quiet --no-absolute-filenames)
sed -e "s/@EXPECTED_KERNEL_RELEASE@/${EXPECTED_RELEASE:-7.1.4-gcdf38b1ddebb}/" \
	-e "s/@EXPECTED_UFS_STORAGE_MODE@/$storage_mode/" \
	-e "s/@EXPECTED_PROBE_BOOT_ID@/$sealed_probe_boot_id/" \
	"$init" >"$work/expected-init"
cmp "$work/root/init" "$work/expected-init"
cmp "$work/root/shutdown" "$shutdown"
readelf -h "$work/root/usr/libexec/rog5-reboot-bootloader" |
	grep -q 'Machine:.*AArch64'
! readelf -d "$work/root/usr/libexec/rog5-reboot-bootloader" |
	grep -q '(NEEDED)'
! readelf -l "$work/root/usr/libexec/rog5-reboot-bootloader" |
	grep -q 'Requesting program interpreter'
sed -e "s/@EXPECTED_UFS_STORAGE_MODE@/$storage_mode/" \
	-e "s/@EXPECTED_PROBE_BOOT_ID@/$sealed_probe_boot_id/" \
	"$attest" >"$work/expected-attest"
cmp "$work/root/usr/local/sbin/rog5-p2-attest" "$work/expected-attest"
cmp "$work/root/usr/local/sbin/persistent-root-verify" "$verifier"
readelf -l "$work/root/bin/busybox" |
	grep -Fq '[Requesting program interpreter: /lib/ld-musl-aarch64.so.1]'
readelf -d "$work/root/bin/busybox" |
	grep -Fq 'Shared library: [libc.musl-aarch64.so.1]'
[ -f "$work/root/lib/ld-musl-aarch64.so.1" ] &&
	[ ! -L "$work/root/lib/ld-musl-aarch64.so.1" ] &&
	[ -x "$work/root/lib/ld-musl-aarch64.so.1" ]
if command -v qemu-aarch64-static >/dev/null 2>&1; then
	qemu-aarch64-static "$work/root/lib/ld-musl-aarch64.so.1" \
		"$work/root/bin/busybox" true
fi
grep -Fqx "expected_kernel_release=${EXPECTED_RELEASE:-7.1.4-gcdf38b1ddebb}" \
	"$work/root/init"
! grep -Fq '@EXPECTED_KERNEL_RELEASE@' "$work/root/init"
grep -Fqx "expected_ufs_storage_mode=$storage_mode" "$work/root/init"
! grep -Fq '@EXPECTED_UFS_STORAGE_MODE@' "$work/root/init"
grep -Fqx "expected_probe_boot_id=$sealed_probe_boot_id" "$work/root/init"
grep -Fqx "expected_probe_boot_id=$sealed_probe_boot_id" \
	"$work/root/usr/local/sbin/rog5-p2-attest"
! grep -Fq '@EXPECTED_PROBE_BOOT_ID@' "$work/root/init" \
	"$work/root/usr/local/sbin/rog5-p2-attest"

if [ -n "$ufs_modules" ]; then
	module_inventory=$(find "$work/root/rog5-ufs-modules" \
		-mindepth 1 -maxdepth 1 -printf '%f\n' | sort |
		tr '\n' ' ')
	[ "$module_inventory" = \
		'phy-qcom-qmp-ufs.ko ufs-qcom.ko ufshcd-core.ko ufshcd-pltfrm.ko ' ] ||
		fail 'built initramfs has the wrong deferred UFS module inventory'
	for module in phy-qcom-qmp-ufs.ko ufshcd-core.ko ufshcd-pltfrm.ko \
		ufs-qcom.ko; do
		cmp "$work/root/rog5-ufs-modules/$module" \
			"$ufs_modules/$module"
	done
	[ ! -e "$work/root/lib/modules" ] ||
		fail 'deferred UFS modules entered automatic module lookup'

	cp -a -- "$ufs_modules" "$work/modules-extra"
	: >"$work/modules-extra/unexpected.ko"
	if "$builder" "$base" "$verifier" "$work/extra.cpio.gz" \
		"$work/modules-extra" >/dev/null 2>&1; then
		fail 'builder accepted an extra deferred UFS module'
	fi
	cp -a -- "$ufs_modules" "$work/modules-extra-symlink"
	ln -s /dev/null "$work/modules-extra-symlink/unexpected.ko"
	if "$builder" "$base" "$verifier" "$work/extra-symlink.cpio.gz" \
		"$work/modules-extra-symlink" >/dev/null 2>&1; then
		fail 'builder accepted an extra symlink in the deferred module inventory'
	fi
	cp -a -- "$ufs_modules" "$work/modules-symlink"
	rm -- "$work/modules-symlink/ufs-qcom.ko"
	ln -s /dev/null "$work/modules-symlink/ufs-qcom.ko"
	if "$builder" "$base" "$verifier" "$work/symlink.cpio.gz" \
		"$work/modules-symlink" >/dev/null 2>&1; then
		fail 'builder accepted a symlinked deferred UFS module'
	fi
fi

if [ -n "${PERSISTENT_ROOT_POWER_MODULES_ROOT:-}" ]; then
	cmp "$work/root/sbin/rog5-load-persistent-power-usb" "$power_loader"
	[ "$(find "$work/root/rog5-power-usb-modules" -type f -name '*.ko' | wc -l)" \
		-eq 15 ] || fail 'built initramfs has the wrong power module inventory'
	[ "$(find "$work/root/opt/rog5-charge-firmware" -type f | wc -l)" -eq 29 ] ||
		fail 'built initramfs has the wrong charging firmware inventory'
fi

[ ! -e "$work/root/root/.ssh/authorized_keys" ]
[ -z "$(find "$work/root/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*' -print -quit 2>/dev/null)" ]
! find "$work/root" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .
! readelf -d "$work/root/usr/local/sbin/persistent-root-verify" |
	grep -q '(NEEDED)'
! readelf -l "$work/root/usr/local/sbin/persistent-root-verify" |
	grep -q 'Requesting program interpreter'

handoff_functions=$work/handoff-functions.sh
awk '
	/^move_handoff_mount\(\) \{/ { copy=1 }
	/^recovery_timeout=/ { copy=0 }
	copy { print }
' "$init" >"$handoff_functions"
grep -Fq 'handoff_persistent_root() {' "$handoff_functions"
# shellcheck disable=SC1090
. "$handoff_functions"
handoff_tree=$work/handoff
handoff_newroot=$handoff_tree/newroot
handoff_userdata=$handoff_tree/userdata
handoff_root=$handoff_tree/root-ro
handoff_state=$handoff_tree/state
handoff_dev=$handoff_tree/dev
handoff_proc=$handoff_tree/proc
handoff_sys=$handoff_tree/sys
handoff_run=$handoff_tree/run
mkdir -p "$handoff_userdata" "$handoff_root" "$handoff_state" "$handoff_dev" \
	"$handoff_proc" "$handoff_sys" "$handoff_run"
handoff_move_count=0
handoff_fail_at=0
move_handoff_mount() {
	handoff_move_count=$((handoff_move_count + 1))
	[ "$handoff_move_count" -ne "$handoff_fail_at" ]
}
for handoff_fail_at in 1 2 3 4 5 6 7; do
	handoff_move_count=0
	if handoff_persistent_root; then
		fail "persistent-root handoff accepted failed move $handoff_fail_at"
	fi
	[ "$handoff_move_count" -eq "$((handoff_fail_at * 2 - 1))" ]
done
handoff_fail_at=0
handoff_move_count=0
handoff_persistent_root
[ "$handoff_move_count" -eq 7 ]

switch_root_failure_log=$work/switch-root-failure
switch_root_failure_probe=$work/switch-root-failure-probe.sh
cp "$handoff_functions" "$switch_root_failure_probe"
cat >>"$switch_root_failure_probe" <<'EOF'
rollback_handoff_mounts() {
	printf 'rollback\n' >>"$SWITCH_ROOT_FAILURE_LOG"
}
publish_stage() {
	[ "$1:$2" = switch-root:FAIL ] || exit 76
	printf 'failed\n' >>"$SWITCH_ROOT_FAILURE_LOG"
}
log() { :; }
force_rollback() {
	printf 'forced\n' >>"$SWITCH_ROOT_FAILURE_LOG"
	exit 77
}
sleep() { :; }
trap switch_root_failure EXIT
if exec /rog5-definitely-missing-switch-root; then
	exit 0
else
	exit $?
fi
EOF
chmod 0755 "$switch_root_failure_probe"
if SWITCH_ROOT_FAILURE_LOG="$switch_root_failure_log" \
	bash -O execfail "$switch_root_failure_probe" 2>/dev/null; then
	fail 'failed switch_root exec bypassed the rollback trap'
else
	switch_root_failure_status=$?
fi
[ "$switch_root_failure_status" -eq 77 ]
printf 'rollback\nfailed\nforced\n' >"$work/expected-switch-root-failure"
cmp "$switch_root_failure_log" "$work/expected-switch-root-failure"

echo 'PASS deterministic credential-free P2 initramfs pins exact UFS, one bounded image write, read-only runtime, tmpfs OverlayFS, restart2 rollback, and emergency SysRq fallback'
