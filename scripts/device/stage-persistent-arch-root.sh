#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

[ "${ALLOW_ROG5_PERSISTENT_STAGE:-}" = 1 ] ||
	fail 'persistent staging is unarmed; set ALLOW_ROG5_PERSISTENT_STAGE=1'

script_dir=$(CDPATH='' cd -- "$(dirname "$0")" && pwd)
inspector=$script_dir/inspect-persistent-layout.sh
root_tool=$script_dir/persistent-root-tool.py
expected_size=2007033670
expected_hash=a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7
generation=arch-a

case $# in
	1)
		mode=live
		archive=$1
		store=/rog5
		layout_root=/
		[ "$(id -u)" = 0 ] ||
			fail 'live persistent staging requires root'
		case ${ROG5_PERSISTENT_TEST_INTERRUPT:-} in
			'') ;;
			*) fail 'test interruption controls are forbidden in live mode' ;;
		esac
		;;
	8)
		[ "$1" = --fixture ] ||
			fail 'usage: stage-persistent-arch-root.sh ARCHIVE'
		mode=fixture
		sys=$2
		mounts=$3
		cmdline=$4
		layout_root=$5
		expected_size=$6
		expected_hash=$7
		archive=$8
		fixture_base=${TMPDIR:-/tmp}
		case $layout_root in
			"$fixture_base"/*) ;;
			*) fail 'fixture root must be below /tmp' ;;
		esac
		store=$layout_root/rog5
		;;
	*)
		fail 'usage: stage-persistent-arch-root.sh ARCHIVE'
		;;
esac

for command in awk bsdtar flock grep id install mv python3 \
	sha256sum stat sync; do
	command -v "$command" >/dev/null ||
		fail "missing persistent staging command: $command"
done
for path in "$inspector" "$root_tool"; do
	[ -x "$path" ] ||
		fail "missing executable persistent staging dependency: $path"
done
case $archive:$store in
	/*:/*) ;;
	*) fail 'archive and persistent store paths must be absolute' ;;
esac
case $expected_size in
	''|*[!0-9]*) fail 'expected archive size is invalid' ;;
esac
[ "$expected_size" -gt 0 ] ||
	fail 'expected archive size is empty'
case $expected_hash in
	????????????????????????????????????????????????????????????????) ;;
	*) fail 'expected archive SHA-256 length is invalid' ;;
esac
case $expected_hash in
	*[!0-9a-f]*) fail 'expected archive SHA-256 is invalid' ;;
esac
[ -f "$archive" ] && [ ! -L "$archive" ] ||
	fail 'source archive is absent, linked, or not regular'
[ "$(stat -c %s "$archive")" = "$expected_size" ] ||
	fail 'source archive size changed'
actual_hash=$(sha256sum "$archive" | awk '{ print $1 }')
[ "$actual_hash" = "$expected_hash" ] ||
	fail 'source archive hash changed'

archive_report=$("$root_tool" archive "$archive") ||
	fail 'source archive contract failed'
printf '%s\n' "$archive_report" |
	grep -Eq '^archive_entries=[1-9][0-9]*$' ||
	fail 'source archive entry count is invalid'

case $mode in
	live)
		layout_report=$("$inspector") ||
			fail 'live persistent layout preflight failed'
		printf '%s\n' "$layout_report" |
			grep -Fq 'PASS persistent layout mode=live ' ||
			fail 'live persistent layout report changed'
		;;
	fixture)
		layout_report=$("$inspector" \
			"$sys" "$mounts" "$cmdline" "$layout_root") ||
			fail 'fixture persistent layout preflight failed'
		printf '%s\n' "$layout_report" |
			grep -Fq 'PASS persistent layout mode=fixture ' ||
			fail 'fixture persistent layout report changed'
		;;
esac

[ ! -L "$store" ] && [ ! -L "$store/roots" ] ||
	fail 'persistent store path is linked'
install -d -m 0700 "$store" "$store/roots"
[ -d "$store" ] && [ -d "$store/roots" ] ||
	fail 'persistent store directories are absent'

lock=$store/.stage.lock
exec 9>"$lock"
chmod 0600 "$lock"
flock -n 9 ||
	fail 'another persistent staging operation holds the lock'

partial=$store/roots/$generation.partial
final=$store/roots/$generation
[ ! -e "$partial" ] && [ ! -L "$partial" ] ||
	fail 'partial generation already exists; inspect it before removal'
[ ! -e "$final" ] && [ ! -L "$final" ] ||
	fail 'published generation already exists; refusing overwrite'
install -d -m 0700 "$partial"

bsdtar --safe-writes --acls --xattrs --fflags -xpf "$archive" \
	-C "$partial" ||
	fail 'metadata-preserving archive extraction failed'
[ "$(stat -c %s "$archive")" = "$expected_size" ] &&
	[ "$(sha256sum "$archive" | awk '{ print $1 }')" = "$expected_hash" ] ||
	fail 'source archive changed during extraction'

case ${ROG5_PERSISTENT_TEST_INTERRUPT:-} in
	'') ;;
	after-extract)
		[ "$mode" = fixture ] ||
			fail 'test interruption control escaped fixture mode'
		echo 'FAIL injected interruption after extraction' >&2
		exit 75
		;;
	*) fail 'unknown fixture interruption point' ;;
esac

seal=$partial/.rog5-persistent-seal
: >"$seal"
tree_report=$("$root_tool" seal "$partial") ||
	fail 'extracted tree sealing failed'
entries=$(printf '%s\n' "$tree_report" |
	awk -F= '$1 == "tree_entries" { print $2 }')
tree_hash=$(printf '%s\n' "$tree_report" |
	awk -F= '$1 == "tree_sha256" { print $2 }')
case $entries in
	''|0|*[!0-9]*) fail 'extracted tree entry count is malformed' ;;
esac
case $tree_hash in
	????????????????????????????????????????????????????????????????) ;;
	*) fail 'extracted tree hash length is malformed' ;;
esac
case $tree_hash in
	*[!0-9a-f]*) fail 'extracted tree hash is malformed' ;;
esac

{
	printf '%s\n' 'seal_format=rog5-persistent-root-v1'
	printf '%s\n' "generation=$generation"
	printf '%s\n' "source_archive_size=$expected_size"
	printf '%s\n' "source_archive_sha256=$expected_hash"
	printf '%s\n' 'promotion_state=UNBOOTED'
	printf '%s\n' "$tree_report"
} >"$seal"
chmod 0444 "$seal"
"$root_tool" verify "$partial" "$seal" >/dev/null ||
	fail 'new persistent root does not match its seal'

sync -f "$store"
[ ! -e "$final" ] ||
	fail 'published generation appeared before atomic rename'
mv -T -- "$partial" "$final" ||
	fail 'atomic persistent-root publication failed'
sync -f "$store"

printf '%s\n' \
	"PASS persistent Arch root staged generation=$generation entries=$entries tree_sha256=$tree_hash publication=atomic-unbooted"
