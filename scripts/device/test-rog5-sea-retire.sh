#!/bin/sh
# Offline test of rog5-sea-retire --stdin with a fake soft_offline_page file.
set -eu
here=$(CDPATH='' cd -- "$(dirname "$0")" && pwd)
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
export ROG5_SEA_SOFT_OFFLINE=$t/soft_offline_page ROG5_SEA_RUN=$t/run ROG5_SEA_KMSG=$t/kmsg ROG5_SEA_MAX_BLOCKS=2
run() { "$here/rog5-sea-retire" --stdin; }
fail() { echo "FAIL $*"; exit 1; }

# One ifetch SEA: the whole 4 MiB block around it, once.
printf '%s\n' \
	'rog5-sea: exe[72905] cpu7 ifetch pc aaaadfe8da70 far aaaadfe8da70 esr 82000010 fsc 0x10 pfn 0x34bc8d order 9 anon lru' \
	'rog5-sea: exe[72905] cpu7 ifetch pc aaaadfe914f8 far aaaadfe914f8 esr 82000010 fsc 0x10 pfn 0x34bc91 order 9 anon lru' | run
[ "$(wc -l <"$t/soft_offline_page")" = 1024 ] || fail "block size $(wc -l <"$t/soft_offline_page")"
[ "$(head -n 1 "$t/soft_offline_page")" = 0x34bc00000 ] || fail "first $(head -n 1 "$t/soft_offline_page")"
[ "$(tail -n 1 "$t/soft_offline_page")" = 0x34bfff000 ] || fail "last $(tail -n 1 "$t/soft_offline_page")"
grep -q 'block 0x34bc00-0x34bfff (1024 retired, 0 not movable)' "$t/kmsg" || fail "log: $(cat "$t/kmsg")"

# Ignored: data aborts, other FSCs, no page, other lines.
printf '%s\n' \
	'rog5-sea: a[1] cpu0 data pc 1 far 2 esr 92000010 fsc 0x10 pfn 0x100000 order 0 anon lru' \
	'rog5-sea: a[1] cpu0 ifetch pc 1 far 1 esr 82000011 fsc 0x11 pfn 0x100000 order 0 anon lru' \
	'rog5-sea: a[1] cpu0 ifetch pc 1 far 1 esr 82000010 fsc 0x10 pfn 0 order 0 no-page' \
	'rog5-sea: a[1] cpu0 ifetch pc 1 far 1 esr 82000010 fsc 0x10 pfn 0x0 order 0 no-page' \
	'rog5-sea: soft_offline pfn 0x100000 -> 0, retrying' \
	'usb 1-1: new high-speed USB device' | run
[ "$(wc -l <"$t/soft_offline_page")" = 1024 ] || fail 'retired a block for an ignored line'

# Second block, then the budget (2) stops a third.
echo 'rog5-sea: FEX[1] cpu7 ifetch pc 3 far 3 esr 82000010 fsc 0x10 pfn 0x34b635 order 9 anon lru' | run
[ "$(wc -l <"$t/soft_offline_page")" = 2048 ] || fail 'second block'
grep -qx 0x34b400000 "$t/soft_offline_page" || fail 'second block start'
echo 'rog5-sea: FEX[1] cpu7 ifetch pc 3 far 3 esr 82000010 fsc 0x10 pfn 0x200000 order 0 anon lru' | run
[ "$(wc -l <"$t/soft_offline_page")" = 2048 ] || fail 'budget exceeded'
grep -q 'budget of 2 blocks used' "$t/kmsg" || fail 'budget not logged'

# A write the kernel refuses counts as not movable.
rm -rf "$t/run" "$t/soft_offline_page"; mkdir "$t/soft_offline_page"
echo 'rog5-sea: FEX[1] cpu7 ifetch pc 3 far 3 esr 82000010 fsc 0x10 pfn 0x300400 order 0 anon lru' | run
grep -q 'block 0x300400-0x3007ff (0 retired, 1024 not movable)' "$t/kmsg" || fail 'refused writes'
echo 'PASS rog5-sea-retire'
