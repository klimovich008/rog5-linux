#!/usr/bin/env bash
# Offline QEMU guest only: the host harness must supply no physical devices.
set -euo pipefail
prepare_editor_runtime() {
    # Package extraction does not execute post-transaction hooks. Derive only
    # these session caches in guest RAM; the authenticated /usr stays read-only.
    local schemas=${1:-/usr/share/glib-2.0/schemas}
    local mime=${2:-/usr/share/mime/packages}
    local cache=${3:-/run/gtk-runtime}
    mkdir -m 700 "$cache"
    mkdir -p "$cache/schemas" "$cache/mime/packages"
    timeout --kill-after=1 10 glib-compile-schemas --strict --targetdir="$cache/schemas" "$schemas"
    cp "$mime"/*.xml "$cache/mime/packages/"
    XDG_DATA_DIRS="$cache:/usr/local/share:/usr/share" \
        timeout --kill-after=1 10 update-mime-database "$cache/mime"
    test -s "$cache/schemas/gschemas.compiled"
    test -s "$cache/mime/mime.cache"
    export GSETTINGS_SCHEMA_DIR="$cache/schemas"
    export XDG_DATA_DIRS="$cache:/usr/local/share:/usr/share"
    sha256sum "$cache/schemas/gschemas.compiled" "$cache/mime/mime.cache"
    echo 'PASS guest RAM GSettings and MIME caches prepared'
}

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
# Existing bounded INFO audit exposes allocation backpressure in release builds.
export DENIA_RENDER_AUDIT=1
# Explicit diagnostic opt-in; never inherit an ambient host/guest setting.
unset DENIA_FOCUS_TRACE
if [[ -f /run/focus-trace ]]; then
    read -r focus_trace < /run/focus-trace
    [[ $focus_trace == 1 ]] || { echo 'FAIL invalid focus trace marker' >&2; exit 1; }
    export DENIA_FOCUS_TRACE=1
    echo 'OBSERVE bounded focus trace enabled; no phone evidence'
fi
# End focus trace setup.
if [[ -f /run/shell-profile ]]; then
    read -r profile < /run/shell-profile
    [[ $profile == mobile ]] || { echo 'FAIL unknown explicit shell profile' >&2; exit 1; }
    export DENIA_SHELL_PROFILE=mobile
    echo 'OBSERVE explicit mobile shell profile; synthetic VM input only'
fi
# Keep buffer format/import evidence at the failing GL boundary. The host
# harness bounds the complete serial log and guest lifetime.
export RUST_LOG=deniald=info,smithay=info,smithay::backend::egl::display=trace,smithay::backend::renderer::gles=trace
if [[ -x /run/payload/egl-thread-probe ]]; then
    for mode in exit unbind release; do
        timeout --kill-after=2 10 /run/payload/egl-thread-probe "$mode"
    done
    echo 'NOT RUN Denial: standalone EGL thread-transfer experiment'
elif [[ -d /run/payload/flutter ]]; then
    if [[ -f /run/mobile-editor || -f /run/mobile-launcher ]]; then
        prepare_editor_runtime
    fi
    # UntilLogout supports initially inactive CRTCs; the external timer owns
    # this guest's lifetime. Keep seatd alive while Denial handles SIGTERM.
    export SEATD_SOCK=/run/seatd.sock
    seatd &
    seat_pid=$!
    export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
    dbus-daemon --session --nofork --address="$DBUS_SESSION_BUS_ADDRESS" &
    bus_pid=$!
    udev_pid=''
    editor_pid=''
    editor_log_pid=''
    native_pid=''
    launcher_prepared=0
    evidence_prepared=0
    trap 'guest_status=$?; if [[ $launcher_prepared == 1 ]]; then launcher_apps_cleanup || guest_status=1; fi; if [[ $evidence_prepared == 1 ]]; then launcher_evidence_finish || guest_status=1; fi; if [[ -n $native_pid ]]; then kill "$native_pid" 2>/dev/null || true; wait "$native_pid" || true; fi; if [[ -n $editor_pid ]]; then kill "$editor_pid" 2>/dev/null || true; wait "$editor_pid" || true; fi; if [[ -n $editor_log_pid ]]; then kill "$editor_log_pid" 2>/dev/null || true; wait "$editor_log_pid" || true; fi; kill "$bus_pid" "$seat_pid"; wait "$bus_pid" || true; wait "$seat_pid" || true; if [[ -n $udev_pid ]]; then kill "$udev_pid"; wait "$udev_pid" || true; fi; exit "$guest_status"' EXIT
    if [[ -f /run/shell-profile ]]; then
        # Fixed virtual devices need real udev input_id data for libinput.
        for event in /sys/class/input/event*; do
            properties=$(timeout --kill-after=1 3 udevadm info --query=property --path="$event")
            if [[ $'\n'"$properties"$'\n' == *$'\nID_INPUT=1\n'* ]]; then
                echo 'OBSERVE virtual input before udev: ID_INPUT present'
            else
                echo 'OBSERVE virtual input before udev: ID_INPUT absent'
            fi
        done
        /usr/lib/systemd/systemd-udevd --resolve-names=never --children-max=2 &
        udev_pid=$!
        for ((attempt=0; attempt<30; attempt++)); do
            [[ ! -S /run/udev/control ]] || break
            sleep 0.1
        done
        # PID1 stays outside the guest chroot; these commands must still
        # contact this guest's udev. The virtual-only entry guard remains above.
        SYSTEMD_IGNORE_CHROOT=1 timeout --kill-after=1 5 udevadm control --ping
        SYSTEMD_IGNORE_CHROOT=1 timeout --kill-after=1 5 udevadm trigger --action=add --subsystem-match=input
        SYSTEMD_IGNORE_CHROOT=1 timeout --kill-after=1 6 udevadm settle --timeout=5
        mouse=0 keyboard=0
        for event in /sys/class/input/event*; do
            name=$(cat "$event/device/name")
            properties=$(timeout --kill-after=1 3 udevadm info --query=property --path="$event")
            [[ $'\n'"$properties"$'\n' == *$'\nID_INPUT=1\n'* ]]
            case $name in
                'QEMU Virtio Tablet')
                    [[ $'\n'"$properties"$'\n' == *$'\nID_INPUT_MOUSE=1\n'* ]]
                    mouse=$((mouse+1)) ;;
                'QEMU Virtio Keyboard')
                    [[ $'\n'"$properties"$'\n' == *$'\nID_INPUT_KEYBOARD=1\n'* ]]
                    keyboard=$((keyboard+1)) ;;
                *) echo 'FAIL unexpected virtual input device' >&2; exit 1 ;;
            esac
            echo "PASS initialized virtual input: $name"
        done
        [[ $mouse == 1 && $keyboard == 1 ]]
    fi
    for ((attempt=0; attempt<50; attempt++)); do
        [[ ! -S $SEATD_SOCK || ! -S $XDG_RUNTIME_DIR/bus ]] || break
        sleep 0.1
    done
    test -S "$SEATD_SOCK"
    test -S "$XDG_RUNTIME_DIR/bus"
    if [[ -f /run/native-capture-enabled ]]; then
        bash /run/native-capture.sh &
        native_pid=$!
    fi
    shell_seconds=45
    shell_options=(--start-locked)
    if [[ -f /run/mobile-launcher ]]; then
        read -r launcher_mode < /run/mobile-launcher
        [[ ( $launcher_mode == discover || $launcher_mode == apps ) && -f /run/shell-profile ]]
        source /run/launcher-apps.sh
        if [[ $launcher_mode == apps ]]; then
            [[ $(cat /sys/class/virtio-ports/vport0p1/name) == rog5.launcher ]]
            source /run/launcher-evidence.sh
            launcher_evidence_prepare
            evidence_prepared=1
        fi
        launcher_prepared=1
        launcher_apps_prepare
        unset DENIA_START_LOCKED
        shell_options=()
        shell_seconds=90
        echo "OBSERVE unlocked launcher mode=$launcher_mode; no automatic app launch"
    fi
    if [[ -f /run/mobile-editor ]]; then
        read -r editor < /run/mobile-editor
        [[ $editor == mousepad && -f /run/shell-profile ]]
        unset DENIA_START_LOCKED
        shell_options=()
        # The retained cold GTK runtime mapped at guest t=61s in qualification.
        # Reserve time for the fixed input sequence within the 120s host cap.
        shell_seconds=90
        : > /tmp/rog5-text-probe.txt
        mkfifo -m 600 /run/editor-stderr
        sed -u 's/^/EDITOR_WAYLAND /' < /run/editor-stderr &
        editor_log_pid=$!
        (
            for ((attempt=0; attempt<250; attempt++)); do
                sockets=()
                for socket in "$XDG_RUNTIME_DIR"/wayland-*; do
                    [[ ! -S $socket ]] || sockets+=("$socket")
                done
                [[ ${#sockets[@]} == 0 ]] || break
                sleep 0.1
            done
            [[ ${#sockets[@]} == 1 ]] || { echo 'FAIL ambiguous/missing guest Wayland socket'; exit 1; }
            echo 'OBSERVE native Mousepad launch; normal unlocked VM startup; RAM file only'
            exec timeout --preserve-status --kill-after=2 95 env \
                GDK_BACKEND=wayland WAYLAND_DEBUG=client WAYLAND_DISPLAY="${sockets[0]##*/}" \
                mousepad /tmp/rog5-text-probe.txt 2>/run/editor-stderr
        ) &
        editor_pid=$!
    fi
    run_denial() {
    timeout --preserve-status --kill-after=5 "$shell_seconds" /run/payload/deniald \
        --device /dev/dri/card0 --wayland \
        --flutter-bundle /run/payload/flutter "${shell_options[@]}"
    }
    if [[ $evidence_prepared == 1 ]]; then
        run_denial 2>&1 | /run/evidence-writer forward 3>/run/launcher-evidence/events
    else
        run_denial
    fi
    echo 'PASS actual deniald shell bounded exit'
else
    # Denial's bounded KMS diagnostic requires an existing mode to restore.
    # This initially blank guest qualifies discovery/ABI separately instead.
    timeout --kill-after=2 5 /run/payload/deniald --version
    echo 'PASS actual deniald guest CLI'
    echo 'NOT RUN Denial frames: use the complete shell runtime'
fi
