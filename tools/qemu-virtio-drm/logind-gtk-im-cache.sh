#!/bin/bash
# Derive GTK's package-hook output in private guest RAM. No display is opened.
prepare_gtk_im_cache() (
    local root=${1:-/run/gtk-runtime} temporary query_pid= status=0
    [[ $root == /* && -d $root && ! -L $root ]] || return 1
    [[ ! -e $root/immodules.cache && ! -L $root/immodules.cache ]] || {
        echo 'FAIL GTK input-method cache already exists' >&2; return 1;
    }
    temporary=$(mktemp -d "$root/.immodules.XXXXXXXX") || return $?
    cleanup_gtk_im_query() {
        if [[ -n $query_pid ]]; then
            kill -TERM "$query_pid" 2>/dev/null || :
            wait "$query_pid" 2>/dev/null || :
        fi
        rm -rf -- "$temporary"
    }
    trap cleanup_gtk_im_query EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    # The same packaged executable as gtk-query-immodules-3.0.hook; stdout
    # chooses a RAM destination instead of --update-cache on readonly /usr.
    (ulimit -f 128; export LC_ALL=C; exec timeout -k 1 10 gtk-query-immodules-3.0) \
        > "$temporary/cache" 2> "$temporary/errors" &
    query_pid=$!
    # wait is interruptible; the EXIT handler signals timeout, which forwards
    # cancellation to its separately owned process group and retains -k1.
    wait "$query_pid" || status=$?
    query_pid=
    if ((status)); then
        cat "$temporary/errors" >&2
        return "$status"
    fi
    if [[ -s $temporary/errors || ! -s $temporary/cache ]]; then
        cat "$temporary/errors" >&2
        echo 'FAIL GTK input-method discovery incomplete' >&2; return 1;
    fi
    # Require the Wayland entry under its actual module stanza. Merely finding
    # the word wayland elsewhere does not establish a usable cache record.
    awk '
        /^#/ || /^[[:space:]]*$/ {next}
        /^"\// {module=$0; next}
        /^"wayland" "Wayland" "gtk30" "\/usr\/share\/locale" ""[[:space:]]*$/ {
            if (module ~ /^"\/usr\/lib\/gtk-3.0\/3.0.0\/immodules\/im-wayland.so"[[:space:]]*$/) count++
        }
        END {exit count != 1}
    ' "$temporary/cache" || {
        echo 'FAIL GTK Wayland input-method registration missing or ambiguous' >&2; return 1;
    }
    chmod 644 "$temporary/cache" || return $?
    # No existing cache is replaced, even if another preparer wins this race.
    ln -T -- "$temporary/cache" "$root/immodules.cache" || return $?
    echo 'PASS GTK input-method cache prepared in RAM; client selection unqualified'
)

# Optional, inventoried VM payload override; caller is the isolated guest PID1.
# Neither an absent contract nor a successful cache query authorizes an override.
stage_gtk_im_override() {
    stage_vm_library_override GTK "${1:-/run/session}" "${2:-/usr}"
}
stage_wayland_debug_override() {
    stage_vm_library_override Wayland "${1:-/run/session}" "${2:-/usr}"
}
stage_vm_library_override() (
    local kind=$1 session=$2 system=$3 relative contract_name
    # A closed set of exact paths, never an arbitrary payload-selected library.
    case $kind in
        GTK) relative=lib/gtk-3.0/3.0.0/immodules/im-wayland.so
             contract_name=gtk-im-override.sha256 ;;
        Wayland) relative=lib/libwayland-client.so.0.26.0
                 contract_name=wayland-debug-override.sha256 ;;
        *) return 1 ;;
    esac
    local contract=$session/usr/share/rog5-denial/$contract_name
    local source=$session/usr/$relative target=$system/$relative
    local pair old new actual options probe_status attempted=0 complete=0
    if [[ ! -e $contract && ! -L $contract && ! -e $source && ! -L $source ]]; then
        return 0
    fi
    [[ $session == /* && $system == /* && -d $session && -d $system &&
       ! -L $session && ! -L $system ]] || return 1
    [[ -f $target && ! -L $target ]] || return 1
    # The immutable mapped baseline legitimately shares its backing inode.
    # Only the newly extracted contract/replacement must have one link.
    for actual in "$contract" "$source"; do
        [[ -f $actual && ! -L $actual && $(stat -c %h -- "$actual") == 1 ]] || {
            echo "FAIL $kind override input is not a single-link regular file" >&2; return 1;
        }
    done
    [[ $(stat -c %s -- "$contract") -le 130 ]] || return 1
    pair=$(cat -- "$contract") || return $?
    [[ $pair =~ ^[0-9a-f]{64}\ [0-9a-f]{64}$ ]] || return 1
    read -r old new <<< "$pair"
    actual=$(sha256sum -- "$target") || return $?
    [[ ${actual%% *} == "$old" ]] || { echo "FAIL $kind baseline module identity" >&2; return 1; }
    actual=$(sha256sum -- "$source") || return $?
    [[ ${actual%% *} == "$new" ]] || { echo "FAIL $kind override module identity" >&2; return 1; }
    # Refuse an existing file mount; an interrupted attempt may only undo ours.
    if mountpoint -q -- "$target"; then
        return 1
    else
        probe_status=$?
        [[ $probe_status == 32 ]] || return "$probe_status"
    fi
    cleanup_gtk_override() {
        if ((attempted && !complete)) && mountpoint -q -- "$target"; then
            umount -- "$target" || echo "FAIL $kind override cleanup; guest must abort" >&2
        fi
    }
    trap cleanup_gtk_override EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    attempted=1
    mount --bind "$source" "$target" || return $?
    mount -o remount,bind,ro "$target" || return $?
    options=$(findmnt -n -o OPTIONS --target "$target") || return $?
    [[ ,$options, == *,ro,* ]] || { echo "FAIL $kind override is not read-only" >&2; return 1; }
    actual=$(sha256sum -- "$target") || return $?
    [[ ${actual%% *} == "$new" ]] || return 1
    complete=1
    printf 'PASS VM-only %s override original=%s replacement=%s read-only\n' "$kind" "$old" "$new"
)
