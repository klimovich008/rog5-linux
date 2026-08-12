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
profile=persistent-root-usb-control-v6-live-v1
image_name=build/persistent-root-usb-control-v6-generation27-20260812-r1/repack/stable-recovery-a.avb.img
basis='one exact Generation 20 kernel/DTB USB-control discriminator that stops before UFS; RAM-only; externally consumed exact claim required; never flash or retry after entry'
role='unbooted Generation 27 exact Generation 20 kernel/DTB USB-control discriminator; persistent initramfs must stop at the deliberate pre-UFS release mismatch; twin signed bundle and byte-distinct AVB wrapper; one RAM-only use only; never flash'
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM

case_source=$(awk -v profile="$profile" '
	/^# Historical profiles retain/ { contracts = 1 }
	!contracts && index($0, "\t" profile ")") == 1 { capture = 1; count++ }
	capture { print }
	capture && /^[[:space:]]*;;$/ { exit }
	END { if (count != 1) exit 1 }
' "$gate") || fail 'persistent-root live profile case is not unique'
case_unindented=$(sed 's/^[[:space:]]*//' <<<"$case_source")
for assignment in \
	expected_boot_image=$image_name \
	expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455 \
	expected_raw=90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6 \
	expected_initramfs=3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d \
	expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31 \
	expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800 \
	expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e \
	expected_target_id=persistent-root-usb-control-v6 \
	expected_bundle=persistent-root-usb-control-v6 \
	expected_bundle_profile=persistent-root-ro-v1 \
	expected_target_release=7.1.4-g7a5cef0db479 \
	expected_avb_salt=bf7f7d708fbf0c03e001da2ee9da9b634b45d523ef4ae53051f6d949ba4cc04e \
	expected_avb_digest=7ded981c6fca8b8ded552c084078301f098a570238a212ea878b06be2c93dc6c \
	expected_generation_record=e9678e7179ea4fd788e5795e026932e2875d5a752b87f095e5ff3651882ca1c7 \
	recovery_init=\$repo/initramfs/recovery-init
do
	grep -Fxq "$assignment" <<<"$case_unindented" ||
		fail "persistent-root live profile omits $assignment"
done

contract_source=$(awk -v profile="$profile" '
	/^# Historical profiles retain/ { contracts = 1 }
	contracts && index($0, "\t" profile) == 1 { capture = 1 }
	capture { print }
	capture && /^[[:space:]]*;;$/ { exit }
' "$gate")
grep -Fq $'\tinitramfs_contract=exact-a600000-v1' <<<"$contract_source" ||
	fail 'persistent-root profile lacks the exact recovery-init contract'
grep -Fq 'grep -Fxq "target_release=$expected_target_release"' "$gate" ||
	fail 'stable gate does not verify the profile-specific target release'

exact=(
	765e45af3d4ced2c87e15adf5ba6141ce5824d75334afc2ddedb4a28db18d88f
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	33715e0c566a5fc7e771f6b89ca81fd1fe0bb6325b926995a0ba5c5f81a44a5b
	8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96
	persistent-root-usb-control-v6
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
grep -Fxq 'target_id=persistent-root-usb-control-v6' <<<"$policy"
grep -Fxq 'authority=none' <<<"$policy"
grep -Fxq 'result=PASS' <<<"$policy"

fields=(recovery trust manifest host-verifier bundle)
errors=(
	'persistent-root recovery image is not pinned'
	'persistent-root trust key is not pinned'
	'persistent-root runtime manifest is not pinned'
	'persistent-root host verifier is not pinned'
	'profile requires bundle=persistent-root-usb-control-v6'
)
for index in "${!fields[@]}"; do
	mutation=("${exact[@]}")
	if ((index == 4)); then
		mutation[$index]=wrong-persistent-bundle
	else
		mutation[$index]=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
	fi
	if run_policy "${mutation[@]}" >"$tmp/out" 2>"$tmp/err"; then
		fail "persistent-root policy accepted wrong ${fields[$index]}"
	fi
	grep -Fq "${errors[$index]}" "$tmp/err" ||
		fail "wrong ${fields[$index]} returned an unexpected rejection"
done

awk -F '\t' -v name="$image_name" -v basis="$basis" '
	$1 == name && $2 == "allow" && $3 == basis && NF == 3 { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$boot_policy" || fail 'persistent-root image is not uniquely admitted'
awk -F '\t' -v name="$image_name" -v role="$role" '
	$1 == name && $2 == "100663296" &&
	$3 == "765e45af3d4ced2c87e15adf5ba6141ce5824d75334afc2ddedb4a28db18d88f" &&
	$4 == role && $5 == "no" && NF == 5 { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$inventory" || fail 'persistent-root artifact inventory is not exact'
grep -Fq "\"$profile\":" "$claim_consumer" ||
	fail 'persistent-root profile lacks an exact-record claim'
grep -Fq 'PERSISTENT_TARGET_PRODUCT = "ROG5 persistent root"' \
	"$repo/scripts/host/pin-minimal-headless-host-key.py" ||
	fail 'host-key pinning does not accept the exact persistent-root gadget'

production_root=$repo/build/persistent-root-usb-control-v6-production-20260812-r1
generation_root=$repo/build/persistent-root-usb-control-v6-generation27-20260812-r1
recovery_root=$repo/build/generation26-rmtfs-recovery
if [[ -d $production_root/bundle-a && -d $generation_root && -d $recovery_root ]]; then
	artifact=$(
		env -i PATH="$PATH" HOME="$HOME" \
			ROG5_STABLE_RECOVERY_PROFILE="$profile" \
			LIVE_BUILD_ROOT="$generation_root" \
			RECOVERY_COMPONENT_ROOT="$recovery_root" \
			TRUST_KEY="$recovery_root/ephemeral-public.raw" \
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
		<<<"$artifact" || fail 'persistent-root artifact preflight did not pass'
else
	[[ ${REQUIRE_CURRENT_PERSISTENT_ARTIFACT:-0} != 1 ]] ||
		fail 'required persistent-root clean-twin output is absent'
	echo 'SKIP persistent-root artifact preflight: ignored clean-twin output absent' >&2
fi

echo 'PASS Generation 27 exact Generation 20 kernel/DTB USB-control profile, exact claim, and admission are pinned'
