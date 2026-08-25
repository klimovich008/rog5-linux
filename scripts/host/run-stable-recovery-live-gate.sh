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
source "$repo/scripts/host/generated-power-usb-active.sh"
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
		headless-diagnostic-ssh-gadget-contract-v17-live-v1 | \
		headless-diagnostic-ssh-configfs-link-v18-live-v1 | \
		headless-diagnostic-ssh-iproute-whitespace-v19-live-v1 | \
		headless-diagnostic-ssh-fatal-token-boundary-v20-live-v1 | \
		headless-core-deployment-v1-live-v1 | \
		$POWER_USB_RECOVERY_PROFILE | \
		local-image-stage-v1-live-v1 | \
		persistent-root-power-usb-v9-generation102-live-v1 | \
		persistent-root-power-usb-v10-generation103-live-v1 | \
		persistent-root-local-image-probe-writer-v11-generation104-live-v1 | \
		persistent-root-local-image-any-prior-v12-generation105-live-v1 | \
		persistent-root-local-image-any-prior-v13-generation106-live-v1 | \
		persistent-root-local-image-any-prior-v14-generation107-live-v1 | \
		persistent-root-local-image-restart2-v15-generation108-live-v1 | \
		persistent-root-local-image-reboot-mode-v16-generation109-live-v1 | \
		persistent-root-sparse-diagnostic-v17-generation110-live-v1 | \
		local-image-stage-writer-v2-generation111-live-v1 | \
		local-image-stage-hotplug-v3-generation112-live-v1 | \
		local-image-stage-preusb-v4-generation113-live-v1 | \
		local-image-stage-usbmode-v5-generation114-live-v1 | \
		local-image-stage-configfs-v6-generation115-live-v1 | \
		local-image-stage-udc-v7-generation116-live-v1 | \
		local-image-stage-udc-stable-v8-generation117-live-v1 | \
		local-image-stage-ncm-v9-generation118-live-v1 | \
		local-image-stage-timing-v10-generation119-live-v1 | \
		local-image-stage-address-v11-generation120-live-v1 | \
		local-image-stage-prebind-v12-generation121-live-v1 | \
		local-image-stage-explicit-v13-generation122-live-v1 | \
		local-image-stage-configfs-udc-v14-generation123-live-v1 | \
		local-image-stage-two-sample-v15-generation124-live-v1 | \
		local-image-stage-bind-v16-generation125-live-v1 | \
		local-image-stage-direct-v17-generation126-live-v1 | \
		local-image-stage-bind-error-v18-generation127-live-v1 | \
		local-image-stage-hostfix-v19-generation128-live-v1 | \
		local-image-stage-postbind-v20-generation129-live-v1 | \
		local-image-stage-power-report-v21-generation130-live-v1 | \
		local-image-stage-listener-v22-generation131-live-v1 | \
		local-image-stage-abi-v23-generation132-live-v1 | \
		local-image-stage-ufs-count-v24-generation133-live-v1 | \
		local-image-stage-ufs-bind-v25-generation134-live-v1 | \
		local-image-stage-runtime-dt-v26-generation135-live-v1 | \
		local-image-stage-of-node-v27-generation136-live-v1 | \
		ufs-baseline-proven-v28-generation137-live-v1 | \
		ufs-reboot-baseline-v29-generation138-live-v1 | \
		ufs-power-reboot-baseline-v30-generation139-live-v1 | \
		ufs-glob-reboot-baseline-v31-generation140-live-v1 | \
		local-image-stage-glob-v32-generation141-live-v1 | \
		local-image-stage-ssh-v33-generation142-live-v1 | \
		local-image-stage-nm-v34-generation143-live-v1 | \
		local-image-stage-fast-v35-generation144-live-v1 | \
		local-image-stage-stages-v36-generation145-live-v1 | \
		local-image-stage-auth-v37-generation146-live-v1 | \
		local-image-stage-globfix-v38-generation147-live-v1 | \
		local-image-stage-rworder-v39-generation148-live-v1 | \
		local-image-stage-writekernel-v40-generation149-live-v1 | \
		local-image-write-benchmark-v41-generation150-live-v1 | \
		local-image-write-benchmark-v42-generation151-live-v1 | \
		local-image-write-benchmark-v43-generation152-live-v1 | \
		local-image-partial-inspect-v44-generation153-live-v1 | \
		local-image-write-benchmark-v45-generation154-live-v1 | \
		persistent-root-qmp-ufs-phy-control-v12-live-v1 | \
		persistent-root-qmp-module-load-control-v13-live-v1 | \
		persistent-root-qmp-regulator-stage-v14-live-v1 | \
		persistent-root-qmp-mmio-stage-v15-live-v1 | \
		persistent-root-qmp-clock-provider-stage-v16-live-v1 | \
		persistent-root-qmp-fixed-clocks-stage-v17-live-v1 | \
		persistent-root-qmp-first-fixed-clock-stage-v18-live-v1 | \
		persistent-root-qmp-allocation-stage-v19-live-v1 | \
		persistent-root-qmp-first-clock-name-stage-v20-live-v1 | \
		persistent-root-qmp-first-clock-runtime-pm-stage-v21-live-v1 | \
		persistent-root-qmp-second-clock-runtime-pm-stage-v22-live-v1 | \
		persistent-root-qmp-third-clock-runtime-pm-stage-v23-live-v1 | \
		persistent-root-qmp-clock-provider-cleanup-stage-v24-live-v1 | \
		persistent-root-qmp-clock-provider-cleanup-stage-v25-live-v1 | \
		persistent-root-qmp-ufs-phy-creation-stage-v26-live-v1 | \
		persistent-root-qmp-ufs-phy-provider-stage-v27-live-v1 | \
		persistent-root-ufs-readonly-enumeration-v28-live-v1 | \
		persistent-root-power-usb-v8-generation84-live-v1 | \
		persistent-root-local-image-early-ssh-v45-generation70-live-v1 | \
		persistent-root-local-image-early-ssh-v45-live-v1 | \
		persistent-root-local-image-ufs-detail-v44-live-v1 | \
		persistent-root-local-image-post-write-v43-live-v1 | \
		persistent-root-local-image-write-mountpoint-v42-live-v1 | \
		persistent-root-local-image-write-contained-v41-live-v1 | \
		persistent-root-local-image-write-roclass-v40-live-v1 | \
		persistent-root-local-image-write-window-v39-live-v1 | \
		persistent-root-local-image-write-diag-v38-live-v1 | \
		persistent-root-local-image-write-v37-live-v1 | \
		persistent-root-local-image-ed25519-v36-live-v1 | \
		persistent-root-local-image-volatile-v35-live-v1 | \
		persistent-root-local-image-loader-v34-repeat-live-v1 | \
		persistent-root-local-image-loader-v34-live-v1 | \
		persistent-root-local-image-fast-attest-v33-live-v1 | \
		persistent-root-local-image-v32-live-v1 | \
		persistent-root-ufs-fast-admission-v31-live-v1 | \
		persistent-root-ufs-local-root-stage-v30-live-v1 | \
		persistent-root-ufs-local-root-v29-live-v1 | \
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
expected_target_release=7.1.4-g7a5cef0db479
expected_target_timeout=480
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
	headless-diagnostic-ssh-gadget-contract-v17-live-v1)
		expected_boot_image=build/ssh-acceptance-v17-gadget-contract-fix-20260811-r1/wrapper/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact diagnostic-gadget-contract-aware SSH recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted diagnostic-gadget-contract-aware SSH recovery; byte-distinct AVB generation over the proven clean-twin raw wrapper and exact runtime manifest; one RAM-only use only; never flash'
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
		expected_avb_salt=8c7dd6b5f7838120a14ab2450e1d7677ca3bf1febbe98fb6f83323a7a3ea38d4
		expected_avb_digest=3240d1339f8d2f81aa64ec6cf6bfafed235efa1b76e4b1f91dce0a086566806e
		expected_generation_record=eb2a2e942cf1c27e42424c060c30bd7d1173bb1e614252db06684758e9f0d822
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d ]] ||
			fail 'SSH-acceptance runtime manifest is not pinned'
		[[ $expected_image == \
			7bd54a15a05c28bc9a5349c91ad9b6730bd1700871e311152c7c929792e1f20c ]] ||
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
	headless-diagnostic-ssh-configfs-link-v18-live-v1)
		expected_boot_image=build/ssh-acceptance-v18-configfs-link-fix-20260811-r1/wrapper/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact configfs-link-aware SSH recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted configfs-link-aware SSH recovery; byte-distinct AVB generation over the proven clean-twin raw wrapper and exact runtime manifest; one RAM-only use only; never flash'
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
		expected_avb_salt=a1b2b3375a32bcd1f9fa4b7c6abc04ec203f08b2efcf32d4a0ddb1fd2dfbce0a
		expected_avb_digest=4755baccb821b09283d9f871ce73f0fecfede58663f4f933a97d4f026c0004ea
		expected_generation_record=4ea38a9d5b1c319ac33140c37880f66b505a36ad5937e017fc05c383788a988b
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d ]] ||
			fail 'SSH-acceptance runtime manifest is not pinned'
		[[ $expected_image == \
			27eec19b7148ed0388a916bbe5c6b629edabf5874018aa88cd078930529a6232 ]] ||
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
	headless-diagnostic-ssh-iproute-whitespace-v19-live-v1)
		expected_boot_image=build/ssh-acceptance-v19-iproute-trailing-space-fix-20260812-r1/wrapper/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact iproute-whitespace-aware SSH recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted iproute-whitespace-aware SSH recovery; byte-distinct AVB generation over the proven clean-twin raw wrapper and exact runtime manifest; one RAM-only use only; never flash'
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
		expected_avb_salt=e4d2f04345b6437640ea796f4789d35efd18a024c6f54b74b3e46e96dc076e85
		expected_avb_digest=6c20b8ad64c713ad7fbde16cbfc866d3b39e97e998497fddce889ec36a716286
		expected_generation_record=e9b3fc6fd473266e667c45eaff43cb057ef0c0cee0eac63a5bbe4e4beb420b1b
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d ]] ||
			fail 'SSH-acceptance runtime manifest is not pinned'
		[[ $expected_image == \
			5f769fcf3355b7a03a894daa61da3adca7b01a97b2a2c0362a9c59108a5a83fb ]] ||
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
	headless-diagnostic-ssh-fatal-token-boundary-v20-live-v1)
		expected_boot_image=build/ssh-acceptance-v20-fatal-token-boundary-fix-20260812-r1/wrapper/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact token-delimited-fatal-filter SSH recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted token-delimited-fatal-filter SSH recovery; byte-distinct AVB generation over the proven clean-twin raw wrapper and exact runtime manifest; one RAM-only use only; never flash'
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
		expected_avb_salt=c217cfc83602e447e40009ee0f557b341ffef08a2101fe6548f3fde913fc0356
		expected_avb_digest=e2052a33ce42c179d4ef255d766dd66a466d0de62a76e82b617571afa2195bf0
		expected_generation_record=8bbc5ba59c550c58f1fd6fc1143adae6fed9552b31031bd8290562877e10b808
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			98a4c4381c90c5d8edd7252309fe438d18f66af0a5ccd47f2cec7ec39e8f971d ]] ||
			fail 'SSH-acceptance runtime manifest is not pinned'
		[[ $expected_image == \
			cacd0164d7d1d581f6fa4cb8926d7fea655be92e333c84635de953dd7d816b39 ]] ||
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
	headless-core-deployment-v1-live-v1)
		expected_boot_image=build/headless-core-v21-generation21-20260812-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact headless-core Arch SSH recovery with power-key indicator; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted headless-core Arch SSH recovery with power-key indicator; clean-twin signed bundle and byte-distinct AVB generation over proven raw wrapper; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=2e5d6e1766aab790dd1d1718125244886d376ffb73aa6b761571b12820b3061c
		expected_raw=067329920cc479714cac10ce001112c9029a3b986ac44269b8e7185a396c4aff
		expected_initramfs=d9a3fba43abf0c3e456feb2e7f9da5e043df1e7cdef2e33112e0313358ae98d8
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef
		expected_target_id=headless-core-network-root
		expected_bundle=headless-core-network-root-v2-live-v1
		expected_bundle_profile=network-root-v1
		expected_avb_salt=e94d6e0017d44437f4c0951afc06b7dd707e44f14fde01fbbe773bae3521e962
		expected_avb_digest=24b325a1f60e67f36eec6977f7a84c7419187b2c1a5707144dc382d16f522489
		expected_generation_record=9726f2dfe6d3dac222d146147f2366931daeabe0181ceaeb4a62e4b84fa50bf0
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			f3884e6554f3d2c1bb437c45484f658817c006185d6c84a5ac4ef452b01bc02f ]] ||
			fail 'headless-core runtime manifest is not pinned'
		[[ $expected_image == \
			40418c0fef418263d3bf8f7c2fc1d7bed4745af79cc6b45bc78b2e8d1e0a56ee ]] ||
			fail 'headless-core recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'headless-core trust key is not pinned'
		[[ $expected_host_verifier == \
			03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0 ]] ||
			fail 'headless-core host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	$POWER_USB_RECOVERY_PROFILE)
		expected_boot_image=$POWER_USB_OUTPUT_ROOT/wrapper/repack/stable-recovery-a.avb.img
		expected_boot_basis=$POWER_USB_BOOT_POLICY_BASIS
		expected_boot_role=$POWER_USB_ARTIFACT_ROLE
		expected_boot_tracked=no
		component_layout=structured
		expected_target_id=$POWER_USB_TARGET_ID
		expected_bundle=$POWER_USB_BUNDLE
		expected_bundle_profile=$POWER_USB_BUNDLE_PROFILE
		expected_target_release=$POWER_USB_TARGET_RELEASE
		expected_target_timeout=$POWER_USB_TARGET_TIMEOUT
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == "$POWER_USB_EXPECTED_MANIFEST_SHA256" ]] ||
			fail 'power USB observer runtime manifest is not pinned'
		if [[ $action != policy-preflight ]]; then
			receipt=${ROG5_POWER_USB_DEPLOYMENT_RECEIPT:-}
			[[ -n $receipt ]] || fail 'set the exact power USB deployment receipt'
			"$repo/scripts/host/power-usb-deployment-receipt.py" verify \
				"$receipt" --build-root "$repo/$POWER_USB_OUTPUT_ROOT"
			expected_kernel=$(sha256sum "$live_root/wrapper-a/asus-kexec-stage/arch/arm64/boot/Image" | cut -d ' ' -f 1)
			expected_raw=$(sha256sum "$live_root/repack/stable-recovery-a.raw.img" | cut -d ' ' -f 1)
			expected_initramfs=$(sha256sum "$component_root/initramfs-a/rog5-stable-recovery.cpio.gz" | cut -d ' ' -f 1)
			expected_control=$(sha256sum "$component_root/components/rog5-recovery-control" | cut -d ' ' -f 1)
			expected_fetcher=$(sha256sum "$component_root/components/rog5-bundle-fetch" | cut -d ' ' -f 1)
			expected_verifier=$(sha256sum "$component_root/components/rog5-bundle-verify" | cut -d ' ' -f 1)
			expected_config=$(sha256sum "$live_root/wrapper-a/asus-kexec-stage/.config" | cut -d ' ' -f 1)
			expected_generation_record=$(sha256sum "$live_root/avb-generation.txt" | cut -d ' ' -f 1)
		fi
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-v1-live-v1)
		expected_boot_image=build/local-image-stage-v1-generation101-20260823-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact UFS-capable local-image staging cycle; RAM-only kernel and recovery; only userdata image path writable after explicit SSH command; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted local-image staging recovery generation 101; unchanged cached recovery raw bytes, signed UFS-capable target bundle, key-only SSH, exact compressed image, relock, and bootloader return; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-v1
		expected_bundle=local-image-stage-v1
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=da54f01aad51c40f43942e9675ce63f9169d36150061d2fdc50857ee88c469df
		expected_avb_digest=61e678fbff8f316f34436aa260e7f85c8483a7365e5feb06da728a7cbf3cdcbb
		expected_generation_record=8ef17e2f5bf56eaf2f7d7352de157e8c50656a0dcef2c01ff3ae08e764de6f22
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == cef076e59fd114ad2559178f115d2873c3a62912a1a00f5028f6a02e392d7271 ]] ||
			fail 'local-image staging manifest is not pinned'
		[[ $expected_image == e4451a7bd042ff4de9593f0649c405d712f7ce2a75ac598d36cd0a5f60a8b267 ]] ||
			fail 'local-image staging recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'local-image staging trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'local-image staging host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-power-usb-v9-generation102-live-v1)
		expected_boot_image=build/persistent-root-power-usb-v9-generation102-20260823-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact first read-only local-image Arch boot after verified userdata-only sparse staging; unchanged live-proven V8 charging/UFS/local-root target under fresh signed bundle; RAM-only kernel/recovery; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 102 local-root successor; unchanged cached recovery raw bytes and live-proven V8 charging, NCM, UFS, storage lock, local-image mount, systemd, key-only SSH, and rollback target under a fresh signed identity; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=persistent-root-power-usb-v9
		expected_bundle=persistent-root-power-usb-v9
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=4be186b038b27843aad0c91ca593d78eb9cefcf75dafb760b6809179daaf60f3
		expected_avb_digest=7e279c1d20115ef8cec45ff735496e6b52670fb68e65d768f76119d20e652db8
		expected_generation_record=bcc02964b40f25cbc7478e337dae9c2b796051d3b420ce11316e58346a531e5d
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == bc44d8b4275192617730e3a5b39e76acdd3a6fe61d032903e3bc34f19f2ef363 ]] ||
			fail 'persistent-root V9 manifest is not pinned'
		[[ $expected_image == c64958f92cdac1cbf2979c8808f87df67d545ff7876b4e1c3bec3112b59451c4 ]] ||
			fail 'persistent-root V9 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'persistent-root V9 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'persistent-root V9 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-power-usb-v10-generation103-live-v1)
		expected_boot_image=build/persistent-root-power-usb-v10-generation103-20260823-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact bounded local-image probe creation and first Arch boot after verified userdata sparse staging; unchanged live-proven charging/UFS/local-root target with local-write/current probe mode only; RAM-only kernel/recovery; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 103 bounded-probe local-root successor; unchanged recovery, Image, DTB, charging, NCM, UFS and Arch root, with target-only local-write/current mode creating one exact probe before relock and read-only runtime; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=persistent-root-power-usb-v10
		expected_bundle=persistent-root-power-usb-v10
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=b5449e2f828d29d666ab7830c9545eb0cfffec6fd6dd2ef0afdb6bfe6600c4dc
		expected_avb_digest=557570d2fcca5426b3c7d587c03e52bc06dcdba954cebb0e513d652e7bf38284
		expected_generation_record=f58d2a0c89df07541b52c668c08bd833a9760ee89f7dc63b70d8ea10a606258d
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 8a143df66f5f4c12321eb717b2f01dc5ce63f9a6078fbeeff8894fb216122b97 ]] ||
			fail 'persistent-root V10 manifest is not pinned'
		[[ $expected_image == c634ebfcf23c7bcab381d02b87a0c17a9ac9e72e4654ea08c340e3a767da1c05 ]] ||
			fail 'persistent-root V10 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'persistent-root V10 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'persistent-root V10 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-probe-writer-v11-generation104-live-v1)
		expected_boot_image=build/persistent-root-local-image-probe-writer-v11-generation104-20260823-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact local-image probe write using the live-proven Generation-64 bounded-write kernel, DTB, UFS modules, and relock path; no charging or unrelated subsystem change; RAM-only kernel/recovery; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 104 probe-writer successor; exact live-proven Generation-64 bounded-write Image/DTB/UFS lineage with current fixed-mountpoint local-write initramfs, one probe write, complete relock, and rollback; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=persistent-root-local-image-probe-writer-v11
		expected_bundle=persistent-root-local-image-probe-writer-v11
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=78104b3659bff01db6bc18f545e48894253035a754e9f13e7954d5bd10db2769
		expected_avb_digest=049117e38951f597a250a7e325f7ba2374fbb95c4b468050e076a12841c995e8
		expected_generation_record=a5a48f1cd78c705fec7f93aedb34778f295a0d395cfc16b0644949f5bb2d6dc3
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 4046c67d1d4626d3b54e2d3e3c1c77d7c1190f5ccf8d14e65d03ca07d8a4ac9a ]] ||
			fail 'probe-writer V11 manifest is not pinned'
		[[ $expected_image == 1f6adb3c9c393777af66df01f918c87aecfcb57825b3e6909c46f873b19e88e4 ]] ||
			fail 'probe-writer V11 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'probe-writer V11 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'probe-writer V11 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-any-prior-v12-generation105-live-v1)
		expected_boot_image=build/persistent-root-local-image-any-prior-v12-generation105-20260823-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact read-only local-image Arch boot accepting only a canonical non-current probe UUID after the freshly staged image was proven marker-free and one writer was consumed; current charging/UFS/NCM baseline; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 105 read-only Arch successor; current charging/UFS/NCM Image and DTB, exact probe metadata plus one canonical non-current producer UUID, full storage relock, systemd, key-only SSH, and rollback; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=persistent-root-local-image-any-prior-v12
		expected_bundle=persistent-root-local-image-any-prior-v12
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=fb7c02d3399afa996258b9a46e2de1c844a0725805011210c6897b2bef8e3513
		expected_avb_digest=b463f64d67246f5c67c9105928d6c6e3768b8444e9c26951ba2d11325c06137d
		expected_generation_record=7dacd8f0af5997cbc3b4127c73bc17e759ca188f2e2861a205d1ae5c91f66788
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 060cfe75b9b3ccd3e4a364257a841f19a406f18e9c1f20bcec562f4b58e8640e ]] ||
			fail 'any-prior V12 manifest is not pinned'
		[[ $expected_image == f10e3bd965baa52c66dad5d13f57d51df296f9d85d3d07d25a5955bf1e1a2731 ]] ||
			fail 'any-prior V12 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'any-prior V12 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'any-prior V12 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-any-prior-v13-generation106-live-v1)
		expected_boot_image=build/persistent-root-local-image-any-prior-v13-generation106-20260823-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact continuous-lifecycle read-only Arch boot using byte-identical V12 target bytes, pre-committed host choreography, canonical prior-writer probe validation, charging/UFS/NCM, pinned SSH, and stock slot-A fallback; never flash or retry after entry'
		expected_boot_role='unbooted Generation 106 continuous-lifecycle Arch successor; byte-identical V12 target under fresh signed identity, repository runner owns claim through fallback, canonical prior-writer probe, charging/UFS/NCM, stage capture, pinned SSH, and rollback; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=persistent-root-local-image-any-prior-v13
		expected_bundle=persistent-root-local-image-any-prior-v13
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=c71b9790b831d44fcea7b8406e883037666d6db4aa714bb4b44e28a47c54c946
		expected_avb_digest=b13d4ae1ea00fefaecefee85b82cd20e18bdb8af79063b51c0f9cbc845e99d2f
		expected_generation_record=52d7310dc3395e79181c78f2908c0edb525c85fc1df3a829925ce77869374012
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 0779827737aaea22f17e44419879d9cdd58e69f4842744edf883a6f40ab09156 ]] ||
			fail 'continuous V13 manifest is not pinned'
		[[ $expected_image == 2f26b608ec7970ddea96cc78da3bd147a8e47f0446cdb9a79fc0dd995cadad97 ]] ||
			fail 'continuous V13 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'continuous V13 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'continuous V13 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-any-prior-v14-generation107-live-v1)
		expected_boot_image=build/persistent-root-local-image-any-prior-v14-generation107-20260823-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact continuous-lifecycle read-only Arch boot with the missing early any-prior policy case fixed; current charging/UFS/NCM Image and DTB, canonical prior-writer probe, pinned SSH, stock slot-A fallback; never flash or retry after entry'
		expected_boot_role='unbooted Generation 107 continuous-lifecycle Arch successor; current charging/UFS/NCM stack and corrected early any-prior target, stage capture, canonical prior-writer probe, pinned SSH, and stock fallback; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=persistent-root-local-image-any-prior-v14
		expected_bundle=persistent-root-local-image-any-prior-v14
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=f95d8d30fd7ec5f2946610663261557804cfb85e9c0949863acf93ffb9b55c80
		expected_avb_digest=e81c8f4e78941ddbd815e2ab9da38ef4577d3203231914972158c3da1b50612b
		expected_generation_record=7c3d1f08c0975234f78fd9fe470fe881b3dc761ef780bce2481cfe0cdf54bdc4
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 3fad573f1a5f68e3650da06d57e8940b4e65de1bf9d81a4db833c407cc20605a ]] ||
			fail 'early-gate-fixed V14 manifest is not pinned'
		[[ $expected_image == 5ecea582c3c3a2d325ae0b118a84a687dee2bbeda887bae364241f9ee7ccec80 ]] ||
			fail 'early-gate-fixed V14 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'early-gate-fixed V14 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'early-gate-fixed V14 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-restart2-v15-generation108-live-v1)
		expected_boot_image=build/persistent-root-local-image-restart2-v15-generation108-20260823-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact continuous-lifecycle read-only Arch boot with restart2 bootloader rollback before emergency SysRq; current charging/UFS/NCM Image and DTB, canonical prior-writer probe, pinned SSH, stock slot-A fallback; never flash or retry after entry'
		expected_boot_role='consumed Generation 108 continuous-lifecycle Arch cycle; UFS and read-only userdata mount passed, deployed rog5/images was absent, and restart2 reached slot-A unauthorized recovery because target reboot-mode modules were unavailable; no target write; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=persistent-root-local-image-restart2-v15
		expected_bundle=persistent-root-local-image-restart2-v15
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=60b172f097614cfe0fdeb6feb802b7aab55fec2becfb80ccb1647b903315ee54
		expected_avb_digest=796900a3be365700d7ef354716de6200346ea0c221d38fc3a8e074a5c0046c26
		expected_generation_record=06fa4210ed6b5d0c49eda863952d9d526b2553e2cfaf5f886fe0ba85af5d87f6
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 7b8e11102e707d426f12be5956e9e166bad4b58f7ffe6185922200fdeef17643 ]] ||
			fail 'restart2 V15 manifest is not pinned'
		[[ $expected_image == 74008dcc4f5a06690ef95756d8bb07d2df09e11879d408a6d84f1445cea14145 ]] ||
			fail 'restart2 V15 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'restart2 V15 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'restart2 V15 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-reboot-mode-v16-generation109-live-v1)
		expected_boot_image=build/persistent-root-local-image-reboot-mode-v16-generation109-20260823-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 109 RAM-only cycle after exact userdata restaging; target again mounted ext4 read-only but lacked rog5/images, while the built-in PMK8350 reboot-mode path returned exact fastboot; no target storage write occurred; never retry or flash'
		expected_boot_role='consumed Generation 109 cycle; repeated userdata-rog5-directory after exact restage, proved built-in PMK8350 reboot-mode return to fastboot, no target write; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=persistent-root-local-image-reboot-mode-v16
		expected_bundle=persistent-root-local-image-reboot-mode-v16
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=9225a96c4a16e8ccc25f2b624f3ad7e95a96d9e3f637dd2b7071b93fdfbc2a4f
		expected_avb_digest=ceeba28b3fa035aec3bbb05c34bc56152799f6301673e89732f7058a4357f2e0
		expected_generation_record=e89a00a4c9d6a1e85b2ffdd69e7c522166af62656f56a23f2eeaf7c56fca4279
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 3c0e549c62f3c41c5385987ae6cef76d14e7b8c4d1475b367f85251409cfdadf ]] ||
			fail 'reboot-mode V16 manifest is not pinned'
		[[ $expected_image == 900449001d9e30358ac1bd934ea6fe8e83b2bbfa63cadd2176761f5107e14955 ]] ||
			fail 'reboot-mode V16 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'reboot-mode V16 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'reboot-mode V16 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-sparse-diagnostic-v17-generation110-live-v1)
		expected_boot_image=build/persistent-root-sparse-diagnostic-v17-generation110-20260823-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 110 read-only cycle; source metadata blocks differed, high inode and directory blocks were zero, and 4-GiB aliases remained unchanged, proving ASUS ABL sparse flash left userdata unchanged; exact fastboot fallback passed; no target write; never retry or flash'
		expected_boot_role='consumed Generation 110 discriminator; proved ABL sparse userdata flash is ineffective, exact fastboot fallback, no target write; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=persistent-root-sparse-diagnostic-v17
		expected_bundle=persistent-root-sparse-diagnostic-v17
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=8591143462aa5fde13fc3076bbee15617f4f3668005d4113a5f68b3599c91ff2
		expected_avb_digest=c55ed733edb037d0f8279df6b47ed5e7f5e10a03044c1618d1b8fed15dd00afd
		expected_generation_record=94aa28067d9b7770f6228da2bf4d6aed32aa9d329417d2ba768c5108a0017b24
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 99ff5e35bf5533df7e99b5bad65aa893f68c69ced22cedd37e74d879041d15cd ]] ||
			fail 'sparse diagnostic V17 manifest is not pinned'
		[[ $expected_image == ce3be4ff692428d56dd92d9daf763803a32e0d129f1b01173229c1ebbe6f3578 ]] ||
			fail 'sparse diagnostic V17 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'sparse diagnostic V17 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'sparse diagnostic V17 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-writer-v2-generation111-live-v1)
		expected_boot_image=build/local-image-stage-writer-v2-generation111-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 111 cycle; recovery departed after COMMIT, no target USB appeared, and exact slot-A unauthorized recovery returned 30.708 seconds later; no SSH transfer or storage write occurred; never retry or flash'
		expected_boot_role='consumed Generation 111 controlled staging cycle; target USB never appeared, slot-A unauthorized recovery returned after 30.708 seconds, and no SSH transfer or storage write occurred; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-writer-v2
		expected_bundle=local-image-stage-writer-v2
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=8d80339a84d0e02cd634a71d328b5b5fc234e4f672b7a5f124bbfa595befcc77
		expected_avb_digest=58ed01cbfa3b492b5305bf40b7c89f62e1c18c66235b180b7f572c70ac297c87
		expected_generation_record=063bff1d8bcc69ded5a0debfe5ba2b6e49c9bef97d170939d4703b71419d6f69
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == f296276d49af5db4b498d2f14afc935065adf1ec4ca4e043e2b14c7a3b707bda ]] ||
			fail 'local-image stage writer V2 manifest is not pinned'
		[[ $expected_image == f58153ef41186b5f2a5c8b2449d432dc02b6f92a9fb4c9397298d2d026d4e7cb ]] ||
			fail 'local-image stage writer V2 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'local-image stage writer V2 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'local-image stage writer V2 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-hotplug-v3-generation112-live-v1)
		expected_boot_image=build/local-image-stage-hotplug-v3-generation112-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 112 cycle; guarded hotplug advanced to an immediate controlled pre-gadget failure, exact fastboot returned 6.903 seconds after recovery USB departure, and no storage write occurred; never retry or flash'
		expected_boot_role='consumed Generation 112 hotplug-guard cycle; immediate controlled pre-gadget fastboot fallback in 6.903 seconds, no target USB, SSH, transfer, installer, or storage write; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-hotplug-v3
		expected_bundle=local-image-stage-hotplug-v3
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=13e4b67e9a27e49c94ace4170acdb9ca6bfd1de7f7c87b212ad9a2eec7684853
		expected_avb_digest=7522dd4cd41d9bbeb2ffa97c67ca19a1110439dc44335bcbffa41f14e4445032
		expected_generation_record=1f33c5ee6eb85ac0451372240165e05d2827561f1f3e7a32e206945023547f7c
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == d3e3dc8627c19356ca187aec1ca7abe23a635ed98ed9c10ed9fa82db9cda043a ]] ||
			fail 'local-image stage hotplug V3 manifest is not pinned'
		[[ $expected_image == dafa103015313aa0d879aaea1f24e5ead375b236abf3170b2e6ac61f3b96d8b8 ]] ||
			fail 'local-image stage hotplug V3 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'local-image stage hotplug V3 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'local-image stage hotplug V3 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-preusb-v4-generation113-live-v1)
		expected_boot_image=build/local-image-stage-preusb-v4-generation113-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 113 timing cycle; exact fastboot returned 31.910 seconds after recovery departure, proving the 25-second both-checks-pass path plus 6.9-second overhead; no USB or storage surface; never retry or flash'
		expected_boot_role='consumed Generation 113 timing discriminator; 31.910-second exact fastboot return proved both release and command-line checks pass; no gadget, UFS, storage, SSH, or payload surface; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-preusb-v4
		expected_bundle=local-image-stage-preusb-v4
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=c54d26e8af262c6f2c68ad3d6c769d64d3e33da3ab64de072095fa477461c8a5
		expected_avb_digest=a5a763173c2b2f2513f8a77f8fa9117e7a0cf9610e5ba506f2536ebe57224635
		expected_generation_record=ff284ad575e9cbe57e559c7d9ba6a2e2880803d5f639b13cbbe75d8ce135902a
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 0ab3364d5622c3b85456f54ccdbc8fa4a9341f471a196027950fa3d352f2ffe3 ]] ||
			fail 'pre-USB V4 manifest is not pinned'
		[[ $expected_image == 615ab41813ed4a3c5600d346fafa3e395155483dc383edd34edd071ec64465e0 ]] ||
			fail 'pre-USB V4 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'pre-USB V4 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'pre-USB V4 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-usbmode-v5-generation114-live-v1)
		expected_boot_image=build/local-image-stage-usbmode-v5-generation114-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 114 cycle; guarded mainline-absent mode path was a no-op, exact fastboot repeated after 6.903 seconds before target USB, and no storage write occurred; never retry or flash'
		expected_boot_role='consumed Generation 114 USB-mode parity cycle; absent guarded mode path changed no runtime behavior, immediate 6.903-second fastboot fallback, no USB or storage write; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-usbmode-v5
		expected_bundle=local-image-stage-usbmode-v5
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=ef83de8ffd4a465c7105ea832a888a05002790cd525180aeaf7a2a674aa1d83c
		expected_avb_digest=c9cc285db38c913e3424d77c2abbdc9fa6ffb28a74cd17a7babe95a0330cc9b3
		expected_generation_record=6b10685bde221de120f889be1f3a9b4e888470e73475598218d2834ef70e1f43
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 78091cdfd341367996b258ebdd12ac447dfe7ab2d2e38101580bf5fc98315fe7 ]] ||
			fail 'USB-mode V5 manifest is not pinned'
		[[ $expected_image == b4334d2729d876270ec86ecf955aee4f2c104dea2c9f650019dc64528d646c7e ]] ||
			fail 'USB-mode V5 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'USB-mode V5 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'USB-mode V5 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-configfs-v6-generation115-live-v1)
		expected_boot_image=build/local-image-stage-configfs-v6-generation115-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 115 beacon; exact fastboot returned 51.961 seconds after recovery departure, selecting the 45-second UDC-identity branch: expected UDC exists but additional candidate present; no storage; never retry or flash'
		expected_boot_role='consumed Generation 115 ConfigFS beacon; 51.961-second return selected UDC-identity branch, expected a600000.usb plus extra candidate, no gadget binding or storage; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-configfs-v6
		expected_bundle=local-image-stage-configfs-v6
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=aa3d80c62408aaefe48ba1a5f8d0da7543312b6d3cddf5a58df8cf2f4b9032c3
		expected_avb_digest=353848c3082fcb6344ff374acd092726d44390a8cd28a57bf9e58ec1a0136a97
		expected_generation_record=e7c2000a1240b7b5cbbb80c38967405edf297a4c71705b4ffbfb71c42c9aef76
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == e68acce824da7be10502fff08522857bfc59ad5c2e53defe5e50fac802d620f3 ]] ||
			fail 'ConfigFS V6 manifest is not pinned'
		[[ $expected_image == 6b376583a52eebec18ba8a20deb26c7c560cacb7784285173e6c4585713a818f ]] ||
			fail 'ConfigFS V6 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'ConfigFS V6 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'ConfigFS V6 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-udc-v7-generation116-live-v1)
		expected_boot_image=build/local-image-stage-udc-v7-generation116-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 116 early inventory; exact fastboot returned in 16.887 seconds, selecting no-extra-yet and proving the additional UDC appears asynchronously after expected registration; no binding/storage; never retry or flash'
		expected_boot_role='consumed Generation 116 early UDC inventory; no-extra-yet at early sample proves late candidate race when combined with Generation 115; no binding, gadget, or storage; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-udc-v7
		expected_bundle=local-image-stage-udc-v7
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=07b6e90ff791f97c92ff5c2fac3932005d2e4ba4d1a9883d0d9cdbe3d684870d
		expected_avb_digest=7ca98319888c3b659727d569c5bdc5c832526579da9ddacd070e1af7eee7ac1f
		expected_generation_record=301cf924912958bccae7548fa1d2166f91ab8e86c14c7e57131dedeeb987da3e
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 16e4bdecca72d584c2cb00e263d9d3756778edcba7ab670ea2e95e2b601cebf9 ]] || fail 'UDC V7 manifest is not pinned'
		[[ $expected_image == 4c0ac09693ed1db066f78c64bf7024da6302b4aa193ffac13435320e512c0f83 ]] || fail 'UDC V7 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'UDC V7 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'UDC V7 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-udc-stable-v8-generation117-live-v1)
		expected_boot_image=build/local-image-stage-udc-stable-v8-generation117-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 117 stabilized inventory; exact fastboot returned in 21.750 seconds, again selecting no-extra after five seconds and proving the transient appears during ConfigFS NCM+ACM setup; no binding/storage; never retry or flash'
		expected_boot_role='consumed Generation 117 stabilized UDC inventory; no extra after five seconds proves ConfigFS-window transient with Generation 115; no binding, gadget, or storage; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-udc-stable-v8
		expected_bundle=local-image-stage-udc-stable-v8
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=70c5ee00a7e4f1848b71c637792fab153faacc46cff4b611739baf02e6f3a966
		expected_avb_digest=cc87d4a338e08ab5cce82a7d9772315f398df5d088cda2dd58b9873d3a2a85d5
		expected_generation_record=8aaf1409e0e68f8d15e7216a24372789be15367a1e4cff57db5e5e83c424ece5
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == f26c2a4c90d19250f9c3475ac5d0008e9d5024cde66a123befc9f545b50a9e09 ]] || fail 'stable UDC V8 manifest is not pinned'
		[[ $expected_image == 0fb3e2504c62b7718c5e72237c38c9c409c6f07c6115f02ec157a8963a925d62 ]] || fail 'stable UDC V8 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'stable UDC V8 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'stable UDC V8 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-ncm-v9-generation118-live-v1)
		expected_boot_image=build/local-image-stage-ncm-v9-generation118-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 118 NCM-only full staging cycle; recovery transfer and COMMIT passed, target NCM never appeared, exact slot-A fastboot returned, no SSH transfer or storage write occurred, and intent resolved FALLBACK_RETURNED; never retry or flash'
		expected_boot_role='consumed Generation 118 NCM-only full staging cycle; target USB never appeared, exact slot-A fastboot and FALLBACK_RETURNED resolution passed, no SSH transfer, installer, or storage write; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-ncm-v9
		expected_bundle=local-image-stage-ncm-v9
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=3d5057d7cfd5599770888849e61757fa6746b687ea227c8a6ce0384c43353bdc
		expected_avb_digest=4bea3a9ae1d4fc52ed95d36ffddf7302de42307aa5ddfd8f774ced41cfd0ff0d
		expected_generation_record=d8229af2a19a1652d3ba5ba591a3a2c0e4e74ffc62e3ff8eea4c47b732c8b4f3
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == ec657d94aea6a71aa7efab80bcddba7794256209609ddc7031bd37764c17a4b5 ]] || fail 'NCM V9 manifest is not pinned'
		[[ $expected_image == 6e1fc8bf8e2c5f65d0e391c6b5275c8dceaf9f1c236d9feee23367a27e4ae1dc ]] || fail 'NCM V9 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'NCM V9 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'NCM V9 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-timing-v10-generation119-live-v1)
		expected_boot_image=build/local-image-stage-timing-v10-generation119-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 119 pre-storage timing cycle; exact 77.046-second recovery-departure-to-fastboot interval selected ncm-address after subtracting the 6.903-second immediate-return baseline; no target USB, UFS, userdata, SSH, installer, or storage write; never retry or flash'
		expected_boot_role='consumed Generation 119 pre-storage timing discriminator; 77.046-second exact USB timeline selected ncm-address; no target USB, UFS, userdata, SSH, installer, or storage write; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-timing-v10
		expected_bundle=local-image-stage-timing-v10
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=4279544470ece288b16484134c8881c629ce2f30e8ffd480827987e960e97440
		expected_avb_digest=b023509d73908c721f9d3b612b944147edf4d107ed611294804699e3fb92a8b5
		expected_generation_record=2f0c4d6ec7f3d787cc652451995173915cc3182681c7173d5a12069d2a5d63cd
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 8f4a7343af094b5a2210a7e5e8be6d2e494a6a93f10ee63d6bf540ab43701cb7 ]] || fail 'timing V10 manifest is not pinned'
		[[ $expected_image == 9a3279dd6de28072afba7926b800760dce60bd5e737849b39c48e46af0ebe154 ]] || fail 'timing V10 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'timing V10 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'timing V10 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-address-v11-generation120-live-v1)
		expected_boot_image=build/local-image-stage-address-v11-generation120-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 120 address-state cycle; exact 77.045-second USB timeline selected address-show-failed, proving usb0 vanished or became unqueryable immediately after link-up; no target USB, carrier, power-USB, UFS, userdata, SSH, installer, or storage; never retry or flash'
		expected_boot_role='consumed Generation 120 usb0 address-state discriminator; 77.045-second exact USB timeline selected address-show-failed immediately after link-up; no target USB or later subsystem/storage surface; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-address-v11
		expected_bundle=local-image-stage-address-v11
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=a43be1deb1c7b3c116d93ed4247417692d479a5596f99bbfbf8334bf35a264f3
		expected_avb_digest=57485c472458a5fa757ff7d67f22587b04bc633144a1066886f937d90f49535e
		expected_generation_record=d6f30b29a2132c1820880477ce53dc807dd59bf7d0fe5fe704ea479cfdd93824
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == fda8afcc23cdb35c782b72bc91c1975138dd8f7404acb40c7744badc03825678 ]] || fail 'address V11 manifest is not pinned'
		[[ $expected_image == 6bd965cf81d976d76f27b90b43d102a4e6d514285d89fdf5ec8664a17897a621 ]] || fail 'address V11 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'address V11 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'address V11 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-prebind-v12-generation121-live-v1)
		expected_boot_image=build/local-image-stage-prebind-v12-generation121-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 121 pre-bind-mdev cycle; exact 31.992-second return, no target USB, SSH, installer, or storage write; moving the second global mdev scan before bind did not fix enumeration; fallback and intent resolution passed; never retry or flash'
		expected_boot_role='consumed Generation 121 pre-bind-mdev full staging cycle; 31.992-second return with no target USB, SSH, installer, or storage write; fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-prebind-v12
		expected_bundle=local-image-stage-prebind-v12
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=a0dc1d2edd95364ee662fa7e461de085d92d5cf14ddce7a29f6e0ffa6803ff34
		expected_avb_digest=0f68dc8f68b195b04e18fb24b109bc9b2ccb7e56803525702307afe78b47c59d
		expected_generation_record=f5e29b0df3c064878a1a3d5871ce03401efe24ce6ae0012ffe71bc1a518a5304
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 60d264a02ba91ad0839f27a8d8054092dd435414d247a9bc50495ca470d5ac70 ]] || fail 'pre-bind V12 manifest is not pinned'
		[[ $expected_image == 08c78710259a8eb6da4545249ba86aaae2fed5e59d4eb6d6a1548c1050df80b5 ]] || fail 'pre-bind V12 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'pre-bind V12 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'pre-bind V12 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-explicit-v13-generation122-live-v1)
		expected_boot_image=build/local-image-stage-explicit-v13-generation122-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 122 explicit-sysfs cycle; exact 31.992-second return selected the 25-second UDC identity timeout plus restart overhead; no target USB, SSH, installer, or storage write; fallback and intent resolution passed; never retry or flash'
		expected_boot_role='consumed Generation 122 explicit-sysfs full staging cycle; exact 31.992-second return selected UDC identity timeout; no target USB, SSH, installer, or storage write; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-explicit-v13
		expected_bundle=local-image-stage-explicit-v13
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=42d0070f0525f774d9b4873cd8f57253fc9e43f39c767fb36878391bef2e5528
		expected_avb_digest=93448baf0ee52906be11c422e28fe7f6299f28223b5097ef9d3acb978d68c452
		expected_generation_record=8f1d044c80f18b93f81c5a6266bc85b1de2a17cb27dd2616439ca112c7b87999
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == eb742d37c8f937a95159f96f23f5d543c6657e1cf6e235659c38e206eff79b4c ]] || fail 'explicit V13 manifest is not pinned'
		[[ $expected_image == 5c693c5cbc91338c9f9d53a3c7425b51651e967729e766befe8cdfa49f472071 ]] || fail 'explicit V13 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'explicit V13 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'explicit V13 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-configfs-udc-v14-generation123-live-v1)
		expected_boot_image=build/local-image-stage-configfs-udc-v14-generation123-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 123 post-ConfigFS inventory cycle; exact 107.256-second return selected 25-second inventory window plus seen-zero delay, proving zero/exact a600000.usb churn with no unexpected UDC; no bind, network, or storage; never retry or flash'
		expected_boot_role='consumed Generation 123 post-ConfigFS UDC inventory classifier; proved zero/exact a600000.usb churn with no unexpected UDC; no bind, network, or storage surface; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-configfs-udc-v14
		expected_bundle=local-image-stage-configfs-udc-v14
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=bd0f350574ab3f70d9dce5dcfc08a89b0fe48e0c25dad4a645a4356584c48546
		expected_avb_digest=fe47f4a1fb2dca37ccc14debf1fd9ea0561649e60d3411045e77366763e14ba1
		expected_generation_record=a46559e9c33444d650fe8524a5917f8d2fe6545c462bc86440f780f38e7a3e6b
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == a9af841d12ecf27f28efed92562b2c5fd944a6db4f4f2e1594c26ad7b12a20dd ]] || fail 'ConfigFS UDC V14 manifest is not pinned'
		[[ $expected_image == 14a4ae239fd5b3a2ac134300f6cd7afaef4d11743af7db130db5bf226989cf4d ]] || fail 'ConfigFS UDC V14 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'ConfigFS UDC V14 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'ConfigFS UDC V14 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-two-sample-v15-generation124-live-v1)
		expected_boot_image=build/local-image-stage-two-sample-v15-generation124-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 124 two-sample UDC cycle; exact 32.248-second return selected the 25-second UDC timeout, proving no two consecutive 100ms exact samples; no target USB, SSH, installer, or storage write; fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 124 two-sample exact-UDC full staging cycle; no two consecutive samples, no target USB, SSH, installer, or storage write; fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-two-sample-v15
		expected_bundle=local-image-stage-two-sample-v15
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=07cd8aa54dda577f9844da63764f11cfb4de3e0b91d84ed7dce2e0e6c73f1b24
		expected_avb_digest=9a5a7cb7c0e63fcc6dd07fd0f0020c522912315f3430c48c5b34861deab8346f
		expected_generation_record=7d944cf309217311a30a95d4c03b3b432a9a1f93f4334b31f63f6debdf1251bf
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == df525ae6794d14b6aa8ee9d3076490ad8bfb47e25b792e15e4e7c7f461d48020 ]] || fail 'two-sample V15 manifest is not pinned'
		[[ $expected_image == 921173ef862bc69b0e578ffc91c97194cc00d4872e94d12eb0872d91e3807727 ]] || fail 'two-sample V15 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'two-sample V15 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'two-sample V15 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-bind-v16-generation125-live-v1)
		expected_boot_image=build/local-image-stage-bind-v16-generation125-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 125 scan-then-bind cycle; exact 32.504-second return selected the 25-second bind timeout, no target USB, SSH, installer, or storage write; full inventory scan remained too slow for the transient expected UDC; fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 125 scan-then-bind full staging cycle; 25-second bind timeout, no target USB, SSH, installer, or storage write; fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-bind-v16
		expected_bundle=local-image-stage-bind-v16
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=678b47bff0f02dceb4b53631561c90c6580c9ca4a07e66d38627f300d0e8db10
		expected_avb_digest=9b0551389333fb962a011d9aacae95a1a3ce602f2039a1339984dd355b5fba05
		expected_generation_record=6e8c3cd69a572bf25892dc52056aa224eb427a5826ed1bfb5870ea3ee8bbbd02
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == e2c25b000269fe5b752ea505ce54855ee00f4babbc04836ff50e94252d67e6c1 ]] || fail 'bind V16 manifest is not pinned'
		[[ $expected_image == e8f6a22641b2520c3a129854cf890449552e08898a6098adcaad8743ad2b4b32 ]] || fail 'bind V16 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'bind V16 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'bind V16 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-direct-v17-generation126-live-v1)
		expected_boot_image=build/local-image-stage-direct-v17-generation126-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 126 direct-bind cycle; exact 6.901-second immediate return proved the exact UDC bind write was refused while the expected path remained present; no target USB, SSH, installer, or storage write; fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 126 direct-bind full staging cycle; bind write refused with expected path present, no target USB or storage write; fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-direct-v17
		expected_bundle=local-image-stage-direct-v17
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=da53d59115b7e2be266432187e5dd498ca5e947b87c58b0635f0eac3df1d81a0
		expected_avb_digest=6010a61bbaca7e040afeb28925f385cace1a24a9b53ddbe4ea60a05866c70243
		expected_generation_record=557fbc4678db9d9f1bd665a951362c2d306e789e18bbafd0d56aa1832cb80c0a
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == e183d08e4814d5751c8bb4cc0e7f900cc1e030bc18335cc63c0dc821de2453eb ]] || fail 'direct V17 manifest is not pinned'
		[[ $expected_image == 4e8985de4d8f1a2a2c98541f9d6db683335a2c1018966dfdbedb22b2b7135d89 ]] || fail 'direct V17 recovery image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'direct V17 trust key is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'direct V17 host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-bind-error-v18-generation127-live-v1)
		expected_boot_image=build/local-image-stage-bind-error-v18-generation127-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 127 bind classifier; target NCM enumerated for 89.864 seconds, selecting bind-success; the host then filtered ROG5_local_image_stage from shared NCM inventory and missed the target; no target network configuration or storage write; exact slot-A fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 127 classifier; ConfigFS/NCM bind succeeded and target USB persisted for 89.864 seconds; host R7 model-filter defect prevented target acceptance; no storage write; slot-A fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-bind-error-v18
		expected_bundle=local-image-stage-bind-error-v18
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=2b4170a0bc3ecfda408d6921cfb22de05ad4d8ee80527d4560fc7f5f239e97ed
		expected_avb_digest=f697b2d27a669959231abd7ef595555d5b4d8d678c4ec5eacd55f6717d9247d8
		expected_generation_record=5e89de6009a6e9e407fb867d365a5a3ee37f868578f5dcb3602e9847555261b9
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 107b72178980a7eec7cce8e4e38a4d8d00a1ae1060234b1fdc41e38a89b4396b ]] || fail 'bind-error manifest is not pinned'
		[[ $expected_image == 5a1b1e8adb5336d0db720b42e2b26824f6c6fc31509aa798de9f67e9f264867c ]] || fail 'bind-error image is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'bind-error trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'bind-error verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-hostfix-v19-generation128-live-v1)
		expected_boot_image=build/local-image-stage-hostfix-v19-generation128-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 128 full staging cycle; exact 6.903960-second recovery-departure-to-slot-A-fastboot return proves immediate post-bind failure before target USB, SSH, installer, or storage; Linux 7.1 ConfigFS store semantics and prior empty/exact class oscillation identify the post-bind UDC-class level check as false; never retry or flash'
		expected_boot_role='consumed Generation 128 full staging cycle; immediate false post-bind UDC-class invariant forced fallback before target USB or storage; exact slot-A fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-hostfix-v19
		expected_bundle=local-image-stage-hostfix-v19
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=8d8fd7ef40834912a9c4623e49a3bd716dbff29eeae81878f60ec1ef781e095d
		expected_avb_digest=9e3deac8f8df5605c1e923cc4074a35357320b9d436a188bcf44cb0a76a618a4
		expected_generation_record=1b4f4eccd4d5cc0f1ee8e890947d356557bca1887bcfa53c1e4583c2940c42e7
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == d5022e9a967bda3171492caba4e4ddf1d5d22bca022cf2b27d2fa1f9e7ef911c ]] || fail 'hostfix V19 manifest is not pinned'
		[[ $expected_image == f1cbb906fdf1ebff9f79ecebabc9775a630bf9ca923bf1206dcacdb87ce262d0 ]] || fail 'hostfix V19 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'hostfix V19 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'hostfix V19 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-postbind-v20-generation129-live-v1)
		expected_boot_image=build/local-image-stage-postbind-v20-generation129-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 129 full staging cycle; removing the false UDC-class check advanced to exact target NCM enumeration for 0.519517 seconds, then target rollback before host activation; no SSH, installer, or storage write; exact slot-A fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 129 full staging cycle; exact target NCM enumerated for 0.519517 seconds, then target rollback before host activation; no storage write; slot-A fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-postbind-v20
		expected_bundle=local-image-stage-postbind-v20
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=b614126bb730862db7143648c2743585da016e28236e8952ce6efec796cf8a82
		expected_avb_digest=e7fa42d7da885ba0567b94c5ded5a38386683731d64e4111d056321068534208
		expected_generation_record=bd65e552d62447e38b7b33f59aeb6290029c42c243432461351e9bab6e4af10f
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == c38000c3818d0c170eca7150517d127b6feef75819072d56f33f40840cdfba6c ]] || fail 'postbind V20 manifest is not pinned'
		[[ $expected_image == 53b74a355527114f65004753bef479665d84d16b1fe0a3b1a57684c8dfb3fed0 ]] || fail 'postbind V20 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'postbind V20 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'postbind V20 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-power-report-v21-generation130-live-v1)
		expected_boot_image=build/local-image-stage-power-report-v21-generation130-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 130 cycle; exact target NCM stayed up for 10.506 seconds and the reporter dwell executed, but the host called the SSH-only helper and never opened the existing stage listener; exact slot-A fallback passed, no SSH, installer, or storage write; never retry or flash'
		expected_boot_role='consumed Generation 130 cycle; target NCM/reporter dwell passed but host used the SSH-only helper and missed stage detail; no storage write; slot-A fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-power-report-v21
		expected_bundle=local-image-stage-power-report-v21
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=01087dab001854d4c7a8c8ed93bc863bf6876de8dd8a53a025c2fa85b8b2e26d
		expected_avb_digest=bf8c1475d829c4d14406ef8c4f36b498d63de9e18cb7ed92862a6233f822b2d5
		expected_generation_record=2961e247c535c32ec1cb462702461a740e85d4ed8372b67c4c30f0791f8a9c1e
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == f333316ac70170a7f3f2afc62679633191d47a5103e979f040c9b404d3222915 ]] || fail 'power-report V21 manifest is not pinned'
		[[ $expected_image == a1cc3db2cc2ed024728db50d7aa8b6def555990814c9a4861b0fa18ea6ec3923 ]] || fail 'power-report V21 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'power-report V21 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'power-report V21 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-listener-v22-generation131-live-v1)
		expected_boot_image=build/local-image-stage-listener-v22-generation131-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 131 cycle; exact stage listener captured power-usb/module-qcom-q6v5-load, proving the packaged module vermagic 7.1.4-gae717d919f87 mismatched target 7.1.4-g359318de534f; no UFS, SSH, installer, or storage write; exact slot-A fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 131 cycle; exact stage detail proved qcom_q6v5 module vermagic mismatch before UFS or storage; slot-A fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-listener-v22
		expected_bundle=local-image-stage-listener-v22
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=96097ff27b9f9d97741213db42c5c4a52fa97472379d0a7bbc287ed5137ea4ac
		expected_avb_digest=d77d6da6c8344f16db13284769ba9acea9073c001c9b5654881cf19d93263955
		expected_generation_record=d7e56413556c4bdce6e3ed2eccf40517553b99e7a7a57350446fd38788ca3555
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 84a21be69df111e4b4f539949d9fd3d4f9a0eee46ea6eb05a57d7cbf7d41d680 ]] || fail 'listener V22 manifest is not pinned'
		[[ $expected_image == ef44ce1ad9f76e7223b2136beb474ae9f5abf8c64527514243e105c20aa4f654 ]] || fail 'listener V22 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'listener V22 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'listener V22 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-abi-v23-generation132-live-v1)
		expected_boot_image=build/local-image-stage-abi-v23-generation132-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 132 cycle; exact g359 power/USB module chain passed and UFS modules loaded, then stage ufs-ready failed at generic ufs-count after the bounded 20-second enumeration wait; no SSH, installer, or storage write; exact slot-A fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 132 cycle; g359 power/USB modules passed, UFS modules loaded, then bounded UFS inventory count failed before storage; slot-A fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-abi-v23
		expected_bundle=local-image-stage-abi-v23
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=f13fd0977f3a0a189d1452852f1702cf550e17586ad63c89ab410de1df2fbd85
		expected_avb_digest=978876e0d428bb1d0a08fefbd235d58eed07e4ff580cf79354035daff1fff486
		expected_generation_record=6584fd4f8152bdee7c115d8de84d028b5d68227e00ffc9740868e0db3059d092
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == ce0f2c191afaf5c4ed49fc513062422b54c1cab3639e462cd63e00a372b02a1b ]] || fail 'ABI V23 manifest is not pinned'
		[[ $expected_image == 7e555e989ceed7db4f71a6f2195b802cbc532460892e4511a41a51db4ca5c114 ]] || fail 'ABI V23 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'ABI V23 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'ABI V23 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-ufs-count-v24-generation133-live-v1)
		expected_boot_image=build/local-image-stage-ufs-count-v24-generation133-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 133 cycle; exact g359 power/USB and UFS module insertion passed, then the bounded UFS inventory was exactly zero; no SSH, installer, block device, mount, or storage write; exact slot-A fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 133 cycle; exact post-module UFS physical count was zero before every storage surface; slot-A fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-ufs-count-v24
		expected_bundle=local-image-stage-ufs-count-v24
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=d315e9a0395847669606365e12dfdadbae6282fd74a135ddb52867850abb0f63
		expected_avb_digest=deed158a963d8626157b332138fef7b862e50579a21e5aec4a839dbee1ca85d3
		expected_generation_record=d778f560c1569c3ceb9949ea6268ad2bca17aec2dc5e9ab69af0267799fa1683
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 4c6740b23fad063b618c3e61d708320549acc44df7149799695a410f85badc9a ]] || fail 'UFS-count V24 manifest is not pinned'
		[[ $expected_image == 0307e45641fb074978770f8c52cfe670e8715fe0347681357f2dfaaf8a1ffff4 ]] || fail 'UFS-count V24 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'UFS-count V24 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'UFS-count V24 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-ufs-bind-v25-generation134-live-v1)
		expected_boot_image=build/local-image-stage-ufs-bind-v25-generation134-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 134 cycle; exact zero-UFS classifier reported ufs-platform-0, proving no runtime platform device matched the 0x1d84000 controller address; no SCSI host, block device, mount, SSH, installer, or storage write; exact slot-A fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 134 cycle; exact classifier proved no runtime UFS platform device before every storage surface; slot-A fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-ufs-bind-v25
		expected_bundle=local-image-stage-ufs-bind-v25
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=43b3294bc1de9ae63ab59c8e6f9a450b9e68872fedac31cb6e00531127e96d5b
		expected_avb_digest=cf238ead4e542e289d5806fb027e180276aa9de0955c68075f0b1b0b2f5baefd
		expected_generation_record=c5250925619aeb017375bcbb218ada671bde089734675166252ca856f14113ce
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 479cc3f958dda3d2cc81cc4a17e243483eeff52d8e255c4fc5ce6fa9036f8e03 ]] || fail 'UFS-bind V25 manifest is not pinned'
		[[ $expected_image == e09090c755def38700ca85c14468512d9c6016c8884a916db6190836a9f0ebf1 ]] || fail 'UFS-bind V25 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'UFS-bind V25 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'UFS-bind V25 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-runtime-dt-v26-generation135-live-v1)
		expected_boot_image=build/local-image-stage-runtime-dt-v26-generation135-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 135 cycle; runtime UFS DT node existed with exact okay status, while the address-name platform scan found zero candidates; no SCSI host, block, mount, SSH, installer, or storage write; exact slot-A fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 135 cycle; runtime UFS DT was okay but address-name platform scan returned zero before storage; slot-A fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-runtime-dt-v26
		expected_bundle=local-image-stage-runtime-dt-v26
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=f0e064ae3facd2d72b1e00bb4aa3581c09334580790b68e43049303548f94210
		expected_avb_digest=811830ebf4b7915b4cacac210d58400006a9c6925322ce97adcf44fb994b0b10
		expected_generation_record=8541e4a10b6446ba49ee74be4039c247aa04d7abd250d21d234acfea890b47b8
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == a55460c67633aaa3506747b8c4e8baf43656c71b9e9fa9abfdcb036f58bd6f8f ]] || fail 'runtime-DT V26 manifest is not pinned'
		[[ $expected_image == bf0de9becc81268934149e111e80c23fd354ad34dc0b35013788b77f318f99a8 ]] || fail 'runtime-DT V26 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'runtime-DT V26 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'runtime-DT V26 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-of-node-v27-generation136-live-v1)
		expected_boot_image=build/local-image-stage-of-node-v27-generation136-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 136 cycle; exact of_node platform matching still reported ufs-dt-okay-platform-0, proving the current g359 Image/DT pair creates no UFS platform device; no SCSI, block, mount, SSH, installer, or storage write; exact slot-A fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 136 cycle; exact OF identity confirmed no UFS platform device under the current Image/DT pair; slot-A fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-of-node-v27
		expected_bundle=local-image-stage-of-node-v27
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=564103f16f6fe6ee96c148a98677cf3870c99131ce74946aa155528df40ca927
		expected_avb_digest=f76b5daf561c7bf2ef08f4f096ac4dfaec580b0d0855324ff87a1afb5f8e6881
		expected_generation_record=dd436d7728a792178a482171168feeed93d3f52c1967caff167455108fd4794f
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 4c10245dfc2651f7eae4c4f466a632b7bd01c04dfe2c81f03354bf8a56159b69 ]] || fail 'OF-node V27 manifest is not pinned'
		[[ $expected_image == c654a28f4ed8834dbd84e863c61ee87b2c9e4e37e10df877a8804c5e20ab9051 ]] || fail 'OF-node V27 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'OF-node V27 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'OF-node V27 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	ufs-baseline-proven-v28-generation137-live-v1)
		expected_boot_image=build/ufs-baseline-proven-v28-generation137-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 137 cycle; exact live-proven g359 Image, DTB, and four modules still reported ufs-count-0 after stable NCM and a bounded 20-second wait; no storage surface or write; exact slot-A stock recovery USB returned and passed after the current descriptor policy correction; never retry or flash'
		expected_boot_role='consumed Generation 137 cycle; live-proven g359 target still reported ufs-count-0; exact stock slot-A recovery fallback passed after the current descriptor policy correction; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=ufs-baseline-proven-v28
		expected_bundle=ufs-baseline-proven-v28
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=c40b7b3d137c8b002d32e4acbeb587f989772b77b607855db0a196156efb4614
		expected_avb_digest=2ea88831747c78164fe27a41b9814b03f9815a233663d9d36e99e42d0dc21003
		expected_generation_record=3bb78adc79a92887fafb04459f16ef58198ebbeceb733a43a34a0e54286d11e2
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 914681f89fe74cf657efc33a26c5ee18f21d31940105491c8e57d21621b555c2 ]] || fail 'UFS baseline V28 manifest is not pinned'
		[[ $expected_image == 68e3a66778bc69356f2fb2aa82adc9e48aa9ec53e6809e77c94a7da2d0f81ce4 ]] || fail 'UFS baseline V28 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'UFS baseline V28 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'UFS baseline V28 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	ufs-reboot-baseline-v29-generation138-live-v1)
		expected_boot_image=build/ufs-reboot-baseline-v29-generation138-20260824-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 138 cycle; exact ae717 Image, DTB, and four UFS modules still reported ufs-count-0 because the minimal init omitted the packaged power/USB dependency loader; built-in reboot mode returned exact fastboot; no storage surface or write; never retry or flash'
		expected_boot_role='consumed Generation 138 cycle; ae717 target still reported ufs-count-0 because minimal init omitted the packaged power/USB loader; exact fastboot fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=ufs-reboot-baseline-v29
		expected_bundle=ufs-reboot-baseline-v29
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=3dab00f45d8079e9d74965cc4f2fa41df79571f43dec78cc90e9d6b6b814ef75
		expected_avb_digest=a43a2e2281a820503a0ce72f420254afb1953275cd1b89720003e02399a2aa52
		expected_generation_record=51ffd4acab0211d1cdb5ea06f2f3c636a78d02b775e4ce6c8bf33319c32ae977
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 836ef28ffcf42c5f883b5456da9348b06f091d532d9855eff2a38fe1280bdf4f ]] || fail 'UFS reboot baseline V29 manifest is not pinned'
		[[ $expected_image == c97163219436d0903aa6130c34f8741381060fdb3e929dbf4a494a26d1839ba8 ]] || fail 'UFS reboot baseline V29 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'UFS reboot baseline V29 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'UFS reboot baseline V29 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	ufs-power-reboot-baseline-v30-generation139-live-v1)
		expected_boot_image=build/ufs-power-reboot-baseline-v30-generation139-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 139 cycle; the exact power/USB loader passed but UFS still falsely reported count zero because `set -f` disabled every fixed sysfs glob in the minimal init; built-in reboot mode returned exact fastboot; no storage surface or write; never retry or flash'
		expected_boot_role='consumed Generation 139 cycle; power/USB passed but set -f suppressed every UFS sysfs glob and falsely reported zero; exact fastboot fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=ufs-power-reboot-baseline-v30
		expected_bundle=ufs-power-reboot-baseline-v30
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=c28264670666fbce5c099912cfd9865d2f65492f48f3bd049fdab216e7a31f11
		expected_avb_digest=119ed2162b32adc397a39b857d27a58fd1cdeb1790cfe54c5f14dda58598a897
		expected_generation_record=46a550f35e38582cd577cd09d5158548688a997b38f89b7bd75264f35228a33d
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 21d28652ffd53bb3472194e781d32b6a32ce7cd377ed39c8f741f38384af10fc ]] || fail 'UFS power baseline V30 manifest is not pinned'
		[[ $expected_image == a33451c6c46500ad738fc8985f1fe2d6c00bfdb8ac8f2380811478c0816cd8af ]] || fail 'UFS power baseline V30 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'UFS power baseline V30 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'UFS power baseline V30 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	ufs-glob-reboot-baseline-v31-generation140-live-v1)
		expected_boot_image=build/ufs-glob-reboot-baseline-v31-generation140-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 140 cycle; exact power/USB and corrected sysfs discovery proved the complete 116-node UFS topology, then built-in reboot mode returned exact fastboot; no mount or storage write; never retry or flash'
		expected_boot_role='consumed Generation 140 cycle; power/USB and complete 116-node UFS topology passed; exact fastboot fallback passed; no write; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=ufs-glob-reboot-baseline-v31
		expected_bundle=ufs-glob-reboot-baseline-v31
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=3fd06106594aeff17209556c63aa6c475537a1763f3d40740a4e2a5fb1870add
		expected_avb_digest=72c27c19a8a4d8269b3a5d22438e0119cec000b9b5e09efd6efc39760a72f001
		expected_generation_record=044b89cbdb5461ae24519edec9c4099d8de9c627d0cff611cab8515003eb6fb8
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 5b19fd9c2df7bb9f1b61a4b879416b92e17b66c3d31294015ce918f0673a832f ]] || fail 'UFS glob baseline V31 manifest is not pinned'
		[[ $expected_image == 9b29868ced920374291f5aa076a5ea6be7f95918d9df4c96acd217592899b78c ]] || fail 'UFS glob baseline V31 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'UFS glob baseline V31 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'UFS glob baseline V31 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-glob-v32-generation141-live-v1)
		expected_boot_image=build/local-image-stage-glob-v32-generation141-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 141 cycle; power/USB and UFS passed and target host key was pinned, but zero-byte `/etc/nologin` blocked OpenSSH before authentication; no image transfer, installer, mount, or storage write; bounded watchdog fallback; never retry or flash'
		expected_boot_role='consumed Generation 141 cycle; UFS passed but sealed nologin blocked SSH before transfer or write; bounded fallback; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-glob-v32
		expected_bundle=local-image-stage-glob-v32
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=f7a5ebc5e53362401bc7674c249c7a3b89ab56f81685dbfc114f1dddc5c2916e
		expected_avb_digest=30e6304145fe01a85ffdee4868dde59b1d3dc3153b80012b18ace74b955a0f41
		expected_generation_record=703019527c364ddc06e101c85388c68f6b9b425054859138b82fb687f76afabc
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == d4fa6160215e68a8919f077894e8b608aa3bf645c93bf2267a90c643c78501d4 ]] || fail 'local-image glob V32 manifest is not pinned'
		[[ $expected_image == 0cf741336db85fb6804dfe20720d8680a4f113e74f5c627326084c44977f210b ]] || fail 'local-image glob V32 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'local-image glob V32 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'local-image glob V32 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-ssh-v33-generation142-live-v1)
		expected_boot_image=build/local-image-stage-ssh-v33-generation142-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 142 cycle; post-COMMIT cleanup hit a transient NetworkManager ownership gap on newly enumerated target NCM before target activation, no target stage/SSH/transfer/installer/write evidence, exact fastboot fallback and cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 142 cycle; transient host NetworkManager ownership gap before target activation; no stage, transfer, or write; exact fastboot fallback; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-ssh-v33
		expected_bundle=local-image-stage-ssh-v33
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=302b9471b121e78ee316405526e1d5d394e3af6b99d14b90154c94a44a0d7495
		expected_avb_digest=cb5f694445e4be43acebb4c0644209f3b35343ea6ee3ca422cab204f3c850002
		expected_generation_record=4d7d3f43e753b0c27563d3052a4cf18566a1d7b01048ed26c99dc7ecd4360fd8
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 333527612db0575cad1df5066bf1dce17c3d4e8a53a7b9b45db1c25936ed831f ]] || fail 'local-image SSH V33 manifest is not pinned'
		[[ $expected_image == 246d5c374495a72690a17ec808aef7b0165cd7f95268bdca453330df2af3ea28 ]] || fail 'local-image SSH V33 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'local-image SSH V33 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'local-image SSH V33 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-nm-v34-generation143-live-v1)
		expected_boot_image=build/local-image-stage-nm-v34-generation143-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 143 cycle; NetworkManager ownership classification no longer aborted, but redundant post-COMMIT host cleanup delayed target activation until it returned fastboot before host-key readiness; no stage/transfer/installer/write; fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 143 cycle; redundant post-COMMIT cleanup delayed target activation; no stage, transfer, or write; exact fastboot fallback; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-nm-v34
		expected_bundle=local-image-stage-nm-v34
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=a1547e01d533f5d0c4d81328799942fe3b032ee9828af7531d49531484784426
		expected_avb_digest=c763b51213f2c5cd5189ff42a96e399050bad61ef9311b94c6d80cbb33932cfc
		expected_generation_record=2e110d65e9114bd8b4b1fb3b51ac39c0cff5bfdfa6be4387cda31accd85795d0
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 0179be7e66ac350caf2483ab15df63ef95ddfc76bbc5b56a3bbf7139aa155208 ]] || fail 'local-image NM V34 manifest is not pinned'
		[[ $expected_image == 341b81e39a96de5b697ef400aeeb01b8cb1cac04fd6f41579f75233f9a6a460a ]] || fail 'local-image NM V34 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'local-image NM V34 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'local-image NM V34 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-fast-v35-generation144-live-v1)
		expected_boot_image=build/local-image-stage-fast-v35-generation144-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 144 cycle; immediate activation worked and UFS passed, then an uninstrumented post-UFS pre-SSH failure returned exact fastboot; no transfer, installer, mount, or write; fallback and cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 144 cycle; immediate activation and UFS passed, then uninstrumented pre-SSH failure; no transfer or write; exact fastboot fallback; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-fast-v35
		expected_bundle=local-image-stage-fast-v35
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=df960e44f316e021088e1f5abae3fefd11420b7c43abf2fa35f1a80feb7e7fc3
		expected_avb_digest=7cf4cf6369d68d06956e9aa837adfa021117bf903153481bf11c479fa88a151d
		expected_generation_record=b5d2e8afc0568c1af527c6cf02e2df44ebe89c0f1939a602cf1ab81659602a5b
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 48fc8bb69fc0d0b0a74f12ba654445d1c723f5aa19081b8c856b35ab5390dfa3 ]] || fail 'local-image fast V35 manifest is not pinned'
		[[ $expected_image == f0c969247818c4f44c2f23746a5967d93195d32fbd6a908536dd20d963b014ac ]] || fail 'local-image fast V35 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'local-image fast V35 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'local-image fast V35 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-stages-v36-generation145-live-v1)
		expected_boot_image=build/local-image-stage-stages-v36-generation145-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 145 cycle; power/UFS, userdata identity, and storage lock passed, runtime failed exact nologin-identity because the member was absent rather than empty; no SSH/transfer/installer/write; fastboot fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 145 cycle; runtime nologin-identity failed on absent member; no SSH, transfer, or write; exact fastboot fallback; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-stages-v36
		expected_bundle=local-image-stage-stages-v36
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=20aab540582307341c3e185b0b37d929aa4da983b1791969e4c181b115fd086b
		expected_avb_digest=e0171db1055e9184d401904f26a8fdc5a03adbb7c3036f0038af609c9dee7c13
		expected_generation_record=7047c3fbb3889aa1e71811bed90b2a2409235d8aa3971fec6507d0309ba4ff0e
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 70f3cb11d345e42a961e9b2a0ad4d5a6f43462d106c237dd67f678944a7c805f ]] || fail 'local-image stages V36 manifest is not pinned'
		[[ $expected_image == 75553f817e821103daee7dc8ff5e22a8157a4d6d602cb018e24d75f59dfff229 ]] || fail 'local-image stages V36 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'local-image stages V36 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'local-image stages V36 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-auth-v37-generation146-live-v1)
		expected_boot_image=build/local-image-stage-auth-v37-generation146-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 146 cycle; exact UFS, key-only SSH, and gzip transfer passed, then installer set -f suppressed its userdata and relock globs and failed before creating an image path; exact fastboot fallback and cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 146 cycle; key-only SSH and exact gzip transfer passed, then installer set -f suppressed userdata/relock globs and failed before creating an image path; exact fastboot fallback; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-auth-v37
		expected_bundle=local-image-stage-auth-v37
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=c88ae8fd8d69859fa979208d4e33d71207067c373ce041b9cc8c56690640d135
		expected_avb_digest=e9794d9e34229ade0b94bf4908e787b59fdaee8c24fd1a629e190fac04a15400
		expected_generation_record=7ef1b1451dcbc16c4d396177b68c57e05ff498c76fe509da90a4b9f05c6ed827
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 2d528cbcec4c2b1f19045767921cd12bb181c9e3ee5458e7226f4fb12eead029 ]] || fail 'local-image auth V37 manifest is not pinned'
		[[ $expected_image == 7ebb3394bf47630b6dabe73ef0bbd8c9164582d4b6e8a378c91889e7ed0433e8 ]] || fail 'local-image auth V37 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'local-image auth V37 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'local-image auth V37 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-globfix-v38-generation147-live-v1)
		expected_boot_image=build/local-image-stage-globfix-v38-generation147-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 147 cycle; exact UFS, key-only SSH, transfer, and installer glob passed, then exact write-window failed before mount or image creation because the child was cleared before its read-only parent; fastboot fallback and cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 147 cycle; UFS, SSH, transfer, and installer glob passed, then parent-child read-write transition remained effectively read-only; no mount or image path; fastboot fallback; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-globfix-v38
		expected_bundle=local-image-stage-globfix-v38
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=71ac845d9e123e9710f31875619059bcbfc201c34448f48e728341dd4a7a796c
		expected_avb_digest=e415a75606a0e235ca431aa5b876cb444737895b46236f2c0dc65c2f9496828d
		expected_generation_record=8e0eb6d6816daf5493f2cf37c6ff3fb7bc940d7d31f9902156a1a3114727cf08
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 1930e049f1f180e90cfcb8e877cb1108e1f1b9a15f3beaf421f4aeac3901a1e6 ]] || fail 'local-image globfix V38 manifest is not pinned'
		[[ $expected_image == 7f2203a94b4dfc98f15e2a02f29c18cf7b8dbcea24983e66597898e512292563 ]] || fail 'local-image globfix V38 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'local-image globfix V38 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'local-image globfix V38 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-rworder-v39-generation148-live-v1)
		expected_boot_image=build/local-image-stage-rworder-v39-generation148-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 148 cycle; exact UFS, SSH, and transfer passed, then disk-rw-state proved the deployed ae717 Image lacks bounded data-write support; no mount or image path; fastboot fallback and cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 148 cycle; exact disk-rw-state proved the deployed ae717 Image is compile-time read-only; no mount or image path; fastboot fallback; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-rworder-v39
		expected_bundle=local-image-stage-rworder-v39
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_target_timeout=600
		expected_avb_salt=b336cd03aa3fb1df77bc9cd52c58d05d5c324abe3d274b42eb10df214f6a4570
		expected_avb_digest=3259932819dc1ce42464f510606e608bc7a170e6f5a98c311c68ceb77376c60b
		expected_generation_record=d820e86414f613451861bdf63a6376cf49ad57e0426f4353976fbb3f95ea32c6
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 59a2ebc8798354545159cf24a836cc23fe9e9a031eea7c7fe181f8674ee8dab3 ]] || fail 'local-image rworder V39 manifest is not pinned'
		[[ $expected_image == ed8611651c205a91b2ad457bb3889a366c304d3f67c7421c1cba1f0269dac002 ]] || fail 'local-image rworder V39 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'local-image rworder V39 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'local-image rworder V39 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-stage-writekernel-v40-generation149-live-v1)
		expected_boot_image=build/local-image-stage-writekernel-v40-generation149-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 149 cycle; write-capable UFS, SSH, and transfer passed, dense decompression created about 826 MB of the bounded partial file, then gzip and sync entered uninterruptible UFS I/O; exact bootloader fallback required the sealed restart reason plus emergency SysRq; never retry or flash'
		expected_boot_role='consumed Generation 149 cycle; bounded-write kernel worked, but dense 16 GiB decompression reached about 826 MB then UFS I/O stalled in D state; emergency exact fastboot fallback; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-stage-writekernel-v40
		expected_bundle=local-image-stage-writekernel-v40
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=2480863b45bcb0d9dd3618ccb175e1dcb74d20ad04c00721ade82c6904ebf585
		expected_avb_digest=a4f4f71055b2d7301692d435c4c831f30923225de98736399f62f828e34f92e5
		expected_generation_record=c2e3e0354675281a351653a4524213fa5b8c1dee3138ad74a7ea8183520a39b6
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 4ed06aa453489f7666c3f7ccb55e519a9fa4074c03edda496326810beed57606 ]] || fail 'local-image writekernel V40 manifest is not pinned'
		[[ $expected_image == e001c6e580b3a07ee0c863e2a4d72b1a4e68c74edd01cae79e46907870bcadfa ]] || fail 'local-image writekernel V40 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'local-image writekernel V40 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'local-image writekernel V40 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-write-benchmark-v41-generation150-live-v1)
		expected_boot_image=build/local-image-write-benchmark-v41-generation150-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 150 cycle; UFS and SSH passed, then the benchmark rejected post-crash partial metadata before creating its benchmark directory or writing data; exact fastboot fallback and cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 150 cycle; post-crash partial metadata differed from the exact pre-crash tuple, so no benchmark write ran; exact fastboot fallback; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-write-benchmark-v41
		expected_bundle=local-image-write-benchmark-v41
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=85bf6ac75b9d395badc8263f5eab7c3feeef0b5c630fbf98174e33828e8a6a3b
		expected_avb_digest=ee54c329e657518e9b8c4d4eb1bc47b2dfd39c2bdceb8b7863ab6d96c0906781
		expected_generation_record=9939299d9f3c5fb24f385729d913de30d99f019700481c88c2ebdaf6f7215547
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 48022ec8595d57b4cb64445fd4802879e0c652a96db31937dc2bd6826a23361a ]] || fail 'local-image write benchmark V41 manifest is not pinned'
		[[ $expected_image == e28b4c489e9507a5dba48b5c94af844c087fcf5d01efc7371343830db577cb12 ]] || fail 'local-image write benchmark V41 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'local-image write benchmark V41 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'local-image write benchmark V41 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-write-benchmark-v42-generation151-live-v1)
		expected_boot_image=build/local-image-write-benchmark-v42-generation151-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 151 cycle; the bounded partial continued growing after the earlier snapshot and exceeded 825884672 bytes, so no benchmark directory or data write occurred; exact fastboot fallback and cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 151 cycle; partial exceeded the transient 825884672-byte snapshot while prior D-state I/O drained, so no benchmark write ran; exact fastboot fallback; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-write-benchmark-v42
		expected_bundle=local-image-write-benchmark-v42
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=7704027d03708d62e0a20f58aa1286f40c0a4a6078e655593fd7f5dc84cbdc1a
		expected_avb_digest=60c556599105d17c63f71ef3834a37787d6b5e268f989a1f248c620b1b87fdba
		expected_generation_record=4d21a50bac3c86271fa26f66f75ee57e97daf0c82f4fae2e8b053c9f3b7046db
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == eda3bd6c644adb12254cf92d1c32dab1ace1982809227f0eb1917286c8cd36e9 ]] || fail 'local-image write benchmark V42 manifest is not pinned'
		[[ $expected_image == a90a25e8270e85205f1898c02e7ce8b146a0e583770cba93cf1f7e23e99a2e35 ]] || fail 'local-image write benchmark V42 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'local-image write benchmark V42 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'local-image write benchmark V42 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-write-benchmark-v43-generation152-live-v1)
		expected_boot_image=build/local-image-write-benchmark-v43-generation152-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 152 cycle; partial-identity still failed under the full logical-image size bound, proving type, owner, mode, link count, or another field differs; no benchmark directory or write; exact fastboot fallback and cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 152 cycle; partial-identity still failed under the full logical-size bound, proving another metadata field differs; no benchmark write; exact fastboot fallback; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-write-benchmark-v43
		expected_bundle=local-image-write-benchmark-v43
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=813b8a2ebc980ceaf3036f411fcb64922ac46acb6d36718307ce277bbee76c32
		expected_avb_digest=433c4bcf801f2373c1c14b9122f2ca63195f999ae3def95a2f6abb86457affa4
		expected_generation_record=e89d88c62e6d43da87d7d4143f50b3b7e93d104250eb190f702e926115769627
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 65203683173ceacfa412d5dad54662bf46a7aa823016e2129c9aea869f3cf0c6 ]] || fail 'local-image write benchmark V43 manifest is not pinned'
		[[ $expected_image == c51667b372cc5a731adae10917f69ea33faa0bf4d76f0aa05db89cb248ca5489 ]] || fail 'local-image write benchmark V43 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'local-image write benchmark V43 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'local-image write benchmark V43 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-partial-inspect-v44-generation153-live-v1)
		expected_boot_image=build/local-image-partial-inspect-v44-generation153-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 153 read-only cycle; exact evidence proves the partial is regular root-owned mode 0644 one link with size zero and zero allocated blocks, final absent, and parent directories exact; no phone write; fastboot fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 153 read-only cycle; partial is regular root-owned mode 0644 one link with zero size and zero blocks; final absent; exact fastboot fallback; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-partial-inspect-v44
		expected_bundle=local-image-partial-inspect-v44
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=52f991bb75356b71653edcc05bc7c4b4140cffa9e7c447c4dea7be7a8370ab6a
		expected_avb_digest=9fe951932f36a0ae77d65e7cf787f142d310233ae8a1926e4afe493accaf07a9
		expected_generation_record=bc5c690dad1b312b380a063e4b50c5aa0b7d7113d8b29a9f005b3ea7ef87295d
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == f5d6229a85f2842cb3c0242f01b7788fc99f6443ade34d330ccd251433856dde ]] || fail 'local-image partial inspection V44 manifest is not pinned'
		[[ $expected_image == d05d4730a65bc6b2c1018b436996bb9aea56fead90a08f23e50516594845152b ]] || fail 'local-image partial inspection V44 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'local-image partial inspection V44 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'local-image partial inspection V44 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	local-image-write-benchmark-v45-generation154-live-v1)
		expected_boot_image=build/local-image-write-benchmark-v45-generation154-20260825-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact Generation 154 cycle accepting the proven root-owned regular mode-0644 one-link zero-length partial, then comparing one 32 MiB aligned direct write with one 32 MiB buffered write; disposable cleanup and sync-independent fallback; RAM-only; never flash or retry after entry'
		expected_boot_role='consumed Generation 154 cycle; direct 32 MiB passed in 50.25 seconds, buffered fsync blocked, sync-independent rollback returned exact fastboot; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783
		expected_raw=4f9ac4e7afd4b5bf46a8a79188a0376406fcca294a8cc1648e4f0a44fc82d9f8
		expected_initramfs=c57ca89da4bddb5f369c4342fc83bd78a738b7733e507e13be454ac501d2f7fb
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_config=df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f
		expected_target_id=local-image-write-benchmark-v45
		expected_bundle=local-image-write-benchmark-v45
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_target_timeout=600
		expected_avb_salt=f12517ba837c44633708dce9ea272b8a8eacaa25710fd8eab007b02a147f2a85
		expected_avb_digest=54171e4abfa9406c55b4bb28ae66132018cf58cc9a15d9a18ef519d9d5e9fb16
		expected_generation_record=36c4e08f65573803f9737290a505f7f200b50e1211107e89ce115a30b58a248e
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == 14741fb36498f039e1711719ad542fa88e5b3b990a147d0877dbd8b400b8f25e ]] || fail 'local-image write benchmark V45 manifest is not pinned'
		[[ $expected_image == 49fbe0fa5f243a522d29f8fcab34dc4618ad797d3ca9e36124c3db568324b839 ]] || fail 'local-image write benchmark V45 recovery is not pinned'
		[[ $expected_trust == cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] || fail 'local-image write benchmark V45 trust is not pinned'
		[[ $expected_host_verifier == 04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] || fail 'local-image write benchmark V45 verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-ufs-phy-control-v12-live-v1)
		expected_boot_image=build/persistent-root-qmp-ufs-phy-control-v12-generation33-20260812-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact QMP-UFS PHY return-and-NCM-survival discriminator; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 33 QMP-UFS PHY-only return-and-NCM-survival discriminator; Generation 32 kernel/modules, clean-twin initramfs, signed bundle; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6
		expected_initramfs=3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-ufs-phy-control-v12
		expected_bundle=persistent-root-qmp-ufs-phy-control-v12
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gcfd385a1c754
		expected_avb_salt=0e3ded143370a1b9eb6d39a08b823c2c61d80d83f7b9ba8c2789b39a05291342
		expected_avb_digest=07710a05e2c16f4d5e40a7b5a6e60fd3d1415e0df78f417efe958964f0e95f88
		expected_generation_record=57f7e45003571d8606114b15b5b9970d755d629b0b276327d3d90b0fdae8e671
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			330f33a533f8f65e1d32b9e9c90bce10b4301983d7dced88fddfcd8f49e9f294 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			56dc47f1ead79a66cfd6d66a293ced84a120f3b980cd5a12685a164938d8f3de ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-module-load-control-v13-live-v1)
		expected_boot_image=build/persistent-root-qmp-module-load-control-v13-generation34-20260812-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact QMP-UFS no-bind module-load discriminator; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 34 QMP-UFS no-bind module-load discriminator; exact Generation 33 Image, modules, and initramfs plus one-property PHY-disabled DTB and signed bundle; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6
		expected_initramfs=3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-module-load-control-v13
		expected_bundle=persistent-root-qmp-module-load-control-v13
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gcfd385a1c754
		expected_avb_salt=54fd12304ba20116f8324dcb8bf9a7852e6068a7365219a45c96686925e65cab
		expected_avb_digest=ad05a544cc54c3a4d125198ca0e247c5eed6687c9be5f594aeb4e18338c1c771
		expected_generation_record=409ac124585987942a64ee0693687ce209691d9c3d8ec4e9f72578398efe9c58
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			30fb6c355aa8e34097592cf4b33fe7ae4c4193a4c85ae36744c90778f1818cb7 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			d314b940d8dbecf63334a8f425719200852d25af364838db24f9e8aebecffadd ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-regulator-stage-v14-live-v1)
		expected_boot_image=build/persistent-root-qmp-regulator-stage-v14-generation35-20260812-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact SM8350 QMP-UFS clock-and-regulator-stage discriminator; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 35 SM8350 QMP-UFS clock-and-regulator-stage discriminator; patched module returns before MMIO parsing or provider creation; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6
		expected_initramfs=3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-regulator-stage-v14
		expected_bundle=persistent-root-qmp-regulator-stage-v14
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gcfd385a1c754
		expected_avb_salt=03beecfa691cbc239e8d93f64cc8f465fd5953b0882c3d0e11936fb30e01e99e
		expected_avb_digest=2a2e01c487ce2927c6cc72742fd1dd89f99861de1e5c464844d01bc0516cd7d9
		expected_generation_record=e237fcbddcc7a9f35cf314b5d73c056107963244b54322e6e5a8828e272c53da
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			03e49b58a082826c1d88ab328c82d6c903c9130e56522fb645eaa3be31eb69a7 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			734a7d0a3632df5f5d04d6faa2ecca82e72e4945daf5bd46db100e062d4e9d6e ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-mmio-stage-v15-live-v1)
		expected_boot_image=build/persistent-root-qmp-mmio-stage-v15-generation36-20260812-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact SM8350 QMP-UFS DT/MMIO-stage discriminator; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 36 SM8350 QMP-UFS DT/MMIO-stage discriminator; patched module returns before clock-provider registration or PHY/provider creation; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6
		expected_initramfs=3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-mmio-stage-v15
		expected_bundle=persistent-root-qmp-mmio-stage-v15
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gcfd385a1c754
		expected_avb_salt=1cd1ceb700ce259a77b74bc506f2f59d1d1b68f836d5fd57595172957788aca1
		expected_avb_digest=532668bb056d7be6e6d9d84f3a57605f5dbdc69587e3ea12f47c1a226e6496ac
		expected_generation_record=af33af01fa0c1429b49ab05925bf9fffa7e71acc723d922b26c67ce34ba097f6
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			d81ff27520337a91e556018109173d4d14d9c38d0846639f2d056150fa39886d ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			d5d5cdeb343b573527db94bc8d5fa909a267c0f87eec690f7b821d16438c483a ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-clock-provider-stage-v16-live-v1)
		expected_boot_image=build/persistent-root-qmp-clock-provider-stage-v16-generation37-20260812-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact SM8350 QMP-UFS clock-provider-stage discriminator; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 37 SM8350 QMP-UFS clock-provider-stage discriminator; patched module returns before PHY creation or provider registration; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6
		expected_initramfs=3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-clock-provider-stage-v16
		expected_bundle=persistent-root-qmp-clock-provider-stage-v16
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gcfd385a1c754
		expected_avb_salt=044ff81b93779ee76a2ca99f5152bb231ef52ddabbe3f013a7aba45fa7660c9f
		expected_avb_digest=005308d8b4c5779363caea95bdbb3fdeac11eee259554645b165d4e22e23a035
		expected_generation_record=731240f0e7c8da3b0c45fb84d4645de87166b92ab65158030011077b09ccce5b
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			dd832a7655e4a1130b69f07188907f80853004f5e05c150e827a0aee4e1c6447 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			bf223a9de39e0822493fa6769fcc4db94eada697eb1b12ae1a1a5197e88e0f8b ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-fixed-clocks-stage-v17-live-v1)
		expected_boot_image=build/persistent-root-qmp-fixed-clocks-stage-v17-generation38-20260812-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact SM8350 QMP-UFS fixed-rate-symbol-clocks discriminator; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 38 SM8350 QMP-UFS fixed-rate-symbol-clocks discriminator; patched module returns before OF clock-provider publication, PHY creation, or provider registration; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6
		expected_initramfs=3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-fixed-clocks-stage-v17
		expected_bundle=persistent-root-qmp-fixed-clocks-stage-v17
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gcfd385a1c754
		expected_avb_salt=da1dd4bb14df8827a8213c26cd714f12825d18c048e65f3089ded06d5e3e7d8b
		expected_avb_digest=2bb64ccc3b0bb62ba05b69c96b6b2da6a4a16cc489a4470cf70aeba07048a29b
		expected_generation_record=a769006b38c7234f9f6a55129e8523a0396261dffb9c70b388852a1018b6990d
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			abd615f73576c798505464c07a3816da470eee5eeb9c26bc2f8f201f85b44ba4 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			e5fe136dc95e7380b144d2f6bd64480e35464ae4523b17712aa695807e1b7f18 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-first-fixed-clock-stage-v18-live-v1)
		expected_boot_image=build/persistent-root-qmp-first-fixed-clock-stage-v18-generation39-20260813-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact SM8350 QMP-UFS first-fixed-clock discriminator; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 39 SM8350 QMP-UFS first-fixed-clock discriminator; patched module returns before the second clock, OF clock-provider publication, PHY creation, or provider registration; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6
		expected_initramfs=3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-first-fixed-clock-stage-v18
		expected_bundle=persistent-root-qmp-first-fixed-clock-stage-v18
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gcfd385a1c754
		expected_avb_salt=04cff56d428149c3c54b44580842730d7c6e8b85d8633c67b933e3ff5d7ee1c7
		expected_avb_digest=1475b6bd506abe5500b65a37ec39c7308cdd3ec7e4896f6008b30720f77d9234
		expected_generation_record=eed09e1837725e26416ff38365bcc5260bdc3fa2c4016cbdbfcfc3decdd41018
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			f047d1c0ca676afa62a8a4f30d7b68306622b2eee5fc8dfb8b94e9d71450d3c5 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			fbaee0cd105ba7d02e76ef5f1b13a4cb43bc0c4e03e14f0c9a0e9406c5513b7a ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-allocation-stage-v19-live-v1)
		expected_boot_image=build/persistent-root-qmp-allocation-stage-v19-generation40-20260813-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact SM8350 QMP-UFS allocation-stage discriminator; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 40 SM8350 QMP-UFS allocation-stage discriminator; patched module returns before the first clock, OF clock-provider publication, PHY creation, or provider registration; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6
		expected_initramfs=3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-allocation-stage-v19
		expected_bundle=persistent-root-qmp-allocation-stage-v19
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gcfd385a1c754
		expected_avb_salt=b4ffa58de47b1a48d2b877fa94865a9e95342c714264a48531c2d0a7e692a628
		expected_avb_digest=7633816778871f84ba86bbc7d72fe67bd9b57dcaf0f56e66518ade4bfac22dfc
		expected_generation_record=40000ccf9ad9e84736c3516eaff8cb2056da9568012fa355cb9256674cd0b382
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			82f38e524cc9f8c65bd5ae225bbb4d0acf4a7ef20021d61af313880c98731835 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			39051935dda192ac24983a91b0508eaa6f74788a77ce14a12f570ea2cad40280 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-first-clock-name-stage-v20-live-v1)
		expected_boot_image=build/persistent-root-qmp-first-clock-name-stage-v20-generation41-20260813-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact SM8350 QMP-UFS first-symbol-clock-name discriminator; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 41 SM8350 QMP-UFS first-symbol-clock-name discriminator; exact 4 MiB RMTFS/ramoops range is reserved; patched module returns after constructing rx_symbol_0 name but before the first clock registration, OF clock-provider publication, PHY creation, or provider registration; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6
		expected_initramfs=3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-first-clock-name-stage-v20
		expected_bundle=persistent-root-qmp-first-clock-name-stage-v20
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gcfd385a1c754
		expected_avb_salt=4053424276bc6675f1335d753c39680a43864c1fd80749806dfa0ad046f96756
		expected_avb_digest=93ec29b61e8e59afbc5088466e97c75b75a7fd7d97dbc2138db46b1fd9a10b7c
		expected_generation_record=e3ec64ce3a7df591fb9629dcc16e5250e5fa91ab00533a07d883b10cf1cd2444
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			86c8262c080b0b7254a9175bc8487f464db7a4304ba7879b450a74504a23f713 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			6f2a17b3d282a96fb491fc371b29f2fefc4ab274ffefa7904d97bd6dcacc98d4 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-third-clock-runtime-pm-stage-v23-live-v1)
		expected_boot_image=build/persistent-root-qmp-third-clock-runtime-pm-stage-v23-generation44-20260813-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact SM8350 QMP-UFS second-and-third fixed-rate clock discriminator with exact target-originated post-insmod proof; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 44 SM8350 QMP-UFS second-and-third fixed-rate clock discriminator; exact kernel release is embedded and exact target-originated post-insmod proof is required; exact 4 MiB RMTFS/ramoops range is reserved; CCF resumes all runtime-PM clock providers outside prepare_lock while orphan reparenting runs; patched QMP module returns after the third clock but before OF clock-provider publication, PHY creation, or provider registration; UFS core and host remain unloaded; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6
		expected_initramfs=3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-third-clock-runtime-pm-stage-v23
		expected_bundle=persistent-root-qmp-third-clock-runtime-pm-stage-v23
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gc732b0b41d8d
		expected_avb_salt=e9bf9a3b3723ea6d70365379f63533359eb780b880312b139fcdb3ac13428e44
		expected_avb_digest=039f3d74802391e894d2c6e24bd7e0eab40880e4abc26d3b834e75ab1a9ab713
		expected_generation_record=5bf1e8489b0fed50a091d950a2ec2d80b4684ff018e4a6d4a5ef36d2dd9fd55b
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			6d8195d2e384558b9ff79a42966fd6841837b38d4b41e83dd745bf554be14dc6 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			2a8c210db1b846df4886c7803d337a4edf4fe1787537d1582529196a82734fd9 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-power-usb-v8-generation84-live-v1)
		expected_boot_image=build/persistent-root-power-usb-v8-generation84-20260822-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact RAM-only verbatim direct-magic classifier after sealed BusyBox od compressed duplicate lines in Generation 83; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 84 verbatim direct-magic filesystem classifier; Generation 83 kernel, DTB, modules, firmware, local image, recovery, mount behavior, and rollback with only sealed BusyBox od duplicate-line compression disabled; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=b8c2a67a4bbf812235e2eccd06531d942c5f52c7f1cd0932ed2ff9187f324975
		expected_raw=09c497ef23718cf74c94f3dc11085575b46982232d9e690df48c52637e5d9616
		expected_initramfs=3dfd4ebb002e0ac3e4e1b6b1e874675297256297740f3e41be29bad89f276b20
		expected_control=9d4cc5a001b16c367a98ce5104bca28dfe29212ce47df6a08e0f5b11532a1093
		expected_fetcher=37fa1d0279b2c5c5eeee9f217e3ba5ccaf17bf1b1576cc689d6f0940a9c1ee50
		expected_verifier=c3c5c31831335867a79c5bcd5999ae67daa6c0f94d76df4522268a493512e3bb
		expected_target_id=persistent-root-power-usb-v8
		expected_bundle=persistent-root-power-usb-v8
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=7997d52541c01129c6914731b9632b9b22c8a5c0bd310a483ef1fc101a3a507c
		expected_avb_digest=5f0f0e1cc321c4c7409272b10a916ea5c0da458bac75db47360e0927128db50c
		expected_generation_record=be5b45a04ceb4408721e9ef0568df1915db09931c5895ca854cfd9edd7479c9c
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			c70ed13367192b26225aa3408bf8cdf4dd3a91da1d3a0c0f5fba59c81be36289 ]] ||
			fail 'persistent-root power/USB manifest is not pinned'
		[[ $expected_image == \
			88075dba4a8564fa21d73c69d696b64813dc024389a5d097be345f7cd9f302bb ]] ||
			fail 'persistent-root power/USB recovery image is not pinned'
		[[ $expected_trust == \
			cc1bca69dadbb0ae6f221a3ac5866d0edfebabd9bf96a9e0ef2747e8283f6054 ]] ||
			fail 'persistent-root power/USB trust key is not pinned'
		[[ $expected_host_verifier == \
			04f8544a26304af03a67c7588e68e2ff1a480cb500bda4fbf213db2cb650cb29 ]] ||
			fail 'persistent-root power/USB host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-early-ssh-v45-generation70-live-v1)
		expected_boot_image=build/persistent-root-local-image-early-ssh-v45-generation70-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact read-only local-image Arch repeat accepting one bounded startup-output stream only when it contains exactly one authenticated marker line before one runtime evidence command; same accepted v45 target bundle, four-module UFS, two ro,noload ext4 layers, persisted Generation 64 marker, early strict Ed25519 SSH, storage attestation, tmpfs OverlayFS, and rollback; RAM-only kernel/recovery; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 70 bounded-startup-output local-image successor; exact unchanged v45 signed target bundle and raw recovery, fresh deterministic AVB wrapper, one exact authenticated marker line amid at most 4096 startup-output bytes before one runtime evidence command; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-early-ssh-v45
		expected_bundle=persistent-root-local-image-early-ssh-v45
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=16a5bcc417b28d927996d6bbaeff33b405439f489307137a2944b55751aae787
		expected_avb_digest=fb5dc23cd31297fb4fb5546048b9f7d9a97d3fed4f1a4e8ac80d1fd7b289e794
		expected_generation_record=5b33f9e4dacf97b29faa1c3170058435903e7a652970aceb1c4c679ef885298a
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			f039b0a34a6ca3f2447b9499f4c4023fa894f5089e5f346dd852e0f132201949 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			0f8352ad767ffb77def5e2ac644af994c0df577c89f6051f87e1e8fb49b6635d ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-early-ssh-v45-live-v1)
		expected_boot_image=build/persistent-root-local-image-early-ssh-v45-generation67-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact read-only local-image Arch cycle starting strict Ed25519 SSH and unchanged storage attestation from sysinit.target before the general Arch basic-target transaction; same accepted four-module UFS, two ro,noload ext4 layers, persisted Generation 64 marker, tmpfs OverlayFS, and bounded rollback; RAM-only kernel/recovery; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 67 early-SSH local-image successor; exact accepted UFS/Image/DTB and two ro,noload ext4 layers, stock sshd masked only in volatile /run, strict custom Ed25519 SSH and unchanged storage attestation ordered before basic.target; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-early-ssh-v45
		expected_bundle=persistent-root-local-image-early-ssh-v45
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=93cb1f277ebe4b3d1eaf1517ba838a35558249cc3b78f55cd8c5e5ba0d6a12b7
		expected_avb_digest=92f0af76bcec47a44b048c55db22d8e2d6012c161a747633f0756c479e57898c
		expected_generation_record=5c6c01703f5d84dd95697c5d9e7318dedd40546fa3f530ca1220dc8193b6cdbd
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			f039b0a34a6ca3f2447b9499f4c4023fa894f5089e5f346dd852e0f132201949 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			0bd1b6b8fddc27a5b4860036a13406f5cf4897c0ae84761a835868c0db086953 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-ufs-detail-v44-live-v1)
		expected_boot_image=build/persistent-root-local-image-ufs-detail-v44-generation66-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 66 RAM-only cycle; exact four-module UFS, read-only userdata and 16 GiB local image, persisted Generation 64 marker, tmpfs OverlayFS, systemd, NCM, and strict key-only SSH passed in 328.363 seconds; normal reboot, exact Alpine fallback, and host cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 66 module-restored local-image Arch cycle; exact UFS, two ro,noload ext4 layers, persisted marker, volatile overlay, strict key-only SSH, normal reboot, and exact Alpine fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-ufs-detail-v44
		expected_bundle=persistent-root-local-image-ufs-detail-v44
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=f537b31e935551de1f80f047f6d35262c2c925bc02533b5e005d965ad6e8ce4d
		expected_avb_digest=b1ceb0949211677269294b9da6f710bbe331e9aa903b7c52b61059af18d4ea3e
		expected_generation_record=e9d3d2add267da9145e8efc713bc68e3fe2ffa2380274d62575c6dd3a19eb70a
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			07e7f72c7c88ea4c081d77e3e561c36278ef0a0273dee6b831ca691f6518ee2e ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			d4d95e010810e09a209f0cde8f82e3d36e28c20dfa1b5aa899b5873c1ee36412 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-post-write-v43-live-v1)
		expected_boot_image=build/persistent-root-local-image-post-write-v43-generation65-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 65 RAM-only cycle; the accepted read-only kernel booted but the sealed initramfs omitted all four deferred UFS modules, so UFS discovery timed out at ufs-ready before any storage node, mount, image, or write path; exact Alpine fallback, PS_HOLD/HARD_RESET lineage, and host cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 65 read-only cycle; the sealed initramfs omitted all four deferred UFS modules, so UFS discovery timed out before storage enumeration; exact Alpine fallback and host cleanup passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-post-write-v43
		expected_bundle=persistent-root-local-image-post-write-v43
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=0497e7a871cc43efff41494dc7591ee28e4dfec440beda78224232804591129c
		expected_avb_digest=8c93bfbd4089873a6a1f4a2de71c125f9bf6c6f31c4aff1889b192c6f9421c5e
		expected_generation_record=3f94c8b014d3aca25c29494fe8f55d7b256ff7ccf2a58e6d53bb743268001794
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			9a57ef7dab71d782bce1893525129e24bd350ee74f24aeabe4ed033af6500d07 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			80a4c775d973a2fc9d2159e48e87c21501339ce27a0226b35bbd7cd723e66fa1 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-write-mountpoint-v42-live-v1)
		expected_boot_image=build/persistent-root-local-image-write-mountpoint-v42-generation64-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 64 RAM-only cycle; the bounded write window, outer and inner ext4 RW mounts, exact marker write, relock, read-only remount, image mount, and root verification passed, then the aggregate UFS-health gate deliberately rolled back; the image remained clean and the exact marker persisted; exact Alpine fallback passed; never retry or flash'
		expected_boot_role='consumed Generation 64 contained-write cycle; exact marker persisted and the image remained clean, then the aggregate UFS-health gate deliberately rolled back; exact Alpine fallback passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-write-mountpoint-v42
		expected_bundle=persistent-root-local-image-write-mountpoint-v42
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_avb_salt=e53e4b09689e0a2258e6ff0f5c6087a8f669bc5d0c4b53235d7e3e9f153c5902
		expected_avb_digest=7348ccbac3447e0ff9a6452bfa320c9c9b9e52ddf268a05ef798eadcaca73a7d
		expected_generation_record=eeff887264c0ba40088b2d647947e97758fd4760594ebc3f0a19c55f4e0c44ca
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			8b2e95268be4e5e0c65eb9367514bb93ab2c20f38a3848a0986de4fe4336d221 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			9e7fa77363afd7afceceb772d4d4c4b7d7a651e38ea9c44354604c4334da818b ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-write-contained-v41-live-v1)
		expected_boot_image=build/persistent-root-local-image-write-contained-v41-generation63-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 63 RAM-only cycle; UFS, exact userdata, the contained partition-and-parent write window, outer userdata RW mount, and writable loop attachment passed, then the inner ext4 mount failed because the sealed initramfs never created /mnt/probe-root; no inner ext4 or UFS data write occurred; exact Alpine fallback and clean marker-free image postcheck passed; never retry or flash'
		expected_boot_role='consumed Generation 63 contained-write cycle; exact write window, outer userdata RW, and writable loop passed, then missing /mnt/probe-root prevented the inner ext4 mount before any inner-filesystem or UFS data write; exact Alpine fallback and clean marker-free image passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-write-contained-v41
		expected_bundle=persistent-root-local-image-write-contained-v41
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g359318de534f
		expected_avb_salt=1db67bc08d7b9685512178f3233c9ff47c50e30c2eb5f53b944a62c507625eb9
		expected_avb_digest=b70134efcd6bb79d78c09b5b362bf36a1e9d609b12d1a7c080cd827c25927c83
		expected_generation_record=a1f33c5a546a500dde19b800005ab306e468e99e5f03c46bd6fd3dd2ce441179
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			5125eddd0aeeb394eea7f24b427b04c1c001276c5b8b2e9dbf544a49c4af0646 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			159bf683100ad25aa9512a21ed2d24f91625b25597563eebe4d13bc42223b55a ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-write-roclass-v40-live-v1)
		expected_boot_image=build/persistent-root-local-image-write-roclass-v40-generation62-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 62 RAM-only cycle; both BLKROSET calls returned success but the selected parent remained effectively read-only, so no RW mount, loop, marker, or persistent write occurred; exact Alpine fallback and clean marker-free image postcheck passed; never retry or flash'
		expected_boot_role='consumed Generation 62 effective-readonly discriminator; parent disk remained effectively read-only after both BLKROSET calls; no RW mount, loop, marker, or persistent write; exact Alpine fallback and clean marker-free image passed; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-write-roclass-v40
		expected_bundle=persistent-root-local-image-write-roclass-v40
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=065c8bbf741c20313eb78464e922370fd1a2da1a6063925f8f1f3cfc4af8e4df
		expected_avb_digest=57d19cf69690e2e2ded485408ae7349b2d3c3aa09a091cd2569e9f3f59e29144
		expected_generation_record=7bebeb697cd04caa9336648fb2811cbf301e24521f38ff6bb5db7c2ae0cb5398
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			c284330d2e37cda85d125c098c6acece877ae5e5b69be66edcae326e57ee0f4b ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			1e19474e2536305f4845346d800e054959408a8ecd5e7dd0ba4cb43272a96ef8 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-write-window-v39-live-v1)
		expected_boot_image=build/persistent-root-local-image-write-window-v39-generation61-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 61 RAM-only cycle; UFS, exact userdata and image resolution, userdata unmount, read-only precheck, and both partition and parent-disk BLKROSET calls passed, then effective blockdev read-only-state verification failed before sysfs/count verification, any RW mount, loop attachment, marker, or persistent write; the image remained clean with mount count one and no marker ancestry; exact Alpine fallback and host cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 61 write-window discriminator; UFS, exact userdata and image, userdata unmount, read-only precheck, and both BLKROSET calls passed; effective blockdev read-only-state verification failed before any RW mount, loop, marker, or persistent write; image remained clean with mount count one and no marker ancestry; exact Alpine fallback and host cleanup passed; retain offline only; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-write-window-v39
		expected_bundle=persistent-root-local-image-write-window-v39
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=0f4c13f39636781d936c4b3b832c62294dfce2f84bea0f3311655c9798bb6500
		expected_avb_digest=47661db4eba88e4f49336156b7b08098d6d7e4a5c50c0d1a0b52d26f2e9a74f1
		expected_generation_record=d66774da20ae34e0b645b326d0b204ecabc35c002355b29f0dfe04675b0e51e5
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			35cdc621f44873e42b1b8f2619e383d1a6ed2236f49790fdf36c7435e7883824 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			8215928fc9c68414e90f50401238a4539b3f0f101c7834f3fce242b71ee3606d ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-write-diag-v38-live-v1)
		expected_boot_image=build/persistent-root-local-image-write-diag-v38-generation60-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 60 RAM-only cycle; exact UFS, userdata, and read-only image resolution passed, then image-write-window failed before outer userdata RW; the image remained clean with mount count one and no marker ancestry; exact PS_HOLD Alpine fallback and host cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 60 bounded-write discriminator; exact UFS, userdata, and read-only image resolution passed, then image-write-window failed before outer userdata RW; image remained clean with mount count one and no marker ancestry; exact PS_HOLD Alpine fallback and host cleanup passed; retain offline only; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-write-diag-v38
		expected_bundle=persistent-root-local-image-write-diag-v38
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=51a7c37619ca333a55ac8d79195dc356a981820f476c1a0d8c2348494d598bad
		expected_avb_digest=bc5b43c21d392b7ca29934915358fd1e0c4b1daf7c1f486570ae50ca442b2d2b
		expected_generation_record=391a94a0fd4009edfd6f5165f88a8337db2a6d724a94dfa542aa22d278dfbad5
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			a12844274c1bc707cee9ae1f3e464e73ffed57adcd477af8f21fbb678173c444 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			b4cbabb688f513db7939670fa1f6068065b6e6130c3418350c78421ee64ff18e ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-write-v37-live-v1)
		expected_boot_image=build/persistent-root-local-image-write-v37-generation59-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 59 RAM-only cycle; UFS, exact userdata, and the read-only image passed, but the bounded write path failed before the image filesystem was mounted read-write; no probe ancestry was created; exact Alpine fallback and host cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 59 bounded-write cycle; exact UFS, userdata, and read-only image resolution passed, terminal image-write failed before the image filesystem was mounted read-write, no marker ancestry exists, and exact Alpine fallback plus host cleanup passed; retain offline only; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-write-v37
		expected_bundle=persistent-root-local-image-write-v37
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=9189a8941f35c91242b0ca4a3544792a078916c854ca0b33506d7410a91df371
		expected_avb_digest=1b0894de77d910e3d9d9c4658c68ea71399993b8c447ca1a5a95fd35ddd7505f
		expected_generation_record=803f15dfbb71fb93182ce0b6e565e63c7471ee9bb6f30c16b5eaabcba2f2568a
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			5033263fbdb28f795fe92b74a850d3e33119f2d440f9e3999b3ebff3804ef259 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			b349d27e41ba2ad1bda9e06e681e3eb8faae9d1f8b32a13943476e63eb997578 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-ed25519-v36-live-v1)
		expected_boot_image=build/persistent-root-local-image-ed25519-v36-generation58-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 58 RAM-only cycle; exact read-only UFS, userdata and 16 GiB image, both ro,noload mounts, tmpfs OverlayFS, Ed25519-only volatile host-key generation, retained-loader attestation, and strict key-only SSH passed in 333.446 seconds; normal reboot, exact Alpine fallback, and host cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 58 Ed25519-only local-image cycle; exact UFS, userdata and 16 GiB image, two ro,noload ext4 mounts, tmpfs OverlayFS, exact per-boot Ed25519 host key in 28 ms, stock all-key generator masked in volatile runtime, retained musl-loader attestation, strict key-only SSH, systemd timing, normal reboot, and exact Alpine fallback passed in 333.446 seconds; retain offline only; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-ed25519-v36
		expected_bundle=persistent-root-local-image-ed25519-v36
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=c3f2b88d54e3a4260d28e69d7796643cc50e3df8b3c37c55690ac92acb5b553d
		expected_avb_digest=22328e06887d643547fa04153d868eb1ec78428210d4b637b6066c8a956d0de7
		expected_generation_record=1fa76a89ca2f0952be3a401ded4bc53bf0044c42b94577f4a8c74b7675d9390a
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			cc41176df74def7a8953dfcd8621e1d1ad2457eb98a7822a0d40ce50ab8c2be0 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			38bc065959a88f4f51f13cc3443a8bd02dda61d8813150821d561239bd02a4f0 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-volatile-v35-live-v1)
		expected_boot_image=build/persistent-root-local-image-volatile-v35-generation57-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact read-only SM8350 UFS local-image Arch boot with verified volatile systemd update markers, headless vconsole mask, retained-musl-loader attestation, systemd timing capture, strict key-only SSH, bounded rollback, and no phone-storage writes; RAM-only kernel/recovery; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 57 volatile-systemd local-image successor; unchanged UFS, userdata, 16 GiB image, two ro,noload ext4 mounts, tmpfs OverlayFS, exact linker cache, volatile update markers, headless vconsole mask, retained musl-loader attestation, key-only SSH, bounded rollback, and systemd timing capture; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-volatile-v35
		expected_bundle=persistent-root-local-image-volatile-v35
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=4c2e1b77db4f30ddf17689f6871ee0abebd51544c3e47271ba2bba33c581e690
		expected_avb_digest=01b82565207da961c4a4bf84fe472768e413562093d055e0bff2a72dc99f2508
		expected_generation_record=2872690a6163d6842249a778b5bbfc3c1257edfa30133980fdf8cf490a363e63
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			1def5f276c7d07668ccb90a9ca3ed966660e0af359e49e2f847371b058291e30 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			425346d1fa88586f20b61d333cbff28c6435e6b099e414d2fe2cf58dce6cc04f ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-loader-v34-repeat-live-v1)
		expected_boot_image=build/persistent-root-local-image-loader-v34-generation56-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 56 RAM-only cycle; exact read-only UFS, userdata and 16 GiB image, both ro,noload mounts, tmpfs OverlayFS, switch_root, systemd, retained-loader attestation, NCM, and strict key-only SSH passed in 362.241 seconds; systemd timing isolated ldconfig and vconsole delays; normal reboot, exact Alpine fallback, and host cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 56 read-only local-image repeat cycle; exact UFS, userdata and 16 GiB image, both ro,noload ext4 mounts, tmpfs OverlayFS, switch_root, systemd, retained-loader attestation, NCM, strict key-only SSH, and timing capture passed; normal reboot and exact Alpine fallback passed; retain offline only; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-loader-v34
		expected_bundle=persistent-root-local-image-loader-v34
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=b4b6808fe13829ac2af49e5901dae76c2ca9709e84420250c79a310d7420b18c
		expected_avb_digest=23a4e129803725693f4d90d1a95a8f37be106d637f90505f01bc52c6e6ac83f9
		expected_generation_record=2fead43348aab866f394ca2ca9fae013497ed359b2b0fb8bf16e32b61f625db4
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			8f2d0d8382a4bf8fd8a18669575af00ec0bfa717c8512db3b59771e4ddce1d79 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			b095064285f764c86e3818b392d12383e4fb9f839ec32b1ad7937172a0684546 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-loader-v34-live-v1)
		expected_boot_image=build/persistent-root-local-image-loader-v34-generation55-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 55 RAM-only cycle; exact read-only UFS, userdata and 16 GiB image, both ro,noload mounts, tmpfs OverlayFS, switch_root, systemd, retained-loader attestation, NCM, and strict key-only SSH passed in 344.676 seconds; normal reboot, exact Alpine fallback, and host cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 55 read-only local-image Arch cycle; exact UFS, userdata and 16 GiB image, both ro,noload ext4 mounts, tmpfs OverlayFS, switch_root, systemd, retained-loader attestation, NCM, and strict key-only SSH passed; normal reboot and exact Alpine fallback passed; retain offline only; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-loader-v34
		expected_bundle=persistent-root-local-image-loader-v34
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=9f018a2ccd39be1535084cb01f42c6036602c33f1ea392e9257b6f0708d021d7
		expected_avb_digest=eb411a0b837ac84193267a18ddcc92c3798a1e945d6c9e2d30217e1e2b332b81
		expected_generation_record=2cfd74db7da6f7aa9f782489ad87a83d04565186b1ddb817d24b0dcce3d674d9
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			8f2d0d8382a4bf8fd8a18669575af00ec0bfa717c8512db3b59771e4ddce1d79 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			c3cd5d584c959b8d78eab54e4b1547a6c24e06677d8c9a827275bc7cfc5b06da ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-fast-attest-v33-live-v1)
		expected_boot_image=build/persistent-root-local-image-fast-attest-v33-generation54-20260814-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 54 RAM-only cycle; read-only UFS, exact userdata and 16 GiB image, both ro,noload mounts, tmpfs OverlayFS, switch_root, systemd, NCM, and key-only SSH reached; post-handoff attestation failed because retained musl BusyBox was executed without its retained loader; exact Alpine fallback and host cleanup passed; never retry or flash'
		expected_boot_role='consumed Generation 54 read-only local-image Arch cycle; UFS, exact userdata and 16 GiB image, both ro,noload ext4 mounts, tmpfs OverlayFS, switch_root, systemd, NCM, and key-only SSH reached; retained musl BusyBox then failed with ENOENT because its loader was not invoked; exact Alpine fallback and host cleanup passed; retain offline only; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-fast-attest-v33
		expected_bundle=persistent-root-local-image-fast-attest-v33
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=684d593dda8f9e9202eafb0348c00d140d6ce48100b5b49f1f8d73b352223e64
		expected_avb_digest=e29c10a9c2f1485370c34313f4e68f9ffb10e9730298ced9a48a5dc93d95216a
		expected_generation_record=1b79288f0311e1d0b30ed09b05708f125ae3f6ac943ef0c9d54e66865ac8e3bf
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			40b5573a4d03f4571ead025083a7989e6ac9288a89b8fe64e4b8439b64aaa42e ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			0832ddd484ad00ed3bcda184f1b75ce688c89ead4c52a1f97e93f9a058b0b75a ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-local-image-v32-live-v1)
		expected_boot_image=build/persistent-root-local-image-v32-generation53-20260813-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='consumed by the sole Generation 53 RAM-only cycle; local-image Arch reached strict key-only SSH at target uptime 298.62 seconds with both ext4 layers ro,noload, tmpfs OverlayFS, clean UFS checks, normal systemd reboot, and exact Alpine fallback; host parser rejected only a stale root marker after success; never retry or flash'
		expected_boot_role='consumed Generation 53 read-only local-image Arch cycle; exact UFS lock, userdata and 16 GiB image identity, two ro,noload ext4 mounts, tmpfs OverlayFS, systemd, strict key-only SSH at target uptime 298.62 seconds, normal reboot, and exact Alpine fallback passed; retain offline only; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-local-image-v32
		expected_bundle=persistent-root-local-image-v32
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=608b5a5694b785d736739ce269d467cf6571575b3520d0e9dc85fd37db5dfe16
		expected_avb_digest=fd02fdb7862f6b08eb23a1718d9d42c55ff05ce26f4bd4a2c5d17945a52e2e00
		expected_generation_record=3c2ddab7539bb3830ca8ea8eb47c5f7e6ccec6fd8262ca6f145caf9ed020cc3f
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			ae1069eb2f85e1b93c24f831e440a54303ca80934864f7fca07afcf34adfaca1 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			fee441e423675610ee828d13e58db4d1c02b3751a024b3bbf1834257bca55d58 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-ufs-fast-admission-v31-live-v1)
		expected_boot_image=build/persistent-root-ufs-fast-admission-v31-generation52-20260813-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact read-only SM8350 UFS local-root boot with bounded boot-critical identity admission, runtime block locks, exact userdata ro,noload mount, tmpfs OverlayFS, systemd, key-only SSH, receive-only stage heartbeats, and bounded rollback; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 52 read-only local-root fast-admission successor; exact UFS lock and userdata identity, ro,noload outer mount, prior full seal plus exact boot-critical identity admission, tmpfs OverlayFS, systemd, key-only SSH, bounded rollback, receive-only stage heartbeats, and one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-ufs-fast-admission-v31
		expected_bundle=persistent-root-ufs-fast-admission-v31
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=ce6211048c1822c1ebc20988a1d5c88d531de48add1ed161c3353d96bd9b7645
		expected_avb_digest=c4d857e2f21769d2ecc2a483f2261302c34901a04e86229794492487b791888a
		expected_generation_record=0dd094c5119c4317e0057cba97418c43d994f760a7e983f273cf09f3c0f15a31
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			3cee4b788a2005e90b4c901955a3b1df392cad8b332ea7252580fe1621af1f89 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			0d0683e3404e890522630808700e6915eb86d83fd3d8ddc8fc5ed716a7e9303f ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-ufs-local-root-stage-v30-live-v1)
		expected_boot_image=build/persistent-root-ufs-local-root-stage-v30-generation51-20260813-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact read-only SM8350 UFS local-root stage-discrimination boot with bounded recovery transfer, runtime block locks, exact userdata ro,noload mount, sealed root verification, tmpfs OverlayFS, systemd, key-only SSH, and receive-only volatile stage heartbeats; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 51 read-only local-root stage discriminator; exact UFS lock and userdata identity, ro,noload outer mount, complete sealed-tree verification, tmpfs OverlayFS, systemd, key-only SSH, bounded rollback, receive-only volatile stage heartbeats, and one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-ufs-local-root-stage-v30
		expected_bundle=persistent-root-ufs-local-root-stage-v30
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=aa854eb8fbe8aea885c9b1360a7ec3b9d57a2e31af3b78c8733cc8e0449164fb
		expected_avb_digest=70c39f67b952e24a7cb4efb34e41ae58ae507d38ca936f974cbe40669e798bd2
		expected_generation_record=6c266ffda3bb2f18e308d74ef7a737b3ac1f1bd309abb93b478c365db4f46260
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			53afa65bb7134e7d5acccc2126aa8764fd3918c7cab02c61417f4be1572aad27 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			3fbcf296b054460a4a5a48092e55e4df080c6e308430177cf999d42ff6ef39cc ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-ufs-readonly-enumeration-v28-live-v1)
		expected_boot_image=build/persistent-root-ufs-readonly-enumeration-v28-generation49-20260813-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact read-only SM8350 UFS consumer enumeration with bounded recovery transfer, compile-time command guards, runtime block locks, and exact target proof before any mount; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 49 read-only SM8350 UFS consumer enumeration; exact four-module load order, compile-time UFS command guards, 116-node runtime read-only lock, zero block-backed mounts, exact target proof, bounded rollback, and one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-ufs-readonly-enumeration-v28
		expected_bundle=persistent-root-ufs-readonly-enumeration-v28
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=9901532ce6956506f5451b2f873873480f92d129fbf8b4f8d4867e8e73453c66
		expected_avb_digest=8275db0d58696cf176bf8cfc27f08bd4cafa7d97cf4ff6c9eaba865a56028cf6
		expected_generation_record=858e1ddf372c77e3180360127367cef4e8290048309a3792092b95b62414ad3e
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			9ea343f70b9dfa3658a13d4b1e4dfd2cb841881ec21ce0444cd4422899434045 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			7bd5cbae17f82d2496af0967534a53d8853f06d4eb6610a55641f7461e067399 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-ufs-phy-provider-stage-v27-live-v1)
		expected_boot_image=build/persistent-root-qmp-ufs-phy-provider-stage-v27-generation48-20260813-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact SM8350 QMP-UFS OF PHY-provider registration discriminator with bounded recovery transfer and exact target-originated post-insmod proof; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 48 SM8350 QMP-UFS OF PHY-provider registration discriminator with bounded recovery connect and host cleanup; exact kernel release is embedded and exact target-originated post-insmod proof is required; exact 4 MiB RMTFS/ramoops range is reserved; UFS core and host remain unloaded; patched QMP module sets PHY drvdata, publishes the exact OF PHY provider, and returns before any UFS consumer probes; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-ufs-phy-provider-stage-v27
		expected_bundle=persistent-root-qmp-ufs-phy-provider-stage-v27
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gae717d919f87
		expected_avb_salt=8f47880b469d9bfbdfadaecd3451b6aa91eeee6e6a3cbf201556153041efbc5b
		expected_avb_digest=bd72ee6a57a57eed2120541a3cd4c9e38a33a8b89745f0415c7c29ae4e653029
		expected_generation_record=540250e4bfa4178c26c25c13f8658a2cd5ff128ea0e6f79f12a741836adb86f8
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			734bd5af4c2f7db1af87e08d0a6c1de0e6d0b013be4901110b892fd065e7656c ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			2e0f347a48ac9cd11c3e73ed795b4a42a5f920ebe98a7177bfedba6491be52b8 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-ufs-phy-creation-stage-v26-live-v1)
		expected_boot_image=build/persistent-root-qmp-ufs-phy-creation-stage-v26-generation47-20260813-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact SM8350 QMP-UFS PHY creation discriminator with bounded recovery transfer and exact target-originated post-insmod proof; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 47 SM8350 QMP-UFS PHY creation discriminator with bounded recovery connect and host cleanup; exact kernel release is embedded and exact target-originated post-insmod proof is required; exact 4 MiB RMTFS/ramoops range is reserved; UFS core and host remain unloaded; patched QMP module returns after devm PHY creation and before drvdata or OF PHY-provider registration; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-ufs-phy-creation-stage-v26
		expected_bundle=persistent-root-qmp-ufs-phy-creation-stage-v26
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g3a0a28dcbbc3
		expected_avb_salt=36d070b134f6a9dddebadda90ee1029a8ead52dfec3378b3e4142175db616b0e
		expected_avb_digest=fcae27ac814be6f998ebf20c5c4c512071b81f33a0ce38f221bfd14c04df7455
		expected_generation_record=e9a1491a6eabace18b3d1812e8c7989f9ed1dac7fdd25058e3878ff372afbbc8
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			7f05c55c553e057b418f2adc23f284a907dd9ca693d532228372ad9dfe3e57c4 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			3443002bbb82c1880d347d891c469c138b1ef10f3c2f26470da53bf89128aeaf ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-clock-provider-cleanup-stage-v25-live-v1)
		expected_boot_image=build/persistent-root-qmp-clock-provider-cleanup-stage-v25-generation46-20260813-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact SM8350 QMP-UFS OF clock-provider publication and cleanup discriminator with bounded recovery transfer and exact target-originated post-insmod proof; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 46 SM8350 QMP-UFS OF clock-provider publication and paired devm cleanup discriminator with bounded recovery connect and host cleanup; exact kernel release is embedded and exact target-originated post-insmod proof is required; exact 4 MiB RMTFS/ramoops range is reserved; UFS core and host remain unloaded; patched QMP module returns before PHY creation and provider registration; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b
		expected_initramfs=14dd9901fc3d0385e126930633a9e58b5195bafc63388d3e7341d0c9eb851946
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=c8f1c5601432223e16566decb3e9a29b32f7ca89859126f11d99a29b17f9e4e3
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-clock-provider-cleanup-stage-v25
		expected_bundle=persistent-root-qmp-clock-provider-cleanup-stage-v25
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g07858678c59c
		expected_avb_salt=d8060f095f4f3534da9597429805c914b87c362c3f6e78f02e0b15555fc99598
		expected_avb_digest=89bf56544cef22085beed51c94862d3141ca7bbbb4a72ceb3be33d8eb94e4064
		expected_generation_record=68075a338135f52b92479c30fc1b38d49db6a3697ecee2298dd9e421682b5cc2
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			14f9b93e9951d664e036ef189526bef59a167572dd7a23c052ba56aed9fd44cf ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			d7088753846b5190c18123cea07c81fac82372f03dd677ba8cb4a997ffcb631d ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-clock-provider-cleanup-stage-v24-live-v1)
		expected_boot_image=build/persistent-root-qmp-clock-provider-cleanup-stage-v24-generation45-20260813-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact SM8350 QMP-UFS OF clock-provider publication and cleanup discriminator with exact target-originated post-insmod proof; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='consumed Generation 45 SM8350 QMP-UFS OF clock-provider publication discriminator; recovery PREPARE failed at FETCH_CONNECT before bundle transfer or mainline execution; exact Alpine fallback returned; no UFS enumeration or phone-storage access; never retry or flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6
		expected_initramfs=3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-clock-provider-cleanup-stage-v24
		expected_bundle=persistent-root-qmp-clock-provider-cleanup-stage-v24
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-g07858678c59c
		expected_avb_salt=52c215cb5e8a379cccf6a4ce04245302bb40edcb791efc768d84f624fd4e502b
		expected_avb_digest=5108fb7ddaa3162facaf071f13776c2a2f2b60aeaa0b66bc08b7d7f360e74a87
		expected_generation_record=d0ef34f8c1cdab3fa553a2a1a46efa64c7d0354c5ac8a868d682e3369c0dbc89
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			1bc07a9e0b0acf874f542a84f1d7d8c12505504790bc4da433eb22989b76839b ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			06fdc98669a72d02795c4fdeabb73875832a673b6d7d8190502ef5841682425f ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-second-clock-runtime-pm-stage-v22-live-v1)
		expected_boot_image=build/persistent-root-qmp-second-clock-runtime-pm-stage-v22-generation43-20260813-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact SM8350 QMP-UFS second fixed-rate clock registration with generic CCF runtime-PM correction; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 43 SM8350 QMP-UFS second fixed-rate clock discriminator; exact 4 MiB RMTFS/ramoops range is reserved; CCF resumes all runtime-PM clock providers outside prepare_lock while orphan reparenting runs; patched QMP module returns after the second clock registration but before the third clock, OF clock-provider publication, PHY creation, or provider registration; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6
		expected_initramfs=3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-second-clock-runtime-pm-stage-v22
		expected_bundle=persistent-root-qmp-second-clock-runtime-pm-stage-v22
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gad56d4021003
		expected_avb_salt=1a081108245ba02632a2dbdabd4f7ff75f811f4a13e2ee91b32b2c7b3ad36c2b
		expected_avb_digest=ecbfb6fddfea40e8c8af9b0d9e27d56467b3d7c1edcfacc6c43ef6e2a0bad959
		expected_generation_record=0b0832039db5d0fda9955fc99978b7fd197c2d481abaf09260eefef594060485
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			052d462cbd7820de331c446598f69224128eced8175665acd703428efb75b371 ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			505e2c0ec00f8b5582cb18e648674737667b7c8d7b9cc5638b6c89c34fad9ec0 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
		avbtool=$repo/artifacts/android-boot-tools-v1/avbtool.py
		unpack=$repo/artifacts/android-boot-tools-v1/unpack_bootimg.py
		qualified_cpio=$repo/scripts/host/qualified-cpio-path/cpio
		qualified_cpio_shim=$repo/scripts/host/qualified-tool-shims/cpio
		initramfs_path=$repo/scripts/host/qualified-cpio-path:$PATH
		requires_qualified_cpio=1
		;;
	persistent-root-qmp-first-clock-runtime-pm-stage-v21-live-v1)
		expected_boot_image=build/persistent-root-qmp-first-clock-runtime-pm-stage-v21-generation42-20260813-r1/repack/stable-recovery-a.avb.img
		expected_boot_basis='one exact SM8350 QMP-UFS first fixed-rate clock registration with generic CCF runtime-PM correction; RAM-only; externally consumed exact claim required; never flash or retry after entry'
		expected_boot_role='unbooted Generation 42 SM8350 QMP-UFS first fixed-rate clock discriminator; exact 4 MiB RMTFS/ramoops range is reserved; CCF resumes all runtime-PM clock providers outside prepare_lock while orphan reparenting runs; patched QMP module returns after the first clock registration but before the second and third clocks, OF clock-provider publication, PHY creation, or provider registration; one RAM-only use only; never flash'
		expected_boot_tracked=no
		component_layout=structured
		expected_kernel=71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455
		expected_raw=90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6
		expected_initramfs=3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d
		expected_control=59e76973965ef9b539d8e79c78e3c480cbeab49af314e44928846794672b3f31
		expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800
		expected_verifier=e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e
		expected_target_id=persistent-root-qmp-first-clock-runtime-pm-stage-v21
		expected_bundle=persistent-root-qmp-first-clock-runtime-pm-stage-v21
		expected_bundle_profile=persistent-root-ro-v1
		expected_target_release=7.1.4-gcdf38b1ddebb
		expected_avb_salt=815aeca872f300a6091ea117c42b167c293152aa1ee5ce15e19ebb30e1bb48f9
		expected_avb_digest=c88b04e8eef66be43f6e309961b8e321d04b94f3f9b42532228e960f6abbd0d2
		expected_generation_record=002232792948b1870a5ecea3ccc3633f3f6c75dcf883e0ccc015e47aa3838baa
		recovery_init=$repo/initramfs/recovery-init
		[[ $expected_manifest == \
			782756493f38d5ea9a634678043214926e9b49ef1ca01ce35e9e41e37169fd4b ]] ||
			fail 'persistent-root runtime manifest is not pinned'
		[[ $expected_image == \
			1b0ec7c7c9b9abb1cbf71c252292203869e853717f4a41cfbc3a03936b5597a1 ]] ||
			fail 'persistent-root recovery image is not pinned'
		[[ $expected_trust == \
			f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b ]] ||
			fail 'persistent-root trust key is not pinned'
		[[ $expected_host_verifier == \
			8e906bd5350d0c4a9a8685f14676ea0c610b9afbdff978562c3aeccab1414c96 ]] ||
			fail 'persistent-root host verifier is not pinned'
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
	headless-diagnostic-ssh-gadget-contract-v17-live-v1 | \
	headless-diagnostic-ssh-configfs-link-v18-live-v1 | \
	headless-diagnostic-ssh-iproute-whitespace-v19-live-v1 | \
	headless-diagnostic-ssh-fatal-token-boundary-v20-live-v1 | \
	headless-core-deployment-v1-live-v1 | \
	$POWER_USB_RECOVERY_PROFILE | \
	local-image-stage-v1-live-v1 | \
	persistent-root-qmp-ufs-phy-control-v12-live-v1 | \
	persistent-root-qmp-module-load-control-v13-live-v1 | \
	persistent-root-qmp-regulator-stage-v14-live-v1 | \
	persistent-root-qmp-mmio-stage-v15-live-v1 | \
	persistent-root-qmp-clock-provider-stage-v16-live-v1 | \
	persistent-root-qmp-fixed-clocks-stage-v17-live-v1 | \
	persistent-root-qmp-first-fixed-clock-stage-v18-live-v1 | \
	persistent-root-qmp-allocation-stage-v19-live-v1 | \
	persistent-root-qmp-first-clock-name-stage-v20-live-v1 | \
	persistent-root-qmp-first-clock-runtime-pm-stage-v21-live-v1 | \
	persistent-root-qmp-second-clock-runtime-pm-stage-v22-live-v1 | \
	persistent-root-qmp-third-clock-runtime-pm-stage-v23-live-v1 | \
	persistent-root-qmp-clock-provider-cleanup-stage-v24-live-v1 | \
	persistent-root-qmp-clock-provider-cleanup-stage-v25-live-v1 | \
	persistent-root-qmp-ufs-phy-creation-stage-v26-live-v1 | \
	persistent-root-qmp-ufs-phy-provider-stage-v27-live-v1 | \
	persistent-root-ufs-readonly-enumeration-v28-live-v1 | \
	persistent-root-local-image-any-prior-v14-generation107-live-v1 | \
	persistent-root-local-image-restart2-v15-generation108-live-v1 | \
	persistent-root-local-image-reboot-mode-v16-generation109-live-v1 | \
	persistent-root-sparse-diagnostic-v17-generation110-live-v1 | \
	local-image-stage-writer-v2-generation111-live-v1 | \
	local-image-stage-hotplug-v3-generation112-live-v1 | \
	local-image-stage-preusb-v4-generation113-live-v1 | \
	local-image-stage-usbmode-v5-generation114-live-v1 | \
	local-image-stage-configfs-v6-generation115-live-v1 | \
	local-image-stage-udc-v7-generation116-live-v1 | \
	local-image-stage-udc-stable-v8-generation117-live-v1 | \
	local-image-stage-ncm-v9-generation118-live-v1 | \
	local-image-stage-timing-v10-generation119-live-v1 | \
	local-image-stage-address-v11-generation120-live-v1 | \
	local-image-stage-prebind-v12-generation121-live-v1 | \
	local-image-stage-explicit-v13-generation122-live-v1 | \
	local-image-stage-configfs-udc-v14-generation123-live-v1 | \
	local-image-stage-two-sample-v15-generation124-live-v1 | \
	local-image-stage-bind-v16-generation125-live-v1 | \
	local-image-stage-direct-v17-generation126-live-v1 | \
	local-image-stage-bind-error-v18-generation127-live-v1 | \
	local-image-stage-hostfix-v19-generation128-live-v1 | \
	local-image-stage-postbind-v20-generation129-live-v1 | \
	local-image-stage-power-report-v21-generation130-live-v1 | \
	local-image-stage-listener-v22-generation131-live-v1 | \
	local-image-stage-abi-v23-generation132-live-v1 | \
	local-image-stage-ufs-count-v24-generation133-live-v1 | \
	local-image-stage-ufs-bind-v25-generation134-live-v1 | \
	local-image-stage-runtime-dt-v26-generation135-live-v1 | \
	local-image-stage-of-node-v27-generation136-live-v1 | \
	ufs-baseline-proven-v28-generation137-live-v1 | \
	ufs-reboot-baseline-v29-generation138-live-v1 | \
	ufs-power-reboot-baseline-v30-generation139-live-v1 | \
	ufs-glob-reboot-baseline-v31-generation140-live-v1 | \
	local-image-stage-glob-v32-generation141-live-v1 | \
	local-image-stage-ssh-v33-generation142-live-v1 | \
	local-image-stage-nm-v34-generation143-live-v1 | \
	local-image-stage-fast-v35-generation144-live-v1 | \
	local-image-stage-stages-v36-generation145-live-v1 | \
	local-image-stage-auth-v37-generation146-live-v1 | \
	local-image-stage-globfix-v38-generation147-live-v1 | \
	local-image-stage-rworder-v39-generation148-live-v1 | \
	local-image-stage-writekernel-v40-generation149-live-v1 | \
	local-image-write-benchmark-v41-generation150-live-v1 | \
	local-image-write-benchmark-v42-generation151-live-v1 | \
	local-image-write-benchmark-v43-generation152-live-v1 | \
	local-image-partial-inspect-v44-generation153-live-v1 | \
	local-image-write-benchmark-v45-generation154-live-v1 | \
	persistent-root-local-image-any-prior-v13-generation106-live-v1 | \
	persistent-root-local-image-any-prior-v12-generation105-live-v1 | \
	persistent-root-local-image-probe-writer-v11-generation104-live-v1 | \
	persistent-root-power-usb-v10-generation103-live-v1 | \
	persistent-root-power-usb-v9-generation102-live-v1 | \
	persistent-root-power-usb-v8-generation84-live-v1 | \
	persistent-root-local-image-early-ssh-v45-generation70-live-v1 | \
	persistent-root-local-image-early-ssh-v45-live-v1 | \
	persistent-root-local-image-ufs-detail-v44-live-v1 | \
	persistent-root-local-image-post-write-v43-live-v1 | \
	persistent-root-local-image-write-mountpoint-v42-live-v1 | \
	persistent-root-local-image-write-contained-v41-live-v1 | \
	persistent-root-local-image-write-roclass-v40-live-v1 | \
	persistent-root-local-image-write-window-v39-live-v1 | \
	persistent-root-local-image-write-diag-v38-live-v1 | \
	persistent-root-local-image-write-v37-live-v1 | \
	persistent-root-local-image-ed25519-v36-live-v1 | \
	persistent-root-local-image-volatile-v35-live-v1 | \
	persistent-root-local-image-loader-v34-repeat-live-v1 | \
	persistent-root-local-image-loader-v34-live-v1 | \
	persistent-root-local-image-fast-attest-v33-live-v1 | \
	persistent-root-local-image-v32-live-v1 | \
	persistent-root-ufs-fast-admission-v31-live-v1 | \
	persistent-root-ufs-local-root-stage-v30-live-v1 | \
	persistent-root-ufs-local-root-v29-live-v1 | \
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
grep -Fxq "target_release=$expected_target_release" <<<"$verified_plan"
grep -Fxq "target_timeout=$expected_target_timeout" <<<"$verified_plan"

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
for token in init=/init selinux=0 rog5linux.test=1 rog5.recovery_timeout=300; do
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
