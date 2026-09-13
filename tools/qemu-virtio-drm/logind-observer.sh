#!/usr/bin/bash
# Offline generic ARM64 VM fixture; never install or run on a phone.
set -u
observe_startup_detail() {
    # Diagnostic bytes are hex, never serial success/protocol evidence. Read
    # only the synthetic session log and selected process metadata, not env,
    # credential files, memory or descriptors. Bound the entire collection.
    local pam=${1:-/run/pam-session.log} proc=${2:-/proc} status=0
    timeout -k 1 4 /usr/bin/bash --noprofile --norc -s -- "$pam" "$proc" <<'STARTUP_DETAIL' || status=$?
set -uo pipefail
pam=$1 proc=$2 count=0 failed=0
emit_hex() {
    local kind=$1 file=$2 limit=$3 reader=${4:-head} data status=0
    if [[ -L $file || ( -e $file && ! -f $file ) ]]; then
        printf 'DIAGNOSTIC_HEX kind=%s status=refused\n' "$kind"
        return 1
    elif [[ ! -e $file ]]; then
        printf 'DIAGNOSTIC_HEX kind=%s status=missing\n' "$kind"
        return 0
    fi
    data=$(LC_ALL=C "$reader" -c "$limit" -- "$file" 2>/dev/null |
           LC_ALL=C od -An -v -tx1 2>/dev/null | LC_ALL=C tr -d ' \n' 2>/dev/null) || status=$?
    if [[ $status != 0 ]]; then
        printf 'DIAGNOSTIC_HEX kind=%s status=read-error code=%s\n' "$kind" "$status"
        return "$status"
    fi
    printf 'DIAGNOSTIC_HEX kind=%s status=read bytes=%s hex=%s\n' "$kind" "$((${#data}/2))" "$data"
}
emit_hex pam "$pam" 4096 tail || failed=1
for file in "$proc"/[0-9]*/comm; do
    [[ -f $file && ! -L $file ]] || continue
    read -r name < "$file" 2>/dev/null || continue
    case $name in pam-session|bash|openvt|timeout|loginctl|systemctl|logind-seat-pro*) ;;
        *) continue ;; esac
    pid=${file%/comm}; pid=${pid##*/}
    [[ $pid =~ ^[1-9][0-9]*$ ]] || continue
    if ((count>=8)); then
        printf 'DIAGNOSTIC_PROCESS status=limit count=8\n'
        break
    fi
    ((count+=1))
    emit_hex "process-$pid-cmdline" "$proc/$pid/cmdline" 1024 || failed=1
    emit_hex "process-$pid-status" "$proc/$pid/status" 1024 || failed=1
done
printf 'DIAGNOSTIC_PROCESS status=collected count=%s\n' "$count"
exit "$failed"
STARTUP_DETAIL
    printf 'DIAGNOSTIC_SNAPSHOT status=%s\n' "$status"
    return "$status"
}
for ((i=0;i<4;i++)); do
    sleep 25
    echo "OBSERVE independent snapshot=$i uptime=$(cat /proc/uptime)"
    while IFS= read -r line; do
        case $line in MemTotal:*|MemFree:*|MemAvailable:*|Slab:*|SUnreclaim:*|AnonPages:*) echo "OBSERVE memory $line";; esac
    done < /proc/meminfo
    observe_startup_detail || :
    timeout -k 1 5 systemctl list-jobs --no-pager || :
    timeout -k 1 5 systemctl --no-pager --full status systemd-logind dbus rog5-logind-fixture || :
    timeout -k 1 5 journalctl -b --no-pager -u systemd-logind -u dbus -n 45 || :
    for file in /proc/[0-9]*/comm; do
        read -r name < "$file" || continue
        case $name in
            systemd|systemd-logind|systemd-executor|dbus-broker|bash)
                p=${file%/comm};echo "OBSERVE process $p $name"
                cat "$p/wchan" "$p/syscall" || : ;;
        esac
    done
done
