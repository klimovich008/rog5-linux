#!/bin/sh
set -eu
repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
awk '/^refresh_module_set\(\) \{/ { copy=1 } copy { print } copy && /^}/ { exit }' \
	"$repo/scripts/device/build-persistent-root-standalone-initramfs.sh" >"$work/function"
[ -s "$work/function" ] || { echo 'FAIL module refresh is not implemented'; exit 1; }
. "$work/function"
expected_release=7.1.4-g359318de534f
mkdir "$work/source" "$work/target"
printf '%s\n' old >"$work/target/probe.ko"
printf '%s\n' new >"$work/source/probe.ko"
readelf() {
	case $1 in
		-h) printf '%s\n' 'Type: REL (Relocatable file)' 'Machine: AArch64' ;;
		-SW) printf '%s\n' '[11] .BTF PROGBITS' ;;
		*) return 1 ;;
	esac
}
modinfo() { printf '%s SMP\n' "${fixture_release:-$expected_release}"; }
refresh_module_set "$work/source" "$work/target" 1
cmp "$work/source/probe.ko" "$work/target/probe.ko"
for hostile in missing extra symlink bad-release; do
	case $hostile in
		missing) mv "$work/source/probe.ko" "$work/probe.ko" ;;
		extra) cp "$work/source/probe.ko" "$work/source/extra.ko" ;;
		symlink) mv "$work/source/probe.ko" "$work/probe.ko"; ln -s ../probe.ko "$work/source/probe.ko" ;;
		bad-release) fixture_release=wrong ;;
	esac
	if (refresh_module_set "$work/source" "$work/target" 1) >"$work/refusal" 2>&1; then
		echo "FAIL module refresh accepted $hostile"; exit 1
	fi
	case $hostile in
		missing) mv "$work/probe.ko" "$work/source/probe.ko" ;;
		extra) rm "$work/source/extra.ko" ;;
		symlink) rm "$work/source/probe.ko"; mv "$work/probe.ko" "$work/source/probe.ko" ;;
		bad-release) unset fixture_release ;;
	esac
done
echo 'PASS standalone module refresh preserves inventory and refuses unsafe inputs'
