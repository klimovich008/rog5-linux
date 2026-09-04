#!/bin/bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
record=$repo/configs/recovery-control/aarch64-build-v1.json
runner=$repo/scripts/host/run-private-arm64-binfmt.sh
builder=$repo/scripts/device/build-persistent-trial-state.sh
source_file=$repo/tools/persistent_trial_state/rog5-persistent-trial-state.c
artifact=$repo/$(cat "$repo/configs/persistent-trial-helper.path")
meta=$(dirname "$artifact")/build-meta.txt
qemu=$repo/artifacts/host-tools/qemu-aarch64-static

fail() { echo "FAIL $*" >&2; exit 1; }
for command in cmp file python3 readelf sha256sum stat strings; do
	command -v "$command" >/dev/null || fail "missing trial-state command: $command"
done
[[ -x $runner && -x $builder && -f $source_file && -x $artifact ]] ||
	fail 'persistent trial-state build input is absent'
(cd "$(dirname "$artifact")" && sha256sum -c SHA256SUMS)
[[ $(stat -c '%s:%a' "$artifact") == "$(sed -n 's/^output_size=//p' "$meta"):755" ]] ||
	fail 'persistent trial artifact metadata changed'
grep -Fxq "output_sha256=$(sha256sum "$artifact" | awk '{print $1}')" "$meta"
# Accepted v1 remains an immutable historical artifact, not current source.
(cd "$repo/artifacts/persistent-trial-state-v1" && sha256sum -c SHA256SUMS)
grep -Fxq "source_sha256=$(sha256sum "$source_file" | awk '{print $1}')" "$meta"
grep -Fxq "builder_sha256=$(sha256sum "$builder" | awk '{print $1}')" "$meta"
file "$artifact" | grep -q 'ARM aarch64.*static-pie linked'
readelf -h "$artifact" | grep -q 'Machine:.*AArch64'
! readelf -l "$artifact" | grep -q INTERP ||
	fail 'persistent trial artifact gained an interpreter'

# Behavioral replay requires no compiler container. Qualified local CI must
# exercise the actual v2 selector with the retained v1 target acknowledgment.
if [[ -x $qemu ]] && command -v bwrap >/dev/null; then
	ROG5_TRIAL_TEST_ARM64=1 python3 "$repo/scripts/host/test-persistent-trial-state.py"
else
	echo 'SKIP isolated AArch64 behavior replay: QEMU/bubblewrap unavailable'
fi

if [[ ! -x $qemu ]] || ! command -v podman >/dev/null; then
	echo 'SKIP private AArch64 twin rebuild environment is unavailable'
	echo 'PASS exact tracked AArch64 persistent trial-state artifact'
	exit 0
fi

readarray -t image_fields < <(python3 - "$record" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))['builder']
print(d['image']); print(d['image_id']); print(d['image_digest'])
PY
)
[[ ${#image_fields[@]} -eq 3 ]] || fail 'AArch64 image record is incomplete'
image=${image_fields[0]}
[[ $(podman image inspect "$image" --format '{{.Id}}') == "${image_fields[1]}" ]] ||
	fail 'AArch64 image ID changed'
[[ $(podman image inspect "$image" --format '{{.Digest}}') == "${image_fields[2]}" ]] ||
	fail 'AArch64 image digest changed'

work=$(mktemp -d)
cleanup() { rm -f -- "$work"/*; rmdir -- "$work"; }
trap cleanup EXIT HUP INT TERM
for twin in a b; do
	"$runner" podman run --rm --network=none --platform linux/arm64 \
		-v "$repo:/workspace:ro,Z" -v "$work:/out:Z" "$image" \
		/workspace/scripts/device/build-persistent-trial-state.sh \
		/workspace/tools/persistent_trial_state/rog5-persistent-trial-state.c \
		"/out/trial-$twin" >"$work/build-$twin.log"
done
cmp "$work/trial-a" "$work/trial-b"
cmp "$work/trial-a" "$artifact"
set +e
"$qemu" "$artifact" >"$work/qemu.out" 2>"$work/qemu.err"
status=$?
set -e
[[ $status -eq 1 ]] || fail 'AArch64 helper usage status changed'
grep -Fq 'usage: decide TRIAL_ID PRIMARY PRIMARY_HASH FALLBACK' "$work/qemu.err"
echo 'PASS reproducible exact AArch64 persistent trial-state helper'
