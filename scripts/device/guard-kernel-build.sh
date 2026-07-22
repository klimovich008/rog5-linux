#!/bin/sh
set -eu

build_pid=${1:?usage: guard-kernel-build.sh BUILD_PID}
limit=${THERMAL_LIMIT_DECIC:-450}
interval=${INTERVAL_SECONDS:-10}
temp_path=${TEMP_PATH:-/sys/class/power_supply/battery/temp}

while kill -0 "$build_pid" 2>/dev/null; do
    temperature=$(cat "$temp_path")
    case $temperature in
        ''|*[!0-9]*) echo "ERROR invalid battery temperature: $temperature" >&2; exit 1 ;;
    esac
    if [ "$temperature" -ge "$limit" ]; then
        echo "STOP battery temperature ${temperature} reached limit ${limit}" >&2
        for child in $(pgrep -P "$build_pid" 2>/dev/null || true); do
            kill -TERM "$child" 2>/dev/null || true
        done
        sleep 2
        kill -TERM "$build_pid" 2>/dev/null || true
        exit 2
    fi
    sleep "$interval"
done

echo 'PASS build exited below the thermal limit'
