#!/usr/bin/bash
# Optional VM-only cache installation, before PID 1. Sourcing has no effects.
# Inputs are admitted by the host runner. /run and /etc must be private guest
# RAM, with no concurrent writer; this is not an arbitrary-filesystem installer.
prepare_linker_cache() (
    local run=${1:-/run} etc=${2:-/etc} expected size staged='' marker_staged='' status
    local dropin made_systemd=0 made_system=0 made_dropin=0 committed=0
    local cache marker guard parent
    [[ ! -e $run/linker-cache && ! -L $run/linker-cache &&
       ! -e $run/linker-cache.sha256 && ! -L $run/linker-cache.sha256 ]] && return 0
    [[ $run == /* && $etc == /* && $run != *[$'\n\r\t %:']* &&
       $etc != *[$'\n\r\t:']* && -d $run && ! -L $run &&
       -d $etc && ! -L $etc ]] || return 1
    cache=$etc/ld.so.cache
    marker=$run/linker-cache.verified
    dropin=$etc/systemd/system/ldconfig.service.d
    guard=$dropin/50-rog5-cache.conf
    for parent in "$run/linker-cache" "$run/linker-cache.sha256"; do
        [[ -f $parent && ! -L $parent && -r $parent ]] || return 1
        [[ $(stat -c %h -- "$parent") == 1 ]] || return 1
    done
    size=$(stat -c %s -- "$run/linker-cache") || return $?
    [[ $size =~ ^[0-9]+$ ]] && ((size >= 48 && size <= 1048576)) || return 1
    [[ $(stat -c %s -- "$run/linker-cache.sha256") == 65 ]] || return 1
    IFS= read -r expected < "$run/linker-cache.sha256" || return 1
    [[ $expected =~ ^[[:xdigit:]]{64}$ ]] || return 1
    expected=${expected,,}
    [[ ! -e $cache && ! -L $cache && ! -e $marker && ! -L $marker &&
       ! -e $dropin && ! -L $dropin ]] || return 1
    for parent in "$etc/systemd" "$etc/systemd/system"; do
        [[ ! -L $parent && ( ! -e $parent || -d $parent ) ]] || return 1
    done
    local digest
    digest=$(sha256sum -- "$run/linker-cache") || return $?
    [[ ${digest%% *} == "$expected" ]] || return 1
    staged=$(mktemp -d -- "$etc/.rog5-linker-cache.XXXXXXXX") || return $?
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
    marker_staged=$(mktemp -d -- "$run/.rog5-linker-cache.XXXXXXXX") || return $?
    cp -- "$run/linker-cache" "$staged/cache" || return $?
    chmod 0644 -- "$staged/cache" || return $?
    digest=$(sha256sum -- "$staged/cache") || return $?
    [[ ${digest%% *} == "$expected" ]] || return 1
    ln -T -- "$staged/cache" "$cache" || return $?
    digest=$(sha256sum -- "$cache") || return $?
    [[ ${digest%% *} == "$expected" ]] || return 1
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
    printf '[Unit]\nConditionPathExists=!%s/linker-cache.verified\n' "$run" > "$staged/guard" || return $?
    chmod 0644 -- "$staged/guard" || return $?
    ln -T -- "$staged/guard" "$guard" || return $?
    printf '%s\n' "$expected" > "$marker_staged/marker" || return $?
    chmod 0644 -- "$marker_staged/marker" || return $?
    # This last publication alone suppresses ldconfig. SIGKILL before this can
    # leave partial files, but cannot publish acceptance or skip the service.
    ln -T -- "$marker_staged/marker" "$marker" || return $?
    committed=1
)
