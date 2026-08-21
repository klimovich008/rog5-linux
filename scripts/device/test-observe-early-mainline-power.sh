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
if grep -Fq 'modprobe --first-time' "$observer"; then
	echo 'FAIL early power observer uses unsupported BusyBox modprobe option' >&2
	exit 1
fi
grep -Fq 'if output=$(modprobe "$module" 2>&1); then' "$observer"
grep -Fq '[ -d "/sys/module/$module" ]' "$observer"

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
storage_functions=$work/storage-functions.sh
awk '
	/^has_block_backed_mount\(\) \{/ { copy=1 }
	/^single_expected_udc\(\) \{/ { copy=0 }
	copy { print }
' "$observer" >"$storage_functions"
grep -Fq 'has_block_backed_mount() {' "$storage_functions"
# shellcheck disable=SC1090
. "$storage_functions"
mkdir -p "$work/sys-dev-block"
cat >"$work/nonblock.mountinfo" <<'EOF'
20 1 0:20 / /dev rw - devtmpfs devtmpfs rw
21 20 0:21 / /dev/pts rw - devpts devpts rw
22 20 0:22 / /dev/shm rw - tmpfs tmpfs rw
EOF
! has_block_backed_mount "$work/nonblock.mountinfo" \
	"$work/sys-dev-block"
cat >"$work/block.mountinfo" <<'EOF'
20 1 0:20 / /dev rw - devtmpfs devtmpfs rw
30 1 8:1 / /mnt/root ro - ext4 /dev/sda1 ro
EOF
mkdir "$work/sys-dev-block/8:1"
has_block_backed_mount "$work/block.mountinfo" "$work/sys-dev-block"
grep -Fq \
	'has_block_backed_mount /proc/self/mountinfo /sys/dev/block' \
	"$observer"

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
