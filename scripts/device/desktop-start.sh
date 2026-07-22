#!/bin/sh
set -u

export HOME=/root
export USER=root
export DISPLAY=:1

mkdir -p /root/.vnc /root/.config/openbox /run/rog5-desktop /run/user/1000
chown browser:browser /run/user/1000
chmod 700 /run/user/1000
ip link set lo up

mkdir -p /run/dbus
pgrep -x dbus-daemon >/dev/null 2>&1 || dbus-daemon --system --fork

if ! pgrep -x Xvnc >/dev/null 2>&1; then
    lock=/tmp/.X1-lock
    socket=/tmp/.X11-unix/X1
    if [ -e "$lock" ]; then
        lock_pid=$(tr -d ' ' < "$lock" 2>/dev/null || true)
        lock_process=
        [ -z "$lock_pid" ] || lock_process=$(cat "/proc/$lock_pid/comm" 2>/dev/null || true)
        [ "$lock_process" != Xvnc ] || {
            echo "ERROR display :1 lock belongs to live Xvnc PID $lock_pid" >&2
            exit 1
        }
        rm -f "$lock" "$socket"
    fi
    if ss -ltn 2>/dev/null | grep -q ':5901 '; then
        echo 'ERROR TCP 5901 is already in use by a non-Xvnc process' >&2
        exit 1
    fi
    nohup Xvnc :1 -geometry 1280x720 -depth 24 -localhost yes -rfbport 5901 -SecurityTypes None \
        >/var/log/xvnc.log 2>&1 &
fi

i=0
while [ "$i" -lt 50 ] && [ ! -S /tmp/.X11-unix/X1 ]; do
    i=$((i + 1))
    sleep 0.1
done
[ -S /tmp/.X11-unix/X1 ] || { echo 'ERROR Xvnc did not create display :1' >&2; exit 1; }

i=0
while [ "$i" -lt 50 ] && ! xset q >/dev/null 2>&1; do
    i=$((i + 1))
    sleep 0.1
done

pgrep -u browser openbox >/dev/null 2>&1 || \
    su -s /bin/sh browser -c 'DISPLAY=:1 HOME=/home/browser nohup openbox >/home/browser/openbox.log 2>&1 &'

pgrep -u browser -f 'rog5-plasma-wayland-session' >/dev/null 2>&1 || \
    su -s /bin/sh browser -c 'HOME=/home/browser XDG_RUNTIME_DIR=/run/user/1000 nohup dbus-run-session /usr/local/sbin/rog5-plasma-wayland-session >/home/browser/plasma-session.log 2>&1 &'

pgrep -f 'websockify.*6080' >/dev/null 2>&1 || \
    nohup websockify --web=/usr/share/novnc 127.0.0.1:6080 127.0.0.1:5901 \
        >/var/log/novnc.log 2>&1 &

if ! pgrep -u browser -f '[c]hromium.*--remote-debugging-port=9222' >/dev/null 2>&1; then
    (
        i=0
        while [ "$i" -lt 300 ] && [ ! -S /run/user/1000/wayland-1 ]; do
            i=$((i + 1))
            sleep 1
        done
        su -s /bin/sh browser -c 'HOME=/home/browser XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-1 nohup chromium-browser \
            --ozone-platform=wayland --disable-gpu --disable-dev-shm-usage \
            --remote-debugging-address=127.0.0.1 --remote-debugging-port=9222 \
            --user-data-dir=/home/browser/.config/chromium-server \
            about:blank >/home/browser/chromium.log 2>&1 &'
    ) &
fi

if ! pgrep -f '[t]tyd.*127.0.0.1.*7681' >/dev/null 2>&1; then
    su -s /bin/sh browser -c 'HOME=/home/browser nohup ttyd -i 127.0.0.1 -p 7681 -W \
        -w /home/browser tmux new-session -A -s main \
        >/home/browser/ttyd.log 2>&1 &'
fi

echo 'PASS localhost-only noVNC, KDE session, Chromium CDP, and ttyd launch requested'
