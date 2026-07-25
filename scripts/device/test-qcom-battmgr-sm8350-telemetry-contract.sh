#!/bin/sh
set -eu

source_dir=${SOURCE_DIR:-}
[ -n "$source_dir" ] || {
	echo 'FAIL set SOURCE_DIR to the pinned Linux 7.1.4 source' >&2
	exit 1
}
source=$source_dir/drivers/power/supply/qcom_battmgr.c

[ -d "$source_dir/.git" ] && [ -r "$source" ]
[ "$(git -C "$source_dir" rev-parse HEAD)" = \
	7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 ]
[ -z "$(git -C "$source_dir" status --porcelain)" ]

extract_descriptor() {
	name=$1
	awk -v name="$name" '
		$0 ~ "static const struct power_supply_desc " name " = \\{" { found = 1 }
		found { print }
		found && /^};$/ { exit }
	' "$source"
}

for descriptor in \
	sm8350_bat_psy_desc \
	sm8350_usb_psy_desc \
	sm8350_wls_psy_desc
do
	block=$(extract_descriptor "$descriptor")
	[ -n "$block" ]
	printf '%s\n' "$block" | grep -q '\.get_property = '
	! printf '%s\n' "$block" | grep -Eq '\.(set_property|property_is_writeable) = '
done

sm8350_bat_props=$(awk '
	/^static const enum power_supply_property sm8350_bat_props\[\]/ { found = 1 }
	found { print }
	found && /^};$/ { exit }
' "$source")
[ -n "$sm8350_bat_props" ]
! printf '%s\n' "$sm8350_bat_props" |
	grep -q 'POWER_SUPPLY_PROP_CHARGE_CONTROL_'

[ "$(rg -c '^#define BATTMGR_(BAT|USB|WLS)_PROPERTY_SET' "$source")" -eq 3 ]
[ "$(rg -c 'BATTMGR_(BAT|USB|WLS)_PROPERTY_SET' "$source")" -eq 3 ]
grep -q 'BATTMGR_REQUEST_NOTIFICATION' "$source"
grep -q 'qcom_battmgr_enable_worker' "$source"
grep -q 'pmic_glink_client_register(battmgr->client);' "$source"

echo 'PASS SM8350 battery, USB, and wireless descriptors expose reads and notifications but no charger-control setter'
