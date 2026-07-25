#!/bin/sh
set -eu

patch=${1:?usage: verify-ccf-registration-trace-patch.sh PATCH [PINNED_V10_SOURCE]}
source_dir=${2:-}
expected_sha=5f0be38bf3773f0cc541d7a52f930bc05dc979ee1a086198f3148aa14552dbc9
expected_parent=d4bb00313e92514f89bc0a9e7a7dffcb4884834f

[ -r "$patch" ]
patch=$(CDPATH= cd -- "$(dirname "$patch")" && pwd)/$(basename "$patch")
[ "$(sha256sum "$patch" | cut -d ' ' -f 1)" = "$expected_sha" ]
[ "$(git apply --numstat "$patch" | wc -l)" -eq 4 ]
git apply --numstat "$patch" |
	grep -Eq '^150[[:space:]]+3[[:space:]]+drivers/clk/clk[.]c$'
git apply --numstat "$patch" |
	grep -Eq '^18[[:space:]]+3[[:space:]]+drivers/clk/qcom/clk-regmap[.]c$'
git apply --numstat "$patch" |
	grep -Eq '^3[[:space:]]+3[[:space:]]+drivers/clk/qcom/common[.]c$'
git apply --numstat "$patch" |
	grep -Eq '^2[[:space:]]+0[[:space:]]+drivers/clk/qcom/common[.]h$'

grep -Fq \
	'core_param(rog5_ccf_register_trace, rog5_ccf_register_trace, bool, 0400);' \
	"$patch"
[ "$(grep -Fc 'of_device_is_compatible(np, "qcom,sm8350-gpucc")' \
	"$patch")" -eq 1 ]
grep -Fq \
	'ROG5 CCF diagnostic: phase=%s clock=%s ret=%d' "$patch"
grep -Fq 'msleep(100);' "$patch"
grep -Fq \
	'return rog5_ccf_register_trace && np &&' "$patch"
[ "$(grep -Ec '^[+ ]	*ret = __clk_core_init[(]core[)];$' "$patch")" -eq 1 ]

for phase in \
	managed-entry \
	devres-allocation-begin \
	devres-allocation-complete \
	hw-register-begin \
	hw-register-complete \
	devres-commit-begin \
	devres-commit-complete \
	devres-release-begin \
	devres-release-complete \
	managed-exit \
	register-entry \
	init-detach-complete \
	core-allocation-begin \
	core-allocation-complete \
	name-copy-begin \
	name-copy-complete \
	runtime-init-begin \
	runtime-init-complete \
	parent-map-begin \
	parent-map-complete \
	consumer-allocation-begin \
	consumer-allocation-complete \
	consumer-link-begin \
	consumer-link-complete \
	core-init-begin \
	core-init-complete \
	register-exit \
	core-init-entry \
	prepare-lock-begin \
	prepare-lock-complete \
	hw-core-link-complete \
	runtime-get-begin \
	runtime-get-complete \
	duplicate-lookup-begin \
	duplicate-lookup-complete \
	ops-validation-begin \
	ops-validation-complete \
	driver-init-begin \
	driver-init-complete \
	parent-init-begin \
	parent-init-complete \
	topology-insert-begin \
	topology-insert-complete \
	accuracy-begin \
	accuracy-complete \
	phase-begin \
	phase-complete \
	duty-begin \
	duty-complete \
	rate-begin \
	rate-complete \
	critical-begin \
	critical-complete \
	orphan-reparent-begin \
	orphan-reparent-complete \
	runtime-put-begin \
	runtime-put-complete \
	prepare-unlock-begin \
	prepare-unlock-complete \
	debug-register-begin \
	debug-register-complete \
	core-init-exit
do
	grep -Fq "\"$phase\"" "$patch"
done

for phase in \
	regmap-device-lookup-begin \
	regmap-device-lookup-complete \
	regmap-device-assign-begin \
	regmap-device-assign-complete \
	regmap-parent-assign-begin \
	regmap-parent-assign-complete \
	regmap-lookup-complete \
	ccf-managed-register-begin \
	ccf-managed-register-complete
do
	grep -Fq "\"$phase\"" "$patch"
done

grep -Fq \
	'void qcom_cc_rog5_trace(struct device *dev, const char *phase,' "$patch"
[ "$(grep -Fc '#include "common.h"' "$patch")" -eq 1 ]
! grep -Eq '^\+.*EXPORT_SYMBOL.*qcom_cc_rog5_trace' "$patch"

added=$(sed -n 's/^+//p' "$patch")
if printf '%s\n' "$added" |
	grep -Eq 'regmap_(write|update_bits)|write[ql]|clk_(prepare_)?enable|regulator_(enable|set_voltage)|reset_control_|gdsc_(enable|disable)|pm_runtime_(enable|disable)|fastboot|/dev/|mount[[:space:]]|status[[:space:]]*=[[:space:]]*"okay"'
then
	echo 'FAIL CCF trace patch adds hardware control or persistent I/O' >&2
	exit 1
fi

if [ -n "$source_dir" ]; then
	[ -d "$source_dir/.git" ]
	[ "$(git -C "$source_dir" rev-parse HEAD)" = "$expected_parent" ]
	[ -z "$(git -C "$source_dir" status --porcelain)" ]
	git -C "$source_dir" apply --check "$patch"
	checkpatch=$source_dir/scripts/checkpatch.pl
	if [ -x "$checkpatch" ]; then
		"$checkpatch" --no-tree --strict --terse "$patch" >/dev/null
	fi
fi

echo 'PASS CCF registration trace is default-off, read-only, exact-device-gated, phase-complete, single-call, and hardware-control-free'
