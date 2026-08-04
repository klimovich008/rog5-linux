#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
gate=$repo/scripts/host/run-stable-recovery-live-gate.sh
lifecycle=$repo/scripts/host/run-minimal-headless-live-cycle.py
lifecycle_test=$repo/scripts/host/test-run-minimal-headless-live-cycle.py
boot_policy=$repo/manifests/temporary-boot-images.tsv
artifact_manifest=$repo/manifests/artifacts.tsv
tmp=$(mktemp -d)
build_tmp=
cleanup() {
	if [[ -n $build_tmp && -d $build_tmp ]]; then
		chmod -R u+rwX "$build_tmp" 2>/dev/null || true
		rm -rf -- "$build_tmp"
	fi
	rm -rf -- "$tmp"
}
trap cleanup EXIT HUP INT TERM

diagnostic_image=build/early-target-diagnostic-deployment-20260801-production/wrapper/repack/stable-recovery-a.avb.img
corrected_diagnostic_image=build/early-target-diagnostic-deployment-20260801-fetch-policy-r2-production/wrapper/repack/stable-recovery-a.avb.img
listener_successor_image=build/early-target-diagnostic-deployment-20260802-listener-r3-production/wrapper/repack/stable-recovery-a.avb.img
nfs_gated_successor_image=build/early-target-diagnostic-deployment-20260802-nfs-gated-r4-production/wrapper/repack/stable-recovery-a.avb.img
generation3_image=build/early-target-diagnostic-deployment-20260802-fresh-fetch-r5-production/wrapper/repack/stable-recovery-a.avb.img
generation3_root=$repo/build/early-target-diagnostic-deployment-20260802-fresh-fetch-r5-production
generation4_image=build/stable-recovery-generation4-timeout-lattice-20260803-a/repack/stable-recovery-a.avb.img
generation4_root=$repo/build/stable-recovery-generation4-timeout-lattice-20260803-a
generation5_image=build/stable-recovery-generation5-choreography-20260803-a/repack/stable-recovery-a.avb.img
generation5_root=$repo/build/stable-recovery-generation5-choreography-20260803-a
generation6_image=build/stable-recovery-generation6-signal-fix-20260803-a/repack/stable-recovery-a.avb.img
generation6_root=$repo/build/stable-recovery-generation6-signal-fix-20260803-a
generation7_image=build/stable-recovery-generation7-deferred-profile-fix-20260803-a/repack/stable-recovery-a.avb.img
generation7_root_a=$repo/build/stable-recovery-generation7-deferred-profile-fix-20260803-a
generation7_root_b=$repo/build/stable-recovery-generation7-deferred-profile-fix-20260803-b
generation8_image=build/stable-recovery-generation8-nmcli-empty-field-fix-20260803-a/repack/stable-recovery-a.avb.img
generation8_root_a=$repo/build/stable-recovery-generation8-nmcli-empty-field-fix-20260803-a
generation8_root_b=$repo/build/stable-recovery-generation8-nmcli-empty-field-fix-20260803-b
generation9_image=build/stable-recovery-generation9-acm-classifier-20260803-a/repack/stable-recovery-a.avb.img
generation9_root_a=$repo/build/stable-recovery-generation9-acm-classifier-20260803-a
generation9_root_b=$repo/build/stable-recovery-generation9-acm-classifier-20260803-b
generation10_image=build/stable-recovery-generation10-prepare-progress-20260803-a/repack/stable-recovery-a.avb.img
generation10_root_a=$repo/build/stable-recovery-generation10-prepare-progress-20260803-a
generation10_root_b=$repo/build/stable-recovery-generation10-prepare-progress-20260803-b
generation10_base=$repo/build/prepare-progress-generation10-production-base-20260803
[[ $(grep -Fxc \
	'DIAGNOSTIC_RECOVERY_PROFILE = "headless-diagnostic-generation10-live-v1"' \
	"$lifecycle") == 1 ]] ||
	{ echo 'FAIL lifecycle does not select exact generation-10 live profile' >&2; exit 1; }
[[ $(grep -Fxc \
	'DIAGNOSTIC_RECOVERY_PROFILE = "headless-diagnostic-generation10-live-v1"' \
	"$lifecycle_test") == 1 ]] ||
	{ echo 'FAIL lifecycle test does not pin exact generation-10 live profile' >&2; exit 1; }
! grep -Fq 'headless-diagnostic-generation9-' "$lifecycle" ||
	{ echo 'FAIL consumed generation-9 profile remains in the lifecycle' >&2; exit 1; }
! grep -Fq 'headless-diagnostic-generation9-' "$lifecycle_test" ||
	{ echo 'FAIL consumed generation-9 profile remains in the lifecycle test' >&2; exit 1; }
! grep -Fq 'headless-diagnostic-generation10-offline-v1' "$lifecycle" ||
	{ echo 'FAIL generation-10 offline-only profile leaked into the lifecycle' >&2; exit 1; }
! grep -Fq 'headless-diagnostic-generation10-offline-v1' "$lifecycle_test" ||
	{ echo 'FAIL generation-10 offline-only profile leaked into the lifecycle test' >&2; exit 1; }
[[ $(awk -F '\t' '$2 == "allow" { count++ } END { print count + 0 }' \
	"$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed policy retains a temporary-boot allow row' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$diagnostic_image" \
	'$1 == name { count++ } END { print count + 0 }' "$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed diagnostic wrapper remains boot-allowlisted' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$diagnostic_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "9c060a27f21f6f99ca0c00cd1ff2ed9532220d585cd726b194f8b6d04e6204ef" \
	&& $4 ~ /^consumed production-signed temporary recovery/ \
	{ count++ } END { print count + 0 }' "$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL diagnostic wrapper artifact identity is not exact' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$corrected_diagnostic_image" \
	'$1 == name { count++ } END { print count + 0 }' "$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed corrected wrapper remains boot-allowlisted' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$corrected_diagnostic_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "f710bbcd1f9602f0fdc3ce7023298f66cc5e7a014a0627c4f9123d7cc897b0ef" \
	&& $4 ~ /^consumed production-signed fetch-policy-corrected diagnostic recovery/ \
	{ count++ } END { print count + 0 }' "$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL corrected diagnostic wrapper artifact identity is not exact' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$listener_successor_image" \
	'$1 == name { count++ } END { print count + 0 }' \
	"$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed listener successor remains boot-allowlisted' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$listener_successor_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "332889a83f541ed0e17c94656836c512a35b5bfd6bbbaf735d2f5f6b94b51830" \
	&& $4 ~ /^consumed generation-1 AVB wrapper/ \
	{ count++ } END { print count + 0 }' "$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL listener successor artifact identity is not exact' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$nfs_gated_successor_image" \
	'$1 == name { count++ } END { print count + 0 }' \
	"$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed NFS-gated successor remains boot-allowlisted' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$nfs_gated_successor_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1" \
	&& $4 ~ /^consumed generation-2 AVB wrapper/ \
	{ count++ } END { print count + 0 }' "$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL NFS-gated successor artifact identity is not exact' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation3_image" \
	'$1 == name { count++ } END { print count + 0 }' \
	"$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed generation-3 recovery remains boot-allowlisted' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation3_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6" \
	&& $4 ~ /^consumed generation-3 fresh-fetch diagnostic recovery/ \
	{ count++ } END { print count + 0 }' "$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL generation-3 consumed artifact identity is not exact' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation4_image" \
	'$1 == name { count++ } END { print count + 0 }' \
	"$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed generation-4 recovery remains boot-allowlisted' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation4_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d" \
	&& $4 ~ /^consumed generation-4 timeout-lattice diagnostic recovery/ \
	&& $4 ~ /45-second NFS readiness deadline expired/ \
	&& $4 ~ /COMMIT was never sent and no target ran/ \
	&& $4 ~ /retain offline only; never retry or flash$/ \
	{ count++ } END { print count + 0 }' "$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL generation-4 consumed artifact identity is not exact' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation5_image" \
	'$1 == name { count++ } END { print count + 0 }' \
	"$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed generation-5 recovery remains boot-allowlisted' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation5_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a" \
	&& $4 ~ /^consumed generation-5 host-choreography diagnostic recovery/ \
	&& $4 ~ /complete 46163787-byte bundle transfer/ \
	&& $4 ~ /NFSv4\.2 readiness gate failed before COMMIT/ \
	&& $4 ~ /execution_started remained NO and no target ran/ \
	&& $4 ~ /retain offline only; never retry or flash$/ \
	{ count++ } END { print count + 0 }' "$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL generation-5 consumed artifact identity is not exact' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation6_image" \
	'$1 == name { count++ } END { print count + 0 }' \
	"$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed generation-6 recovery remains boot-allowlisted' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation6_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398" \
	&& $4 == "consumed generation-6 signal-mask-corrected host diagnostic recovery; one RAM-only recovery boot reached verified recovery ACM/NCM and completed the 46163787-byte signed-bundle transfer; recovery control produced no output and no PREPARED record; independently, the diagnostic collector reached its fixed 120-second ACM deadline with zero target frames; no COMMIT intent existed and no target ran; anchored Alpine restoration and strict SSH fallback passed; automated final host cleanup verification failed because production udev ID_MODEL=ROG_Phone_5_Linux_Server does not match the verifier-required ROG5_ prefix, while independent read-only residue checks passed; retain offline only; never retry or flash" \
	&& $5 == "no" { count++ } END { print count + 0 }' \
	"$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL generation-6 consumed artifact identity is not exact' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation7_image" \
	'$1 == name { count++ } END { print count + 0 }' \
	"$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed generation-7 recovery remains boot-allowlisted' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation7_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901" \
	&& $4 == "consumed generation-7 deferred-profile-corrected host diagnostic recovery; one RAM-only recovery boot reached verified recovery ACM/NCM and completed the 46163787-byte signed-bundle transfer; recovery control produced no output and no PREPARED record; independently, the diagnostic collector rejected after its fixed 120-second ACM-stability deadline with zero target frames; no COMMIT intent existed and no target ran; anchored Alpine profile restoration and strict SSH fallback passed; final host cleanup proof failed because the deferred interface exposed an unexpected NetworkManager association and the post-fallback continuous clean dwell did not complete before its deadline, while independent read-only residue checks were clean; retain offline only; never retry or flash" \
	&& $5 == "no" { count++ } END { print count + 0 }' \
	"$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL generation-7 consumed artifact identity is not exact' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation8_image" \
	'$1 == name { count++ } END { print count + 0 }' "$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed generation-8 recovery remains boot-allowlisted' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation8_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415" && \
	$4 == "consumed generation-8 NetworkManager-empty-field-corrected host diagnostic recovery; one RAM-only recovery boot reached verified recovery ACM/NCM and completed the 46163787-byte signed-bundle transfer; recovery returned no PREPARED record and the terminal identity-stability rejection did not label whether it sampled initial recovery or replay discovery after transport loss; Generation-9 timing makes replay of watchdog fallback plausible but does not retroactively prove that phase; independently, the diagnostic collector rejected after its fixed ACM-stability deadline with zero target frames; no COMMIT intent existed and no target ran; exact Alpine fallback returned after the pre-commit failure; final host cleanup proof failed because the lifecycle could not inspect the empty root-owned mode-0600 NFS export table; independent read-only checks found no NFS listener, service, kernel threads, export mount, or lifecycle marker; retain offline only; never retry or flash" && \
	$5 == "no" { count++ } END { print count + 0 }' \
	"$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL generation-8 consumed artifact identity is not exact' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation9_image" \
	'$1 == name { count++ } END { print count + 0 }' "$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed generation-9 recovery remains boot-allowlisted' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation9_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008" && \
	$4 == "consumed generation-9 recovery-ACM-classifier diagnostic wrapper; one RAM-only recovery boot reached verified recovery ACM/NCM and completed the 46163787-byte signed-bundle transfer after PREPARE; recovery returned no PREPARED response and recovery USB disconnected about 178 seconds after enumeration; the terminal classifier reported product-mismatch in all 216 samples, one transition, no identity-field changes, and no truncation, but did not label the discovery phase; the complete transfer and USB timeline support replay discovery of Alpine after transport loss as the best interpretation, not direct phase evidence; recovery rejected before COMMIT, the diagnostic collector rejected at its ACM-stability preflight with zero frames and zero dropped USB events, no COMMIT intent existed, and no target ran; exact Alpine fallback returned and final host cleanup proof passed; retain offline only; never retry or flash" && \
	$5 == "no" { count++ } END { print count + 0 }' \
	"$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL generation-9 consumed artifact identity is not exact' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation10_image" \
	'$1 == name { count++ } END { print count + 0 }' "$boot_policy") == 0 ]] ||
	{ echo 'FAIL unbooted generation-10 recovery is boot-allowlisted' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation10_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51" && \
	$4 == "unbooted generation-10 PREPARE-progress-instrumented diagnostic recovery; production-key-bound twin wrapper build and two deterministic issuer invocations pass; immutable offline profile and separate live lifecycle profile; authority=none; no phone contact, temporary-boot admission, or boot claim; retain offline until separately admitted; never flash" && \
	$5 == "no" { count++ } END { print count + 0 }' \
	"$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL generation-10 unadmitted live-profile artifact identity is not exact' >&2; exit 1; }

if env -i PATH="$PATH" HOME="$HOME" bash "$gate" boot \
	>"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL unguarded stable-recovery boot passed' >&2
	exit 1
fi
grep -Fq 'ALLOW_TEMPORARY_BOOT=1' "$tmp/err"
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL unguarded boot reached host inspection' >&2
	exit 1
fi

if env -i PATH="$PATH" HOME="$HOME" bash "$gate" artifact-preflight \
	>"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL stable-recovery profile defaulted implicitly' >&2
	exit 1
fi
grep -Fq 'set ROG5_STABLE_RECOVERY_PROFILE explicitly' "$tmp/err"
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL absent profile reached host inspection' >&2
	exit 1
fi

if env -i PATH="$PATH" HOME="$HOME" \
	ROG5_STABLE_RECOVERY_PROFILE=historical-2026-07-29 \
	bash "$gate" policy-preflight >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL policy preflight accepted a profile without complete pins' >&2
	exit 1
fi
grep -Fq 'policy preflight requires a fully pinned diagnostic profile' \
	"$tmp/err"

if env -i PATH="$PATH" HOME="$HOME" \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_HEADLESS_LIVE_GATE=1 \
	ROG5_STABLE_RECOVERY_PROFILE=headless-ssh-deployment-v3 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-ssh-network-root-v3-r2 \
	RECOVERY_SHA256=11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=457273993a9ce3cb0a9c735ef29e96101c1303720cafefc774aed12972a6926e \
	HOST_VERIFIER_SHA256=9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b \
	bash "$gate" boot >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL consumed deployment manifest reached boot admission' >&2
	exit 1
fi
grep -Fq 'refusing a consumed deployment manifest' "$tmp/err"

if env -i PATH="$PATH" HOME="$HOME" \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_HEADLESS_LIVE_GATE=1 \
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-deployment-v1 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-netroot-early-diag-v1 \
	RECOVERY_SHA256=9c060a27f21f6f99ca0c00cd1ff2ed9532220d585cd726b194f8b6d04e6204ef \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	bash "$gate" boot >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL consumed diagnostic recovery reached boot admission' >&2
	exit 1
fi
grep -Fq 'refusing the consumed diagnostic recovery image' "$tmp/err"
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL consumed diagnostic recovery reached host inspection' >&2
	exit 1
fi

if env -i PATH="$PATH" HOME="$HOME" \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_HEADLESS_LIVE_GATE=1 \
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-deployment-v1 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-netroot-early-diag-v1 \
	RECOVERY_SHA256=70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1 \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	bash "$gate" boot >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL consumed generation-2 recovery reached boot admission' >&2
	exit 1
fi
grep -Fq 'refusing the consumed generation-2 diagnostic recovery image' \
	"$tmp/err"

if env -i PATH="$PATH" HOME="$HOME" \
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-deployment-v1 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-netroot-early-diag-v1 \
	RECOVERY_SHA256=70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1 \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	bash "$gate" preflight >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL historical diagnostic profile reached connected preflight' >&2
	exit 1
fi
grep -Fq 'historical diagnostic profile is offline-only and consumed' \
	"$tmp/err"
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL historical diagnostic preflight reached host inspection' >&2
	exit 1
fi

if env -i PATH="$PATH" HOME="$HOME" \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_HEADLESS_LIVE_GATE=1 \
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation3-offline-v1 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-netroot-early-diag-v1 \
	RECOVERY_SHA256=eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6 \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	bash "$gate" boot >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL offline generation-3 profile reached boot admission' >&2
	exit 1
fi
grep -Fq 'generation-3 diagnostic profile is offline-only and not boot-authorized' \
	"$tmp/err"
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL offline generation-3 boot reached host inspection' >&2
	exit 1
fi

if env -i PATH="$PATH" HOME="$HOME" \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_HEADLESS_LIVE_GATE=1 \
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation4-offline-v1 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-netroot-early-diag-v1 \
	RECOVERY_SHA256=220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	bash "$gate" boot >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL offline generation-4 profile reached boot admission' >&2
	exit 1
fi
grep -Fq 'generation-4 diagnostic profile is offline-only and not boot-authorized' \
	"$tmp/err"
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL offline generation-4 boot reached host inspection' >&2
	exit 1
fi

if env -i PATH="$PATH" HOME="$HOME" \
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation4-offline-v1 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-netroot-early-diag-v1 \
	RECOVERY_SHA256=220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	bash "$gate" preflight >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL offline generation-4 profile reached connected preflight' >&2
	exit 1
fi
grep -Fq 'generation-4 diagnostic profile is offline-only and not boot-authorized' \
	"$tmp/err"
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL offline generation-4 preflight reached host inspection' >&2
	exit 1
fi

for generation5_action in boot preflight; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation5-offline-v1 \
		LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
		RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
		TRUST_KEY="$repo/build/unused-trust-key" \
		BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" "$generation5_action" >"$tmp/out" 2>"$tmp/err"
	then
		echo "FAIL offline generation-5 profile reached $generation5_action" >&2
		exit 1
	fi
	grep -Fq 'generation-5 diagnostic profile is offline-only and not boot-authorized' \
		"$tmp/err"
	if grep -Fq 'missing live-gate command' "$tmp/err"; then
		echo "FAIL offline generation-5 $generation5_action reached host inspection" >&2
		exit 1
	fi
done

for generation6_action in boot preflight; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation6-offline-v1 \
		LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
		RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
		TRUST_KEY="$repo/build/unused-trust-key" \
		BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" "$generation6_action" >"$tmp/out" 2>"$tmp/err"
	then
		echo "FAIL offline generation-6 profile reached $generation6_action" >&2
		exit 1
	fi
	grep -Fq 'generation-6 diagnostic profile is offline-only and not boot-authorized' \
		"$tmp/err"
	if grep -Fq 'missing live-gate command' "$tmp/err"; then
		echo "FAIL offline generation-6 $generation6_action reached host inspection" >&2
		exit 1
	fi
done

for generation7_action in boot preflight; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation7-offline-v1 \
		LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
		RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
		TRUST_KEY="$repo/build/unused-trust-key" \
		BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" "$generation7_action" >"$tmp/out" 2>"$tmp/err"
	then
		echo "FAIL offline generation-7 profile reached $generation7_action" >&2
		exit 1
	fi
	grep -Fq 'generation-7 diagnostic profile is offline-only and not boot-authorized' \
		"$tmp/err"
	if grep -Fq 'missing live-gate command' "$tmp/err"; then
		echo "FAIL offline generation-7 $generation7_action reached host inspection" >&2
		exit 1
	fi
done

for generation8_action in boot preflight; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation8-offline-v1 \
		LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
		RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
		TRUST_KEY="$repo/build/unused-trust-key" \
		BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" "$generation8_action" >"$tmp/out" 2>"$tmp/err"
	then
		echo "FAIL offline generation-8 profile reached $generation8_action" >&2
		exit 1
	fi
	grep -Fq 'generation-8 diagnostic profile is offline-only and not boot-authorized' \
		"$tmp/err"
	if grep -Fq 'missing live-gate command' "$tmp/err"; then
		echo "FAIL offline generation-8 $generation8_action reached host inspection" >&2
		exit 1
	fi
done

for generation9_action in boot preflight; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation9-offline-v1 \
		LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
		RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
		TRUST_KEY="$repo/build/unused-trust-key" \
		BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" "$generation9_action" >"$tmp/out" 2>"$tmp/err"
	then
		echo "FAIL offline generation-9 profile reached $generation9_action" >&2
		exit 1
	fi
	grep -Fq 'generation-9 diagnostic profile is offline-only and not boot-authorized' \
		"$tmp/err"
	if grep -Fq 'missing live-gate command' "$tmp/err"; then
		echo "FAIL offline generation-9 $generation9_action reached host inspection" >&2
		exit 1
	fi
done

for generation10_action in boot preflight; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation10-offline-v1 \
		LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
		RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
		TRUST_KEY="$repo/build/unused-trust-key" \
		BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" "$generation10_action" >"$tmp/out" 2>"$tmp/err"
	then
		echo "FAIL offline generation-10 profile reached $generation10_action" >&2
		exit 1
	fi
	grep -Fq 'generation-10 diagnostic profile is offline-only and not boot-authorized' \
		"$tmp/err" ||
		{ echo "FAIL offline generation-10 $generation10_action returned the wrong rejection" >&2; exit 1; }
	if grep -Fq 'missing live-gate command' "$tmp/err"; then
		echo "FAIL offline generation-10 $generation10_action reached host inspection" >&2
		exit 1
	fi
done

for generation10_connected_action in boot preflight; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation10-live-v1 \
		LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
		RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
		TRUST_KEY="$repo/build/unused-trust-key" \
		BUNDLE_ROOT="$repo/build/unused-bundle-root" \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" "$generation10_connected_action" >"$tmp/out" 2>"$tmp/err"
	then
		echo "FAIL generation-10 live profile reached direct $generation10_connected_action" >&2
		exit 1
	fi
	grep -Fq \
		'generation-10 connected action requires the one-shot lifecycle controller' \
		"$tmp/err" ||
		{ echo "FAIL generation-10 direct $generation10_connected_action returned the wrong rejection" >&2; exit 1; }
	if grep -Fq 'missing live-gate command' "$tmp/err"; then
		echo "FAIL generation-10 direct $generation10_connected_action reached host inspection" >&2
		exit 1
	fi
done

generation10_boot_basis='one generation-10 PREPARE-progress-instrumented diagnostic lifecycle after connected preflight; remove after any result; never flash'
for generation10_policy_shape in missing duplicate wrong-basis; do
	policy_fixture=$tmp/generation10-policy-$generation10_policy_shape
	install -d -m 0755 "$policy_fixture/scripts/host" \
		"$policy_fixture/manifests"
	install -m 0755 "$gate" \
		"$policy_fixture/scripts/host/run-stable-recovery-live-gate.sh"
	cp -- "$artifact_manifest" "$policy_fixture/manifests/artifacts.tsv"
	cp -- "$boot_policy" \
		"$policy_fixture/manifests/temporary-boot-images.tsv"
	case $generation10_policy_shape in
		missing) ;;
		duplicate)
			printf '%s\tallow\t%s\n' "$generation10_image" \
				"$generation10_boot_basis" \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			printf '%s\tallow\t%s\n' "$generation10_image" \
				"$generation10_boot_basis" \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		wrong-basis)
			printf '%s\tallow\t%s\n' "$generation10_image" \
				'wrong generation-10 basis; never boot' \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
	esac
	for generation10_connected_action in boot preflight; do
		if env -i PATH="$PATH" HOME="$HOME" \
			ALLOW_TEMPORARY_BOOT=1 \
			ALLOW_HEADLESS_LIVE_GATE=1 \
			ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
			ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation10-live-v1 \
			LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
			RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
			TRUST_KEY="$repo/build/unused-trust-key" \
			BUNDLE_ROOT="$repo/build/unused-bundle-root" \
			BUNDLE=headless-netroot-early-diag-v1 \
			RECOVERY_SHA256=b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51 \
			TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
			MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
			HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
			bash "$policy_fixture/scripts/host/run-stable-recovery-live-gate.sh" \
			"$generation10_connected_action" >"$tmp/out" 2>"$tmp/err"
		then
			echo "FAIL generation-10 $generation10_policy_shape policy reached $generation10_connected_action" >&2
			exit 1
		fi
		if [[ $generation10_policy_shape == wrong-basis ]]; then
			expected_policy_error="temporary boot policy basis does not match $generation10_image"
		else
			expected_policy_error="temporary boot policy does not uniquely list $generation10_image"
		fi
		grep -Fq "$expected_policy_error" "$tmp/err" ||
			{ echo "FAIL generation-10 $generation10_policy_shape returned the wrong policy rejection" >&2; exit 1; }
		if grep -Fq 'missing live-gate command' "$tmp/err"; then
			echo "FAIL generation-10 $generation10_policy_shape policy reached host inspection" >&2
			exit 1
		fi
	done
done

! grep -Eq \
	'headless-diagnostic-generation(1[1-9]|[2-9][0-9]|[1-9][0-9]{2,})-' \
	"$gate" ||
	{ echo 'FAIL an unreviewed future diagnostic generation is supported' >&2; exit 1; }

generation10_case=$(awk '
	index($0, "\theadless-diagnostic-generation10-offline-v1") == 1 { capture = 1 }
	capture { print }
	capture && /^[[:space:]]*;;$/ { exit }
' "$gate")
generation10_case_unindented=$(sed 's/^[[:space:]]*//' \
	<<<"$generation10_case")
for generation10_assignment in \
	expected_kernel=bb49b4057ce573e3a53366c4663094cf462efb09d496b64b890ed2b0dcb65f98 \
	expected_raw=27f4dbcc61decd00ce6861cddb021070f38e9badde99152fc2dedbd4103d73b3 \
	expected_initramfs=99046d30e0910531ebda1163719ae8b5b81489f11329e29e12195fbfd63c6e31 \
	expected_control=67b4f012aab21e7b29934d3d6e41949aca5e46fdf90e9578ad5f6c87a3f2c167 \
	expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800 \
	expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0 \
	expected_target_id=headless-netroot-early-diag \
	expected_bundle=headless-netroot-early-diag-v1 \
	expected_bundle_profile=diagnostic-initramfs-v1 \
	expected_generation_record=cb999cd881959055f32fc1b7299cf1dffcf139656ff8c326ea1101d2ffd63b6d \
	expected_avb_salt=5f62ef87305b45de2d189729a601ac4b143c45e83485272ef5b91c508df5d3ee \
	expected_avb_digest=32b0de39bd409601da6b8c16bf5039fe9102410d9fb13a8b9f668283d53aee42
do
	grep -Fxq "$generation10_assignment" \
		<<<"$generation10_case_unindented" ||
		{ echo "FAIL generation-10 case does not pin $generation10_assignment" >&2; exit 1; }
done
generation10_live_policy_block=$(awk '
	index($0, "if [[ $profile == headless-diagnostic-generation10-live-v1 ]]; then") { capture = 1 }
	capture { print }
	capture && /^[[:space:]]*fi$/ { exit }
' <<<"$generation10_case")
generation10_live_policy_unindented=$(sed 's/^[[:space:]]*//' \
	<<<"$generation10_live_policy_block")
for generation10_live_assignment in \
	expected_boot_image=build/stable-recovery-generation10-prepare-progress-20260803-a/repack/stable-recovery-a.avb.img \
	"expected_boot_basis='one generation-10 PREPARE-progress-instrumented diagnostic lifecycle after connected preflight; remove after any result; never flash'"
do
	[[ $(grep -Fxc "$generation10_live_assignment" \
		<<<"$generation10_case_unindented") == 1 ]] ||
		{ echo "FAIL generation-10 case does not uniquely pin $generation10_live_assignment" >&2; exit 1; }
	grep -Fxq "$generation10_live_assignment" \
		<<<"$generation10_live_policy_unindented" ||
		{ echo "FAIL generation-10 live-only block does not pin $generation10_live_assignment" >&2; exit 1; }
done

for generation9_connected_action in boot preflight; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation9-live-v1 \
		LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
		RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
		TRUST_KEY="$repo/build/unused-trust-key" \
		BUNDLE_ROOT="$repo/build/unused-bundle-root" \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" "$generation9_connected_action" >"$tmp/out" 2>"$tmp/err"
	then
		echo "FAIL generation-9 live profile reached direct $generation9_connected_action" >&2
		exit 1
	fi
	grep -Fq \
		'generation-9 connected action requires the one-shot lifecycle controller' \
		"$tmp/err"
	if grep -Fq 'missing live-gate command' "$tmp/err"; then
		echo "FAIL generation-9 direct $generation9_connected_action reached host inspection" >&2
		exit 1
	fi
done

for generation9_policy_shape in missing duplicate wrong-basis readmitted-exact-basis; do
	policy_fixture=$tmp/generation9-policy-$generation9_policy_shape
	install -d -m 0755 "$policy_fixture/scripts/host" \
		"$policy_fixture/manifests"
	install -m 0755 "$gate" \
		"$policy_fixture/scripts/host/run-stable-recovery-live-gate.sh"
	cp -- "$artifact_manifest" "$policy_fixture/manifests/artifacts.tsv"
	case $generation9_policy_shape in
		missing)
			cp -- "$boot_policy" \
				"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		duplicate)
			cp -- "$boot_policy" \
				"$policy_fixture/manifests/temporary-boot-images.tsv"
			printf '%s\tallow\t%s\n' "$generation9_image" \
				'one generation-9 recovery-ACM-classifier diagnostic lifecycle after connected preflight; remove after any result; never flash' \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			printf '%s\tallow\t%s\n' "$generation9_image" \
				'one generation-9 recovery-ACM-classifier diagnostic lifecycle after connected preflight; remove after any result; never flash' \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		wrong-basis)
			cp -- "$boot_policy" \
				"$policy_fixture/manifests/temporary-boot-images.tsv"
			printf '%s\tallow\t%s\n' "$generation9_image" \
				'wrong generation-9 basis; never boot' \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		readmitted-exact-basis)
			cp -- "$boot_policy" \
				"$policy_fixture/manifests/temporary-boot-images.tsv"
			printf '%s\tallow\t%s\n' "$generation9_image" \
				'one generation-9 recovery-ACM-classifier diagnostic lifecycle after connected preflight; remove after any result; never flash' \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
	esac
	for generation9_connected_action in boot preflight; do
		if env -i PATH="$PATH" HOME="$HOME" \
			ALLOW_TEMPORARY_BOOT=1 \
			ALLOW_HEADLESS_LIVE_GATE=1 \
			ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
			ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation9-live-v1 \
			LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
			RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
			TRUST_KEY="$repo/build/unused-trust-key" \
			BUNDLE_ROOT="$repo/build/unused-bundle-root" \
			BUNDLE=headless-netroot-early-diag-v1 \
			RECOVERY_SHA256=b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008 \
			TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
			MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
			HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
			bash "$policy_fixture/scripts/host/run-stable-recovery-live-gate.sh" \
			"$generation9_connected_action" >"$tmp/out" 2>"$tmp/err"
		then
			echo "FAIL generation-9 $generation9_policy_shape policy reached $generation9_connected_action" >&2
			exit 1
		fi
		if [[ $generation9_policy_shape == wrong-basis ]]; then
			expected_policy_error="temporary boot policy basis does not match $generation9_image"
		elif [[ $generation9_policy_shape == readmitted-exact-basis ]]; then
			expected_policy_error='temporary boot artifact is recorded as consumed'
		else
			expected_policy_error="temporary boot policy does not uniquely list $generation9_image"
		fi
		grep -Fq "$expected_policy_error" "$tmp/err"
		if grep -Fq 'missing live-gate command' "$tmp/err"; then
			echo "FAIL generation-9 $generation9_policy_shape policy reached host inspection" >&2
			exit 1
		fi
	done
done

if env -i PATH="$PATH" HOME="$HOME" \
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation11-live-v1 \
	RECOVERY_SHA256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	BUNDLE=headless-netroot-early-diag-v1 \
	bash "$gate" policy-preflight >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL unsupported generation-11 live profile passed policy preflight' >&2
	exit 1
fi
grep -Fq 'policy preflight requires a fully pinned diagnostic profile' "$tmp/err"

for generation8_connected_action in boot preflight; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation8-live-v1 \
		LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
		RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
		TRUST_KEY="$repo/build/unused-trust-key" \
		BUNDLE_ROOT="$repo/build/unused-bundle-root" \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" "$generation8_connected_action" >"$tmp/out" 2>"$tmp/err"
	then
		echo "FAIL generation-8 live profile reached direct $generation8_connected_action" >&2
		exit 1
	fi
	if ! grep -Fq \
		'generation-8 connected action requires the one-shot lifecycle controller' \
		"$tmp/err"; then
		echo "FAIL generation-8 direct $generation8_connected_action rejected for wrong reason" >&2
		exit 1
	fi
	if grep -Fq 'missing live-gate command' "$tmp/err"; then
		echo "FAIL generation-8 direct $generation8_connected_action reached host inspection" >&2
		exit 1
	fi
done

for generation8_policy_shape in missing duplicate wrong-basis; do
	policy_fixture=$tmp/generation8-policy-$generation8_policy_shape
	install -d -m 0755 "$policy_fixture/scripts/host" \
		"$policy_fixture/manifests"
	install -m 0755 "$gate" \
		"$policy_fixture/scripts/host/run-stable-recovery-live-gate.sh"
	case $generation8_policy_shape in
		missing)
			awk -F '\t' -v name="$generation8_image" '$1 != name' \
				"$boot_policy" >"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		duplicate)
			cp -- "$boot_policy" \
				"$policy_fixture/manifests/temporary-boot-images.tsv"
			printf '%s\tallow\t%s\n%s\tallow\t%s\n' \
				"$generation8_image" \
				'disposable duplicate-policy fixture; never boot' \
				"$generation8_image" \
				'disposable duplicate-policy fixture; never boot' \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		wrong-basis)
			cp -- "$boot_policy" \
				"$policy_fixture/manifests/temporary-boot-images.tsv"
			printf '%s\tallow\t%s\n' \
				"$generation8_image" \
				'wrong generation-8 basis; never boot' \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
	esac
	for generation8_connected_action in boot preflight; do
		if env -i PATH="$PATH" HOME="$HOME" \
			ALLOW_TEMPORARY_BOOT=1 \
			ALLOW_HEADLESS_LIVE_GATE=1 \
			ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
			ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation8-live-v1 \
			LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
			RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
			TRUST_KEY="$repo/build/unused-trust-key" \
			BUNDLE_ROOT="$repo/build/unused-bundle-root" \
			BUNDLE=headless-netroot-early-diag-v1 \
			RECOVERY_SHA256=f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415 \
			TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
			MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
			HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
			bash "$policy_fixture/scripts/host/run-stable-recovery-live-gate.sh" \
			"$generation8_connected_action" >"$tmp/out" 2>"$tmp/err"
		then
			echo "FAIL generation-8 $generation8_policy_shape policy reached $generation8_connected_action" >&2
			exit 1
		fi
		if [[ $generation8_policy_shape == wrong-basis ]]; then
			expected_policy_error="temporary boot policy basis does not match $generation8_image"
		else
			expected_policy_error="temporary boot policy does not uniquely list $generation8_image"
		fi
		if ! grep -Fq "$expected_policy_error" "$tmp/err"; then
			echo "FAIL generation-8 $generation8_policy_shape policy rejected $generation8_connected_action for wrong reason" >&2
			exit 1
		fi
		if grep -Fq 'missing live-gate command' "$tmp/err"; then
			echo "FAIL generation-8 $generation8_policy_shape policy reached host inspection" >&2
			exit 1
		fi
	done
done

if env -i PATH="$PATH" HOME="$HOME" \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_HEADLESS_LIVE_GATE=1 \
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation7-live-v1 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-netroot-early-diag-v1 \
	RECOVERY_SHA256=d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901 \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	bash "$gate" boot >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL generation-7 live profile booted outside lifecycle' >&2
	exit 1
fi
grep -Fq 'generation-7 boot requires the one-shot lifecycle controller' \
	"$tmp/err"
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL generation-7 direct boot reached host inspection' >&2
	exit 1
fi

if env -i PATH="$PATH" HOME="$HOME" \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_HEADLESS_LIVE_GATE=1 \
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation6-live-v1 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-netroot-early-diag-v1 \
	RECOVERY_SHA256=6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398 \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	bash "$gate" boot >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL generation-6 live profile booted outside lifecycle' >&2
	exit 1
fi
grep -Fq 'generation-6 boot requires the one-shot lifecycle controller' \
	"$tmp/err"
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL generation-6 direct boot reached host inspection' >&2
	exit 1
fi

if env -i PATH="$PATH" HOME="$HOME" \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_HEADLESS_LIVE_GATE=1 \
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation5-live-v1 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-netroot-early-diag-v1 \
	RECOVERY_SHA256=abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	bash "$gate" boot >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL generation-5 live profile booted outside lifecycle' >&2
	exit 1
fi
grep -Fq 'generation-5 boot requires the one-shot lifecycle controller' \
	"$tmp/err"
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL generation-5 direct boot reached host inspection' >&2
	exit 1
fi

if env -i PATH="$PATH" HOME="$HOME" \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_HEADLESS_LIVE_GATE=1 \
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation4-live-v1 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-netroot-early-diag-v1 \
	RECOVERY_SHA256=220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	bash "$gate" boot >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL generation-4 live profile booted outside lifecycle' >&2
	exit 1
fi
grep -Fq 'generation-4 boot requires the one-shot lifecycle controller' \
	"$tmp/err"
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL generation-4 direct boot reached host inspection' >&2
	exit 1
fi

if env -i PATH="$PATH" HOME="$HOME" \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_HEADLESS_LIVE_GATE=1 \
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation3-live-v1 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-netroot-early-diag-v1 \
	RECOVERY_SHA256=eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6 \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	bash "$gate" boot >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL generation-3 live profile booted outside lifecycle' >&2
	exit 1
fi
grep -Fq 'generation-3 boot requires the one-shot lifecycle controller' \
	"$tmp/err"
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL generation-3 direct boot reached host inspection' >&2
	exit 1
fi

run_generation3_policy() {
	local selected_profile=$1 recovery=$2 trust=$3 manifest=$4
	local host_verifier=$5 selected_bundle=$6
	env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE="$selected_profile" \
		BUNDLE="$selected_bundle" \
		RECOVERY_SHA256="$recovery" \
		TRUST_KEY_SHA256="$trust" \
		MANIFEST_SHA256="$manifest" \
		HOST_VERIFIER_SHA256="$host_verifier" \
		bash "$gate" policy-preflight
}

generation3_exact=(
	eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76
	0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621
	headless-netroot-early-diag-v1
)
generation3_fields=(recovery trust manifest host-verifier bundle)
generation3_errors=(
	'generation-3 diagnostic recovery image is not pinned'
	'generation-3 diagnostic trust root is not pinned'
	'generation-3 diagnostic runtime manifest is not pinned'
	'generation-3 diagnostic host verifier is not pinned'
	'profile requires bundle=headless-netroot-early-diag-v1'
)
for generation3_profile in \
	headless-diagnostic-generation3-offline-v1 \
	headless-diagnostic-generation3-live-v1
do
	generation3_policy=$(run_generation3_policy \
		"$generation3_profile" "${generation3_exact[@]}")
	grep -Fxq "recovery_profile=$generation3_profile" \
		<<<"$generation3_policy"
	grep -Fxq \
		'recovery_sha256=eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6' \
		<<<"$generation3_policy"
	grep -Fxq 'authority=none' <<<"$generation3_policy"
	grep -Fxq 'result=PASS' <<<"$generation3_policy"
	for index in "${!generation3_fields[@]}"; do
		mutation=("${generation3_exact[@]}")
		if ((index == 4)); then
			mutation[$index]=wrong-generation3-bundle
		else
			mutation[$index]=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
		fi
		if run_generation3_policy \
			"$generation3_profile" "${mutation[@]}" \
			>"$tmp/out" 2>"$tmp/err"; then
			echo "FAIL $generation3_profile accepted wrong ${generation3_fields[$index]}" >&2
			exit 1
		fi
		grep -Fq "${generation3_errors[$index]}" "$tmp/err"
	done
done

generation4_exact=(
	220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76
	0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621
	headless-netroot-early-diag-v1
)
generation4_fields=(recovery trust manifest host-verifier bundle)
generation4_errors=(
	'generation-4 diagnostic recovery image is not pinned'
	'generation-4 diagnostic trust root is not pinned'
	'generation-4 diagnostic runtime manifest is not pinned'
	'generation-4 diagnostic host verifier is not pinned'
	'profile requires bundle=headless-netroot-early-diag-v1'
)
[[ ${#generation4_fields[@]} -eq ${#generation4_exact[@]} &&
	${#generation4_errors[@]} -eq ${#generation4_exact[@]} ]] ||
	{ echo 'FAIL generation-4 policy mutation matrix is inconsistent' >&2; exit 1; }
for generation4_profile in \
	headless-diagnostic-generation4-offline-v1 \
	headless-diagnostic-generation4-live-v1
do
	generation4_policy=$(run_generation3_policy \
		"$generation4_profile" "${generation4_exact[@]}")
	grep -Fxq "recovery_profile=$generation4_profile" \
		<<<"$generation4_policy"
	grep -Fxq \
		'recovery_sha256=220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d' \
		<<<"$generation4_policy"
	grep -Fxq 'authority=none' <<<"$generation4_policy"
	grep -Fxq 'result=PASS' <<<"$generation4_policy"
	for index in "${!generation4_fields[@]}"; do
		mutation=("${generation4_exact[@]}")
		if ((index == 4)); then
			mutation[$index]=wrong-generation4-bundle
		else
			mutation[$index]=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
		fi
		if run_generation3_policy \
			"$generation4_profile" "${mutation[@]}" \
			>"$tmp/out" 2>"$tmp/err"; then
			echo "FAIL $generation4_profile accepted wrong ${generation4_fields[$index]}" >&2
			exit 1
		fi
		grep -Fq "${generation4_errors[$index]}" "$tmp/err"
	done
done

generation5_exact=(
	abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76
	0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621
	headless-netroot-early-diag-v1
)
generation5_fields=(recovery trust manifest host-verifier bundle)
generation5_errors=(
	'generation-5 diagnostic recovery image is not pinned'
	'generation-5 diagnostic trust root is not pinned'
	'generation-5 diagnostic runtime manifest is not pinned'
	'generation-5 diagnostic host verifier is not pinned'
	'profile requires bundle=headless-netroot-early-diag-v1'
)
[[ ${#generation5_fields[@]} -eq ${#generation5_exact[@]} &&
	${#generation5_errors[@]} -eq ${#generation5_exact[@]} ]] ||
	{ echo 'FAIL generation-5 policy mutation matrix is inconsistent' >&2; exit 1; }
for generation5_profile in \
	headless-diagnostic-generation5-offline-v1 \
	headless-diagnostic-generation5-live-v1
do
	generation5_policy=$(run_generation3_policy \
		"$generation5_profile" "${generation5_exact[@]}")
	grep -Fxq "recovery_profile=$generation5_profile" \
		<<<"$generation5_policy"
	grep -Fxq \
		'recovery_sha256=abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a' \
		<<<"$generation5_policy"
	grep -Fxq 'authority=none' <<<"$generation5_policy"
	grep -Fxq 'result=PASS' <<<"$generation5_policy"
	for index in "${!generation5_fields[@]}"; do
		mutation=("${generation5_exact[@]}")
		if ((index == 4)); then
			mutation[$index]=wrong-generation5-bundle
		else
			mutation[$index]=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
		fi
		if run_generation3_policy \
			"$generation5_profile" "${mutation[@]}" \
			>"$tmp/out" 2>"$tmp/err"; then
			echo "FAIL $generation5_profile accepted wrong ${generation5_fields[$index]}" >&2
			exit 1
		fi
		grep -Fq "${generation5_errors[$index]}" "$tmp/err"
	done
done

generation6_exact=(
	6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76
	0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621
	headless-netroot-early-diag-v1
)
generation6_fields=(recovery trust manifest host-verifier bundle)
generation6_errors=(
	'generation-6 diagnostic recovery image is not pinned'
	'generation-6 diagnostic trust root is not pinned'
	'generation-6 diagnostic runtime manifest is not pinned'
	'generation-6 diagnostic host verifier is not pinned'
	'profile requires bundle=headless-netroot-early-diag-v1'
)
[[ ${#generation6_fields[@]} -eq ${#generation6_exact[@]} &&
	${#generation6_errors[@]} -eq ${#generation6_exact[@]} ]] ||
	{ echo 'FAIL generation-6 policy mutation matrix is inconsistent' >&2; exit 1; }
for generation6_profile in \
	headless-diagnostic-generation6-offline-v1 \
	headless-diagnostic-generation6-live-v1
do
	generation6_policy=$(run_generation3_policy \
		"$generation6_profile" "${generation6_exact[@]}")
	grep -Fxq "recovery_profile=$generation6_profile" \
		<<<"$generation6_policy"
	grep -Fxq \
		'recovery_sha256=6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398' \
		<<<"$generation6_policy"
	grep -Fxq 'authority=none' <<<"$generation6_policy"
	grep -Fxq 'result=PASS' <<<"$generation6_policy"
	for index in "${!generation6_fields[@]}"; do
		mutation=("${generation6_exact[@]}")
		if ((index == 4)); then
			mutation[$index]=wrong-generation6-bundle
		else
			mutation[$index]=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
		fi
		if run_generation3_policy \
			"$generation6_profile" "${mutation[@]}" \
			>"$tmp/out" 2>"$tmp/err"; then
			echo "FAIL $generation6_profile accepted wrong ${generation6_fields[$index]}" >&2
			exit 1
		fi
		grep -Fq "${generation6_errors[$index]}" "$tmp/err"
	done
done

generation7_exact=(
	d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76
	0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621
	headless-netroot-early-diag-v1
)
generation7_fields=(recovery trust manifest host-verifier bundle)
generation7_errors=(
	'generation-7 diagnostic recovery image is not pinned'
	'generation-7 diagnostic trust root is not pinned'
	'generation-7 diagnostic runtime manifest is not pinned'
	'generation-7 diagnostic host verifier is not pinned'
	'profile requires bundle=headless-netroot-early-diag-v1'
)
[[ ${#generation7_fields[@]} -eq ${#generation7_exact[@]} &&
	${#generation7_errors[@]} -eq ${#generation7_exact[@]} ]] ||
	{ echo 'FAIL generation-7 policy mutation matrix is inconsistent' >&2; exit 1; }
for generation7_profile in \
	headless-diagnostic-generation7-offline-v1 \
	headless-diagnostic-generation7-live-v1
do
	generation7_policy=$(run_generation3_policy \
		"$generation7_profile" "${generation7_exact[@]}")
	grep -Fxq "recovery_profile=$generation7_profile" <<<"$generation7_policy"
	grep -Fxq \
		'recovery_sha256=d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901' \
		<<<"$generation7_policy"
	grep -Fxq 'authority=none' <<<"$generation7_policy"
	grep -Fxq 'result=PASS' <<<"$generation7_policy"
	for index in "${!generation7_fields[@]}"; do
		mutation=("${generation7_exact[@]}")
		if ((index == 4)); then
			mutation[$index]=wrong-generation7-bundle
		else
			mutation[$index]=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
		fi
		if run_generation3_policy "$generation7_profile" "${mutation[@]}" \
			>"$tmp/out" 2>"$tmp/err"; then
			echo "FAIL $generation7_profile accepted wrong ${generation7_fields[$index]}" >&2
			exit 1
		fi
		grep -Fq "${generation7_errors[$index]}" "$tmp/err"
	done
done

generation8_exact=(
	f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76
	0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621
	headless-netroot-early-diag-v1
)
generation8_fields=(recovery trust manifest host-verifier bundle)
generation8_errors=(
	'generation-8 diagnostic recovery image is not pinned'
	'generation-8 diagnostic trust root is not pinned'
	'generation-8 diagnostic runtime manifest is not pinned'
	'generation-8 diagnostic host verifier is not pinned'
	'profile requires bundle=headless-netroot-early-diag-v1'
)
[[ ${#generation8_fields[@]} -eq ${#generation8_exact[@]} &&
	${#generation8_errors[@]} -eq ${#generation8_exact[@]} ]] ||
	{ echo 'FAIL generation-8 policy mutation matrix is inconsistent' >&2; exit 1; }
for generation8_profile in \
	headless-diagnostic-generation8-offline-v1 \
	headless-diagnostic-generation8-live-v1
do
	generation8_policy=$(run_generation3_policy \
		"$generation8_profile" "${generation8_exact[@]}")
	grep -Fxq "recovery_profile=$generation8_profile" <<<"$generation8_policy"
	grep -Fxq \
		'recovery_sha256=f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415' \
		<<<"$generation8_policy"
	grep -Fxq 'authority=none' <<<"$generation8_policy"
	grep -Fxq 'result=PASS' <<<"$generation8_policy"
	for index in "${!generation8_fields[@]}"; do
		mutation=("${generation8_exact[@]}")
		if ((index == 4)); then
			mutation[$index]=wrong-generation8-bundle
		else
			mutation[$index]=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
		fi
		if run_generation3_policy "$generation8_profile" "${mutation[@]}" \
			>"$tmp/out" 2>"$tmp/err"; then
			echo "FAIL $generation8_profile accepted wrong ${generation8_fields[$index]}" >&2
			exit 1
		fi
		grep -Fq "${generation8_errors[$index]}" "$tmp/err"
	done
done

generation9_exact=(
	b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76
	0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621
	headless-netroot-early-diag-v1
)
generation9_fields=(recovery trust manifest host-verifier bundle)
generation9_errors=(
	'generation-9 diagnostic recovery image is not pinned'
	'generation-9 diagnostic trust root is not pinned'
	'generation-9 diagnostic runtime manifest is not pinned'
	'generation-9 diagnostic host verifier is not pinned'
	'profile requires bundle=headless-netroot-early-diag-v1'
)
[[ ${#generation9_fields[@]} -eq ${#generation9_exact[@]} &&
	${#generation9_errors[@]} -eq ${#generation9_exact[@]} ]] ||
	{ echo 'FAIL generation-9 policy mutation matrix is inconsistent' >&2; exit 1; }
for generation9_profile in \
	headless-diagnostic-generation9-offline-v1 \
	headless-diagnostic-generation9-live-v1
do
	generation9_policy=$(run_generation3_policy \
		"$generation9_profile" "${generation9_exact[@]}")
	grep -Fxq "recovery_profile=$generation9_profile" <<<"$generation9_policy"
	grep -Fxq \
		'recovery_sha256=b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008' \
		<<<"$generation9_policy"
	grep -Fxq 'authority=none' <<<"$generation9_policy"
	grep -Fxq 'result=PASS' <<<"$generation9_policy"
	for index in "${!generation9_fields[@]}"; do
		mutation=("${generation9_exact[@]}")
		if ((index == 4)); then
			mutation[$index]=wrong-generation9-bundle
		else
			mutation[$index]=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
		fi
		if run_generation3_policy "$generation9_profile" \
			"${mutation[@]}" >"$tmp/out" 2>"$tmp/err"; then
			echo "FAIL $generation9_profile accepted wrong ${generation9_fields[$index]}" >&2
			exit 1
		fi
		grep -Fq "${generation9_errors[$index]}" "$tmp/err"
	done
done

generation10_exact=(
	b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76
	0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621
	headless-netroot-early-diag-v1
)
generation10_fields=(recovery trust manifest host-verifier bundle)
generation10_errors=(
	'generation-10 diagnostic recovery image is not pinned'
	'generation-10 diagnostic trust root is not pinned'
	'generation-10 diagnostic runtime manifest is not pinned'
	'generation-10 diagnostic host verifier is not pinned'
	'profile requires bundle=headless-netroot-early-diag-v1'
)
[[ ${#generation10_fields[@]} -eq ${#generation10_exact[@]} &&
	${#generation10_errors[@]} -eq ${#generation10_exact[@]} ]] ||
	{ echo 'FAIL generation-10 policy mutation matrix is inconsistent' >&2; exit 1; }
for generation10_profile in \
	headless-diagnostic-generation10-offline-v1 \
	headless-diagnostic-generation10-live-v1
do
	generation10_policy=$(run_generation3_policy \
		"$generation10_profile" "${generation10_exact[@]}")
	grep -Fxq "recovery_profile=$generation10_profile" \
		<<<"$generation10_policy" ||
		{ echo "FAIL $generation10_profile policy omitted the exact profile" >&2; exit 1; }
	grep -Fxq \
		'recovery_sha256=b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51' \
		<<<"$generation10_policy" ||
		{ echo "FAIL $generation10_profile policy omitted the exact recovery identity" >&2; exit 1; }
	grep -Fxq 'authority=none' <<<"$generation10_policy" ||
		{ echo "FAIL $generation10_profile policy granted authority" >&2; exit 1; }
	grep -Fxq 'result=PASS' <<<"$generation10_policy" ||
		{ echo "FAIL $generation10_profile policy did not pass" >&2; exit 1; }
	for index in "${!generation10_fields[@]}"; do
		mutation=("${generation10_exact[@]}")
		if ((index == 4)); then
			mutation[$index]=wrong-generation10-bundle
		else
			mutation[$index]=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
		fi
		if run_generation3_policy "$generation10_profile" \
			"${mutation[@]}" >"$tmp/out" 2>"$tmp/err"; then
			echo "FAIL $generation10_profile accepted wrong ${generation10_fields[$index]}" >&2
			exit 1
		fi
		grep -Fq "${generation10_errors[$index]}" "$tmp/err" ||
			{ echo "FAIL $generation10_profile wrong ${generation10_fields[$index]} returned the wrong rejection" >&2; exit 1; }
	done
done

if [[ -d $generation3_root ]]; then
	for generation3_profile in \
		headless-diagnostic-generation3-offline-v1 \
		headless-diagnostic-generation3-live-v1
	do
		generation3_artifact=$(
			env -i PATH="$PATH" HOME="$HOME" \
				ROG5_STABLE_RECOVERY_PROFILE="$generation3_profile" \
				LIVE_BUILD_ROOT="$generation3_root/wrapper" \
				RECOVERY_COMPONENT_ROOT="$generation3_root/recovery" \
				TRUST_KEY="$generation3_root/recovery/ephemeral-public.raw" \
				BUNDLE_ROOT="$generation3_root/bundle-a" \
				BUNDLE=headless-netroot-early-diag-v1 \
				RECOVERY_SHA256=eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6 \
				TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
				MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
				HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
				bash "$gate" artifact-preflight
		)
		grep -Fxq \
			"PASS stable-recovery artifact preflight profile=$generation3_profile image_sha256=eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6" \
			<<<"$generation3_artifact"
	done
else
	echo 'SKIP generation-3 retained artifact preflight: ignored build tree absent' >&2
fi

if [[ -d $generation4_root && -d $generation3_root ]]; then
	for generation4_profile in \
		headless-diagnostic-generation4-offline-v1 \
		headless-diagnostic-generation4-live-v1
	do
		generation4_artifact=$(
			env -i PATH="$PATH" HOME="$HOME" \
			ROG5_STABLE_RECOVERY_PROFILE="$generation4_profile" \
			LIVE_BUILD_ROOT="$generation4_root" \
			RECOVERY_COMPONENT_ROOT="$generation3_root/recovery" \
			TRUST_KEY="$generation3_root/recovery/ephemeral-public.raw" \
			BUNDLE_ROOT="$generation3_root/bundle-a" \
			BUNDLE=headless-netroot-early-diag-v1 \
			RECOVERY_SHA256=220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d \
			TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
			MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
			HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
				bash "$gate" artifact-preflight
		)
		grep -Fxq \
			"PASS stable-recovery artifact preflight profile=$generation4_profile image_sha256=220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d" \
			<<<"$generation4_artifact"
	done
else
	echo 'SKIP generation-4 artifact preflight: ignored build trees absent' >&2
fi

if [[ -d $generation5_root && -d $generation3_root ]]; then
	for generation5_profile in \
		headless-diagnostic-generation5-offline-v1 \
		headless-diagnostic-generation5-live-v1
	do
		generation5_artifact=$(
			env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE="$generation5_profile" \
		LIVE_BUILD_ROOT="$generation5_root" \
		RECOVERY_COMPONENT_ROOT="$generation3_root/recovery" \
		TRUST_KEY="$generation3_root/recovery/ephemeral-public.raw" \
		BUNDLE_ROOT="$generation3_root/bundle-a" \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
				bash "$gate" artifact-preflight
		)
		grep -Fxq \
			"PASS stable-recovery artifact preflight profile=$generation5_profile image_sha256=abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a" \
			<<<"$generation5_artifact"
	done
else
	echo 'SKIP generation-5 artifact preflight: ignored build trees absent' >&2
fi

if [[ -d $generation6_root && -d $generation3_root ]]; then
	for generation6_profile in \
		headless-diagnostic-generation6-offline-v1 \
		headless-diagnostic-generation6-live-v1
	do
		generation6_artifact=$(
			env -i PATH="$PATH" HOME="$HOME" \
			ROG5_STABLE_RECOVERY_PROFILE="$generation6_profile" \
			LIVE_BUILD_ROOT="$generation6_root" \
			RECOVERY_COMPONENT_ROOT="$generation3_root/recovery" \
			TRUST_KEY="$generation3_root/recovery/ephemeral-public.raw" \
			BUNDLE_ROOT="$generation3_root/bundle-a" \
			BUNDLE=headless-netroot-early-diag-v1 \
			RECOVERY_SHA256=6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398 \
			TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
			MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
			HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
				bash "$gate" artifact-preflight
		)
		grep -Fxq \
			"PASS stable-recovery artifact preflight profile=$generation6_profile image_sha256=6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398" \
			<<<"$generation6_artifact"
	done
else
	echo 'SKIP generation-6 artifact preflight: ignored build trees absent' >&2
fi

if [[ -d $generation7_root_a || -d $generation7_root_b ]]; then
	[[ -d $generation7_root_a && -d $generation7_root_b ]] ||
		{ echo 'FAIL generation-7 production issuer twins are asymmetric' >&2; exit 1; }
	[[ -d $generation3_root ]] ||
		{ echo 'FAIL generation-7 retained component tree is absent' >&2; exit 1; }
	build_tmp=$(mktemp -d "$repo/build/stable-recovery-gate-test.XXXXXX")
	for relative in \
		avb-generation.txt \
		repack/stable-recovery-a.avb.img \
		repack/stable-recovery-a.raw.img \
		repack/stable-recovery-b.avb.img \
		repack/stable-recovery-b.raw.img \
		wrapper-a/asus-kexec-stage/.config \
		wrapper-a/asus-kexec-stage/arch/arm64/boot/Image \
		wrapper-a/rog5-kexec-stage-initramfs.cpio.gz \
		wrapper-b/asus-kexec-stage/.config \
		wrapper-b/asus-kexec-stage/arch/arm64/boot/Image \
		wrapper-b/rog5-kexec-stage-initramfs.cpio.gz
	do
		cmp "$generation7_root_a/$relative" "$generation7_root_b/$relative"
	done
	for generation7_root in "$generation7_root_a" "$generation7_root_b"; do
		for generation7_profile in \
			headless-diagnostic-generation7-offline-v1 \
			headless-diagnostic-generation7-live-v1
		do
			generation7_artifact=$(
				env -i PATH="$PATH" HOME="$HOME" \
			ROG5_STABLE_RECOVERY_PROFILE="$generation7_profile" \
			LIVE_BUILD_ROOT="$generation7_root" \
			RECOVERY_COMPONENT_ROOT="$generation3_root/recovery" \
			TRUST_KEY="$generation3_root/recovery/ephemeral-public.raw" \
			BUNDLE_ROOT="$generation3_root/bundle-a" \
			BUNDLE=headless-netroot-early-diag-v1 \
			RECOVERY_SHA256=d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901 \
			TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
			MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
			HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
					bash "$gate" artifact-preflight
			)
			grep -Fxq \
				"PASS stable-recovery artifact preflight profile=$generation7_profile image_sha256=d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901" \
				<<<"$generation7_artifact"
		done
	done

	generation7_mutation=$build_tmp/generation7-record-mutation
	cp -a --reflink=auto "$generation7_root_a" "$generation7_mutation"
	chmod -R u+rwX "$generation7_mutation"
	sed -i 's/^generation=7$/generation=6/' \
		"$generation7_mutation/avb-generation.txt"
	grep -Fxq 'generation=6' "$generation7_mutation/avb-generation.txt"
	if env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation7-offline-v1 \
		LIVE_BUILD_ROOT="$generation7_mutation" \
		RECOVERY_COMPONENT_ROOT="$generation3_root/recovery" \
		TRUST_KEY="$generation3_root/recovery/ephemeral-public.raw" \
		BUNDLE_ROOT="$generation3_root/bundle-a" \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" artifact-preflight >"$tmp/out" 2>"$tmp/err"
	then
		echo 'FAIL generation-7 artifact preflight accepted a mutated generation record' >&2
		exit 1
	fi
	grep -Fq "identity mismatch: $generation7_mutation/avb-generation.txt" "$tmp/err"
else
	echo 'SKIP generation-7 twin artifact preflight: ignored build trees absent' >&2
fi

if [[ -d $generation8_root_a || -d $generation8_root_b ]]; then
	[[ -d $generation8_root_a && -d $generation8_root_b ]] ||
		{ echo 'FAIL generation-8 production issuer twins are asymmetric' >&2; exit 1; }
	[[ -d $generation3_root ]] ||
		{ echo 'FAIL generation-8 retained component tree is absent' >&2; exit 1; }
	if [[ -z $build_tmp ]]; then
		build_tmp=$(mktemp -d "$repo/build/stable-recovery-gate-test.XXXXXX")
	fi
	for relative in \
		avb-generation.txt \
		repack/stable-recovery-a.avb.img \
		repack/stable-recovery-a.raw.img \
		repack/stable-recovery-b.avb.img \
		repack/stable-recovery-b.raw.img \
		wrapper-a/asus-kexec-stage/.config \
		wrapper-a/asus-kexec-stage/arch/arm64/boot/Image \
		wrapper-a/rog5-kexec-stage-initramfs.cpio.gz \
		wrapper-b/asus-kexec-stage/.config \
		wrapper-b/asus-kexec-stage/arch/arm64/boot/Image \
		wrapper-b/rog5-kexec-stage-initramfs.cpio.gz
	do
		cmp "$generation8_root_a/$relative" "$generation8_root_b/$relative"
	done
	for generation8_root in "$generation8_root_a" "$generation8_root_b"; do
		cmp "$generation8_root/repack/stable-recovery-a.avb.img" \
			"$generation8_root/repack/stable-recovery-b.avb.img"
		cmp "$generation8_root/repack/stable-recovery-a.raw.img" \
			"$generation8_root/repack/stable-recovery-b.raw.img"
	done
	for generation8_root in "$generation8_root_a" "$generation8_root_b"; do
		for generation8_profile in \
			headless-diagnostic-generation8-offline-v1 \
			headless-diagnostic-generation8-live-v1
		do
			generation8_artifact=$(
				env -i PATH="$PATH" HOME="$HOME" \
				ROG5_STABLE_RECOVERY_PROFILE="$generation8_profile" \
				LIVE_BUILD_ROOT="$generation8_root" \
				RECOVERY_COMPONENT_ROOT="$generation3_root/recovery" \
				TRUST_KEY="$generation3_root/recovery/ephemeral-public.raw" \
				BUNDLE_ROOT="$generation3_root/bundle-a" \
				BUNDLE=headless-netroot-early-diag-v1 \
				RECOVERY_SHA256=f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415 \
				TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
				MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
				HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
					bash "$gate" artifact-preflight
			)
			grep -Fxq \
				"PASS stable-recovery artifact preflight profile=$generation8_profile image_sha256=f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415" \
				<<<"$generation8_artifact"
		done
	done

	generation8_mutation=$build_tmp/generation8-record-mutation
	cp -a --reflink=auto "$generation8_root_a" "$generation8_mutation"
	chmod -R u+rwX "$generation8_mutation"
	sed -i 's/^generation=8$/generation=7/' \
		"$generation8_mutation/avb-generation.txt"
	grep -Fxq 'generation=7' "$generation8_mutation/avb-generation.txt"
	if env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation8-offline-v1 \
		LIVE_BUILD_ROOT="$generation8_mutation" \
		RECOVERY_COMPONENT_ROOT="$generation3_root/recovery" \
		TRUST_KEY="$generation3_root/recovery/ephemeral-public.raw" \
		BUNDLE_ROOT="$generation3_root/bundle-a" \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" artifact-preflight >"$tmp/out" 2>"$tmp/err"
	then
		echo 'FAIL generation-8 artifact preflight accepted a mutated generation record' >&2
		exit 1
	fi
	grep -Fq "identity mismatch: $generation8_mutation/avb-generation.txt" "$tmp/err"
else
	echo 'SKIP generation-8 twin artifact preflight: ignored build trees absent' >&2
fi

if [[ -d $generation9_root_a || -d $generation9_root_b ]]; then
	[[ -d $generation9_root_a && -d $generation9_root_b ]] ||
		{ echo 'FAIL generation-9 production issuer twins are asymmetric' >&2; exit 1; }
	[[ -d $generation3_root ]] ||
		{ echo 'FAIL generation-9 retained component tree is absent' >&2; exit 1; }
	if [[ -z $build_tmp ]]; then
		build_tmp=$(mktemp -d "$repo/build/stable-recovery-gate-test.XXXXXX")
	fi
	for relative in \
		avb-generation.txt \
		repack/stable-recovery-a.avb.img \
		repack/stable-recovery-a.raw.img \
		repack/stable-recovery-b.avb.img \
		repack/stable-recovery-b.raw.img \
		wrapper-a/asus-kexec-stage/.config \
		wrapper-a/asus-kexec-stage/arch/arm64/boot/Image \
		wrapper-a/rog5-kexec-stage-initramfs.cpio.gz \
		wrapper-b/asus-kexec-stage/.config \
		wrapper-b/asus-kexec-stage/arch/arm64/boot/Image \
		wrapper-b/rog5-kexec-stage-initramfs.cpio.gz
	do
		cmp "$generation9_root_a/$relative" "$generation9_root_b/$relative"
	done
	for generation9_root in "$generation9_root_a" "$generation9_root_b"; do
		cmp "$generation9_root/repack/stable-recovery-a.avb.img" \
			"$generation9_root/repack/stable-recovery-b.avb.img"
		cmp "$generation9_root/repack/stable-recovery-a.raw.img" \
			"$generation9_root/repack/stable-recovery-b.raw.img"
		for generation9_profile in \
			headless-diagnostic-generation9-offline-v1 \
			headless-diagnostic-generation9-live-v1
		do
			generation9_artifact=$(
				env -i PATH="$PATH" HOME="$HOME" \
					ROG5_STABLE_RECOVERY_PROFILE="$generation9_profile" \
					LIVE_BUILD_ROOT="$generation9_root" \
					RECOVERY_COMPONENT_ROOT="$generation3_root/recovery" \
					TRUST_KEY="$generation3_root/recovery/ephemeral-public.raw" \
					BUNDLE_ROOT="$generation3_root/bundle-a" \
					BUNDLE=headless-netroot-early-diag-v1 \
					RECOVERY_SHA256=b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008 \
					TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
					MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
					HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
					bash "$gate" artifact-preflight
			)
			grep -Fxq \
				"PASS stable-recovery artifact preflight profile=$generation9_profile image_sha256=b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008" \
				<<<"$generation9_artifact"
		done
	done

	generation9_mutation=$build_tmp/generation9-record-mutation
	cp -a --reflink=auto "$generation9_root_a" "$generation9_mutation"
	chmod -R u+rwX "$generation9_mutation"
	sed -i 's/^generation=9$/generation=8/' \
		"$generation9_mutation/avb-generation.txt"
	if env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation9-offline-v1 \
		LIVE_BUILD_ROOT="$generation9_mutation" \
		RECOVERY_COMPONENT_ROOT="$generation3_root/recovery" \
		TRUST_KEY="$generation3_root/recovery/ephemeral-public.raw" \
		BUNDLE_ROOT="$generation3_root/bundle-a" \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" artifact-preflight >"$tmp/out" 2>"$tmp/err"; then
		echo 'FAIL generation-9 artifact preflight accepted a mutated generation record' >&2
		exit 1
	fi
	grep -Fq "identity mismatch: $generation9_mutation/avb-generation.txt" "$tmp/err"
else
	echo 'SKIP generation-9 twin artifact preflight: ignored build trees absent' >&2
fi

if [[ -d $generation10_root_a || -d $generation10_root_b ||
	-d $generation10_base ]]; then
	[[ -d $generation10_root_a && -d $generation10_root_b &&
		-d $generation10_base ]] ||
		{ echo 'FAIL generation-10 production inputs are asymmetric' >&2; exit 1; }
	if [[ -z $build_tmp ]]; then
		build_tmp=$(mktemp -d "$repo/build/stable-recovery-gate-test.XXXXXX")
	fi
	for relative in \
		avb-generation.txt \
		repack/stable-recovery-a.avb.img \
		repack/stable-recovery-a.raw.img \
		repack/stable-recovery-b.avb.img \
		repack/stable-recovery-b.raw.img \
		wrapper-a/asus-kexec-stage/.config \
		wrapper-a/asus-kexec-stage/arch/arm64/boot/Image \
		wrapper-a/rog5-kexec-stage-initramfs.cpio.gz \
		wrapper-b/asus-kexec-stage/.config \
		wrapper-b/asus-kexec-stage/arch/arm64/boot/Image \
		wrapper-b/rog5-kexec-stage-initramfs.cpio.gz
	do
		cmp "$generation10_root_a/$relative" "$generation10_root_b/$relative"
	done
	for generation10_profile in \
		headless-diagnostic-generation10-offline-v1 \
		headless-diagnostic-generation10-live-v1
	do
		for generation10_suffix in a b; do
			if [[ $generation10_suffix == a ]]; then
				generation10_root=$generation10_root_a
			else
				generation10_root=$generation10_root_b
			fi
			generation10_artifact=$(
				env -i PATH="$PATH" HOME="$HOME" \
					ROG5_STABLE_RECOVERY_PROFILE="$generation10_profile" \
					LIVE_BUILD_ROOT="$generation10_root" \
					RECOVERY_COMPONENT_ROOT="$generation10_base/recovery" \
					TRUST_KEY="$generation10_base/recovery/ephemeral-public.raw" \
					BUNDLE_ROOT="$generation10_base/bundle-$generation10_suffix" \
					BUNDLE=headless-netroot-early-diag-v1 \
					RECOVERY_SHA256=b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51 \
					TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
					MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
					HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
					bash "$gate" artifact-preflight
			)
			grep -Fxq \
				"PASS stable-recovery artifact preflight profile=$generation10_profile image_sha256=b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51" \
				<<<"$generation10_artifact" ||
				{ echo "FAIL $generation10_profile tree $generation10_suffix did not pass artifact preflight" >&2; exit 1; }
		done
	done

	generation10_mutation=$build_tmp/generation10-record-mutation
	cp -a --reflink=auto "$generation10_root_a" "$generation10_mutation"
	chmod -R u+rwX "$generation10_mutation"
	sed -i 's/^generation=10$/generation=9/' \
		"$generation10_mutation/avb-generation.txt"
	if env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation10-offline-v1 \
		LIVE_BUILD_ROOT="$generation10_mutation" \
		RECOVERY_COMPONENT_ROOT="$generation10_base/recovery" \
		TRUST_KEY="$generation10_base/recovery/ephemeral-public.raw" \
		BUNDLE_ROOT="$generation10_base/bundle-a" \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" artifact-preflight >"$tmp/out" 2>"$tmp/err"; then
		echo 'FAIL generation-10 artifact preflight accepted a mutated generation record' >&2
		exit 1
	fi
	grep -Fq "identity mismatch: $generation10_mutation/avb-generation.txt" \
		"$tmp/err" ||
		{ echo 'FAIL generation-10 record mutation returned the wrong rejection' >&2; exit 1; }
else
	echo 'SKIP generation-10 twin artifact preflight: ignored build trees absent' >&2
fi

run_diagnostic_policy() {
	local selected_bundle=$1 selected_image=$2 selected_manifest=$3
	env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-deployment-v1 \
		BUNDLE="$selected_bundle" \
		RECOVERY_SHA256="$selected_image" \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256="$selected_manifest" \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" policy-preflight
}

if run_diagnostic_policy \
	headless-netroot-early-diag-v1 \
	70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1 \
	9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630 \
	>"$tmp/out" 2>"$tmp/err"; then
	echo 'FAIL diagnostic artifact policy accepted the normal r2 manifest' >&2
	exit 1
fi
grep -Fq 'diagnostic runtime manifest is not allowlisted' "$tmp/err"

if run_diagnostic_policy \
	headless-ssh-network-root-v3-r2 \
	70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1 \
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	>"$tmp/out" 2>"$tmp/err"; then
	echo 'FAIL diagnostic artifact policy accepted the normal r2 bundle' >&2
	exit 1
fi
grep -Fq 'profile requires bundle=headless-netroot-early-diag-v1' "$tmp/err"

if run_diagnostic_policy \
	headless-netroot-early-diag-v1 \
	ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff \
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	>"$tmp/out" 2>"$tmp/err"; then
	echo 'FAIL diagnostic artifact policy accepted a wrong recovery image' >&2
	exit 1
fi
grep -Fq 'diagnostic recovery image identity is not allowlisted' "$tmp/err"

# Every consumed diagnostic identity must fail before profile association or
# host discovery; negative association tests above use the admitted generation.
for consumed_image in \
	9c060a27f21f6f99ca0c00cd1ff2ed9532220d585cd726b194f8b6d04e6204ef \
	f710bbcd1f9602f0fdc3ce7023298f66cc5e7a014a0627c4f9123d7cc897b0ef \
	332889a83f541ed0e17c94656836c512a35b5bfd6bbbaf735d2f5f6b94b51830
do
	if env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-deployment-v1 \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256="$consumed_image" \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" policy-preflight >"$tmp/out" 2>"$tmp/err"
	then
		echo 'FAIL consumed diagnostic recovery passed policy preflight' >&2
		exit 1
	fi
	grep -Fq 'refusing the consumed diagnostic recovery image' "$tmp/err"
done

if env -i PATH="$PATH" HOME="$HOME" \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_HEADLESS_LIVE_GATE=1 \
	ROG5_STABLE_RECOVERY_PROFILE=headless-ssh-deployment-v3 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-ssh-network-root-v3-r2 \
	RECOVERY_SHA256=11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630 \
	HOST_VERIFIER_SHA256=9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b \
	bash "$gate" boot >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL consumed r2 manifest reached direct boot admission' >&2
	exit 1
fi
grep -Fq 'refusing a consumed deployment manifest' "$tmp/err"

# shellcheck disable=SC2016
for required in \
	'ALLOW_HEADLESS_LIVE_GATE' \
	'artifact-preflight' \
	'policy-preflight' \
	'ROG5_STABLE_RECOVERY_PROFILE' \
	'set ROG5_STABLE_RECOVERY_PROFILE explicitly' \
	'corrected-headless-successor-2026-07-30' \
	'headless-ssh-deployment-v3' \
	'headless-diagnostic-deployment-v1' \
	'headless-diagnostic-generation3-offline-v1' \
	'headless-diagnostic-generation3-live-v1' \
	'headless-diagnostic-generation4-offline-v1' \
	'headless-diagnostic-generation4-live-v1' \
	'headless-diagnostic-generation5-offline-v1' \
	'headless-diagnostic-generation5-live-v1' \
	'headless-diagnostic-generation6-offline-v1' \
	'headless-diagnostic-generation6-live-v1' \
	'headless-diagnostic-generation7-offline-v1' \
	'headless-diagnostic-generation7-live-v1' \
	'headless-diagnostic-generation8-offline-v1' \
	'headless-diagnostic-generation8-live-v1' \
	'headless-diagnostic-generation9-offline-v1' \
	'headless-diagnostic-generation9-live-v1' \
	'headless-diagnostic-generation10-offline-v1' \
	'headless-diagnostic-generation10-live-v1' \
	'historical diagnostic profile is offline-only and consumed' \
	'generation-3 diagnostic profile is offline-only and not boot-authorized' \
	'generation-3 boot requires the one-shot lifecycle controller' \
	'generation-4 diagnostic profile is offline-only and not boot-authorized' \
	'generation-4 boot requires the one-shot lifecycle controller' \
	'generation-5 diagnostic profile is offline-only and not boot-authorized' \
	'generation-5 boot requires the one-shot lifecycle controller' \
	'generation-6 diagnostic profile is offline-only and not boot-authorized' \
	'generation-6 boot requires the one-shot lifecycle controller' \
	'generation-7 diagnostic profile is offline-only and not boot-authorized' \
	'generation-7 boot requires the one-shot lifecycle controller' \
	'generation-8 diagnostic profile is offline-only and not boot-authorized' \
	'generation-8 connected action requires the one-shot lifecycle controller' \
	'generation-9 diagnostic profile is offline-only and not boot-authorized' \
	'generation-9 connected action requires the one-shot lifecycle controller' \
	'generation-10 diagnostic profile is offline-only and not boot-authorized' \
	'generation-10 connected action requires the one-shot lifecycle controller' \
	'temporary boot artifact is recorded as consumed' \
	'temporary boot policy basis does not match' \
	'expected_boot_image=build/stable-recovery-generation8-nmcli-empty-field-fix-20260803-a/repack/stable-recovery-a.avb.img' \
	'expected_boot_image=build/stable-recovery-generation9-acm-classifier-20260803-a/repack/stable-recovery-a.avb.img' \
	"expected_boot_basis='one generation-8 NetworkManager-empty-field-corrected diagnostic lifecycle after connected preflight; remove after any result; never flash'" \
	"expected_boot_basis='one generation-9 recovery-ACM-classifier diagnostic lifecycle after connected preflight; remove after any result; never flash'" \
	'416d62e4f0d89e9184d8a362c8c9e5091bd265f4c48504916920706f08611430' \
	'bc42d9ffc78ed88c5e8f597905844e472a5681c57caab020ce88c1eae1b706da' \
	'157da94bf50635099c571ce97d3e3c797c22eb66e3b9730b4ea332d952a9261c' \
	'ac5fd5169be86a44b01e8e2d5d5343feddf9ffdc34ea3581a430c5cbc2962c04' \
	'11feb00b6a80e701e74c8538b6f80fb4956d9b21463d666806e0b5f14b52213c' \
	'expected_kernel=1a8bac7a2b016dc7d63d22f09d0872b9c3f251952b7627c68f7c387f386b0068' \
	'expected_raw=a937b03b54c01c6240cff45aa243632827d0c9d328e6f285ae489c973a6213a9' \
	'expected_initramfs=f414d0ea26ee3aa6cca5c3aa12c1601934294c0207fc2709ebbae305bb3642e0' \
	'9c060a27f21f6f99ca0c00cd1ff2ed9532220d585cd726b194f8b6d04e6204ef' \
	'f710bbcd1f9602f0fdc3ce7023298f66cc5e7a014a0627c4f9123d7cc897b0ef' \
	'332889a83f541ed0e17c94656836c512a35b5bfd6bbbaf735d2f5f6b94b51830' \
	'70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1' \
	'eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6' \
	'220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d' \
	'abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a' \
	'6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398' \
	'd3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901' \
	'f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415' \
	'b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008' \
	'29beac5ec4ef88194927283a45427fcc89b95f94c4afa4fda9d6b24301fc9961' \
	'4ddc34b9dace6d11338be71dba16797ff38e8f8e9e572cd61a6b1434c18b59df' \
	'8c97c36eed4dab241bc3353b8f70dc0ece8301fb795362cb129fe331af6c8dc0' \
	'expected_generation_record=cb999cd881959055f32fc1b7299cf1dffcf139656ff8c326ea1101d2ffd63b6d' \
	'expected_avb_salt=5f62ef87305b45de2d189729a601ac4b143c45e83485272ef5b91c508df5d3ee' \
	'expected_avb_digest=32b0de39bd409601da6b8c16bf5039fe9102410d9fb13a8b9f668283d53aee42' \
	'expected_kernel=bb49b4057ce573e3a53366c4663094cf462efb09d496b64b890ed2b0dcb65f98' \
	'expected_raw=27f4dbcc61decd00ce6861cddb021070f38e9badde99152fc2dedbd4103d73b3' \
	'expected_initramfs=99046d30e0910531ebda1163719ae8b5b81489f11329e29e12195fbfd63c6e31' \
	'expected_control=67b4f012aab21e7b29934d3d6e41949aca5e46fdf90e9578ad5f6c87a3f2c167' \
	'expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800' \
	'expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0' \
	'expected_target_id=headless-netroot-early-diag' \
	'expected_bundle_profile=diagnostic-initramfs-v1' \
	'expected_boot_image=build/stable-recovery-generation10-prepare-progress-20260803-a/repack/stable-recovery-a.avb.img' \
	"expected_boot_basis='one generation-10 PREPARE-progress-instrumented diagnostic lifecycle after connected preflight; remove after any result; never flash'" \
	'expected_kernel=8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c' \
	'expected_raw=f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce' \
	'expected_initramfs=144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec' \
	'expected_control=f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77' \
	'expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800' \
	'expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0' \
	'expected_target_id=headless-netroot-early-diag' \
	'expected_bundle_profile=diagnostic-initramfs-v1' \
	'expected_avb_salt=f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce' \
	'expected_avb_digest=6de238c36bd8325d2a6f431f27ee39e5d7bab81d9fe91bd6d3d0bad48ba3c60d' \
	'expected_generation_record=8e537a2eae12c0d58d6a37a23816031f9a1a4e83b37679c3321c60aa688d3dc4' \
	'expected_avb_salt=82fd20a6c16d7e0387568beb0ada378ea513119fa4480064c6afa5b3dfa567f8' \
	'expected_avb_digest=3e8fc9703763bd9572141f909f8e79881dd689ddd3123ec76ce45b13f0708562' \
	'expected_generation_record=7d1a1071df1dcc4172c9f1e28ab5b62d6c44670b21f075f775de587f789cf98f' \
	'expected_avb_salt=818427845bc55deb8167fbb205fb672f2edfb3b465160109dacc0f4d65a9f306' \
	'expected_avb_digest=b1a6bb43d26230e3c623332703998459d51b37fc8244c051287c8291f9e213b0' \
	'expected_generation_record=bff8432e20e01f74132addda464120886c5090b079798054fe359845b1a552a2' \
	'expected_avb_salt=66d5537af0ff592b94ab516306ad03643ee48b15e90e49cb3c990e786031fbe8' \
	'expected_avb_digest=47c517b5c066671b32728076e3b4a5836e839efa9f2ba878659156cffdf0d461' \
	'expected_generation_record=8127197dcf0704bf7bee81a7b25a604fb9e7c9b752ba6d9523e073de2bf9799e' \
	'expected_avb_salt=47daea8fa91810575df6d694bd5e3949eb6295920f7b980eb8935e86950506e4' \
	'expected_avb_digest=5690894d337769a462828bc786de74724abf89115c1e456b8e4064ab6831b86b' \
	'expected_generation_record=9805809c27e1fe47efcbc7561fe5289e81d789beba231acbac59c32a67ae59d5' \
	'expected_avb_salt=a8563ded9a34767ed97ed4f9130361a1b4efadc91ee7294d9a212caf59e53899' \
	'expected_avb_digest=b297100d269798d4eaf46b37899c3cf9196f7c076df3a31d39fe3d2db5915dbc' \
	'expected_generation_record=4a1de575f2c428ae2625e38a37f31fa70850ce64895cf549509434d806e8d109' \
	'expected_avb_salt=8f20854a98ee31fa889c5bfe2b7818ed42c5ed6186b671a55b3f57835c87e712' \
	'expected_avb_digest=903826e0579863b0290004f5f415aecfcee1384f5b81a949ddd8845c880a7541' \
	'profile does not permit an AVB-generation record' \
	'AVB generation descriptor inventory changed' \
	'expected_kernel=7fac4dda6a7133e7d3a6589da4fb5d0bdad3802705da5edf52701a20133728ed' \
	'expected_raw=2f460aa01ee1b97c495d0857b3207bf74920487c56f30c5e155e199967628a01' \
	'expected_initramfs=fec72c4dba62a24ced899af4d4fc3d0af3b7b691ea6f6c1bcf90c7aaf181c57a' \
	'expected_control=f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77' \
	'expected_fetcher=f410ca875031dcf9c41cf2c8a67e5a9fba862cf50b53e1d8c51453f4e0b5d13d' \
	'expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0' \
	'expected_target_id=headless-ssh-network-root' \
	'expected_target_id=headless-netroot-early-diag' \
	'f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b' \
	'457273993a9ce3cb0a9c735ef29e96101c1303720cafefc774aed12972a6926e' \
	'9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630' \
	'4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76' \
	'9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b' \
	'0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621' \
	'expected_bundle=headless-ssh-network-root-v3-r2' \
	'expected_bundle=headless-netroot-early-diag-v1' \
	'expected_bundle_profile=diagnostic-initramfs-v1' \
	'profile requires bundle=$expected_bundle' \
	'profile=$expected_bundle_profile' \
	'target_id=$expected_target_id' \
	'manifests/temporary-boot-images.tsv' \
	'manifests/artifacts.tsv' \
	'temporary boot policy does not uniquely list' \
	'artifact manifest does not uniquely list' \
	'temporary boot artifact manifest identity is not allowlisted' \
	'artifacts/android-boot-tools-v1/avbtool.py' \
	'qualified-cpio-path/cpio' \
	'7520899a405e1fc698875e047d8671c9415116e944831135a8e8eb6a93a21580' \
	'qualified cpio path must contain only the pinned cpio' \
	'component_layout=structured' \
	'cmp "$image" "$twin_image"' \
	'verify-stable-recovery-initramfs.sh' \
	'--bundle-root "$bundle_root"' \
	'verify_image --image "$inspection/recovery.img"' \
	'cp --reflink=never -- "$raw" "$inspection/boot.img"' \
	'getvar product' \
	'verified-fastboot-boot.py' \
	'cmp -n "$raw_size" "$raw" "$image"' \
	'find_rog5_acm ROG5_recovery' \
	'stop ModemManager'
do
	grep -Fq -- "$required" "$gate"
done

artifact_exit=$(
	grep -n 'if \[\[ \$action == artifact-preflight \]\]' "$gate" |
		tail -1 | cut -d: -f1
)
fastboot_devices=$(
	grep -n 'devices 2>/dev/null' "$gate" | cut -d: -f1
)
[[ $artifact_exit =~ ^[0-9]+$ && $fastboot_devices =~ ^[0-9]+$ &&
	$artifact_exit -lt $fastboot_devices ]] ||
	{ echo 'FAIL artifact preflight can reach fastboot inspection' >&2; exit 1; }

# The final pattern is intentionally literal shell source, not an expansion here.
# shellcheck disable=SC2016
for forbidden in ' fastboot flash ' ' fastboot erase ' ' fastboot format ' \
	' fastboot set_active ' '"$fastboot" -s "$fastboot_serial" boot' \
	' adb ' ' ssh '; do
	! grep -Fq -- "$forbidden" "$gate" ||
		{ echo "FAIL live gate contains forbidden action: $forbidden" >&2; exit 1; }
done

echo 'PASS stable-recovery live gate is exact, twin-built, guarded, and boot-only'
