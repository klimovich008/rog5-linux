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
    ln -- "$temporary/cache" "$root/immodules.cache" || return $?
    echo 'PASS packaged GTK input-method cache prepared in RAM; client selection unqualified'
)
