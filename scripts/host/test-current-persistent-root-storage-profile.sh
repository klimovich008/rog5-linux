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
issued_basis='one exact read-only local-image Arch repeat accepting one bounded startup-output stream only when it contains exactly one authenticated marker line before one runtime evidence command; same accepted v45 target bundle, four-module UFS, two ro,noload ext4 layers, persisted Generation 64 marker, early strict Ed25519 SSH, storage attestation, tmpfs OverlayFS, and rollback; RAM-only kernel/recovery; externally consumed exact claim required; never flash or retry after entry'
consumed_basis='consumed by the sole Generation 70 RAM-only cycle; exact UFS, local image, tmpfs OverlayFS, P2 storage attestation, bounded authenticated SSH marker acceptance, strict key-only runtime, normal reboot, exact Alpine fallback, PS_HOLD lineage, and host restoration passed in 326.300 seconds; never retry or flash'
generation69_basis='consumed by the sole Generation 69 RAM-only cycle; exact UFS, local image, tmpfs OverlayFS, P2 storage attestation, and key-only sshd passed; the bounded rendezvous reached one status-zero SSH response within its deadline but rejected unretained extra startup output before the runtime command; the same boot later passed exact runtime at 378.07 seconds and diagnostics; normal reboot, exact Alpine fallback, PS_HOLD lineage, and host restoration passed; never retry or flash'
profile=persistent-root-local-image-early-ssh-v45-generation70-live-v1
image_name=build/persistent-root-local-image-early-ssh-v45-generation70-20260814-r1/repack/stable-recovery-a.avb.img
generation69_image=build/persistent-root-local-image-early-ssh-v45-generation69-20260814-r1/repack/stable-recovery-a.avb.img
issued_role='unbooted Generation 70 bounded-startup-output local-image successor; exact unchanged v45 signed target bundle and raw recovery, fresh deterministic AVB wrapper, one exact authenticated marker line amid at most 4096 startup-output bytes before one runtime evidence command; one RAM-only use only; never flash'
consumed_role='consumed Generation 70 bounded-startup-output local-image cycle; exact UFS/local-image/P2, one authenticated marker amid 175 bounded startup bytes, strict runtime at 243.46 seconds uptime, normal reboot, exact Alpine fallback, and host restoration passed in 326.300 seconds; never retry or flash'
generation69_role='consumed Generation 69 authenticated-SSH-rendezvous cycle; exact UFS/local-image/P2 and later same-boot runtime passed; a status-zero cold SSH response carried unretained extra startup output and was rejected before runtime; normal reboot and exact Alpine fallback passed; never retry or flash'
[[ $consumed_role == consumed\ * ]] || fail 'Generation 70 role must remain consumed'
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
grep -Fxq "expected_boot_basis='$issued_basis'" <<<"$case_unindented" ||
	fail 'Generation 70 boot basis is not pinned in the profile'
grep -Fxq "expected_boot_role='$issued_role'" <<<"$case_unindented" ||
	fail 'Generation 70 artifact role is not pinned in the profile'
for assignment in \
	expected_boot_image=$image_name \
	expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455 \
	expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b \
	expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946 \
	expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31 \
	expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3 \
	expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e \
	expected_target_id=persistent-root-local-image-early-ssh-v45 \
	expected_bundle=persistent-root-local-image-early-ssh-v45 \
	expected_bundle_profile=persistent-root-ro-v1 \
	expected_target_release=7.1.4-gae717d919f87 \
	expected_avb_salt=16a5bcc417b28d927996d6bbaeff33b405439f489307137a2944b55751aae787 \
	expected_avb_digest=fb5dc23cd31297fb4fb5546048b9f7d9a97d3fed4f1a4e8ac80d1fd7b289e794 \
	expected_generation_record=5b33f9e4dacf97b29faa1c3170058435903e7a652970aceb1c4c679ef885298a \
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
	0f8352ad767ffb77def5e2ac644af994c0df577c89f6051f87e1e8fb49b6635d
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	f039b0a34a6ca3f2447b9499f4c4023fa894f5089e5f346dd852e0f132201949
	8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96
	persistent-root-local-image-early-ssh-v45
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
grep -Fxq 'target_id=persistent-root-local-image-early-ssh-v45' <<<"$policy"
grep -Fxq 'authority=none' <<<"$policy"
grep -Fxq 'result=PASS' <<<"$policy"

fields=(recovery trust manifest host-verifier bundle)
errors=(
	'persistent-root recovery image is not pinned'
	'persistent-root trust key is not pinned'
	'persistent-root runtime manifest is not pinned'
	'persistent-root host verifier is not pinned'
	'profile requires bundle=persistent-root-local-image-early-ssh-v45'
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

awk -F '\t' -v name="$image_name" -v basis="$consumed_basis" '
	$1 == name && $2 == "revoked" && $3 == basis && NF == 3 { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$boot_policy" || fail 'Generation 70 image is not uniquely revoked'
awk -F '\t' -v name="$generation69_image" -v basis="$generation69_basis" '
	$1 == name && $2 == "revoked" && $3 == basis && NF == 3 { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$boot_policy" || fail 'Generation 69 image is not uniquely revoked'
awk -F '\t' -v name="$image_name" -v role="$consumed_role" '
	$1 == name && $2 == "100663296" &&
	$3 == "0f8352ad767ffb77def5e2ac644af994c0df577c89f6051f87e1e8fb49b6635d" &&
	$4 == role && $5 == "no" && NF == 5 { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$inventory" || fail 'Generation 70 consumed artifact inventory is not exact'
awk -F '\t' -v name="$generation69_image" -v role="$generation69_role" '
	$1 == name && $2 == "100663296" &&
	$3 == "4dfc0efc92b511b424b7d9db115d692c79b0366459e23582421cd37d9c307a65" &&
	$4 == role && $5 == "no" && NF == 5 { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$inventory" || fail 'Generation 69 consumed artifact inventory changed'
grep -Fq "\"$profile\":" "$claim_consumer" ||
	fail 'persistent-root profile lacks an exact-record claim'
grep -Fq 'PERSISTENT_TARGET_PRODUCT = "ROG5 persistent root"' \
	"$repo/scripts/host/pin-minimal-headless-host-key.py" ||
	fail 'host-key pinning does not accept the exact persistent-root gadget'

production_root=$repo/build/persistent-root-local-image-early-ssh-v45-production-20260814-r1
generation_root=$repo/build/persistent-root-local-image-early-ssh-v45-generation70-20260814-r1
recovery_root=$repo/build/generation46-transport-recovery
if [[ -d $production_root/bundle-a && -d $generation_root && -d $recovery_root ]]; then
	image=$generation_root/repack/stable-recovery-a.avb.img
	[[ $(stat -c %s "$image") == 100663296 ]] ||
		fail 'retained Generation 70 image size changed'
	[[ $(sha256sum "$image" | cut -d ' ' -f 1) == "${exact[0]}" ]] ||
		fail 'retained Generation 70 image identity changed'
	module_root=$tmp/module-proof
	mkdir "$module_root"
	gzip -dc "$production_root/bundle-a/persistent-root-local-image-early-ssh-v45/initramfs.cpio.gz" |
		(cd "$module_root" && cpio -idm --quiet --no-absolute-filenames)
	module_inventory=$(find "$module_root/rog5-ufs-modules" -mindepth 1 \
		-maxdepth 1 -printf '%f\n' | sort | tr '\n' ' ')
	[[ $module_inventory == \
		'phy-qcom-qmp-ufs.ko ufs-qcom.ko ufshcd-core.ko ufshcd-pltfrm.ko ' ]] ||
		fail 'current image omits the exact deferred UFS module inventory'
	[[ $(sha256sum "$module_root/rog5-ufs-modules/phy-qcom-qmp-ufs.ko" | cut -d ' ' -f 1) == 73fef6fa7620bd4f9ac6df658521904ffeff2e19b02bc0258b77c410b7051ddb ]]
	[[ $(sha256sum "$module_root/rog5-ufs-modules/ufs-qcom.ko" | cut -d ' ' -f 1) == b55d7641727557e9682eb61cc0c43d21983676dfe258226dec49b33c71e8a26c ]]
	[[ $(sha256sum "$module_root/rog5-ufs-modules/ufshcd-core.ko" | cut -d ' ' -f 1) == a3e26e00e56950d0cd89ffcf16eb4911b778eb832cdbafdea332451a94ef6562 ]]
	[[ $(sha256sum "$module_root/rog5-ufs-modules/ufshcd-pltfrm.ko" | cut -d ' ' -f 1) == ef0a566ccd84094b47a4316c470d8db417a06604276ef240beaac72ae301b74d ]]
	grep -Fq \
		'Description=Start strict SSH before the general Arch boot transaction' \
		"$module_root/init"
	grep -Fq 'WantedBy=sysinit.target' "$module_root/init"
	grep -Fq 'Before=basic.target' "$module_root/init"
	grep -Fq 'systemctl is-active --quiet rog5-early-sshd.service' \
		"$module_root/usr/local/sbin/rog5-p2-attest"
else
	[[ ${REQUIRE_CURRENT_PERSISTENT_ARTIFACT:-0} != 1 ]] ||
		fail 'required persistent-root clean-twin output is absent'
	echo 'SKIP persistent-root artifact preflight: ignored clean-twin output absent' >&2
fi

echo 'PASS Generation 70 profile remains exact and artifact-verified while policy and inventory permanently refuse reuse'
