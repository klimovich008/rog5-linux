#!/bin/sh
# Offline test of rog5-usb-storage with a fake sysfs, mountinfo, blkid,
# e2fsck, mount and umount.
set -eu
here=$(CDPATH='' cd -- "$(dirname "$0")" && pwd)
s=$here/rog5-usb-storage
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
b=$t/bin; mkdir -p $b $t/sys/class/block $t/dev $t/root/run
export ROG5_USB_STORAGE_CONF=$t/conf ROG5_USB_STORAGE_SYS=$t/sys ROG5_USB_STORAGE_DEV=$t/dev \
	ROG5_USB_STORAGE_ROOT=$t/root ROG5_USB_STORAGE_P2=$t/p2 ROG5_USB_STORAGE_PSTATE=$t/pstate ROG5_USB_STORAGE_BOOT_ID=$t/boot_id \
	ROG5_USB_STORAGE_MOUNTINFO=$t/mountinfo ROG5_USB_STORAGE_STATE=$t/state ROG5_USB_STORAGE_KMSG=/dev/null \
	ROG5_USB_STORAGE_OWNER="$(id -u):$(id -g)" ROG5_USB_STORAGE_FAKE_DEV=1 PATH=$b:$PATH
fail() { echo "FAIL $*"; exit 1; }

# Block devices: sdb1 on a USB bus (the bottom-port drive), sda23 on the UFS.
usbdev=$t/sys/devices/platform/soc/a800000.usb/xhci-hcd.1/usb2/2-1/2-1:1.0/host0/target0:0:0/0:0:0:0/block/sdb/sdb1
ufsdev=$t/sys/devices/platform/soc/1d84000.ufshc/host0/target0:0:0/0:0:0:0/block/sda/sda23
mkdir -p $usbdev $ufsdev
echo 8:17 >$usbdev/dev; echo 8:23 >$ufsdev/dev
ln -s $usbdev $t/sys/class/block/sdb1; ln -s $ufsdev $t/sys/class/block/sda23
echo 11111111-2222-3333-4444-555555555555 >$t/boot_id
printf 'format=x\nstatus=PASS\nattested_boot_id=11111111-2222-3333-4444-555555555555\n' >$t/p2
printf 'format=rog5-persistent-service-state-runtime-v1\nboot_id=11111111-2222-3333-4444-555555555555\n' >$t/pstate
echo '22 1 0:21 / /run rw,nosuid shared:5 - tmpfs tmpfs rw' >$t/mountinfo

cat >$b/blkid <<EOF
#!/bin/sh
cat $t/blkid.\$(basename "\$4")
EOF
printf 'UUID=0b5e-ext4\nLABEL=ROG5-USB\nTYPE=ext4\n' >$t/blkid.sdb1
printf 'UUID=ufs\nLABEL=ROG5-USB\nTYPE=ext4\n' >$t/blkid.sda23
cat >$b/e2fsck <<EOF
#!/bin/sh
echo "\$*" >>$t/fsck
exit \$(cat $t/fsck-rc 2>/dev/null || echo 0)
EOF
cat >$b/mount <<EOF
#!/bin/sh
# mount -t TYPE -o OPTS DEV TARGET
echo "\$*" >>$t/mounts
echo "36 22 8:17 / \$6 rw,\$4 shared:9 - \$2 \$5 rw" >>$t/mountinfo
EOF
cat >$b/systemctl <<EOF
#!/bin/sh
echo "\$*" >>$t/systemctl
EOF
cat >$b/umount <<EOF
#!/bin/sh
[ ! -e $t/busy ] || { echo "umount: target is busy" >&2; exit 32; }
echo "\$*" >>$t/umounts
t=\$1; [ "\$1" != -l ] || t=\$2
grep -v " \$t " $t/mountinfo >$t/mi.new || true; mv $t/mi.new $t/mountinfo
EOF
chmod +x $b/*
mp=$t/root/run/media/phone/ROG5-USB
mounted() { grep -q " $mp " $t/mountinfo; }

# Config validation.
cat >$t/conf <<'EOF'
# comment
LABEL=ROG5-USB /run/media/phone/ROG5-USB
UUID=bad /etc/evil
UUID=srv /srv/data
UUID=dots /run/media/../../etc
UUID=opts /run/media/x rw;rm
UUID=0b5e-vfat /run/media/data uid=1000,gid=1000
EOF
[ "$("$s" status 2>/dev/null)" = "LABEL=ROG5-USB /run/media/phone/ROG5-USB: not mounted
UUID=0b5e-vfat /run/media/data: not mounted" ] || fail "status/config validation: $("$s" status 2>&1)"

# udev-match: properties only for a configured filesystem.
[ "$(ID_FS_LABEL=ROG5-USB ID_FS_UUID=x "$s" udev-match)" = "ROG5_USB_STORAGE=1
UDISKS_AUTO=0" ] || fail 'udev-match by label'
[ "$(ID_FS_UUID=0b5e-vfat "$s" udev-match)" = "ROG5_USB_STORAGE=1
UDISKS_AUTO=0" ] || fail 'udev-match by uuid'
[ -z "$(ID_FS_LABEL=OTHER ID_FS_UUID=y "$s" udev-match)" ] || fail 'udev-match other disk'
[ -z "$("$s" udev-match)" ] || fail 'udev-match without properties'

# Never before the boot gate, never the UFS.
mv $t/p2 $t/p2.saved
"$s" mount sdb1 2>/dev/null && fail 'mounted without the P2 gate record'
printf 'status=PASS\nattested_boot_id=00000000-0000-0000-0000-000000000000\n' >$t/p2
"$s" mount sdb1 2>/dev/null && fail 'mounted with a gate record of another boot'
printf 'status=FAIL\nattested_boot_id=11111111-2222-3333-4444-555555555555\n' >$t/p2
"$s" mount sdb1 2>/dev/null && fail 'mounted with a failed gate'
mv $t/p2.saved $t/p2
mv $t/pstate $t/pstate.saved
"$s" mount sdb1 2>/dev/null && fail 'mounted without the persistent-state record'
printf 'boot_id=00000000-0000-0000-0000-000000000000\n' >$t/pstate
"$s" mount sdb1 2>/dev/null && fail 'mounted with a persistent-state record of another boot'
mv $t/pstate.saved $t/pstate
"$s" mount sda23 2>/dev/null && fail 'mounted a UFS partition'
"$s" mount 'sdb1/../x' 2>/dev/null && fail 'accepted a bad device name'
[ ! -e $t/mounts ] || fail "mount ran: $(cat $t/mounts)"
[ ! -e $mp ] || fail 'created the mountpoint without mounting'

# Mount: parents created, mountpoint root-owned 0755, e2fsck first.
"$s" mount sdb1 2>/dev/null || fail 'mount sdb1'
mounted || fail 'not in mountinfo'
[ "$(cat $t/mounts)" = "-t ext4 -o nosuid,nodev,noatime $t/dev/sdb1 $mp" ] || fail "mount args: $(cat $t/mounts)"
[ "$(cat $t/fsck)" = "-p $t/dev/sdb1" ] || fail 'e2fsck -p not run'
[ "$(stat -c %a $mp)" = 755 ] || fail "mountpoint mode $(stat -c %a $mp)"
"$s" status 2>/dev/null | grep -q 'ROG5-USB: mounted' || fail 'status mounted'
# Again (udev change event, restart): no second mount.
"$s" mount sdb1 2>/dev/null || fail 'second mount call'
[ "$(wc -l <$t/mounts)" = 1 ] || fail 'mounted twice'

# rescan: starts the unit for configured attached filesystems only.
"$s" rescan >/dev/null 2>&1 || fail 'rescan'
[ "$(cat $t/systemctl)" = 'start rog5-usb-storage@sdb1.service' ] || fail "rescan: $(cat $t/systemctl)"

# Stop while busy: fails and stays mounted; then a clean unmount removes the
# mountpoint below /run/media.
: >$t/busy
"$s" umount sdb1 2>/dev/null && fail 'busy unmount reported success'
mounted || fail 'busy filesystem was detached'
rm $t/busy
"$s" umount sdb1 2>/dev/null || fail 'umount sdb1'
mounted && fail 'still mounted'
[ ! -e $mp ] || fail 'mountpoint left behind'
[ -d $t/root/run/media/phone ] || fail 'parent removed'
"$s" umount sdb1 2>/dev/null || fail 'second umount'

# Absent disk: a non-empty mountpoint (someone wrote there) is not hidden.
mkdir -p $mp; : >$mp/stray
"$s" mount sdb1 2>/dev/null && fail 'mounted over files'
rm $mp/stray
# A mountpoint left with the user's ownership is made root-owned again.
chmod 0777 $mp
"$s" mount sdb1 2>/dev/null || fail 'mount on existing empty dir'
[ "$(stat -c %a $mp)" = 755 ] || fail 'mountpoint not reset to 0755'

# Record cannot be written: no mount, nothing left behind.
"$s" umount sdb1 2>/dev/null || fail 'umount before record test'
mv $t/state $t/state.saved; : >$t/state
n=$(wc -l <$t/mounts)
"$s" mount sdb1 2>/dev/null && fail 'mounted without a record'
[ "$(wc -l <$t/mounts)" = "$n" ] || fail 'mount ran without a record'
rm $t/state; mv $t/state.saved $t/state
"$s" mount sdb1 2>/dev/null || fail 'mount after the record test'

# Removed while mounted: lazy detach, record and mountpoint gone.
rm $t/sys/class/block/sdb1
"$s" umount sdb1 2>/dev/null || fail 'umount after removal'
mounted && fail 'still mounted after removal'
[ ! -e $t/state/sdb1 ] || fail 'state record left'
ln -s $usbdev $t/sys/class/block/sdb1

# e2fsck that cannot repair unattended: not mounted.
echo 4 >$t/fsck-rc
"$s" mount sdb1 2>/dev/null && fail 'mounted after e2fsck exit 4'
mounted && fail 'mounted despite e2fsck'
echo 1 >$t/fsck-rc
"$s" mount sdb1 2>/dev/null || fail 'e2fsck exit 1 (repaired) must mount'
"$s" umount sdb1 2>/dev/null; rm $t/fsck-rc

# Already mounted elsewhere (the desktop won a race): left alone.
echo "40 22 8:17 / /run/media/phone/other rw shared:9 - ext4 /dev/sdb1 rw" >>$t/mountinfo
n=$(wc -l <$t/mounts)
"$s" mount sdb1 2>/dev/null || fail 'already mounted elsewhere'
[ "$(wc -l <$t/mounts)" = "$n" ] || fail 'mounted a second time'
[ ! -e $t/state/sdb1 ] || fail 'claimed a mount it did not make'
grep -v ' /run/media/phone/other ' $t/mountinfo >$t/mi; mv $t/mi $t/mountinfo

# An unconfigured disk: nothing happens, success.
printf 'UUID=abcd\nLABEL=OTHER\nTYPE=exfat\n' >$t/blkid.sdb1
"$s" mount sdb1 2>/dev/null || fail 'unconfigured disk'
[ "$(wc -l <$t/mounts)" = "$n" ] || fail 'mounted an unconfigured disk'

# Options from the config are appended to the defaults.
printf 'UUID=0b5e-vfat\nLABEL=\nTYPE=vfat\n' >$t/blkid.sdb1
"$s" mount sdb1 2>/dev/null || fail 'vfat mount'
[ "$(tail -n 1 $t/mounts)" = "-t vfat -o nosuid,nodev,noatime,uid=1000,gid=1000 $t/dev/sdb1 $t/root/run/media/data" ] ||
	fail "vfat args: $(tail -n 1 $t/mounts)"
"$s" umount sdb1 2>/dev/null
[ ! -e $t/root/run/media/data ] || fail 'mountpoint left behind'

# A symlinked component: mountinfo would show another path; refused.
printf 'UUID=0b5e-ext4\nLABEL=ROG5-USB\nTYPE=ext4\n' >$t/blkid.sdb1
rm -r $t/root/run/media/phone; mkdir $t/root/run/real; ln -s ../real $t/root/run/media/phone
n=$(wc -l <$t/mounts)
"$s" mount sdb1 2>/dev/null && fail 'mounted through a symlink'
[ "$(wc -l <$t/mounts)" = "$n" ] || fail 'mount ran through a symlink'
rm $t/root/run/media/phone

# A second disk with the same label: never stacked on the first.
sdc=$t/sys/devices/platform/soc/a800000.usb/xhci-hcd.1/usb2/2-2/2-2:1.0/host1/target1:0:0/1:0:0:0/block/sdc/sdc1
mkdir -p $sdc; echo 8:33 >$sdc/dev; ln -s $sdc $t/sys/class/block/sdc1
printf 'UUID=other\nLABEL=ROG5-USB\nTYPE=ext4\n' >$t/blkid.sdc1
"$s" mount sdb1 2>/dev/null || fail 'mount sdb1 before the second disk'
n=$(wc -l <$t/mounts)
"$s" mount sdc1 2>/dev/null && fail 'second disk with the same label mounted'
[ "$(wc -l <$t/mounts)" = "$n" ] || fail 'second disk stacked'
echo PASS rog5-usb-storage
