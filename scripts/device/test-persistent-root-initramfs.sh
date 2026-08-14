#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/persistent-root-init
attest=$repo/initramfs/persistent-root-attest
shutdown=$repo/initramfs/persistent-root-shutdown
builder=$repo/scripts/device/build-persistent-root-initramfs.sh
base=${1:-$repo/artifacts/ufs-discovery-v2/rog5-ufs-discovery-initramfs.cpio.gz}
verifier=${2:-$repo/artifacts/persistent-root-verifier-build-a/persistent-root-verify}
config=${3:-$repo/artifacts/persistent-root-p2/config-7.1.4-persistent-root}
ufs_modules=${4:-}
storage_mode=${UFS_STORAGE_MODE:-read-only}

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in cpio gzip grep mktemp sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing P2 initramfs test command: $command"
done
for path in "$init" "$attest" "$shutdown" "$builder"; do
	[ -x "$path" ] || fail "missing executable P2 source: $path"
done
[ -s "$base" ] && [ -x "$verifier" ] && [ -s "$config" ] ||
	fail 'missing P2 initramfs binary input'
config_sha256=$(sha256sum "$config" | cut -d ' ' -f 1)
if [ -n "$ufs_modules" ]; then
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
grep -Fq '[ "$expected_ufs_storage_mode" = local-write ]' "$init" ||
	fail 'P2 target lacks the local-write UFS policy branch'
grep -Fq "'ROG5 UFS discovery: forced read-only before registration'" "$init" ||
	fail 'local-write policy does not reject the discovery-only disk guard'
grep -Fq 'UFS_STORAGE_MODE must be read-only or local-write' "$builder" ||
	fail 'P2 builder does not fail closed on the storage mode'
grep -Fq 'expected_ufs_storage_mode=$storage_mode' "$builder" ||
	fail 'P2 builder does not seal the selected storage mode'
grep -Fq 'expected_physical_count=116' "$init"
grep -Fq 'expected_seal_sha256=02231e86746fbc656090f52c96d7e0c968c7ca86ba7449c306f611ea20c6a876' \
	"$init"
grep -Fq 'expected_tree_sha256=4701c23b93624bf894bb76331c165b650c9a2aecb99273a4e6d37c20ac3ef167' \
	"$init"
grep -Fq 'expected_image_bytes=17179869184' "$init" "$attest"
grep -Fq 'expected_image_uuid=598a876b-a8db-4859-a01a-1b864b0a87f4' \
	"$init" "$attest"
grep -Fq 'mount -t ext4 -o ro,noload "$userdata" /mnt/userdata' "$init"
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
grep -Fq 'WantedBy=multi-user.target' "$init"
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
for module in phy-qcom-qmp-ufs.ko ufshcd-core.ko ufshcd-pltfrm.ko \
	ufs-qcom.ko; do
	grep -Fq "$module" "$builder"
done
grep -Fq 'modinfo -F vermagic' "$builder"
grep -Fq 'rog5-ufs-modules' "$builder"
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

grep -Fq '/.rog5/userdata-ro' "$attest"
grep -Fq '/.rog5/root-ro' "$attest"
grep -Fq '/.rog5/state' "$attest"
grep -Fq 'findmnt' "$attest" ||
	grep -Fq '/proc/self/mountinfo' "$attest"
grep -Fq 'systemctl is-active --quiet sshd.service' "$attest"
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

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
if UFS_STORAGE_MODE=invalid "$builder" "$base" "$verifier" \
	"$work/invalid.cpio.gz" >"$work/invalid.out" 2>"$work/invalid.err"; then
	fail 'P2 builder accepted an invalid UFS storage mode'
fi
grep -Fxq 'FAIL UFS_STORAGE_MODE must be read-only or local-write' \
	"$work/invalid.err"
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
	"$init" >"$work/expected-init"
cmp "$work/root/init" "$work/expected-init"
cmp "$work/root/shutdown" "$shutdown"
cmp "$work/root/usr/local/sbin/rog5-p2-attest" "$attest"
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

echo 'PASS deterministic credential-free P2 initramfs pins exact UFS, one bounded image write, read-only runtime, tmpfs OverlayFS, and SysRq rollback'
