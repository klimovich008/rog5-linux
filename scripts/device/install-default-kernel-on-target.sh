#!/bin/sh
# Install one signed bundle as the slot-B default (try-once primary plus the
# fallback named in the selector). With fallback_install=1 the same write
# window also installs a new fallback bundle (from $source_root/fallback) that
# the new selector names; otherwise the existing fallback must be unchanged.
#
# Runs as root on the booted ROG5 system, fed on stdin by
# scripts/host/install-default-kernel.py, which prepends the exact values
# below (every one validated there). Modes:
#   --inspect    read-only identity, power, scope and fallback checks
#   --preflight  also checks the payload transferred to $source_root (RAM)
#   --stage      one write window: new bundle directory and staged selector
#                on p24, a read-only remount proven before activation, the
#                new selector exchanged in atomically (the previous one keeps
#                its inode as selector.rollback-$bundle), p24 relocked, then
#                the previous try-once record on p23 archived so the next
#                boot starts the new trial.
# A 180 s relock timer and the EXIT trap put p24 back to read-only on any
# failure. Nothing is ever deleted; no boot is performed.
#
# Nothing on p24 is ever unlinked, not even by a rename over an existing
# name. / is an overlay whose lower layer is this same p24 superblock, and a
# cached overlay dentry (anything that once looked up /boot/rog5-linux/selector
# through /) holds its lower dentry: an inode replaced by rename stays alive
# as an orphan, and ext4 refuses every read-only remount (EBUSY) while an
# orphan is pending. That failed the r206 install on 2026-09-30 after the
# selector swap. RENAME_EXCHANGE (util-linux exch) keeps both inodes linked.
#
# If p24 cannot be relocked after the new selector is active, the exit trap
# finishes the install on p23 (archives the record, once the selector was
# durably written and it and both bundles re-verify) so the next boot is the
# new trial rather than an unintended fallback, and prints a STATE line
# saying what the next boot does.
#
# Values (prepended by the host):
#   boot_id bundle trial_id payload_{image,dtb,initramfs,manifest,signature}
#   selector_old_sha256 selector_old_size selector_new_sha256
#   record_old_sha256 (or "absent") record_archive
#   fallback_bundle fallback_install (0 keep, 1 install)
#   fallback_{image,dtb,initramfs,manifest,signature}
#   p24_uuid p23_uuid p24_size
#   root_mount userdata_mount source_root sys_block sys_power drop_caches
#   install_path (tests only; the host never sets it)
set -eu

PATH=${install_path:-/usr/sbin:/usr/bin:/sbin:/bin}
export PATH
[ "$#" -eq 1 ] || exit 2
case $1 in --inspect|--preflight|--stage) ;; *) exit 2 ;; esac
mode=$1
mutating=0
# 1 once the checked sync after activation succeeded (the new selector and
# rollback are on disk), and once the p23 archival completed with its sync.
p24_durable=0
record_durable=0

linux=$root_mount/boot/rog5-linux
bundle_target=$linux/bundles/$bundle
selector=$linux/selector
selector_next=$linux/.selector.next-$trial_id
selector_rollback=$linux/selector.rollback-$bundle
fallback_dir=$linux/bundles/$fallback_bundle
record=$userdata_mount/rog5/boot/wifi-trial-state
record_next=$userdata_mount/rog5/boot/.wifi-trial-state.next
guard=rog5-default-kernel-guard-$(printf '%s' "$trial_id" | cut -c1-16)

fail() { echo "FAIL default kernel install: $*" >&2; exit 1; }

writable() {
	result=
	for node in "$sys_block"/sd*; do
		[ -e "$node/ro" ] || continue
		# USB mass storage (a flash drive, a hub's card reader) is not on
		# the UFS and not part of the write scope.
		case $(readlink -f "$node") in */usb[0-9]*/*) continue ;; esac
		[ "$(cat "$node/ro")" = 1 ] || result="$result ${node##*/}"
	done
	printf '%s\n' "$result"
}

sha() { sha256sum "$1" | cut -d ' ' -f 1; }

# Read-only remount of p24 with retries. EBUSY means a writer or a pending
# orphan inode; an orphan pinned only by unused cached dentries (an overlay
# dentry of / holds its lower p24 dentry) is released by dropping the
# reclaimable dentry and inode caches.
remount_ro() {
	attempt=1
	until mount -o remount,ro "$root_mount"; do
		[ "$attempt" -lt 3 ] || return 1
		attempt=$((attempt + 1))
		sync
		echo 2 >"$drop_caches" || true
		sleep 1
	done
	case ,$(findmnt -n -o OPTIONS "$root_mount"), in *,ro,*) ;; *) return 1 ;; esac
}

payload_pairs() {
	printf '%s\n' "Image:$payload_image" "board.dtb:$payload_dtb" \
		"initramfs.cpio.gz:$payload_initramfs" "manifest:$payload_manifest" \
		"manifest.sig:$payload_signature"
}

# The active selector and the primary bundle re-verify on p24.
primary_verified() {
	[ -f "$selector" ] && [ ! -L "$selector" ] &&
		[ "$(sha "$selector")" = "$selector_new_sha256" ] || return 1
	for pair in $(payload_pairs); do
		[ "$(sha "$bundle_target/${pair%%:*}")" = "${pair#*:}" ] || return 1
	done
}

fallback_verified() {
	for pair in $fallback_pairs; do
		[ "$(sha "$fallback_dir/${pair%%:*}")" = "${pair#*:}" ] || return 1
	done
}

# Move the previous try-once record aside so the next boot starts the new
# trial. Only after the new selector is active and durable: with the old
# selector the old record still describes the current trial.
archive_record() {
	if [ "$record_old_sha256" != absent ]; then
		mv -T "$record" "$userdata_mount/rog5/boot/$record_archive" || fail 'previous record archival failed'
		[ "$(sha "$userdata_mount/rog5/boot/$record_archive")" = "$record_old_sha256" ] || fail 'archived record changed'
	fi
	[ ! -e "$record" ] && [ ! -L "$record" ] || fail 'active record remains'
	sync -f "$userdata_mount" || fail 'p23 sync failed'
	record_durable=1
}

# What the p23 record paths hold now.
record_now() {
	archive=$userdata_mount/rog5/boot/$record_archive
	if [ -e "$record" ] || [ -L "$record" ]; then
		[ "$record_old_sha256" != absent ] && [ ! -e "$archive" ] && [ ! -L "$archive" ] &&
			[ -f "$record" ] && [ ! -L "$record" ] &&
			[ "$(sha "$record")" = "$record_old_sha256" ] && echo previous || echo unknown
	elif [ "$record_old_sha256" = absent ]; then
		echo absent
	else
		[ -f "$archive" ] && [ ! -L "$archive" ] &&
			[ "$(sha "$archive")" = "$record_old_sha256" ] && echo archived || echo unknown
	fi
}

cleanup() {
	status=$?
	trap - EXIT HUP INT TERM
	set +e
	[ "$mutating" = 1 ] || exit "$status"
	sync
	remount_ro
	mount_status=$?
	blockdev --setro /dev/sda24
	lock_status=$?
	systemctl --job-mode=ignore-dependencies stop "$guard.timer" >/dev/null 2>&1
	p24_state=relocked
	if [ "$mount_status" -ne 0 ] || [ "$lock_status" -ne 0 ] ||
		[ "$(writable)" != "$scope" ]; then
		echo 'FAIL default kernel install: p24 cleanup/relock failed' >&2
		status=97
		p24_state=not-relocked
	fi
	# Leave a well-defined next boot and say which.
	case $(sha "$selector" 2>/dev/null) in
	"$selector_old_sha256") selector_state=previous ;;
	"$selector_new_sha256") selector_state=new ;;
	*) selector_state=unknown ;;
	esac
	record_state=$(record_now)
	if [ "$selector_state" = new ] && [ "$p24_durable" = 1 ] &&
		[ "$record_state" = previous ] && primary_verified && fallback_verified; then
		# The new selector is active and was durably written: finish on
		# p23 so the next boot is the intended trial, not a fallback. The
		# loader verifies the fallback before booting either bundle.
		(archive_record) && record_durable=1 &&
			echo 'default kernel install: new selector active; previous try-once record archived' >&2
		record_state=$(record_now)
	fi
	case $selector_state:$record_state in
	previous:previous|previous:absent) next_boot='unchanged (previous selector and record)' ;;
	new:archived|new:absent)
		if [ "$p24_durable" = 1 ] &&
			{ [ "$record_state" = absent ] || [ "$record_durable" = 1 ]; } &&
			primary_verified && fallback_verified; then
			next_boot="tries $bundle once, falls back to $fallback_bundle"
		else
			next_boot='undetermined (durability unproven): inspect the phone before rebooting'
		fi ;;
	new:previous)
		# The kept record does not match the new trial, so the loader
		# selects the fallback, which must itself verify.
		if [ "$p24_durable" = 1 ] && fallback_verified; then
			next_boot="$fallback_bundle (record does not match the new trial)"
		else
			next_boot='undetermined: inspect the phone before rebooting'
		fi ;;
	*) next_boot='undetermined: inspect the phone before rebooting' ;;
	esac
	echo "STATE selector=$selector_state record=$record_state p24=$p24_state p24_durable=$p24_durable next_boot=$next_boot" >&2
	[ "$status" -ne 0 ] || status=1
	exit "$status"
}
trap cleanup EXIT
trap 'exit 130' HUP INT TERM

case $fallback_install in 0|1) ;; *) fail 'fallback_install must be 0 or 1' ;; esac
[ "$fallback_bundle" != "$bundle" ] || fail 'primary and fallback are the same bundle'
[ "$(id -u)" = 0 ] || fail 'root required'
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$boot_id" ] || fail 'boot identity changed'
[ "$(findmnt -n -o SOURCE "$root_mount")" = /dev/sda24 ] || fail 'p24 source changed'
case ,$(findmnt -n -o OPTIONS "$root_mount"), in *,ro,*) ;; *) fail 'p24 is not read-only' ;; esac
[ "$(blockdev --getsize64 /dev/sda24)" = "$p24_size" ] || fail 'p24 size changed'
blkid /dev/sda24 | grep -Fq " UUID=\"$p24_uuid\"" || fail 'p24 UUID changed'
[ "$(findmnt -n -o SOURCE "$userdata_mount")" = /dev/sda23 ] || fail 'p23 source changed'
blkid /dev/sda23 | grep -Fq " UUID=\"$p23_uuid\"" || fail 'p23 UUID changed'
scope=$(writable)
case $scope in ' sda'|' sda sda23') ;; *) fail "write scope is$scope" ;; esac
[ "$(findmnt -n -o FSTYPE /run)" = tmpfs ] || fail 'transfer path is not RAM'
awk '/MemAvailable:/ { if ($2 >= 524288) ok = 1 } END { exit !ok }' /proc/meminfo || fail 'RAM headroom'
[ "$(systemctl show -p LoadState --value "$guard.timer")" = not-found ] || fail 'guard unit already exists'
command -v exch >/dev/null || fail 'exch (util-linux) is missing'
[ -f "$drop_caches" ] && [ -w "$drop_caches" ] || fail 'drop_caches is not writable'

[ -f "$selector" ] && [ ! -L "$selector" ] || fail 'selector missing'
[ "$(stat -c '%u:%g:%a:%s:%h' "$selector")" = "0:0:600:$selector_old_size:1" ] || fail 'selector metadata changed'
[ "$(sha "$selector")" = "$selector_old_sha256" ] || fail 'previous selector changed'
if [ "$record_old_sha256" = absent ]; then
	[ ! -e "$record" ] && [ ! -L "$record" ] || fail 'a try-once record appeared'
else
	[ -f "$record" ] && [ ! -L "$record" ] &&
		[ "$(stat -c '%u:%g:%a:%h' "$record")" = 0:0:600:1 ] || fail 'record metadata changed'
	[ "$(sha "$record")" = "$record_old_sha256" ] || fail 'previous record changed'
fi
for path in "$bundle_target" "$selector_next" "$selector_rollback" \
	"$userdata_mount/rog5/boot/$record_archive" "$record_next"; do
	[ ! -e "$path" ] && [ ! -L "$path" ] || fail "path exists: $path"
done
[ ! -e "$userdata_mount/rog5/state/good" ] && [ ! -e "$userdata_mount/rog5/state/next" ] ||
	fail 'unexpected userdata boot state'

[ "$(cat "$sys_power/qcom-battmgr-bat/health")" = Good ] || fail 'battery health unsafe'
[ "$(cat "$sys_power/qcom-battmgr-usb/online")" = 1 ] || fail 'USB power offline'
temperature=$(cat "$sys_power/qcom-battmgr-bat/temp")
case $temperature in ''|*[!0-9]*) fail 'battery temperature invalid' ;; esac
[ "$temperature" -lt 400 ] || fail 'battery temperature unsafe'
voltage=$(cat "$sys_power/qcom-battmgr-bat/voltage_now")
case $voltage in ''|*[!0-9]*) fail 'battery voltage invalid' ;; esac
# Dual cell: 7.4 V is 3.7 V per cell; a full pack rests near 8.4 V.
[ "$voltage" -ge 7400000 ] && [ "$voltage" -le 9000000 ] || fail 'battery voltage unsafe'
capacity=$(cat "$sys_power/qcom-battmgr-bat/capacity")
case $capacity in ''|*[!0-9]*) fail 'battery capacity invalid' ;; esac
[ "$capacity" -ge 30 ] || fail 'battery capacity below 30 %'

fallback_pairs="Image:$fallback_image board.dtb:$fallback_dtb initramfs.cpio.gz:$fallback_initramfs
	manifest:$fallback_manifest manifest.sig:$fallback_signature"
if [ "$fallback_install" = 1 ]; then
	[ ! -e "$fallback_dir" ] && [ ! -L "$fallback_dir" ] || fail "path exists: $fallback_dir"
else
	for pair in $fallback_pairs; do
		[ "$(sha "$fallback_dir/${pair%%:*}")" = "${pair#*:}" ] || fail "fallback ${pair%%:*} changed"
	done
fi
[ "$mode" != --inspect ] || { echo "PASS default kernel inspection scope=$scope"; exit 0; }

for pair in "Image:$payload_image" "board.dtb:$payload_dtb" \
	"initramfs.cpio.gz:$payload_initramfs" "manifest:$payload_manifest" \
	"manifest.sig:$payload_signature" "selector:$selector_new_sha256"; do
	[ "$(sha "$source_root/${pair%%:*}")" = "${pair#*:}" ] || fail "transferred ${pair%%:*} changed"
done
if [ "$fallback_install" = 1 ]; then
	for pair in $fallback_pairs; do
		[ "$(sha "$source_root/fallback/${pair%%:*}")" = "${pair#*:}" ] ||
			fail "transferred fallback ${pair%%:*} changed"
	done
fi
[ "$mode" != --preflight ] || { echo 'PASS default kernel payload preflight'; exit 0; }

mutating=1
systemd-run --quiet --unit="$guard" --on-active=180s --timer-property=AccuracySec=1s \
	/bin/sh -c "sync; mount -o remount,ro $root_mount || { echo 2 >$drop_caches; sleep 1; mount -o remount,ro $root_mount; }; blockdev --setro /dev/sda24; sync"
systemctl is-active --quiet "$guard.timer" || fail 'relock guard did not arm'
blockdev --setrw /dev/sda24 || fail 'p24 write window did not open'
case $scope in
	' sda') expected=' sda sda24' ;;
	*) expected=' sda sda23 sda24' ;;
esac
[ "$(writable)" = "$expected" ] || fail 'p24 write scope is not exact'
mount -o remount,rw "$root_mount" || fail 'p24 remount failed'
case ,$(findmnt -n -o OPTIONS "$root_mount"), in *,rw,*) ;; *) fail 'p24 is not rw' ;; esac

mkdir -m 0700 "$bundle_target" || fail 'cannot create bundle directory'
for name in Image board.dtb initramfs.cpio.gz manifest manifest.sig; do
	install -o root -g root -m 0400 "$source_root/$name" "$bundle_target/$name" || fail "cannot install $name"
	cmp "$source_root/$name" "$bundle_target/$name" || fail "installed $name changed"
done
[ "$(find "$bundle_target" -mindepth 1 -maxdepth 1 | wc -l)" -eq 5 ] || fail 'bundle inventory changed'
if [ "$fallback_install" = 1 ]; then
	mkdir -m 0700 "$fallback_dir" || fail 'cannot create fallback directory'
	for name in Image board.dtb initramfs.cpio.gz manifest manifest.sig; do
		install -o root -g root -m 0400 "$source_root/fallback/$name" "$fallback_dir/$name" ||
			fail "cannot install fallback $name"
		cmp "$source_root/fallback/$name" "$fallback_dir/$name" || fail "installed fallback $name changed"
	done
	[ "$(find "$fallback_dir" -mindepth 1 -maxdepth 1 | wc -l)" -eq 5 ] || fail 'fallback inventory changed'
fi
install -o root -g root -m 0600 "$source_root/selector" "$selector_next" || fail 'cannot stage selector'
[ "$(sha "$selector_next")" = "$selector_new_sha256" ] || fail 'staged selector changed'
sync -f "$root_mount" || fail 'p24 sync failed'
# Prove that p24 can go read-only again before anything is activated: a
# writer or pending orphan found here leaves the previous selector in charge.
remount_ro || fail 'p24 read-only remount failed before activation; previous selector kept'
mount -o remount,rw "$root_mount" || fail 'p24 remount failed'
case ,$(findmnt -n -o OPTIONS "$root_mount"), in *,rw,*) ;; *) fail 'p24 is not rw' ;; esac
[ "$(sha "$selector")" = "$selector_old_sha256" ] || fail 'previous selector changed'
# Atomic swap without an unlink: the previous selector inode becomes the
# staged name and is then renamed (to a name proven absent) as the rollback.
exch "$selector_next" "$selector" || fail 'selector activation failed'
[ "$(sha "$selector")" = "$selector_new_sha256" ] || fail 'active selector changed'
[ ! -e "$selector_rollback" ] && [ ! -L "$selector_rollback" ] || fail "path exists: $selector_rollback"
mv -T "$selector_next" "$selector_rollback" || fail 'cannot preserve previous selector'
[ "$(sha "$selector_rollback")" = "$selector_old_sha256" ] || fail 'rollback selector changed'
[ "$(stat -c '%u:%g:%a:%h' "$selector_rollback")" = 0:0:600:1 ] || fail 'rollback selector metadata changed'
sync -f "$root_mount" || fail 'p24 sync failed'
p24_durable=1
remount_ro || fail 'p24 read-only remount failed'
blockdev --setro /dev/sda24 || fail 'p24 relock failed'
case ,$(findmnt -n -o OPTIONS "$root_mount"), in *,ro,*) ;; *) fail 'p24 mount remained writable' ;; esac
[ "$(writable)" = "$scope" ] || fail 'post-p24 write scope changed'
archive_record
systemctl --job-mode=ignore-dependencies stop "$guard.timer" >/dev/null 2>&1 || true
mutating=0

[ "$fallback_install" = 1 ] && fallback_state=installed || fallback_state=preserved
echo "PASS default kernel $bundle installed; fallback $fallback_bundle $fallback_state; p24 relocked; no boot performed"
