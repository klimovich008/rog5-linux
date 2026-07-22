#!/bin/sh
set -u

if [ "${ALLOW_GPU_FAULT_TEST:-0}" != 1 ]; then
    echo 'Refusing known GPU fault test. Set ALLOW_GPU_FAULT_TEST=1 only after core tests pass.' >&2
    exit 2
fi

command -v python3 >/dev/null 2>&1 || { echo 'python3 is required' >&2; exit 2; }
kgsl=/sys/devices/platform/soc/3d00000.qcom,kgsl-3d0/kgsl/kgsl-3d0
before=$(cat "$kgsl/snapshot/faultcount" 2>/dev/null || echo unavailable)

python3 - <<'PY'
import os
for attempt in (1, 2):
    fd = os.open('/dev/kgsl-3d0', os.O_RDWR | os.O_CLOEXEC)
    os.close(fd)
    print(f'PASS raw KGSL open {attempt}')
PY
result=$?
after=$(cat "$kgsl/snapshot/faultcount" 2>/dev/null || echo unavailable)
printf 'INFO fault_count_before=%s\nINFO fault_count_after=%s\n' "$before" "$after"

[ "$result" -eq 0 ] || exit "$result"
[ "$before" = unavailable ] || [ "$after" = "$before" ] || exit 1
