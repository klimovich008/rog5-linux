#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
observer=$repo/scripts/device/observe-early-mainline-power.sh
parser=$repo/scripts/host/early-target-diagnostics.py

[ -x "$observer" ] && [ -f "$observer" ] && [ ! -L "$observer" ]
sh -n "$observer"

for contract in \
	'rog5-early-power-evidence-v1' \
	'present|*:*:absent|*:*:error' \
	'verify_storage_absent' \
	'verify_transport' \
	'verify_rollback' \
	'check_battery_safety' \
	'snapshot_class power_supply' \
	'snapshot_class typec' \
	'snapshot_remoteproc' \
	'snapshot_auxiliary' \
	'snapshot_dmesg' \
	'summary net-positive' \
	'summary result present complete'
do
	grep -Fq "$contract" "$observer"
done

if grep -Eq 'fastboot[[:space:]]+(flash|erase)|dd[[:space:]].*of=/dev/|charge_control_.*>|/sys/class/typec/.*>' "$observer"; then
	echo 'FAIL early power observer contains a storage or charging-control write' >&2
	exit 1
fi

python3 - "$observer" "$parser" <<'PY'
import importlib.util
from pathlib import Path
import subprocess
import sys

observer = Path(sys.argv[1])
source = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("early_diag", source)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

candidate = "headless-power-usb-observer-v99"
boot_id = "01234567-89ab-cdef-0123-456789abcdef"
diagnostic = module.DiagnosticRecord(
    candidate=candidate,
    boot_id=boot_id,
    sequence=1,
    boottime_ms=1000,
    stage_code=141,
    stage="charging-exec",
    last_good_code=141,
    fault="none",
    watchdog_deadline_ms=900000,
    dropped_updates=0,
)
payload = module.frame_for(diagnostic) + subprocess.check_output(
    [str(observer), "--self-test"]
)
stream = module.DiagnosticStream(candidate)
records = stream.feed(payload)
stream.finalize()
power = [
    record
    for record in records
    if isinstance(record, module.PowerEvidenceRecord)
]
assert len(power) == 3
assert [record.status for record in power] == [
    "present",
    "absent",
    "present",
]
assert bytes.fromhex(power[0].value) == b"50"
assert power[-1].category == "summary"
assert power[-1].name == "result"
assert bytes.fromhex(power[-1].value) == b"complete"

mutated = payload.replace(b"status=absent", b"status=unknown", 1)
try:
    module.DiagnosticStream(candidate).feed(mutated)
except module.DiagnosticError:
    pass
else:
    raise AssertionError("unknown telemetry status was accepted")
PY

echo 'PASS early mainline power observer is bounded, typed, non-fatal for optional telemetry, and ACM-parseable'
