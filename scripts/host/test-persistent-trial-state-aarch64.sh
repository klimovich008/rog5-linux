#!/bin/bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
record=$repo/configs/recovery-control/aarch64-build-v1.json
runner=$repo/scripts/host/run-private-arm64-binfmt.sh
builder=$repo/scripts/device/build-persistent-trial-state.sh
source_file=$repo/tools/persistent_trial_state/rog5-persistent-trial-state.c
artifact=$repo/artifacts/persistent-trial-state-v1/rog5-persistent-trial-state
meta=$repo/artifacts/persistent-trial-state-v1/build-meta.txt

fail() { echo "FAIL $*" >&2; exit 1; }
for command in cmp file podman python3 qemu-aarch64-static sha256sum; do
	command -v "$command" >/dev/null || fail "missing trial-state command: $command"
done
[[ -x $runner && -x $builder && -f $source_file && -x $artifact ]] ||
	fail 'persistent trial-state build input is absent'

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
(cd "$(dirname "$artifact")" && sha256sum -c SHA256SUMS)
[[ $(stat -c '%s:%a' "$artifact") == 67520:755 ]] ||
	fail 'persistent trial artifact metadata changed'
grep -Fxq "source_sha256=$(sha256sum "$source_file" | awk '{print $1}')" "$meta"
grep -Fxq "builder_sha256=$(sha256sum "$builder" | awk '{print $1}')" "$meta"
file "$artifact" | grep -q 'ARM aarch64.*static-pie linked'
set +e
qemu-aarch64-static "$artifact" >"$work/qemu.out" 2>"$work/qemu.err"
status=$?
set -e
[[ $status -eq 1 ]] || fail 'AArch64 helper usage status changed'
grep -Fq 'usage: decide TRIAL_ID PRIMARY PRIMARY_HASH FALLBACK' "$work/qemu.err"
echo 'PASS reproducible exact AArch64 persistent trial-state helper'
