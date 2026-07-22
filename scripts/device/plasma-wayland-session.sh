#!/bin/sh
set -u

export HOME=/home/browser
export XDG_RUNTIME_DIR=/run/user/1000
export WAYLAND_DISPLAY=wayland-1
export QT_QPA_PLATFORM=wayland
export QT_QUICK_BACKEND=software
export LIBGL_ALWAYS_SOFTWARE=1

# Stop only the nested VNC compositor, never the physical DRM session.
for pid in $(ps w | grep '[k]win_wayland.*--socket wayland-1' | awk '{print $1}'); do
    kill "$pid" 2>/dev/null || true
done
sleep 1
rm -f "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY.lock"

DISPLAY=:1 QT_QPA_PLATFORM=xcb kwin_wayland \
    --x11-display :1 --xwayland --socket "$WAYLAND_DISPLAY" \
    --width 1280 --height 720 >>/home/browser/kwin.log 2>&1 &

i=0
while [ "$i" -lt 100 ] && [ ! -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]; do
    i=$((i + 1))
    sleep 0.1
done
[ -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ] || exit 1

i=0
while [ "$i" -lt 150 ] && ! QT_QPA_PLATFORM=offscreen qdbus6 org.kde.KWin /KWin >/dev/null 2>&1; do
    i=$((i + 1))
    sleep 0.2
done

dbus-update-activation-environment HOME XDG_RUNTIME_DIR WAYLAND_DISPLAY \
    QT_QPA_PLATFORM QT_QUICK_BACKEND LIBGL_ALWAYS_SOFTWARE

/usr/lib/libexec/kactivitymanagerd &
kded6 &

attempt=0
while [ "$attempt" -lt 8 ]; do
    attempt=$((attempt + 1))
    : > /home/browser/plasmashell.log
    plasmashell >>/home/browser/plasmashell.log 2>&1 &
    shell_pid=$!
    sleep 20
    if ! grep -q 'unexisting screen geometry' /home/browser/plasmashell.log 2>/dev/null; then
        break
    fi
    kill "$shell_pid" 2>/dev/null || true
    sleep 2
done

wait "$shell_pid" 2>/dev/null || true
while :; do
    plasmashell >>/home/browser/plasmashell.log 2>&1
    sleep 2
done
