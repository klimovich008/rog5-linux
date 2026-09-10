#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
shutdown=$repo/initramfs/network-root-shutdown
stage=$(mktemp -d)
trap 'rmdir "$stage"' EXIT INT TERM

[ -x "$shutdown" ]
sh -n "$shutdown"

if ! command -v unshare >/dev/null ||
	! unshare --user --map-root-user --mount true 2>/dev/null; then
	echo 'SKIP unprivileged mount namespaces are unavailable'
	exit 0
fi

unshare --user --map-root-user --mount sh -eu -s -- "$stage" <<'EOF'
stage=$1
mount --make-rprivate /
mount -t tmpfs tmpfs "$stage"
mkdir -p "$stage/lower" "$stage/state/upper" "$stage/state/work" \
	"$stage/merged" "$stage/exitrd/oldroot" "$stage/exitrd/oldsys"
mount -t tmpfs tmpfs "$stage/lower"
mount -t tmpfs tmpfs "$stage/state"
mkdir -p "$stage/state/upper" "$stage/state/work"
printf 'lower\n' >"$stage/lower/probe"
mount -t overlay overlay \
	-o "lowerdir=$stage/lower,upperdir=$stage/state/upper,workdir=$stage/state/work" \
	"$stage/merged"
mkdir -p "$stage/merged/.rog5/root-ro" "$stage/merged/.rog5/state"
mount --move "$stage/lower" "$stage/merged/.rog5/root-ro"
mount --move "$stage/state" "$stage/merged/.rog5/state"
mount --move "$stage/merged" "$stage/exitrd/oldroot"

mkdir -p "$stage/exitrd/oldsys/root-ro" "$stage/exitrd/oldsys/state"
mount --move "$stage/exitrd/oldroot/.rog5/root-ro" \
	"$stage/exitrd/oldsys/root-ro"
mount --move "$stage/exitrd/oldroot/.rog5/state" \
	"$stage/exitrd/oldsys/state"
umount "$stage/exitrd/oldroot"
umount "$stage/exitrd/oldsys/state"
umount "$stage/exitrd/oldsys/root-ro"

! mountpoint -q "$stage/exitrd/oldroot"
! mountpoint -q "$stage/exitrd/oldsys/state"
! mountpoint -q "$stage/exitrd/oldsys/root-ro"
umount "$stage"
EOF

echo 'PASS exitrd move order cleanly unmounts overlay root before its backing filesystems'
