#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

case ${1:-} in
	preflight|stage) mode=$1 ;;
	*) fail 'usage: stage-local-arch-image.sh preflight|stage ARCHIVE BSDTAR_RUNTIME ROOT_TOOL' ;;
esac
[ "$#" -eq 4 ] ||
	fail 'usage: stage-local-arch-image.sh preflight|stage ARCHIVE BSDTAR_RUNTIME ROOT_TOOL'
archive=$2
bsdtar_runtime=$3
root_tool=$4

expected_archive_size=536746495
expected_archive_sha256=4d120a4b3a10be098cea47ba8536969bbaa931b47b31cc37fc3474fea045b324
expected_bsdtar_sha256=a119cde57ed38a306bcb235cd275646723e6c84fa1923c77027b23dd1c8c2ca0
expected_bsdtar_loader_sha256=32377e6d71725bb019e9ff6d5e9f16b4d5156d6f2c36504191c2d6a7c4d4a44d
expected_root_tool_sha256=0b2a3a9a8ad330dd427427ac8deb79ca18cb2f8575d46cdc9b354594dce27057
expected_source_seal_sha256=42ef8388bb771fbd0dd8141939b042a89037ea1cf1bec9288f7a3ae51455210a
expected_source_tree_sha256=f4affd6d83f3af48259c7d7f650e91461465b59e045519310ac81bb5d71a0087
expected_local_seal_sha256=02231e86746fbc656090f52c96d7e0c968c7ca86ba7449c306f611ea20c6a876
expected_local_tree_sha256=4701c23b93624bf894bb76331c165b650c9a2aecb99273a4e6d37c20ac3ef167
expected_authorized_key_sha256=04f39d5949c813450e201b7e579256b1afcd5c7fcea077d36ae445aa53519b61
expected_systemd_sha256=dad2b1339d6b9178f83ef96791e5c020604e16ec7921e6eaf89d3b38eec478d0
expected_sshd_sha256=6a88a601266f5775291e394106e97fa0c1c38ac10a1715c56156cda7e8812932
expected_ssh_policy_sha256=c6b01ef801333ee11bb8805a250df2c4f02f38f0015df1449dadb66490e43693
image_bytes=17179869184
image_uuid=598a876b-a8db-4859-a01a-1b864b0a87f4
image_label=ROG5_ARCH_A
userdata_root=${ROG5_USERDATA_ROOT:-/}
case $userdata_root in /|/mnt/userdata) ;; *) fail 'userdata root is not fixed' ;; esac
store=$userdata_root/rog5/images
partial=$store/arch-local-a.ext4.partial
final=$store/arch-local-a.ext4
mountpoint=/run/rog5-local-arch-image

[ "$(id -u)" -eq 0 ] || fail 'local-image staging requires root'
for command in awk basename blkid blockdev cat chmod chown df e2fsck \
	fallocate find flock grep id losetup mkdir mkfs.ext4 mount mv python3 \
	readlink rmdir sed sha256sum stat sync touch umount wc; do
	command -v "$command" >/dev/null ||
		fail "missing local-image staging command: $command"
done
for path in "$archive" "$root_tool"; do
	case $path in /run/*) ;; *) fail 'staging inputs must be volatile /run files' ;; esac
	[ -f "$path" ] && [ ! -L "$path" ] ||
		fail "unsafe staging input: $path"
	[ "$(stat -c '%u:%h' "$path")" = 0:1 ] ||
		fail "staging input owner or link count changed: $path"
done
case $bsdtar_runtime in /run/*) ;; *) fail 'bsdtar runtime must be volatile' ;; esac
[ -d "$bsdtar_runtime" ] && [ ! -L "$bsdtar_runtime" ] &&
	[ "$(stat -c '%u:%g:%a:%h' "$bsdtar_runtime")" = 0:0:755:4 ] ||
	fail 'unsafe bsdtar runtime directory'
[ "$(stat -c '%u:%g:%a:%h' "$bsdtar_runtime/bin")" = 0:0:755:2 ] &&
	[ "$(stat -c '%u:%g:%a:%h' "$bsdtar_runtime/lib")" = 0:0:755:2 ] ||
	fail 'unsafe bsdtar runtime subdirectory'
[ "$(find "$bsdtar_runtime" -mindepth 1 | wc -l)" -eq 20 ] ||
	fail 'bsdtar runtime inventory changed'
bsdtar=$bsdtar_runtime/bin/bsdtar
bsdtar_loader=$bsdtar_runtime/lib/ld-musl-aarch64.so.1
for path in "$bsdtar" "$bsdtar_loader"; do
	[ -f "$path" ] && [ ! -L "$path" ] && [ -x "$path" ] &&
		[ "$(stat -c '%u:%h' "$path")" = 0:1 ] ||
		fail "unsafe bsdtar runtime executable: $path"
done
for link in \
	'libacl.so.1 libacl.so.1.1.2302' \
	'libbz2.so.1 libbz2.so.1.0.8' \
	'libc.musl-aarch64.so.1 ld-musl-aarch64.so.1' \
	'libexpat.so.1 libexpat.so.1.12.2' \
	'liblz4.so.1 liblz4.so.1.10.0' \
	'liblzma.so.5 liblzma.so.5.8.3' \
	'libz.so.1 libz.so.1.3.2' \
	'libzstd.so.1 libzstd.so.1.5.7'; do
	set -- $link
	path=$bsdtar_runtime/lib/$1
	[ -L "$path" ] && [ "$(readlink "$path")" = "$2" ] ||
		fail "bsdtar runtime link changed: $1"
done
[ "$(sha256sum "$bsdtar_loader" | awk '{ print $1 }')" = \
	"$expected_bsdtar_loader_sha256" ] || fail 'bsdtar loader hash changed'
for library in \
	'libacl.so.1.1.2302 d9f3a4f69bc2a45a6f97f570920b044e80f84612bdc57aa39301c4d7198f7fe7' \
	'libbz2.so.1.0.8 101e3342e60a5dd834389a025f7c6dc6d45fa5e9dba1e3a81cd750571da2fb12' \
	'libcrypto.so.3 ae1d370e3146642824c6ee4bde0fdf83b9e8174a9d28d093362afde5cc4b3e6c' \
	'libexpat.so.1.12.2 27ea21f9e2672f2b5589f0c71baa9f7ffc2e4bbd2461231c946e3c4c8f344b3c' \
	'liblz4.so.1.10.0 729ca3feae715dca6947674fa1f5451b4f36bbc54aa8a4471bf5c66096aeb41c' \
	'liblzma.so.5.8.3 a30eb437c4fb1fc99a14d8038ee5db824121e14579abff329831a9a1be0f5f37' \
	'libz.so.1.3.2 d3b940580ded8f736804c78df7302b9e7a3f27900ac25a5c97bb05f50992f567' \
	'libzstd.so.1.5.7 baeb93cf3904f55809f9229c7b0e9348bfe07b80d319a477df9ac63657a9fa55'; do
	set -- $library
	path=$bsdtar_runtime/lib/$1
	[ -f "$path" ] && [ ! -L "$path" ] && [ -x "$path" ] &&
		[ "$(stat -c '%u:%h' "$path")" = 0:1 ] ||
		fail "unsafe bsdtar runtime library: $1"
	[ "$(sha256sum "$path" | awk '{ print $1 }')" = "$2" ] ||
		fail "bsdtar runtime library hash changed: $1"
done
[ -x "$root_tool" ] || fail 'root verifier is not executable'
[ "$(stat -c %s "$archive")" -eq "$expected_archive_size" ] ||
	fail 'headless Arch archive size changed'
[ "$(sha256sum "$archive" | awk '{ print $1 }')" = \
	"$expected_archive_sha256" ] || fail 'headless Arch archive hash changed'
[ "$(sha256sum "$bsdtar" | awk '{ print $1 }')" = \
	"$expected_bsdtar_sha256" ] || fail 'bsdtar hash changed'
[ "$(sha256sum "$root_tool" | awk '{ print $1 }')" = \
	"$expected_root_tool_sha256" ] || fail 'root verifier hash changed'
run_bsdtar() {
	"$bsdtar_loader" --library-path "$bsdtar_runtime/lib" "$bsdtar" "$@"
}
run_bsdtar --version | grep -Fq 'bsdtar 3.8.7' ||
	fail 'bsdtar version changed'
python3 -m py_compile "$root_tool" || fail 'root verifier is not valid Python'

resolve_userdata_root() {
	userdata_count=0
	exact_count=0
	userdata_device=
	for sys_disk in /sys/class/block/*; do
		[ -e "$sys_disk/device" ] || continue
		[ ! -e "$sys_disk/partition" ] || continue
		disk=$(basename "$sys_disk")
		case $disk in sd[a-z]) ;; *) continue ;; esac
		for sys_block in "$sys_disk"/"$disk"*; do
			[ -e "$sys_block/partition" ] || continue
			partition_name=$(sed -n 's/^PARTNAME=//p' \
				"$sys_block/uevent" | sed -n '1p')
			[ "$partition_name" = userdata ] || continue
			userdata_count=$((userdata_count + 1))
			name=$(basename "$sys_block")
			[ "$name" = "${disk}23" ] || continue
			[ "$(cat "$sys_disk/size")" = 494927872 ] || continue
			[ "$(cat "$sys_disk/queue/logical_block_size")" = 4096 ] ||
				continue
			[ "$(cat "$sys_block/partition")" = 23 ] || continue
			[ "$(cat "$sys_block/start")" = 18821440 ] || continue
			[ "$(cat "$sys_block/size")" = 476106392 ] || continue
			[ "$(sed -n 's/^DEVNAME=//p' "$sys_block/uevent")" = \
				"$name" ] || continue
			exact_count=$((exact_count + 1))
			userdata_device=/dev/$name
		done
	done
	[ "$userdata_count" -eq 1 ] && [ "$exact_count" -eq 1 ] || return 1
	[ -b "$userdata_device" ] || return 1

	root_record=$(awk -v target="$userdata_root" \
		'$2 == target { count++; source=$1; type=$3; options=$4 }
		END { if (count != 1) exit 1; print source, type, options }' \
		/proc/mounts) || return 1
	set -- $root_record
	[ "$#" -eq 3 ] && [ "$1" = "$userdata_device" ] &&
		[ "$2" = ext4 ] || return 1
	case ,$3, in *,rw,*) ;; *) return 1 ;; esac
	awk -v expected="$userdata_device" -v target="$userdata_root" \
	'$1 ~ "^/dev/sd" {
		if ($1 != expected || $2 != target) exit 1
		count++
	} END { exit count != 1 }' /proc/mounts || return 1
	return 0
}

resolve_userdata_root || fail 'exact writable fallback userdata root is absent'
[ -f /.rog5-linux-root ] && [ ! -L /.rog5-linux-root ] ||
	fail 'known-good Alpine fallback marker is absent'
[ -d "$userdata_root/rog5" ] && [ ! -L "$userdata_root/rog5" ] ||
	fail 'persistent store is unsafe'
if [ -e "$store" ] || [ -L "$store" ]; then
	[ -d "$store" ] && [ ! -L "$store" ] ||
		fail 'local-image store is unsafe'
fi
[ ! -e "$partial" ] && [ ! -L "$partial" ] ||
	fail 'partial local image already exists; preserve and inspect it'
[ ! -e "$final" ] && [ ! -L "$final" ] ||
	fail 'published local image already exists; refusing overwrite'
free_kib=$(df -Pk "$userdata_root" | awk 'NR == 2 { print $4 }')
case $free_kib in ''|*[!0-9]*) fail 'fallback free space is invalid' ;; esac
[ "$free_kib" -ge 18874368 ] || fail 'less than 18 GiB is free on userdata'

if [ "$mode" = preflight ]; then
	echo 'PASS local headless Arch image preflight; no phone-storage write occurred'
	exit 0
fi
[ "${ALLOW_ROG5_LOCAL_IMAGE_STAGE:-}" = 1 ] ||
	fail 'local-image staging is unarmed'

exec 9>/run/rog5-local-image-stage.lock
flock -n 9 || fail 'another local-image staging operation holds the lock'
mkdir -m 0700 "$store"
set -C
: >"$partial"
set +C
chmod 0600 "$partial"
[ "$(stat -c '%u:%g:%a:%h' "$partial")" = 0:0:600:1 ] ||
	fail 'new local image metadata is unsafe'
fallocate -l "$image_bytes" "$partial"
[ "$(stat -c %s "$partial")" -eq "$image_bytes" ] ||
	fail 'local image allocation size changed'
mkfs.ext4 -q -F -m 1 -L "$image_label" -U "$image_uuid" \
	-E hash_seed="$image_uuid",lazy_itable_init=0,lazy_journal_init=0 "$partial"

loop_device=
mounted=0
cleanup() {
	status=$?
	trap - EXIT HUP INT TERM
	if [ "$mounted" -eq 1 ]; then
		umount "$mountpoint" || status=1
	fi
	if [ -n "$loop_device" ]; then
		losetup -d "$loop_device" || status=1
	fi
	rmdir "$mountpoint" 2>/dev/null || true
	exit "$status"
}
trap cleanup EXIT HUP INT TERM

loop_device=$(losetup -f)
case $loop_device in /dev/loop[0-9]*) ;; *) fail 'unsafe loop-device result' ;; esac
losetup "$loop_device" "$partial"
[ "$(blockdev --getsize64 "$loop_device")" -eq "$image_bytes" ] ||
	fail 'loop-device size changed'
loop_name=${loop_device##*/}
backing_file=$(cat "/sys/class/block/$loop_name/loop/backing_file") ||
	fail 'loop-device backing file is unreadable'
case $backing_file in
	/rog5/images/arch-local-a.ext4.partial|\
	rog5/images/arch-local-a.ext4.partial|\
	/mnt/userdata/rog5/images/arch-local-a.ext4.partial|\
	mnt/userdata/rog5/images/arch-local-a.ext4.partial) ;;
	*) fail 'loop-device backing file changed' ;;
esac
mkdir -m 0700 "$mountpoint"
mount -t ext4 -o rw,nodev,nosuid,noatime "$loop_device" "$mountpoint"
mounted=1
awk -v device="$loop_device" -v target="$mountpoint" '
	$1 == device && $2 == target && $3 == "ext4" &&
	$4 ~ /(^|,)rw(,|$)/ && $4 ~ /(^|,)nodev(,|$)/ &&
	$4 ~ /(^|,)nosuid(,|$)/ { count++ }
	END { exit count != 1 }' /proc/mounts ||
	fail 'local image mount identity changed'
[ -d "$mountpoint/lost+found" ] && [ ! -L "$mountpoint/lost+found" ] &&
	[ -z "$(find "$mountpoint/lost+found" -mindepth 1 -print -quit)" ] ||
	fail 'new ext4 lost+found is not one empty real directory'
rmdir "$mountpoint/lost+found"

run_bsdtar --numeric-owner --same-permissions --safe-writes \
	--acls --xattrs --fflags --strip-components 1 \
	-xpf "$archive" -C "$mountpoint"
[ "$(stat -c '%u:%g:%a:%s:%h' \
	"$mountpoint/.rog5-persistent-seal")" = 0:0:444:430:1 ] ||
	fail 'headless source seal metadata changed'
[ "$(sha256sum "$mountpoint/.rog5-persistent-seal" | awk '{ print $1 }')" = \
	"$expected_source_seal_sha256" ] || fail 'headless source seal hash changed'
grep -Fqx "tree_sha256=$expected_source_tree_sha256" \
	"$mountpoint/.rog5-persistent-seal" || fail 'headless tree identity changed'
[ -L "$mountpoint/sbin/init" ] &&
	[ "$(readlink "$mountpoint/sbin/init")" = ../lib/systemd/systemd ] ||
	fail 'headless init link changed'
[ "$(sha256sum "$mountpoint/usr/lib/systemd/systemd" | awk '{ print $1 }')" = \
	"$expected_systemd_sha256" ] || fail 'headless systemd changed'
[ "$(sha256sum "$mountpoint/usr/bin/sshd" | awk '{ print $1 }')" = \
	"$expected_sshd_sha256" ] || fail 'headless sshd changed'
[ "$(sha256sum "$mountpoint/root/.ssh/authorized_keys" | awk '{ print $1 }')" = \
	"$expected_authorized_key_sha256" ] || fail 'deployment SSH key changed'
[ "$(sha256sum "$mountpoint/etc/ssh/sshd_config.d/10-rog5-server.conf" |
	awk '{ print $1 }')" = "$expected_ssh_policy_sha256" ] ||
	fail 'headless SSH policy changed'
[ ! -s "$mountpoint/etc/machine-id" ] || fail 'headless machine ID is reusable'
[ -z "$(find "$mountpoint/etc/ssh" -maxdepth 1 -type f \
	-name 'ssh_host_*_key' -print -quit)" ] || fail 'headless host key is reusable'
[ -L "$mountpoint/etc/systemd/system/multi-user.target.wants/sshd.service" ] &&
	[ "$(readlink "$mountpoint/etc/systemd/system/multi-user.target.wants/sshd.service")" = \
	/usr/lib/systemd/system/sshd.service ] || fail 'sshd is not enabled'

[ ! -e "$mountpoint/.rog5-source-seal" ] ||
	fail 'local-image source seal path already exists'
mv "$mountpoint/.rog5-persistent-seal" "$mountpoint/.rog5-source-seal"
: >"$mountpoint/.rog5-persistent-seal"
chown 0:0 "$mountpoint" "$mountpoint/.rog5-persistent-seal"
chmod 0755 "$mountpoint"
touch -d @1681862400 "$mountpoint"
tree_report=$("$root_tool" seal "$mountpoint") ||
	fail 'ext4 local-root sealing failed'
for field in \
	'tree_entries=37736' \
	'tree_regular_files=27604' \
	'tree_directories=1902' \
	'tree_symlinks=8230' \
	'tree_bytes=1625282905' \
	'tree_xattrs=3' \
	"tree_sha256=$expected_local_tree_sha256"; do
	printf '%s\n' "$tree_report" | grep -Fqx "$field" ||
		fail "ext4 local-root seal changed: $field"
done
{
	printf '%s\n' \
		'seal_format=rog5-persistent-root-v1' \
		'generation=arch-a' \
		"source_archive_size=$expected_archive_size" \
		"source_archive_sha256=$expected_archive_sha256" \
		'promotion_state=UNBOOTED'
	printf '%s\n' "$tree_report"
} >"$mountpoint/.rog5-persistent-seal"
chmod 0444 "$mountpoint/.rog5-persistent-seal"
[ "$(stat -c '%u:%g:%a:%s:%h' \
	"$mountpoint/.rog5-persistent-seal")" = 0:0:444:430:1 ] ||
	fail 'ext4 local-root seal metadata changed'
[ "$(sha256sum "$mountpoint/.rog5-persistent-seal" | awk '{ print $1 }')" = \
	"$expected_local_seal_sha256" ] || fail 'ext4 local-root seal hash changed'
[ "$(sha256sum "$mountpoint/.rog5-source-seal" | awk '{ print $1 }')" = \
	"$expected_source_seal_sha256" ] || fail 'retained source seal changed'
"$root_tool" verify "$mountpoint" \
	"$mountpoint/.rog5-persistent-seal" >/dev/null
[ "$(stat -c %s "$archive")" -eq "$expected_archive_size" ] &&
	[ "$(sha256sum "$archive" | awk '{ print $1 }')" = \
	"$expected_archive_sha256" ] || fail 'source archive changed during staging'

sync -f "$mountpoint"
umount "$mountpoint"
mounted=0
losetup -d "$loop_device"
loop_device=
rmdir "$mountpoint"
e2fsck -fn "$partial" >/dev/null
blkid_record=$(blkid "$partial") || fail 'local image identity is absent'
printf '%s\n' "$blkid_record" | grep -Fq ' TYPE="ext4"' ||
	fail 'local image filesystem type changed'
printf '%s\n' "$blkid_record" | grep -Fq " LABEL=\"$image_label\"" ||
	fail 'local image label changed'
printf '%s\n' "$blkid_record" | grep -Fq " UUID=\"$image_uuid\"" ||
	fail 'local image UUID changed'
image_sha256=$(sha256sum "$partial" | awk '{ print $1 }')
sync -f "$partial"
[ ! -e "$final" ] || fail 'published image appeared before atomic rename'
mv -T -- "$partial" "$final"
sync -f "$store"
trap - EXIT HUP INT TERM

printf '%s\n' \
	'format=rog5-local-arch-image-v1' \
	"path=$final" \
	"bytes=$image_bytes" \
	"filesystem_uuid=$image_uuid" \
	"filesystem_label=$image_label" \
	"root_tree_sha256=$expected_local_tree_sha256" \
	"root_seal_sha256=$expected_local_seal_sha256" \
	"image_sha256=$image_sha256" \
	'result=PASS'
