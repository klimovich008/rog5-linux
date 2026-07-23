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
check_hash rog5-recovery-initramfs.cpio.gz 8bd91d390cf3d65e55c7d1e7e581800edfbede30f8d3f5e51e0d53cf5a495226
check_hash rog5-kexec-stage-initramfs.cpio.gz 940df2d403dcf02dd03b3dc428747a25bcc4290bfd9d31bd7c2f00876bb821f0
check_hash boot-5.4.210-kexec-stage.raw.img 5be6a072aaff93df210cf0a86511789f995e3ec8499d1b6728e7c4a8739185f0
check_hash boot-5.4.210-kexec-stage.avb.img 88777b3c32fbe6fa29964dd9d1865447c9109d07593e5d4ab910a6bdf1f27aa0

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
grep -qx 'set -u' "$stage/target/init"
[ -x "$stage/staging/usr/sbin/kexec" ]
[ -x "$stage/staging/usr/local/sbin/rog5-load-mainline-recovery" ]
grep -qx 'set -u' "$stage/staging/init"
! grep -rIl 'BEGIN .*PRIVATE KEY' "$stage/target" "$stage/staging" >/dev/null
readelf -h "$stage/staging/usr/sbin/kexec" | grep -q 'Machine:.*AArch64'

(
	cd "$stage/staging/opt/rog5-recovery"
	sha256sum -c SHA256SUMS
)
[ "$(sha256sum "$stage/staging/opt/rog5-recovery/Image" | cut -d ' ' -f 1)" = \
	f010217f70eb6c8022b6af0d937c7ad33498b2c65913a448ef342a72f0148909 ]
[ "$(sha256sum "$stage/staging/opt/rog5-recovery/board.dtb" | cut -d ' ' -f 1)" = \
	c9af02720703471425bbf5a9086869754031d7dced1ec7ec53cbf4c487f3a351 ]
[ "$(sha256sum "$stage/staging/opt/rog5-recovery/initramfs.cpio.gz" | cut -d ' ' -f 1)" = \
	8bd91d390cf3d65e55c7d1e7e581800edfbede30f8d3f5e51e0d53cf5a495226 ]

python3 "$mkbootimg_dir/unpack_bootimg.py" \
	--boot_img "$artifact_dir/boot-5.4.210-kexec-stage.raw.img" \
	--out "$stage/boot" >/dev/null
[ "$(sha256sum "$stage/boot/kernel" | cut -d ' ' -f 1)" = \
	5655a45839340cb68e4cf5fe497f1e2790db293d4a8e234fb4d12dd54d98c9d7 ]
[ "$(sha256sum "$stage/boot/ramdisk" | cut -d ' ' -f 1)" = \
	940df2d403dcf02dd03b3dc428747a25bcc4290bfd9d31bd7c2f00876bb821f0 ]

[ "$(stat -c %s "$artifact_dir/boot-5.4.210-kexec-stage.avb.img")" = 100663296 ]
python3 "$avbtool" info_image \
	--image "$artifact_dir/boot-5.4.210-kexec-stage.avb.img" >"$stage/avb-info"
grep -q '^Algorithm:[[:space:]]*NONE$' "$stage/avb-info"
grep -q 'Partition Name:[[:space:]]*boot$' "$stage/avb-info"

echo 'PASS self-contained two-stage kexec recovery bundle; offline validation only'
