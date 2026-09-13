#!/usr/bin/bash
# Sourced only for the explicit authenticated VM editor observation.
drain_editor_protocol() {
    local sink=${1:-/dev/vport0p1}
    [[ -c $sink || -p $sink ]] || return 1
    # One writer owns this port. Retain and drain the existing application log;
    # cap the attributed stream too, without imposing a limit on client memfds.
    LC_ALL=C awk -v sink="$sink" 'BEGIN {remaining=1048576; wire=1048576}
        {if (remaining>0) {piece=substr($0 "\n",1,remaining);
            printf "%s",piece; fflush(); remaining-=length(piece)}
         record="EDITOR_WAYLAND " $0 "\n";
         if (wire>0) {piece=substr(record,1,wire); printf "%s",piece > sink;
            fflush(sink); wire-=length(piece)}}'
}
run_authenticated_editor() {
    local attempt count
    # Exercise normal Foot lifecycle first; never direct OSK input at Foot.
    prepare_foot_close
    launch_foot
    for ((attempt=0;attempt<160;attempt++)); do
        require_running launcher && require_running foot || return 1
        grep -q 'xdg_toplevel.*configure' "$HOME/foot.log" && break
        sleep .25
    done
    grep -q 'xdg_toplevel.*configure' "$HOME/foot.log" || return 1
    close_foot_normally || return $?
    : > "$HOME/rog5-text-probe.txt"
    GDK_BACKEND=wayland WAYLAND_DEBUG=client timeout -k 2 65 mousepad "$HOME/rog5-text-probe.txt" > "$HOME/mousepad.pipe" 2>&1 &
    editor=$!
    # Exact focused key ordering is checked by the host protocol parser. This
    # bound keeps the real editor alive until the pointer-only flow has run.
    for ((attempt=0;attempt<180;attempt++)); do
        require_running launcher && require_running editor || return 1
        count=$(grep -c 'wl_keyboard.*\.key(' "$HOME/mousepad.log") || count=0
        if ((count >= 12)); then
            sleep 3
            echo 'OBSERVE editor key events collected; host must verify ordering and captures'
            return 0
        fi
        sleep .25
    done
    echo 'FAIL authenticated editor key observation deadline' >&2
    return 124
}
