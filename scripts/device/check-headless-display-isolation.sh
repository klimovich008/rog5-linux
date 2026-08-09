#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

root=${1:-/}
case $root in
	/*) ;;
	*) fail 'runtime root must be absolute' ;;
esac
[ -d "$root" ] && [ ! -L "$root" ] ||
	fail 'runtime root is not a directory'
root=$(realpath -e -- "$root")
dt=$root/sys/firmware/devicetree/base
[ -d "$dt" ] && [ ! -L "$dt" ] ||
	fail 'device-tree sysfs root is unavailable'

require_disabled() {
	label=$1
	node=$2
	status=$dt/$node/status
	[ -f "$status" ] && [ ! -L "$status" ] ||
		fail "device-tree display status is not an ordinary file: $label"
	[ "$(stat -c %s "$status")" -eq 9 ] &&
		[ "$(tr -d '\000' <"$status")" = disabled ] ||
		fail "device-tree display provider is not disabled: $label"
}

mdss=soc@0/display-subsystem@ae00000
require_disabled mdss "$mdss"
require_disabled displayport "$mdss/displayport-controller@ae90000"
require_disabled dsi0 "$mdss/dsi@ae94000"
require_disabled dsi0-phy "$mdss/phy@ae94400"
require_disabled dsi1 "$mdss/dsi@ae96000"
require_disabled dsi1-phy "$mdss/phy@ae96400"
require_disabled dispcc soc@0/clock-controller@af00000

platform=$root/sys/bus/platform/devices
[ -d "$platform" ] && [ ! -L "$platform" ] ||
	fail 'platform-device sysfs root is unavailable'
for name in \
	ae00000.display-subsystem \
	ae01000.display-controller \
	ae90000.displayport-controller \
	ae94000.dsi \
	ae94400.phy \
	ae96000.dsi \
	ae96400.phy \
	af00000.clock-controller
do
	if [ -e "$platform/$name" ] || [ -L "$platform/$name" ]; then
		fail "disabled display platform device exists: $name"
	fi
done

first_entry() {
	directory=$1
	pattern=$2
	find "$directory" -mindepth 1 -maxdepth 1 -name "$pattern" \
		-printf '%f\n' 2>/dev/null | LC_ALL=C sort | head -n 1
}

name=$(first_entry "$root/sys/class/drm" 'card*')
[ -z "$name" ] || fail "DRM device exists in headless mode: $name"
name=$(first_entry "$root/sys/class/drm" 'renderD*')
[ -z "$name" ] || fail "DRM device exists in headless mode: $name"
name=$(first_entry "$root/sys/class/backlight" '*')
[ -z "$name" ] || fail "backlight exists in headless mode: $name"
name=$(first_entry "$root/sys/class/graphics" 'fb*')
[ -z "$name" ] || fail "framebuffer exists in headless mode: $name"

name=$(first_entry "$root/dev/dri" 'card*')
[ -z "$name" ] ||
	fail "display device node exists in headless mode: dev/dri/$name"
name=$(first_entry "$root/dev/dri" 'renderD*')
[ -z "$name" ] ||
	fail "display device node exists in headless mode: dev/dri/$name"
name=$(first_entry "$root/dev" 'fb*')
[ -z "$name" ] || fail "display device node exists in headless mode: dev/$name"

echo 'PASS headless display providers=disabled drm_nodes=0 backlights=0 framebuffers=0'
