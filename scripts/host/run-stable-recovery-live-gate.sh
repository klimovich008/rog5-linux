#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

validate_temporary_boot_policy_header() {
	local input=$1 name_header status_header basis_header extra
	IFS=$'\t' read -r name_header status_header basis_header extra \
		<"$input" || fail 'malformed temporary-boot policy header'
	[[ $name_header == name && $status_header == status &&
		$basis_header == basis && -z $extra ]] ||
		fail 'malformed temporary-boot policy header'
}

validate_artifact_manifest_header() {
	local input=$1 name_header size_header sha_header role_header \
		tracked_header extra
	IFS=$'\t' read -r name_header size_header sha_header role_header \
		tracked_header extra <"$input" ||
		fail 'malformed artifact manifest header'
	[[ $name_header == name && $size_header == size &&
		$sha_header == sha256 && $role_header == role &&
		$tracked_header == tracked && -z $extra ]] ||
		fail 'malformed artifact manifest header'
}

validate_exact_boot_admission() {
	local policy=$1 inventory=$2 name=$3 basis=$4 sha=$5
	local expected_role=${6:-} expected_tracked=${7:-}
	local matches fields status found_basis identity role tracked
	validate_temporary_boot_policy_header "$policy"
	matches=$(awk -F '\t' -v name="$name" \
		'$1 == name { count++ } END { print count + 0 }' "$policy")
	[[ $matches == 1 ]] ||
		fail "temporary boot policy does not uniquely list $name"
	fields=$(awk -F '\t' -v name="$name" \
		'$1 == name { print NF; exit }' "$policy")
	[[ $fields == 3 ]] ||
		fail 'temporary boot policy row has trailing fields'
	status=$(awk -F '\t' -v name="$name" \
		'$1 == name { print $2; exit }' "$policy")
	found_basis=$(awk -F '\t' -v name="$name" \
		'$1 == name { print $3; exit }' "$policy")
	[[ $status == allow && -n $found_basis ]] ||
		fail "temporary boot policy does not allow $name"
	[[ $found_basis == "$basis" ]] ||
		fail "temporary boot policy basis does not match $name"

	validate_artifact_manifest_header "$inventory"
	matches=$(awk -F '\t' -v name="$name" \
		'$1 == name { count++ } END { print count + 0 }' "$inventory")
	[[ $matches == 1 ]] ||
		fail "artifact manifest does not uniquely list $name"
	fields=$(awk -F '\t' -v name="$name" \
		'$1 == name { print NF; exit }' "$inventory")
	[[ $fields == 5 ]] ||
		fail 'temporary boot artifact row has trailing fields'
	identity=$(awk -F '\t' -v name="$name" \
		'$1 == name { print $2 "\t" $3; exit }' "$inventory")
	[[ $identity == $'100663296\t'"$sha" ]] ||
		fail 'temporary boot artifact manifest identity is not allowlisted'
	role=$(awk -F '\t' -v name="$name" \
		'$1 == name { print $4; exit }' "$inventory")
	case $role in
		unbooted\ *) ;;
		consumed\ *) fail 'temporary boot artifact is recorded as consumed' ;;
		*) fail 'temporary boot artifact is not recorded as unbooted' ;;
	esac
	if [[ -n $expected_role ]]; then
		[[ $role == "$expected_role" ]] ||
			fail 'temporary boot artifact role does not match the pinned profile'
	fi
	tracked=$(awk -F '\t' -v name="$name" \
		'$1 == name { print $5; exit }' "$inventory")
	if [[ -n $expected_tracked ]]; then
		[[ $tracked == "$expected_tracked" ]] ||
			fail 'temporary boot artifact tracked state does not match the pinned profile'
	fi
}

action=${1:-preflight}
case $action in
	policy-preflight) ;;
	artifact-preflight) ;;
	preflight) ;;
	boot)
		[[ ${ALLOW_TEMPORARY_BOOT:-} == 1 ]] ||
			fail 'set ALLOW_TEMPORARY_BOOT=1 for one non-flashing boot'
		[[ ${ALLOW_HEADLESS_LIVE_GATE:-} == 1 ]] ||
			fail 'set ALLOW_HEADLESS_LIVE_GATE=1 for this attended candidate'
		;;
	*)
		fail 'usage: run-stable-recovery-live-gate.sh [policy-preflight|artifact-preflight|preflight|boot]'
		;;
esac

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
profile=${ROG5_STABLE_RECOVERY_PROFILE:-}
[[ -n $profile ]] ||
	fail 'set ROG5_STABLE_RECOVERY_PROFILE explicitly'
if [[ $action == policy-preflight ]]; then
	case $profile in
		headless-diagnostic-deployment-v1 | \
		headless-diagnostic-generation3-offline-v1 | \
		headless-diagnostic-generation3-live-v1 | \
		headless-diagnostic-generation4-offline-v1 | \
		headless-diagnostic-generation4-live-v1 | \
		headless-diagnostic-generation5-offline-v1 | \
		headless-diagnostic-generation5-live-v1 | \
		headless-diagnostic-generation6-offline-v1 | \
		headless-diagnostic-generation6-live-v1 | \
		headless-diagnostic-generation7-offline-v1 | \
		headless-diagnostic-generation7-live-v1 | \
		headless-diagnostic-generation8-offline-v1 | \
		headless-diagnostic-generation8-live-v1 | \
		headless-diagnostic-generation9-offline-v1 | \
		headless-diagnostic-generation9-live-v1 | \
		headless-diagnostic-generation10-offline-v1 | \
		headless-diagnostic-generation10-live-v1 | \
		headless-diagnostic-generation11-offline-v1 | \
		headless-diagnostic-generation11-live-v1 | \
		headless-diagnostic-generation12-offline-v1 | \
		headless-diagnostic-generation12-live-v1 | \
		headless-diagnostic-stage75-v2-superseded-offline-v1 | \
		headless-diagnostic-host-rendezvous-v3-haven-production-hold-v1 | \
		headless-diagnostic-host-rendezvous-v3-live-v2 | \
		headless-diagnostic-host-rendezvous-v3-live-v3 | \
		headless-diagnostic-host-rendezvous-v3-live-v4 | \
		headless-diagnostic-host-rendezvous-v3-live-v5 | \
		headless-diagnostic-host-rendezvous-v3-live-v6 | \
		headless-diagnostic-host-rendezvous-v3-live-v7 | \
		headless-diagnostic-host-rendezvous-v3-live-v8 | \
		headless-diagnostic-host-rendezvous-v3-live-v9 | \
		headless-diagnostic-host-rendezvous-v3-live-v10 | \
		headless-diagnostic-ssh-network-ready-v15-live-v1 | \
		headless-diagnostic-ssh-inert-block-v16-live-v1 | \
		retention-host-rendezvous-v3-execution-v1 | \
		retention-host-rendezvous-v11-mainline-udc-execution-v2 | \
		retention-host-rendezvous-v12-nfs-xattr-execution-v1) ;;
		*) fail 'policy preflight requires a fully pinned diagnostic profile' ;;
	esac
fi
live_root=${LIVE_BUILD_ROOT:-}
component_root=${RECOVERY_COMPONENT_ROOT:-}
trust_key=${TRUST_KEY:-}
bundle_root=${BUNDLE_ROOT:-}
bundle=${BUNDLE:-}
expected_image=${RECOVERY_SHA256:-}
expected_trust=${TRUST_KEY_SHA256:-}
expected_manifest=${MANIFEST_SHA256:-}
expected_host_verifier=${HOST_VERIFIER_SHA256:-}
expected_generation_record=
expected_avb_salt=
expected_avb_digest=
expected_boot_image=
expected_boot_basis=
expected_boot_role=
expected_boot_tracked=
admission_snapshot_dir=
early_boot_policy_snapshot=
early_artifact_manifest_snapshot=
fastboot=/usr/bin/fastboot
fastboot_serial=${FASTBOOT_SERIAL:-}
acm_timeout=${ACM_TIMEOUT:-90}
retention_boot_result=${ROG5_RETENTION_BOOT_RESULT:-0}
expected_usb_location=${ROG5_EXPECTED_USB_LOCATION:-}
component_layout=
expected_kernel=
expected_raw=
expected_initramfs=
expected_target_id=
expected_bundle=
expected_bundle_profile=network-root-v1
initramfs_contract=
initramfs_verifier_expected=
recovery_init=-
consumed_deployment_manifest=457273993a9ce3cb0a9c735ef29e96101c1303720cafefc774aed12972a6926e
consumed_r2_manifest=9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630
consumed_diagnostic_recovery=9c060a27f21f6f99ca0c00cd1ff2ed9532220d585cd726b194f8b6d04e6204ef
consumed_corrected_diagnostic_recovery=f710bbcd1f9602f0fdc3ce7023298f66cc5e7a014a0627c4f9123d7cc897b0ef
consumed_listener_successor_recovery=332889a83f541ed0e17c94656836c512a35b5bfd6bbbaf735d2f5f6b94b51830
consumed_nfs_gated_generation2_recovery=70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1
requires_qualified_cpio=0
expected_control=c1e1b7b58f36b9ff091bed3b5de463d6239031729a49e12c07064c410de43fd0
expected_fetcher=becc3fc1442823118fa75e79a9b756395df9f1b5b7df37440d4e2c8c5b4ef89c
expected_verifier=374900be5769eee074820007ab2e335d4c033c500da7a480cc88f9a70137029b
expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
avbtool=
unpack=
initramfs_path=$PATH
qualified_cpio=
qualified_cpio_shim=

[[ -n $bundle ]] || fail 'set the exact bundle input'
if [[ $action != policy-preflight ]]; then
	[[ -n $live_root && -n $component_root && -n $trust_key &&
		-n $bundle_root ]] ||
		fail 'set live-build, component, trust-key, and bundle inputs'
fi
for value in "$expected_image" "$expected_trust" "$expected_manifest" \
	"$expected_host_verifier"; do
	[[ $value =~ ^[0-9a-f]{64}$ &&
		$value != 0000000000000000000000000000000000000000000000000000000000000000 ]] ||
		fail 'every expected identity must be one nonzero SHA-256'
done
[[ $bundle =~ ^[a-z0-9][a-z0-9._-]{0,63}$ &&
	$bundle != *..* && $bundle != none ]] ||
	fail 'invalid bundle identity'
if [[ $action == boot &&
	( $expected_manifest == "$consumed_deployment_manifest" ||
	$expected_manifest == "$consumed_r2_manifest" ) ]]; then
	fail 'refusing a consumed deployment manifest'
fi
if [[ $expected_image == "$consumed_diagnostic_recovery" ||
	$expected_image == "$consumed_corrected_diagnostic_recovery" ||
	$expected_image == "$consumed_listener_successor_recovery" ]]; then
	fail 'refusing the consumed diagnostic recovery image'
fi
if [[ $action == boot &&
	$expected_image == "$consumed_nfs_gated_generation2_recovery" ]]; then
	fail 'refusing the consumed generation-2 diagnostic recovery image'
fi
case $profile in
	historical-2026-07-29)
		component_layout=flat
		expected_kernel=91732d1bdbf73c5f574d87eb0d07b5394db2889e4c0dc4b258577a0bcdb0101f
		expected_raw=854c48adb4316bc8496579ebab78cfbbd3e0550fe0c5204ae3c5661187818fb4
		expected_initramfs=6245147d464985df3d861d2b177ea39f6132767b45c07e39a131fecf3bf69aa2
		expected_target_id=headless-network-root
		avbtool=$repo/../work/linux-server/avb/avbtool.py
		unpack=$repo/../work/linux-server/mkbootimg/unpack_bootimg.py
		;;
	corrected-headless-successor-2026-07-30)
		component_layout=structured
		expected_kernel=bc42d9ffc78ed88c5e8f597905844e472a5681c57caab020ce88c1eae1b706da
		expected_raw=157da94bf50635099c571ce97d3e3c797c22eb66e3b9730b4ea332d952a9261c
		expected_initramfs=ac5fd5169be86a44b01e8e2d5d5343feddf9ffdc34ea3581a430c5cbc2962c04
		expected_target_id=headless-network-root
		[[ $expected_image == \
			416d62e4f0d89e9184d8a362c8c9e5091bd265f4c48504916920706f08611430 ]] ||
			fail 'successor recovery image identity is not allowlisted'
		[[ $expected_trust == \
			ce9f89c9c1859a3239615932da36617f3436f9a0355c8db9c852a1b764f2dfeb ]] ||
			fail 'successor recovery trust root is not allowlisted'
		[[ $expected_manifest == \
			d7a02a2403caf885a015060a8361019936e86efafde44f3bb7e6bdd48d2ee32d ]] ||
			fail 'successor runtime manifest is not allowlisted'
		[[ $expected_host_verifier == \
			9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b ]] ||
			fail 'successor host verifier is not allowlisted'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-ssh-deployment-v3)
		component_layout=structured
		expected_kernel=1a8bac7a2b016dc7d63d22f09d0872b9c3f251952b7627c68f7c387f386b0068
		expected_raw=a937b03b54c01c6240cff45aa243632827d0c9d328e6f285ae489c973a6213a9
		expected_initramfs=f414d0ea26ee3aa6cca5c3aa12c1601934294c0207fc2709ebbae305bb3642e0
		expected_control=f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77
		expected_fetcher=677fa731b1bd9fd11efc46aabeb32e7a725725483c86a2f58d417f482c27f392
		expected_verifier=374900be5769eee074820007ab2e335d4c033c500da7a480cc88f9a70137029b
		expected_target_id=headless-ssh-network-root
		expected_bundle=headless-ssh-network-root-v3-r2
		[[ $expected_manifest == \
			9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630 ]] ||
			fail 'deployment runtime manifest is not allowlisted'
		[[ $expected_image == \
			11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c ]] ||
			fail 'deployment recovery image identity is not allowlisted'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'deployment recovery trust root is not allowlisted'
		[[ $expected_host_verifier == \
			9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b ]] ||
			fail 'deployment host verifier is not allowlisted'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-deployment-v1)
		[[ $action == policy-preflight || $action == artifact-preflight ]] ||
			fail 'historical diagnostic profile is offline-only and consumed'
		component_layout=structured
		expected_kernel=7fac4dda6a7133e7d3a6589da4fb5d0bdad3802705da5edf52701a20133728ed
		expected_raw=2f460aa01ee1b97c495d0857b3207bf74920487c56f30c5e155e199967628a01
		expected_initramfs=fec72c4dba62a24ced899af4d4fc3d0af3b7b691ea6f6c1bcf90c7aaf181c57a
		expected_control=f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77
		expected_fetcher=f410ca875031dcf9c41cf2c8a67e5a9fba862cf50b53e1d8c51453f4e0b5d13d
		expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0
		expected_target_id=headless-netroot-early-diag
		expected_bundle=headless-netroot-early-diag-v1
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=4a1de575f2c428ae2625e38a37f31fa70850ce64895cf549509434d806e8d109
		expected_avb_salt=8f20854a98ee31fa889c5bfe2b7818ed42c5ed6186b671a55b3f57835c87e712
		expected_avb_digest=903826e0579863b0290004f5f415aecfcee1384f5b81a949ddd8845c880a7541
		[[ $expected_manifest == \
			4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 ]] ||
			fail 'diagnostic runtime manifest is not allowlisted'
		[[ $expected_image == \
			70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1 ]] ||
			fail 'diagnostic recovery image identity is not allowlisted'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'diagnostic recovery trust root is not allowlisted'
		[[ $expected_host_verifier == \
			0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 ]] ||
			fail 'diagnostic host verifier is not allowlisted'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-generation3-offline-v1 | \
	headless-diagnostic-generation3-live-v1)
		if [[ $profile == headless-diagnostic-generation3-offline-v1 &&
			$action != policy-preflight && $action != artifact-preflight ]]; then
			fail 'generation-3 diagnostic profile is offline-only and not boot-authorized'
		fi
		if [[ $profile == headless-diagnostic-generation3-live-v1 &&
			$action == boot &&
			${ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE:-} != 1 ]]; then
			fail 'generation-3 boot requires the one-shot lifecycle controller'
		fi
		# This is a fresh twin build, not an AVB-generation issuer output;
		# expected_generation_record intentionally remains empty.
		component_layout=structured
		expected_kernel=8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c
		expected_raw=f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce
		expected_initramfs=144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec
		expected_control=f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0
		expected_target_id=headless-netroot-early-diag
		expected_bundle=headless-netroot-early-diag-v1
		expected_bundle_profile=diagnostic-initramfs-v1
		# The production builder deterministically uses the raw wrapper digest
		# as the AVB salt; equality here is intentional.
		expected_avb_salt=f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce
		expected_avb_digest=6de238c36bd8325d2a6f431f27ee39e5d7bab81d9fe91bd6d3d0bad48ba3c60d
		[[ $expected_manifest == \
			4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 ]] ||
			fail 'generation-3 diagnostic runtime manifest is not pinned'
		[[ $expected_image == \
			eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6 ]] ||
			fail 'generation-3 diagnostic recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'generation-3 diagnostic trust root is not pinned'
		[[ $expected_host_verifier == \
			0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 ]] ||
			fail 'generation-3 diagnostic host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-generation4-offline-v1 | \
	headless-diagnostic-generation4-live-v1)
		if [[ $profile == headless-diagnostic-generation4-offline-v1 &&
			$action != policy-preflight && $action != artifact-preflight ]]; then
			fail 'generation-4 diagnostic profile is offline-only and not boot-authorized'
		fi
		if [[ $profile == headless-diagnostic-generation4-live-v1 &&
			$action == boot &&
			${ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE:-} != 1 ]]; then
			fail 'generation-4 boot requires the one-shot lifecycle controller'
		fi
		component_layout=structured
		expected_kernel=8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c
		expected_raw=f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce
		expected_initramfs=144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec
		expected_control=f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0
		expected_target_id=headless-netroot-early-diag
		expected_bundle=headless-netroot-early-diag-v1
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=8e537a2eae12c0d58d6a37a23816031f9a1a4e83b37679c3321c60aa688d3dc4
		expected_avb_salt=82fd20a6c16d7e0387568beb0ada378ea513119fa4480064c6afa5b3dfa567f8
		expected_avb_digest=3e8fc9703763bd9572141f909f8e79881dd689ddd3123ec76ce45b13f0708562
		[[ $expected_manifest == \
			4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 ]] ||
			fail 'generation-4 diagnostic runtime manifest is not pinned'
		[[ $expected_image == \
			220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d ]] ||
			fail 'generation-4 diagnostic recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'generation-4 diagnostic trust root is not pinned'
		[[ $expected_host_verifier == \
			0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 ]] ||
			fail 'generation-4 diagnostic host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-generation5-offline-v1 | \
	headless-diagnostic-generation5-live-v1)
		if [[ $profile == headless-diagnostic-generation5-offline-v1 &&
			$action != policy-preflight && $action != artifact-preflight ]]; then
			fail 'generation-5 diagnostic profile is offline-only and not boot-authorized'
		fi
		if [[ $profile == headless-diagnostic-generation5-live-v1 &&
			$action == boot &&
			${ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE:-} != 1 ]]; then
			fail 'generation-5 boot requires the one-shot lifecycle controller'
		fi
		component_layout=structured
		expected_kernel=8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c
		expected_raw=f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce
		expected_initramfs=144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec
		expected_control=f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0
		expected_target_id=headless-netroot-early-diag
		expected_bundle=headless-netroot-early-diag-v1
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=7d1a1071df1dcc4172c9f1e28ab5b62d6c44670b21f075f775de587f789cf98f
		expected_avb_salt=818427845bc55deb8167fbb205fb672f2edfb3b465160109dacc0f4d65a9f306
		expected_avb_digest=b1a6bb43d26230e3c623332703998459d51b37fc8244c051287c8291f9e213b0
		[[ $expected_manifest == \
			4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 ]] ||
			fail 'generation-5 diagnostic runtime manifest is not pinned'
		[[ $expected_image == \
			abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a ]] ||
			fail 'generation-5 diagnostic recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'generation-5 diagnostic trust root is not pinned'
		[[ $expected_host_verifier == \
			0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 ]] ||
			fail 'generation-5 diagnostic host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-generation6-offline-v1 | \
	headless-diagnostic-generation6-live-v1)
		if [[ $profile == headless-diagnostic-generation6-offline-v1 &&
			$action != policy-preflight && $action != artifact-preflight ]]; then
			fail 'generation-6 diagnostic profile is offline-only and not boot-authorized'
		fi
		if [[ $profile == headless-diagnostic-generation6-live-v1 &&
			$action == boot &&
			${ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE:-} != 1 ]]; then
			fail 'generation-6 boot requires the one-shot lifecycle controller'
		fi
		component_layout=structured
		expected_kernel=8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c
		expected_raw=f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce
		expected_initramfs=144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec
		expected_control=f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0
		expected_target_id=headless-netroot-early-diag
		expected_bundle=headless-netroot-early-diag-v1
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=bff8432e20e01f74132addda464120886c5090b079798054fe359845b1a552a2
		expected_avb_salt=66d5537af0ff592b94ab516306ad03643ee48b15e90e49cb3c990e786031fbe8
		expected_avb_digest=47c517b5c066671b32728076e3b4a5836e839efa9f2ba878659156cffdf0d461
		[[ $expected_manifest == \
			4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 ]] ||
			fail 'generation-6 diagnostic runtime manifest is not pinned'
		[[ $expected_image == \
			6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398 ]] ||
			fail 'generation-6 diagnostic recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'generation-6 diagnostic trust root is not pinned'
		[[ $expected_host_verifier == \
			0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 ]] ||
			fail 'generation-6 diagnostic host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-generation7-offline-v1 | \
	headless-diagnostic-generation7-live-v1)
		if [[ $profile == headless-diagnostic-generation7-offline-v1 &&
			$action != policy-preflight && $action != artifact-preflight ]]; then
			fail 'generation-7 diagnostic profile is offline-only and not boot-authorized'
		fi
		if [[ $profile == headless-diagnostic-generation7-live-v1 &&
			$action == boot &&
			${ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE:-} != 1 ]]; then
			fail 'generation-7 boot requires the one-shot lifecycle controller'
		fi
		component_layout=structured
		expected_kernel=8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c
		expected_raw=f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce
		expected_initramfs=144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec
		expected_control=f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0
		expected_target_id=headless-netroot-early-diag
		expected_bundle=headless-netroot-early-diag-v1
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=8127197dcf0704bf7bee81a7b25a604fb9e7c9b752ba6d9523e073de2bf9799e
		expected_avb_salt=47daea8fa91810575df6d694bd5e3949eb6295920f7b980eb8935e86950506e4
		expected_avb_digest=5690894d337769a462828bc786de74724abf89115c1e456b8e4064ab6831b86b
		[[ $expected_manifest == \
			4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 ]] ||
			fail 'generation-7 diagnostic runtime manifest is not pinned'
		[[ $expected_image == \
			d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901 ]] ||
			fail 'generation-7 diagnostic recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'generation-7 diagnostic trust root is not pinned'
		[[ $expected_host_verifier == \
			0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 ]] ||
			fail 'generation-7 diagnostic host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-generation8-offline-v1 | \
	headless-diagnostic-generation8-live-v1)
		if [[ $profile == headless-diagnostic-generation8-offline-v1 &&
			$action != policy-preflight && $action != artifact-preflight ]]; then
			fail 'generation-8 diagnostic profile is offline-only and not boot-authorized'
		fi
		if [[ $profile == headless-diagnostic-generation8-live-v1 &&
			( $action == preflight || $action == boot ) &&
			${ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE:-} != 1 ]]; then
			fail 'generation-8 connected action requires the one-shot lifecycle controller'
		fi
		component_layout=structured
		expected_kernel=8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c
		expected_raw=f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce
		expected_initramfs=144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec
		expected_control=f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0
		expected_target_id=headless-netroot-early-diag
		expected_bundle=headless-netroot-early-diag-v1
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=9805809c27e1fe47efcbc7561fe5289e81d789beba231acbac59c32a67ae59d5
		expected_avb_salt=a8563ded9a34767ed97ed4f9130361a1b4efadc91ee7294d9a212caf59e53899
		expected_avb_digest=b297100d269798d4eaf46b37899c3cf9196f7c076df3a31d39fe3d2db5915dbc
		expected_boot_image=build/stable-recovery-generation8-nmcli-empty-field-fix-20260803-a/repack/stable-recovery-a.avb.img
		expected_boot_basis='one generation-8 NetworkManager-empty-field-corrected diagnostic lifecycle after connected preflight; remove after any result; never flash'
		[[ $expected_manifest == \
			4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 ]] ||
			fail 'generation-8 diagnostic runtime manifest is not pinned'
		[[ $expected_image == \
			f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415 ]] ||
			fail 'generation-8 diagnostic recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'generation-8 diagnostic trust root is not pinned'
		[[ $expected_host_verifier == \
			0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 ]] ||
			fail 'generation-8 diagnostic host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-generation9-offline-v1 | \
	headless-diagnostic-generation9-live-v1)
		if [[ $profile == headless-diagnostic-generation9-offline-v1 &&
			$action != policy-preflight && $action != artifact-preflight ]]; then
			fail 'generation-9 diagnostic profile is offline-only and not boot-authorized'
		fi
		if [[ $profile == headless-diagnostic-generation9-live-v1 &&
			( $action == preflight || $action == boot ) &&
			${ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE:-} != 1 ]]; then
			fail 'generation-9 connected action requires the one-shot lifecycle controller'
		fi
		component_layout=structured
		expected_kernel=8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c
		expected_raw=f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce
		expected_initramfs=144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec
		expected_control=f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0
		expected_target_id=headless-netroot-early-diag
		expected_bundle=headless-netroot-early-diag-v1
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=29beac5ec4ef88194927283a45427fcc89b95f94c4afa4fda9d6b24301fc9961
		expected_avb_salt=4ddc34b9dace6d11338be71dba16797ff38e8f8e9e572cd61a6b1434c18b59df
		expected_avb_digest=8c97c36eed4dab241bc3353b8f70dc0ece8301fb795362cb129fe331af6c8dc0
		if [[ $profile == headless-diagnostic-generation9-live-v1 ]]; then
			expected_boot_image=build/stable-recovery-generation9-acm-classifier-20260803-a/repack/stable-recovery-a.avb.img
			expected_boot_basis='one generation-9 recovery-ACM-classifier diagnostic lifecycle after connected preflight; remove after any result; never flash'
		fi
		[[ $expected_manifest == \
			4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 ]] ||
			fail 'generation-9 diagnostic runtime manifest is not pinned'
		[[ $expected_image == \
			b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008 ]] ||
			fail 'generation-9 diagnostic recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'generation-9 diagnostic trust root is not pinned'
		[[ $expected_host_verifier == \
			0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 ]] ||
			fail 'generation-9 diagnostic host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-generation10-offline-v1 | \
	headless-diagnostic-generation10-live-v1)
		if [[ $profile == headless-diagnostic-generation10-offline-v1 &&
			$action != policy-preflight && $action != artifact-preflight ]]; then
			fail 'generation-10 diagnostic profile is offline-only and not boot-authorized'
		fi
		if [[ $profile == headless-diagnostic-generation10-live-v1 &&
			$action != policy-preflight && $action != artifact-preflight &&
			${ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE:-} != 1 ]]; then
			fail 'generation-10 connected action requires the one-shot lifecycle controller'
		fi
		component_layout=structured
		expected_kernel=bb49b4057ce573e3a53366c4663094cf462efb09d496b64b890ed2b0dcb65f98
		expected_raw=27f4dbcc61decd00ce6861cddb021070f38e9badde99152fc2dedbd4103d73b3
		expected_initramfs=99046d30e0910531ebda1163719ae8b5b81489f11329e29e12195fbfd63c6e31
		expected_control=67b4f012aab21e7b29934d3d6e41949aca5e46fdf90e9578ad5f6c87a3f2c167
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0
		expected_target_id=headless-netroot-early-diag
		expected_bundle=headless-netroot-early-diag-v1
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=cb999cd881959055f32fc1b7299cf1dffcf139656ff8c326ea1101d2ffd63b6d
		expected_avb_salt=5f62ef87305b45de2d189729a601ac4b143c45e83485272ef5b91c508df5d3ee
		expected_avb_digest=32b0de39bd409601da6b8c16bf5039fe9102410d9fb13a8b9f668283d53aee42
		if [[ $profile == headless-diagnostic-generation10-live-v1 ]]; then
			expected_boot_image=build/stable-recovery-generation10-prepare-progress-20260803-a/repack/stable-recovery-a.avb.img
			expected_boot_basis='one generation-10 PREPARE-progress-instrumented diagnostic lifecycle after connected preflight; remove after any result; never flash'
		fi
		[[ $expected_manifest == \
			4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 ]] ||
			fail 'generation-10 diagnostic runtime manifest is not pinned'
		[[ $expected_image == \
			b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51 ]] ||
			fail 'generation-10 diagnostic recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'generation-10 diagnostic trust root is not pinned'
		[[ $expected_host_verifier == \
			0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 ]] ||
			fail 'generation-10 diagnostic host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-generation11-offline-v1 | \
	headless-diagnostic-generation11-live-v1)
		if [[ $profile == headless-diagnostic-generation11-offline-v1 &&
			$action != policy-preflight && $action != artifact-preflight ]]; then
			fail 'generation-11 diagnostic profile is offline-only and not boot-authorized'
		fi
		if [[ $profile == headless-diagnostic-generation11-live-v1 &&
			$action != policy-preflight && $action != artifact-preflight &&
			${ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE:-} != 1 ]]; then
			fail 'generation-11 connected action requires the one-shot lifecycle controller'
		fi
		component_layout=structured
		expected_kernel=895272e87d5a90ae6b9b8df71862b48d819479d5bbf2741fab002126e47d3eae
		expected_raw=44c43e27ba0cdb646eb3a6327c519011090f64b1e76ec67e2ff9db469e6612b2
		expected_initramfs=3695ded23cc422f8363235884cb3cc402c0c90eeddee04d0603c09befd0f6a8c
		expected_control=242ac7fc4b7d7614cf5fe8a26162255c898de2f2aeef9cf70687d0d327c149e7
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0
		expected_target_id=headless-netroot-early-diag
		expected_bundle=headless-netroot-early-diag-v1
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=4b62b7906ad40f2a36b52a9756a7250364dfe6d9eff4b0c57d25f60713145e49
		expected_avb_salt=00272b827ebb11f198be4758db4008cf534f592f0e63fc82c891cda3b4691c6d
		expected_avb_digest=9ccf32a823f5a4685922ed42400bc024d7210412216537cfffb1c128e17febf9
		if [[ $profile == headless-diagnostic-generation11-live-v1 ]]; then
			expected_boot_image=build/stable-recovery-generation11-ncm-progress-20260804-a/repack/stable-recovery-a.avb.img
			expected_boot_basis='one generation-11 receive-only NCM-progress diagnostic lifecycle after connected preflight; remove after any result; never flash'
		fi
		[[ $expected_manifest == \
			4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 ]] ||
			fail 'generation-11 diagnostic runtime manifest is not pinned'
		[[ $expected_image == \
			8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562 ]] ||
			fail 'generation-11 diagnostic recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'generation-11 diagnostic trust root is not pinned'
		[[ $expected_host_verifier == \
			0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 ]] ||
			fail 'generation-11 diagnostic host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-generation12-offline-v1 | \
	headless-diagnostic-generation12-live-v1)
		if [[ $profile == headless-diagnostic-generation12-offline-v1 &&
			$action != policy-preflight && $action != artifact-preflight ]]; then
			fail 'generation-12 diagnostic profile is offline-only and not boot-authorized'
		fi
		if [[ $profile == headless-diagnostic-generation12-live-v1 &&
			$action != policy-preflight && $action != artifact-preflight ]]; then
			fail 'generation-12 is consumed and cannot enter connected preflight or boot'
		fi
		component_layout=structured
		expected_kernel=895272e87d5a90ae6b9b8df71862b48d819479d5bbf2741fab002126e47d3eae
		expected_raw=44c43e27ba0cdb646eb3a6327c519011090f64b1e76ec67e2ff9db469e6612b2
		expected_initramfs=3695ded23cc422f8363235884cb3cc402c0c90eeddee04d0603c09befd0f6a8c
		expected_control=242ac7fc4b7d7614cf5fe8a26162255c898de2f2aeef9cf70687d0d327c149e7
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0
		expected_target_id=headless-netroot-early-diag
		expected_bundle=headless-netroot-early-diag-v1
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=2b8a05d4655a4794ae4ee5ce9fe1279b194dec39d3a4bfcb93904cc665192c72
		expected_avb_salt=728dcc59f29e0fbf83165b6979bb5dc68571b0d0e0236993fc9b8f2dd98084c9
		expected_avb_digest=31d1ec59526d876de914330004d42752cfc7b24bd069b955d64687ef750b526d
		if [[ $profile == headless-diagnostic-generation12-live-v1 ]]; then
			expected_boot_role='consumed generation-12 host-confinement-corrected diagnostic recovery; one RAM-only lifecycle transferred the exact 46163787-byte signed bundle and recovery accepted correlated PREPARE and COMMIT; receive-only target evidence reached stage 70 nfs-mount-begin, then USB disconnected before stage 80 nfs-mount-ok with no terminal fault frame; the lifecycle host parser separately misclassified the valid postmortem-extended PREPARE response after commit, then the durable intent resolved FALLBACK_RETURNED; exact Alpine fallback, strict SSH, profile restoration, final host cleanup, and Steam socket restoration passed; no target acceptance; retain offline only; never retry or flash'
		fi
		[[ $expected_manifest == \
			4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 ]] ||
			fail 'generation-12 diagnostic runtime manifest is not pinned'
		[[ $expected_image == \
			615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6 ]] ||
			fail 'generation-12 diagnostic recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'generation-12 diagnostic trust root is not pinned'
		[[ $expected_host_verifier == \
			0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 ]] ||
			fail 'generation-12 diagnostic host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-stage75-v2-superseded-offline-v1)
		[[ $action == policy-preflight || $action == artifact-preflight ]] ||
			fail 'superseded stage-75 v2 artifact profile is historical, offline-only, and not boot-authorized'
		component_layout=structured
		expected_kernel=7a6c2a19c7a00a2699fd598b4fc3ad5fed680bf2cd9cb7cfa7bafa783d9fe563
		expected_raw=406b2497bff8174b01119e4bcfa4dddb544df3de8fdb9168d80e88708f20a995
		expected_initramfs=a38b61462468272c8d8409461d7318cfc442c3a4707a624e9f8ab1751ef047a4
		expected_control=242ac7fc4b7d7614cf5fe8a26162255c898de2f2aeef9cf70687d0d327c149e7
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0
		expected_target_id=headless-netroot-early-diag-v2
		expected_bundle=headless-netroot-early-diag-v2
		expected_bundle_profile=diagnostic-initramfs-v1
		# The deterministic builder intentionally derives the AVB salt from the
		# complete raw-wrapper digest; equality is independently checked here.
		expected_avb_salt=406b2497bff8174b01119e4bcfa4dddb544df3de8fdb9168d80e88708f20a995
		expected_avb_digest=a1d19575dd21b6da3fd3cbb6c0f4ea33e312cc59ddc860889f1f54ef976e7b49
		[[ $expected_manifest == \
			2fb99ba07676d696fd3182da6bf62bd572b032b9e4bb90bff4b0d2a24544e156 ]] ||
			fail 'stage-75 v2 diagnostic runtime manifest is not pinned'
		[[ $expected_image == \
			833899cb067a28d57e41c5a8291c7f5099c4f7fcc11316c2976d04a7b926e7de ]] ||
			fail 'stage-75 v2 diagnostic recovery image is not pinned'
		[[ $expected_trust == \
			58950b2101dca0702f2c436015bbb21eb6535e4e06f74808c2f8183c9da27268 ]] ||
			fail 'stage-75 v2 diagnostic trust root is not pinned'
		[[ $expected_host_verifier == \
			0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 ]] ||
			fail 'stage-75 v2 diagnostic host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-host-rendezvous-v3-haven-production-hold-v1 | \
	headless-diagnostic-host-rendezvous-v3-live-v2 | \
	headless-diagnostic-host-rendezvous-v3-live-v3 | \
	retention-host-rendezvous-v3-execution-v1)
		if [[ $profile == \
			headless-diagnostic-host-rendezvous-v3-haven-production-hold-v1 ]]; then
			[[ $action == policy-preflight || $action == artifact-preflight ]] ||
				fail 'current production HOLD profile is offline-only and not boot-authorized'
		else
			expected_boot_image=build/host-rendezvous-v3-haven-production-20260810-r2/wrapper/repack/stable-recovery-a.avb.img
			expected_boot_basis='one retention-cycle execution recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
			expected_boot_role='unbooted retention-cycle execution recovery with Haven watchdog deactivation and bounded host rendezvous; one RAM-only use only; never flash'
			expected_boot_tracked=no
		fi
		component_layout=structured
		expected_kernel=8a600acfc6f7e01f9eb932e0a04174079d6ee68142c44fad819fe96bbd34325d
		expected_raw=ea9e90fdbf1bfdbe75816462ae79897e6cf7749d9e87607be2b033b7cfb06517
		expected_initramfs=ab0a3ee219684c994af386cb60e5280dcc4269457b196f96ca3928acce691f0b
		expected_control=68142abd8daafed2f1d017bd0ae07407be9dcac17e57d2294a162d2b58bf2840
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef
		expected_target_id=headless-netroot-early-diag-v2
		expected_bundle=headless-netroot-early-diag-v2
		expected_bundle_profile=diagnostic-initramfs-v1
		# The production builder deterministically uses the raw wrapper digest
		# as the AVB salt; equality here is intentional.
		expected_avb_salt=ea9e90fdbf1bfdbe75816462ae79897e6cf7749d9e87607be2b033b7cfb06517
		expected_avb_digest=9647a92d83bc1d3a71a59742d8aacd8d05b9e5105ac729c792e6577ef9af52eb
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc ]] ||
			fail 'current production runtime manifest is not pinned'
		[[ $expected_image == \
			cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d ]] ||
			fail 'current production recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'current production trust key is not pinned'
		[[ $expected_host_verifier == \
			03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0 ]] ||
			fail 'current production host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-host-rendezvous-v3-live-v4)
		expected_boot_image=build/host-rendezvous-v4-udc-inventory-production-20260810-r1/wrapper/repack/stable-recovery-a.avb.img
		expected_boot_basis='one UDC-inventory-corrected diagnostic execution recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted UDC-inventory-corrected diagnostic execution recovery; exact ASUS wrapper inventory and bounded host rendezvous; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=88da6fc4ee6ec61614324678805a5af6591320bc1b2ede2b094ce6aad5bd1a1f
		expected_raw=73b6a892ca7066b2bbc399602ace9f8664f157e1b0e99c91d6e907da80e9f70f
		expected_initramfs=04c52bbd9cbaedc442faeba83fdc7eb2291be28519e54ea0dd3ade40acbd6948
		expected_control=68142abd8daafed2f1d017bd0ae07407be9dcac17e57d2294a162d2b58bf2840
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef
		expected_target_id=headless-netroot-early-diag-v2
		expected_bundle=headless-netroot-early-diag-v2
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_avb_salt=73b6a892ca7066b2bbc399602ace9f8664f157e1b0e99c91d6e907da80e9f70f
		expected_avb_digest=0d5fc07e0a3ea5bce7fa52c334cf9ec400b95594613bbd093972c785bc199756
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc ]] ||
			fail 'UDC-inventory successor runtime manifest is not pinned'
		[[ $expected_image == \
			ee662ab9e057449abfdfedb7a273246fcba62c78ad159f9ac35f0ca36ceb6752 ]] ||
			fail 'UDC-inventory successor recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'UDC-inventory successor trust key is not pinned'
		[[ $expected_host_verifier == \
			03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0 ]] ||
			fail 'UDC-inventory successor host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-host-rendezvous-v3-live-v5)
		expected_boot_image=build/host-rendezvous-v5-usb-ancestry-production-20260810-r1/wrapper/repack/stable-recovery-a.avb.img
		expected_boot_basis='one USB-ancestry-corrected diagnostic execution recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted USB-ancestry-corrected diagnostic execution recovery; deterministic AVB generation over the unchanged clean-twin UDC-corrected raw wrapper and bounded host rendezvous; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=88da6fc4ee6ec61614324678805a5af6591320bc1b2ede2b094ce6aad5bd1a1f
		expected_raw=73b6a892ca7066b2bbc399602ace9f8664f157e1b0e99c91d6e907da80e9f70f
		expected_initramfs=04c52bbd9cbaedc442faeba83fdc7eb2291be28519e54ea0dd3ade40acbd6948
		expected_control=68142abd8daafed2f1d017bd0ae07407be9dcac17e57d2294a162d2b58bf2840
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef
		expected_target_id=headless-netroot-early-diag-v2
		expected_bundle=headless-netroot-early-diag-v2
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=481c59b10a0db36277aed87dd8badfab0095e9f974bd7a97fb1405592ca87ef9
		expected_avb_salt=eb9271e8c053ba1e774ee26c3b89ddc50f31e97baa48a916f6b3983d7e5e1542
		expected_avb_digest=70d63810c2909150a7467ba625f75a8a4562ba8524060a90355c2f3c95d43cb1
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc ]] ||
			fail 'USB-ancestry successor runtime manifest is not pinned'
		[[ $expected_image == \
			e4ae63731f3369914cd382367e6abb4371f526c5417ab9436453cd58e764c722 ]] ||
			fail 'USB-ancestry successor recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'USB-ancestry successor trust key is not pinned'
		[[ $expected_host_verifier == \
			03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0 ]] ||
			fail 'USB-ancestry successor host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-host-rendezvous-v3-live-v6)
		expected_boot_image=build/host-rendezvous-v6-post-claim-status-production-20260810-r1/wrapper/repack/stable-recovery-a.avb.img
		expected_boot_basis='one post-claim-status diagnostic execution recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted post-claim-status diagnostic execution recovery; deterministic AVB generation over the unchanged clean-twin UDC-corrected raw wrapper; bounded host STATUS discriminates recovery return from target USB departure; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=88da6fc4ee6ec61614324678805a5af6591320bc1b2ede2b094ce6aad5bd1a1f
		expected_raw=73b6a892ca7066b2bbc399602ace9f8664f157e1b0e99c91d6e907da80e9f70f
		expected_initramfs=04c52bbd9cbaedc442faeba83fdc7eb2291be28519e54ea0dd3ade40acbd6948
		expected_control=68142abd8daafed2f1d017bd0ae07407be9dcac17e57d2294a162d2b58bf2840
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef
		expected_target_id=headless-netroot-early-diag-v2
		expected_bundle=headless-netroot-early-diag-v2
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=fd5ff56ef6ecdccf1e71a7e0104ca92333374b20d558681f5578d4fc6548a74a
		expected_avb_salt=c8877b5ea58252c75fc700049784ce164c3575f829733d0c0826f1a32a42648c
		expected_avb_digest=1413c008c0ddbfe20a2322df6a5313b24aa44b7259e511d23e126ef1e7c75527
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc ]] ||
			fail 'post-claim-status successor runtime manifest is not pinned'
		[[ $expected_image == \
			43613a11e23620787d25b4b4267a9e6922b9591d2ddcda086d9c97075fd8eb0a ]] ||
			fail 'post-claim-status successor recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'post-claim-status successor trust key is not pinned'
		[[ $expected_host_verifier == \
			03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0 ]] ||
			fail 'post-claim-status successor host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-host-rendezvous-v3-live-v7)
		expected_boot_image=build/host-rendezvous-v7-haven-reason-production-20260810-r1/wrapper/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact Haven-failure-classification diagnostic execution recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted exact Haven-failure-classification diagnostic execution recovery; clean-twin ASUS wrapper distinguishes secure, hypervisor, and unclassified recovery watchdog deactivation failures before kexec; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=feb2637696b9a7bc739c87c621aa0dbd234ba0c1bd6a769c82248727111d4ae3
		expected_raw=018e46c7f416020e0afc3f42789ad4339baf9a2f5d30c1a212aae1249e341bc1
		expected_initramfs=373d08f64244c0f4322eed7e3720a46f1ff56f4ec355a327153758e912b25546
		expected_control=b4e08b2725980117a172ed117a1260f3940304790e857be8ee1ae4c706fe6d9e
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef
		expected_target_id=headless-netroot-early-diag-v2
		expected_bundle=headless-netroot-early-diag-v2
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=3a272ff018ead9a81a0c00d5f477c6af984d19927ef1f4ebeae720de0365c745
		expected_avb_salt=6abc5a841e8060cc5e3a02ef6cfb84f035eded57da6c19af23758d9f59235e68
		expected_avb_digest=408caa4149d954b26f5225de27248bed928457581a84314b6d845a26f1ddf178
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc ]] ||
			fail 'Haven-classification successor runtime manifest is not pinned'
		[[ $expected_image == \
			0dc48152b932b94334238a96fedaaa3dd1865eb010e747877f38ce654bd28be2 ]] ||
			fail 'Haven-classification successor recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'Haven-classification successor trust key is not pinned'
		[[ $expected_host_verifier == \
			03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0 ]] ||
			fail 'Haven-classification successor host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-host-rendezvous-v3-live-v8)
		expected_boot_image=build/host-rendezvous-v8-haven-boundary-production-20260810-r2/wrapper/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact Haven-boundary-classification diagnostic execution recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted exact Haven-boundary-classification diagnostic execution recovery; clean-twin ASUS wrapper distinguishes every reviewed fail-closed watchdog handoff boundary before kexec; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=01087419a9381ab4967dd9aad8d78873979f33e3906139865af9db049471942d
		expected_raw=d087aaae42699a4889341326407dc231084d1f008013f0970136883c632a94f5
		expected_initramfs=9410b1a6735675023bdf18c7f02e6d9f4dde9e8c25820913e575f030922e6aa1
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef
		expected_target_id=headless-netroot-early-diag-v2
		expected_bundle=headless-netroot-early-diag-v2
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=2f7ab8b62e5303d17ded1445c1dc81cb32f7c5fea9fa20f3d356afd712e75a48
		expected_avb_salt=f1ca79c2e3175d6a85eab07bc3b9b2c28287a416fd9f678c429e7b8d01a99d9a
		expected_avb_digest=fc24d389b1224014fad131aebf484fe23eb98a2e03ec175a8262fff2f3dd0437
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc ]] ||
			fail 'Haven-boundary successor runtime manifest is not pinned'
		[[ $expected_image == \
			faf7ebd1f2638646bc169e3af79b406f11e792686949b58d43783ce08bbf034f ]] ||
			fail 'Haven-boundary successor recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'Haven-boundary successor trust key is not pinned'
		[[ $expected_host_verifier == \
			03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0 ]] ||
			fail 'Haven-boundary successor host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-host-rendezvous-v3-live-v9)
		expected_boot_image=build/host-rendezvous-v9-kmsg-device-production-20260810-r1/wrapper/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact recovery-kmsg-device diagnostic execution recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted exact recovery-kmsg-device diagnostic execution recovery; clean-twin ASUS wrapper materializes and validates the exact root-owned mode-0600 /dev/kmsg character device 1:11 before controller start; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=2e5d6e1766aab790dd1d1718125244886d376ffb73aa6b761571b12820b3061c
		expected_raw=067329920cc479714cac10ce001112c9029a3b986ac44269b8e7185a396c4aff
		expected_initramfs=d9a3fba43abf0c3e456feb2e7f9da5e043df1e7cdef2e33112e0313358ae98d8
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef
		expected_target_id=headless-netroot-early-diag-v2
		expected_bundle=headless-netroot-early-diag-v2
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=4d58546e838c151a4cfcc33ee983e0cbbbedd04081052508ec922d7daeec8c59
		expected_avb_salt=500d8c1659c467b43b3a7930924334e6ede2fac3353d6b4a92cc94929fd6432d
		expected_avb_digest=6236f10b21765a72805ccf39568b677774f92768ea6189293f4572d2b5587a09
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc ]] ||
			fail 'recovery-kmsg-device successor runtime manifest is not pinned'
		[[ $expected_image == \
			4f3bb23cb5a95873053c8d58c512cbbe749ea7f43c654f36b55ac4988d268133 ]] ||
			fail 'recovery-kmsg-device successor recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'recovery-kmsg-device successor trust key is not pinned'
		[[ $expected_host_verifier == \
			03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0 ]] ||
			fail 'recovery-kmsg-device successor host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-host-rendezvous-v3-live-v10)
		expected_boot_image=build/host-rendezvous-v10-observer-production-20260811-r1/wrapper/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact retention-observed diagnostic execution recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted retention-observed diagnostic execution successor; unchanged recovery-kmsg-device raw wrapper with a fresh deterministic AVB generation; corrected observation recovery is separately admitted; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=2e5d6e1766aab790dd1d1718125244886d376ffb73aa6b761571b12820b3061c
		expected_raw=067329920cc479714cac10ce001112c9029a3b986ac44269b8e7185a396c4aff
		expected_initramfs=d9a3fba43abf0c3e456feb2e7f9da5e043df1e7cdef2e33112e0313358ae98d8
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef
		expected_target_id=headless-netroot-early-diag-v2
		expected_bundle=headless-netroot-early-diag-v2
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=13821062e2d3d83100b125d853197e56cbe2240d34881917c234f151524038ed
		expected_avb_salt=983545d63d606b6cf2965127139a4f43944fd8161f3667895d0544d49ee96af3
		expected_avb_digest=da72637ff12a53fcd6bc2db9963e94506cd1f68f002bd30e6e51afe97145ab97
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc ]] ||
			fail 'retention-observed successor runtime manifest is not pinned'
		[[ $expected_image == \
			fb5fce1a8cd7849b70ea52052caf8dc524708f94eb2d5756b29abb2074523452 ]] ||
			fail 'retention-observed successor recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'retention-observed successor trust key is not pinned'
		[[ $expected_host_verifier == \
			03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0 ]] ||
			fail 'retention-observed successor host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	retention-host-rendezvous-v11-mainline-udc-execution-v2)
		expected_boot_image=build/mainline-udc-v11-generation9-wrapper-20260811-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact mainline-UDC-corrected retention execution recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted mainline-UDC-corrected retention execution recovery successor; clean-twin ASUS wrapper with a fresh deterministic AVB generation; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=2e5d6e1766aab790dd1d1718125244886d376ffb73aa6b761571b12820b3061c
		expected_raw=067329920cc479714cac10ce001112c9029a3b986ac44269b8e7185a396c4aff
		expected_initramfs=d9a3fba43abf0c3e456feb2e7f9da5e043df1e7cdef2e33112e0313358ae98d8
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef
		expected_target_id=headless-netroot-early-diag-v2
		expected_bundle=headless-netroot-early-diag-v2
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=05363adb23eb0b542e6958d1743370bbbcf2fa3223b0d91e27dde4667de49548
		expected_avb_salt=b83baa48af9b34ef6c351b8f33ee87302e22ad1c3f4fec6f2ffea671199190dd
		expected_avb_digest=61a852924d7cdef76695e6ce90f6f00ed1cc0461c3e6bfa8d6d58893505fa7a3
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			ddccf8025190097219f5a7bd8ef32f2b8ad9feed024ae00ecd07e0f446520034 ]] ||
			fail 'mainline-UDC retention manifest is not pinned'
		[[ $expected_image == \
			2fa17df6ac83daa767bbe35220ff48062c43cdbc6f3945e7c2d0018608130ffb ]] ||
			fail 'mainline-UDC retention recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'mainline-UDC retention trust key is not pinned'
		[[ $expected_host_verifier == \
			03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0 ]] ||
			fail 'mainline-UDC retention host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	retention-host-rendezvous-v12-nfs-xattr-execution-v1)
		expected_boot_image=build/mainline-udc-nfs-xattr-generation10-wrapper-20260811-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact NFS-xattr-projected retention execution recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted NFS-xattr-projected retention execution recovery successor; clean-twin ASUS wrapper with fresh deterministic AVB generation and signed exact xattr projection; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=2e5d6e1766aab790dd1d1718125244886d376ffb73aa6b761571b12820b3061c
		expected_raw=067329920cc479714cac10ce001112c9029a3b986ac44269b8e7185a396c4aff
		expected_initramfs=d9a3fba43abf0c3e456feb2e7f9da5e043df1e7cdef2e33112e0313358ae98d8
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef
		expected_target_id=headless-netroot-early-diag-v2
		expected_bundle=headless-netroot-early-diag-v2
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_generation_record=4e3cb3c3998c4a6eeac3697231658a9970e4529a65a4ec7fcbde2c2ecaf386a8
		expected_avb_salt=14b23c4412e941ba46366491a43265cf8c11fb391f3c6c91e5e4da56c31cb2c5
		expected_avb_digest=c710bc66a9a0e426a65cf86ab7bc9705ae93233cc78ced70c3a00575805d825b
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			325aa8fb76444b5c01bc517a22ad2483c016837cc1fcb46c203ab5288b916854 ]] ||
			fail 'NFS-xattr retention manifest is not pinned'
		[[ $expected_image == \
			f53418cbca5c79c65f63ca24e838ec299eb47ee0d5593286bbbebdb98529bab2 ]] ||
			fail 'NFS-xattr retention recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'NFS-xattr retention trust key is not pinned'
		[[ $expected_host_verifier == \
			03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0 ]] ||
			fail 'NFS-xattr retention host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-ssh-network-ready-v15-live-v1)
		expected_boot_image=build/ssh-acceptance-v15-host-network-ready-fix-20260811-r1/wrapper/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact host-network-readiness-corrected SSH diagnostic recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted host-network-readiness-corrected SSH diagnostic recovery; byte-distinct AVB generation over the proven clean-twin raw wrapper and exact runtime manifest; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=2e5d6e1766aab790dd1d1718125244886d376ffb73aa6b761571b12820b3061c
		expected_raw=067329920cc479714cac10ce001112c9029a3b986ac44269b8e7185a396c4aff
		expected_initramfs=d9a3fba43abf0c3e456feb2e7f9da5e043df1e7cdef2e33112e0313358ae98d8
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef
		expected_target_id=headless-netroot-early-diag-v2
		expected_bundle=headless-netroot-early-diag-v2
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_avb_salt=2567ca66854065cdd9945d9f7f5d4285dc3b42ed9828ad99e40f9574bc852217
		expected_avb_digest=616213ada961c460802adda86fb5c68655852701f941247a1d765b9300f25910
		expected_generation_record=50011e507c1064dd95433a2a6b04f5b56d42e1a9f3132824e1194f8ed21aec42
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d ]] ||
			fail 'SSH-acceptance runtime manifest is not pinned'
		[[ $expected_image == \
			74cb0bcc3361b349f8af2a400f6cbdab05d98e64a02b7ea1e4ef6f656c29f9b1 ]] ||
			fail 'SSH-acceptance recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'SSH-acceptance trust key is not pinned'
		[[ $expected_host_verifier == \
			03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0 ]] ||
			fail 'SSH-acceptance host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	headless-diagnostic-ssh-inert-block-v16-live-v1)
		expected_boot_image=build/ssh-acceptance-v16-inert-block-fix-20260811-r1/wrapper/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact inert-virtual-block-aware SSH diagnostic recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted inert-virtual-block-aware SSH diagnostic recovery; byte-distinct AVB generation over the proven clean-twin raw wrapper and exact runtime manifest; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=2e5d6e1766aab790dd1d1718125244886d376ffb73aa6b761571b12820b3061c
		expected_raw=067329920cc479714cac10ce001112c9029a3b986ac44269b8e7185a396c4aff
		expected_initramfs=d9a3fba43abf0c3e456feb2e7f9da5e043df1e7cdef2e33112e0313358ae98d8
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef
		expected_target_id=headless-netroot-early-diag-v2
		expected_bundle=headless-netroot-early-diag-v2
		expected_bundle_profile=diagnostic-initramfs-v1
		expected_avb_salt=3451c8a37abc342fd1205f297fe8a479b02ee9b9fe3a7a64d7d10f69ed3ca359
		expected_avb_digest=3ab12489b339e3a305a0afb2c96cf895303eaa22e7f51d23264525088bd2dbe0
		expected_generation_record=8f1c7977c7ffa18a4fa130d08710a4e6e9744b9edbcc0071b02fb9d1f2dcf91b
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d ]] ||
			fail 'SSH-acceptance runtime manifest is not pinned'
		[[ $expected_image == \
			c12c1f2879b4a0c36b604fdaaf83b7216d66b664ef4c5f96f2dd18c1533952c8 ]] ||
			fail 'SSH-acceptance recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'SSH-acceptance trust key is not pinned'
		[[ $expected_host_verifier == \
			03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0 ]] ||
			fail 'SSH-acceptance host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	*) fail "unsupported stable-recovery live profile: $profile" ;;
esac

# Historical profiles retain their pinned embedded init. The current
# profile must instead prove the repository-owned init and exact UDC contract.
case $profile in
	historical-2026-07-29 | \
	corrected-headless-successor-2026-07-30 | \
	headless-ssh-deployment-v3 | \
	headless-diagnostic-deployment-v1 | \
	headless-diagnostic-generation[3-9]-offline-v1 | \
	headless-diagnostic-generation[3-9]-live-v1 | \
	headless-diagnostic-generation1[0-2]-offline-v1 | \
	headless-diagnostic-generation1[0-2]-live-v1 | \
	headless-diagnostic-stage75-v2-superseded-offline-v1)
		initramfs_contract=historical-pinned-v1
		initramfs_verifier_expected=$expected_initramfs
		;;
	headless-diagnostic-host-rendezvous-v3-haven-production-hold-v1 | \
	headless-diagnostic-host-rendezvous-v3-live-v2 | \
	headless-diagnostic-host-rendezvous-v3-live-v3 | \
	headless-diagnostic-host-rendezvous-v3-live-v4 | \
	headless-diagnostic-host-rendezvous-v3-live-v5 | \
	headless-diagnostic-host-rendezvous-v3-live-v6 | \
	headless-diagnostic-host-rendezvous-v3-live-v7 | \
	headless-diagnostic-host-rendezvous-v3-live-v8 | \
	headless-diagnostic-host-rendezvous-v3-live-v9 | \
	headless-diagnostic-host-rendezvous-v3-live-v10 | \
	headless-diagnostic-ssh-network-ready-v15-live-v1 | \
	headless-diagnostic-ssh-inert-block-v16-live-v1 | \
	retention-host-rendezvous-v3-execution-v1 | \
	retention-host-rendezvous-v11-mainline-udc-execution-v2 | \
	retention-host-rendezvous-v12-nfs-xattr-execution-v1)
		initramfs_contract=exact-a600000-v1
		initramfs_verifier_expected=-
		;;
	*) fail 'profile lacks an explicit stable-recovery init contract' ;;
esac
[[ -z $expected_bundle || $bundle == "$expected_bundle" ]] ||
	fail "profile requires bundle=$expected_bundle"
# expected_image is the caller-supplied RECOVERY_SHA256 and is never
# reassigned by profile selection.

if [[ -n $expected_boot_image &&
	( $action == preflight || $action == boot ) ]]; then
	[[ -n $expected_boot_basis ]] ||
		fail "profile lacks an exact temporary-boot basis for $expected_boot_image"
	early_boot_policy=$repo/manifests/temporary-boot-images.tsv
	early_artifact_manifest=$repo/manifests/artifacts.tsv
	[[ -f $early_boot_policy && ! -L $early_boot_policy &&
		-r $early_boot_policy ]] ||
		fail 'unsafe or missing early temporary-boot policy input'
	[[ -f $early_artifact_manifest && ! -L $early_artifact_manifest &&
		-r $early_artifact_manifest ]] ||
		fail 'unsafe or missing early artifact manifest input'
	for command in cp mktemp; do
		command -v "$command" >/dev/null ||
			fail "missing admission-snapshot command: $command"
	done
	admission_snapshot_dir=$(mktemp -d)
	trap 'rm -rf -- "$admission_snapshot_dir"' EXIT HUP INT TERM
	early_boot_policy_snapshot=$admission_snapshot_dir/temporary-boot-images.tsv
	early_artifact_manifest_snapshot=$admission_snapshot_dir/artifacts.tsv
	cp --reflink=never -- "$early_boot_policy" "$early_boot_policy_snapshot"
	cp --reflink=never -- "$early_artifact_manifest" \
		"$early_artifact_manifest_snapshot"
	validate_exact_boot_admission \
		"$early_boot_policy_snapshot" "$early_artifact_manifest_snapshot" \
		"$expected_boot_image" "$expected_boot_basis" "$expected_image" \
		"$expected_boot_role" "$expected_boot_tracked"
fi

if [[ $action == policy-preflight ]]; then
	printf '%s\n' \
		'format=rog5-stable-recovery-policy-v1' \
		"recovery_profile=$profile" \
		"bundle=$bundle" \
		"manifest_sha256=$expected_manifest" \
		"bundle_profile=$expected_bundle_profile" \
		"target_id=$expected_target_id" \
		"recovery_sha256=$expected_image" \
		"trust_key_sha256=$expected_trust" \
		"host_verifier_sha256=$expected_host_verifier" \
		'authority=none' \
		'result=PASS'
	exit 0
fi

for command in awk cmp cp cut find git grep mktemp python3 realpath sha256sum \
	stat tr; do
	command -v "$command" >/dev/null ||
		fail "missing live-gate command: $command"
done
[[ $(uname -s) == Linux ]] || fail 'the live gate requires Linux'
if [[ $action != artifact-preflight ]]; then
	for command in sed systemctl; do
		command -v "$command" >/dev/null ||
			fail "missing live-gate command: $command"
	done
	[[ -f $fastboot && ! -L $fastboot && -x $fastboot &&
		$(stat -Lc '%u:%g:%a:%F' "$fastboot") == \
		'0:0:755:regular file' ]] ||
		fail 'fixed root-owned fastboot executable is unavailable'
	systemctl is-active --quiet ModemManager.service &&
		fail 'stop ModemManager before the recovery ACM is exposed'
fi
if [[ $action == boot ]]; then
	for command in date sleep udevadm wc; do
		command -v "$command" >/dev/null ||
			fail "missing live-gate command: $command"
	done
fi

live_root=$(realpath -e "$live_root")
component_root=$(realpath -e "$component_root")
trust_key=$(realpath -e "$trust_key")
bundle_root=$(realpath -e "$bundle_root")
case $live_root in
	"$repo"/build/*) ;;
	*) fail 'live build root must be below the ignored build directory' ;;
esac
git -C "$repo" check-ignore -q "$live_root" ||
	fail 'live build root is not ignored by Git'
case $component_root in
	"$repo"/build/*) ;;
	*) fail 'recovery component root must be below the ignored build directory' ;;
esac
git -C "$repo" check-ignore -q "$component_root" ||
	fail 'recovery component root is not ignored by Git'
if [[ $action == artifact-preflight ]]; then
	case $bundle_root in
		"$repo"/build/*) ;;
		*) fail 'artifact-preflight bundle root must remain below build' ;;
	esac
	git -C "$repo" check-ignore -q "$bundle_root" ||
		fail 'artifact-preflight bundle root is not ignored by Git'
else
	[[ $bundle_root == /var/lib/rog5-recovery-bundles ]] ||
		fail 'unexpected recovery bundle root'
fi

image=$live_root/repack/stable-recovery-a.avb.img
twin_image=$live_root/repack/stable-recovery-b.avb.img
raw=$live_root/repack/stable-recovery-a.raw.img
twin_raw=$live_root/repack/stable-recovery-b.raw.img
kernel=$live_root/wrapper-a/asus-kexec-stage/arch/arm64/boot/Image
twin_kernel=$live_root/wrapper-b/asus-kexec-stage/arch/arm64/boot/Image
ramdisk=$live_root/wrapper-a/rog5-kexec-stage-initramfs.cpio.gz
twin_ramdisk=$live_root/wrapper-b/rog5-kexec-stage-initramfs.cpio.gz
config=$live_root/wrapper-a/asus-kexec-stage/.config
twin_config=$live_root/wrapper-b/asus-kexec-stage/.config
case $component_layout in
	flat)
		control=$component_root/rog5-recovery-control
		fetcher=$component_root/rog5-bundle-fetch
		verifier=$component_root/rog5-bundle-verify
		host_verifier=$component_root/rog5-bundle-verify-host-test
		source_initramfs=$component_root/stable-recovery-a.cpio.gz
		twin_source_initramfs=$component_root/stable-recovery-b.cpio.gz
		;;
	structured)
		control=$component_root/components/rog5-recovery-control
		fetcher=$component_root/components/rog5-bundle-fetch
		verifier=$component_root/components/rog5-bundle-verify
		host_verifier=$component_root/components/rog5-bundle-verify-host-test
		source_initramfs=$component_root/initramfs-a/rog5-stable-recovery.cpio.gz
		twin_source_initramfs=$component_root/initramfs-b/rog5-stable-recovery.cpio.gz
		;;
esac
manifest=$bundle_root/$bundle/manifest
generation_record=$live_root/avb-generation.txt

for input in "$image" "$twin_image" "$raw" "$twin_raw" "$kernel" \
	"$twin_kernel" "$ramdisk" "$twin_ramdisk" "$config" "$twin_config" \
	"$control" "$fetcher" "$verifier" "$host_verifier" \
	"$source_initramfs" "$twin_source_initramfs" "$trust_key" "$manifest" \
	"$avbtool" "$unpack"; do
	[[ -f $input && ! -L $input && -r $input ]] ||
		fail "unsafe or missing live input: $input"
done
if [[ -n $expected_generation_record ]]; then
	[[ -f $generation_record && ! -L $generation_record &&
		-r $generation_record ]] ||
		fail 'unsafe or missing AVB-generation record'
elif [[ -e $generation_record || -L $generation_record ]]; then
	fail 'profile does not permit an AVB-generation record'
fi
if [[ $action == preflight || $action == boot ]]; then
	boot_policy=$repo/manifests/temporary-boot-images.tsv
	artifact_manifest=$repo/manifests/artifacts.tsv
	for policy_input in "$boot_policy" "$artifact_manifest"; do
		[[ -f $policy_input && ! -L $policy_input && -r $policy_input ]] ||
			fail "unsafe or missing temporary-boot policy input: $policy_input"
	done
	image_name=${image#"$repo"/}
	[[ $image_name != "$image" ]] ||
		fail 'temporary boot image must remain below the repository'
	if [[ -n $expected_boot_image ]]; then
		[[ $image_name == "$expected_boot_image" ]] ||
			fail 'temporary boot image does not match the pinned profile path'
		[[ -n $early_boot_policy_snapshot &&
			-n $early_artifact_manifest_snapshot &&
			-f $early_boot_policy_snapshot &&
			-f $early_artifact_manifest_snapshot ]] ||
			fail 'early temporary-boot admission snapshot is absent'
		validate_exact_boot_admission \
			"$early_boot_policy_snapshot" \
			"$early_artifact_manifest_snapshot" "$image_name" \
			"$expected_boot_basis" "$expected_image" \
			"$expected_boot_role" "$expected_boot_tracked"
	else
		# Historical profiles without an exact path pin retain their legacy
		# non-empty-basis rule until they are retired.
		validate_temporary_boot_policy_header "$boot_policy"
		validate_artifact_manifest_header "$artifact_manifest"
		policy_matches=$(awk -F '\t' -v name="$image_name" \
			'$1 == name { count++ } END { print count + 0 }' "$boot_policy")
		[[ $policy_matches == 1 ]] ||
			fail "temporary boot policy does not uniquely list $image_name"
		policy_status=$(awk -F '\t' -v name="$image_name" \
			'$1 == name { print $2; exit }' "$boot_policy")
		policy_basis=$(awk -F '\t' -v name="$image_name" \
			'$1 == name { print $3; exit }' "$boot_policy")
		[[ $policy_status == allow && -n $policy_basis ]] ||
			fail "temporary boot policy does not allow $image_name"
		validate_exact_boot_admission \
			"$boot_policy" "$artifact_manifest" "$image_name" \
			"$policy_basis" "$expected_image"
	fi
fi
if [[ $requires_qualified_cpio == 1 ]]; then
	for input in "$qualified_cpio" "$qualified_cpio_shim"; do
		[[ -f $input && ! -L $input && -x $input ]] ||
			fail "unsafe or missing qualified cpio input: $input"
	done
	mapfile -d '' -t qualified_cpio_entries < <(
		find "$repo/scripts/host/qualified-cpio-path" \
			-mindepth 1 -maxdepth 1 -print0
	)
	[[ ${#qualified_cpio_entries[@]} -eq 1 &&
		${qualified_cpio_entries[0]} == "$qualified_cpio" ]] ||
		fail 'qualified cpio path must contain only the pinned cpio'
fi
[[ $(stat -c %s "$image") == 100663296 &&
	$(stat -c %s "$twin_image") == 100663296 ]] ||
	fail 'temporary AVB wrapper has the wrong partition size'
[[ $(stat -c %s "$trust_key") == 32 ]] ||
	fail 'recovery trust root is not a raw Ed25519 public key'
cmp "$image" "$twin_image"
cmp "$raw" "$twin_raw"
cmp "$kernel" "$twin_kernel"
cmp "$ramdisk" "$twin_ramdisk"
cmp "$config" "$twin_config"
cmp "$source_initramfs" "$twin_source_initramfs"
cmp "$ramdisk" "$source_initramfs"

check_hash() {
	local input=$1 expected=$2
	[[ $(sha256sum "$input" | cut -d ' ' -f 1) == "$expected" ]] ||
		fail "identity mismatch: $input"
}
check_hash "$image" "$expected_image"
check_hash "$trust_key" "$expected_trust"
check_hash "$manifest" "$expected_manifest"
check_hash "$host_verifier" "$expected_host_verifier"
check_hash "$kernel" "$expected_kernel"
check_hash "$raw" "$expected_raw"
check_hash "$source_initramfs" "$expected_initramfs"
check_hash "$control" "$expected_control"
check_hash "$fetcher" "$expected_fetcher"
check_hash "$verifier" "$expected_verifier"
check_hash "$config" "$expected_config"
if [[ -n $expected_generation_record ]]; then
	check_hash "$generation_record" "$expected_generation_record"
fi
if [[ $requires_qualified_cpio == 1 ]]; then
	check_hash "$qualified_cpio" \
		7520899a405e1fc698875e047d8671c9415116e944831135a8e8eb6a93a21580
	check_hash "$qualified_cpio_shim" \
		a0a0a1d5b134d18470cc2fc55b0220fa464057e95ba05145e3dde6338ed59b58
fi

env PATH="$initramfs_path" \
	"$repo/scripts/device/verify-stable-recovery-initramfs.sh" \
	"$source_initramfs" "$recovery_init" "$control" "$fetcher" "$verifier" \
	"$trust_key" "$initramfs_contract" "$initramfs_verifier_expected"

verified_plan=$(
	"$host_verifier" --bundle-root "$bundle_root" \
		--trust-key "$trust_key" "$bundle" "$expected_manifest"
)
grep -Fxq "bundle=$bundle" <<<"$verified_plan"
grep -Fxq "manifest_sha256=$expected_manifest" <<<"$verified_plan"
grep -Fxq "profile=$expected_bundle_profile" <<<"$verified_plan"
grep -Fxq "target_id=$expected_target_id" <<<"$verified_plan"
grep -Fxq 'target_release=7.1.4-g7a5cef0db479' <<<"$verified_plan"
grep -Fxq 'target_timeout=480' <<<"$verified_plan"

check_hash "$avbtool" \
	6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff
check_hash "$unpack" \
	7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef

inspection=$(mktemp -d)
trap 'rm -rf -- "$inspection" "$admission_snapshot_dir"' EXIT HUP INT TERM
# avbtool resolves a "boot" hash descriptor as boot.img beside the wrapper.
# Private copies prevent an unrelated sibling from satisfying that descriptor.
cp --reflink=never -- "$image" "$inspection/recovery.img"
cp --reflink=never -- "$raw" "$inspection/boot.img"
cmp "$inspection/recovery.img" "$image"
cmp "$inspection/boot.img" "$raw"
check_hash "$inspection/recovery.img" "$expected_image"
python3 "$avbtool" verify_image --image "$inspection/recovery.img"
avb_info=$(python3 "$avbtool" info_image --image "$inspection/recovery.img")
grep -q '^Algorithm:[[:space:]]*NONE$' <<<"$avb_info"
grep -q '^      Partition Name:[[:space:]]*boot$' <<<"$avb_info"
if [[ -n $expected_avb_salt ]]; then
	[[ $(grep -c '^    Hash descriptor:$' <<<"$avb_info") == 1 &&
		$(grep -c '^      Salt:' <<<"$avb_info") == 1 &&
		$(grep -c '^      Digest:' <<<"$avb_info") == 1 ]] ||
		fail 'AVB generation descriptor inventory changed'
	[[ $(awk '/^      Salt:/ { print $2; exit }' <<<"$avb_info") == \
		"$expected_avb_salt" ]] || fail 'AVB generation salt changed'
	[[ $(awk '/^      Digest:/ { print $2; exit }' <<<"$avb_info") == \
		"$expected_avb_digest" ]] || fail 'AVB generation digest changed'
fi
cmp "$inspection/recovery.img" "$image"
cmp "$inspection/boot.img" "$raw"

python3 "$unpack" --boot_img "$raw" --out "$inspection" \
	--format=mkbootimg --null >"$inspection/args.nul"
raw_size=$(stat -c %s "$raw")
[[ $raw_size -gt 0 && $raw_size -lt 100663296 ]] ||
	fail 'raw wrapper size is invalid'
cmp -n "$raw_size" "$raw" "$image" ||
	fail 'raw wrapper is not the exact AVB image prefix'
python3 "$unpack" --boot_img "$image" --out "$inspection/booted" \
	--format=mkbootimg --null >"$inspection/booted-args.nul"
tr '\000' '\n' <"$inspection/booted-args.nul" \
	>"$inspection/booted-args.lines"
cmp "$inspection/booted/kernel" "$kernel"
cmp "$inspection/booted/ramdisk" "$ramdisk"
cmp "$inspection/kernel" "$inspection/booted/kernel"
cmp "$inspection/ramdisk" "$inspection/booted/ramdisk"
cmp "$inspection/kernel" "$kernel"
cmp "$inspection/ramdisk" "$ramdisk"
tr '\000' '\n' <"$inspection/args.nul" >"$inspection/args.lines"
command_line=$(
	awk '$0 == "--cmdline" { getline; print; exit }' \
		"$inspection/booted-args.lines"
)
for token in init=/init selinux=0 rog5linux.test=1 rog5.recovery_timeout=180; do
	[[ $(tr ' ' '\n' <<<"$command_line" | grep -Fxc "$token" || true) == 1 ]] ||
		fail "missing or duplicate wrapper token: $token"
done
if tr ' ' '\n' <<<"$command_line" |
	grep -Eq '^(root=|resume=|rog5\.recovery_cidr=|rog5\.ufs_discovery=)'
then
	fail 'physical-storage or legacy network input reached the recovery wrapper'
fi

if [[ $action == artifact-preflight ]]; then
	echo "PASS stable-recovery artifact preflight profile=$profile image_sha256=$expected_image"
	exit 0
fi

devices=$("$fastboot" devices 2>/dev/null) ||
	fail 'fastboot devices failed'
if [[ -n $fastboot_serial ]]; then
	awk -v serial="$fastboot_serial" \
		'$1 == serial && $2 == "fastboot" { found=1 } END { exit !found }' \
		<<<"$devices" ||
		fail 'requested fastboot device is not present'
else
	count=$(awk '$2 == "fastboot" { count++ } END { print count + 0 }' \
		<<<"$devices")
	[[ $count == 1 ]] ||
		fail "expected exactly one fastboot device, found $count"
	fastboot_serial=$(awk '$2 == "fastboot" { print $1; exit }' <<<"$devices")
fi
product=$("$fastboot" -s "$fastboot_serial" getvar product 2>&1) ||
	fail 'unable to query fastboot product'
product=$(sed -n \
	's/^(bootloader)[[:space:]]*//; s/^product:[[:space:]]*//p' \
	<<<"$product" | sed -n '1p')
[[ $product == lahaina ]] ||
	fail "unexpected fastboot product: ${product:-missing}"

if [[ $action == preflight ]]; then
	echo "PASS exact boot-only live gate profile=$profile image_sha256=$expected_image"
	exit 0
fi

[[ $acm_timeout =~ ^[0-9]+$ && $acm_timeout -ge 15 &&
	$acm_timeout -le 180 ]] ||
	fail 'ACM_TIMEOUT must be between 15 and 180 seconds'

find_rog5_acm() {
	local expected=$1 device properties
	for device in /dev/ttyACM*; do
		[[ -e $device ]] || continue
		properties=$(udevadm info --query=property --name="$device" 2>/dev/null ||
			true)
		grep -qx 'ID_VENDOR_ID=1d6b' <<<"$properties" || continue
		grep -qx 'ID_MODEL_ID=0104' <<<"$properties" || continue
		grep -qx "ID_MODEL=$expected" <<<"$properties" || continue
		printf '%s\n' "$device"
	done
}

verify_retention_acm_location() {
	local acm=$1 expected=$2 sysfs_path expected_prefix suffix leaf
	[[ $expected =~ ^[A-Za-z0-9._:/-]{1,512}$ &&
		$expected != /* && $expected != *..* ]] ||
		fail 'retention USB location is not canonical'
	sysfs_path=$(udevadm info --query=path --name="$acm" 2>/dev/null) ||
		fail 'cannot resolve recovery ACM sysfs location'
	[[ $sysfs_path =~ ^/devices/[A-Za-z0-9._:/-]+$ ]] ||
		fail 'recovery ACM sysfs location is not canonical'
	expected_prefix=/devices/$expected/
	[[ $sysfs_path == "$expected_prefix"* ]] ||
		fail 'recovery ACM enumerated on a different physical USB port'
	suffix=${sysfs_path#"$expected_prefix"}
	leaf=${expected##*/}
	[[ $suffix == "$leaf:"*"/tty/${acm##*/}" ]] ||
		fail 'recovery ACM sysfs ancestry is not exact'
}

[[ $retention_boot_result == 0 || $retention_boot_result == 1 ]] ||
	fail 'ROG5_RETENTION_BOOT_RESULT must be exactly 0 or 1'
if [[ $retention_boot_result == 1 ]]; then
	[[ $expected_usb_location =~ ^[A-Za-z0-9._:/-]{1,512}$ &&
		$expected_usb_location != /* && $expected_usb_location != *..* ]] ||
		fail 'retention USB location is not canonical'
fi

[[ -z $(find_rog5_acm ROG5_recovery) ]] ||
	fail 'recovery ACM already exists before temporary boot'
python3 "$repo/scripts/host/verified-fastboot-boot.py" \
	"$image" "$expected_image" "$fastboot_serial"

deadline=$(( $(date +%s) + acm_timeout ))
acm=
while (( $(date +%s) < deadline )); do
	acm=$(find_rog5_acm ROG5_recovery)
	[[ -z $acm ]] || break
	sleep 1
done
[[ $(wc -w <<<"$acm") == 1 && -r $acm && -w $acm ]] ||
	fail 'exact recovery ACM did not enumerate uniquely'
echo "PASS temporary stable recovery ready at $acm"
echo "INFO profile=$profile; no payload has been committed; rollback remains armed"
if [[ $retention_boot_result == 1 ]]; then
	verify_retention_acm_location "$acm" "$expected_usb_location"
	printf 'ROG5_RETENTION_BOOT_RESULT_V1 action=execution-boot recovery_sha256=%s rollback_armed=1 usb_location=%s\n' \
		"$expected_image" "$expected_usb_location"
fi
