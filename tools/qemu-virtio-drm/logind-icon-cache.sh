#!/bin/bash
# Function-only helpers; the production entry below is restricted to VM PID1.
generate_icon_caches() (
    local tree=$1 child= theme count=0 seen=0 status started=$SECONDS
    [[ $tree == /* && -d $tree && ! -L $tree ]] || return 1
    stop_icon_query() {
        if [[ -n $child ]]; then
            kill -TERM "$child" 2>/dev/null || :
            wait "$child" 2>/dev/null || :
        fi
    }
    trap stop_icon_query EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    for theme in "$tree"/*; do
        [[ -d $theme && -f $theme/index.theme ]] || continue
        [[ ! -L $theme && ! -L $theme/index.theme ]] || return 1
        ((seen+=1)); ((seen<=32)) || return 1
        # The caller owns this writable RAM overlay. Never retain stale caches
        # or follow a copied cache symlink into the immutable lower directory.
        rm -f -- "$theme/icon-theme.cache" || return $?
        timeout -k 1 10 gtk-update-icon-cache -q "$theme" & child=$!
        status=0; wait "$child" || status=$?; child=
        ((status==0)) || return "$status"
        # An inheritance-only alias (the packaged default theme) has no local
        # icon directories. The real GTK tool succeeds without creating a cache.
        # Allow that precise case; zero exit with missing output elsewhere fails.
        if [[ ! -e $theme/icon-theme.cache && ! -L $theme/icon-theme.cache ]] &&
            awk '
                /^[[:space:]]*[#;]/ || /^[[:space:]]*$/ {next}
                /^\[Icon Theme\][[:space:]]*$/ {section=1; next}
                /^\[/ {section=0}
                section && /^(ScaledDirectories|Directories)[[:space:]]*=/ {dirs=1}
                section && /^Inherits[[:space:]]*=[[:space:]]*[^[:space:]]/ {inherits=1}
                END {exit !(inherits && !dirs)}
            ' "$theme/index.theme"; then
            continue
        fi
        [[ -f $theme/icon-theme.cache && -s $theme/icon-theme.cache &&
           ! -L $theme/icon-theme.cache ]] || return 1
        timeout -k 1 10 gtk-update-icon-cache --validate "$theme" & child=$!
        status=0; wait "$child" || status=$?; child=
        ((status==0)) || return "$status"
        [[ ! $theme -nt $theme/icon-theme.cache ]] || return 1
        ((count+=1))
    done
    ((count>0)) || return 1
    printf 'PASS icon caches generated themes=%s elapsed_seconds=%s\n' "$count" "$((SECONDS-started))"
)

prepare_icon_mount() (
    local target=$1 root=$2 temporary= overlay=0 bound=0 complete=0 status options
    [[ $target == /* && $root == /* && -d $target && -d $root &&
       ! -L $target && ! -L $root ]] || return 1
    # overlay mount option paths must not contain separators or escapes.
    [[ $target != *[,:\\]* && $root != *[,:\\]* ]] || return 1
    if mountpoint -q -- "$target"; then return 1; else
        status=$?; [[ $status == 32 ]] || return "$status"
    fi
    # Serialize preparation without replacing any existing state.
    mkdir -- "$root/.icons.lock" || return $?
    cleanup_icon_mount() {
        local safe=1 probe
        if ((bound && !complete)); then
            if mountpoint -q -- "$target"; then
                umount -- "$target" || { safe=0; echo 'FAIL icon bind cleanup; guest must abort' >&2; }
            else
                probe=$?; [[ $probe == 32 ]] || safe=0
            fi
        fi
        if ((overlay)); then
            if mountpoint -q -- "$temporary/merged"; then
                umount -- "$temporary/merged" || { safe=0; echo 'FAIL icon overlay cleanup; guest must abort' >&2; }
            else
                probe=$?; [[ $probe == 32 ]] || safe=0
            fi
        fi
        # Never traverse a mount whose ordinary unmount failed.
        if ((!complete && safe)) && [[ -n $temporary ]]; then rm -rf -- "$temporary"; fi
        rmdir -- "$root/.icons.lock"
    }
    trap cleanup_icon_mount EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    temporary=$(mktemp -d "$root/.icons.XXXXXXXX") || return $?
    mkdir -- "$temporary/upper" "$temporary/work" "$temporary/merged" || return $?
    # Keep the 27 MB package tree in readonly 9P. Only cache files and parent
    # metadata copy up into RAM; cp -a of the entire tree exceeded 30 seconds.
    overlay=1
    mount -t overlay overlay -o "lowerdir=$target,upperdir=$temporary/upper,workdir=$temporary/work" \
        "$temporary/merged" || return $?
    generate_icon_caches "$temporary/merged" || return $?
    bound=1
    mount --bind "$temporary/merged" "$target" || return $?
    # Change VFS bind flags; a filesystem remount triggers overlay reconfigure
    # and the pinned kernel rejects it with 'No changes allowed'.
    mount -o remount,bind,ro,nodev,nosuid,noexec "$target" || return $?
    options=$(findmnt -n -o OPTIONS --target "$target") || return $?
    [[ ,$options, == *,ro,* ]] || return 1
    umount -- "$temporary/merged" || return $?
    overlay=0
    complete=1
    echo 'PASS GTK icon cache mounted read-only in guest RAM; session startup unqualified'
)

stage_icon_cache() {
    [[ $$ == 1 && $EUID == 0 && -d /sys/bus/virtio/devices ]] || return 1
    prepare_icon_mount /usr/share/icons /run/gtk-runtime
}
