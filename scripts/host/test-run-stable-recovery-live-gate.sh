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
awk -F '\t' '
	NR == 1 {
		if ($1 != "name" || $2 != "status" || $3 != "basis" || NF != 3)
			exit 1
		next
	}
	$1 == "build/observation-recovery-mainline-udc-v11-generation10-20260811-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "allow" &&
		$3 == "one exact NFS-xattr retention observation recovery; RAM-only; externally consumed exact claim required; never flash or retry after entry" && NF == 3 { observer++ ; next }
	$1 == "build/headless-core-v21-generation21-20260812-r1/repack/stable-recovery-a.avb.img" &&
		$2 == "allow" &&
		$3 == "one exact headless-core Arch SSH recovery with power-key indicator; RAM-only; externally consumed exact claim required; never flash or retry after entry" && NF == 3 { core++ ; next }
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
		$2 == "allow" &&
		$3 == "one exact read-only local-image Arch cycle restoring the accepted four deferred UFS modules omitted from Generation 65; UFS failures report bounded stage detail, both ext4 layers remain ro,noload, no write window is entered, and the persisted Generation 64 marker remains pinned; RAM-only kernel/recovery; externally consumed exact claim required; never flash or retry after entry" && NF == 3 { generation66++ ; next }
	$1 == "artifacts/recovery-stage-v18/boot-5.4.210-kexec-stage-builtin-recovery.avb.img" &&
		$2 == "revoked" &&
		$3 == "twice-live-accepted historical staging image; superseded as active authority by the corrected diagnostic lifecycle; never flash" && NF == 3 { revoked++ ; next }
	{ exit 1 }
	END { if (NR != 46 || observer != 1 || core != 1 || generation25 != 1 || generation26 != 1 || generation27 != 1 || generation28 != 1 || generation29 != 1 || generation30 != 1 || generation31 != 1 || generation32 != 1 || generation33 != 1 || generation34 != 1 || generation35 != 1 || generation36 != 1 || generation37 != 1 || generation38 != 1 || generation39 != 1 || generation40 != 1 || generation41 != 1 || generation42 != 1 || generation43 != 1 || generation44 != 1 || generation45 != 1 || generation46 != 1 || generation47 != 1 || generation48 != 1 || generation49 != 1 || generation50 != 1 || generation51 != 1 || generation52 != 1 || generation53 != 1 || generation54 != 1 || generation55 != 1 || generation56 != 1 || generation57 != 1 || generation58 != 1 || generation59 != 1 || generation60 != 1 || generation61 != 1 || generation62 != 1 || generation63 != 1 || generation64 != 1 || generation65 != 1 || generation66 != 1 || revoked != 1) exit 1 }
	' "$boot_policy" ||
	{ echo 'FAIL committed temporary-boot policy is not the exact observer/core admissions plus consumed history' >&2; exit 1; }
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
[[ $(awk -F '\t' '$2 == "allow" { count++ } END { print count + 0 }' \
	"$boot_policy") == 3 ]] ||
	{ echo 'FAIL temporary-boot policy does not contain exactly observer, core, and Generation 66' >&2; exit 1; }
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
	index($1, "generation12") || index($1, "generation-12") ||
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
	grep -n 'verify-stable-recovery-initramfs.sh' "$gate" | cut -d: -f1
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
