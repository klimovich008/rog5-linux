#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=$repo/patches/linux-7.1.4/0004-pmic-glink-add-battery-only-diagnostic-mode.patch
source_dir=${SOURCE_DIR:-}

[ -r "$patch" ]
[ "$(git apply --numstat "$patch" | wc -l)" -eq 1 ]
git apply --numstat "$patch" | grep -Eq '^[0-9]+[[:space:]]+[0-9]+[[:space:]]+drivers/soc/qcom/pmic_glink\.c$'
grep -Fq 'static bool battery_only;' "$patch"
grep -Fq 'module_param(battery_only, bool, 0400);' "$patch"
grep -Fq 'pg->client_mask &= BIT(PMIC_GLINK_CLIENT_BATT);' "$patch"
[ "$(grep -c '^+.*pg->client_mask & BIT(PMIC_GLINK_CLIENT_' "$patch")" -eq 9 ]
[ "$(grep -c '^[+].*module_param' "$patch")" -eq 1 ]
! grep -Eq 'drivers/(power/supply|usb)|BATTMGR_.*SET|set_property|property_is_writeable|firmware|request_firmware|fastboot|/dev/' \
	"$patch"

if [ -n "$source_dir" ]; then
	[ -d "$source_dir/.git" ]
	[ "$(git -C "$source_dir" rev-parse HEAD)" = \
		7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 ]
	[ -z "$(git -C "$source_dir" status --porcelain)" ]
	git -C "$source_dir" apply --check "$patch"
fi

echo 'PASS PMIC GLINK diagnostic patch is default-off, read-only, battery-client-only, and touches one driver'
