#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
helper=$repo/initramfs/persistent-service-state
init=$repo/initramfs/persistent-root-init
builder=$repo/scripts/device/build-persistent-root-standalone-initramfs.sh
shutdown=$repo/initramfs/persistent-root-shutdown-standalone
ssh_identity=$repo/initramfs/persistent-ssh-identity

fail() { echo "FAIL $*" >&2; exit 1; }

for path in "$helper" "$init" "$builder" "$shutdown" "$ssh_identity"; do
	[ -x "$path" ]
	sh -n "$path"
done

for contract in \
	'expected_physical_count=117' \
	'expected_userdata_partition=23' \
	'expected_userdata_start=18821440' \
	'expected_userdata_sectors=408997568' \
	'expected_userdata_partuuid=8d82ef11-4d42-60e9-24e8-4d6ebf20491b' \
	'expected_userdata_uuid=0892bacf-3e02-41b0-84a4-5f05c2df7ce5' \
	'expected_state_uuid=52037413-561a-48f4-92c4-8ad45b748a6f' \
	'expected_manifest_sha256=2c93224d74394876d1617f193f7ec7c3c1cac4575c95da1dfb233557d0819ea6' \
	'state_relative=rog5/state/server-state-v1.ext4' \
	'preflight_state() {' \
	'format=rog5-persistent-service-state-preflight-v1' \
	'verify_storage_read_only' \
	'verify_only_root_mount' \
	'verify_write_window' \
	'bb blockdev --setrw "$userdata"' \
	'bb blockdev --setrw "$userdata_disk"' \
	'bb mount -t ext4 -o rw,nodev,nosuid,noexec,noatime' \
	'bb losetup -d "$recorded_loop"' \
	'bb umount "$state_mount" || status=1' \
	'bb losetup -d "$recorded_loop" || status=1' \
	'bb umount "$userdata_mount" || status=1' \
	'relock_storage || status=1'; do
	grep -Fq "$contract" "$helper" || fail "missing helper contract: $contract"
done

for forbidden in fastboot adb sgdisk parted fdisk mkfs blkdiscard wipefs \
	'/dev/sda23' 'rm -rf'; do
	! grep -Fq "$forbidden" "$helper" || fail "forbidden helper surface: $forbidden"
done

[ "$(grep -Fc 'blockdev --setrw' "$helper")" -eq 2 ]
[ "$(grep -Fc 'mount -t ext4 -o rw,nodev,nosuid,noexec,noatime' "$helper")" -eq 2 ]
[ "$(grep -Fc 'trap cleanup_start EXIT HUP INT TERM' "$helper")" -eq 1 ]
! grep -Eq '^[[:space:]]*\[ .* =$' "$helper"
! grep -Eq '^[[:space:]]*\[ .* =$' "$ssh_identity"

for contract in \
	'persist_identity=$persist_root/host-ed25519-v1' \
	'identity_record=/run/rog5-persistent-ssh-identity.record' \
	'verify_key_pair() {' \
	'verify_sshd_listener() {' \
	'ssh-keygen -y -f "$private"' \
	'bb awk '\''{ print $1 " " $2 }'\'' ' \
	'PPid:[[:space:]]*' \
	'kill -HUP "$sshd_pid"' \
	'format=rog5-persistent-ssh-identity-v1' \
	'format=rog5-persistent-ssh-preflight-v1'; do
	grep -Fq "$contract" "$ssh_identity" ||
		fail "missing persistent SSH contract: $contract"
done
[ "$(grep -Fc 'identity_record=/run/rog5-persistent-ssh-identity.record' \
	"$ssh_identity")" -eq 1 ]
! grep -Fxq 'identity_record=/run/rog5-persistent-ssh-identity' "$ssh_identity"
grep -Fq '[ "$identity_record" != "$0" ]' "$ssh_identity"
for forbidden in fastboot adb sgdisk parted fdisk mkfs blkdiscard wipefs \
	'/dev/sda' 'rm -rf'; do
	! grep -Fq "$forbidden" "$ssh_identity" ||
		fail "forbidden persistent SSH surface: $forbidden"
done

grep -Fq 'cp -p /usr/local/sbin/rog5-persistent-state' "$init"
grep -Fq 'find_exact_userdata /sys/class/block /dev' "$init"
grep -Fq 'Requires=rog5-p2-ready.service' "$init"
grep -Fq 'After=rog5-p2-ready.service' "$init"
grep -Fq 'ExecStart=/run/rog5-persistent-state start' "$init"
grep -Fq 'ExecStop=/run/rog5-persistent-state stop' "$init"
grep -Fq 'sysinit.target.wants/rog5-persistent-state.service' "$init"
grep -Fq 'Requires=rog5-persistent-state.service rog5-early-sshd.service' "$init"
grep -Fq 'ExecStart=/run/rog5-persistent-ssh-identity apply' "$init"
grep -Fq 'sysinit.target.wants/rog5-persistent-ssh-identity.service' "$init"
grep -Fq 'install -D -m 0755 "$state_helper"' "$builder"
grep -Fq 'detach_persistent_state || clean=0' "$shutdown"
grep -Fq 'losetup -d "$loop_device"' "$shutdown"
grep -Fq 'loop_device=/oldsys/dev/${loop_device#/dev/}' "$shutdown"
persist_lazy=$(grep -n 'lazy_unmount /oldroot/persist' "$shutdown" | cut -d: -f1)
root_lazy=$(grep -n 'lazy_unmount /oldroot$' "$shutdown" | cut -d: -f1)
[ "$persist_lazy" -lt "$root_lazy" ]

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
awk '
	/^verify_key_pair\(\) \{/ { copy=1 }
	/^verify_sshd_listener\(\) \{/ { copy=0 }
	copy { print }
' "$ssh_identity" >"$work/verify-key-pair.sh"
ssh-keygen -q -t ed25519 -N '' -C root@alarm -f "$work/key-a"
ssh-keygen -q -t ed25519 -N '' -C other@alarm -f "$work/key-b"
chmod 0600 "$work/key-a" "$work/key-b"
chmod 0644 "$work/key-a.pub" "$work/key-b.pub"
bb() {
	applet=$1
	shift
	if [ "$applet:$1" = stat:-c ]; then
		path=$3
		case $path in
			*.pub) printf '0:0:644:92:1\n' ;;
			*) printf '0:0:600:399:1\n' ;;
		esac
		return 0
	fi
	command "$applet" "$@"
}
# shellcheck disable=SC1090
. "$work/verify-key-pair.sh"
verify_key_pair "$work/key-a" "$work/key-a.pub"
cp "$work/key-b.pub" "$work/key-a.pub"
! verify_key_pair "$work/key-a" "$work/key-a.pub"

manifest=$work/rog5-state.manifest
printf '%s\n' \
	'format=rog5-persistent-service-state-v1' \
	'image_bytes=4294967296' \
	'image_uuid=52037413-561a-48f4-92c4-8ad45b748a6f' \
	'layout=home,root,var-lib,var-log,etc-ssh,secrets' >"$manifest"
[ "$(stat -c %s "$manifest")" -eq 160 ]
[ "$(sha256sum "$manifest" | cut -d ' ' -f 1)" = \
	2c93224d74394876d1617f193f7ec7c3c1cac4575c95da1dfb233557d0819ea6 ]
printf x >>"$manifest"
[ "$(sha256sum "$manifest" | cut -d ' ' -f 1)" != \
	2c93224d74394876d1617f193f7ec7c3c1cac4575c95da1dfb233557d0819ea6 ]

echo 'PASS persistent state mounts only exact p23/image after P2 and relocks on stop'
