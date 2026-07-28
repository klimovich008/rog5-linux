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
[ "$(sha256sum "$config" | cut -d ' ' -f 1)" = \
	8a7fabffa076a65d09529ef1004c315e1296e547a02d08c362031d0363ba63c3 ] ||
	fail 'P2 runtime-config identity does not match the pinned target config'

for script in "$init" "$attest" "$shutdown" "$builder"; do
	sh -n "$script"
done

grep -Fq 'rog5.persistent_ro=1' "$init"
grep -Fq 'expected_config_sha256=8a7fabffa076a65d09529ef1004c315e1296e547a02d08c362031d0363ba63c3' \
	"$init"
grep -Fq 'kernel_config=/run/rog5-kernel.config' "$init"
grep -Fq 'gzip -dc /proc/config.gz >"$kernel_config"' "$init"
grep -Fq 'chmod 0400 "$kernel_config"' "$init"
grep -Fq 'sha256sum "$kernel_config"' "$init"
config_decode_count=$(grep -Fc \
	'gzip -dc /proc/config.gz >"$kernel_config"' "$init" || true)
[ "$config_decode_count" -eq 1 ] ||
	fail "expected one runtime-config decode, found $config_decode_count"
config_hash_count=$(grep -Fc 'sha256sum "$kernel_config"' "$init" || true)
[ "$config_hash_count" -eq 1 ] ||
	fail "expected one runtime-config identity check, found $config_hash_count"
grep -Fq 'expected_physical_count=116' "$init"
grep -Fq 'expected_seal_sha256=e201955dead61a04ca0e70d67fcea18750940330421334c91cfe2c760e7fb3ff' \
	"$init"
grep -Fq 'expected_tree_sha256=b71eccbe5275f8d125a6d3251fff166b57f196c23984b845e31666ecaaea9a8c' \
	"$init"
grep -Fq 'mount -t ext4 -o ro,noload "$userdata" /mnt/userdata' "$init"
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
	'config-file:10' \
	'config-decode:15' \
	'config-identity:20' \
	'ufs-discovery:35' \
	'ufs-power:50' \
	'storage-lock:65' \
	'userdata:80' \
	'inventory:95' \
	'usb:110'; do
	grep -Fq "$timing_marker" "$init"
done
grep -Fq 'failure timing marker stage=$stage delay=${delay}s' "$init"
grep -Fq 'sleep "$delay"' "$init"

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
[ "$watchdog_line" -lt "$wait_line" ]
[ "$wait_line" -lt "$lock_line" ]
[ "$lock_line" -lt "$usb_line" ]
[ "$usb_line" -lt "$mount_line" ]
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
"$builder" "$base" "$verifier" "$work/a.cpio.gz" >/dev/null
"$builder" "$base" "$verifier" "$work/b.cpio.gz" >/dev/null
cmp "$work/a.cpio.gz" "$work/b.cpio.gz"

mkdir "$work/root"
gzip -dc "$work/a.cpio.gz" |
	(cd "$work/root" && cpio -idm --quiet --no-absolute-filenames)
cmp "$work/root/init" "$init"
cmp "$work/root/shutdown" "$shutdown"
cmp "$work/root/usr/local/sbin/rog5-p2-attest" "$attest"
cmp "$work/root/usr/local/sbin/persistent-root-verify" "$verifier"

[ ! -e "$work/root/root/.ssh/authorized_keys" ]
[ -z "$(find "$work/root/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*' -print -quit 2>/dev/null)" ]
! find "$work/root" -type f -exec grep -Il 'BEGIN .*PRIVATE KEY' {} + |
	grep -q .

echo 'PASS deterministic credential-free P2 initramfs pins one-pass runtime config identity, read-only UFS, exact userdata/root seal, tmpfs OverlayFS, and SysRq rollback'
