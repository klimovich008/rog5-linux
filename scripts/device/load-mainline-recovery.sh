#!/bin/sh
set -eu

payload=/opt/rog5-recovery
image=$payload/Image
dtb=$payload/board.dtb
initramfs=$payload/initramfs.cpio.gz
manifest=$payload/SHA256SUMS

[ -r "$manifest" ]
(cd "$payload" && sha256sum -c SHA256SUMS)
gzip -t "$initramfs"

command_line='console=ttyMSM0,115200n8 rdinit=/init panic=10'
for argument in $(cat /proc/cmdline); do
	case $argument in
		rog5.recovery_timeout=*|rog5.recovery_cidr=*|rog5.recovery_gateway=*)
			command_line="$command_line $argument"
			;;
	esac
done

kexec -l "$image" \
	--dtb="$dtb" \
	--initrd="$initramfs" \
	--command-line="$command_line"

echo 'PASS mainline recovery payload loaded; run kexec -e only during an attended test'
