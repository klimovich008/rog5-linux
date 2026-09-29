#!/bin/sh
set -eu

repo=$(CDPATH='' cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.2.7/0037-drm-panel-add-ASUS-ROG-Phone-5-AMS678-ER2.patch
policy=$repo/configs/kernel/rog5-production-build-7.2.7.json
expected=6967fbef059e84b9319414ea834b8eafafeb7fe716675e0ba3a3d3f69ae02b8e

[ -f "$patch" ] && [ ! -L "$patch" ]
[ -f "$policy" ] && [ ! -L "$policy" ]
[ "$(sha256sum "$patch" | cut -d ' ' -f 1)" = "$expected" ]
[ "$(git apply --numstat "$patch")" = "$(printf '%s\n' \
	'73	0	Documentation/devicetree/bindings/display/panel/asus,rog5-ams678.yaml' \
	'12	0	drivers/gpu/drm/panel/Kconfig' \
	'1	0	drivers/gpu/drm/panel/Makefile' \
	'537	0	drivers/gpu/drm/panel/panel-asus-rog5-ams678.c')" ]

for marker in \
	'The Samsung AMS678 ER2 is a 1080x2448 command-mode MIPI-DSI OLED panel' \
	'Say Y here to enable the 1080x2448 command-mode DSC OLED panel' \
	'compatible = "asus,rog5-ams678-er2"' \
	'Pixelworks Iris6 one-wire ENTER_ANALOG_BYPASS command: two pulses.' \
	'for (i = 0; i < 2; i++)' \
	'usleep_range(56, 70)' \
	'usleep_range(237, 300)' \
	'Iris6 analog bypass did not become ready' \
	'mipi_dsi_dcs_set_display_brightness_large' \
	'(1080 + 30 + 4 + 14) * (2448 + 2 + 1 + 12) * 60 / 1000' \
	'ctx->dsc.slice_height = 48' \
	'ctx->dsc.slice_width = 540' \
	'ctx->dsc.bits_per_pixel = 8 << 4'; do
	grep -Fq "$marker" "$patch" || {
		echo "FAIL panel patch marker missing: $marker" >&2
		exit 1
	}
done
[ "$(grep -Fc 'static const struct drm_display_mode ' "$patch")" -eq 1 ]
if grep -Eq 'iris-cmd-list|iris-lightup-sequence|debugfs|ioctl|90hz|120hz|144hz' "$patch"; then
	echo 'FAIL initial panel patch contains Pixelworks PQ or higher-rate scope' >&2
	exit 1
fi
# The production build policy carries the panel as a module next to the
# MSM KMS/DSI stack and the DSI reference generator.
python3 - "$policy" <<'PY'
import json, sys
required = json.load(open(sys.argv[1]))['required']
for key, value in (('CONFIG_DRM_PANEL_ASUS_ROG5_AMS678', 'm'), ('CONFIG_DRM_MSM', 'm'),
                   ('CONFIG_DRM_MSM_KMS', 'y'), ('CONFIG_DRM_MSM_DSI', 'y'),
                   ('CONFIG_REGULATOR_QCOM_REFGEN', 'y')):
    if required.get(key) != value:
        raise SystemExit(f'FAIL production policy {key}={required.get(key)}, want {value}')
PY

echo 'PASS artifact identity and static 60 Hz/production configuration constraints'
python3 "$repo/scripts/device/test-ams678-lifecycle.py"
python3 "$repo/scripts/host/test-ams678-compile-location.py"

if [ -n "${ROG5_LINUX_SOURCE:-}" ]; then
	[ -e "$ROG5_LINUX_SOURCE/.git" ] && [ ! -L "$ROG5_LINUX_SOURCE" ]
	[ -z "$(git -C "$ROG5_LINUX_SOURCE" status --porcelain)" ]
	[ "$(git -C "$ROG5_LINUX_SOURCE" rev-parse HEAD)" = \
		f42acb3678424d1e08f6ed27c0d8ba8a125e14d6 ]
	git -C "$ROG5_LINUX_SOURCE" apply --check "$patch"
	echo 'PASS applicability: exact Linux v7.2.7 base'
else
	echo 'NOT RUN patch applicability: ROG5_LINUX_SOURCE unset'
fi

echo 'NOT RUN affected-driver compilation: use scripts/host/build-ams678-panel-check.sh'
echo 'NOT RUN physical panel validation'
