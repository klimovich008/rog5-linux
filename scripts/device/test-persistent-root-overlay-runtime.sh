#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
init=$repo/initramfs/persistent-root-init
attest=$repo/initramfs/persistent-root-attest
state=$repo/initramfs/persistent-service-state
shutdown=$repo/initramfs/persistent-root-shutdown-standalone
builder=$repo/scripts/device/build-persistent-root-standalone-initramfs.sh
stager=$repo/scripts/device/stage-persistent-root-overlay.sh
failure_fixture=$repo/tests/fixtures/persistent-root/overlay-v1-attest-failure.log
exec_failure_fixture=$repo/tests/fixtures/persistent-root/overlay-v4-nonroot-exec-failure.log

fail() { echo "FAIL $*" >&2; exit 1; }

for path in "$init" "$attest" "$state" "$shutdown" "$builder" "$stager"; do
	[ -x "$path" ] || fail "missing executable: $path"
	sh -n "$path"
done

grep -Fq 'stage sequence=25 stage=switch-root state=PASS' "$failure_fixture"
grep -Fq 'rog5-p2-attest: FAIL overlay state is not writable tmpfs' \
	"$failure_fixture"
grep -Fq 'overlay_state=rw,nosuid,nodev,noexec,noatime' \
	"$exec_failure_fixture"
grep -Fq 'uid=81 executable=/bin/true result=127' "$exec_failure_fixture"
for contract in \
	'expected_persistent_overlay_mode=@EXPECTED_PERSISTENT_OVERLAY_MODE@' \
	'overlay_record=/run/rog5-persistent-overlay.runtime' \
	'format=rog5-persistent-root-overlay-runtime-v1' \
	'expected_block_mounts=3' \
	'overlay_state=ext4-rw-exec' \
	'root=native-ext4-overlay-persistent'; do
	grep -Fq "$contract" "$attest" || fail "missing attestation contract: $contract"
done

for contract in \
	'expected_persistent_overlay_mode=@EXPECTED_PERSISTENT_OVERLAY_MODE@' \
	'expected_overlay_bytes=17179869184' \
	'expected_overlay_uuid=f4834541-6e7a-4214-80d5-818fcc5cc252' \
	'expected_overlay_label=ROG5_ROOT_RW_V1' \
	'overlay_relative=rog5/root/root-overlay-v1.ext4' \
	'prepare_persistent_overlay() {' \
	'verify_persistent_overlay_runtime() {' \
	'verify_overlay_workdir_pre_mount() {' \
	'verify_exact_rw_exec_mount() {' \
	'format=rog5-persistent-root-overlay-runtime-v1' \
	'upperdir=/mnt/state/upper,workdir=/mnt/state/work' \
	'"$handoff_newroot/.rog5/userdata-rw"'; do
	grep -Fq "$contract" "$init" || fail "missing init contract: $contract"
done
grep -Fq 'mount -t ext4 -o rw,nodev,nosuid,noatime' "$init"
! grep -A1 -F '"$overlay_loop" /mnt/state' "$init" | grep -Fq noexec

for contract in \
	'PERSISTENT_ROOT_OVERLAY' \
	'EXPECTED_STANDALONE_BASE_SHA256' \
	'EXPECTED_PERSISTENT_OVERLAY_MODE' \
	'PERSISTENT_ROOT_OVERLAY must be 0 or 1'; do
	grep -Fq "$contract" "$builder" || fail "missing builder contract: $contract"
done

for contract in \
	'overlay_record=/run/rog5-persistent-overlay.runtime' \
	'userdata_owner=overlay' \
	'[ "$userdata_owner" = overlay ]' \
	'bb umount "$userdata_mount" || status=1'; do
	grep -Fq "$contract" "$state" || fail "missing state contract: $contract"
done

for contract in \
	'detach_persistent_overlay() {' \
	'rog5-persistent-root-overlay-runtime-v1' \
	'unmount_mount /oldsys/state' \
	'unmount_mount /oldsys/userdata-rw' \
	'relock_storage'; do
	grep -Fq "$contract" "$shutdown" || fail "missing shutdown contract: $contract"
done

root_unmount=$(grep -n '^unmount_mount /oldroot ' "$shutdown" | cut -d: -f1)
overlay_detach=$(grep -n '^detach_persistent_overlay ||' "$shutdown" | cut -d: -f1)
overlay_unmount=$(grep -n '^[[:space:]]*unmount_mount /oldsys/state' "$shutdown" | head -n 1 | cut -d: -f1)
userdata_unmount=$(grep -n '^[[:space:]]*unmount_mount /oldsys/userdata-rw' "$shutdown" | tail -n 1 | cut -d: -f1)
[ "$root_unmount" -lt "$overlay_detach" ] || fail 'overlay detach precedes merged root unmount'
[ "$overlay_unmount" -lt "$userdata_unmount" ] || fail 'p23 unmount precedes overlay image unmount'

for contract in \
	'image_bytes=17179869184' \
	'image_uuid=f4834541-6e7a-4214-80d5-818fcc5cc252' \
	'image_label=ROG5_ROOT_RW_V1' \
	'relative_final=rog5/root/root-overlay-v1.ext4' \
	'format=rog5-persistent-root-overlay-v1' \
	'layout=upper,work' \
	'mkfs.ext4 -q -F -m 1' \
	'mkdir -m 0755 "$image_mount/upper"' \
	'timeout -k 5 180 e2fsck -fn' \
	'mv -T "$mountpoint/$relative_partial" "$mountpoint/$relative_final"'; do
	grep -Fq "$contract" "$stager" || fail "missing stager contract: $contract"
done

for path in "$init" "$state" "$shutdown" "$stager"; do
	! grep -Fq 'rm -rf' "$path" || fail "broad recursive removal in $path"
	! grep -Fq '/dev/sda23' "$path" || fail "literal target device in $path"
done

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
awk '
	/^verify_overlay_workdir_pre_mount\(\) \{/ { copy=1 }
	copy { print }
	copy && /^}/ { exit }
' "$init" >"$work/function.sh"
# shellcheck disable=SC1090
. "$work/function.sh"
stat() {
	if [ "$1:$2:$3" = "-c:%u:%g:%a:%h:$work/state/work/work" ]; then
		printf '0:0:%s:2\n' "$(command stat -c %a "$3")"
	else
		command stat "$@"
	fi
}
find() {
	if [ "$1" = "$work/state/work/work" ] && [ "$(command stat -c %a "$1")" = 0 ]; then
		return 0
	fi
	command find "$@"
}
mkdir -p "$work/state/work"
verify_overlay_workdir_pre_mount "$work/state"
mkdir -m 000 "$work/state/work/work"
verify_overlay_workdir_pre_mount "$work/state"
chmod 0700 "$work/state/work/work"
! verify_overlay_workdir_pre_mount "$work/state"
rmdir "$work/state/work/work"
touch "$work/state/work/hostile"
! verify_overlay_workdir_pre_mount "$work/state"

echo 'PASS persistent root overlay is exact-scope, shared-mount aware, and teardown ordered'
