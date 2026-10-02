#!/bin/sh
# Install the host side of the ROG5 sensor DSP (SLPI) on the production root.
# Runs on the phone as root, with a copy of third_party/hexagonrpc in $1:
#   tar -C third_party/hexagonrpc -cf - . |
#     ssh root@PHONE 'rm -rf /run/hrpc && mkdir /run/hrpc && tar -C /run/hrpc -xf -'
#   ssh root@PHONE sh -s /run/hrpc <scripts/device/install-rog5-sensors.sh
#
# 1. Builds hexagonrpcd from the pinned upstream archive plus our patches
#    (0002 validates the remote side's buffer counts and sizes) and installs
#    it as /usr/local/bin/hexagonrpcd (rog5-sensors.service runs it as a
#    dynamic, unprivileged user).
# 2. Stages the files the SLPI's sensor_process reads through it, under
#    /usr/share/qcom/sm8350/ASUS/ZS673KS (hexagonrpcd -R layout):
#      sensors/config, sensors/sns_reg.conf  <- vendor_a /etc/sensors
#      sensors/registry, sensors/sns_reg_version <- persist /sensors/registry
#      dsp/{adsp,cdsp,sdsp}                   <- dsp_a
#    Only these are copied: persist also holds IMEI and other factory data.
#    Every partition is mounted read-only (vendor_a through a read-only loop on
#    the super partition, whose single vendor_a extent is fixed below).
#    The copies become root-owned and world-readable (Android's owners, e.g.
#    system = uid 1000 = the phone user, mean nothing here, and the sandboxed
#    daemon only reads). The new tree and binary are staged next to their
#    destinations and swapped in only once complete; the old ones stay until
#    then, and the service is restarted at the end.
set -eu
src=${1:?usage: install-rog5-sensors.sh THIRD_PARTY_HEXAGONRPC_DIR}
archive=hexagonrpc-598b591.tar.gz
archive_sha256=47924eabba00c37a366b1e78a9ee85a6497cfd44f49a2484cd2b4c4e9cabb1b8
data=/usr/share/qcom/sm8350/ASUS/ZS673KS
# super: LP metadata slot 0, partition vendor_a = one linear extent.
vendor_offset=$((11894784 * 512))
vendor_size=$((2346168 * 512))

partition() {
	for block in /sys/class/block/*; do
		grep -qx "PARTNAME=$1" "$block/uevent" 2>/dev/null && { echo "/dev/${block##*/}"; return 0; }
	done
	return 1
}

work=$(mktemp -d /run/rog5-sensors.XXXXXX)
stage= bin_new=
cleanup() {
	for m in "$work/vendor" "$work/persist" "$work/dsp"; do
		mountpoint -q "$m" 2>/dev/null && umount "$m"
	done
	[ -n "${loop:-}" ] && losetup -d "$loop" 2>/dev/null
	[ -z "$stage" ] || rm -rf "$stage"
	[ -z "$bin_new" ] || rm -f "$bin_new"
	rm -rf "$work"
}
trap cleanup EXIT

echo "$archive_sha256  $src/$archive" | sha256sum -c --quiet
tar -C "$work" -xzf "$src/$archive"
tree=$work/hexagonrpc-598b591
for p in "$src"/0*.patch; do
	git -C "$tree" apply "$p"
done
cc -O2 -Wall -Wno-unused-parameter -I"$tree/include" -I"$tree/hexagonrpcd" \
	-o "$work/hexagonrpcd" "$tree"/libhexagonrpc/*.c "$tree"/libhexagonrpc/interface/*.c \
	"$tree"/hexagonrpcd/*.c "$tree"/hexagonrpcd/interface/*.c
install -d -m 0755 /usr/local/bin
bin_new=/usr/local/bin/.hexagonrpcd.new
install -o root -g root -m 0755 "$work/hexagonrpcd" "$bin_new"

super=$(partition super)
persist=$(partition persist)
dsp=$(partition dsp_a)
mkdir -p "$work/vendor" "$work/persist" "$work/dsp"
loop=$(losetup -r -f --show -o "$vendor_offset" --sizelimit "$vendor_size" "$super")
[ "$(blkid -o value -s LABEL "$loop")" = vendor ] || { echo 'vendor_a extent does not hold the vendor ext4' >&2; exit 1; }
mount -o ro,noload "$loop" "$work/vendor"
mount -o ro,noload "$persist" "$work/persist"
mount -o ro "$dsp" "$work/dsp"

mkdir -p "${data%/*}"
stage=$(mktemp -d "${data%/*}/.${data##*/}.new.XXXXXX")
mkdir -p "$stage/sensors" "$stage/dsp"
cp -a "$work/vendor/etc/sensors/config" "$stage/sensors/config"
cp -a "$work/vendor/etc/sensors/sns_reg_config" "$stage/sensors/sns_reg.conf"
cp -a "$work/persist/sensors/registry/registry" "$stage/sensors/registry"
cp -a "$work/persist/sensors/registry/sns_reg_version" "$stage/sensors/sns_reg_version"
cp -a "$work/dsp/adsp" "$work/dsp/cdsp" "$work/dsp/sdsp" "$stage/dsp/"
ln -s /sys/devices/soc0 "$stage/socinfo"
# root-owned, read-only for everyone else (chmod -R skips the symlink)
chown -R -h root:root "$stage"
chmod -R u=rwX,go=rX "$stage"
chmod 0755 "$stage"
[ -n "$(ls -A "$stage/sensors/registry")" ] && [ -n "$(ls -A "$stage/sensors/config")" ] ||
	{ echo 'the staged registry or config is empty' >&2; exit 1; }
sync
# swap: one atomic exchange (renameat2 RENAME_EXCHANGE through util-linux
# exch), so the data path never goes missing; the old tree then sits at the
# staging path and is removed below
old=
if [ -e "$data" ] || [ -L "$data" ]; then
	if exch "$stage" "$data" 2>/dev/null; then
		old=$stage
	else
		# no exchange here (e.g. an overlay directory without redirect_dir):
		# two renames, putting the old tree back if the second fails
		old=${data%/*}/.${data##*/}.old.$$
		mv "$data" "$old"
		mv "$stage" "$data" || { mv "$old" "$data"; exit 1; }
	fi
else
	mv "$stage" "$data"
fi
stage=
mv -f "$bin_new" /usr/local/bin/hexagonrpcd
bin_new=
sync
[ -z "$old" ] || rm -rf "$old"
echo "hexagonrpcd $(sha256sum /usr/local/bin/hexagonrpcd | cut -c1-16)"
echo "registry entries $(ls "$data/sensors/registry" | wc -l), configs $(ls "$data/sensors/config" | wc -l)"
# pick up the new binary and data (no-op when the unit is not running)
systemctl try-restart rog5-sensors.service || true
