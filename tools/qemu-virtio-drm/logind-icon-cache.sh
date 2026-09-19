#!/bin/bash
# Function-only preparation for isolated VM RAM; never changes package backing.
prepare_icon_tree() (
    local source=$1 root=$2 temporary= child= theme count=0 status started=$SECONDS
    [[ $source == /* && $root == /* && -d $source && -d $root &&
       ! -L $source && ! -L $root ]] || return 1
    [[ ! -e $root/icons && ! -L $root/icons ]] || return 1
    # One preparer owns publication; neither existing nor raced output is replaced.
    mkdir -- "$root/.icons.lock" || return $?
    cleanup_icon_tree() {
        if [[ -n $child ]]; then
            kill -TERM "$child" 2>/dev/null || :
            wait "$child" 2>/dev/null || :
        fi
        [[ -z $temporary ]] || rm -rf -- "$temporary"
        rmdir -- "$root/.icons.lock"
    }
    trap cleanup_icon_tree EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    temporary=$(mktemp -d "$root/.icons.XXXXXXXX") || return $?
    mkdir -- "$temporary/icons" || return $?
    run_icon_step() {
        local phase=$1 seconds=$2 began=$SECONDS
        shift 2
        timeout -k 1 "$seconds" "$@" & child=$!
        status=0; wait "$child" || status=$?; child=
        printf 'OBSERVE icon-cache phase=%s status=%s elapsed_seconds=%s\n' \
            "$phase" "$status" "$((SECONDS-began))"
        return "$status"
    }
    # Copy assets, not symlinks to an original-path alias which would recurse
    # after publication. This authenticated package tree is about 27 MB.
    run_icon_step copy 30 cp -a -- "$source/." "$temporary/icons/" || return $?
    chmod 755 "$temporary/icons" || return $?
    for theme in "$temporary/icons"/*; do
        [[ -d $theme && -f $theme/index.theme ]] || continue
        [[ ! -L $theme && ! -L $theme/index.theme ]] || return 1
        ((count+=1)); ((count<=32)) || return 1
        # Never follow a copied cache symlink or inherit stale package output.
        rm -f -- "$theme/icon-theme.cache" || return $?
        run_icon_step generate 10 gtk-update-icon-cache -q "$theme" || return $?
        [[ -f $theme/icon-theme.cache && -s $theme/icon-theme.cache &&
           ! -L $theme/icon-theme.cache ]] || return 1
        run_icon_step validate 10 gtk-update-icon-cache --validate "$theme" || return $?
        [[ ! $theme -nt $theme/icon-theme.cache ]] || return 1
    done
    ((count>0)) || return 1
    # GNU mv -n can return success when refusing a raced destination. Require
    # the source to disappear too, and never move inside an existing directory.
    mv -T -n -- "$temporary/icons" "$root/icons" || return $?
    [[ ! -e $temporary/icons ]] || return 1
    printf 'PASS icon cache tree prepared themes=%s elapsed_seconds=%s\n' "$count" "$((SECONDS-started))"
)

stage_icon_cache() (
    local target=/usr/share/icons root=/run/gtk-runtime status attempted=0 complete=0 options
    # Production entry is valid only in the isolated VM pre-PID1 fixture.
    [[ $$ == 1 && $EUID == 0 && -d /sys/bus/virtio/devices ]] || return 1
    if mountpoint -q -- "$target"; then return 1; else
        status=$?; [[ $status == 32 ]] || return "$status"
    fi
    prepare_icon_tree "$target" "$root" || return $?
    for theme in Adwaita AdwaitaLegacy hicolor; do
        [[ -s $root/icons/$theme/icon-theme.cache ]] || return 1
    done
    cleanup_icon_mount() {
        if ((attempted && !complete)) && mountpoint -q -- "$target"; then
            umount -- "$target" || echo 'FAIL icon cache mount cleanup; guest must abort' >&2
        fi
    }
    trap cleanup_icon_mount EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    attempted=1
    mount --bind "$root/icons" "$target" || return $?
    mount -o remount,bind,ro,nodev,nosuid,noexec "$target" || return $?
    options=$(findmnt -n -o OPTIONS --target "$target") || return $?
    [[ ,$options, == *,ro,* ]] || return 1
    complete=1
    echo 'PASS GTK icon cache mounted read-only in guest RAM; session startup unqualified'
)
