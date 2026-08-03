#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
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
		headless-diagnostic-generation5-offline-v1) ;;
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
	headless-diagnostic-generation5-offline-v1)
		[[ $action == policy-preflight || $action == artifact-preflight ]] ||
			fail 'generation-5 diagnostic profile is offline-only and not boot-authorized'
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
	*) fail "unsupported stable-recovery live profile: $profile" ;;
esac
[[ -z $expected_bundle || $bundle == "$expected_bundle" ]] ||
	fail "profile requires bundle=$expected_bundle"
# expected_image is the caller-supplied RECOVERY_SHA256 and is never
# reassigned by profile selection.

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
	manifest_matches=$(awk -F '\t' -v name="$image_name" \
		'$1 == name { count++ } END { print count + 0 }' \
		"$artifact_manifest")
	[[ $manifest_matches == 1 ]] ||
		fail "artifact manifest does not uniquely list $image_name"
	manifest_identity=$(awk -F '\t' -v name="$image_name" \
		'$1 == name { print $2 "\t" $3; exit }' "$artifact_manifest")
	[[ $manifest_identity == $'100663296\t'"$expected_image" ]] ||
		fail 'temporary boot artifact manifest identity is not allowlisted'
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
