#!/bin/bash
set -euo pipefail

stage=${STAGE_ROOT:-/stage}
resolver=$stage/etc/resolv.conf
device_stage=${ARCH_DEVICE_STAGE:-scripts/device/stage-arch-rootfs.sh}
kind='missing'
target=

case $device_stage in
	scripts/device/stage-arch-rootfs.sh|\
	scripts/device/stage-arch-rootfs-v3.sh) ;;
	*) echo "FAIL unsupported Arch device stage: $device_stage" >&2; exit 1 ;;
esac
backup=$(mktemp)

restore_resolver() {
	rm -f "$resolver"
	case $kind in
		link) ln -s "$target" "$resolver" ;;
		file) cp -a "$backup" "$resolver" ;;
	esac
	rm -f "$backup"
}
trap restore_resolver EXIT INT TERM

if [[ -L $resolver ]]; then
	kind='link'
	target=$(readlink "$resolver")
elif [[ -e $resolver ]]; then
	kind='file'
	cp -a "$resolver" "$backup"
fi
rm -f "$resolver"
cp -L /etc/resolv.conf "$resolver"

chroot "$stage" /bin/bash "/workspace/repo/$device_stage"
