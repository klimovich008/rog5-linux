#!/usr/bin/env bash
# Offline VM fixture: seatd mediation, not logind/login/lock-screen qualification.
nonroot_guest_guard() {
    local cmdline
    read -r cmdline < /proc/cmdline
    [[ " $cmdline " == *' rog5.virtual_drm=1 '* && -d /sys/bus/virtio/devices ]]
}
nonroot_accounts() {
    # Pure transformation seam: reject both name and numeric-ID conflicts.
    local passwd=$1 group=$2 destination=$3
    awk -F: '$1 == "mobile" || $3 == "1000" { exit 1 }' "$passwd" || return 1
    awk -F: '$1 == "mobile" || $3 == "1000" { exit 1 }' "$group" || return 1
    cp "$passwd" "$destination/passwd" || return 1
    cp "$group" "$destination/group" || return 1
    printf 'mobile:x:1000:1000:VM fixture:/run/mobile-home:/usr/bin/bash\n' >> "$destination/passwd"
    printf 'mobile:x:1000:\n' >> "$destination/group"
    chmod 644 "$destination/passwd" "$destination/group"
}
nonroot_prepare() {
    nonroot_guest_guard && [[ $EUID == 0 ]] || return 1
    # Both account files are bind mounted from RAM; retained /etc is read-only.
    mkdir -m 700 /run/mobile-accounts /run/mobile-home || return 1
    nonroot_accounts /etc/passwd /etc/group /run/mobile-accounts || return 1
    mount --bind /run/mobile-accounts/passwd /etc/passwd || return 1
    mount --bind /run/mobile-accounts/group /etc/group || return 1
    export HOME=/run/mobile-home USER=mobile LOGNAME=mobile
    export XDG_RUNTIME_DIR=/run/user/1000
    mkdir -p "$XDG_RUNTIME_DIR" || return 1
    chown 1000:1000 "$HOME" "$XDG_RUNTIME_DIR" || return 1
    chmod 700 "$HOME" "$XDG_RUNTIME_DIR" || return 1
    echo 'OBSERVE non-root VM fixture uses seatd; logind/authentication NOT RUN'
}
nonroot_run() {
    exec setpriv --reuid=1000 --regid=1000 --clear-groups --bounding-set=-all \
        --inh-caps=-all --ambient-caps=-all --no-new-privs "$@"
}
nonroot_identity() {
    local role=$1 status=${2:-/proc/$BASHPID/status} key value
    local uid='' gid='' groups=missing nnp='' caps=0
    local -a values
    [[ $role == denial || $role == bus || $role == foot || $role == mousepad ]] || return 1
    while IFS=: read -r key value; do
        read -ra values <<< "$value"
        case $key in
            Uid) uid="${values[*]}" ;;
            Gid) gid="${values[*]}" ;;
            Groups) groups="${values[*]}" ;;
            NoNewPrivs) nnp="${values[*]}" ;;
            CapInh|CapPrm|CapEff|CapBnd|CapAmb)
                [[ ${values[*]} =~ ^0+$ ]] || return 1
                caps=$((caps+1)) ;;
        esac
    done < "$status"
    [[ $uid == '1000 1000 1000 1000' && $gid == '1000 1000 1000 1000' &&
       -z $groups && $nnp == 1 && $caps == 5 ]] || return 1
    printf 'OBSERVE nonroot exec=%s uid=1000 gid=1000 groups=none caps=zero nnp=1\n' "$role"
}
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    set -euo pipefail
    nonroot_guest_guard
    case ${1:-} in
        exec)
            [[ $# -ge 3 ]]
            role=$2; shift 2
            nonroot_identity "$role"
            exec "$@" ;;
        launch)
            [[ $# == 2 && ( $2 == foot || $2 == mousepad ) ]]
            record=$(nonroot_identity "$2")
            /run/evidence-writer record "$record" > /run/launcher-evidence/events
            exec /usr/bin/bash /run/launcher-apps.sh launch "$2" ;;
        *) exit 2 ;;
    esac
fi
