#!/bin/sh
# Offline tests of steam-arm64 (environment given to the client) and
# steam-fex-rootfs-install (publication never leaves no root; one run at a
# time), with fake tools on PATH.
set -eu
here=$(CDPATH='' cd -- "$(dirname "$0")" && pwd)
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
fail() { echo "FAIL $*"; exit 1; }
export ROG5_FEX_LOCK=$t/fex.lock

# --- steam-arm64 --------------------------------------------------------------
s=$t/Steam; mkdir -p "$s/steamrtarm64" "$t/home"
cat >"$s/steamrtarm64/steam" <<EOF
#!/bin/sh
n=\$(cat $t/runs 2>/dev/null || echo 0); echo \$((n + 1)) >$t/runs
echo "\$LD_LIBRARY_PATH|\${SYSTEM_LD_LIBRARY_PATH-unset}|\$*" >>$t/env
[ "\$n" -ge 1 ] || exit 42
EOF
chmod +x "$s/steamrtarm64/steam"
HOME=$t/home STEAMROOT=$s LD_LIBRARY_PATH=/usr/lib/caller sh "$here/steam-arm64" -silent 2>/dev/null
[ "$(cat "$t/runs")" = 2 ] || fail "steam-arm64: exit 42 did not restart the client once"
exp="$s/steamrtarm64:/usr/lib/caller|/usr/lib/caller|-noverifyfiles -silent"
[ "$(sed -n 1p "$t/env")" = "$exp" ] || fail "steam-arm64: client environment: $(sed -n 1p "$t/env")"
[ "$(sed -n 2p "$t/env")" = "$exp" ] || fail "steam-arm64: restart changed the environment: $(sed -n 2p "$t/env")"
rm -f "$t/runs" "$t/env"
HOME=$t/home STEAMROOT=$s env -u LD_LIBRARY_PATH sh "$here/steam-arm64" 2>/dev/null
[ "$(sed -n 1p "$t/env")" = "$s/steamrtarm64||-noverifyfiles" ] || fail "steam-arm64: empty caller path: $(sed -n 1p "$t/env")"
echo "PASS steam-arm64: steamrtarm64 only for the client, SYSTEM_LD_LIBRARY_PATH = caller's"

# --- steam-fex-rootfs-install -------------------------------------------------
b=$t/bin; mkdir -p "$b"
cat >"$b/id" <<'EOF'
#!/bin/sh
echo 0
EOF
cat >"$b/curl" <<'EOF'
#!/bin/sh
while [ $# -gt 1 ]; do [ "$1" = -o ] && out=$2; shift; done
case $out in
*links.json) echo '{"v1": {"ArchLinux (SquashFS)": {"URL": "https://example.invalid/r.sqsh", "Hash": "abc"}}}' >"$out" ;;
*) echo image >"$out" ;;
esac
EOF
cat >"$b/xxhsum" <<'EOF'
#!/bin/sh
echo "XXH3_abc  $2"
EOF
cat >"$b/unsquashfs" <<EOF
#!/bin/sh
[ ! -e $t/unsquash-fails ] || exit 1
while [ \$# -gt 1 ]; do [ "\$1" = -d ] && d=\$2; shift; done
mkdir -p "\$d"; echo '{}' >"\$d/graphics_provider.json"; echo new >"\$d/marker"
EOF
cat >"$b/pgrep" <<EOF
#!/bin/sh
[ -e $t/steam-running ]
EOF
chmod +x "$b"/*
root=$t/guestos/fex-mesa cache=$t/cache
run() { PATH=$b:$PATH ROG5_FEX_ROOT=$root ROG5_FEX_CACHE=$cache sh "$here/steam-fex-rootfs-install" >/dev/null 2>"$t/err"; }

run || fail "fex: fresh install failed: $(cat "$t/err")"
[ "$(cat "$root/marker")" = new ] || fail "fex: fresh install has no root"

echo old >"$root/marker"
run || fail "fex: replace failed: $(cat "$t/err")"
[ "$(cat "$root/marker")" = new ] && [ ! -e "$root.new" ] && [ ! -e "$root.old" ] ||
	fail "fex: replace (exchange) left $(ls "$t/guestos")"

echo old >"$root/marker"; : >"$t/unsquash-fails"
run && fail "fex: a failed unpack reported success"
[ "$(cat "$root/marker")" = old ] || fail "fex: a failed unpack touched the working root"
rm "$t/unsquash-fails"

# no RENAME_EXCHANGE: fall back to two renames
cat >"$b/mv" <<'EOF'
#!/bin/sh
for a; do [ "$a" = --exchange ] && { echo "mv: unrecognized option '--exchange'" >&2; exit 1; }; done
exec /bin/mv "$@"
EOF
chmod +x "$b/mv"
echo old >"$root/marker"
run || fail "fex: fallback replace failed: $(cat "$t/err")"
[ "$(cat "$root/marker")" = new ] && [ ! -e "$root.old" ] && [ ! -e "$root.new" ] ||
	fail "fex: fallback replace left $(ls "$t/guestos")"
rm "$b/mv"

# an interrupted fallback left only the old root under .old
mv "$root" "$root.old"; echo old >"$root.old/marker"; : >"$t/unsquash-fails"
run || true
[ "$(cat "$root/marker")" = old ] || fail "fex: interrupted replace not repaired"
rm "$t/unsquash-fails"

: >"$t/steam-running"
run && fail "fex: installed while Steam runs"
rm "$t/steam-running"

exec 8>"$cache/install.lock"; flock -n 8
run && fail "fex: second concurrent run was not refused"
grep -q 'another install is running' "$t/err" || fail "fex: lock message: $(cat "$t/err")"
exec 8>&-

# Steam started through steam-arm64 holds the root lock shared
exec 8<"$ROG5_FEX_LOCK"; flock -s -n 8
run && fail "fex: installed while steam-arm64 holds the root lock"
exec 8<&-
exec 8<"$ROG5_FEX_LOCK"; flock -x -n 8
rm -f "$t/runs" "$t/env"
HOME=$t/home STEAMROOT=$s sh "$here/steam-arm64" 2>/dev/null && fail "steam-arm64 started during a root install"
[ ! -e "$t/runs" ] || fail "steam-arm64 ran the client during a root install"
exec 8<&-
echo "PASS steam-fex-rootfs-install: exchange, fallback, repair, locks, Steam running"
