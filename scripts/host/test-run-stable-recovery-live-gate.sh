#!/usr/bin/env bash
set -euo pipefail

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
gate=$repo/scripts/host/run-stable-recovery-live-gate.sh

grep -Fq "expected_boot_role='consumed Generation 108 continuous-lifecycle Arch cycle; UFS and read-only userdata mount passed, deployed rog5/images was absent, and restart2 reached slot-A unauthorized recovery because target reboot-mode modules were unavailable; no target write; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 109 cycle; repeated userdata-rog5-directory after exact restage, proved built-in PMK8350 reboot-mode return to fastboot, no target write; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 110 discriminator; proved ABL sparse userdata flash is ineffective, exact fastboot fallback, no target write; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 111 controlled staging cycle; target USB never appeared, slot-A unauthorized recovery returned after 30.708 seconds, and no SSH transfer or storage write occurred; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 112 hotplug-guard cycle; immediate controlled pre-gadget fastboot fallback in 6.903 seconds, no target USB, SSH, transfer, installer, or storage write; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 113 timing discriminator; 31.910-second exact fastboot return proved both release and command-line checks pass; no gadget, UFS, storage, SSH, or payload surface; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 114 USB-mode parity cycle; absent guarded mode path changed no runtime behavior, immediate 6.903-second fastboot fallback, no USB or storage write; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 115 ConfigFS beacon; 51.961-second return selected UDC-identity branch, expected a600000.usb plus extra candidate, no gadget binding or storage; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 116 early UDC inventory; no-extra-yet at early sample proves late candidate race when combined with Generation 115; no binding, gadget, or storage; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 117 stabilized UDC inventory; no extra after five seconds proves ConfigFS-window transient with Generation 115; no binding, gadget, or storage; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 118 NCM-only full staging cycle; target USB never appeared, exact slot-A fastboot and FALLBACK_RETURNED resolution passed, no SSH transfer, installer, or storage write; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 119 pre-storage timing discriminator; 77.046-second exact USB timeline selected ncm-address; no target USB, UFS, userdata, SSH, installer, or storage write; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 120 usb0 address-state discriminator; 77.045-second exact USB timeline selected address-show-failed immediately after link-up; no target USB or later subsystem/storage surface; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 121 pre-bind-mdev full staging cycle; 31.992-second return with no target USB, SSH, installer, or storage write; fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 122 explicit-sysfs full staging cycle; exact 31.992-second return selected UDC identity timeout; no target USB, SSH, installer, or storage write; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 123 post-ConfigFS UDC inventory classifier; proved zero/exact a600000.usb churn with no unexpected UDC; no bind, network, or storage surface; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 124 two-sample exact-UDC full staging cycle; no two consecutive samples, no target USB, SSH, installer, or storage write; fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 125 scan-then-bind full staging cycle; 25-second bind timeout, no target USB, SSH, installer, or storage write; fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 126 direct-bind full staging cycle; bind write refused with expected path present, no target USB or storage write; fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 127 classifier; ConfigFS/NCM bind succeeded and target USB persisted for 89.864 seconds; host R7 model-filter defect prevented target acceptance; no storage write; slot-A fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 128 full staging cycle; immediate false post-bind UDC-class invariant forced fallback before target USB or storage; exact slot-A fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 129 full staging cycle; exact target NCM enumerated for 0.519517 seconds, then target rollback before host activation; no storage write; slot-A fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 130 cycle; target NCM/reporter dwell passed but host used the SSH-only helper and missed stage detail; no storage write; slot-A fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 131 cycle; exact stage detail proved qcom_q6v5 module vermagic mismatch before UFS or storage; slot-A fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 132 cycle; g359 power/USB modules passed, UFS modules loaded, then bounded UFS inventory count failed before storage; slot-A fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 133 cycle; exact post-module UFS physical count was zero before every storage surface; slot-A fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 134 cycle; exact classifier proved no runtime UFS platform device before every storage surface; slot-A fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 135 cycle; runtime UFS DT was okay but address-name platform scan returned zero before storage; slot-A fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 136 cycle; exact OF identity confirmed no UFS platform device under the current Image/DT pair; slot-A fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 137 cycle; live-proven g359 target still reported ufs-count-0; exact stock slot-A recovery fallback passed after the current descriptor policy correction; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 138 cycle; ae717 target still reported ufs-count-0 because minimal init omitted the packaged power/USB loader; exact fastboot fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 139 cycle; power/USB passed but set -f suppressed every UFS sysfs glob and falsely reported zero; exact fastboot fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 140 cycle; power/USB and complete 116-node UFS topology passed; exact fastboot fallback passed; no write; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 141 cycle; UFS passed but sealed nologin blocked SSH before transfer or write; bounded fallback; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 142 cycle; transient host NetworkManager ownership gap before target activation; no stage, transfer, or write; exact fastboot fallback; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 143 cycle; redundant post-COMMIT cleanup delayed target activation; no stage, transfer, or write; exact fastboot fallback; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 144 cycle; immediate activation and UFS passed, then uninstrumented pre-SSH failure; no transfer or write; exact fastboot fallback; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 145 cycle; runtime nologin-identity failed on absent member; no SSH, transfer, or write; exact fastboot fallback; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 146 cycle; key-only SSH and exact gzip transfer passed, then installer set -f suppressed userdata/relock globs and failed before creating an image path; exact fastboot fallback; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 147 cycle; UFS, SSH, transfer, and installer glob passed, then parent-child read-write transition remained effectively read-only; no mount or image path; fastboot fallback; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 148 cycle; exact disk-rw-state proved the deployed ae717 Image is compile-time read-only; no mount or image path; fastboot fallback; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 149 cycle; bounded-write kernel worked, but dense 16 GiB decompression reached about 826 MB then UFS I/O stalled in D state; emergency exact fastboot fallback; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 150 cycle; post-crash partial metadata differed from the exact pre-crash tuple, so no benchmark write ran; exact fastboot fallback; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 151 cycle; partial exceeded the transient 825884672-byte snapshot while prior D-state I/O drained, so no benchmark write ran; exact fastboot fallback; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 152 cycle; partial-identity still failed under the full logical-size bound, proving another metadata field differs; no benchmark write; exact fastboot fallback; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 153 read-only cycle; partial is regular root-owned mode 0644 one link with zero size and zero blocks; final absent; exact fastboot fallback; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 154 cycle; direct 32 MiB passed in 50.25 seconds, buffered fsync blocked, sync-independent rollback returned exact fastboot; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 155 cycle; prepare failed before extent streaming and the old host discarded its reason; exact fastboot fallback; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 156 cycle; prepare and extent 1 passed, 4 KiB O_DIRECT throughput was impossible within watchdog, controlled SSH/HUP returned fastboot; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 157 cycle; 1 MiB writes remained 0.66 MiB/s, proving UFS/transport fixed-bandwidth limit; controlled fallback passed; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='consumed Generation 158 cycle; UFS high-speed fixed throughput and exact 16 GiB image publish completed; target PASS, host CRLF-only misclassification, exact fastboot; never retry or flash'" "$gate"
grep -Fq "expected_boot_role='unbooted Generation 159 read-only staged-seal local Arch runtime acceptance; RAM-only, never flash'" "$gate"
generated_power=$repo/scripts/host/generated-power-usb-active.sh
source "$generated_power"
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
generation10_boot_basis='one generation-10 PREPARE-progress-instrumented diagnostic lifecycle after connected preflight; remove after any result; never flash'
generation10_root_a=$repo/build/stable-recovery-generation10-prepare-progress-20260803-a
generation10_root_b=$repo/build/stable-recovery-generation10-prepare-progress-20260803-b
generation10_base=$repo/build/prepare-progress-generation10-production-base-20260803
generation11_image=build/stable-recovery-generation11-ncm-progress-20260804-a/repack/stable-recovery-a.avb.img
generation11_boot_basis='one generation-11 receive-only NCM-progress diagnostic lifecycle after connected preflight; remove after any result; never flash'
generation11_root_a=$repo/build/stable-recovery-generation11-ncm-progress-20260804-a
generation11_root_b=$repo/build/stable-recovery-generation11-ncm-progress-20260804-b
generation11_base=$repo/build/generation11-ncm-progress-production-base-20260804
generation11_bundle_base=$generation10_base
generation12_image=build/stable-recovery-generation12-host-confinement-fix-20260804-a/repack/stable-recovery-a.avb.img
generation12_boot_basis='one generation-12 host-confinement-corrected diagnostic lifecycle after connected preflight; remove after any result; never flash'
generation12_consumed_role='consumed generation-12 host-confinement-corrected diagnostic recovery; one RAM-only lifecycle transferred the exact 46163787-byte signed bundle and recovery accepted correlated PREPARE and COMMIT; receive-only target evidence reached stage 70 nfs-mount-begin, then USB disconnected before stage 80 nfs-mount-ok with no terminal fault frame; the lifecycle host parser separately misclassified the valid postmortem-extended PREPARE response after commit, then the durable intent resolved FALLBACK_RETURNED; exact Alpine fallback, strict SSH, profile restoration, final host cleanup, and Steam socket restoration passed; no target acceptance; retain offline only; never retry or flash'
generation12_root_a=$repo/build/stable-recovery-generation12-host-confinement-fix-20260804-a
generation12_root_b=$repo/build/stable-recovery-generation12-host-confinement-fix-20260804-b
generation12_base=$generation11_base
generation12_bundle_base=$generation11_bundle_base
stage75_v2_root=$repo/build/stage75-v2-offline-20260805-a
[[ -f $boot_policy && ! -L $boot_policy && -r $boot_policy ]] ||
	{ echo 'FAIL unsafe or missing committed temporary-boot policy' >&2; exit 1; }
awk -F '\t' \
	-v power_name="$POWER_USB_OUTPUT_ROOT/wrapper/repack/stable-recovery-a.avb.img" \
	-v power_basis="$POWER_USB_BOOT_POLICY_BASIS" '
	NR == 1 {
		if ($1 != "name" || $2 != "status" || $3 != "basis" || NF != 3)
			exit 1
		next
	}
	$1 == "build/observation-recovery-mainline-udc-v11-generation10-20260811-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 111 postmortem observation; recovery reported EMPTY pstore with zero records and bytes, then exact-path stock recovery returned; absence remains inconclusive; never retry or flash" && NF == 3 { observer++ ; next }
	$1 == "build/observation-recovery-mainline-udc-v11-generation11-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 118 postmortem observation; one retained record exposed only the prior ASUS recovery kexec shutdown tail and no target lineage, so target failure remains unclassified; no payload or storage surface; never retry or flash" && NF == 3 { observer118++ ; next }
	$1 == "build/headless-core-v21-generation21-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "allow" &&
		$3 == "one exact headless-core Arch SSH recovery with power-key indicator; RAM-only; externally consumed exact claim required; never flash or retry after entry" && NF == 3 { core++ ; next }
	$1 == power_name && $2 == "allow" && $3 == power_basis && NF == 3 {
		power_usb++ ; next
	}
	$1 ~ /^build\/power-usb-observer-v[0-9]+-offline-r1\/wrapper\/repack\/stable-recovery-a[.]avb[.]img$/ &&
		$2 == "revoked" &&
		 (($3 ~ /^consumed by the sole v[0-9]+ RAM-only cycle;/ &&
		  $3 ~ /never retry or flash$/) ||
		 ($3 ~ /^unbooted .* superseded before execution/ &&
		  $3 ~ /never boot or flash$/) ||
		 ($3 ~ /^unbooted offline R2 composition failure:/ &&
		  $3 ~ /no claim or phone boot occurred; never boot or flash$/)) &&
		NF == 3 { power_history++ ; next }
	$1 == "build/local-image-stage-v1-generation101-20260823-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 101 RAM-only cycle; signed transfer, PREPARE, and COMMIT passed, but the replacement minimal target init produced no observable NCM/ACM before stock slot-A return; no staging SSH command or image write occurred; never retry or flash" &&
		NF == 3 { local_stage++ ; next }
	$1 == "build/persistent-root-power-usb-v9-generation102-20260823-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 102 RAM-only cycle; target NCM/ACM enumerated for 15 seconds, but the newly rebuilt image lacks the exact prior-write probe required by V9 read-only init, so this composition cannot complete; no target storage write occurred; never retry or flash" &&
		NF == 3 { local_boot++ ; next }
	$1 == "build/persistent-root-power-usb-v10-generation103-20260823-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 103 RAM-only cycle; target NCM stayed reachable for 60 seconds, but V10 paired local-write userspace with the deliberately read-only V8 UFS kernel and therefore cannot pass the exact ufs-power containment gate; no probe or target write occurred; never retry or flash" &&
		NF == 3 { local_write_boot++ ; next }
	$1 == "build/persistent-root-local-image-probe-writer-v11-generation104-20260823-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 104 RAM-only cycle; target NCM appeared for 14 seconds and returned through stock slot A, matching the historical post-probe UFS-health rollback, but the host attached after departure so probe success remains unconfirmed; never retry or flash" &&
		NF == 3 { probe_writer++ ; next }
	$1 == "build/persistent-root-local-image-any-prior-v12-generation105-20260823-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 105 RAM-only cycle; target NCM appeared for 19 seconds and returned before Arch, but manual multi-call orchestration again attached the host after departure, so the exact probe verdict is unavailable; no target write occurred; never retry or flash" &&
		NF == 3 { marker_reader++ ; next }
	$1 == "build/persistent-root-local-image-any-prior-v13-generation106-20260823-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 106 continuous lifecycle; host network and stage listener were ready two seconds after target NCM, but the target emitted zero stages and rolled back after exactly 20 seconds because the early policy gate still rejected any-prior; no target write occurred; never retry or flash" &&
		NF == 3 { continuous_reader++ ; next }
	$1 == "build/persistent-root-local-image-any-prior-v14-generation107-20260823-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "unbooted Generation 107 was superseded before admission by restart2-first rollback; never boot, retry, or flash" &&
		NF == 3 { early_fixed_reader++ ; next }
	$1 == "build/persistent-root-local-image-restart2-v15-generation108-20260823-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 108 RAM-only cycle; target reached UFS and mounted userdata read-only, then proved the deployed filesystem lacks the required rog5/images tree; restart2 rebooted, but absent target reboot-mode modules left the Qualcomm bootloader reason unset and slot A entered unauthorized recovery ADB; no target storage write occurred; R2/R3/R8; never retry or flash" &&
		NF == 3 { restart_reader++ ; next }
	$1 == "build/persistent-root-local-image-reboot-mode-v16-generation109-20260823-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 109 RAM-only cycle after exact userdata restaging; target again mounted ext4 read-only but lacked rog5/images, while the built-in PMK8350 reboot-mode path returned exact fastboot; no target storage write occurred; never retry or flash" &&
		NF == 3 { reboot_mode_reader++ ; next }
	$1 == "build/persistent-root-sparse-diagnostic-v17-generation110-20260823-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 110 read-only cycle; source metadata blocks differed, high inode and directory blocks were zero, and 4-GiB aliases remained unchanged, proving ASUS ABL sparse flash left userdata unchanged; exact fastboot fallback passed; no target write; never retry or flash" &&
		NF == 3 { sparse_reader++ ; next }
	$1 == "build/local-image-stage-writer-v2-generation111-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 111 cycle; recovery departed after COMMIT, no target USB appeared, and exact slot-A unauthorized recovery returned 30.708 seconds later; no SSH transfer or storage write occurred; never retry or flash" &&
		NF == 3 { stage_writer++ ; next }
	$1 == "build/local-image-stage-hotplug-v3-generation112-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 112 cycle; guarded hotplug advanced to an immediate controlled pre-gadget failure, exact fastboot returned 6.903 seconds after recovery USB departure, and no storage write occurred; never retry or flash" &&
		NF == 3 { hotplug_writer++ ; next }
	$1 == "build/local-image-stage-preusb-v4-generation113-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 113 timing cycle; exact fastboot returned 31.910 seconds after recovery departure, proving the 25-second both-checks-pass path plus 6.9-second overhead; no USB or storage surface; never retry or flash" &&
		NF == 3 { preusb_writer++ ; next }
	$1 == "build/local-image-stage-usbmode-v5-generation114-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 114 cycle; guarded mainline-absent mode path was a no-op, exact fastboot repeated after 6.903 seconds before target USB, and no storage write occurred; never retry or flash" &&
		NF == 3 { usbmode_writer++ ; next }
	$1 == "build/local-image-stage-configfs-v6-generation115-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 115 beacon; exact fastboot returned 51.961 seconds after recovery departure, selecting the 45-second UDC-identity branch: expected UDC exists but additional candidate present; no storage; never retry or flash" &&
		NF == 3 { configfs_writer++ ; next }
	$1 == "build/local-image-stage-udc-v7-generation116-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 116 early inventory; exact fastboot returned in 16.887 seconds, selecting no-extra-yet and proving the additional UDC appears asynchronously after expected registration; no binding/storage; never retry or flash" &&
		NF == 3 { udc_writer++ ; next }
	$1 == "build/local-image-stage-udc-stable-v8-generation117-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 117 stabilized inventory; exact fastboot returned in 21.750 seconds, again selecting no-extra after five seconds and proving the transient appears during ConfigFS NCM+ACM setup; no binding/storage; never retry or flash" &&
		NF == 3 { stable_udc_writer++ ; next }
	$1 == "build/local-image-stage-ncm-v9-generation118-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 118 NCM-only full staging cycle; recovery transfer and COMMIT passed, target NCM never appeared, exact slot-A fastboot returned, no SSH transfer or storage write occurred, and intent resolved FALLBACK_RETURNED; never retry or flash" &&
		NF == 3 { stage_ncm++ ; next }
	$1 == "build/local-image-stage-timing-v10-generation119-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 119 pre-storage timing cycle; exact 77.046-second recovery-departure-to-fastboot interval selected ncm-address after subtracting the 6.903-second immediate-return baseline; no target USB, UFS, userdata, SSH, installer, or storage write; never retry or flash" &&
		NF == 3 { timing_writer++ ; next }
	$1 == "build/local-image-stage-address-v11-generation120-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 120 address-state cycle; exact 77.045-second USB timeline selected address-show-failed, proving usb0 vanished or became unqueryable immediately after link-up; no target USB, carrier, power-USB, UFS, userdata, SSH, installer, or storage; never retry or flash" &&
		NF == 3 { address_writer++ ; next }
	$1 == "build/local-image-stage-prebind-v12-generation121-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 121 pre-bind-mdev cycle; exact 31.992-second return, no target USB, SSH, installer, or storage write; moving the second global mdev scan before bind did not fix enumeration; fallback and intent resolution passed; never retry or flash" &&
		NF == 3 { prebind_writer++ ; next }
	$1 == "build/local-image-stage-explicit-v13-generation122-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 122 explicit-sysfs cycle; exact 31.992-second return selected the 25-second UDC identity timeout plus restart overhead; no target USB, SSH, installer, or storage write; fallback and intent resolution passed; never retry or flash" &&
		NF == 3 { explicit_writer++ ; next }
	$1 == "build/local-image-stage-configfs-udc-v14-generation123-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 123 post-ConfigFS inventory cycle; exact 107.256-second return selected 25-second inventory window plus seen-zero delay, proving zero/exact a600000.usb churn with no unexpected UDC; no bind, network, or storage; never retry or flash" &&
		NF == 3 { post_configfs_udc++ ; next }
	$1 == "build/local-image-stage-two-sample-v15-generation124-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 124 two-sample UDC cycle; exact 32.248-second return selected the 25-second UDC timeout, proving no two consecutive 100ms exact samples; no target USB, SSH, installer, or storage write; fallback passed; never retry or flash" &&
		NF == 3 { two_sample_writer++ ; next }
	$1 == "build/local-image-stage-bind-v16-generation125-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 125 scan-then-bind cycle; exact 32.504-second return selected the 25-second bind timeout, no target USB, SSH, installer, or storage write; full inventory scan remained too slow for the transient expected UDC; fallback passed; never retry or flash" &&
		NF == 3 { bind_writer++ ; next }
	$1 == "build/local-image-stage-direct-v17-generation126-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 126 direct-bind cycle; exact 6.901-second immediate return proved the exact UDC bind write was refused while the expected path remained present; no target USB, SSH, installer, or storage write; fallback passed; never retry or flash" &&
		NF == 3 { direct_writer++ ; next }
	$1 == "build/local-image-stage-bind-error-v18-generation127-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 127 bind classifier; target NCM enumerated for 89.864 seconds, selecting bind-success; the host then filtered ROG5_local_image_stage from shared NCM inventory and missed the target; no target network configuration or storage write; exact slot-A fallback passed; never retry or flash" &&
		NF == 3 { bind_error_writer++ ; next }
	$1 == "build/local-image-stage-hostfix-v19-generation128-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 128 full staging cycle; exact 6.903960-second recovery-departure-to-slot-A-fastboot return proves immediate post-bind failure before target USB, SSH, installer, or storage; Linux 7.1 ConfigFS store semantics and prior empty/exact class oscillation identify the post-bind UDC-class level check as false; never retry or flash" &&
		NF == 3 { hostfix_writer++ ; next }
	$1 == "build/local-image-stage-postbind-v20-generation129-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 129 full staging cycle; removing the false UDC-class check advanced to exact target NCM enumeration for 0.519517 seconds, then target rollback before host activation; no SSH, installer, or storage write; exact slot-A fallback passed; never retry or flash" &&
		NF == 3 { postbind_writer++ ; next }
	$1 == "build/local-image-stage-power-report-v21-generation130-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 130 cycle; exact target NCM stayed up for 10.506 seconds and the reporter dwell executed, but the host called the SSH-only helper and never opened the existing stage listener; exact slot-A fallback passed, no SSH, installer, or storage write; never retry or flash" &&
		NF == 3 { power_report_writer++ ; next }
	$1 == "build/local-image-stage-listener-v22-generation131-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 131 cycle; exact stage listener captured power-usb/module-qcom-q6v5-load, proving the packaged module vermagic 7.1.4-gae717d919f87 mismatched target 7.1.4-g359318de534f; no UFS, SSH, installer, or storage write; exact slot-A fallback passed; never retry or flash" &&
		NF == 3 { listener_writer++ ; next }
	$1 == "build/local-image-stage-abi-v23-generation132-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 132 cycle; exact g359 power/USB module chain passed and UFS modules loaded, then stage ufs-ready failed at generic ufs-count after the bounded 20-second enumeration wait; no SSH, installer, or storage write; exact slot-A fallback passed; never retry or flash" &&
		NF == 3 { abi_writer++ ; next }
	$1 == "build/local-image-stage-ufs-count-v24-generation133-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 133 cycle; exact g359 power/USB and UFS module insertion passed, then the bounded UFS inventory was exactly zero; no SSH, installer, block device, mount, or storage write; exact slot-A fallback passed; never retry or flash" &&
		NF == 3 { ufs_count_writer++ ; next }
	$1 == "build/local-image-stage-ufs-bind-v25-generation134-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 134 cycle; exact zero-UFS classifier reported ufs-platform-0, proving no runtime platform device matched the 0x1d84000 controller address; no SCSI host, block device, mount, SSH, installer, or storage write; exact slot-A fallback passed; never retry or flash" &&
		NF == 3 { ufs_bind_writer++ ; next }
	$1 == "build/local-image-stage-runtime-dt-v26-generation135-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 135 cycle; runtime UFS DT node existed with exact okay status, while the address-name platform scan found zero candidates; no SCSI host, block, mount, SSH, installer, or storage write; exact slot-A fallback passed; never retry or flash" &&
		NF == 3 { runtime_dt_writer++ ; next }
	$1 == "build/local-image-stage-of-node-v27-generation136-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 136 cycle; exact of_node platform matching still reported ufs-dt-okay-platform-0, proving the current g359 Image/DT pair creates no UFS platform device; no SCSI, block, mount, SSH, installer, or storage write; exact slot-A fallback passed; never retry or flash" &&
		NF == 3 { of_node_writer++ ; next }
	$1 == "build/ufs-baseline-proven-v28-generation137-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 137 cycle; exact live-proven g359 Image, DTB, and four modules still reported ufs-count-0 after stable NCM and a bounded 20-second wait; no storage surface or write; exact slot-A stock recovery USB returned and passed after the current descriptor policy correction; never retry or flash" &&
		NF == 3 { proven_ufs_writer++ ; next }
	$1 == "build/ufs-reboot-baseline-v29-generation138-20260824-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 138 cycle; exact ae717 Image, DTB, and four UFS modules still reported ufs-count-0 because the minimal init omitted the packaged power/USB dependency loader; built-in reboot mode returned exact fastboot; no storage surface or write; never retry or flash" &&
		NF == 3 { proven_ufs_reboot_writer++ ; next }
	$1 == "build/ufs-power-reboot-baseline-v30-generation139-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 139 cycle; the exact power/USB loader passed but UFS still falsely reported count zero because `set -f` disabled every fixed sysfs glob in the minimal init; built-in reboot mode returned exact fastboot; no storage surface or write; never retry or flash" &&
		NF == 3 { proven_power_ufs_writer++ ; next }
	$1 == "build/ufs-glob-reboot-baseline-v31-generation140-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 140 cycle; exact power/USB and corrected sysfs discovery proved the complete 116-node UFS topology, then built-in reboot mode returned exact fastboot; no mount or storage write; never retry or flash" &&
		NF == 3 { proven_glob_ufs_writer++ ; next }
	$1 == "build/local-image-stage-glob-v32-generation141-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 141 cycle; power/USB and UFS passed and target host key was pinned, but zero-byte `/etc/nologin` blocked OpenSSH before authentication; no image transfer, installer, mount, or storage write; bounded watchdog fallback; never retry or flash" &&
		NF == 3 { local_glob_writer++ ; next }
	$1 == "build/local-image-stage-ssh-v33-generation142-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 142 cycle; post-COMMIT cleanup hit a transient NetworkManager ownership gap on newly enumerated target NCM before target activation, no target stage/SSH/transfer/installer/write evidence, exact fastboot fallback and cleanup passed; never retry or flash" &&
		NF == 3 { local_ssh_writer++ ; next }
	$1 == "build/local-image-stage-nm-v34-generation143-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 143 cycle; NetworkManager ownership classification no longer aborted, but redundant post-COMMIT host cleanup delayed target activation until it returned fastboot before host-key readiness; no stage/transfer/installer/write; fallback passed; never retry or flash" &&
		NF == 3 { local_nm_writer++ ; next }
	$1 == "build/local-image-stage-fast-v35-generation144-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 144 cycle; immediate activation worked and UFS passed, then an uninstrumented post-UFS pre-SSH failure returned exact fastboot; no transfer, installer, mount, or write; fallback and cleanup passed; never retry or flash" &&
		NF == 3 { local_fast_writer++ ; next }
	$1 == "build/local-image-stage-stages-v36-generation145-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 145 cycle; power/UFS, userdata identity, and storage lock passed, runtime failed exact nologin-identity because the member was absent rather than empty; no SSH/transfer/installer/write; fastboot fallback passed; never retry or flash" &&
		NF == 3 { local_stages_writer++ ; next }
	$1 == "build/local-image-stage-auth-v37-generation146-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 146 cycle; exact UFS, key-only SSH, and gzip transfer passed, then installer set -f suppressed its userdata and relock globs and failed before creating an image path; exact fastboot fallback and cleanup passed; never retry or flash" &&
		NF == 3 { local_auth_writer++ ; next }
	$1 == "build/local-image-stage-globfix-v38-generation147-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 147 cycle; exact UFS, key-only SSH, transfer, and installer glob passed, then exact write-window failed before mount or image creation because the child was cleared before its read-only parent; fastboot fallback and cleanup passed; never retry or flash" &&
		NF == 3 { local_globfix_writer++ ; next }
	$1 == "build/local-image-stage-rworder-v39-generation148-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 148 cycle; exact UFS, SSH, and transfer passed, then disk-rw-state proved the deployed ae717 Image lacks bounded data-write support; no mount or image path; fastboot fallback and cleanup passed; never retry or flash" &&
		NF == 3 { local_rworder_writer++ ; next }
	$1 == "build/local-image-stage-writekernel-v40-generation149-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 149 cycle; write-capable UFS, SSH, and transfer passed, dense decompression created about 826 MB of the bounded partial file, then gzip and sync entered uninterruptible UFS I/O; exact bootloader fallback required the sealed restart reason plus emergency SysRq; never retry or flash" &&
		NF == 3 { local_writekernel_writer++ ; next }
	$1 == "build/local-image-write-benchmark-v41-generation150-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 150 cycle; UFS and SSH passed, then the benchmark rejected post-crash partial metadata before creating its benchmark directory or writing data; exact fastboot fallback and cleanup passed; never retry or flash" &&
		NF == 3 { local_write_benchmark++ ; next }
	$1 == "build/local-image-write-benchmark-v42-generation151-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 151 cycle; the bounded partial continued growing after the earlier snapshot and exceeded 825884672 bytes, so no benchmark directory or data write occurred; exact fastboot fallback and cleanup passed; never retry or flash" &&
		NF == 3 { local_write_benchmark_v42++ ; next }
	$1 == "build/local-image-write-benchmark-v43-generation152-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 152 cycle; partial-identity still failed under the full logical-image size bound, proving type, owner, mode, link count, or another field differs; no benchmark directory or write; exact fastboot fallback and cleanup passed; never retry or flash" &&
		NF == 3 { local_write_benchmark_v43++ ; next }
	$1 == "build/local-image-partial-inspect-v44-generation153-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 153 read-only cycle; exact evidence proves the partial is regular root-owned mode 0644 one link with size zero and zero allocated blocks, final absent, and parent directories exact; no phone write; fastboot fallback passed; never retry or flash" &&
		NF == 3 { local_partial_inspect++ ; next }
	$1 == "build/local-image-write-benchmark-v45-generation154-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 154 cycle; direct 32 MiB completed in 50.25 seconds, buffered fsync remained blocked past its 180-second bound, and the sync-independent timer returned exact slot-A fastboot; candidate resolved FALLBACK_RETURNED; never retry or flash" &&
		NF == 3 { local_write_benchmark_v45++ ; next }
	$1 == "build/local-image-direct-v46-generation155-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 155 cycle; target reached runtime and key-only SSH, then prepare failed before any extent stream; host discarded the bounded target reason; exact fastboot fallback and cleanup passed; resolved FALLBACK_RETURNED; never retry or flash" &&
		NF == 3 { local_direct_stage++ ; next }
	$1 == "build/local-image-direct-v47-generation156-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 156 cycle; prepare passed and extent 1 completed, but 4 KiB O_DIRECT made extent 2 run at about 0.6 MiB/s; operator ended the impossible-within-watchdog stream through SSH/HUP; exact fastboot fallback and cleanup passed; never retry or flash" &&
		NF == 3 { local_direct_successor++ ; next }
	$1 == "build/local-image-direct-v48-generation157-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 157 cycle; prepare and extents 1-2 completed, but 1 MiB O_DIRECT remained about 0.66 MiB/s, proving syscall size was not the bottleneck; operator ended extent 3 through SSH/HUP; exact fastboot fallback and cleanup passed; never retry or flash" &&
		NF == 3 { local_direct_megabyte++ ; next }
	$1 == "build/local-image-direct-v49-generation158-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 158 cycle; high-speed UFS branch executed, all 37 extents staged, fsync/e2fsck/publish/unmount/relock and target final PASS completed in about 92 seconds after SSH; host rejected only the known trailing timeout CRLF; exact fastboot fallback passed; never retry or flash" &&
		NF == 3 { local_high_speed++ ; next }
	$1 == "build/persistent-root-local-v50-generation159-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 159 cycle; target NCM appeared but no stage arrived before slot-A stock recovery, proving failure before UFS reporter; ae717 reboot-mode drivers were modular and absent from initramfs; no storage write; never retry or flash" &&
		NF == 3 { local_runtime++ ; next }
	$1 == "build/persistent-root-local-v51-generation160-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 160 cycle; target persistent-root NCM enumerated for 23 seconds, but the host selected the obsolete local-image-stage product and never activated networking; no storage write; exact slot-A fastboot fallback passed; never retry or flash" &&
		NF == 3 { local_runtime_successor++ ; next }
	$1 == "build/persistent-root-local-v52-generation161-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 161 cycle; reboot-mode, charging/UFS, userdata, and image mount passed, then staged-seal was rejected by an unreachable-policy control-flow defect at root-verify; no storage write; exact fastboot fallback passed; never retry or flash" &&
		NF == 3 { local_runtime_observer++ ; next }
	$1 == "build/persistent-root-local-v53-generation162-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 162 cycle; local Arch, power/USB, read-only UFS, OverlayFS, systemd, runtime attestation, and key-only SSH passed in 325.697 seconds; exitrd omitted its restart2 helper and systemctl reboot returned stock recovery; never retry or flash" &&
		NF == 3 { local_runtime_sealfix++ ; next }
	$1 == "build/persistent-root-local-v54-generation163-20260825-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 163 cycle; local Arch, read-only UFS, OverlayFS, systemd, power/NCM, runtime attestation, key-only SSH, exitrd restart2, and exact slot-A fastboot passed in 338.141 seconds; never retry or flash" &&
		NF == 3 { local_runtime_exitrd++ ; next }
	$1 == "build/storage-layout-stage2-mainline-readonly-v1-generation191-20260826-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 191 cycle; historical V54 recovery expected pre-Stage-1 userdata/topology and returned before ACM on the current 117-node p23/p24 layout; target bundle never executed, no storage write, stock slot-A recovery returned; never retry or flash" &&
		NF == 3 { stage2_mainline++ ; next }
	$1 == "build/storage-layout-stage2-mainline-readonly-v2-generation192-20260826-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 192 cycle; mainline runtime passed at 254 seconds with 117 physical nodes, two read-only backing mounts, strict SSH and zero UFS errors, but host acceptance still required stale physical_blocks=116; exact fallback and intent resolution passed; no p24 write; never retry or flash" &&
		NF == 3 { stage2_mainline_v2++ ; next }
	$1 == "build/storage-layout-stage2-mainline-readonly-v3-generation193-20260826-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed successful Generation 193 read-only cycle; exact p23/p24, 117 read-only nodes, local Arch/systemd/strict SSH, 30.1 C battery, +312 mA USB input, 39.5 C max thermal, zero UFS errors, and exact fastboot passed in 339.080 seconds; no p24 write; never retry or flash" &&
		NF == 3 { stage2_mainline_v3++ ; next }
	$1 == "build/storage-layout-stage2-mainline-clone-v1-generation194-20260826-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 194 cycle; mainline reached exact UFS/NCM/SSH, then the redundant 16 GiB source hash stalled UFS and NCM before any observed clone-WRITE marker; host NCM watchdog timed out, rollback returned exact fastboot after 19m31s, intent remains UNKNOWN, and p24 disposition requires read-only proof; never retry or flash" &&
		NF == 3 { stage2_clone++ ; next }
	$1 == "build/storage-layout-stage2-native-postmortem-v1-generation195-20260826-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed successful Generation 195 read-only p24 postmortem; exact 117-node UFS and key-only SSH passed, p24 classified non-ext4 with first 4 MiB exactly zero-filled, target and exact slot-A fastboot proofs passed, intent resolved TARGET_ACCEPTED; never retry or flash" &&
		NF == 3 { stage2_postmortem++ ; next }
	$1 == "build/storage-layout-stage2-mainline-clone-v2-generation196-20260826-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed Generation 196 prewrite watchdog probe; exact UFS passed, qcom-wdt load/open advanced to the optional timeout-sysfs check, then failed closed because CONFIG_WATCHDOG_SYSFS is disabled; no p24 write, exact slot-A fastboot and intent fallback resolution passed; never retry or flash" &&
		NF == 3 { stage2_clone_v2++ ; next }
	$1 == "build/storage-layout-stage2-mainline-clone-v3-generation197-20260826-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed Generation 197 prewrite watchdog probe; exact UFS passed but the remaining generic hardware-watchdog predicate failed, no p24 write occurred, exact slot-A fastboot and fallback intent resolution passed; never retry or flash" &&
		NF == 3 { stage2_clone_v3++ ; next }
	$1 == "build/storage-layout-stage2-watchdog-probe-v1-generation198-20260826-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 198 read-only cycle; the watchdog armed and target emitted storage-locked, but the host parser allowed only the nonexistent storage-relock spelling; the 900-second target fallback returned exact slot-A fastboot at the host deadline, no p24 write path was packaged, and intent resolved FALLBACK_RETURNED; never retry or flash" &&
		NF == 3 { stage2_watchdog_probe++ ; next }
	$1 == "build/storage-layout-stage2-mainline-clone-v4-generation199-20260827-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed Generation 199 prewrite watchdog-lifetime failure; mainline UFS/NCM/runtime/key-only SSH passed in 7.86 seconds, then the watchdog process was absent before source verification or any p24 write window; exact slot-A fastboot and FALLBACK_RETURNED resolution passed; never retry or flash" &&
		NF == 3 { stage2_clone_v4++ ; next }
	$1 == "build/storage-layout-stage2-watchdog-lifetime-v1-generation200-20260827-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed successful Generation 200 read-only watchdog lifetime probe; runtime at 7.90 seconds proved qcom_wdt, class and device absent, BusyBox failed ENOENT opening watchdog0, and dmesg proved struct-module ABI size mismatch; exact fastboot and TARGET_ACCEPTED resolution passed; never retry or flash" &&
		NF == 3 { stage2_watchdog_lifetime++ ; next }
	$1 == "build/storage-layout-stage2-watchdog-lifetime-v2-generation201-20260827-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed Generation 201 watchdog-reset cycle; exact-ABI qcom_wdt arming produced no reporter frame, NCM TX timeout at 11 seconds, target USB loss at 13 seconds and stock slot-A recovery return; no storage write path, FALLBACK_RETURNED resolved; never retry or flash" &&
		NF == 3 { stage2_watchdog_runtime_abi++ ; next }
	$1 == "build/storage-layout-stage2-watchdog-observer-v1-generation202-20260827-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed Generation 202 inherited-watchdog timing proof; MMIO-read-only observer made no watchdog write, yet target NCM disconnected at 12 seconds and stock slot-A recovery returned, proving the watchdog was armed before mainline; no reporter frame or storage writes, FALLBACK_RETURNED resolved; never retry or flash" &&
		NF == 3 { stage2_watchdog_observer++ ; next }
	$1 == "build/storage-layout-stage2-watchdog-observer-v2-generation203-20260827-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed Generation 203 early module observer; NCM still timed out and target reset before any stage frame, proving external module relocation/probe is too slow for inherited watchdog deadline; no MMIO or storage writes, FALLBACK_RETURNED resolved; never retry or flash" &&
		NF == 3 { stage2_watchdog_observer_v2++ ; next }
	$1 == "build/storage-layout-stage2-watchdog-mmio-v1-generation204-20260827-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed Generation 204 MMIO-read classifier; target reported watchdog-mmio-detail before writes, proving the pipeline masked an empty or invalid register read; exact fastboot and FALLBACK_RETURNED passed, no storage writes; never retry or flash" &&
		NF == 3 { stage2_watchdog_mmio++ ; next }
	$1 == "build/storage-layout-stage2-watchdog-mmio-v2-generation205-20260827-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed Generation 205 arm64 devmem-read classifier; exact watchdog-mmio-en proved read() rejected the first MMIO access, exact fastboot and FALLBACK_RETURNED passed, no storage path; never retry or flash" &&
		NF == 3 { stage2_watchdog_mmio_v2++ ; next }
	$1 == "build/storage-layout-stage2-watchdog-mmap-v1-generation206-20260827-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "allow" &&
		$3 == "one exact Generation 206 read-only mmap watchdog snapshot with open/mmap/bus-fault classification; no MMIO write, watchdog registration or storage dependency; RAM-only, never flash or retry after COMMIT" &&
		NF == 3 { stage2_watchdog_mmap++ ; next }
	$1 == "build/persistent-root-storage-read-v4-generation25-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 25 RAM-only cycle; exact Alpine fallback returned; never retry or flash" && NF == 3 { generation25++ ; next }
	$1 == "build/persistent-root-storage-read-v5-generation26-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 26 RAM-only cycle; no target USB appeared and exact Alpine returned after 25.333 seconds; never retry or flash" && NF == 3 { generation26++ ; next }
	$1 == "build/persistent-root-usb-control-v6-generation27-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 27 RAM-only cycle; stable target NCM passed before exact Alpine fallback; never retry or flash" && NF == 3 { generation27++ ; next }
	$1 == "build/persistent-root-dtb-control-v7-generation28-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 28 RAM-only cycle; stable target NCM passed before exact Alpine fallback; never retry or flash" && NF == 3 { generation28++ ; next }
	$1 == "build/persistent-root-image-control-v8-generation29-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 29 RAM-only cycle; stable target NCM passed before exact Alpine fallback; never retry or flash" && NF == 3 { generation29++ ; next }
	$1 == "build/persistent-root-accepted-image-v9-generation30-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 30 RAM-only cycle; no target USB appeared before exact Alpine fallback; never retry or flash" && NF == 3 { generation30++ ; next }
	$1 == "build/persistent-root-deferred-ufs-v10-generation31-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 31 RAM-only cycle; no target USB appeared before exact Alpine fallback; never retry or flash" && NF == 3 { generation31++ ; next }
	$1 == "build/persistent-root-deferred-qmp-ufs-v11-generation32-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 32 RAM-only cycle; stable target NCM appeared before the module chain and exact Alpine fallback; never retry or flash" && NF == 3 { generation32++ ; next }
	$1 == "build/persistent-root-qmp-ufs-phy-control-v12-generation33-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 33 RAM-only cycle; target NCM disappeared during the PHY-only control window; never retry or flash" && NF == 3 { generation33++ ; next }
	$1 == "build/persistent-root-qmp-module-load-control-v13-generation34-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 34 RAM-only cycle; QMP-UFS module registration passed the exact NCM window and Alpine returned; never retry or flash" && NF == 3 { generation34++ ; next }
	$1 == "build/persistent-root-qmp-regulator-stage-v14-generation35-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 35 RAM-only cycle; clock/regulator probe stage passed the exact NCM window and Alpine returned; never retry or flash" && NF == 3 { generation35++ ; next }
	$1 == "build/persistent-root-qmp-mmio-stage-v15-generation36-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 36 RAM-only cycle; DT/MMIO probe stage passed the exact NCM window and Alpine returned; never retry or flash" && NF == 3 { generation36++ ; next }
	$1 == "build/persistent-root-qmp-clock-provider-stage-v16-generation37-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 37 RAM-only cycle; target NCM disappeared inside qmp_ufs_register_clocks and exact Alpine returned; never retry or flash" && NF == 3 { generation37++ ; next }
	$1 == "build/persistent-root-qmp-fixed-clocks-stage-v17-generation38-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 38 RAM-only cycle; target NCM disappeared during allocation or one of three fixed-rate clock registrations and exact Alpine returned; no phone-storage access; never retry or flash" && NF == 3 { generation38++ ; next }
	$1 == "build/persistent-root-qmp-first-fixed-clock-stage-v18-generation39-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 39 RAM-only cycle; target NCM disappeared during allocation or first fixed-rate clock registration and exact Alpine returned; no phone-storage access; never retry or flash" && NF == 3 { generation39++ ; next }
	$1 == "build/persistent-root-qmp-allocation-stage-v19-generation40-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 40 RAM-only cycle; clock-data allocation completed, stable target NCM passed, and exact Alpine returned; no phone-storage access; never retry or flash" && NF == 3 { generation40++ ; next }
	$1 == "build/persistent-root-qmp-first-clock-name-stage-v20-generation41-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 41 RAM-only cycle; first-symbol-clock name construction and stable NCM passed before exact Alpine fallback; no phone-storage access; never retry or flash" && NF == 3 { generation41++ ; next }
	$1 == "build/persistent-root-qmp-first-clock-runtime-pm-stage-v21-generation42-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 42 RAM-only cycle; first fixed-rate clock registration and stable NCM passed before exact Alpine fallback; no phone-storage access; never retry or flash" && NF == 3 { generation42++ ; next }
	$1 == "build/persistent-root-qmp-second-clock-runtime-pm-stage-v22-generation43-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 43 RAM-only cycle; stable target NCM and exact Alpine fallback passed, but stale initramfs release identity stopped before QMP-UFS module load; no phone-storage access; never retry or flash" && NF == 3 { generation43++ ; next }
	$1 == "build/persistent-root-qmp-third-clock-runtime-pm-stage-v23-generation44-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 44 RAM-only cycle; exact target proof crossed all three fixed-rate clocks, stable NCM and exact Alpine fallback passed, and no phone-storage access occurred; never retry or flash" && NF == 3 { generation44++ ; next }
	$1 == "build/persistent-root-qmp-clock-provider-cleanup-stage-v24-generation45-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 45 RAM-only cycle; recovery bundle fetch failed before transfer or mainline execution, exact Alpine fallback returned, and no phone-storage access occurred; never retry or flash" && NF == 3 { generation45++ ; next }
	$1 == "build/persistent-root-qmp-clock-provider-cleanup-stage-v25-generation46-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 46 RAM-only cycle; OF clock-provider publication and paired cleanup completed, stable target NCM passed, exact Alpine fallback returned, and no phone-storage access occurred; never retry or flash" && NF == 3 { generation46++ ; next }
	$1 == "build/persistent-root-qmp-ufs-phy-creation-stage-v26-generation47-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 47 RAM-only cycle; PHY creation completed, stable target NCM passed, exact Alpine fallback returned, and no phone-storage access occurred; never retry or flash" && NF == 3 { generation47++ ; next }
	$1 == "build/persistent-root-qmp-ufs-phy-provider-stage-v27-generation48-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 48 RAM-only cycle; QMP-UFS OF PHY-provider registration completed, stable target NCM passed, exact Alpine fallback returned, and no phone-storage access occurred; never retry or flash" && NF == 3 { generation48++ ; next }
	$1 == "build/persistent-root-ufs-readonly-enumeration-v28-generation49-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 49 RAM-only cycle; exact 116-node read-only UFS enumeration, stable NCM, and exact Alpine fallback passed with zero mounts and writes; never retry or flash" && NF == 3 { generation49++ ; next }
	$1 == "build/persistent-root-ufs-local-root-v29-generation50-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 50 RAM-only cycle; target NCM remained stable for approximately 599 seconds, key-only SSH never appeared, the bounded target watchdog reset, and exact Alpine fallback returned; no persistent phone writes; never retry or flash" && NF == 3 { generation50++ ; next }
	$1 == "build/persistent-root-ufs-local-root-stage-v30-generation51-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 51 RAM-only cycle; exact read-only UFS, 116-node storage lock, dynamic userdata resolution, and ro,noload mount passed; complete 181242-entry root verification exceeded the 600-second rollback window while NCM remained stable; exact Alpine fallback returned; no persistent phone writes; never retry or flash" && NF == 3 { generation51++ ; next }
	$1 == "build/persistent-root-ufs-fast-admission-v31-generation52-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 52 RAM-only cycle; read-only UFS, exact userdata, bounded root admission, and switch-root entry passed, key-only SSH did not appear, and exact Alpine fallback returned; never retry or flash" && NF == 3 { generation52++ ; next }
	$1 == "build/persistent-root-local-image-v32-generation53-20260813-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 53 RAM-only cycle; local-image Arch reached strict key-only SSH at target uptime 298.62 seconds with both ext4 layers ro,noload, tmpfs OverlayFS, clean UFS checks, normal systemd reboot, and exact Alpine fallback; host parser rejected only a stale root marker after success; never retry or flash" && NF == 3 { generation53++ ; next }
	$1 == "build/persistent-root-local-image-fast-attest-v33-generation54-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 54 RAM-only cycle; read-only UFS, exact userdata and 16 GiB image, both ro,noload mounts, tmpfs OverlayFS, switch_root, systemd, NCM, and key-only SSH reached; post-handoff attestation failed because retained musl BusyBox was executed without its retained loader; exact Alpine fallback and host cleanup passed; never retry or flash" && NF == 3 { generation54++ ; next }
	$1 == "build/persistent-root-local-image-loader-v34-generation55-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 55 RAM-only cycle; exact read-only UFS, userdata and 16 GiB image, both ro,noload mounts, tmpfs OverlayFS, switch_root, systemd, retained-loader attestation, NCM, and strict key-only SSH passed in 344.676 seconds; normal reboot, exact Alpine fallback, and host cleanup passed; never retry or flash" && NF == 3 { generation55++ ; next }
	$1 == "build/persistent-root-local-image-loader-v34-generation56-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 56 RAM-only cycle; exact read-only UFS, userdata and 16 GiB image, both ro,noload mounts, tmpfs OverlayFS, switch_root, systemd, retained-loader attestation, NCM, and strict key-only SSH passed in 362.241 seconds; systemd timing isolated ldconfig and vconsole delays; normal reboot, exact Alpine fallback, and host cleanup passed; never retry or flash" && NF == 3 { generation56++ ; next }
	$1 == "build/persistent-root-local-image-volatile-v35-generation57-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 57 RAM-only cycle; exact read-only UFS, userdata and 16 GiB image, both ro,noload mounts, tmpfs OverlayFS, volatile systemd markers, retained-loader attestation, and strict key-only SSH passed in 305.928 seconds; normal reboot, exact Alpine fallback, and host cleanup passed; never retry or flash" && NF == 3 { generation57++ ; next }
	$1 == "build/persistent-root-local-image-ed25519-v36-generation58-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 58 RAM-only cycle; exact read-only UFS, userdata and 16 GiB image, both ro,noload mounts, tmpfs OverlayFS, Ed25519-only volatile host-key generation, retained-loader attestation, and strict key-only SSH passed in 333.446 seconds; normal reboot, exact Alpine fallback, and host cleanup passed; never retry or flash" && NF == 3 { generation58++ ; next }
	$1 == "build/persistent-root-local-image-write-v37-generation59-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 59 RAM-only cycle; UFS, exact userdata, and the read-only image passed, but the bounded write path failed before the image filesystem was mounted read-write; no probe ancestry was created; exact Alpine fallback and host cleanup passed; never retry or flash" && NF == 3 { generation59++ ; next }
	$1 == "build/persistent-root-local-image-write-diag-v38-generation60-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 60 RAM-only cycle; exact UFS, userdata, and read-only image resolution passed, then image-write-window failed before outer userdata RW; the image remained clean with mount count one and no marker ancestry; exact PS_HOLD Alpine fallback and host cleanup passed; never retry or flash" && NF == 3 { generation60++ ; next }
	$1 == "build/persistent-root-local-image-write-window-v39-generation61-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 61 RAM-only cycle; UFS, exact userdata and image resolution, userdata unmount, read-only precheck, and both partition and parent-disk BLKROSET calls passed, then effective blockdev read-only-state verification failed before sysfs/count verification, any RW mount, loop attachment, marker, or persistent write; the image remained clean with mount count one and no marker ancestry; exact Alpine fallback and host cleanup passed; never retry or flash" && NF == 3 { generation61++ ; next }
	$1 == "build/persistent-root-local-image-write-roclass-v40-generation62-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 62 RAM-only cycle; both BLKROSET calls returned success but the selected parent remained effectively read-only, so no RW mount, loop, marker, or persistent write occurred; exact Alpine fallback and clean marker-free image postcheck passed; never retry or flash" && NF == 3 { generation62++ ; next }
	$1 == "build/persistent-root-local-image-write-contained-v41-generation63-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 63 RAM-only cycle; UFS, exact userdata, the contained partition-and-parent write window, outer userdata RW mount, and writable loop attachment passed, then the inner ext4 mount failed because the sealed initramfs never created /mnt/probe-root; no inner ext4 or UFS data write occurred; exact Alpine fallback and clean marker-free image postcheck passed; never retry or flash" && NF == 3 { generation63++ ; next }
	$1 == "build/persistent-root-local-image-write-mountpoint-v42-generation64-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 64 RAM-only cycle; the bounded write window, outer and inner ext4 RW mounts, exact marker write, relock, read-only remount, image mount, and root verification passed, then the aggregate UFS-health gate deliberately rolled back; the image remained clean and the exact marker persisted; exact Alpine fallback passed; never retry or flash" && NF == 3 { generation64++ ; next }
	$1 == "build/persistent-root-local-image-post-write-v43-generation65-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 65 RAM-only cycle; the accepted read-only kernel booted but the sealed initramfs omitted all four deferred UFS modules, so UFS discovery timed out at ufs-ready before any storage node, mount, image, or write path; exact Alpine fallback, PS_HOLD/HARD_RESET lineage, and host cleanup passed; never retry or flash" && NF == 3 { generation65++ ; next }
	$1 == "build/persistent-root-local-image-ufs-detail-v44-generation66-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 66 RAM-only cycle; exact four-module UFS, read-only userdata and 16 GiB local image, persisted Generation 64 marker, tmpfs OverlayFS, systemd, NCM, and strict key-only SSH passed in 328.363 seconds; normal reboot, exact Alpine fallback, and host cleanup passed; never retry or flash" && NF == 3 { generation66++ ; next }
	$1 == "build/persistent-root-local-image-early-ssh-v45-generation67-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 67 RAM-only cycle; exact UFS, two ro,noload ext4 layers, persisted marker, early strict key-only SSH, and storage attestation passed, but recovery ACM closed after the COMMIT claim before the post-claim response; host salvage proved early SSH active at about 94.147 seconds and full attestation at 130.057 seconds; normal reboot, exact Alpine fallback, and host restoration passed; never retry or flash" && NF == 3 { generation67++ ; next }
	$1 == "build/persistent-root-local-image-early-ssh-v45-generation68-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 68 RAM-only cycle; corrected post-CLAIMED recovery departure, exact UFS, local image, tmpfs OverlayFS, P2 storage attestation, and early key-only sshd passed; the first cold authenticated SSH session exceeded the host 10-second connection deadline, while the same boot later passed exact strict SSH runtime and diagnostics; normal reboot, exact Alpine fallback, PS_HOLD lineage, and host restoration passed; never retry or flash" && NF == 3 { generation68++ ; next }
	$1 == "build/persistent-root-local-image-early-ssh-v45-generation69-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 69 RAM-only cycle; exact UFS, local image, tmpfs OverlayFS, P2 storage attestation, and key-only sshd passed; the bounded rendezvous reached one status-zero SSH response within its deadline but rejected unretained extra startup output before the runtime command; the same boot later passed exact runtime at 378.07 seconds and diagnostics; normal reboot, exact Alpine fallback, PS_HOLD lineage, and host restoration passed; never retry or flash" && NF == 3 { generation69++ ; next }
	$1 == "build/persistent-root-local-image-early-ssh-v45-generation70-20260814-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 70 RAM-only cycle; exact UFS, local image, tmpfs OverlayFS, P2 storage attestation, bounded authenticated SSH marker acceptance, strict key-only runtime, normal reboot, exact Alpine fallback, PS_HOLD lineage, and host restoration passed in 326.300 seconds; never retry or flash" && NF == 3 { generation70++ ; next }
	$1 == "build/persistent-root-power-usb-v1-generation77-20260821-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 77 RAM-only cycle; recovery and exact bundle transfer passed, target NCM enumerated for 2.77 seconds, then an immediate target fail-closed rollback returned exact stock slot A before UFS or SSH evidence; packaged pdr_interface retained the V18-proven rejected BTF section; resolved FALLBACK_RETURNED; never retry or flash" && NF == 3 { generation77++ ; next }
	$1 == "build/persistent-root-power-usb-v2-generation78-20260821-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 78 RAM-only cycle; no-BTF PDR payload advanced beyond Generation 77 and emitted exact target stage sequence 3, then the power/USB loader failed with legacy generic detail before UFS and forced the reviewed two-second rollback; exact stock slot-A fallback and cleanup passed; R3 component-level cause remains unresolved; never retry or flash" && NF == 3 { generation78++ ; next }
	$1 == "build/persistent-root-power-usb-v3-generation79-20260822-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 79 RAM-only cycle; exact target failure detail proved that the power/USB loader rejected the kernel role-switch text host [device] before checking the equally bracketed source [sink] power role; exact stock slot-A fallback and cleanup passed; resolved FALLBACK_RETURNED; never retry or flash" && NF == 3 { generation79++ ; next }
	$1 == "build/persistent-root-power-usb-v4-generation80-20260822-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 80 RAM-only cycle; bracketed Type-C roles passed, as did power/USB, deferred UFS, storage lock, and exact userdata resolution; target then failed at the generic userdata-mount boundary before local-image resolution; exact stock slot-A fallback and cleanup passed; resolved FALLBACK_RETURNED; never retry or flash" && NF == 3 { generation80++ ; next }
	$1 == "build/persistent-root-power-usb-v5-generation81-20260822-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 81 RAM-only cycle; power/USB, deferred UFS, storage lock, and exact userdata resolution passed; target proved the ext4 mount syscall itself returned nonzero before every post-mount check; exact stock slot-A fallback and cleanup passed; resolved FALLBACK_RETURNED; never retry or flash" && NF == 3 { generation81++ ; next }
	$1 == "build/persistent-root-power-usb-v6-generation82-20260822-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 82 RAM-only cycle; mount retained status 255 and EINVAL, while blkid exposed no recognized type and the type-gated classifier did not run dumpe2fs; exact stock slot-A fallback and cleanup passed; resolved FALLBACK_RETURNED; never retry or flash" && NF == 3 { generation82++ ; next }
	$1 == "build/persistent-root-power-usb-v7-generation83-20260822-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 83 RAM-only cycle; direct magic remained unknown because BusyBox od compressed duplicate output lines to an asterisk without -v; mount retained status 255 and EINVAL; exact stock slot-A fallback and cleanup passed; resolved FALLBACK_RETURNED; never retry or flash" && NF == 3 { generation83++ ; next }
	$1 == "build/persistent-root-power-usb-v8-generation84-20260822-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "revoked" &&
		$3 == "consumed by the sole Generation 84 RAM-only cycle; verbatim raw userdata magic remained neither ext4 nor F2FS, blkid exposed no type, and ext4 mount returned status 255 EINVAL; WW33 fstab independently proves F2FS behind dm-default-key metadata encryption; exact stock slot-A fallback and cleanup passed; resolved FALLBACK_RETURNED; never retry or flash" && NF == 3 { generation84++ ; next }
	$1 == "artifacts/recovery-stage-v18/boot-5.4.210-kexec-stage-builtin-recovery.avb.img" &&
		$2 == "revoked" &&
		$3 == "twice-live-accepted historical staging image; superseded as active authority by the corrected diagnostic lifecycle; never flash" && NF == 3 { revoked++ ; next }
	{ exit 1 }
	END { if (NR != 138 + power_usb + power_history || power_usb > 1 || power_history < 1 || local_stage != 1 || local_boot != 1 || local_write_boot != 1 || probe_writer != 1 || marker_reader != 1 || continuous_reader != 1 || early_fixed_reader != 1 || restart_reader != 1 || reboot_mode_reader != 1 || sparse_reader != 1 || stage_writer != 1 || hotplug_writer != 1 || preusb_writer != 1 || usbmode_writer != 1 || configfs_writer != 1 || udc_writer != 1 || stable_udc_writer != 1 || stage_ncm != 1 || timing_writer != 1 || address_writer != 1 || prebind_writer != 1 || explicit_writer != 1 || post_configfs_udc != 1 || two_sample_writer != 1 || bind_writer != 1 || direct_writer != 1 || bind_error_writer != 1 || hostfix_writer != 1 || postbind_writer != 1 || power_report_writer != 1 || listener_writer != 1 || abi_writer != 1 || ufs_count_writer != 1 || ufs_bind_writer != 1 || runtime_dt_writer != 1 || of_node_writer != 1 || proven_ufs_writer != 1 || proven_ufs_reboot_writer != 1 || proven_power_ufs_writer != 1 || proven_glob_ufs_writer != 1 || local_glob_writer != 1 || local_ssh_writer != 1 || local_nm_writer != 1 || local_fast_writer != 1 || local_stages_writer != 1 || local_auth_writer != 1 || local_globfix_writer != 1 || local_rworder_writer != 1 || local_writekernel_writer != 1 || local_write_benchmark != 1 || local_write_benchmark_v42 != 1 || local_write_benchmark_v43 != 1 || local_partial_inspect != 1 || local_write_benchmark_v45 != 1 || local_direct_stage != 1 || local_direct_successor != 1 || local_direct_megabyte != 1 || local_high_speed != 1 || local_runtime != 1 || local_runtime_successor != 1 || local_runtime_observer != 1 || local_runtime_sealfix != 1 || local_runtime_exitrd != 1 || stage2_mainline != 1 || stage2_mainline_v2 != 1 || stage2_mainline_v3 != 1 || stage2_clone != 1 || stage2_postmortem != 1 || stage2_clone_v2 != 1 || stage2_clone_v3 != 1 || stage2_watchdog_probe != 1 || stage2_clone_v4 != 1 || stage2_watchdog_lifetime != 1 || stage2_watchdog_runtime_abi != 1 || stage2_watchdog_observer != 1 || stage2_watchdog_observer_v2 != 1 || stage2_watchdog_mmio != 1 || stage2_watchdog_mmio_v2 != 1 || stage2_watchdog_mmap != 1 || observer != 1 || observer118 != 1 || core != 1 || generation25 != 1 || generation26 != 1 || generation27 != 1 || generation28 != 1 || generation29 != 1 || generation30 != 1 || generation31 != 1 || generation32 != 1 || generation33 != 1 || generation34 != 1 || generation35 != 1 || generation36 != 1 || generation37 != 1 || generation38 != 1 || generation39 != 1 || generation40 != 1 || generation41 != 1 || generation42 != 1 || generation43 != 1 || generation44 != 1 || generation45 != 1 || generation46 != 1 || generation47 != 1 || generation48 != 1 || generation49 != 1 || generation50 != 1 || generation51 != 1 || generation52 != 1 || generation53 != 1 || generation54 != 1 || generation55 != 1 || generation56 != 1 || generation57 != 1 || generation58 != 1 || generation59 != 1 || generation60 != 1 || generation61 != 1 || generation62 != 1 || generation63 != 1 || generation64 != 1 || generation65 != 1 || generation66 != 1 || generation67 != 1 || generation68 != 1 || generation69 != 1 || generation70 != 1 || generation77 != 1 || generation78 != 1 || generation79 != 1 || generation80 != 1 || generation81 != 1 || generation82 != 1 || generation83 != 1 || generation84 != 1 || revoked != 1) exit 1 }
	' "$boot_policy" ||
	{ echo 'FAIL committed temporary-boot policy is not the exact retained admissions plus consumed history' >&2; exit 1; }
grep -Fq '"headless-diagnostic-ssh-fatal-token-boundary-v20-live-v1"' "$lifecycle" ||
	{ echo 'FAIL lifecycle does not select exact successor execution profile' >&2; exit 1; }
[[ $(grep -Fxc \
	'DIAGNOSTIC_RECOVERY_PROFILE = "headless-diagnostic-generation12-live-v1"' \
	"$lifecycle_test") == 1 ]] ||
	{ echo 'FAIL lifecycle test does not pin exact generation-12 live profile' >&2; exit 1; }
[[ $(grep -Fxc 'DIAGNOSTIC_LIVE_STATUS = "admitted"' "$lifecycle") == 1 ]] ||
	{ echo 'FAIL lifecycle does not admit the exact retention execution profile' >&2; exit 1; }
! grep -Fq 'headless-diagnostic-generation9-' "$lifecycle" ||
	{ echo 'FAIL consumed generation-9 profile remains in the lifecycle' >&2; exit 1; }
! grep -Fq 'headless-diagnostic-generation9-' "$lifecycle_test" ||
	{ echo 'FAIL consumed generation-9 profile remains in the lifecycle test' >&2; exit 1; }
! grep -Fq 'headless-diagnostic-generation10-' "$lifecycle" ||
	{ echo 'FAIL consumed generation-10 profile remains in the lifecycle' >&2; exit 1; }
! grep -Fq 'headless-diagnostic-generation10-' "$lifecycle_test" ||
	{ echo 'FAIL consumed generation-10 profile remains in the lifecycle test' >&2; exit 1; }
! grep -Fq 'headless-diagnostic-generation11-' "$lifecycle" ||
	{ echo 'FAIL consumed generation-11 profile remains in the lifecycle' >&2; exit 1; }
! grep -Fq 'headless-diagnostic-generation11-' "$lifecycle_test" ||
	{ echo 'FAIL consumed generation-11 profile remains in the lifecycle test' >&2; exit 1; }
for generation11_lifecycle_leak in \
	"$generation11_image" \
	8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562
do
	! grep -Fq "$generation11_lifecycle_leak" "$lifecycle" ||
		{ echo 'FAIL generation-11 artifact leaked into the lifecycle' >&2; exit 1; }
	! grep -Fq "$generation11_lifecycle_leak" "$lifecycle_test" ||
		{ echo 'FAIL generation-11 artifact leaked into the lifecycle test' >&2; exit 1; }
done
for generation12_lifecycle_leak in \
	headless-diagnostic-generation12-offline-v1 \
	"$generation12_image" \
	615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6
do
	! grep -Fq "$generation12_lifecycle_leak" "$lifecycle" ||
		{ echo 'FAIL generation-12 offline artifact leaked into the lifecycle' >&2; exit 1; }
	! grep -Fq "$generation12_lifecycle_leak" "$lifecycle_test" ||
		{ echo 'FAIL generation-12 offline artifact leaked into the lifecycle test' >&2; exit 1; }
done
awk -F '\t' \
	-v power_name="$POWER_USB_OUTPUT_ROOT/wrapper/repack/stable-recovery-a.avb.img" \
	-v power_basis="$POWER_USB_BOOT_POLICY_BASIS" '
	$2 == "allow" { allowed++ }
	$1 == power_name && $2 == "allow" && $3 == power_basis && NF == 3 {
		power_usb++
	}
	END { exit allowed == 2 + power_usb && power_usb <= 1 ? 0 : 1 }
' "$boot_policy" ||
	{ echo 'FAIL temporary-boot policy does not contain the exact retained admissions and optional active power/USB admission' >&2; exit 1; }
grep -Fq "expected_boot_basis='one exact Generation 193 mainline read-only Stage-2 diagnostics cycle; current responder, p23/p24, qcom-battmgr, thermal, UFS, local Arch, strict SSH, corrected 117-node host acceptance, and exact fastboot; externally consumed exact claim required; never flash or retry after entry'" "$gate" ||
	{ echo 'FAIL Generation 193 gate basis differs from policy' >&2; exit 1; }
grep -Fq "expected_boot_basis='consumed by the sole Generation 194 cycle; mainline reached exact UFS/NCM/SSH, then the redundant 16 GiB source hash stalled UFS and NCM before any observed clone-WRITE marker; host NCM watchdog timed out, rollback returned exact fastboot after 19m31s, intent remains UNKNOWN, and p24 disposition requires read-only proof; never retry or flash'" "$gate" ||
	{ echo 'FAIL Generation 194 gate basis differs from policy' >&2; exit 1; }
grep -Fq "expected_boot_basis='consumed successful Generation 195 read-only p24 postmortem; exact 117-node UFS and key-only SSH passed, p24 classified non-ext4 with first 4 MiB exactly zero-filled, target and exact slot-A fastboot proofs passed, intent resolved TARGET_ACCEPTED; never retry or flash'" "$gate" ||
	{ echo 'FAIL Generation 195 gate basis differs from policy' >&2; exit 1; }
grep -Fq "expected_boot_basis='consumed Generation 196 prewrite watchdog probe; exact UFS passed, qcom-wdt load/open advanced to the optional timeout-sysfs check, then failed closed because CONFIG_WATCHDOG_SYSFS is disabled; no p24 write, exact slot-A fastboot and intent fallback resolution passed; never retry or flash'" "$gate" ||
	{ echo 'FAIL Generation 196 gate basis differs from policy' >&2; exit 1; }
grep -Fq "expected_boot_basis='consumed Generation 197 prewrite watchdog probe; exact UFS passed but the remaining generic hardware-watchdog predicate failed, no p24 write occurred, exact slot-A fastboot and fallback intent resolution passed; never retry or flash'" "$gate" ||
	{ echo 'FAIL Generation 197 gate basis differs from policy' >&2; exit 1; }
grep -Fq "expected_boot_basis='consumed by the sole Generation 198 read-only cycle; the watchdog armed and target emitted storage-locked, but the host parser allowed only the nonexistent storage-relock spelling; the 900-second target fallback returned exact slot-A fastboot at the host deadline, no p24 write path was packaged, and intent resolved FALLBACK_RETURNED; never retry or flash'" "$gate" ||
	{ echo 'FAIL Generation 198 gate basis differs from policy' >&2; exit 1; }
grep -Fq "expected_boot_basis='consumed Generation 199 prewrite watchdog-lifetime failure; mainline UFS/NCM/runtime/key-only SSH passed in 7.86 seconds, then the watchdog process was absent before source verification or any p24 write window; exact slot-A fastboot and FALLBACK_RETURNED resolution passed; never retry or flash'" "$gate" ||
	{ echo 'FAIL Generation 199 gate basis differs from policy' >&2; exit 1; }
grep -Fq "expected_boot_basis='consumed successful Generation 200 read-only watchdog lifetime probe; runtime at 7.90 seconds proved qcom_wdt, class and device absent, BusyBox failed ENOENT opening watchdog0, and dmesg proved struct-module ABI size mismatch; exact fastboot and TARGET_ACCEPTED resolution passed; never retry or flash'" "$gate" ||
	{ echo 'FAIL Generation 200 gate basis differs from policy' >&2; exit 1; }
grep -Fq "expected_boot_basis='consumed Generation 201 watchdog-reset cycle; exact-ABI qcom_wdt arming produced no reporter frame, NCM TX timeout at 11 seconds, target USB loss at 13 seconds and stock slot-A recovery return; no storage write path, FALLBACK_RETURNED resolved; never retry or flash'" "$gate" ||
	{ echo 'FAIL Generation 201 gate basis differs from policy' >&2; exit 1; }
grep -Fq "expected_boot_basis='consumed Generation 202 inherited-watchdog timing proof; MMIO-read-only observer made no watchdog write, yet target NCM disconnected at 12 seconds and stock slot-A recovery returned, proving the watchdog was armed before mainline; no reporter frame or storage writes, FALLBACK_RETURNED resolved; never retry or flash'" "$gate" ||
	{ echo 'FAIL Generation 202 gate basis differs from policy' >&2; exit 1; }
grep -Fq "expected_boot_basis='consumed Generation 203 early module observer; NCM still timed out and target reset before any stage frame, proving external module relocation/probe is too slow for inherited watchdog deadline; no MMIO or storage writes, FALLBACK_RETURNED resolved; never retry or flash'" "$gate" ||
	{ echo 'FAIL Generation 203 gate basis differs from policy' >&2; exit 1; }
grep -Fq "expected_boot_basis='consumed Generation 204 MMIO-read classifier; target reported watchdog-mmio-detail before writes, proving the pipeline masked an empty or invalid register read; exact fastboot and FALLBACK_RETURNED passed, no storage writes; never retry or flash'" "$gate" ||
	{ echo 'FAIL Generation 204 gate basis differs from policy' >&2; exit 1; }
grep -Fq "expected_boot_basis='consumed Generation 205 arm64 devmem-read classifier; exact watchdog-mmio-en proved read() rejected the first MMIO access, exact fastboot and FALLBACK_RETURNED passed, no storage path; never retry or flash'" "$gate" ||
	{ echo 'FAIL Generation 205 gate basis differs from policy' >&2; exit 1; }
grep -Fq "expected_boot_basis='one exact Generation 206 read-only mmap watchdog snapshot with open/mmap/bus-fault classification; no MMIO write, watchdog registration or storage dependency; RAM-only, never flash or retry after COMMIT'" "$gate" ||
	{ echo 'FAIL Generation 206 gate basis differs from policy' >&2; exit 1; }
awk -F '\t' '
	$1 == "build/storage-layout-stage2-watchdog-mmio-v1-generation204-20260827-r1/repack/stable-recovery-a.avb.img" &&
	$4 == "consumed Generation 204 pipeline-masked MMIO read failure; exact fallback, no writes; never retry or flash" && NF == 5 { found++ }
	END { exit found == 1 ? 0 : 1 }
' "$artifact_manifest" ||
	{ echo 'FAIL Generation 204 artifact role differs from live gate' >&2; exit 1; }
awk -F '\t' '
	$1 == "build/storage-layout-stage2-watchdog-mmio-v2-generation205-20260827-r1/repack/stable-recovery-a.avb.img" &&
	$4 == "consumed Generation 205 arm64 devmem read failure; exact fallback, no writes; never retry or flash" && NF == 5 { found++ }
	END { exit found == 1 ? 0 : 1 }
' "$artifact_manifest" ||
	{ echo 'FAIL Generation 205 artifact role differs from live gate' >&2; exit 1; }
awk -F '\t' '
	$1 == "build/storage-layout-stage2-watchdog-mmap-v1-generation206-20260827-r1/repack/stable-recovery-a.avb.img" &&
	$4 == "unbooted Generation 206 read-only mmap watchdog snapshot; never flash or retry after COMMIT" && NF == 5 { found++ }
	END { exit found == 1 ? 0 : 1 }
' "$artifact_manifest" ||
	{ echo 'FAIL Generation 206 artifact role differs from live gate' >&2; exit 1; }
v20_image=build/ssh-acceptance-v20-fatal-token-boundary-fix-20260812-r1/wrapper/repack/stable-recovery-a.avb.img
[[ $(awk -F '\t' -v name="$v20_image" \
	'$1 == name { count++ } END { print count + 0 }' "$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed Generation 20 remains boot-allowlisted' >&2; exit 1; }
awk -F '\t' -v name="$v20_image" '
	$1 == name && $2 == "100663296" &&
	$3 == "cacd0164d7d1d581f6fa4cb8926d7fea655be92e333c84635de953dd7d816b39" &&
	$4 ~ /^consumed token-delimited-fatal-filter SSH recovery/ &&
	$4 ~ /strict key-only SSH and runtime acceptance/ &&
	$4 ~ /FALLBACK_RETURNED intent resolution passed/ &&
	$4 ~ /never retry or flash$/ && $5 == "no" { count++ }
	END { exit count == 1 ? 0 : 1 }
' "$artifact_manifest" ||
	{ echo 'FAIL consumed Generation 20 artifact inventory is not exact' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation12_image" -v basis="$generation12_boot_basis" \
	'$1 == name && $2 == "allow" && $3 == basis { count++ } \
	END { print count + 0 }' "$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed generation-12 recovery remains admitted' >&2; exit 1; }
check_generation12_inventory() {
	local inventory=$1
	awk -F '\t' -v name="$generation12_image" -v role="$generation12_consumed_role" '
	$1 ~ /generation-?12([^0-9]|$)/ ||
		index($4, "generation-12") ||
		$3 == "615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6" {
		generation12_count++
	}
	$1 == name {
		count++
		if (NF != 5 || $2 != "100663296" ||
			$3 != "615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6" ||
			$4 != role ||
			$5 != "no")
			exit 1
	}
	END { if (count != 1 || generation12_count != 1) exit 1 }
' "$inventory"
}
check_generation12_inventory "$artifact_manifest" ||
	{ echo 'FAIL generation-12 artifact inventory row is not exact and authority-free' >&2; exit 1; }
generation12_inventory_mutation=$tmp/generation12-artifacts.tsv
cp -- "$artifact_manifest" "$generation12_inventory_mutation"
awk -F '\t' 'BEGIN { OFS = "\t" }
	$3 == "615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6" {
		$1 = "build/generation12-alias/repack/stable-recovery-a.avb.img"
		print
	}
' "$artifact_manifest" >>"$generation12_inventory_mutation"
if check_generation12_inventory "$generation12_inventory_mutation"; then
	echo 'FAIL generation-12 inventory accepted an additional identity row' >&2
	exit 1
fi
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
	{ echo 'FAIL consumed generation-10 recovery remains boot-allowlisted' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation10_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51" && \
	$4 == "consumed generation-10 PREPARE-progress-instrumented diagnostic recovery; one RAM-only recovery boot reached verified recovery ACM/NCM and accepted PREPARE; the responder emitted REQUEST_ACCEPTED and the one-transfer host sent all 46163787 signed-bundle bytes, but the ACM transport closed before FETCH_COMPLETE or PREPARED; replay discovery reported stable product-mismatch in all 216 samples with phase=prepare-replay and no identity changes; the diagnostic collector expired after its fixed 120-second ACM-stability deadline with zero frames; restricted NFSv4.2 reached pre-COMMIT readiness, but no COMMIT intent existed and no target ran; exact Alpine fallback, strict SSH, profile restoration, and final host cleanup passed; retain offline only; never retry or flash" && \
	$5 == "no" { count++ } END { print count + 0 }' \
	"$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL generation-10 consumed artifact identity is not exact' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation11_image" \
	'$1 == name { count++ } END { print count + 0 }' "$boot_policy") == 0 ]] ||
	{ echo 'FAIL consumed generation-11 recovery remains boot-allowlisted' >&2; exit 1; }
[[ $(awk -F '\t' -v name="$generation11_image" \
	'$1 == name && $2 == "100663296" && \
	$3 == "8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562" && \
	$4 == "consumed generation-11 receive-only NCM-progress diagnostic recovery; one RAM-only recovery boot reached verified recovery ACM/NCM; the privileged serve-progress-deferred host path started the exact receive-only 8081 collector, but its post-start listener-confinement check failed before the bundle-server ready marker; capture ended PARTIAL/NO_ADMISSION with zero records and authority=NONE; early-target diagnostic ACM never became stable and produced zero frames with zero dropped USB events; no recovery PREPARE or COMMIT intent existed and no target ran; exact Alpine fallback, strict SSH, profile restoration, host cleanup, and Steam socket restoration passed; retain offline only; never retry or flash" && \
	$5 == "no" { count++ } END { print count + 0 }' \
	"$artifact_manifest") == 1 ]] ||
	{ echo 'FAIL generation-11 consumed artifact identity is not exact' >&2; exit 1; }

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

for generation11_action in boot preflight; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation11-offline-v1 \
		LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
		RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
		TRUST_KEY="$repo/build/unused-trust-key" \
		BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" "$generation11_action" >"$tmp/out" 2>"$tmp/err"
	then
		echo "FAIL offline generation-11 profile reached $generation11_action" >&2
		exit 1
	fi
	grep -Fq 'generation-11 diagnostic profile is offline-only and not boot-authorized' \
		"$tmp/err" ||
		{ echo "FAIL offline generation-11 $generation11_action returned the wrong rejection" >&2; exit 1; }
	if grep -Fq 'missing live-gate command' "$tmp/err"; then
		echo "FAIL offline generation-11 $generation11_action reached host inspection" >&2
		exit 1
	fi
done

for generation12_action in boot preflight; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation12-offline-v1 \
		LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
		RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
		TRUST_KEY="$repo/build/unused-trust-key" \
		BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" "$generation12_action" >"$tmp/out" 2>"$tmp/err"
	then
		echo "FAIL offline generation-12 profile reached $generation12_action" >&2
		exit 1
	fi
	grep -Fq 'generation-12 diagnostic profile is offline-only and not boot-authorized' \
		"$tmp/err" ||
		{ echo "FAIL offline generation-12 $generation12_action returned the wrong rejection" >&2; exit 1; }
	if grep -Fq 'missing live-gate command' "$tmp/err"; then
		echo "FAIL offline generation-12 $generation12_action reached host inspection" >&2
		exit 1
	fi
done

for generation12_connected_action in boot preflight; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation12-live-v1 \
		LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
		RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
		TRUST_KEY="$repo/build/unused-trust-key" \
		BUNDLE_ROOT="$repo/build/unused-bundle-root" \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" "$generation12_connected_action" >"$tmp/out" 2>"$tmp/err"
	then
		echo "FAIL generation-12 live profile reached direct $generation12_connected_action" >&2
		exit 1
	fi
		grep -Fq \
			'generation-12 is consumed and cannot enter connected preflight or boot' \
			"$tmp/err" ||
		{ echo "FAIL generation-12 direct $generation12_connected_action returned the wrong rejection" >&2; exit 1; }
	if grep -Fq 'missing live-gate command' "$tmp/err"; then
		echo "FAIL generation-12 direct $generation12_connected_action reached host inspection" >&2
		exit 1
	fi
done

for generation11_connected_action in boot preflight; do
	if env -i PATH="$PATH" HOME="$HOME" \
		ALLOW_TEMPORARY_BOOT=1 \
		ALLOW_HEADLESS_LIVE_GATE=1 \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation11-live-v1 \
		LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
		RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
		TRUST_KEY="$repo/build/unused-trust-key" \
		BUNDLE_ROOT="$repo/build/unused-bundle-root" \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" "$generation11_connected_action" >"$tmp/out" 2>"$tmp/err"
	then
		echo "FAIL generation-11 live profile reached direct $generation11_connected_action" >&2
		exit 1
	fi
	grep -Fq \
		'generation-11 connected action requires the one-shot lifecycle controller' \
		"$tmp/err" ||
		{ echo "FAIL generation-11 direct $generation11_connected_action returned the wrong rejection" >&2; exit 1; }
	if grep -Fq 'missing live-gate command' "$tmp/err"; then
		echo "FAIL generation-11 direct $generation11_connected_action reached host inspection" >&2
		exit 1
	fi
done

if env -i PATH="$PATH" HOME="$HOME" \
	XDG_STATE_HOME="$tmp/generation11-claimless-state" \
	ALLOW_TEMPORARY_BOOT=1 \
	ALLOW_HEADLESS_LIVE_GATE=1 \
	ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation11-live-v1 \
	LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
	TRUST_KEY="$repo/build/unused-trust-key" \
	BUNDLE_ROOT="$repo/build/unused-bundle-root" \
	BUNDLE=headless-netroot-early-diag-v1 \
	RECOVERY_SHA256=8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562 \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	bash "$gate" boot >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL consumed generation-11 boot passed without a policy row' >&2
	exit 1
fi
grep -Fq "temporary boot policy does not uniquely list $generation11_image" \
	"$tmp/err" ||
	{ echo 'FAIL consumed generation-11 boot returned the wrong policy rejection' >&2; exit 1; }
if grep -Fq 'missing live-gate command' "$tmp/err"; then
	echo 'FAIL consumed generation-11 boot reached host inspection' >&2
	exit 1
fi

for generation11_policy_shape in \
	missing-file missing-row malformed-header malformed-artifact-header \
	missing-artifact-row duplicate-artifact-row duplicate wrong-basis \
	denied-status identity-mismatch readmitted-exact-basis policy-trailing-field \
	artifact-trailing-field
do
	policy_fixture=$tmp/generation11-policy-$generation11_policy_shape
	install -d -m 0755 "$policy_fixture/scripts/host" \
		"$policy_fixture/manifests"
	install -m 0755 "$gate" \
		"$policy_fixture/scripts/host/run-stable-recovery-live-gate.sh"
	install -m 0644 "$generated_power" \
		"$policy_fixture/scripts/host/generated-power-usb-active.sh"
	cp -- "$artifact_manifest" "$policy_fixture/manifests/artifacts.tsv"
	install -m 0644 "$boot_policy" \
		"$policy_fixture/manifests/temporary-boot-images.tsv"
	case $generation11_policy_shape in
		missing-file)
			rm -f -- "$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		missing-row)
			;;
		malformed-header)
			sed -i '1s/^name\tstatus\tbasis$/artifact\tstate\treason/' \
				"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		malformed-artifact-header)
			printf '%s\tallow\t%s\n' "$generation11_image" \
				"$generation11_boot_basis" \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			sed -i \
				'1s/^name\tsize\tsha256\trole\ttracked$/artifact\tbytes\tdigest\tdisposition\tpresent/' \
				"$policy_fixture/manifests/artifacts.tsv"
			;;
		missing-artifact-row)
			printf '%s\tallow\t%s\n' "$generation11_image" \
				"$generation11_boot_basis" \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			awk -F '\t' -v name="$generation11_image" '$1 != name' \
				"$artifact_manifest" >"$policy_fixture/manifests/artifacts.tsv"
			;;
		duplicate-artifact-row)
			printf '%s\tallow\t%s\n' "$generation11_image" \
				"$generation11_boot_basis" \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			awk -F '\t' -v name="$generation11_image" '$1 == name { print }' \
				"$artifact_manifest" >>"$policy_fixture/manifests/artifacts.tsv"
			;;
		duplicate)
			printf '%s\tallow\t%s\n' "$generation11_image" \
				"$generation11_boot_basis" \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			printf '%s\tallow\t%s\n' "$generation11_image" \
				"$generation11_boot_basis" \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		wrong-basis)
			printf '%s\tallow\t%s\n' "$generation11_image" \
				'wrong generation-11 basis; never boot' \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		denied-status)
			printf '%s\tdeny\t%s\n' "$generation11_image" \
				"$generation11_boot_basis" \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		identity-mismatch)
			printf '%s\tallow\t%s\n' "$generation11_image" \
				"$generation11_boot_basis" \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			awk -F '\t' -v OFS='\t' -v name="$generation11_image" \
				'$1 == name { $3 = "0000000000000000000000000000000000000000000000000000000000000000" } { print }' \
				"$artifact_manifest" >"$policy_fixture/manifests/artifacts.tsv"
			;;
		readmitted-exact-basis)
			printf '%s\tallow\t%s\n' "$generation11_image" \
				"$generation11_boot_basis" \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		policy-trailing-field)
			printf '%s\tallow\t%s\t\n' "$generation11_image" \
				"$generation11_boot_basis" \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		artifact-trailing-field)
			printf '%s\tallow\t%s\n' "$generation11_image" \
				"$generation11_boot_basis" \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			awk -F '\t' -v name="$generation11_image" \
				'$1 == name { print $0 "\t"; next } { print }' \
				"$artifact_manifest" >"$policy_fixture/manifests/artifacts.tsv"
			;;
	esac
	for generation11_connected_action in boot preflight; do
		if env -i PATH="$PATH" HOME="$HOME" \
			ALLOW_TEMPORARY_BOOT=1 \
			ALLOW_HEADLESS_LIVE_GATE=1 \
			ALLOW_MINIMAL_HEADLESS_LIVE_CYCLE=1 \
			ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation11-live-v1 \
			LIVE_BUILD_ROOT="$repo/build/unused-live-root" \
			RECOVERY_COMPONENT_ROOT="$repo/build/unused-component-root" \
			TRUST_KEY="$repo/build/unused-trust-key" \
			BUNDLE_ROOT="$repo/build/unused-bundle-root" \
			BUNDLE=headless-netroot-early-diag-v1 \
			RECOVERY_SHA256=8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562 \
			TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
			MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
			HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
			bash "$policy_fixture/scripts/host/run-stable-recovery-live-gate.sh" \
			"$generation11_connected_action" >"$tmp/out" 2>"$tmp/err"
		then
			echo "FAIL generation-11 $generation11_policy_shape policy reached $generation11_connected_action" >&2
			exit 1
		fi
		if [[ $generation11_policy_shape == missing-file ]]; then
			expected_policy_error='unsafe or missing early temporary-boot policy input'
		elif [[ $generation11_policy_shape == malformed-header ]]; then
			expected_policy_error='malformed temporary-boot policy header'
		elif [[ $generation11_policy_shape == malformed-artifact-header ]]; then
			expected_policy_error='malformed artifact manifest header'
		elif [[ $generation11_policy_shape == missing-artifact-row ||
			$generation11_policy_shape == duplicate-artifact-row ]]; then
			expected_policy_error="artifact manifest does not uniquely list $generation11_image"
		elif [[ $generation11_policy_shape == wrong-basis ]]; then
			expected_policy_error="temporary boot policy basis does not match $generation11_image"
		elif [[ $generation11_policy_shape == denied-status ]]; then
			expected_policy_error="temporary boot policy does not allow $generation11_image"
		elif [[ $generation11_policy_shape == identity-mismatch ]]; then
			expected_policy_error='temporary boot artifact manifest identity is not allowlisted'
		elif [[ $generation11_policy_shape == readmitted-exact-basis ]]; then
			expected_policy_error='temporary boot artifact is recorded as consumed'
		elif [[ $generation11_policy_shape == policy-trailing-field ]]; then
			expected_policy_error='temporary boot policy row has trailing fields'
		elif [[ $generation11_policy_shape == artifact-trailing-field ]]; then
			expected_policy_error='temporary boot artifact row has trailing fields'
		else
			expected_policy_error="temporary boot policy does not uniquely list $generation11_image"
		fi
		grep -Fq "$expected_policy_error" "$tmp/err" ||
			{ echo "FAIL generation-11 $generation11_policy_shape returned the wrong policy rejection" >&2; exit 1; }
		if grep -Fq 'missing live-gate command' "$tmp/err"; then
			echo "FAIL generation-11 $generation11_policy_shape policy reached host inspection" >&2
			exit 1
		fi
	done
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

for generation10_policy_shape in \
	missing-file missing-row malformed-header malformed-artifact-header \
	duplicate wrong-basis readmitted-exact-basis
do
	policy_fixture=$tmp/generation10-policy-$generation10_policy_shape
	install -d -m 0755 "$policy_fixture/scripts/host" \
		"$policy_fixture/manifests"
	install -m 0755 "$gate" \
		"$policy_fixture/scripts/host/run-stable-recovery-live-gate.sh"
	install -m 0644 "$generated_power" \
		"$policy_fixture/scripts/host/generated-power-usb-active.sh"
	cp -- "$artifact_manifest" "$policy_fixture/manifests/artifacts.tsv"
	install -m 0644 "$boot_policy" \
		"$policy_fixture/manifests/temporary-boot-images.tsv"
	case $generation10_policy_shape in
		missing-file)
			rm -f -- "$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		missing-row)
			;;
		malformed-header)
			sed -i '1s/^name\tstatus\tbasis$/artifact\tstate\treason/' \
				"$policy_fixture/manifests/temporary-boot-images.tsv"
			;;
		malformed-artifact-header)
			printf '%s\tallow\t%s\n' "$generation10_image" \
				"$generation10_boot_basis" \
				>>"$policy_fixture/manifests/temporary-boot-images.tsv"
			sed -i \
				'1s/^name\tsize\tsha256\trole\ttracked$/artifact\tbytes\tdigest\tdisposition\tpresent/' \
				"$policy_fixture/manifests/artifacts.tsv"
			;;
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
		readmitted-exact-basis)
			printf '%s\tallow\t%s\n' "$generation10_image" \
				"$generation10_boot_basis" \
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
		if [[ $generation10_policy_shape == missing-file ]]; then
			expected_policy_error='unsafe or missing early temporary-boot policy input'
		elif [[ $generation10_policy_shape == malformed-header ]]; then
			expected_policy_error='malformed temporary-boot policy header'
		elif [[ $generation10_policy_shape == malformed-artifact-header ]]; then
			expected_policy_error='malformed artifact manifest header'
		elif [[ $generation10_policy_shape == wrong-basis ]]; then
			expected_policy_error="temporary boot policy basis does not match $generation10_image"
		elif [[ $generation10_policy_shape == readmitted-exact-basis ]]; then
			expected_policy_error='temporary boot artifact is recorded as consumed'
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

generation11_profiles=$(grep -o \
	'headless-diagnostic-generation11-[a-z0-9-]*' "$gate" | LC_ALL=C sort -u)
expected_generation11_profiles=$(printf '%s\n' \
	headless-diagnostic-generation11-live-v1 \
	headless-diagnostic-generation11-offline-v1 | LC_ALL=C sort)
[[ $generation11_profiles == "$expected_generation11_profiles" ]] ||
	{ echo 'FAIL an unreviewed generation-11 diagnostic profile is supported' >&2; exit 1; }
generation12_profiles=$(grep -o \
	'headless-diagnostic-generation12-[a-z0-9-]*' "$gate" | LC_ALL=C sort -u)
expected_generation12_profiles=$(printf '%s\n' \
	headless-diagnostic-generation12-live-v1 \
	headless-diagnostic-generation12-offline-v1 | LC_ALL=C sort)
[[ $generation12_profiles == "$expected_generation12_profiles" ]] ||
	{ echo 'FAIL generation-12 support is not exactly one offline and one live profile' >&2; exit 1; }
! grep -Eq \
	'headless-diagnostic-generation(1[3-9]|[2-9][0-9]|[1-9][0-9]{2,})-' \
	"$gate" ||
	{ echo 'FAIL an unreviewed future diagnostic generation is supported' >&2; exit 1; }

stage75_v2_case=$(awk '
	index($0, "\theadless-diagnostic-stage75-v2-superseded-offline-v1)") == 1 { capture = 1 }
	capture { print }
	capture && /^[[:space:]]*;;$/ { exit }
' "$gate")
stage75_v2_case_unindented=$(sed 's/^[[:space:]]*//' \
	<<<"$stage75_v2_case")
for stage75_v2_assignment in \
	expected_kernel=7a6c2a19c7a00a2699fd598b4fc3ad5fed680bf2cd9cb7cfa7bafa783d9fe563 \
	expected_raw=406b2497bff8174b01119e4bcfa4dddb544df3de8fdb9168d80e88708f20a995 \
	expected_initramfs=a38b61462468272c8d8409461d7318cfc442c3a4707a624e9f8ab1751ef047a4 \
	expected_control=242ac7fc4b7d7614cf5fe8a26162255c898de2f2aeef9cf70687d0d327c149e7 \
	expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800 \
	expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0 \
	expected_target_id=headless-netroot-early-diag-v2 \
	expected_bundle=headless-netroot-early-diag-v2 \
	expected_bundle_profile=diagnostic-initramfs-v1 \
	expected_avb_salt=406b2497bff8174b01119e4bcfa4dddb544df3de8fdb9168d80e88708f20a995 \
	expected_avb_digest=a1d19575dd21b6da3fd3cbb6c0f4ea33e312cc59ddc860889f1f54ef976e7b49
do
	grep -Fxq "$stage75_v2_assignment" \
		<<<"$stage75_v2_case_unindented" ||
		{ echo "FAIL stage-75 v2 case does not pin $stage75_v2_assignment" >&2; exit 1; }
done
for stage75_v2_identity in \
	2fb99ba07676d696fd3182da6bf62bd572b032b9e4bb90bff4b0d2a24544e156 \
	833899cb067a28d57e41c5a8291c7f5099c4f7fcc11316c2976d04a7b926e7de \
	58950b2101dca0702f2c436015bbb21eb6535e4e06f74808c2f8183c9da27268 \
	0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621
do
	grep -Fq "$stage75_v2_identity" <<<"$stage75_v2_case" ||
		{ echo "FAIL stage-75 v2 case omits identity $stage75_v2_identity" >&2; exit 1; }
done
grep -Fq \
	"fail 'superseded stage-75 v2 artifact profile is historical, offline-only, and not boot-authorized'" \
	<<<"$stage75_v2_case" ||
	{ echo 'FAIL stage-75 v2 profile is not offline-only' >&2; exit 1; }

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

generation11_case=$(awk '
	index($0, "\theadless-diagnostic-generation11-offline-v1") == 1 { capture = 1 }
	capture { print }
	capture && /^[[:space:]]*;;$/ { exit }
' "$gate")
generation11_case_unindented=$(sed 's/^[[:space:]]*//' \
	<<<"$generation11_case")
for generation11_assignment in \
	expected_kernel=895272e87d5a90ae6b9b8df71862b48d819479d5bbf2741fab002126e47d3eae \
	expected_raw=44c43e27ba0cdb646eb3a6327c519011090f64b1e76ec67e2ff9db469e6612b2 \
	expected_initramfs=3695ded23cc422f8363235884cb3cc402c0c90eeddee04d0603c09befd0f6a8c \
	expected_control=242ac7fc4b7d7614cf5fe8a26162255c898de2f2aeef9cf70687d0d327c149e7 \
	expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800 \
	expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0 \
	expected_target_id=headless-netroot-early-diag \
	expected_bundle=headless-netroot-early-diag-v1 \
	expected_bundle_profile=diagnostic-initramfs-v1 \
	expected_generation_record=4b62b7906ad40f2a36b52a9756a7250364dfe6d9eff4b0c57d25f60713145e49 \
	expected_avb_salt=00272b827ebb11f198be4758db4008cf534f592f0e63fc82c891cda3b4691c6d \
	expected_avb_digest=9ccf32a823f5a4685922ed42400bc024d7210412216537cfffb1c128e17febf9
do
	grep -Fxq "$generation11_assignment" \
		<<<"$generation11_case_unindented" ||
		{ echo "FAIL generation-11 case does not pin $generation11_assignment" >&2; exit 1; }
done
generation11_live_policy_block=$(awk '
	index($0, "if [[ $profile == headless-diagnostic-generation11-live-v1 ]]; then") { capture = 1 }
	capture { print }
	capture && /^[[:space:]]*fi$/ { exit }
' <<<"$generation11_case")
generation11_live_policy_unindented=$(sed 's/^[[:space:]]*//' \
	<<<"$generation11_live_policy_block")
for generation11_live_assignment in \
	expected_boot_image=build/stable-recovery-generation11-ncm-progress-20260804-a/repack/stable-recovery-a.avb.img \
	"expected_boot_basis='one generation-11 receive-only NCM-progress diagnostic lifecycle after connected preflight; remove after any result; never flash'"
do
	[[ $(grep -Fxc "$generation11_live_assignment" \
		<<<"$generation11_case_unindented") == 1 ]] ||
		{ echo "FAIL generation-11 case does not uniquely pin $generation11_live_assignment" >&2; exit 1; }
	grep -Fxq "$generation11_live_assignment" \
		<<<"$generation11_live_policy_unindented" ||
		{ echo "FAIL generation-11 live-only block does not pin $generation11_live_assignment" >&2; exit 1; }
done

generation12_case=$(awk '
	index($0, "\theadless-diagnostic-generation12-offline-v1") == 1 { capture = 1 }
	capture { print }
	capture && /^[[:space:]]*;;$/ { exit }
' "$gate")
generation12_case_unindented=$(sed 's/^[[:space:]]*//' \
	<<<"$generation12_case")
for generation12_assignment in \
	expected_kernel=895272e87d5a90ae6b9b8df71862b48d819479d5bbf2741fab002126e47d3eae \
	expected_raw=44c43e27ba0cdb646eb3a6327c519011090f64b1e76ec67e2ff9db469e6612b2 \
	expected_initramfs=3695ded23cc422f8363235884cb3cc402c0c90eeddee04d0603c09befd0f6a8c \
	expected_control=242ac7fc4b7d7614cf5fe8a26162255c898de2f2aeef9cf70687d0d327c149e7 \
	expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800 \
	expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0 \
	expected_target_id=headless-netroot-early-diag \
	expected_bundle=headless-netroot-early-diag-v1 \
	expected_bundle_profile=diagnostic-initramfs-v1 \
	expected_generation_record=2b8a05d4655a4794ae4ee5ce9fe1279b194dec39d3a4bfcb93904cc665192c72 \
	expected_avb_salt=728dcc59f29e0fbf83165b6979bb5dc68571b0d0e0236993fc9b8f2dd98084c9 \
	expected_avb_digest=31d1ec59526d876de914330004d42752cfc7b24bd069b955d64687ef750b526d
do
	grep -Fxq "$generation12_assignment" \
		<<<"$generation12_case_unindented" ||
		{ echo "FAIL generation-12 case does not pin $generation12_assignment" >&2; exit 1; }
done
grep -Fq \
	"fail 'generation-12 is consumed and cannot enter connected preflight or boot'" \
	<<<"$generation12_case" ||
	{ echo 'FAIL generation-12 case does not permanently reject connected actions' >&2; exit 1; }
! grep -Fq 'expected_boot_image=build/stable-recovery-generation12' \
	<<<"$generation12_case" ||
	{ echo 'FAIL consumed generation-12 still pins a boot-admission image' >&2; exit 1; }

late_exact_admission=$(awk '
	index($0, "\tif [[ -n $expected_boot_image ]]; then") == 1 {
		capture = 1
	}
	capture { print }
	capture && $0 == "\telse" { exit }
' "$gate")
for snapshot_input in \
	'"$early_boot_policy_snapshot"' \
	'"$early_artifact_manifest_snapshot"'
do
	grep -Fq "$snapshot_input" <<<"$late_exact_admission" ||
		{ echo "FAIL late exact admission does not reuse $snapshot_input" >&2; exit 1; }
done
! grep -Fq '"$boot_policy" "$artifact_manifest"' \
	<<<"$late_exact_admission" ||
	{ echo 'FAIL late exact admission rereads live policy paths' >&2; exit 1; }

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
	install -m 0644 "$generated_power" \
		"$policy_fixture/scripts/host/generated-power-usb-active.sh"
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
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation12-live-v1 \
	RECOVERY_SHA256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
	TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
	MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	BUNDLE=headless-netroot-early-diag-v1 \
	bash "$gate" policy-preflight >"$tmp/out" 2>"$tmp/err"
then
	echo 'FAIL generation-12 live profile accepted a wrong recovery identity' >&2
	exit 1
fi
grep -Fq 'generation-12 diagnostic recovery image is not pinned' "$tmp/err"

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
	install -m 0644 "$generated_power" \
		"$policy_fixture/scripts/host/generated-power-usb-active.sh"
	cp -- "$artifact_manifest" "$policy_fixture/manifests/artifacts.tsv"
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

run_diagnostic_policy() {
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
	generation3_policy=$(run_diagnostic_policy \
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
		if run_diagnostic_policy \
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
	generation4_policy=$(run_diagnostic_policy \
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
		if run_diagnostic_policy \
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
	generation5_policy=$(run_diagnostic_policy \
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
		if run_diagnostic_policy \
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
	generation6_policy=$(run_diagnostic_policy \
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
		if run_diagnostic_policy \
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
	generation7_policy=$(run_diagnostic_policy \
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
		if run_diagnostic_policy "$generation7_profile" "${mutation[@]}" \
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
	generation8_policy=$(run_diagnostic_policy \
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
		if run_diagnostic_policy "$generation8_profile" "${mutation[@]}" \
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
	generation9_policy=$(run_diagnostic_policy \
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
		if run_diagnostic_policy "$generation9_profile" \
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
	generation10_policy=$(run_diagnostic_policy \
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
		if run_diagnostic_policy "$generation10_profile" \
			"${mutation[@]}" >"$tmp/out" 2>"$tmp/err"; then
			echo "FAIL $generation10_profile accepted wrong ${generation10_fields[$index]}" >&2
			exit 1
		fi
		grep -Fq "${generation10_errors[$index]}" "$tmp/err" ||
			{ echo "FAIL $generation10_profile wrong ${generation10_fields[$index]} returned the wrong rejection" >&2; exit 1; }
	done
done

generation11_exact=(
	8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76
	0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621
	headless-netroot-early-diag-v1
)
generation11_fields=(recovery trust manifest host-verifier bundle)
generation11_errors=(
	'generation-11 diagnostic recovery image is not pinned'
	'generation-11 diagnostic trust root is not pinned'
	'generation-11 diagnostic runtime manifest is not pinned'
	'generation-11 diagnostic host verifier is not pinned'
	'profile requires bundle=headless-netroot-early-diag-v1'
)
[[ ${#generation11_fields[@]} -eq ${#generation11_exact[@]} &&
	${#generation11_errors[@]} -eq ${#generation11_exact[@]} ]] ||
	{ echo 'FAIL generation-11 policy mutation matrix is inconsistent' >&2; exit 1; }
for generation11_profile in \
	headless-diagnostic-generation11-offline-v1 \
	headless-diagnostic-generation11-live-v1
do
	generation11_policy=$(run_diagnostic_policy \
		"$generation11_profile" "${generation11_exact[@]}")
	grep -Fxq "recovery_profile=$generation11_profile" \
		<<<"$generation11_policy" ||
		{ echo "FAIL $generation11_profile policy omitted the exact profile" >&2; exit 1; }
	grep -Fxq \
		'recovery_sha256=8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562' \
		<<<"$generation11_policy" ||
		{ echo "FAIL $generation11_profile policy omitted the exact recovery identity" >&2; exit 1; }
	grep -Fxq 'authority=none' <<<"$generation11_policy" ||
		{ echo "FAIL $generation11_profile policy granted authority" >&2; exit 1; }
	grep -Fxq 'result=PASS' <<<"$generation11_policy" ||
		{ echo "FAIL $generation11_profile policy did not pass" >&2; exit 1; }
	for index in "${!generation11_fields[@]}"; do
		mutation=("${generation11_exact[@]}")
		if ((index == 4)); then
			mutation[$index]=wrong-generation11-bundle
		else
			mutation[$index]=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
		fi
		if run_diagnostic_policy "$generation11_profile" \
			"${mutation[@]}" >"$tmp/out" 2>"$tmp/err"; then
			echo "FAIL $generation11_profile accepted wrong ${generation11_fields[$index]}" >&2
			exit 1
		fi
		grep -Fq "${generation11_errors[$index]}" "$tmp/err" ||
			{ echo "FAIL $generation11_profile wrong ${generation11_fields[$index]} returned the wrong rejection" >&2; exit 1; }
	done
done

generation12_exact=(
	615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6
	f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76
	0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621
	headless-netroot-early-diag-v1
)
generation12_fields=(recovery trust manifest host-verifier bundle)
generation12_errors=(
	'generation-12 diagnostic recovery image is not pinned'
	'generation-12 diagnostic trust root is not pinned'
	'generation-12 diagnostic runtime manifest is not pinned'
	'generation-12 diagnostic host verifier is not pinned'
	'profile requires bundle=headless-netroot-early-diag-v1'
)
[[ ${#generation12_fields[@]} -eq ${#generation12_exact[@]} &&
	${#generation12_errors[@]} -eq ${#generation12_exact[@]} ]] ||
	{ echo 'FAIL generation-12 policy mutation matrix is inconsistent' >&2; exit 1; }
for generation12_profile in \
	headless-diagnostic-generation12-offline-v1 \
	headless-diagnostic-generation12-live-v1
do
	generation12_policy=$(run_diagnostic_policy \
		"$generation12_profile" "${generation12_exact[@]}")
	grep -Fxq "recovery_profile=$generation12_profile" \
		<<<"$generation12_policy" ||
		{ echo "FAIL $generation12_profile policy omitted the exact profile" >&2; exit 1; }
	grep -Fxq \
		'recovery_sha256=615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6' \
		<<<"$generation12_policy" ||
		{ echo "FAIL $generation12_profile policy omitted the exact recovery identity" >&2; exit 1; }
	grep -Fxq 'authority=none' <<<"$generation12_policy" ||
		{ echo "FAIL $generation12_profile policy granted authority" >&2; exit 1; }
	grep -Fxq 'result=PASS' <<<"$generation12_policy" ||
		{ echo "FAIL $generation12_profile policy did not pass" >&2; exit 1; }
	for index in "${!generation12_fields[@]}"; do
		mutation=("${generation12_exact[@]}")
		if ((index == 4)); then
			mutation[$index]=wrong-generation12-bundle
		else
			mutation[$index]=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
		fi
		if run_diagnostic_policy "$generation12_profile" \
			"${mutation[@]}" >"$tmp/out" 2>"$tmp/err"; then
			echo "FAIL $generation12_profile accepted wrong ${generation12_fields[$index]}" >&2
			exit 1
		fi
		grep -Fq "${generation12_errors[$index]}" "$tmp/err" ||
			{ echo "FAIL $generation12_profile wrong ${generation12_fields[$index]} returned the wrong rejection" >&2; exit 1; }
	done
done

# The hostile policy matrix above checks both names in every offline/live
# pair. Each pair shares one artifact contract in the gate, so verify each
# distinct retained byte tree once. Twin-root comparisons below prove when a
# second build tree has the same byte inputs; bundle-a/b remain separate when
# they are not covered by those comparisons.
if [[ -d $generation3_root ]]; then
	generation3_artifact=$(
		env -i PATH="$PATH" HOME="$HOME" \
			ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation3-offline-v1 \
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
		'PASS stable-recovery artifact preflight profile=headless-diagnostic-generation3-offline-v1 image_sha256=eb514a57eb8cf27c5864a01d64256e77919f2e12604ea45f7daba02c52cd77b6' \
		<<<"$generation3_artifact"
else
	echo 'SKIP generation-3 retained artifact preflight: ignored build tree absent' >&2
fi

if [[ -d $generation4_root && -d $generation3_root ]]; then
	generation4_artifact=$(
		env -i PATH="$PATH" HOME="$HOME" \
			ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation4-offline-v1 \
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
		'PASS stable-recovery artifact preflight profile=headless-diagnostic-generation4-offline-v1 image_sha256=220e85568d1e92d9dbe33e3405f28c9b23dc8520b9e1ab2c81a30085e9cb270d' \
		<<<"$generation4_artifact"
else
	echo 'SKIP generation-4 artifact preflight: ignored build trees absent' >&2
fi

if [[ -d $generation5_root && -d $generation3_root ]]; then
	generation5_artifact=$(
		env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation5-offline-v1 \
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
		'PASS stable-recovery artifact preflight profile=headless-diagnostic-generation5-offline-v1 image_sha256=abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a' \
		<<<"$generation5_artifact"
else
	echo 'SKIP generation-5 artifact preflight: ignored build trees absent' >&2
fi

if [[ -d $generation6_root && -d $generation3_root ]]; then
	generation6_artifact=$(
		env -i PATH="$PATH" HOME="$HOME" \
			ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation6-offline-v1 \
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
		'PASS stable-recovery artifact preflight profile=headless-diagnostic-generation6-offline-v1 image_sha256=6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398' \
		<<<"$generation6_artifact"
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
	generation7_artifact=$(
		env -i PATH="$PATH" HOME="$HOME" \
			ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation7-offline-v1 \
			LIVE_BUILD_ROOT="$generation7_root_a" \
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
		'PASS stable-recovery artifact preflight profile=headless-diagnostic-generation7-offline-v1 image_sha256=d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901' \
		<<<"$generation7_artifact"

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
	generation8_artifact=$(
		env -i PATH="$PATH" HOME="$HOME" \
			ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation8-offline-v1 \
			LIVE_BUILD_ROOT="$generation8_root_a" \
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
		'PASS stable-recovery artifact preflight profile=headless-diagnostic-generation8-offline-v1 image_sha256=f102d53c3b64ac8407ebe81b06213899c5907666bd9ed79b149dc91ec69f2415' \
		<<<"$generation8_artifact"

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
	done
	generation9_artifact=$(
		env -i PATH="$PATH" HOME="$HOME" \
			ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation9-offline-v1 \
			LIVE_BUILD_ROOT="$generation9_root_a" \
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
		'PASS stable-recovery artifact preflight profile=headless-diagnostic-generation9-offline-v1 image_sha256=b458e64bca6ab3b94aa88ceb968ed306625e4282836bbad57f9e22689482d008' \
		<<<"$generation9_artifact"

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
	for generation10_suffix in a b; do
		if [[ $generation10_suffix == a ]]; then
			generation10_root=$generation10_root_a
		else
			generation10_root=$generation10_root_b
		fi
		generation10_artifact=$(
			env -i PATH="$PATH" HOME="$HOME" \
					ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation10-offline-v1 \
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
			'PASS stable-recovery artifact preflight profile=headless-diagnostic-generation10-offline-v1 image_sha256=b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51' \
			<<<"$generation10_artifact" ||
			{ echo "FAIL generation-10 tree $generation10_suffix did not pass artifact preflight" >&2; exit 1; }
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

if [[ -d $generation11_root_a || -d $generation11_root_b ||
	-d $generation11_base ]]; then
	[[ -d $generation11_root_a && -d $generation11_root_b &&
		-d $generation11_base && -d $generation11_bundle_base ]] ||
		{ echo 'FAIL generation-11 production inputs are asymmetric' >&2; exit 1; }
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
		cmp "$generation11_root_a/$relative" "$generation11_root_b/$relative"
	done
	for generation11_suffix in a b; do
		if [[ $generation11_suffix == a ]]; then
			generation11_root=$generation11_root_a
		else
			generation11_root=$generation11_root_b
		fi
		generation11_artifact=$(
			env -i PATH="$PATH" HOME="$HOME" \
					ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation11-offline-v1 \
					LIVE_BUILD_ROOT="$generation11_root" \
					RECOVERY_COMPONENT_ROOT="$generation11_base/recovery" \
					TRUST_KEY="$generation11_base/recovery/ephemeral-public.raw" \
					BUNDLE_ROOT="$generation11_bundle_base/bundle-$generation11_suffix" \
					BUNDLE=headless-netroot-early-diag-v1 \
					RECOVERY_SHA256=8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562 \
					TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
					MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
					HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
					bash "$gate" artifact-preflight
		)
		grep -Fxq \
			'PASS stable-recovery artifact preflight profile=headless-diagnostic-generation11-offline-v1 image_sha256=8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562' \
			<<<"$generation11_artifact" ||
			{ echo "FAIL generation-11 tree $generation11_suffix did not pass artifact preflight" >&2; exit 1; }
	done

	generation11_mutation=$build_tmp/generation11-record-mutation
	cp -a --reflink=auto "$generation11_root_a" "$generation11_mutation"
	chmod -R u+rwX "$generation11_mutation"
	sed -i 's/^generation=11$/generation=10/' \
		"$generation11_mutation/avb-generation.txt"
	if env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation11-offline-v1 \
		LIVE_BUILD_ROOT="$generation11_mutation" \
		RECOVERY_COMPONENT_ROOT="$generation11_base/recovery" \
		TRUST_KEY="$generation11_base/recovery/ephemeral-public.raw" \
		BUNDLE_ROOT="$generation11_bundle_base/bundle-a" \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=8472b206476e9a3143dec000b7f2369678c11248ad10203ef0646389e6bcf562 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" artifact-preflight >"$tmp/out" 2>"$tmp/err"; then
		echo 'FAIL generation-11 artifact preflight accepted a mutated generation record' >&2
		exit 1
	fi
	grep -Fq "identity mismatch: $generation11_mutation/avb-generation.txt" \
		"$tmp/err" ||
		{ echo 'FAIL generation-11 record mutation returned the wrong rejection' >&2; exit 1; }
else
	echo 'SKIP generation-11 twin artifact preflight: ignored build trees absent' >&2
fi

if [[ -d $generation12_root_a || -d $generation12_root_b ||
	-d $generation11_root_a ]]; then
	[[ -d $generation12_root_a && -d $generation12_root_b &&
		-d $generation11_root_a && -d $generation12_base &&
		-d $generation12_bundle_base ]] ||
		{ echo 'FAIL generation-12 production inputs are asymmetric' >&2; exit 1; }
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
		cmp "$generation12_root_a/$relative" "$generation12_root_b/$relative"
	done
	for suffix in a b; do
		cmp "$generation12_root_a/repack/stable-recovery-$suffix.raw.img" \
			"$generation11_root_a/repack/stable-recovery-$suffix.raw.img"
		cmp "$generation12_root_a/wrapper-$suffix/asus-kexec-stage/.config" \
			"$generation11_root_a/wrapper-$suffix/asus-kexec-stage/.config"
		cmp "$generation12_root_a/wrapper-$suffix/asus-kexec-stage/arch/arm64/boot/Image" \
			"$generation11_root_a/wrapper-$suffix/asus-kexec-stage/arch/arm64/boot/Image"
		cmp "$generation12_root_a/wrapper-$suffix/rog5-kexec-stage-initramfs.cpio.gz" \
			"$generation11_root_a/wrapper-$suffix/rog5-kexec-stage-initramfs.cpio.gz"
		! cmp -s "$generation12_root_a/repack/stable-recovery-$suffix.avb.img" \
			"$generation11_root_a/repack/stable-recovery-$suffix.avb.img" ||
			{ echo "FAIL generation-12 reused Generation-11 twin-$suffix AVB" >&2; exit 1; }
	done
	for generation12_suffix in a b; do
		if [[ $generation12_suffix == a ]]; then
			generation12_root=$generation12_root_a
		else
			generation12_root=$generation12_root_b
		fi
		generation12_artifact=$(
			env -i PATH="$PATH" HOME="$HOME" \
					ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation12-offline-v1 \
					LIVE_BUILD_ROOT="$generation12_root" \
					RECOVERY_COMPONENT_ROOT="$generation12_base/recovery" \
					TRUST_KEY="$generation12_base/recovery/ephemeral-public.raw" \
					BUNDLE_ROOT="$generation12_bundle_base/bundle-$generation12_suffix" \
					BUNDLE=headless-netroot-early-diag-v1 \
					RECOVERY_SHA256=615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6 \
					TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
					MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
					HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
					bash "$gate" artifact-preflight
		)
		grep -Fxq \
			'PASS stable-recovery artifact preflight profile=headless-diagnostic-generation12-offline-v1 image_sha256=615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6' \
			<<<"$generation12_artifact" ||
			{ echo "FAIL generation-12 tree $generation12_suffix did not pass artifact preflight" >&2; exit 1; }
	done

	generation12_mutation=$build_tmp/generation12-record-mutation
	cp -a --reflink=auto "$generation12_root_a" "$generation12_mutation"
	chmod -R u+rwX "$generation12_mutation"
	sed -i 's/^generation=12$/generation=11/' \
		"$generation12_mutation/avb-generation.txt"
	if env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-generation12-offline-v1 \
		LIVE_BUILD_ROOT="$generation12_mutation" \
		RECOVERY_COMPONENT_ROOT="$generation12_base/recovery" \
		TRUST_KEY="$generation12_base/recovery/ephemeral-public.raw" \
		BUNDLE_ROOT="$generation12_bundle_base/bundle-a" \
		BUNDLE=headless-netroot-early-diag-v1 \
		RECOVERY_SHA256=615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6 \
		TRUST_KEY_SHA256=f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b \
		MANIFEST_SHA256=4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" artifact-preflight >"$tmp/out" 2>"$tmp/err"; then
		echo 'FAIL generation-12 artifact preflight accepted a mutated generation record' >&2
		exit 1
	fi
	grep -Fq "identity mismatch: $generation12_mutation/avb-generation.txt" \
		"$tmp/err" ||
		{ echo 'FAIL generation-12 record mutation returned the wrong rejection' >&2; exit 1; }
else
	echo 'SKIP generation-12 twin artifact preflight: ignored build trees absent' >&2
fi

run_stage75_v2_policy() {
	local selected_bundle=$1 selected_image=$2 selected_manifest=$3
	env -i PATH="$PATH" HOME="$HOME" \
		ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-stage75-v2-superseded-offline-v1 \
		BUNDLE="$selected_bundle" \
		RECOVERY_SHA256="$selected_image" \
		TRUST_KEY_SHA256=58950b2101dca0702f2c436015bbb21eb6535e4e06f74808c2f8183c9da27268 \
		MANIFEST_SHA256="$selected_manifest" \
		HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
		bash "$gate" policy-preflight
}

run_stage75_v2_policy \
	headless-netroot-early-diag-v2 \
	833899cb067a28d57e41c5a8291c7f5099c4f7fcc11316c2976d04a7b926e7de \
	2fb99ba07676d696fd3182da6bf62bd572b032b9e4bb90bff4b0d2a24544e156 \
	>"$tmp/out" 2>"$tmp/err"
grep -Fxq 'recovery_profile=headless-diagnostic-stage75-v2-superseded-offline-v1' \
	"$tmp/out" ||
	{ echo 'FAIL exact stage-75 v2 policy preflight omitted its profile' >&2; exit 1; }
grep -Fxq 'target_id=headless-netroot-early-diag-v2' "$tmp/out" ||
	{ echo 'FAIL exact stage-75 v2 policy preflight omitted its target' >&2; exit 1; }
grep -Fxq 'authority=none' "$tmp/out" ||
	{ echo 'FAIL exact stage-75 v2 policy preflight claimed authority' >&2; exit 1; }

if run_stage75_v2_policy \
	headless-netroot-early-diag-v1 \
	833899cb067a28d57e41c5a8291c7f5099c4f7fcc11316c2976d04a7b926e7de \
	2fb99ba07676d696fd3182da6bf62bd572b032b9e4bb90bff4b0d2a24544e156 \
	>"$tmp/out" 2>"$tmp/err"; then
	echo 'FAIL stage-75 v2 policy accepted the legacy bundle identity' >&2
	exit 1
fi
grep -Fq 'profile requires bundle=headless-netroot-early-diag-v2' "$tmp/err"

if run_stage75_v2_policy \
	headless-netroot-early-diag-v2 \
	833899cb067a28d57e41c5a8291c7f5099c4f7fcc11316c2976d04a7b926e7de \
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	>"$tmp/out" 2>"$tmp/err"; then
	echo 'FAIL stage-75 v2 policy accepted the legacy manifest identity' >&2
	exit 1
fi
grep -Fq 'stage-75 v2 diagnostic runtime manifest is not pinned' "$tmp/err"

if env -i PATH="$PATH" HOME="$HOME" \
	ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-stage75-v2-superseded-offline-v1 \
	LIVE_BUILD_ROOT="$repo/build/unused-stage75-v2-live-root" \
	RECOVERY_COMPONENT_ROOT="$repo/build/unused-stage75-v2-component-root" \
	TRUST_KEY="$repo/build/unused-stage75-v2-trust-key" \
	BUNDLE_ROOT=/var/lib/rog5-recovery-bundles \
	BUNDLE=headless-netroot-early-diag-v2 \
	RECOVERY_SHA256=833899cb067a28d57e41c5a8291c7f5099c4f7fcc11316c2976d04a7b926e7de \
	TRUST_KEY_SHA256=58950b2101dca0702f2c436015bbb21eb6535e4e06f74808c2f8183c9da27268 \
	MANIFEST_SHA256=2fb99ba07676d696fd3182da6bf62bd572b032b9e4bb90bff4b0d2a24544e156 \
	HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
	bash "$gate" preflight >"$tmp/out" 2>"$tmp/err"; then
	echo 'FAIL stage-75 v2 offline profile reached a connected preflight' >&2
	exit 1
fi
grep -Fq 'superseded stage-75 v2 artifact profile is historical, offline-only, and not boot-authorized' \
	"$tmp/err"

if [[ -d $stage75_v2_root ]]; then
	command -v bsdtar >/dev/null ||
		{ echo 'FAIL retained stage-75 v2 inspection requires bsdtar' >&2; exit 1; }
	stage75_v2_target_init=$tmp/stage75-v2-superseded-init
	bsdtar -xOf \
		"$stage75_v2_root/bundle-a/headless-netroot-early-diag-v2/initramfs.cpio.gz" \
		init >"$stage75_v2_target_init"
	grep -Fq 'while [ "$attempt" -lt 30 ]; do' "$stage75_v2_target_init" &&
		grep -Fq '[ -n "$udc" ] || udc=$(basename "$candidate")' \
			"$stage75_v2_target_init" ||
		{ echo 'FAIL superseded stage-75 profile no longer exposes its old target payload' >&2; exit 1; }
	! grep -Fq 'select_expected_udc' "$stage75_v2_target_init" ||
		{ echo 'FAIL superseded stage-75 profile unexpectedly certifies the corrected UDC selector' >&2; exit 1; }
	stage75_v2_artifact=$(
		env -i PATH="$PATH" HOME="$HOME" \
			ROG5_STABLE_RECOVERY_PROFILE=headless-diagnostic-stage75-v2-superseded-offline-v1 \
			LIVE_BUILD_ROOT="$stage75_v2_root/wrapper" \
			RECOVERY_COMPONENT_ROOT="$stage75_v2_root/recovery" \
			TRUST_KEY="$stage75_v2_root/recovery/ephemeral-public.raw" \
			BUNDLE_ROOT="$stage75_v2_root/bundle-a" \
			BUNDLE=headless-netroot-early-diag-v2 \
			RECOVERY_SHA256=833899cb067a28d57e41c5a8291c7f5099c4f7fcc11316c2976d04a7b926e7de \
			TRUST_KEY_SHA256=58950b2101dca0702f2c436015bbb21eb6535e4e06f74808c2f8183c9da27268 \
			MANIFEST_SHA256=2fb99ba07676d696fd3182da6bf62bd572b032b9e4bb90bff4b0d2a24544e156 \
			HOST_VERIFIER_SHA256=0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621 \
			bash "$gate" artifact-preflight
	)
	grep -Fxq \
		'PASS stable-recovery artifact preflight profile=headless-diagnostic-stage75-v2-superseded-offline-v1 image_sha256=833899cb067a28d57e41c5a8291c7f5099c4f7fcc11316c2976d04a7b926e7de' \
		<<<"$stage75_v2_artifact" ||
		{ echo 'FAIL retained stage-75 v2 artifact preflight omitted its exact pass marker' >&2; exit 1; }
else
	echo 'SKIP retained stage-75 v2 artifact preflight: ignored build tree absent' >&2
fi

run_legacy_diagnostic_policy() {
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

if run_legacy_diagnostic_policy \
	headless-netroot-early-diag-v1 \
	70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1 \
	9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630 \
	>"$tmp/out" 2>"$tmp/err"; then
	echo 'FAIL diagnostic artifact policy accepted the normal r2 manifest' >&2
	exit 1
fi
grep -Fq 'diagnostic runtime manifest is not allowlisted' "$tmp/err"

if run_legacy_diagnostic_policy \
	headless-ssh-network-root-v3-r2 \
	70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1 \
	4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76 \
	>"$tmp/out" 2>"$tmp/err"; then
	echo 'FAIL diagnostic artifact policy accepted the normal r2 bundle' >&2
	exit 1
fi
grep -Fq 'profile requires bundle=headless-netroot-early-diag-v1' "$tmp/err"

if run_legacy_diagnostic_policy \
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
	'headless-diagnostic-generation11-offline-v1' \
	'headless-diagnostic-generation11-live-v1' \
	'headless-diagnostic-generation12-offline-v1' \
	'headless-diagnostic-generation12-live-v1' \
	'headless-diagnostic-stage75-v2-superseded-offline-v1' \
	'retention-host-rendezvous-v11-mainline-udc-execution-v2' \
	'expected_boot_image=build/mainline-udc-v11-generation9-wrapper-20260811-r1/repack/stable-recovery-a.avb.img' \
	'2fa17df6ac83daa767bbe35220ff48062c43cdbc6f3945e7c2d0018608130ffb' \
	'expected_generation_record=05363adb23eb0b542e6958d1743370bbbcf2fa3223b0d91e27dde4667de49548' \
	'expected_avb_salt=b83baa48af9b34ef6c351b8f33ee87302e22ad1c3f4fec6f2ffea671199190dd' \
	'expected_avb_digest=61a852924d7cdef76695e6ce90f6f00ed1cc0461c3e6bfa8d6d58893505fa7a3' \
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
	'superseded stage-75 v2 artifact profile is historical, offline-only, and not boot-authorized' \
	'generation-10 diagnostic profile is offline-only and not boot-authorized' \
	'generation-10 connected action requires the one-shot lifecycle controller' \
	'generation-11 diagnostic profile is offline-only and not boot-authorized' \
	'generation-11 connected action requires the one-shot lifecycle controller' \
	'generation-12 diagnostic profile is offline-only and not boot-authorized' \
		'generation-12 is consumed and cannot enter connected preflight or boot' \
	'temporary boot artifact is recorded as consumed' \
	'temporary boot artifact role does not match the pinned profile' \
	'temporary boot artifact tracked state does not match the pinned profile' \
	'early temporary-boot admission snapshot is absent' \
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
	'expected_generation_record=2b8a05d4655a4794ae4ee5ce9fe1279b194dec39d3a4bfcb93904cc665192c72' \
	'expected_avb_salt=728dcc59f29e0fbf83165b6979bb5dc68571b0d0e0236993fc9b8f2dd98084c9' \
	'expected_avb_digest=31d1ec59526d876de914330004d42752cfc7b24bd069b955d64687ef750b526d' \
	'615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6' \
	'expected_boot_image=build/stable-recovery-generation10-prepare-progress-20260803-a/repack/stable-recovery-a.avb.img' \
	"expected_boot_basis='one generation-10 PREPARE-progress-instrumented diagnostic lifecycle after connected preflight; remove after any result; never flash'" \
	'expected_boot_image=build/stable-recovery-generation11-ncm-progress-20260804-a/repack/stable-recovery-a.avb.img' \
	"expected_boot_basis='one generation-11 receive-only NCM-progress diagnostic lifecycle after connected preflight; remove after any result; never flash'" \
	'expected_generation_record=4b62b7906ad40f2a36b52a9756a7250364dfe6d9eff4b0c57d25f60713145e49' \
	'expected_avb_salt=00272b827ebb11f198be4758db4008cf534f592f0e63fc82c891cda3b4691c6d' \
	'expected_avb_digest=9ccf32a823f5a4685922ed42400bc024d7210412216537cfffb1c128e17febf9' \
	'expected_kernel=895272e87d5a90ae6b9b8df71862b48d819479d5bbf2741fab002126e47d3eae' \
	'expected_raw=44c43e27ba0cdb646eb3a6327c519011090f64b1e76ec67e2ff9db469e6612b2' \
	'expected_initramfs=3695ded23cc422f8363235884cb3cc402c0c90eeddee04d0603c09befd0f6a8c' \
	'expected_control=242ac7fc4b7d7614cf5fe8a26162255c898de2f2aeef9cf70687d0d327c149e7' \
	'expected_fetcher=77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800' \
	'expected_verifier=5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0' \
	'expected_target_id=headless-netroot-early-diag' \
	'expected_bundle_profile=diagnostic-initramfs-v1' \
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
	'expected_bundle=headless-netroot-early-diag-v2' \
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
	'initramfs_contract=historical-pinned-v1' \
	'verify-stable-recovery-initramfs.sh' \
	'"$trust_key" "$initramfs_contract" "$initramfs_verifier_expected"' \
	'--bundle-root "$bundle_root"' \
	'verify_image --image "$inspection/recovery.img"' \
	'cp --reflink=never -- "$raw" "$inspection/boot.img"' \
	'getvar product' \
	'verified-fastboot-boot.py' \
	'cmp -n "$raw_size" "$raw" "$image"' \
	'find_rog5_acm ROG5_recovery' \
	'ROG5_RETENTION_BOOT_RESULT' \
	'ROG5_EXPECTED_USB_LOCATION' \
	'udevadm info --query=path --name="$acm"' \
	'ROG5_RETENTION_BOOT_RESULT_V1 action=execution-boot' \
	'stop ModemManager'
do
	grep -Fq -- "$required" "$gate"
done

retention_location_function=$(
	awk '
		/^verify_retention_acm_location\(\) \{/ { copy=1 }
		copy { print }
		copy && /^}/ { exit }
	' "$gate"
)
[[ $retention_location_function == verify_retention_acm_location* ]] ||
	{ echo 'FAIL retention ACM location verifier is not extractable' >&2; exit 1; }
run_retention_location_fixture() {
	local observed=$1 expected=$2
	(
		fail() { exit 1; }
		udevadm() { printf '%s\n' "$observed"; }
		eval "$retention_location_function"
		verify_retention_acm_location /dev/ttyACM0 "$expected"
	)
}
retention_location='pci0000:00/0000:00:14.0/usb1/1-3'
run_retention_location_fixture \
	"/devices/$retention_location/1-3:1.2/tty/ttyACM0" \
	"$retention_location"
for hostile_pair in \
	"/devices/pci0000:00/other/1-3:1.2/tty/ttyACM0|$retention_location" \
	"/devices/$retention_location/1-4:1.2/tty/ttyACM0|$retention_location" \
	"/devices/$retention_location/1-3:1.2/tty/ttyACM1|$retention_location" \
	"/devices/$retention_location/1-3:1.2/tty/ttyACM0|pci/../usb1/1-3"
do
	IFS='|' read -r observed expected <<<"$hostile_pair"
	if run_retention_location_fixture "$observed" "$expected"; then
		echo 'FAIL retention ACM location verifier accepted hostile ancestry' >&2
		exit 1
	fi
done

retention_guard_line=$(grep -n -m1 '^\[\[ \$retention_boot_result == 0' "$gate" | cut -d: -f1)
retention_location_guard_line=$(grep -n -m1 '^if \[\[ \$retention_boot_result == 1 \]\]; then' "$gate" | cut -d: -f1)
temporary_boot_line=$(grep -n -m1 'verified-fastboot-boot.py' "$gate" | cut -d: -f1)
[[ -n $retention_guard_line && -n $retention_location_guard_line &&
	-n $temporary_boot_line && $retention_guard_line -lt $temporary_boot_line &&
	$retention_location_guard_line -lt $temporary_boot_line ]] ||
	{ echo 'FAIL retention result inputs are not validated before temporary boot' >&2; exit 1; }

initramfs_hash_line=$(
	grep -n 'check_hash "$source_initramfs" "$expected_initramfs"' "$gate" |
		cut -d: -f1
)
initramfs_verify_line=$(
	grep -nF '"$initramfs_verifier" \' "$gate" | cut -d: -f1
)
[[ $initramfs_hash_line =~ ^[0-9]+$ &&
	$initramfs_verify_line =~ ^[0-9]+$ &&
	$initramfs_hash_line -lt $initramfs_verify_line ]] ||
	{ echo 'FAIL historical init verification can run before exact archive identity' >&2; exit 1; }

! grep -Fq 'consume-exact-boot-claim.py' "$gate" ||
	{ echo 'FAIL consumed generation-12 still reaches a claim-consumer path' >&2; exit 1; }
grep -Fq 'lifecycle claim root is unsafe or absent' \
	"$repo/scripts/host/consume-exact-boot-claim.py" ||
	{ echo 'FAIL exact-record claim consumer does not fail closed on its state root' >&2; exit 1; }

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
