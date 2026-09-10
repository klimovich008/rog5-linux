#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
init=$repo/initramfs/local-image-stage-timing-init

[ -f "$init" ] && [ -x "$init" ]
for contract in \
	'kernel-release:5' \
	'command-line:10' \
	'usb-mode:15' \
	'configfs-mount:20' \
	'gadget-tree:25' \
	'gadget-descriptor:30' \
	'ncm-function:35' \
	'ncm-link:40' \
	'udc-identity:45' \
	'udc-bind:50' \
	'post-bind-mdev:55' \
	'ncm-absent:60' \
	'ncm-link-up:65' \
	'ncm-address:70' \
	'ncm-carrier:75' \
	'power-usb:80' \
	'timing-pass:85'; do
	grep -Fq "${contract%%:*}) delay=${contract#*:}" "$init"
done
grep -Fq 'fail timing-pass' "$init"
! grep -Fq '/rog5-ufs-modules/' "$init"
! grep -Fq 'blockdev ' "$init"
! grep -Fq '/usr/sbin/sshd' "$init"
! grep -Fq 'rog5-install-local-arch-image' "$init"

echo 'PASS timing discriminator changes only bounded pre-storage failure observability'
