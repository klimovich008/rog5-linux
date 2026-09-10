#!/bin/sh
set -eu

patch=${1:?usage: verify-qcom-cc-registration-trace-patch.sh PATCH GPUCC_PATCH [PINNED_SOURCE]}
gpucc_patch=${2:?missing prerequisite GPUCC trace patch}
source_dir=${3:-}
expected_sha=a6084f1b9f7d72fc984827a9f43559ef6a9a5cb3222a273775249924567f2df5

[ -r "$patch" ] && [ -r "$gpucc_patch" ]
patch=$(CDPATH= cd -- "$(dirname "$patch")" && pwd)/$(basename "$patch")
gpucc_patch=$(CDPATH= cd -- "$(dirname "$gpucc_patch")" && pwd)/$(basename "$gpucc_patch")
[ "$(sha256sum "$patch" | cut -d ' ' -f 1)" = "$expected_sha" ]
[ "$(git apply --numstat "$patch" | wc -l)" -eq 1 ]
git apply --numstat "$patch" |
	grep -Eq '^63[[:space:]]+2[[:space:]]+drivers/clk/qcom/common[.]c$'

grep -Fq \
	'core_param(rog5_qcom_cc_probe_trace, rog5_qcom_cc_probe_trace, bool, 0400);' \
	"$patch"
grep -Fq 'of_device_is_compatible(dev->of_node, "qcom,sm8350-gpucc")' \
	"$patch"
grep -Fq \
	'ROG5 QCOM CC diagnostic: phase=%s index=%d ret=%d' "$patch"
grep -Fq 'msleep(100);' "$patch"

for phase in \
	entry \
	allocation-complete \
	power-domain-attach-begin \
	power-domain-attach-complete \
	reset-register-begin \
	reset-register-complete \
	gdsc-allocation-begin \
	gdsc-allocation-complete \
	gdsc-register-begin \
	gdsc-register-complete \
	gdsc-action-begin \
	gdsc-action-complete \
	drop-protected-begin \
	drop-protected-complete \
	clock-hw-register-begin \
	clock-hw-register-complete \
	clock-regmap-register-begin \
	clock-regmap-register-complete \
	provider-register-begin \
	provider-register-complete \
	interconnect-register-begin \
	interconnect-register-complete \
	exit
do
	grep -Fq "\"$phase\"" "$patch"
done

added=$(sed -n 's/^+//p' "$patch")
if printf '%s\n' "$added" |
	grep -Eq 'regmap_(write|update_bits)|write[ql]|clk_(prepare_)?enable|regulator_(enable|set_voltage)|reset_control_|gdsc_(enable|disable)|fastboot|/dev/|mount[[:space:]]|status[[:space:]]*=[[:space:]]*"okay"'
then
	echo 'FAIL common-clock trace patch adds hardware control or persistent I/O' >&2
	exit 1
fi

if [ -n "$source_dir" ]; then
	[ -d "$source_dir/.git" ]
	[ "$(git -C "$source_dir" rev-parse HEAD)" = \
		7a5cef0db4795d9d453a12e0f61b5b7634fc4d40 ]
	[ -z "$(git -C "$source_dir" status --porcelain)" ]
	git -C "$source_dir" apply --check "$gpucc_patch"
	git -C "$source_dir" apply --check "$patch"
	checkpatch=$source_dir/scripts/checkpatch.pl
	if [ -x "$checkpatch" ]; then
		"$checkpatch" --no-tree --strict --terse "$patch" >/dev/null
	fi
fi

echo 'PASS common-clock trace is default-off, read-only, SM8350-GPUCC-only, phase-complete, and hardware-control-free'
