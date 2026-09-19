#!/usr/bin/bash
# Optional VM-only cache installation, before PID 1. Sourcing has no effects.
# Inputs are admitted by the host runner. /run and /etc must be private guest
# RAM, with no concurrent writer; this is not an arbitrary-filesystem installer.
prepare_vm_cache() (
    local kind=$1 prefix relative unit minimum maximum
    shift
    case $kind in
        linker) prefix=linker-cache; relative=ld.so.cache; unit=ldconfig; minimum=48; maximum=1048576 ;;
        hwdb) prefix=hwdb-cache; relative=udev/hwdb.bin; unit=systemd-hwdb-update; minimum=80; maximum=67108864 ;;
        *) return 1 ;;
    esac
    local run=${1:-/run} etc=${2:-/etc} expected size staged='' marker_staged='' status
    local dropin made_systemd=0 made_system=0 made_dropin=0 committed=0
    local cache marker guard parent
    [[ ! -e $run/$prefix && ! -L $run/$prefix &&
       ! -e $run/$prefix.sha256 && ! -L $run/$prefix.sha256 ]] && return 0
    [[ $run == /* && $etc == /* && $run != *[$'\n\r\t %:']* &&
       $etc != *[$'\n\r\t:']* && -d $run && ! -L $run &&
       -d $etc && ! -L $etc ]] || return 1
    if [[ $kind == hwdb ]]; then
        [[ -d $etc/udev && ! -L $etc/udev ]] || return 1
    fi
    cache=$etc/$relative
    marker=$run/$prefix.verified
    dropin=$etc/systemd/system/$unit.service.d
    guard=$dropin/50-rog5-cache.conf
    for parent in "$run/$prefix" "$run/$prefix.sha256"; do
        [[ -f $parent && ! -L $parent && -r $parent ]] || return 1
        [[ $(stat -c %h -- "$parent") == 1 ]] || return 1
    done
    size=$(stat -c %s -- "$run/$prefix") || return $?
    [[ $size =~ ^[0-9]+$ ]] && ((size >= minimum && size <= maximum)) || return 1
    [[ $(stat -c %s -- "$run/$prefix.sha256") == 65 ]] || return 1
    IFS= read -r expected < "$run/$prefix.sha256" || return 1
    [[ $expected =~ ^[[:xdigit:]]{64}$ ]] || return 1
    expected=${expected,,}
    [[ ! -e $cache && ! -L $cache && ! -e $marker && ! -L $marker &&
       ! -e $dropin && ! -L $dropin ]] || return 1
    for parent in "$etc/systemd" "$etc/systemd/system"; do
        [[ ! -L $parent && ( ! -e $parent || -d $parent ) ]] || return 1
    done
    local digest
    digest=$(sha256sum -- "$run/$prefix") || return $?
    [[ ${digest%% *} == "$expected" ]] || return 1
    staged=$(mktemp -d -- "$etc/.rog5-$prefix.XXXXXXXX") || return $?
    # Keep staging hardlinks until commit so cleanup can identify owned outputs
    # even when a signal lands between publication and the next shell command.
    trap 'status=$?; trap - EXIT; if (( ! committed )); then
        for parent in "$cache:cache" "$guard:guard" "$marker:marker"; do
            local_name=${parent##*:}; final_name=${parent%:*}
            source_name=$staged/$local_name
            [[ $local_name != marker ]] || source_name=$marker_staged/marker
            if [[ $final_name -ef $source_name ]]; then
                rm -f -- "$final_name" || status=1
            fi
        done
        (( ! made_dropin )) || rmdir -- "$dropin" || status=1
        (( ! made_system )) || rmdir -- "$etc/systemd/system" || status=1
        (( ! made_systemd )) || rmdir -- "$etc/systemd" || status=1
    fi
    rm -rf -- "$staged" || status=1
    [[ -z $marker_staged ]] || rm -rf -- "$marker_staged" || status=1
    exit "$status"' EXIT
    trap 'exit 143' TERM
    trap 'exit 130' INT
    # /run and /etc can be distinct tmpfs mounts. Each atomic publication
    # must use a staging inode on the destination filesystem.
    marker_staged=$(mktemp -d -- "$run/.rog5-$prefix.XXXXXXXX") || return $?
    cp -- "$run/$prefix" "$staged/cache" || return $?
    chmod 0644 -- "$staged/cache" || return $?
    digest=$(sha256sum -- "$staged/cache") || return $?
    [[ ${digest%% *} == "$expected" ]] || return 1
    ln -T -- "$staged/cache" "$cache" || return $?
    digest=$(sha256sum -- "$cache") || return $?
    [[ ${digest%% *} == "$expected" ]] || return 1
    if [[ $kind == hwdb ]]; then
        # Consume the published /etc cache before suppressing generation. The
        # modalias is synthetic: this is a database lookup, not a device probe.
        local query_status=0 answer
        (ulimit -f 16 || exit $?
         exec timeout -k 1 5 systemd-hwdb query usb:v046Dp0200d0000
        ) > "$staged/query" 2> "$staged/query-error" || query_status=$?
        ((query_status == 0)) || return "$query_status"
        [[ ! -s $staged/query-error ]] || return 1
        answer=$(cat -- "$staged/query") || return $?
        [[ $answer == $'ID_VENDOR_FROM_DATABASE=Logitech, Inc.\nID_MODEL_FROM_DATABASE=WingMan Extreme Joystick' ]] || return 1
    fi
    if [[ ! -d $etc/systemd ]]; then
        mkdir -- "$etc/systemd" || return $?
        made_systemd=1
    fi
    if [[ ! -d $etc/systemd/system ]]; then
        mkdir -- "$etc/systemd/system" || return $?
        made_system=1
    fi
    mkdir -- "$dropin" || return $?
    made_dropin=1
    printf '[Unit]\nConditionPathExists=!%s/%s.verified\n' "$run" "$prefix" > "$staged/guard" || return $?
    chmod 0644 -- "$staged/guard" || return $?
    ln -T -- "$staged/guard" "$guard" || return $?
    printf '%s\n' "$expected" > "$marker_staged/marker" || return $?
    chmod 0644 -- "$marker_staged/marker" || return $?
    # This last publication alone suppresses the selected cache generator. SIGKILL before this can
    # leave partial files, but cannot publish acceptance or skip the service.
    ln -T -- "$marker_staged/marker" "$marker" || return $?
    committed=1
)

# Public entry points remain optional and have no effects when inputs are absent.
prepare_linker_cache() { prepare_vm_cache linker "$@"; }
prepare_hwdb_cache() { prepare_vm_cache hwdb "$@"; }

prepare_boot_caches() {
    prepare_linker_cache "$@" || return $?
    prepare_hwdb_cache "$@" || return $?
}
