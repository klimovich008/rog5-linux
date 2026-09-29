#!/bin/bash
# Emulate an external-monitor unplug for a locked Phosh without touching the
# real display or session. Headless sway (no DRM, no input devices) hosts a
# nested phoc (wayland backend, 2 outputs = 2 sway windows); Phosh runs in
# that phoc, locked, on a private session bus without service activation.
# Closing the sway window of WL-2 destroys phoc's output WL-2: phoc closes the
# layer surfaces on it (the lock shield) and removes the wl_output global --
# the same sequence as a DP unplug.
# Optional steps (env):
#   CLOSE_SHIELD=1  before the unplug, destroy the lock shield widget from gdb,
#                   i.e. what PhoshLayerSurface does when the compositor closes
#                   it while it's still tracked (the state seen in the crashes)
#   UNLOCK=1        after the unplug, unlock the test Phosh via
#                   phosh_lockscreen_manager_set_locked(FALSE) from gdb (needs
#                   an unstripped phosh; it's the test instance, no PIN used)
# usage (as the phone user): hotplug-test.sh /path/to/phosh
set -u
PHOSH=${1:-/usr/lib/phosh/phosh}
CLOSE_SHIELD=${CLOSE_SHIELD:-0}
UNLOCK=${UNLOCK:-0}
gdbcall() { timeout 20 gdb -q -batch -p "$PID" -ex "call $1" 2>&1 | grep -E "^\$|No symbol|error" ; }
T=$(mktemp -d /tmp/phosh-hotplug.XXXXXX)
chmod 700 "$T"
export XDG_RUNTIME_DIR=$T
unset WAYLAND_DISPLAY DISPLAY DBUS_SESSION_BUS_ADDRESS GDMSESSION
cat > "$T/sway.conf" <<'EOC'
output * resolution 1280x1600
# floating: closing WL-2 must not resize WL-1 (the phone's DSI panel never
# changes size on a DP unplug)
for_window [title="WL-"] floating enable
EOC
printf '[core]\nxwayland=false\n' > "$T/phoc.ini"
cat > "$T/bus.conf" <<'EOC'
<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-Bus Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <listen>unix:tmpdir=/tmp</listen>
  <auth>EXTERNAL</auth>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
EOC
cat > "$T/run-phosh" <<EOC
#!/bin/sh
exec env G_MESSAGES_DEBUG="phosh-lockscreen-manager phosh-monitor-manager phosh-layer-surface" \
  GSETTINGS_BACKEND=memory GIO_USE_VFS=local GVFS_DISABLE_FUSE=1 NO_AT_BRIDGE=1 \
  "$PHOSH" --locked
EOC
chmod +x "$T/run-phosh"
WLR_BACKENDS=headless WLR_RENDERER=pixman WLR_LIBINPUT_NO_DEVICES=1 \
  setsid sway -c "$T/sway.conf" > "$T/sway.log" 2>&1 &
SWAY=$!
BUS=
cleanup() {
  [ -n "${PID:-}" ] && kill "$PID" 2>/dev/null; sleep 0.5
  [ -n "${PID:-}" ] && kill -9 "$PID" 2>/dev/null
  [ -n "$BUS" ] && pkill -9 -s "$(ps -o sid= -p "$BUS" | tr -d ' ')" 2>/dev/null
  pkill -9 -s "$(ps -o sid= -p "$SWAY" | tr -d ' ')" 2>/dev/null
  sleep 1
  grep -q "$T" /proc/mounts && fusermount3 -u "$T"/gvfs
  rm -rf "$T"
}
trap cleanup EXIT INT TERM
for i in $(seq 50); do ls "$T"/wayland-? >/dev/null 2>&1 && ls "$T"/sway-ipc.* >/dev/null 2>&1 && break; sleep 0.1; done
export SWAYSOCK=$(ls "$T"/sway-ipc.* | head -1)
export WAYLAND_DISPLAY=$(basename "$(ls "$T"/wayland-? | head -1)")
setsid dbus-run-session --config-file="$T/bus.conf" -- env WLR_BACKENDS=wayland WLR_WL_OUTPUTS=2 WLR_RENDERER=pixman \
  phoc -C "$T/phoc.ini" -E "$T/run-phosh" > "$T/phoc.log" 2>&1 &
BUS=$!
sleep 10
PID=$(pgrep -P "$(pgrep -P "$BUS" -x phoc)" -f "$PHOSH")
echo "phosh under test: $PHOSH pid $PID"
echo "sway windows: $(swaymsg -t get_tree | grep -o '"name": "wlroots[^"]*"' | tr '\n' ' ')"
if [ "$CLOSE_SHIELD" = 1 ]; then
  SHIELD=$(grep -ao "Mapped 'phosh lockshield' (0x[0-9a-f]*)" "$T/phoc.log" | tail -1 | grep -o "0x[0-9a-f]*")
  echo "--- destroying lock shield $SHIELD (as if the compositor closed it)"
  gdbcall "(void)gtk_widget_destroy((void*)$SHIELD)"
  sleep 1
fi
echo "--- unplug WL-2 at $(date +%T.%N)"
[ "${NO_UNPLUG:-0}" = 1 ] || swaymsg -q '[title="WL-2"] kill'
sleep 4
if kill -0 "$PID" 2>/dev/null; then echo "RESULT: phosh survived the unplug"; else echo "RESULT: PHOSH DIED"; fi
if [ "$UNLOCK" = 1 ] && kill -0 "$PID" 2>/dev/null; then
  echo "--- unlocking the test phosh"
  gdbcall "(void)phosh_lockscreen_manager_set_locked(phosh_shell_get_lockscreen_manager(phosh_shell_get_default()), 0)"
  sleep 2
  if kill -0 "$PID" 2>/dev/null; then echo "RESULT: phosh survived the unlock"; else echo "RESULT: PHOSH DIED on unlock"; fi
fi
echo "=== relevant phoc/phosh log"
grep -aE "shield|Shield|G_IS_OBJECT|Monitor .*(gone|removed|added)|lock|Destroying layer surface 'phosh lockshield|SEGV|Segmentation|CRITICAL|assertion" "$T/phoc.log" | grep -v "dbus-daemon" | tail -25
# cleanup() runs on exit
