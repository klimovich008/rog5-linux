#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-kexec-recovery-stage.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}

check_hash() {
	actual=$(sha256sum "$artifact_dir/$1" | cut -d ' ' -f 1)
	[ "$actual" = "$2" ] || {
		echo "FAIL artifact hash mismatch: $1" >&2
		exit 1
	}
}

check_hash Image-5.4.210-kexec-stage 5655a45839340cb68e4cf5fe497f1e2790db293d4a8e234fb4d12dd54d98c9d7
check_hash config-5.4.210-kexec-stage 8c7fabbf879d2bce652d8b44d8ac1d982126015732b1176f63cedeb53064d571
check_hash Image-7.1.4 f010217f70eb6c8022b6af0d937c7ad33498b2c65913a448ef342a72f0148909
check_hash sm8350-asus-rog-phone5-recovery.dtb c9af02720703471425bbf5a9086869754031d7dced1ec7ec53cbf4c487f3a351
check_hash rog5-recovery-initramfs.cpio.gz bad228341c7a69de46444642f2519ad9c2f51e333f6c8e19660fce12eb000cb5
check_hash rog5-kexec-stage-initramfs.cpio.gz cce82e680ae4b745edabb6a9da5ecb979cdeecb2e6f304bc7cad18d33eef3c52
check_hash boot-5.4.210-kexec-stage.raw.img d127d1319b72082c375ddcb3fc4362502af0dcf23ecd0cac3aac53728699011e
check_hash boot-5.4.210-kexec-stage.avb.img 628477310bafa27eb31341efb5c6b7a2ace0d8e85586655d08c335bc233c06af

config=$artifact_dir/config-5.4.210-kexec-stage
grep -qx 'CONFIG_KEXEC=y' "$config"
grep -qx '# CONFIG_KEXEC_FILE is not set' "$config"
strings "$artifact_dir/Image-5.4.210-kexec-stage" | grep -q 'Linux version 5.4.210.*-kexec-stage'

dtb=$artifact_dir/sm8350-asus-rog-phone5-recovery.dtb
for node in \
	/soc@0/ufshc@1d84000 \
	/soc@0/phy@1d87000 \
	/soc@0/usb@a6f8800 \
	/soc@0/phy@88e3000 \
	/soc@0/phy@88e8000
do
	[ "$(fdtget -t s "$dtb" "$node" status)" = okay ]
done
[ "$(fdtget -t s "$dtb" /soc@0/usb@a8f8800 status)" = disabled ]

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
mkdir "$stage/target" "$stage/staging" "$stage/boot"
gzip -dc "$artifact_dir/rog5-recovery-initramfs.cpio.gz" | \
	(cd "$stage/target" && cpio -idm --quiet --no-absolute-filenames)
gzip -dc "$artifact_dir/rog5-kexec-stage-initramfs.cpio.gz" | \
	(cd "$stage/staging" && cpio -idm --quiet --no-absolute-filenames)

[ -x "$stage/target/init" ]
[ ! -e "$stage/target/opt/rog5-recovery" ]
! grep -q 'mount.*\(userdata\|rootdev\)' "$stage/target/init"
[ -x "$stage/staging/usr/sbin/kexec" ]
[ -x "$stage/staging/usr/local/sbin/rog5-load-mainline-recovery" ]
! grep -rIl 'BEGIN .*PRIVATE KEY' "$stage/target" "$stage/staging" >/dev/null
readelf -h "$stage/staging/usr/sbin/kexec" | grep -q 'Machine:.*AArch64'

[ "$(sha256sum "$stage/staging/opt/rog5-recovery/Image" | cut -d ' ' -f 1)" = \
	f010217f70eb6c8022b6af0d937c7ad33498b2c65913a448ef342a72f0148909 ]
[ "$(sha256sum "$stage/staging/opt/rog5-recovery/board.dtb" | cut -d ' ' -f 1)" = \
	c9af02720703471425bbf5a9086869754031d7dced1ec7ec53cbf4c487f3a351 ]
[ "$(sha256sum "$stage/staging/opt/rog5-recovery/initramfs.cpio.gz" | cut -d ' ' -f 1)" = \
	bad228341c7a69de46444642f2519ad9c2f51e333f6c8e19660fce12eb000cb5 ]

python3 "$mkbootimg_dir/unpack_bootimg.py" \
	--boot_img "$artifact_dir/boot-5.4.210-kexec-stage.raw.img" \
	--out "$stage/boot" >/dev/null
[ "$(sha256sum "$stage/boot/kernel" | cut -d ' ' -f 1)" = \
	5655a45839340cb68e4cf5fe497f1e2790db293d4a8e234fb4d12dd54d98c9d7 ]
[ "$(sha256sum "$stage/boot/ramdisk" | cut -d ' ' -f 1)" = \
	cce82e680ae4b745edabb6a9da5ecb979cdeecb2e6f304bc7cad18d33eef3c52 ]

[ "$(stat -c %s "$artifact_dir/boot-5.4.210-kexec-stage.avb.img")" = 100663296 ]
python3 "$avbtool" info_image \
	--image "$artifact_dir/boot-5.4.210-kexec-stage.avb.img" >"$stage/avb-info"
grep -q '^Algorithm:[[:space:]]*NONE$' "$stage/avb-info"
grep -q 'Partition Name:[[:space:]]*boot$' "$stage/avb-info"

echo 'PASS self-contained two-stage kexec recovery bundle; offline validation only'
