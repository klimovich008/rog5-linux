#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0037-drm-panel-add-ASUS-ROG-Phone-5-AMS678-ER2.patch
fragment=$repo/configs/kernel/rog5-display-60hz.fragment
expected=1a244e3da6f44a00e2aca2abb679e40b9e28c6a96e7a4d2e2a16bac6a2b6cbec

[ -f "$patch" ] && [ ! -L "$patch" ]
[ -f "$fragment" ] && [ ! -L "$fragment" ]
[ "$(sha256sum "$patch" | cut -d ' ' -f 1)" = "$expected" ]
[ "$(git apply --numstat "$patch")" = "$(printf '%s\n' \
	'73	0	Documentation/devicetree/bindings/display/panel/asus,rog5-ams678.yaml' \
	'12	0	drivers/gpu/drm/panel/Kconfig' \
	'1	0	drivers/gpu/drm/panel/Makefile' \
	'448	0	drivers/gpu/drm/panel/panel-asus-rog5-ams678.c')" ]

for marker in \
	'compatible = "asus,rog5-ams678-er2"' \
	'Pixelworks Iris6 one-wire ENTER_ANALOG_BYPASS command: two pulses.' \
	'for (i = 0; i < 2; i++)' \
	'usleep_range(56, 70)' \
	'usleep_range(237, 300)' \
	'Iris6 analog bypass did not become ready' \
	'MIPI_DCS_SET_DISPLAY_BRIGHTNESS' \
	'brightness & 0xff' \
	'(1080 + 30 + 4 + 14) * (2448 + 2 + 1 + 12) * 60 / 1000' \
	'ctx->dsc.slice_height = 48' \
	'ctx->dsc.slice_width = 540' \
	'ctx->dsc.bits_per_pixel = 8 << 4'; do
	grep -Fq "$marker" "$patch"
done
[ "$(grep -Fc 'static const struct drm_display_mode ' "$patch")" -eq 1 ]
if grep -Eq 'iris-cmd-list|iris-lightup-sequence|debugfs|ioctl|90hz|120hz|144hz' "$patch"; then
	echo 'FAIL initial panel patch contains Pixelworks PQ or higher-rate scope' >&2
	exit 1
fi
[ "$(grep -Fxc 'CONFIG_DRM_PANEL_ASUS_ROG5_AMS678=y' "$fragment")" -eq 1 ]
grep -Fqx 'CONFIG_REGULATOR_QCOM_REFGEN=m' "$fragment"
grep -Fqx 'CONFIG_LOCALVERSION="-rog5-display60-v1"' "$fragment"
grep -Fqx '# CONFIG_LOCALVERSION_AUTO is not set' "$fragment"
for symbol in DRM_MSM_KMS DRM_MSM_DPU DRM_MSM_DSI DRM_MSM_DSI_7NM_PHY \
	DRM_FBDEV_EMULATION DRM_CLIENT_DEFAULT_FBDEV VT_CONSOLE \
	BACKLIGHT_CLASS_DEVICE; do
	grep -Fqx "CONFIG_${symbol}=y" "$fragment"
done

if [ -n "${ROG5_LINUX_SOURCE:-}" ]; then
	[ -d "$ROG5_LINUX_SOURCE/.git" ] && [ ! -L "$ROG5_LINUX_SOURCE" ]
	[ -z "$(git -C "$ROG5_LINUX_SOURCE" status --porcelain)" ]
	[ "$(git -C "$ROG5_LINUX_SOURCE" rev-parse HEAD)" = \
		7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 ]
	git -C "$ROG5_LINUX_SOURCE" apply --check "$patch"
fi

echo 'PASS AMS678 patch is 60 Hz-only, analog-bypass-gated, and base-applicable'
