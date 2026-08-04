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
	local matches fields status found_basis identity role
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
		headless-diagnostic-generation11-live-v1) ;;
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
fastboot=/usr/bin/fastboot
fastboot_serial=${FASTBOOT_SERIAL:-}
acm_timeout=${ACM_TIMEOUT:-90}
component_layout=
expected_kernel=
expected_raw=
expected_initramfs=
expected_target_id=
expected_bundle=
expected_bundle_profile=network-root-v1
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
	*) fail "unsupported stable-recovery live profile: $profile" ;;
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
	validate_exact_boot_admission \
		"$early_boot_policy" "$early_artifact_manifest" \
		"$expected_boot_image" "$expected_boot_basis" "$expected_image"
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
if [[ $profile == headless-diagnostic-generation11-live-v1 &&
	$action == boot ]]; then
	claim_consumer=$repo/scripts/host/consume-generation11-boot-claim.py
	[[ -f $claim_consumer && ! -L $claim_consumer && -x $claim_consumer ]] ||
		fail 'generation-11 claim consumer is unsafe or absent'
	"$claim_consumer" ||
		fail 'generation-11 durable BOOT_CLAIMED record was not entered'
fi
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
		validate_exact_boot_admission \
			"$boot_policy" "$artifact_manifest" "$image_name" \
			"$expected_boot_basis" "$expected_image"
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
	"$source_initramfs" "$repo/initramfs/recovery-init" \
	"$control" "$fetcher" "$verifier" "$trust_key"

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
trap 'rm -rf -- "$inspection"' EXIT HUP INT TERM
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
