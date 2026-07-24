#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
writer=$repo/scripts/device/write-network-root-manifest.sh
verifier=$repo/scripts/device/verify-network-root-bundle.sh

[ -x "$writer" ] || {
	echo 'FAIL missing executable network-root manifest writer' >&2
	exit 1
}
[ -x "$verifier" ] || {
	echo 'FAIL missing executable network-root bundle verifier' >&2
	exit 1
}

required='
Image-5.4.210-network-root-stage
config-5.4.210-network-root-stage
embedded-kexec-stage-initramfs.cpio.gz
build-meta-5.4.210-network-root-stage.txt
Image-7.1.4-network-root
Image.gz-7.1.4-network-root
config-7.1.4-network-root
modules-7.1.4-network-root.tar.gz
build-meta-7.1.4-network-root.txt
sm8350-asus-rog-phone5-recovery.dtb
rog5-network-root-initramfs.cpio.gz
rog5-network-root-kexec-stage-initramfs.cpio.gz
boot-5.4.210-network-root-stage.raw.img
boot-5.4.210-network-root-stage.avb.img
'

for file in $required; do
	grep -Fq "$file" "$writer" || {
		echo "FAIL manifest writer omits $file" >&2
		exit 1
	}
	grep -Fq "$file" "$verifier" || {
		echo "FAIL bundle verifier omits $file" >&2
		exit 1
	}
done

grep -Fq 'verify-mainline-network-root-build.sh' "$verifier"
grep -Fq 'verify-network-root-initramfs.sh' "$verifier"
grep -Fq 'load-mainline-network-root.sh' "$verifier"
grep -Fq 'CONFIG_SCSI_UFSHCD' "$verifier"
grep -Fq 'rog5.netroot=1' "$verifier"
grep -Fq 'Algorithm:' "$verifier"
for node in \
	/reserved-memory/memory@9b800000 \
	/soc@0/gpu@3d00000 \
	/soc@0/gmu@3d6a000 \
	/soc@0/clock-controller@3d90000 \
	/soc@0/iommu@3da0000
do
	grep -Fq "$node" "$verifier"
done

if grep -Eq '(^|[[:space:]])fastboot[[:space:]]+flash|(^|[[:space:]])dd[[:space:]].*of=/dev/' \
	"$writer" "$verifier"; then
	echo 'FAIL offline bundle tools contain a persistent-write command' >&2
	exit 1
fi

echo 'PASS network-root bundle contract covers exact artifacts and offline safety'
