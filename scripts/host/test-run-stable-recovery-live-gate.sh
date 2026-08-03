#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
gate=$repo/scripts/host/run-stable-recovery-live-gate.sh
boot_policy=$repo/manifests/temporary-boot-images.tsv
artifact_manifest=$repo/manifests/artifacts.tsv
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT HUP INT TERM

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
[[ $(awk -F '\t' '$2 == "allow" { count++ } END { print count + 0 }' \
	"$boot_policy") == 1 ]] ||
	{ echo 'FAIL temporary-boot policy must contain exactly one allow row' >&2; exit 1; }
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
	'$1 == name && $2 == "allow" && \
	$3 == "one generation-6 signal-mask-corrected diagnostic lifecycle after connected preflight; remove after any result; never flash" \
	{ count++ } END { print count + 0 }' "$boot_policy") == 1 ]] ||
	{ echo 'FAIL generation-6 temporary-boot admission is not exact and one-shot' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation6_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398" \
	&& $4 == "unbooted generation-6 signal-mask-corrected host diagnostic recovery; deterministic AVB-only successor over the unchanged accepted raw recovery after corrected broker installation; offline issuance record with authority=none; central policy separately admits one RAM-only lifecycle; never flash" \
	&& $5 == "no" { count++ } END { print count + 0 }' \
	"$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL generation-6 admitted artifact identity is not exact' >&2; exit 1; }

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
	'historical diagnostic profile is offline-only and consumed' \
	'generation-3 diagnostic profile is offline-only and not boot-authorized' \
	'generation-3 boot requires the one-shot lifecycle controller' \
	'generation-4 diagnostic profile is offline-only and not boot-authorized' \
	'generation-4 boot requires the one-shot lifecycle controller' \
	'generation-5 diagnostic profile is offline-only and not boot-authorized' \
	'generation-5 boot requires the one-shot lifecycle controller' \
	'generation-6 diagnostic profile is offline-only and not boot-authorized' \
	'generation-6 boot requires the one-shot lifecycle controller' \
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
