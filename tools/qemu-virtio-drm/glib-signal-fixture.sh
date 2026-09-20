#!/usr/bin/bash
# Run only inside the explicitly marked small ARM64 API guest as the mobile UID.
set -euo pipefail
[[ $EUID == 1000 && -d /sys/bus/virtio/devices ]]
read -r cmdline < /proc/cmdline
[[ " $cmdline " == *' rog5.signal_fixture=1 '* ]]
source /run/payload/launcher-apps.sh
source /run/payload/logind-apps.sh
state=$(mktemp -d /tmp/rog5-signal.XXXXXXXX)
parent='' close_probe_pid=''
cleanup() {
    local status=$?
    trap - EXIT
    if [[ -n $parent ]]; then kill -TERM "$parent" 2>/dev/null || :; wait "$parent" || :; fi
    if [[ -n $close_probe_pid ]]; then kill -TERM "$close_probe_pid" 2>/dev/null || :; wait "$close_probe_pid" || :; fi
    exit "$status"
}
trap cleanup EXIT
for mode in immediate delayed; do
    for observe in no yes; do
        out=$state/$mode-$observe
        mkdir -m 700 "$out"
        (umask 077; : > "$out/sync.log")
        timeout --verbose -k 2 10 /usr/bin/bash --noprofile --norc -c '
            export LD_PRELOAD=/run/payload/probe.so ROG5_SETTINGS_SYNC_LOG="$1"
            exec /run/payload/signal-fixture "$2"
        ' fixture "$out/sync.log" "$mode" > "$out/app.log" 2> "$out/timeout.log" &
        parent=$!
        ready=0
        for ((i=0;i<100;i++)); do
            if grep -q 'stage=ready ' "$out/app.log"; then ready=1; break; fi
            kill -0 "$parent"
            sleep .01
        done
        [[ $ready == 1 ]]
        if [[ $observe == yes ]]; then
            logind_apps_start_close_probe "$parent" "$out/sync.log" /run/payload/app-close-probe "$out/observer.log"
        fi
        # Match the production launcher: asynchronous observer, then TERM to timeout.
        kill -TERM "$parent"
        result=0; wait "$parent" || result=$?; parent=''
        probe_status=not-requested
        if [[ -n $close_probe_pid ]]; then
            probe_status=0; wait "$close_probe_pid" || probe_status=$?; close_probe_pid=''
        fi
        printf 'CASE mode=%s observer=%s app_status=%s probe_status=%s\n' "$mode" "$observe" "$result" "$probe_status"
        cat "$out/app.log" "$out/sync.log" "$out/timeout.log"
        [[ $observe == no ]] || cat "$out/observer.log"
        [[ $result == 0 ]]
        [[ $(grep -c 'stage=signal-callback ' "$out/app.log") == 1 ]]
        [[ $(grep -c 'stage=shutdown-enter ' "$out/app.log") == 1 ]]
        [[ $(grep -c 'stage=run-return ' "$out/app.log") == 1 ]]
        ! grep -q 'signal KILL' "$out/timeout.log"
        if [[ $observe == yes ]]; then
            # Fast exit may legitimately finish before attachment. Delayed exit
            # supplies a known interval and must yield the requested capture.
            if [[ $mode == delayed ]]; then
                [[ $probe_status == 0 ]]
                grep -q 'kind=ptrace-pc ' "$out/observer.log"
            else
                [[ $probe_status == 0 || $probe_status == 125 ]]
            fi
        fi
    done
done
echo 'PASS GLib signal fixture four cases; Denial NOT RUN; phone NOT RUN'
