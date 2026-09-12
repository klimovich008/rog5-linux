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
mkdir -m 1777 /tmp/.X11-unix
echo 'BEGIN virtual DRM discovery (phone hardware NOT RUN)'
uname -a
test -c /dev/dri/card0
for connector in /sys/class/drm/card0-*/status; do
    printf '%s: ' "$connector"
    cat "$connector"
done
timeout --kill-after=2 15 modetest -M virtio_gpu -c
echo 'PASS virtual DRM discovery'
export LIBSEAT_BACKEND=seatd
export SEATD_VTBOUND=0
read -r graphics_mode < /run/graphics-mode
case $graphics_mode in
    software) export LIBGL_ALWAYS_SOFTWARE=1 ;;
    virgl) unset LIBGL_ALWAYS_SOFTWARE ;;
    *) echo 'FAIL unknown virtual graphics mode' >&2; exit 1 ;;
esac
export RUST_BACKTRACE=1
if [[ -d /run/payload/flutter ]]; then
    # UntilLogout supports initially inactive CRTCs; the external timer owns
    # this guest's lifetime. Keep seatd alive while Denial handles SIGTERM.
    export SEATD_SOCK=/run/seatd.sock
    seatd &
    seat_pid=$!
    export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
    dbus-daemon --session --nofork --address="$DBUS_SESSION_BUS_ADDRESS" &
    bus_pid=$!
    trap 'kill "$bus_pid" "$seat_pid"; wait "$bus_pid" || true; wait "$seat_pid" || true' EXIT
    for ((attempt=0; attempt<50; attempt++)); do
        [[ ! -S $SEATD_SOCK || ! -S $XDG_RUNTIME_DIR/bus ]] || break
        sleep 0.1
    done
    test -S "$SEATD_SOCK"
    test -S "$XDG_RUNTIME_DIR/bus"
    timeout --preserve-status --kill-after=5 45 /run/payload/deniald \
        --device /dev/dri/card0 --wayland \
        --flutter-bundle /run/payload/flutter --start-locked
    echo 'PASS actual deniald shell bounded exit'
else
    # Denial's bounded KMS diagnostic requires an existing mode to restore.
    # This initially blank guest qualifies discovery/ABI separately instead.
    timeout --kill-after=2 5 /run/payload/deniald --version
    echo 'PASS actual deniald guest CLI'
    echo 'NOT RUN Denial frames: use the complete shell runtime'
fi
