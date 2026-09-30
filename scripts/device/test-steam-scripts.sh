#!/bin/sh
# Offline tests of steam-arm64 (environment given to the client, drag shim
# build and preload),
# steam-fex-rootfs-install (publication never leaves no root; one run at a
# time) and steam-fex-turnip-8bit (checked replace, backup, restore, reapply
# on a new root), with fake tools on PATH.
set -eu
here=$(CDPATH='' cd -- "$(dirname "$0")" && pwd)
t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
fail() { echo "FAIL $*"; exit 1; }
export ROG5_FEX_LOCK=$t/fex.lock ROG5_STEAM_DRAG=0 ROG5_FEX_TURNIP_STATE=$t/turnip-state

# --- steam-arm64 --------------------------------------------------------------
s=$t/Steam; mkdir -p "$s/steamrtarm64" "$t/home"
cat >"$s/steamrtarm64/steam" <<EOF
#!/bin/sh
n=\$(cat $t/runs 2>/dev/null || echo 0); echo \$((n + 1)) >$t/runs
echo "\$LD_LIBRARY_PATH|\${SYSTEM_LD_LIBRARY_PATH-unset}|\$*" >>$t/env
echo "\${LD_PRELOAD-unset}" >$t/preload
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

# --- steam-arm64: title-bar drag shim ------------------------------------------
cc=$t/cc; cat >"$cc" <<EOF
#!/bin/sh
echo "\$*" >>$t/cc.args
[ ! -e $t/cc-fails ] || exit 1
while [ \$# -gt 1 ]; do [ "\$1" = -o ] && out=\$2; shift; done
echo so >"\$out"
EOF
chmod +x "$cc"
src=$t/drag.c; echo 'int x;' >"$src"
drag() { rm -f "$t/runs"; ROG5_STEAM_DRAG=1 ROG5_STEAM_DRAG_SRC=$src CC=$cc XDG_CACHE_HOME=$t/cache2 HOME=$t/home STEAMROOT=$s LD_PRELOAD=${1-} sh "$here/steam-arm64" 2>"$t/err"; }
so=$t/cache2/rog5/steam-arm64-drag.so
drag
[ "$(cat "$so")" = so ] && [ "$(cat "$t/preload")" = "$so" ] || fail "drag: shim not built/preloaded: $(cat "$t/preload") $(cat "$t/err")"
grep -q -- "--version-script=$so.map" "$t/cc.args" && [ ! -e "$so.map" ] || fail "drag: build arguments / leftovers: $(cat "$t/cc.args")"
: >"$t/cc.args"; drag /usr/lib/other.so
[ ! -s "$t/cc.args" ] && [ "$(cat "$t/preload")" = "$so:/usr/lib/other.so" ] || fail "drag: rebuilt an up-to-date shim or lost LD_PRELOAD: $(cat "$t/preload")"
touch -d '+1 minute' "$src"; : >"$t/cc-fails"; drag
grep -q 'could not build' "$t/err" && [ "$(cat "$so")" = so ] && [ ! -e "$so.new" ] || fail "drag: failed rebuild: $(cat "$t/err")"
rm -rf "$t/cache2"; drag
[ -z "$(cat "$t/preload")" ] || fail "drag: preloaded a shim that failed to build: $(cat "$t/preload")"
rm -f "$t/cc-fails"; ROG5_STEAM_DRAG=0 HOME=$t/home STEAMROOT=$s sh "$here/steam-arm64" 2>/dev/null
[ "$(cat "$t/preload")" = unset ] || fail "drag: ROG5_STEAM_DRAG=0 still preloads"
echo "PASS steam-arm64: drag shim (build, preload, up to date, build failure, opt-out)"

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

# --- steam-fex-turnip-8bit -------------------------------------------------------
L64=usr/lib/libvulkan_freedreno.so L32=usr/lib32/libvulkan_freedreno.so
st=$ROG5_FEX_TURNIP_STATE
mkroot() {  # $1 dir, $2 content suffix
	mkdir -p "$1/usr/lib" "$1/usr/lib32"; echo '{}' >"$1/graphics_provider.json"
	echo "x86_64 $2" >"$1/$L64"; echo "i686 $2" >"$1/$L32"; chmod 755 "$1/$L64" "$1/$L32"
}
tu() { PATH=$b:$PATH ROG5_FEX_ROOT=$root ROG5_FEX_CACHE=$cache sh "$here/steam-fex-turnip-8bit" "$@" >"$t/out" 2>"$t/err"; }
content() { cat "$root/$L64" "$root/$L32" | tr '\n' '|'; }
rm -rf "$root" "$st"; mkroot "$root" stock
pay=$t/payload; mkroot "$pay" 8bit; chmod 700 "$pay/$L64" "$pay/$L32"
(cd "$pay" && sha256sum $L64 $L32 >SHA256SUMS)
(cd "$root" && sha256sum $L64 $L32 >"$pay/BASE.SHA256SUMS")

tu install "$pay" || fail "turnip: install failed: $(cat "$t/err")"
[ "$(content)" = 'x86_64 8bit|i686 8bit|' ] || fail "turnip: install did not replace both: $(content)"
[ -e "$st/enabled" ] && [ "$(ls "$st/orig" | wc -l)" = 2 ] || fail "turnip: no backups/enabled marker"
[ -z "$(find "$root" -name '*.rog5-new')" ] || fail "turnip: temporary files left in the root"
[ "$(stat -c %a "$root/$L64")" = 755 ] || fail "turnip: mode not kept"
tu install "$pay" && grep -q 'already the 8-bit build' "$t/out" || fail "turnip: second install: $(cat "$t/out" "$t/err")"
tu status && grep -q "$L32: 8-bit build" "$t/out" && grep -q 'rootfs update: yes' "$t/out" || fail "turnip: status: $(cat "$t/out")"
tu restore || fail "turnip: restore failed: $(cat "$t/err")"
[ "$(content)" = 'x86_64 stock|i686 stock|' ] && [ ! -e "$st/enabled" ] || fail "turnip: restore: $(content)"
tu status && grep -q "$L64: guest original" "$t/out" || fail "turnip: status after restore: $(cat "$t/out")"

# a damaged payload or an unknown driver in the root changes nothing
echo junk >>"$pay/$L32"
tu install "$pay" && fail "turnip: installed a payload that fails its SHA256SUMS"
[ "$(content)" = 'x86_64 stock|i686 stock|' ] || fail "turnip: damaged payload touched the root"
echo "i686 8bit" >"$pay/$L32"
echo "x86_64 other" >"$root/$L64"
tu install "$pay" && fail "turnip: replaced an unknown driver without --force"
[ "$(content)" = 'x86_64 other|i686 stock|' ] || fail "turnip: refused install touched the root: $(content)"
tu install "$pay" --force || fail "turnip: --force install: $(cat "$t/err")"
[ "$(content)" = 'x86_64 8bit|i686 8bit|' ] || fail "turnip: --force: $(content)"
tu restore && [ "$(content)" = 'x86_64 other|i686 stock|' ] || fail "turnip: restore after --force: $(content)"
echo "x86_64 stock" >"$root/$L64"

: >"$t/steam-running"
tu install "$pay" && fail "turnip: installed while Steam runs"
rm "$t/steam-running"
exec 8<"$ROG5_FEX_LOCK"; flock -s -n 8
tu install "$pay" && fail "turnip: installed while steam-arm64 holds the root lock"
exec 8<&-
[ "$(content)" = 'x86_64 stock|i686 stock|' ] || fail "turnip: refused installs touched the root"

# steam-fex-rootfs-install puts it into a new root before publishing it
tu install "$pay" || fail "turnip: install before rootfs update: $(cat "$t/err")"
cat >"$b/unsquashfs" <<EOF
#!/bin/sh
while [ \$# -gt 1 ]; do [ "\$1" = -d ] && d=\$2; shift; done
mkdir -p "\$d/usr/lib" "\$d/usr/lib32"; echo '{}' >"\$d/graphics_provider.json"; echo new >"\$d/marker"
echo "x86_64 \$(cat $t/image-mesa)" >"\$d/$L64"; echo "i686 \$(cat $t/image-mesa)" >"\$d/$L32"
EOF
chmod +x "$b/unsquashfs"
echo stock >"$t/image-mesa"
run || fail "turnip: rootfs update failed: $(cat "$t/err")"
[ "$(cat "$root/marker")" = new ] && [ "$(content)" = 'x86_64 8bit|i686 8bit|' ] ||
	fail "turnip: rootfs update did not reapply: $(content)"
echo newer >"$t/image-mesa"
run || fail "turnip: rootfs update with another Mesa failed: $(cat "$t/err")"
[ "$(content)" = 'x86_64 newer|i686 newer|' ] && grep -q 'was not applied' "$t/err" ||
	fail "turnip: another Mesa: $(content) $(cat "$t/err")"
tu restore && grep -q 'left alone' "$t/err" && [ "$(content)" = 'x86_64 newer|i686 newer|' ] ||
	fail "turnip: restore on a root with another Mesa: $(content) $(cat "$t/err")"
echo stock >"$t/image-mesa"
run && [ "$(content)" = 'x86_64 stock|i686 stock|' ] || fail "turnip: disabled but still reapplied: $(content)"
echo "PASS steam-fex-turnip-8bit: checked replace, backups, restore, refusals, locks, reapply on rootfs update"
