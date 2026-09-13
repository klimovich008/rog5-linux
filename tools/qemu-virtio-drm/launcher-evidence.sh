#!/usr/bin/env bash
# Sourced by the virtual guest only; one FIFO reader owns the serial port.
launcher_evidence_prepare() {
    launcher_guest_guard || return 1
    local state=${1:-/run/launcher-evidence} sink=${2:-/dev/vport0p1} writer=${3:-/run/evidence-writer}
    [[ -x $writer && ( -c $sink || -p $sink ) ]] || return 1
    mkdir -m 700 "$state" || return 1
    mkfifo -m 600 "$state/events" || return 1
    exec {launcher_evidence_keep}<>"$state/events"
    (
        exec {launcher_evidence_keep}>&-
        exec cat < "$state/events" > "$sink"
    ) &
    launcher_evidence_pid=$!
}
launcher_evidence_finish() {
    local attempt result=0
    exec {launcher_evidence_keep}>&-
    for ((attempt=0; attempt<50; attempt++)); do
        kill -0 "$launcher_evidence_pid" 2>/dev/null || break
        sleep .02
    done
    if kill -0 "$launcher_evidence_pid" 2>/dev/null; then
        kill "$launcher_evidence_pid" 2>/dev/null || true
        result=1
    fi
    wait "$launcher_evidence_pid" || result=1
    [[ $result == 0 ]] || echo 'FAIL launcher evidence drain' >&2
    return "$result"
}
