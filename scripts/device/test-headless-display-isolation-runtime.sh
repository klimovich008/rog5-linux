#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
checker=$repo/scripts/device/check-headless-display-isolation.sh
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -f "$checker" ] && [ ! -L "$checker" ] && [ -x "$checker" ] ||
	fail 'missing executable headless display-isolation runtime checker'

mdss=soc@0/display-subsystem@ae00000
dispcc=soc@0/clock-controller@af00000
dsi0=$mdss/dsi@ae94000
dsi0_phy=$mdss/phy@ae94400
dsi1=$mdss/dsi@ae96000
dsi1_phy=$mdss/phy@ae96400
dp=$mdss/displayport-controller@ae90000

make_fixture() {
	root=$1
	mkdir -p "$root/sys/firmware/devicetree/base" \
		"$root/sys/bus/platform/devices" \
		"$root/sys/class/drm" "$root/sys/class/backlight" \
		"$root/sys/class/graphics" "$root/dev"
	for node in "$mdss" "$dispcc" "$dsi0" "$dsi0_phy" \
		"$dsi1" "$dsi1_phy" "$dp"; do
		mkdir -p "$root/sys/firmware/devicetree/base/$node"
		printf 'disabled\0' >"$root/sys/firmware/devicetree/base/$node/status"
	done
}

make_fixture "$stage/good"
"$checker" "$stage/good" >/dev/null

mutant() {
	name=$1
	cp -a "$stage/good" "$stage/$name"
	printf '%s\n' "$stage/$name"
}

reject() {
	root=$1
	expected=$2
	if "$checker" "$root" >"$root.log" 2>&1; then
		fail "runtime checker accepted $(basename "$root")"
	fi
	grep -Fq "$expected" "$root.log" || {
		echo "FAIL runtime checker rejected $(basename "$root") incorrectly" >&2
		cat "$root.log" >&2
		exit 1
	}
}

root=$(mutant mdss-enabled)
printf 'okay\0' >"$root/sys/firmware/devicetree/base/$mdss/status"
reject "$root" 'FAIL device-tree display provider is not disabled: mdss'

root=$(mutant missing-dispcc-status)
rm "$root/sys/firmware/devicetree/base/$dispcc/status"
reject "$root" 'FAIL device-tree display status is not an ordinary file: dispcc'

root=$(mutant linked-dsi-status)
mv "$root/sys/firmware/devicetree/base/$dsi0/status" "$root/real-status"
ln -s "$root/real-status" \
	"$root/sys/firmware/devicetree/base/$dsi0/status"
reject "$root" 'FAIL device-tree display status is not an ordinary file: dsi0'

root=$(mutant bound-mdss)
mkdir -p "$root/sys/bus/platform/devices/ae00000.display-subsystem"
reject "$root" \
	'FAIL disabled display platform device exists: ae00000.display-subsystem'

root=$(mutant bound-dispcc)
mkdir -p "$root/sys/bus/platform/devices/af00000.clock-controller"
reject "$root" \
	'FAIL disabled display platform device exists: af00000.clock-controller'

root=$(mutant bound-dsi)
mkdir -p "$root/sys/bus/platform/devices/ae94000.dsi"
reject "$root" 'FAIL disabled display platform device exists: ae94000.dsi'

root=$(mutant drm-card)
mkdir -p "$root/sys/class/drm/card0"
reject "$root" 'FAIL DRM device exists in headless mode: card0'

root=$(mutant render-node)
mkdir -p "$root/sys/class/drm/renderD128"
reject "$root" 'FAIL DRM device exists in headless mode: renderD128'

root=$(mutant backlight)
mkdir -p "$root/sys/class/backlight/panel0-backlight"
reject "$root" 'FAIL backlight exists in headless mode: panel0-backlight'

root=$(mutant framebuffer)
mkdir -p "$root/sys/class/graphics/fb0"
reject "$root" 'FAIL framebuffer exists in headless mode: fb0'

root=$(mutant dri-device)
mkdir -p "$root/dev/dri"
printf 'unexpected\n' >"$root/dev/dri/card7"
reject "$root" 'FAIL display device node exists in headless mode: dev/dri/card7'

root=$(mutant fb-device)
printf 'unexpected\n' >"$root/dev/fb7"
reject "$root" 'FAIL display device node exists in headless mode: dev/fb7'

echo 'PASS hostile headless display-isolation runtime classifications'
