#!/usr/bin/bash
# Function-only helper for the guarded VM PID1 preparation; guest RAM only.
font_cache_stage() {
    local stage=$1 started=$SECONDS status output
    shift
    printf 'OBSERVE font-cache stage=%s phase=begin\n' "$stage" >&2
    # Bound diagnostics independently of cache files: RLIMIT_FSIZE would also
    # truncate the legitimate >1 MiB Noto cache. A cap failure is an error.
    if output=$(set -o pipefail; "$@" 2>&1 | LC_ALL=C awk '
        BEGIN {remaining=1048576}
        {line=$0 "\n"; if (length(line)>remaining) exit 42;
         printf "%s",line; remaining-=length(line)}'); then status=0; else status=$?; fi
    printf '%s\n' "$output"
    printf 'OBSERVE font-cache stage=%s phase=end status=%s elapsed_seconds=%s\n' \
        "$stage" "$status" "$((SECONDS-started))" >&2
    return "$status"
}
font_config_identity() {
    sha256sum -- "$1" || return $?
    stat -c '%i %y %z %n' -- "$1" || return $?
    if [[ -L $1 ]]; then readlink -- "$1" || return $?; fi
}
prepare_font_config() {
    local defaults=$1 config=$2 hook=$3 source target input='' identity count=0
    local -A retained=() expected=()
    [[ $defaults == /* && $config == /* && $hook == /* && -d $defaults &&
       -d $config && ! -L $config && -f $hook && -r $hook && ! -L $hook ]] || return 1
    for source in "$defaults"/*.conf; do
        [[ -f $source && -r $source && -s $source && $source != *$'\n'* ]] || {
            echo 'FAIL packaged font default unavailable' >&2; return 1;
        }
        ((count+=1)); ((count<=128)) || return 1
        target=$config/${source##*/}
        if [[ -e $target ]]; then
            [[ -f $target && -r $target && -s $target ]] || return 1
            retained[$target]=$(font_config_identity "$target") || return $?
        elif [[ -L $target ]]; then
            echo 'FAIL dangling font configuration conflict' >&2; return 1
        else
            expected[$target]=$source
        fi
        # The packaged hook consumes paths relative to / and prepends / when
        # creating links. It leaves existing readable configuration untouched.
        input+=${source#/}$'\n'
    done
    ((count>0)) || return 1
    # bash -e prevents a later successful ln from hiding an earlier failure in
    # the packaged loop. Only the RAM destination is writable in the guest.
    (cd / && font_cache_stage config-restore timeout -k 1 10 bash -e -- "$hook" "$config" \
        <<< "${input%$'\n'}") || return $?
    for target in "${!expected[@]}"; do
        [[ -L $target && -f $target && -r $target ]] || return 1
        identity=$(readlink -- "$target") || return $?
        [[ $identity == "${expected[$target]}" ]] || {
            echo 'FAIL unexpected restored font configuration link' >&2; return 1;
        }
    done
    for target in "${!retained[@]}"; do
        identity=$(font_config_identity "$target") || return $?
        [[ $identity == "${retained[$target]}" ]] || {
            echo 'FAIL preexisting font configuration changed' >&2; return 1;
        }
    done
}
font_config_processed() {
    local defaults=$1 config=$2 output=$3 source line path
    local -A processed=()
    while IFS= read -r line; do
        if [[ $line == "+ $config/"* ]]; then
            path=${line#'+ '}; path=${path%%: *}; processed[$path]=1
        fi
    done <<< "$output"
    for source in "$defaults"/*.conf; do
        path=$config/${source##*/}
        [[ ${processed[$path]:-0} == 1 ]] || {
            echo 'FAIL packaged font default not processed' >&2; return 1;
        }
    done
}
font_cache_inventory() {
    local cache=$1 file target digest count=0 entries=0
    for file in "$cache"/*-le64.cache-*; do
        [[ -e $file || -L $file ]] || continue
        ((entries+=1))
        ((entries<=128)) || { echo 'FAIL font cache inventory bound' >&2; return 1; }
        if [[ -L $file ]]; then
            # Fontconfig2.18.3 creates older-version aliases to the same local
            # regular cache. Refuse dangling aliases or escape outside cache.
            target=$(readlink -e -- "$file") || return $?
            [[ $target == "$cache/"* && -f $target && -s $target && ! -L $target ]] || return 1
            printf 'alias %s %s\n' "$file" "$target"
        else
            [[ -f $file && -s $file && -r $file ]] || return 1
            digest=$(sha256sum -- "$file") || return $?
            printf '%s\n' "$digest"
            # Detect an identical-byte rewrite as well as content mutation.
            stat -c '%i %y %z %n' -- "$file" || return $?
            ((count+=1))
        fi
    done
    ((count>0)) || { echo 'FAIL no nonempty regular le64 font caches' >&2; return 1; }
}
font_cache_no_fallback() {
    local home=$1 path
    for path in "$home/.cache/fontconfig" "$home/.fontconfig"; do
        [[ ! -e $path && ! -L $path ]] || {
            echo 'FAIL unexpected per-user font cache fallback' >&2; return 1;
        }
    done
}
font_cache_loaded() {
    local cache=$1 fonts=$2 output=$3 line pending='' directory='' file
    local cache_line='^cache: ([^ /]+) \(dir: (.+)\)$'
    local valid_line='^FcCacheTimeValid dir "([^"]+)" cache checksum (-?[0-9]+(\.[0-9]+)?) dir checksum (-?[0-9]+(\.[0-9]+)?)$'
    local -A seen=()
    while IFS= read -r line; do
        if [[ $line =~ $cache_line ]]; then
            [[ -z $pending ]] || return 1
            pending=${BASH_REMATCH[1]}; directory=${BASH_REMATCH[2]}
            [[ $directory == "$fonts" || $directory == "$fonts/"* ]] || return 1
            [[ -f $cache/$pending && ! -L $cache/$pending ]] || return 1
        elif [[ $line =~ $valid_line ]]; then
            [[ -n $pending && ${BASH_REMATCH[1]} == "$directory" &&
               ${BASH_REMATCH[2]} == "${BASH_REMATCH[4]}" ]] || return 1
            seen[$pending]=1; pending=''
        fi
    done <<< "$output"
    [[ -z $pending ]] || return 1
    for file in "$cache"/*-le64.cache-*; do
        [[ ! -L $file ]] || continue
        [[ -f $file && ${seen[${file##*/}]:-0} == 1 ]] || return 1
    done
}
prepare_font_cache() {
    local cache=${1:-/var/cache/fontconfig} home=${2:-/run/mobile-home}
    local fonts=${3:-/usr/share/fonts} before after consumer line font='' matches=0
    local defaults=${4:-/usr/share/fontconfig/conf.default} config=${5:-/etc/fonts/conf.d}
    local hook=${6:-/usr/share/libalpm/scripts/40-fontconfig-config} configuration status
    [[ $cache == /* && $home == /* && $fonts == /* && ! -L $cache && -d $home && -d $fonts ]] || return 1
    font_cache_no_fallback "$home" || return $?
    prepare_font_config "$defaults" "$config" "$hook" || return $?
    mkdir -p -- "$cache" || return $?
    chmod 755 -- "$cache" || return $?
    font_cache_stage prepare timeout -k 1 20 fc-cache -s -v || return $?
    before=$(font_cache_inventory "$cache") || return $?
    # FcConfigGetCurrent in fc-conflist may initialize fonts. Validate only
    # after warming the system cache, then include it in no-fallback/no-write
    # checks along with the actual font-match consumer below.
    if configuration=$(font_cache_stage config-consume timeout -k 1 10 setpriv --reuid=1000 --regid=1000 \
        --clear-groups --no-new-privs env HOME="$home" XDG_CACHE_HOME="$home/.cache" \
        LANG=C.UTF-8 fc-conflist); then
        printf '%s\n' "$configuration"
    else
        status=$?; printf '%s\n' "$configuration"; return "$status"
    fi
    font_config_processed "$defaults" "$config" "$configuration" || return $?
    if consumer=$(font_cache_stage consume timeout -k 1 10 setpriv --reuid=1000 --regid=1000 \
        --clear-groups --no-new-privs env HOME="$home" XDG_CACHE_HOME="$home/.cache" \
        LANG=C.UTF-8 FC_DEBUG=16 fc-match -f 'FONT_FILE=%{file}\n' sans); then
        printf '%s\n' "$consumer"
    else
        local status=$?
        printf '%s\n' "$consumer"
        return "$status"
    fi
    while IFS= read -r line; do
        if [[ $line == FONT_FILE=* ]]; then
            ((matches+=1)); font=${line#FONT_FILE=}
        fi
    done <<< "$consumer"
    [[ $matches == 1 && $font == "$fonts/"* && -f $font && -r $font ]] || {
        echo 'FAIL expected one readable matched font under font directory' >&2; return 1;
    }
    # Resolve containment too: a lexically valid path must not escape via ../
    # or a symlink. Source fonts and their timestamps are never modified.
    font=$(readlink -e -- "$font") || return $?
    [[ $font == "$fonts/"* ]] || return 1
    # Exact2.18.3 cache-load diagnostics bind every retained regular cache to
    # a successfully matching source-directory timestamp checksum. Verbose
    # fc-cache alone is insufficient: its initialization can build first.
    font_cache_loaded "$cache" "$fonts" "$consumer" || {
        echo 'FAIL incomplete or mismatched font cache consumption diagnostics' >&2; return 1;
    }
    font_cache_no_fallback "$home" || return $?
    after=$(font_cache_inventory "$cache") || return $?
    [[ $before == "$after" ]] || { echo 'FAIL font caches changed during consumption' >&2; return 1; }
    printf 'PASS prepared font caches consumed by mobile UID; unchanged hashes and no fallback\n'
}
