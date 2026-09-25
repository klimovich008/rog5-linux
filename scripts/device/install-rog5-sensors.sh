#!/bin/sh
# Install the host side of the ROG5 sensor DSP (SLPI) on the production root.
# Runs on the phone as root, with a copy of third_party/hexagonrpc in $1:
#   tar -C third_party/hexagonrpc -cf - . |
#     ssh root@PHONE 'rm -rf /run/hrpc && mkdir /run/hrpc && tar -C /run/hrpc -xf -'
#   ssh root@PHONE sh -s /run/hrpc <scripts/device/install-rog5-sensors.sh
#
# 1. Builds hexagonrpcd from the pinned upstream archive plus our patch and
#    installs it as /usr/local/bin/hexagonrpcd (rog5-sensors.service runs it).
# 2. Stages the files the SLPI's sensor_process reads through it, under
#    /usr/share/qcom/sm8350/ASUS/ZS673KS (hexagonrpcd -R layout):
#      sensors/config, sensors/sns_reg.conf  <- vendor_a /etc/sensors
#      sensors/registry, sensors/sns_reg_version <- persist /sensors/registry
#      dsp/{adsp,cdsp,sdsp}                   <- dsp_a
#    Only these are copied: persist also holds IMEI and other factory data.
#    Every partition is mounted read-only (vendor_a through a read-only loop on
#    the super partition, whose single vendor_a extent is fixed below).
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
cleanup() {
	for m in "$work/vendor" "$work/persist" "$work/dsp"; do
		mountpoint -q "$m" 2>/dev/null && umount "$m"
	done
	[ -n "${loop:-}" ] && losetup -d "$loop" 2>/dev/null
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
install -D -m 0755 "$work/hexagonrpcd" /usr/local/bin/hexagonrpcd

super=$(partition super)
persist=$(partition persist)
dsp=$(partition dsp_a)
mkdir -p "$work/vendor" "$work/persist" "$work/dsp"
loop=$(losetup -r -f --show -o "$vendor_offset" --sizelimit "$vendor_size" "$super")
[ "$(blkid -o value -s LABEL "$loop")" = vendor ] || { echo 'vendor_a extent does not hold the vendor ext4' >&2; exit 1; }
mount -o ro,noload "$loop" "$work/vendor"
mount -o ro,noload "$persist" "$work/persist"
mount -o ro "$dsp" "$work/dsp"

stage=$work/data
mkdir -p "$stage/sensors" "$stage/dsp"
cp -a "$work/vendor/etc/sensors/config" "$stage/sensors/config"
cp -a "$work/vendor/etc/sensors/sns_reg_config" "$stage/sensors/sns_reg.conf"
cp -a "$work/persist/sensors/registry/registry" "$stage/sensors/registry"
cp -a "$work/persist/sensors/registry/sns_reg_version" "$stage/sensors/sns_reg_version"
cp -a "$work/dsp/adsp" "$work/dsp/cdsp" "$work/dsp/sdsp" "$stage/dsp/"
ln -s /sys/devices/soc0 "$stage/socinfo"
rm -rf "$data"
mkdir -p "${data%/*}"
mv "$stage" "$data"
echo "hexagonrpcd $(sha256sum /usr/local/bin/hexagonrpcd | cut -c1-16)"
echo "registry entries $(ls "$data/sensors/registry" | wc -l), configs $(ls "$data/sensors/config" | wc -l)"
