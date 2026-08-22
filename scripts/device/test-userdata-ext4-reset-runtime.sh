#!/bin/sh
set -eu

for command in dumpe2fs e2fsck mkfs.ext4 mktemp truncate; do
	command -v "$command" >/dev/null || {
		echo "FAIL missing command: $command" >&2
		exit 1
	}
done

fixture=$(mktemp)
trap 'rm -f -- "$fixture"' EXIT HUP INT TERM
truncate -s 64M "$fixture"
uuid=0892bacf-3e02-41b0-84a4-5f05c2df7ce5

mkfs.ext4 -q -F -b 4096 -L rog5-linux -U "$uuid" -m 0 \
	-O ^casefold,^encrypt,^verity,^quota,^project \
	-E lazy_itable_init=0,lazy_journal_init=0 "$fixture"
e2fsck -fn "$fixture" >/dev/null
header=$(dumpe2fs -h "$fixture" 2>/dev/null)

printf '%s\n' "$header" | grep -Fq "Filesystem UUID:          $uuid"
printf '%s\n' "$header" | grep -Fq 'Filesystem volume name:   rog5-linux'
printf '%s\n' "$header" | grep -Fq 'Reserved block count:     0'
features=$(printf '%s\n' "$header" |
	sed -n 's/^Filesystem features:[[:space:]]*//p')
for forbidden in casefold encrypt verity quota project; do
	! printf '%s\n' "$features" | grep -Eq "(^| )$forbidden( |$)" || {
		echo "FAIL forbidden ext4 feature survived: $forbidden" >&2
		exit 1
	}
done

echo 'PASS exact userdata ext4 reset options create the reviewed filesystem identity'
