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
issued_basis='one exact read-only local-image Arch cycle starting strict Ed25519 SSH and unchanged storage attestation from sysinit.target before the general Arch basic-target transaction; same accepted four-module UFS, two ro,noload ext4 layers, persisted Generation 64 marker, tmpfs OverlayFS, and bounded rollback; RAM-only kernel/recovery; externally consumed exact claim required; never flash or retry after entry'
consumed_basis='consumed by the sole Generation 67 RAM-only cycle; exact UFS, two ro,noload ext4 layers, persisted marker, early strict key-only SSH, and storage attestation passed, but recovery ACM closed after the COMMIT claim before the post-claim response; host salvage proved early SSH active at about 94.147 seconds and full attestation at 130.057 seconds; normal reboot, exact Alpine fallback, and host restoration passed; never retry or flash'
profile=persistent-root-local-image-early-ssh-v45-live-v1
image_name=build/persistent-root-local-image-early-ssh-v45-generation67-20260814-r1/repack/stable-recovery-a.avb.img
issued_role='unbooted Generation 67 early-SSH local-image successor; exact accepted UFS/Image/DTB and two ro,noload ext4 layers, stock sshd masked only in volatile /run, strict custom Ed25519 SSH and unchanged storage attestation ordered before basic.target; one RAM-only use only; never flash'
role='consumed Generation 67 early-SSH local-image cycle; exact UFS, two ro,noload ext4 layers, persisted marker, early strict key-only SSH, storage attestation, normal reboot, and exact Alpine fallback passed; lifecycle acceptance failed because recovery ACM closed before the post-claim response; never retry or flash'
[[ $role == consumed\ * ]] || fail 'Generation 67 role must remain consumed'
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
	fail 'Generation 67 boot basis is not pinned in the profile'
grep -Fxq "expected_boot_role='$issued_role'" <<<"$case_unindented" ||
	fail 'Generation 67 artifact role is not pinned in the profile'
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
	expected_avb_salt=93cb1f277ebe4b3d1eaf1517ba838a35558249cc3b78f55cd8c5e5ba0d6a12b7 \
	expected_avb_digest=92f0af76bcec47a44b048c55db22d8e2d6012c161a747633f0756c479e57898c \
	expected_generation_record=5c6c01703f5d84dd95697c5d9e7318dedd40546fa3f530ca1220dc8193b6cdbd \
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
	0bd1b6b8fddc27a5b4860036a13406f5cf4897c0ae84761a835868c0db086953
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
' "$boot_policy" || fail 'Generation 67 image is not uniquely revoked'
awk -F '\t' -v name="$image_name" -v role="$role" '
	$1 == name && $2 == "100663296" &&
	$3 == "0bd1b6b8fddc27a5b4860036a13406f5cf4897c0ae84761a835868c0db086953" &&
	$4 == role && $5 == "no" && NF == 5 { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$inventory" || fail 'persistent-root artifact inventory is not exact'
grep -Fq "\"$profile\":" "$claim_consumer" ||
	fail 'persistent-root profile lacks an exact-record claim'
grep -Fq 'PERSISTENT_TARGET_PRODUCT = "ROG5 persistent root"' \
	"$repo/scripts/host/pin-minimal-headless-host-key.py" ||
	fail 'host-key pinning does not accept the exact persistent-root gadget'

production_root=$repo/build/persistent-root-local-image-early-ssh-v45-production-20260814-r1
generation_root=$repo/build/persistent-root-local-image-early-ssh-v45-generation67-20260814-r1
recovery_root=$repo/build/generation46-transport-recovery
if [[ -d $production_root/bundle-a && -d $generation_root && -d $recovery_root ]]; then
	image=$generation_root/repack/stable-recovery-a.avb.img
	[[ $(stat -c %s "$image") == 100663296 ]] ||
		fail 'retained Generation 67 image size changed'
	[[ $(sha256sum "$image" | cut -d ' ' -f 1) == "${exact[0]}" ]] ||
		fail 'retained Generation 67 image identity changed'
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

echo 'PASS Generation 67 early-SSH local-image result is consumed, revoked, retained exactly, and cannot be reused'
