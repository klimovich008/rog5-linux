#!/usr/bin/env bash
# Offline QEMU guest only: the host harness must supply no physical devices.
set -euo pipefail
case " $(cat /proc/cmdline) " in
    *' rog5.virtual_drm=1 '*) ;;
    *) echo 'FAIL virtual guest marker absent' >&2; exit 1 ;;
esac
test -d /sys/bus/virtio/devices
ulimit -c 0
export XDG_RUNTIME_DIR=/run/user/0
mkdir -p "$XDG_RUNTIME_DIR" /run/seatd /run/dbus
chmod 700 "$XDG_RUNTIME_DIR"
echo 'BEGIN virtual DRM discovery (phone hardware NOT RUN)'
uname -a
test -c /dev/dri/card0
for connector in /sys/class/drm/card0-*/status; do
    printf '%s: ' "$connector"
    cat "$connector"
done
timeout --kill-after=2 15 modetest -M virtio_gpu -c
echo 'PASS virtual DRM discovery'
# Deliberately no Flutter yet: isolate seat, EGL and KMS startup first.
export LIBSEAT_BACKEND=seatd
export SEATD_VTBOUND=0
export LIBGL_ALWAYS_SOFTWARE=1
export RUST_BACKTRACE=1
timeout --kill-after=2 45 seatd-launch -- /run/payload/deniald \
    --device /dev/dri/card0 --frames 3
echo 'PASS actual deniald virtual KMS frames'
