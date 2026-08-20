#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
gate=$repo/scripts/host/run-stable-recovery-live-gate.sh
claim_consumer=$repo/scripts/host/consume-exact-boot-claim.py
boot_policy=$repo/manifests/temporary-boot-images.tsv
inventory=$repo/manifests/artifacts.tsv
lifecycle=$repo/scripts/host/run-minimal-headless-live-cycle.py
profile=headless-core-deployment-v1-live-v1
image_name=build/headless-core-v21-generation21-20260812-r1/repack/stable-recovery-a.avb.img
basis='one exact headless-core Arch SSH recovery with power-key indicator; RAM-only; externally consumed exact claim required; never flash or retry after entry'
role='unbooted headless-core Arch SSH recovery with power-key indicator; clean-twin signed bundle and byte-distinct AVB generation over proven raw wrapper; one RAM-only use only; never flash'
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM

case_source=$(awk -v profile="$profile" '
	/^# Historical profiles retain/ { contracts = 1 }
	!contracts && index($0, "\t" profile ")") == 1 { capture = 1; count++ }
	capture { print }
	capture && /^[[:space:]]*;;$/ { exit }
	END { if (count != 1) exit 1 }
' "$gate") || fail 'headless-core live profile case is not unique'
case_unindented=$(sed 's/^[[:space:]]*//' <<<"$case_source")
for assignment in \
	expected_boot_image=$image_name \
	expected_kernel=2e5d6e1766aab790dd1d1718125244886d376ffb73aa6b761571b12820b3061c \
	expected_raw=067329920cc479714cac10ce001112c9029a3b986ac44269b8e7185a396c4aff \
	expected_initramfs=d9a3fba43abf0c3e456feb2e7f9da5e043df1e7cdef2e33112e0313358ae98d8 \
	expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31 \
	expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800 \
	expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef \
	expected_target_id=headless-core-network-root \
	expected_bundle=headless-core-network-root-v2-live-v1 \
	expected_bundle_profile=network-root-v1 \
	expected_avb_salt=e94d6e0017d44437f4c0951afc06b7dd707e44f14fde01fbbe773bae3521e962 \
	expected_avb_digest=24b325a1f60e67f36eec6977f7a84c7419187b2c1a5707144dc382d16f522489 \
	expected_generation_record=9726f2dfe6d3dac222d146147f2366931daeabe0181ceaeb4a62e4b84fa50bf0 \
	recovery_init=\$repo/initramfs/recovery-init
do
	grep -Fxq "$assignment" <<<"$case_unindented" ||
		fail "headless-core live profile omits $assignment"
done

contract_source=$(awk -v profile="$profile" '
	/^# Historical profiles retain/ { contracts = 1 }
	contracts && index($0, "\t" profile) == 1 { capture = 1 }
	capture { print }
	capture && /^[[:space:]]*;;$/ { exit }
' "$gate")
grep -Fq $'\tinitramfs_contract=exact-a600000-v1' <<<"$contract_source" ||
	fail 'headless-core profile lacks the exact recovery-init contract'

exact=(
	40418c0fef418263d3bf8f7c2fc1d7bed4745af79cc6b45bc78b2e8d1e0a56ee
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	f3884e6554f3d2c1bb437c45484f658817c006185d6c84a5ac4ef452b01bc02f
	03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0
	headless-core-network-root-v2-live-v1
)
run_policy() {
	env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE="$profile" \
		RECOVERY_SHA256="$1" TRUST_KEY_SHA256="$2" \
		MANIFEST_SHA256="$3" HOST_VERIFIER_SHA256="$4" BUNDLE="$5" \
		bash "$gate" policy-preflight
}
policy=$(run_policy "${exact[@]}")
grep -Fxq "recovery_profile=$profile" <<<"$policy"
grep -Fxq 'target_id=headless-core-network-root' <<<"$policy"
grep -Fxq 'authority=none' <<<"$policy"
grep -Fxq 'result=PASS' <<<"$policy"

fields=(recovery trust manifest host-verifier bundle)
errors=(
	'headless-core recovery image is not pinned'
	'headless-core trust key is not pinned'
	'headless-core runtime manifest is not pinned'
	'headless-core host verifier is not pinned'
	'profile requires bundle=headless-core-network-root-v2-live-v1'
)
for index in "${!fields[@]}"; do
	mutation=("${exact[@]}")
	if ((index == 4)); then
		mutation[$index]=wrong-core-bundle
	else
		mutation[$index]=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
	fi
	if run_policy "${mutation[@]}" >"$tmp/out" 2>"$tmp/err"; then
		fail "headless-core policy accepted wrong ${fields[$index]}"
	fi
	grep -Fq "${errors[$index]}" "$tmp/err" ||
		fail "wrong ${fields[$index]} returned an unexpected rejection"
done

[[ $(awk -F '\t' '$2 == "allow" { count++ } END { print count + 0 }' \
	"$boot_policy") == 3 ]] || fail 'observer/core/power-USB temporary-boot policy is not exact'
awk -F '\t' -v name="$image_name" -v basis="$basis" '
	$1 == name && $2 == "allow" && $3 == basis && NF == 3 { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$boot_policy" || fail 'headless-core image is not uniquely admitted'
awk -F '\t' -v name="$image_name" -v role="$role" '
	$1 == name && $2 == "100663296" &&
	$3 == "40418c0fef418263d3bf8f7c2fc1d7bed4745af79cc6b45bc78b2e8d1e0a56ee" &&
	$4 == role && $5 == "no" && NF == 5 { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$inventory" || fail 'headless-core artifact inventory is not exact'
grep -Fq "\"$profile\":" "$claim_consumer" ||
	fail 'headless-core profile lacks an exact-record claim'
grep -Fq 'CORE_RECOVERY_PROFILE = "headless-core-deployment-v1-live-v1"' \
	"$lifecycle" || fail 'lifecycle does not select the headless-core profile'

production_root=$repo/build/headless-core-v21-production-20260812-r1
generation_root=$repo/build/headless-core-v21-generation21-20260812-r1
if [[ ${REQUIRE_CURRENT_CORE_ARTIFACT:-0} == 1 ]]; then
	[[ -d $production_root && -d $generation_root ]] ||
		fail 'required headless-core clean-twin output is absent'
	artifact=$(
		env -i PATH="$PATH" HOME="$HOME" \
			ROG5_STABLE_RECOVERY_PROFILE="$profile" \
			LIVE_BUILD_ROOT="$generation_root" \
			RECOVERY_COMPONENT_ROOT="$production_root/recovery" \
			TRUST_KEY="$production_root/recovery/ephemeral-public.raw" \
			BUNDLE_ROOT="$production_root/bundle-a" \
			BUNDLE="${exact[4]}" \
			RECOVERY_SHA256="${exact[0]}" \
			TRUST_KEY_SHA256="${exact[1]}" \
			MANIFEST_SHA256="${exact[2]}" \
			HOST_VERIFIER_SHA256="${exact[3]}" \
			bash "$gate" artifact-preflight
	)
	grep -Fxq \
		"PASS stable-recovery artifact preflight profile=$profile image_sha256=${exact[0]}" \
		<<<"$artifact" || fail 'headless-core artifact preflight did not pass'
else
	echo 'SKIP headless-core artifact preflight: explicit retained-artifact check not requested' >&2
fi

echo 'PASS Generation 21 headless-core profile, exact claim, and admission are pinned'
