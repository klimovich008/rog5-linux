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
candidate_source=$repo/configs/recovery-candidates/headless-netroot-early-diag-v2.json

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
avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
avb_info=$(python3 "$avbtool" info_image --image "$image")
fixture_avb_salt=$(awk '/^      Salt:/ { print $2; exit }' <<<"$avb_info")
fixture_avb_digest=$(awk '/^      Digest:/ { print $2; exit }' <<<"$avb_info")
[[ $fixture_avb_salt == "$raw_sha" &&
	$fixture_avb_digest =~ ^[0-9a-f]{64}$ &&
	$fixture_avb_digest != 0000000000000000000000000000000000000000000000000000000000000000 ]] ||
	fail 'full disposable diagnostic AVB descriptor identity is malformed'

cp -- "$gate" "$fixture_gate"
# Rewrite only the private gate copy from the exact authority-free stage-75 v2
# tuple to this run's disposable trust-root tuple. The manifest and component
# binaries remain deterministic; the embedded public key changes the recovery
# initramfs, wrapper kernel, raw image, AVB image, and descriptor digest.
python3 - "$fixture_gate" \
	"833899cb067a28d57e41c5a8291c7f5099c4f7fcc11316c2976d04a7b926e7de=$image_sha" \
	"406b2497bff8174b01119e4bcfa4dddb544df3de8fdb9168d80e88708f20a995=$raw_sha" \
	"7a6c2a19c7a00a2699fd598b4fc3ad5fed680bf2cd9cb7cfa7bafa783d9fe563=$kernel_sha" \
	"df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f=$config_sha" \
	"a38b61462468272c8d8409461d7318cfc442c3a4707a624e9f8ab1751ef047a4=$initramfs_sha" \
	"58950b2101dca0702f2c436015bbb21eb6535e4e06f74808c2f8183c9da27268=$trust_sha" \
	"0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621=$host_verifier_sha" \
	"242ac7fc4b7d7614cf5fe8a26162255c898de2f2aeef9cf70687d0d327c149e7=$control_sha" \
	"77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800=$fetcher_sha" \
	"5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0=$verifier_sha" \
	"a1d19575dd21b6da3fd3cbb6c0f4ea33e312cc59ddc860889f1f54ef976e7b49=$fixture_avb_digest" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
payload = path.read_text(encoding="ascii")
consumed_records = (
    "consumed_diagnostic_recovery=9c060a27f21f6f99ca0c00cd1ff2ed9532220d585cd726b194f8b6d04e6204ef",
    "consumed_corrected_diagnostic_recovery=f710bbcd1f9602f0fdc3ce7023298f66cc5e7a014a0627c4f9123d7cc897b0ef",
    "consumed_listener_successor_recovery=332889a83f541ed0e17c94656836c512a35b5bfd6bbbaf735d2f5f6b94b51830",
    "consumed_nfs_gated_generation2_recovery=70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1",
)
for record in consumed_records:
    if payload.count(record) != 1:
        raise SystemExit(f"missing exact consumed recovery guard: {record}")
for replacement in sys.argv[2:]:
    before, after = replacement.split("=", 1)
    if before not in payload:
        raise SystemExit(f"missing fixture pin: {before}")
    payload = payload.replace(before, after)
fixture_image = sys.argv[2].split("=", 1)[1]
if payload.count(fixture_image) != 1:
    raise SystemExit("fixture image is not the unique stage-75 v2 allowlist pin")
for record in consumed_records:
    if payload.count(record) != 1:
        raise SystemExit(f"consumed recovery guard changed by fixture rewrite: {record}")
    if record.endswith(fixture_image):
        raise SystemExit("fixture image collides with a consumed recovery guard")
path.write_text(payload, encoding="ascii")
PY
chmod 0755 "$fixture_gate"

ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-stage75-v2-superseded-offline-v1 \
LIVE_BUILD_ROOT="$output_root/wrapper" \
RECOVERY_COMPONENT_ROOT="$output_root/recovery" \
TRUST_KEY="$trust" \
BUNDLE_ROOT="$output_root/bundle-a" \
BUNDLE=headless-netroot-early-diag-v2 \
RECOVERY_SHA256="$image_sha" \
TRUST_KEY_SHA256="$trust_sha" \
MANIFEST_SHA256=2ca802ee37d444dca71629064ccadfb81c3e8db2b83a6a4e040c1d5d5469cbe7 \
HOST_VERIFIER_SHA256="$host_verifier_sha" \
	"$fixture_gate" artifact-preflight >"$test_root/artifact-preflight.out"
grep -Fxq \
	"PASS stable-recovery artifact preflight profile=headless-diagnostic-stage75-v2-superseded-offline-v1 image_sha256=$image_sha" \
	"$test_root/artifact-preflight.out" ||
	fail 'disposable diagnostic artifact preflight omitted its exact pass marker'

printf 'image_sha256=%s\ntrust_key_sha256=%s\n' "$image_sha" "$trust_sha"
echo 'authority=none'
echo 'PASS full disposable-key diagnostic wrapper, twin build, native verification, and artifact-preflight fixture'
