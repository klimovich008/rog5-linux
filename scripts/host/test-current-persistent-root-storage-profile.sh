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
profile=persistent-root-ufs-local-root-v29-live-v1
image_name=build/persistent-root-ufs-local-root-v29-generation50-20260813-r1/repack/stable-recovery-a.avb.img
basis='one exact read-only SM8350 UFS local-root boot with bounded recovery transfer, runtime block locks, exact userdata ro,noload mount, sealed root verification, tmpfs OverlayFS, systemd, and key-only SSH; RAM-only; externally consumed exact claim required; never flash or retry after entry'
role='unbooted Generation 50 read-only local Arch root; exact UFS lock and userdata identity, ro,noload outer mount, complete sealed-tree verification, tmpfs OverlayFS, systemd, key-only SSH, bounded rollback, and one RAM-only use only; never flash'
[[ $role == unbooted\ * ]] ||
	fail 'current persistent-root artifact role must remain live-gate eligible'
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
	expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b \
	expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946 \
	expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31 \
	expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3 \
	expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e \
	expected_target_id=persistent-root-ufs-local-root-v29 \
	expected_bundle=persistent-root-ufs-local-root-v29 \
	expected_bundle_profile=persistent-root-ro-v1 \
	expected_target_release=7.1.4-gae717d919f87 \
	expected_avb_salt=4e9f2860a79b396933e64bd9d5ab4b558267c9c1777b41e4ea37b5901f64ab7e \
	expected_avb_digest=2f6ce96b8f597b7469f222baf822b08f4068bfc78ad49c8296fda8005df04dc3 \
	expected_generation_record=0d4ec27a5559df88b0888efeffd07fa93a9ed2db57f109480c6900483191bc3c \
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
	26d2d9b7a230268d9bd3e82497aab3e8126aefcf951b2e1fcf0a4c7fc5d6df28
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	ae22914906d63accc893157b51c683f24a3a7e933bba84e13661e664764b9cc6
	8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96
	persistent-root-ufs-local-root-v29
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
grep -Fxq 'target_id=persistent-root-ufs-local-root-v29' <<<"$policy"
grep -Fxq 'authority=none' <<<"$policy"
grep -Fxq 'result=PASS' <<<"$policy"

fields=(recovery trust manifest host-verifier bundle)
errors=(
	'persistent-root recovery image is not pinned'
	'persistent-root trust key is not pinned'
	'persistent-root runtime manifest is not pinned'
	'persistent-root host verifier is not pinned'
	'profile requires bundle=persistent-root-ufs-local-root-v29'
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
	$3 == "26d2d9b7a230268d9bd3e82497aab3e8126aefcf951b2e1fcf0a4c7fc5d6df28" &&
	$4 == role && $5 == "no" && NF == 5 { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$inventory" || fail 'persistent-root artifact inventory is not exact'
grep -Fq "\"$profile\":" "$claim_consumer" ||
	fail 'persistent-root profile lacks an exact-record claim'
grep -Fq 'PERSISTENT_TARGET_PRODUCT = "ROG5 persistent root"' \
	"$repo/scripts/host/pin-minimal-headless-host-key.py" ||
	fail 'host-key pinning does not accept the exact persistent-root gadget'

production_root=$repo/build/persistent-root-ufs-local-root-v29-production-20260813-r1
generation_root=$repo/build/persistent-root-ufs-local-root-v29-generation50-20260813-r1
recovery_root=$repo/build/generation46-transport-recovery
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

echo 'PASS Generation 50 read-only local-root profile, exact claim, artifact, and admission are pinned'
