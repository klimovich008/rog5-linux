#!/bin/sh
set -u

pkill -u browser -f '[c]hromium.*--remote-debugging-port=9222' 2>/dev/null || true
pkill -u browser -f '[r]og5-plasma-wayland-session' 2>/dev/null || true

for pid in $(ps w | grep '[k]win_wayland.*--socket wayland-1' | awk '{print $1}'); do
    kill "$pid" 2>/dev/null || true
done

pkill -u browser -x openbox 2>/dev/null || true
pkill -f '[w]ebsockify.*127.0.0.1:6080.*127.0.0.1:5901' 2>/dev/null || true
pkill -x Xvnc 2>/dev/null || true
sleep 1

rm -f /tmp/.X1-lock /tmp/.X11-unix/X1 /run/user/1000/wayland-1 /run/user/1000/wayland-1.lock
echo 'PASS remote KDE/Chromium session stopped; physical Plasma and ttyd remain running'
