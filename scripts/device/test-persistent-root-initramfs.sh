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
	[ "$config_sha256" = \
		b959774825e2bca7c634e55cd00e838121fde8d95fd214ffeead732ce92e35e6 ]
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
grep -Fq 'expected_physical_count=116' "$init"
grep -Fq 'expected_seal_sha256=e201955dead61a04ca0e70d67fcea18750940330421334c91cfe2c760e7fb3ff' \
	"$init"
grep -Fq 'expected_tree_sha256=b71eccbe5275f8d125a6d3251fff166b57f196c23984b845e31666ecaaea9a8c' \
	"$init"
grep -Fq 'mount -t ext4 -o ro,noload "$userdata" /mnt/userdata' "$init"
grep -Fq 'find_exact_userdata /sys/class/block /dev' "$init"
grep -Fq 'userdata_record=/run/rog5-p2-userdata-device' "$attest"
! grep -Fq '/dev/sda23' "$init" "$attest"
! grep -Fq '/sys/class/block/sda23' "$init" "$attest"
grep -Fq 'expected_udc=a600000.usb' "$init"
grep -Fq 'select_expected_udc' "$init"
! grep -Fq '*a600000*' "$init"
grep -Fq 'lowerdir=/mnt/userdata/rog5/roots/arch-a' "$init"
grep -Fq 'upperdir=/mnt/state/upper,workdir=/mnt/state/work' "$init"
grep -Fq '/usr/local/sbin/persistent-root-verify' "$init"
grep -Fq 'mount --move /mnt/userdata /newroot/.rog5/userdata-ro' "$init"
grep -Fq 'mount --move /mnt/state /newroot/.rog5/state' "$init"
grep -Fq 'exec switch_root /newroot /sbin/init' "$init"
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
	'ufs-module:20' \
	'ufs-readonly-control:5'; do
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
grep -Fq 'format=rog5-readonly-ufs-enumeration-proof-v1' "$init"
grep -Fq 'target_release=$running_kernel_release' "$init"
grep -Fq 'modules=phy_qcom_qmp_ufs,ufshcd_core,ufshcd_pltfrm,ufs_qcom' "$init"
grep -Fq 'physical_blocks=$physical_blocks' "$init"
grep -Fq 'all_physical_read_only=1' "$init"
grep -Fq 'block_backed_mounts=0' "$init"
grep -Fq 'phone_storage_mounts=0' "$init"
grep -Fq 'phone_storage_writes=0' "$init"
grep -Fq 'nc -n -w 1 -s 169.254.77.2 169.254.77.1 8079' "$init"
proof_line=$(grep -nF 'readonly_record=$(printf' "$init" | cut -d: -f1)
insmod_line=$(grep -nF 'insmod /rog5-ufs-modules/ufs-qcom.ko' "$init" |
	cut -d: -f1)
control_line=$(grep -nF '# Keep the read-only enumeration identity alive long enough' \
	"$init" | cut -d: -f1)
[ "$insmod_line" -lt "$proof_line" ]
[ "$proof_line" -lt "$control_line" ]
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
grep -Fq '/oldsys/state' "$shutdown"

if grep -Eq \
	'(^|[[:space:]])(sync|fsck|e2fsck|tune2fs|mkfs|blkdiscard|reboot|poweroff|halt)([[:space:]]|$)|mount[[:space:]].*-o[[:space:]]+rw.*(/dev/|userdata)' \
	"$init" "$attest" "$shutdown"
then
	fail 'P2 target exposes a physical-write, repair, selector, or orderly-shutdown path'
fi
if grep -Eq \
	'(touch|install|mv|cp|ln|mkdir|printf|echo).*state/(good|next)|>[[:space:]]*[^[:space:]]*state/(good|next)' \
	"$init" "$attest" "$shutdown"
then
	fail 'P2 target writes a persistent root selector'
fi

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
if [ -n "$ufs_modules" ]; then
	"$builder" "$base" "$verifier" "$work/a.cpio.gz" \
		"$ufs_modules" >/dev/null
	"$builder" "$base" "$verifier" "$work/b.cpio.gz" \
		"$ufs_modules" >/dev/null
else
	"$builder" "$base" "$verifier" "$work/a.cpio.gz" >/dev/null
	"$builder" "$base" "$verifier" "$work/b.cpio.gz" >/dev/null
fi
cmp "$work/a.cpio.gz" "$work/b.cpio.gz"

mkdir "$work/root"
gzip -dc "$work/a.cpio.gz" |
	(cd "$work/root" && cpio -idm --quiet --no-absolute-filenames)
sed "s/@EXPECTED_KERNEL_RELEASE@/${EXPECTED_RELEASE:-7.1.4-gcdf38b1ddebb}/" \
	"$init" >"$work/expected-init"
cmp "$work/root/init" "$work/expected-init"
cmp "$work/root/shutdown" "$shutdown"
cmp "$work/root/usr/local/sbin/rog5-p2-attest" "$attest"
cmp "$work/root/usr/local/sbin/persistent-root-verify" "$verifier"
grep -Fqx "expected_kernel_release=${EXPECTED_RELEASE:-7.1.4-gcdf38b1ddebb}" \
	"$work/root/init"
! grep -Fq '@EXPECTED_KERNEL_RELEASE@' "$work/root/init"

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

echo 'PASS deterministic credential-free P2 initramfs pins exact running-kernel release, read-only UFS, exact userdata/root seal, tmpfs OverlayFS, and SysRq rollback'
