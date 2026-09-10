#!/bin/sh
set -eu

# Keep this byte stream compatible with the rootfs identity accepted on
# 2026-07-29. Runtime-injected container filesystems and resolver/host files
# are excluded; every other regular-file content hash and path/type/mode/
# owner/symlink record is included.
find / -xdev \
	\( -path /dev -o -path /proc -o -path /sys -o -path /run \) -prune -o \
	! -path /etc/hostname ! -path /etc/hosts \
	! -path /etc/resolv.conf -type f -print0 \
	2>/dev/null |
	LC_ALL=C sort -z |
	xargs -0 sha256sum
find / -xdev \
	\( -path /dev -o -path /proc -o -path /sys -o -path /run \) -prune -o \
	! -path /etc/hostname ! -path /etc/hosts \
	! -path /etc/resolv.conf \
	\( -type f -o -type d -o -type l \) \
	-printf 'META\t%y\t%m\t%U\t%G\t%p\t%l\n' \
	2>/dev/null |
	LC_ALL=C sort
