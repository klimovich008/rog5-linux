#!/bin/sh
set -eu

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
patch=${PATCH_FILE:-$repo/patches/linux-7.1.4/0018-power-supply-qcom-battmgr-add-rog5-cell-voltage.patch}
source_dir=${SOURCE_DIR:-}

[ -f "$patch" ] && [ ! -L "$patch" ] && [ -r "$patch" ] ||
	fail "patch is not a readable ordinary file: $patch"

numstat=$(git apply --numstat "$patch") || fail "patch is not parseable: $patch"
[ "$(printf '%s\n' "$numstat" | wc -l)" -eq 1 ] ||
	fail 'patch must modify exactly one file'
printf '%s\n' "$numstat" |
	grep -Eq '^[0-9]+[[:space:]]+[0-9]+[[:space:]]+drivers/power/supply/qcom_battmgr\.c$' ||
	fail 'patch must modify only drivers/power/supply/qcom_battmgr.c'

added=$(sed -n '/^+[^+]/p' "$patch")
printf '%s\n' "$added" |
	grep -Eq '^\+#define[[:space:]]+PMIC_GLINK_OWNER_ASUS_ROG5[[:space:]]+32782$' ||
	fail 'patch lacks the exact ASUS OEM owner'
printf '%s\n' "$added" |
	grep -Eq '^\+#define[[:space:]]+ASUS_ROG5_GET_CELL_VOLTAGE[[:space:]]+0x3005$' ||
	fail 'patch lacks the exact ASUS cell-voltage opcode'

required_added_lines='
"asus,cell-voltage-readonly"
devm_pmic_glink_client_alloc(dev,
PMIC_GLINK_OWNER_ASUS_ROG5,
if (len != sizeof(*resp))
le32_to_cpu(resp->hdr.owner) != PMIC_GLINK_OWNER_ASUS_ROG5
le32_to_cpu(resp->hdr.type) != PMIC_GLINK_REQ_RESP
le32_to_cpu(resp->hdr.opcode) != ASUS_ROG5_GET_CELL_VOLTAGE
mutex_lock(&battmgr->lock);
wait_for_completion_timeout(&battmgr->oem_ack, HZ)
READ_ONCE(battmgr->oem_service_up)
READ_ONCE(battmgr->oem_request_poisoned)
READ_ONCE(battmgr->oem_service_generation) != generation
WRITE_ONCE(battmgr->oem_request_poisoned, true);
le16_to_cpu(resp->cell1_voltage)
le16_to_cpu(resp->cell2_voltage)
DEVICE_ATTR_RO(cell_voltages);
psy_cfg.attr_grp = qcom_battmgr_asus_groups;'
old_ifs=$IFS
IFS='
'
for required in $required_added_lines; do
	[ -z "$required" ] && continue
	printf '%s\n' "$added" | grep -Fq "$required" ||
		fail "patch lacks required bounded implementation: $required"
done
IFS=$old_ifs

if printf '%s\n' "$added" | grep -Eq \
	'DEVICE_ATTR_(RW|WO)|set_property|property_is_writeable|module_param|debugfs|proc_create|request_firmware|devm_gpiod|nvmem|charge_(control|limit)|of_property_write'; then
	fail 'patch adds a write/control, firmware, GPIO, nvmem, or debug interface'
fi

[ "$(printf '%s\n' "$added" | grep -Fc 'pmic_glink_client_register(battmgr->oem_client);')" -eq 1 ] ||
	fail 'patch must register exactly one dedicated OEM client'
[ "$(printf '%s\n' "$added" | grep -Fc 'complete(&battmgr->oem_ack);')" -ge 1 ] ||
	fail 'OEM callback must complete the bounded request'

if [ -n "$source_dir" ]; then
	[ -d "$source_dir/.git" ] || fail "source is not a Git worktree: $source_dir"
	[ "$(git -C "$source_dir" rev-parse HEAD)" = \
		7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 ] ||
		fail 'source HEAD is not pinned Linux 7.1.4'
	[ -z "$(git -C "$source_dir" status --porcelain)" ] ||
		fail 'pinned Linux source is dirty'
	git -C "$source_dir" apply --check "$patch" ||
		fail 'patch does not apply to pinned Linux 7.1.4'
fi

echo 'PASS ROG5 cell-voltage patch is opt-in, read-only, exact-length, serialized, and one-file bounded'
