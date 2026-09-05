#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
image=${ROG5_AARCH64_BUILD_IMAGE:-localhost/rog5-persistent-root-verifier:alpine-3.24-deck-v1}
expected_image_id=a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e
expected_image_digest=sha256:ab143fea42bd7780c2b69512397f9a33251ef9218c3258e5dd2995a905abddaa
source_file=$repo/tools/early_target_diag/rog5-early-target-diag.c
builder=$repo/scripts/device/build-early-target-diag.sh
runner=$repo/scripts/host/run-private-arm64-binfmt.sh

fail() {
	echo "FAIL $*" >&2
	exit 1
}

for command in cmp file podman sha256sum; do
	command -v "$command" >/dev/null ||
		fail "missing AArch64 reporter test command: $command"
done
podman image exists "$image" ||
	fail 'missing pinned local AArch64 build image'
[[ -x $runner && -f $runner && ! -L $runner ]] ||
	fail 'missing sealed private ARM64 runner'
[[ $(podman image inspect "$image" --format '{{.Architecture}}') == arm64 ]] ||
	fail 'reporter build image is not arm64'
actual_image_id=$(podman image inspect "$image" --format '{{.Id}}')
actual_image_digest=$(podman image inspect "$image" --format '{{.Digest}}')
[[ $actual_image_id == "$expected_image_id" ]] ||
	fail 'unexpected reporter build image ID'
[[ $actual_image_digest == "$expected_image_digest" ]] ||
	fail 'unexpected reporter build image digest'

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

build_one() {
	local name=$1

	"$runner" podman run --rm --pull=never --network=none --platform linux/arm64 \
		--security-opt label=disable \
		-v "$repo:/workspace:ro" \
		-v "$work:/out" \
		--workdir /workspace \
		"$image" \
		/workspace/scripts/device/build-early-target-diag.sh \
		/workspace/tools/early_target_diag/rog5-early-target-diag.c \
		"/out/$name"
}

build_one reporter-a >"$work/build-a.txt"
build_one reporter-b >"$work/build-b.txt"
cmp "$work/reporter-a" "$work/reporter-b"
file "$work/reporter-a" |
	grep -q 'ARM aarch64.*static-pie linked, stripped'

"$runner" "$work/reporter-a" frame \
	headless-netroot-early-diag-v1 \
	12345678-1234-4abc-8def-1234567890ab \
	1 250 10 10 none 600000 0 >"$work/native-frame"
python3 - "$repo" >"$work/oracle-frame" <<'PY'
import importlib.util
from pathlib import Path
import sys

repo = Path(sys.argv[1])
source = repo / "scripts/host/early-target-diagnostics.py"
spec = importlib.util.spec_from_file_location("early_target_diagnostics", source)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
record = module.DiagnosticRecord(
    candidate="headless-netroot-early-diag-v1",
    boot_id="12345678-1234-4abc-8def-1234567890ab",
    sequence=1,
    boottime_ms=250,
    stage_code=10,
    stage="reporter-up",
    last_good_code=10,
    fault="none",
    watchdog_deadline_ms=600000,
    dropped_updates=0,
)
sys.stdout.buffer.write(module.frame_for(record))
PY
cmp "$work/native-frame" "$work/oracle-frame"

for fault in host-port-probe-failed host-port-unreachable host-port-timeout; do
	"$runner" "$work/reporter-a" frame \
		headless-netroot-early-diag-v1 \
		12345678-1234-4abc-8def-1234567890ab \
		2 500 200 60 "$fault" 600000 0 >"$work/native-$fault"
	python3 - "$repo" "$fault" >"$work/oracle-$fault" <<'PY'
import importlib.util
from pathlib import Path
import sys

repo = Path(sys.argv[1])
fault = sys.argv[2]
source = repo / "scripts/host/early-target-diagnostics.py"
spec = importlib.util.spec_from_file_location("early_target_diagnostics", source)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
record = module.DiagnosticRecord(
    candidate="headless-netroot-early-diag-v1",
    boot_id="12345678-1234-4abc-8def-1234567890ab",
    sequence=2,
    boottime_ms=500,
    stage_code=200,
    stage="fault",
    last_good_code=60,
    fault=fault,
    watchdog_deadline_ms=600000,
    dropped_updates=0,
)
sys.stdout.buffer.write(module.frame_for(record))
PY
	cmp "$work/native-$fault" "$work/oracle-$fault"
done

sha256sum "$work/reporter-a" "$work/reporter-b"
printf 'build_image_id=%s build_image_digest=%s\n' \
	"$actual_image_id" "$actual_image_digest"
echo 'PASS reproducible static AArch64 early-target reporter and oracle frame'
