#!/usr/bin/env bash
# Guest-only worker; its private 9p directory has no host project/recovery data.
set -euo pipefail
case " $(cat /proc/cmdline) " in
    *' rog5.virtual_drm=1 '*) ;;
    *) exit 1 ;;
esac
capture_child=''
trap 'if [[ -n $capture_child ]]; then kill "$capture_child" 2>/dev/null || true; wait "$capture_child" || true; fi' EXIT
trap 'exit 1' TERM INT
for ((attempt=0; attempt<250; attempt++)); do
    sockets=()
    for socket in "$XDG_RUNTIME_DIR"/wayland-*; do
        [[ ! -S $socket ]] || sockets+=("$socket")
    done
    [[ ${#sockets[@]} == 0 ]] || break
    sleep 0.1
done
[[ ${#sockets[@]} == 1 ]]
export WAYLAND_DISPLAY="${sockets[0]##*/}"
for label in initial final; do
    # A request may wait up to one second; client5s + poll1s fits host8s.
    # Avoid hundreds of short-lived sleep processes during cold GTK startup.
    for ((attempt=0; attempt<110; attempt++)); do
        [[ ! -f /run/native-capture/$label.request ]] || break
        sleep 1
    done
    read -r request < "/run/native-capture/$label.request"
    [[ $request == "$label" ]]
    /run/payload/screencopy "/run/native-capture/$label.ppm" \
        >"/run/native-capture/$label.json" &
    capture_child=$!
    status=0
    wait "$capture_child" || status=$?
    capture_child=''
    printf '%s\n' "$status" > "/run/native-capture/$label.done.tmp"
    mv "/run/native-capture/$label.done.tmp" "/run/native-capture/$label.done"
    [[ $status == 0 ]]
done
