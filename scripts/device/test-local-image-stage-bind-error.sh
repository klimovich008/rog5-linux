#!/bin/sh
set -eu
repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
init=$repo/initramfs/local-image-stage-bind-error-init
sh -n "$init"
for value in -16 -19 -22 -11 -517; do grep -Fq "failed to start configfs-gadget: $value" "$init"; done
for delay in 10 20 30 40 50 60 70 80 85 90; do grep -Fq "delayed_return $delay" "$init"; done
for forbidden in '/sys/class/block' '/dev/sd' blockdev ext4 ssh insmod modprobe; do ! grep -Fq "$forbidden" "$init"; done
echo 'PASS bind-error classifier maps synchronous kernel errno without storage'
