#!/bin/bash
set -euo pipefail

stage=${STAGE_ROOT:-/stage}
resolver=$stage/etc/resolv.conf
kind=missing
target=
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
	kind=link
	target=$(readlink "$resolver")
elif [[ -e $resolver ]]; then
	kind=file
	cp -a "$resolver" "$backup"
fi
rm -f "$resolver"
cp -L /etc/resolv.conf "$resolver"

chroot "$stage" /bin/bash /workspace/repo/scripts/device/stage-arch-rootfs.sh
