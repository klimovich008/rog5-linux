#!/usr/bin/bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

PATH=/usr/bin:/bin
export PATH
unset -f bash chmod cmp cp cut dirname env git grep mkdir mktemp openssl \
	python3 rm sha256sum stat 2>/dev/null || true

[[ ${ROG5_RUN_FULL_DISPOSABLE_DIAGNOSTIC:-} == 1 ]] ||
	fail 'set ROG5_RUN_FULL_DISPOSABLE_DIAGNOSTIC=1 for the expensive disposable full-path test'

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
output_root=${1:?usage: test-full-diagnostic-deployment-path.sh OUTPUT_ROOT}
wrapper=$repo/scripts/host/build-early-target-diagnostic-deployment-candidate.sh
gate=$repo/scripts/host/run-stable-recovery-live-gate.sh
candidate_source=$repo/configs/recovery-candidates/headless-netroot-early-diag-v1.json

[[ -x $wrapper && -x $gate && -f $candidate_source ]] ||
	fail 'full-path diagnostic test inputs are unavailable'
[[ -z $(git -C "$repo" status --porcelain --untracked-files=all) ]] ||
	fail 'full-path diagnostic test requires a clean repository'
branch=$(git -C "$repo" branch --show-current)
[[ -n $branch &&
	$(git -C "$repo" rev-parse --abbrev-ref --symbolic-full-name '@{u}') == \
	"origin/$branch" &&
	$(git -C "$repo" rev-parse HEAD) == \
	$(git -C "$repo" rev-parse '@{u}') ]] ||
	fail 'full-path diagnostic test requires a synchronized origin branch'

test_root=$(mktemp -d)
chmod 0700 "$test_root"
fixture_gate=$repo/scripts/host/.diagnostic-artifact-fixture-gate.$$
cleanup() {
	rm -f -- "$fixture_gate"
	if [[ -d $test_root && $test_root != / ]]; then
		chmod -R u+rwX -- "$test_root" 2>/dev/null || true
		rm -rf -- "$test_root"
	fi
}
trap cleanup EXIT HUP INT TERM

source_key=$test_root/disposable-ed25519.pem
source_candidate=$test_root/diagnostic-candidate.json
openssl genpkey -algorithm ED25519 -out "$source_key" 2>/dev/null
chmod 0600 "$source_key"
cp -- "$candidate_source" "$source_candidate"
chmod 0444 "$source_candidate"
source_key_sha=$(sha256sum "$source_key" | cut -d ' ' -f 1)

"$wrapper" \
	--authorize-recovery-deployment-build \
	--authorize-phone-credential-use \
	--candidate-record "$source_candidate" \
	--signing-key "$source_key" \
	"$output_root" >"$test_root/full-build.out"
grep -Fxq \
	'PASS twin credential-bound deployment candidate, signed bundle, recovery wrapper, and hardware-free gate; source key verified and private snapshot destroyed' \
	"$test_root/full-build.out" ||
	fail 'full disposable diagnostic build omitted its exact pass marker'
[[ $(sha256sum "$source_key" | cut -d ' ' -f 1) == "$source_key_sha" ]] ||
	fail 'full disposable diagnostic build changed its caller-owned key'

image=$output_root/wrapper/repack/stable-recovery-a.avb.img
raw=$output_root/wrapper/repack/stable-recovery-a.raw.img
kernel=$output_root/wrapper/wrapper-a/asus-kexec-stage/arch/arm64/boot/Image
config=$output_root/wrapper/wrapper-a/asus-kexec-stage/.config
initramfs=$output_root/recovery/initramfs-a/rog5-stable-recovery.cpio.gz
trust=$output_root/recovery/ephemeral-public.raw
host_verifier=$output_root/recovery/components/rog5-bundle-verify-host-test
control=$output_root/recovery/components/rog5-recovery-control
fetcher=$output_root/recovery/components/rog5-bundle-fetch
verifier=$output_root/recovery/components/rog5-bundle-verify
for artifact in "$image" "$raw" "$kernel" "$config" "$initramfs" \
	"$trust" "$host_verifier" "$control" "$fetcher" "$verifier"; do
	[[ -f $artifact && ! -L $artifact ]] ||
		fail "full disposable diagnostic artifact is missing: $artifact"
done

image_sha=$(sha256sum "$image" | cut -d ' ' -f 1)
raw_sha=$(sha256sum "$raw" | cut -d ' ' -f 1)
kernel_sha=$(sha256sum "$kernel" | cut -d ' ' -f 1)
config_sha=$(sha256sum "$config" | cut -d ' ' -f 1)
initramfs_sha=$(sha256sum "$initramfs" | cut -d ' ' -f 1)
trust_sha=$(sha256sum "$trust" | cut -d ' ' -f 1)
host_verifier_sha=$(sha256sum "$host_verifier" | cut -d ' ' -f 1)
control_sha=$(sha256sum "$control" | cut -d ' ' -f 1)
fetcher_sha=$(sha256sum "$fetcher" | cut -d ' ' -f 1)
verifier_sha=$(sha256sum "$verifier" | cut -d ' ' -f 1)

cp -- "$gate" "$fixture_gate"
python3 - "$fixture_gate" \
	"11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c=$image_sha" \
	"a937b03b54c01c6240cff45aa243632827d0c9d328e6f285ae489c973a6213a9=$raw_sha" \
	"1a8bac7a2b016dc7d63d22f09d0872b9c3f251952b7627c68f7c387f386b0068=$kernel_sha" \
	"df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f=$config_sha" \
	"f414d0ea26ee3aa6cca5c3aa12c1601934294c0207fc2709ebbae305bb3642e0=$initramfs_sha" \
	"f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b=$trust_sha" \
	"9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b=$host_verifier_sha" \
	"f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77=$control_sha" \
	"677fa731b1bd9fd11efc46aabeb32e7a725725483c86a2f58d417f482c27f392=$fetcher_sha" \
	"374900be5769eee074820007ab2e335d4c033c500da7a480cc88f9a70137029b=$verifier_sha" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
payload = path.read_text(encoding="ascii")
for replacement in sys.argv[2:]:
    before, after = replacement.split("=", 1)
    if before not in payload:
        raise SystemExit(f"missing fixture pin: {before}")
    payload = payload.replace(before, after)
path.write_text(payload, encoding="ascii")
PY
chmod 0755 "$fixture_gate"

ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-deployment-v1 \
LIVE_BUILD_ROOT="$output_root/wrapper" \
RECOVERY_COMPONENT_ROOT="$output_root/recovery" \
TRUST_KEY="$trust" \
BUNDLE_ROOT="$output_root/bundle-a" \
BUNDLE=headless-netroot-early-diag-v1 \
RECOVERY_SHA256="$image_sha" \
TRUST_KEY_SHA256="$trust_sha" \
MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
HOST_VERIFIER_SHA256="$host_verifier_sha" \
	"$fixture_gate" artifact-preflight >"$test_root/artifact-preflight.out"
grep -Fxq \
	"PASS stable-recovery artifact preflight profile=headless-diagnostic-deployment-v1 image_sha256=$image_sha" \
	"$test_root/artifact-preflight.out" ||
	fail 'disposable diagnostic artifact preflight omitted its exact pass marker'

printf 'image_sha256=%s\ntrust_key_sha256=%s\n' "$image_sha" "$trust_sha"
echo 'authority=none'
echo 'PASS full disposable-key diagnostic wrapper, twin build, native verification, and artifact-preflight fixture'
