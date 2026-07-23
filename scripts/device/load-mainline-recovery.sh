#!/bin/sh
set -eu

payload=/opt/rog5-recovery
image=$payload/Image
dtb=$payload/board.dtb
initramfs=$payload/initramfs.cpio.gz

[ "$(sha256sum "$image" | cut -d ' ' -f 1)" = \
	f010217f70eb6c8022b6af0d937c7ad33498b2c65913a448ef342a72f0148909 ]
[ "$(sha256sum "$dtb" | cut -d ' ' -f 1)" = \
	c9af02720703471425bbf5a9086869754031d7dced1ec7ec53cbf4c487f3a351 ]
[ "$(sha256sum "$initramfs" | cut -d ' ' -f 1)" = \
	bad228341c7a69de46444642f2519ad9c2f51e333f6c8e19660fce12eb000cb5 ]
gzip -t "$initramfs"

kexec -l "$image" \
	--dtb="$dtb" \
	--initrd="$initramfs" \
	--command-line='console=ttyMSM0,115200n8 rdinit=/init panic=10'

echo 'PASS mainline recovery payload loaded; run kexec -e only during an attended test'
