#!/bin/sh
set -eu

[ "$(id -u)" -eq 0 ] || { echo 'ERROR run as root' >&2; exit 1; }
source_dir=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
backup=/root/rog5-backups/repo-runtime-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$backup"

backup_and_install() {
    source=$1
    target=$2
    [ ! -e "$target" ] || cp -p "$target" "$backup/$(basename "$target")"
    install -m 0755 "$source_dir/$source" "$target"
}

backup_and_install display-profile.sh /usr/local/bin/rog5-display-profile.sh
backup_and_install power-profile.sh /usr/local/bin/rog5-power-profile.sh
backup_and_install screen-toggle.sh /usr/local/bin/rog5-screen-toggle.sh
backup_and_install desktop-start.sh /usr/local/sbin/rog5-desktop-start
backup_and_install desktop-stop.sh /usr/local/sbin/rog5-desktop-stop
backup_and_install plasma-wayland-session.sh /usr/local/sbin/rog5-plasma-wayland-session

echo "PASS runtime tools installed; prior files backed up under $backup"
