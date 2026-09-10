#!/bin/sh
set -eu

probe=${1:?usage: verify-gpucc-trace-free-confirmation.sh PROBE ACM_HELPER GPUCC_TRACE_PATCH}
acm=${2:?missing ACM helper}
gpucc_patch=${3:?missing GPUCC trace patch}

for file in "$probe" "$acm" "$gpucc_patch"; do
	[ -r "$file" ] && [ ! -L "$file" ]
done
sh -n "$probe"

[ "$(grep -Fc \
	'gpucc_trace_mode=${ROG5_GPUCC_TRACE_MODE:-diagnostic}' "$probe")" -eq 1 ]
[ "$(grep -Fc 'diagnostic|confirmation)' "$probe")" -eq 1 ]
[ "$(grep -Fc 'trace_expected_count=1' "$probe")" -eq 1 ]
[ "$(grep -Fc 'trace_expected_state=Y' "$probe")" -eq 1 ]
[ "$(grep -Fc 'trace_expected_count=0' "$probe")" -eq 1 ]
[ "$(grep -Fc 'trace_expected_state=N' "$probe")" -eq 1 ]
[ "$(grep -Fc '[ "$gpucc_trace_mode" = confirmation ]' "$probe")" -eq 1 ]

for parameter in \
	rog5_qcom_cc_probe_trace \
	rog5_ccf_register_trace \
	rog5_rcg2_parent_trace
do
	[ "$(grep -Fc "$parameter" "$probe")" -eq 1 ]
done

for contract in \
	'boot_argument=$parameter=1' \
	'trace_prefix=$parameter=' \
	'[ "$trace_count" -eq "$trace_expected_count" ]' \
	'[ "$trace_enabled_count" -eq "$trace_expected_count" ]' \
	'[ "$(cat "$trace_path")" = "$trace_expected_state" ]' \
	'[ "$(stat -c %a "$trace_path")" = 400 ]' \
	'insmod "$module_file" probe_trace=1'
do
	grep -Fq "$contract" "$probe"
done

mode_line=$(grep -n \
	'gpucc_trace_mode=${ROG5_GPUCC_TRACE_MODE:-diagnostic}' "$probe" |
	cut -d: -f1)
trace_line=$(grep -n 'trace_expected_count=1' "$probe" | cut -d: -f1)
watchdog_line=$(grep -n '^setsid sh -c' "$probe" | cut -d: -f1)
module_line=$(grep -n '^[[:space:]]*insmod "\$module_file" probe_trace=1' \
	"$probe" | cut -d: -f1)
[ "$mode_line" -lt "$trace_line" ]
[ "$trace_line" -lt "$watchdog_line" ]
[ "$watchdog_line" -lt "$module_line" ]

python3 - "$acm" <<'PY'
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

source = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("rog5_network_root_acm", source)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

command, marker, disconnect, timeout = module.ACTIONS[
    "load-gpucc-confirmation"
]
assert command == (
    "ROG5_SYSTEMD_DIAGNOSTIC=1 ROG5_RECOVERY_TIMEOUT=900 "
    "/usr/local/sbin/rog5-load-mainline-recovery"
)
assert marker == module.LOAD_MARKER
assert disconnect is False
assert timeout == 60
for forbidden in (
    "ROG5_QCOM_CC_PROBE_TRACE",
    "ROG5_CCF_REGISTER_TRACE",
    "ROG5_RCG2_PARENT_TRACE",
):
    assert forbidden not in command
PY

[ "$(grep -Ec '^[+].*dev_notice[(]' "$gpucc_patch")" -eq 8 ]
grep -Fq 'module_param(probe_trace, bool, 0400);' "$gpucc_patch"
if sed -n 's/^+//p' "$gpucc_patch" |
	grep -Eiq 'msleep|usleep|udelay|mdelay|schedule_timeout|ssleep|[^a-z]sleep[(]'
then
	echo 'FAIL outer GPUCC trace adds a deliberate delay' >&2
	exit 1
fi

if grep -Eq 'fastboot[[:space:]]+flash|dd[[:space:]].*of=/dev/|mount[[:space:]].*/dev/' \
	"$probe" "$acm"
then
	echo 'FAIL trace-free confirmation contains a persistent-write path' >&2
	exit 1
fi

echo 'PASS trace-free GPUCC confirmation requires three core traces off and retains only the bounded delay-free outer trace'
