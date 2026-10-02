Review request (read-only): hardware video decode/encode for the ASUS ROG Phone 5 (SM8350) on Linux 7.2.7.

Repository: this worktree (branch agent/video-iris-261001). Kernel source with the series 0001-0153 applied:
/home/deck/.local/state/rog5-kernel-7.2.7-build-r113/source (read only; the iris driver is drivers/media/platform/qcom/iris).

Files to review:
1. patches/linux-7.2.7/0154-media-iris-power-the-core-off-when-the-firmware-does-not-come-up.patch
   (new kernel patch; read its commit message). Check correctness: locking (core->lock, the wait happens
   outside the lock), runtime PM reference counting in iris_open -> iris_core_init -> iris_wait_for_system_response
   -> iris_core_deinit, interaction with iris_sys_error_handler (deinit+init from a workqueue) and with
   iris_pm_suspend/resume (they only act in IRIS_CORE_INIT), double power-off/unload risks, IRQ enable/disable
   balance (iris_vpu_power_on enables the IRQ, iris_vpu_power_off disables it unless the watchdog bit is set),
   the reinit_completion placement, and whether returning -EINVAL from the UC-region poll is right.
2. dts/qcom/sm8350-asus-rog-phone5-video.dtso (overlay adding the iris node and the videocc node) and
   scripts/device/compose-video-dtb.sh (applies it on the pinned d13 DTB with before/after checks).
   Compare against upstream mainline v7.3 sm8350.dtsi (copy: /tmp/claude-1000/-home-deck-Projects-rog-phone-linux-migration/2cc1c994-1a4f-4a0b-aca7-41804577680f/scratchpad/mainline-sm8350.dtsi, lines 2750-2835),
   the stock ASUS runtime FDT (/home/deck/.local/state/rog5-production-boot-20260923/trial-stockcap-c1-session/stock-fdt.dts:
   nodes qcom,vidc@aa00000 at line 23345 and qcom,venus@aab0000 at line 12748) and the downstream sources
   /home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/arch/arm64/boot/dts/vendor/qcom/lahaina-vidc.dtsi,
   .../drivers/clk/qcom/videocc-lahaina.c (frequency/rail tables). Composed result (for fdtdump/dtc): /tmp/claude-1000/-home-deck-Projects-rog-phone-linux-migration/2cc1c994-1a4f-4a0b-aca7-41804577680f/scratchpad/d14-test.dtb.
3. configs/kernel/rog5-video.fragment and the policy change in configs/kernel/rog5-production-build-7.2.7.json.

Context: the board DTB is not built from the kernel tree; it is composed from an installed binary DTB with overlays.
The apps SMMU on this phone sits under the Qualcomm hypervisor: patch 0064 (patches/linux-7.2.7/0064-*.patch) reserves
context banks 8-10 that the hypervisor routes for the secure video streams 0x2101/0x2103/0x2104; patches 0049/0051 put
DSP streams on banks >= 20 because the hypervisor silently ignores S2CR writes for those SIDs on low banks.
Firmware: the phone's vendor_a vpu20_4v.mbn (ASUS OEM-signed, same root certificate as the ADSP image that TrustZone
accepts; vpu20_1v/2v are generic QTI-signed). PAS id 9 into the 5 MiB no-map carve-out at 0x85700000; the ELF load span
is 0x4ff020 bytes. The iris driver matches qcom,sm8250-venus (iris_platform_vpu2.c sm8250_data); venus does not match it
when CONFIG_VIDEO_QCOM_IRIS is enabled.

Questions: (a) real bugs in 0154; (b) anything in the DT that is wrong for SM8350 or for this board (power domains,
OPP levels, interconnect tags, reset, iommus, memory-region, firmware path); (c) risks on this phone at first firmware
boot (hypervisor S2CR handling of SID 0x2100 on a low context bank, the content-protection SCM call
qcom_scm_mem_protect_video_var with cp_start 0 / cp_size 0x25800000, IOVA allocation below 0x25800000, MMCX/MX votes,
ICC INT_MAX vote at power-on) and what to look for in dmesg; (d) whether a SM8350-specific change to the driver is needed
beyond the SM8250 fallback. Be concrete; cite file:line. Do not modify anything.


## Round 2 brief

Follow-up review (read-only) of the ROG5 SM8350 video work in this worktree, after your first review
(your previous findings are in /tmp/claude-1000/-home-deck-Projects-rog-phone-linux-migration/2cc1c994-1a4f-4a0b-aca7-41804577680f/scratchpad/video-review-sol-r1.md).
Kernel source with 0001-0153 applied: /home/deck/.local/state/rog5-kernel-7.2.7-build-r113/source.

Changed since:
1. patches/linux-7.2.7/0154-media-iris-power-the-core-off-when-the-firmware-does-not-come-up.patch was reworked:
   attempt numbering (core->init_attempt), iris_core_abandon_init() that takes a PM reference, disable_irq() outside
   core->lock, tears down only the current attempt, enable_irq() after; shared iris_core_teardown() that logs a failed PAS
   shutdown; gen1/gen2 init-done handlers complete on failure too. Check the IRQ depth arithmetic in all cases (IRQ enabled
   after power-on; already disabled because the hard ISR ran and the thread is pending/running; watchdog interrupt case;
   core already torn down by someone else), the PM reference handling from both callers (iris_open holds a reference;
   iris_sys_error_handler does not), and any new deadlock (e.g. pm_runtime_resume_and_get() invoking iris_pm_resume, which
   takes core->lock, while ... ), plus whether completing core_init_done on an error response could confuse anything.
2. New patch 0155 (backport of the proposed upstream binding change allowing a second memory-region) and the DT overlay
   dts/qcom/sm8350-asus-rog-phone5-video.dtso now adds /reserved-memory/iris-iova (iommu-addresses <&iris 0 0 0 0x25800000>,
   no reg) as the second memory-region, as in Vikash Garodia's proposed "arm64: dts: qcom: sm8350: Reserve low IOVA range
   for Iris" (2026-08-07). scripts/device/compose-video-dtb.sh checks it. Composed result:
   /tmp/claude-1000/-home-deck-Projects-rog-phone-linux-migration/2cc1c994-1a4f-4a0b-aca7-41804577680f/scratchpad/d14-test.dtb.
   Check that 7.2.7 really applies it (of_iommu_get_resv_regions via iommu_dma_get_resv_regions for arm-smmu; of_translate_dma_region
   with soc@0 dma-ranges <0 0 0 0 0x10 0>), that early reserved-memory scanning ignores a node without reg/size, and nothing
   else in this kernel (of_reserved_mem, kexec of the DTB, the iris driver's index-0 lookup) trips on it.
3. New patch 0156-iommu-arm-smmu-qcom-ROG5-SM8350-report-stream-routes-the-hypervisor-did-not-take.patch: reads back
   each translating S2CR on SM8350 and warns on a mismatch. Check correctness (when write_s2cr is called, locking/RPM state,
   smrs indexing when stream matching uses SMRs, the bypass quirk path, any risk the readback itself causes) and whether
   it could spam the log at boot.
4. Not changed on purpose: the overlay is not added to the kernel build policy's dt_sources (an overlay compiled outside its
   base gives reg_format/avoid_default_addr_size warnings, and the build fails on any unreviewed warning; the other board
   feature overlays are not in dt_sources either).
5. New platform-kit plumbing: configs/production/video-modules.list, configs/systemd/rog5-video.service, the changes in
   initramfs/persistent-root-init (prepare_platform_services), initramfs/production-platform-modules and
   scripts/device/build-persistent-root-standalone-initramfs.sh (all-or-nothing video list), and
   scripts/device/install-rog5-video-firmware (device-side installer). Look for real bugs only.
Answer with concrete findings (file:line), most important first; say explicitly if you find nothing blocking. Do not modify anything.


## Round 3 brief

Third, short review (read-only) of two reworked kernel patches in this worktree, after your round-2 findings
(/tmp/claude-1000/-home-deck-Projects-rog-phone-linux-migration/2cc1c994-1a4f-4a0b-aca7-41804577680f/scratchpad/video-review-sol-r2.md).
Kernel source with 0001-0153 applied: /home/deck/.local/state/rog5-kernel-7.2.7-build-r113/source.
1. patches/linux-7.2.7/0154-media-iris-power-the-core-off-when-the-firmware-does-not-come-up.patch: __iris_core_deinit()
   now quiesces the IRQ outside core->lock for every teardown (iris_core_deinit and the init-failure path);
   iris_wait_for_system_response() takes the result under the lock for its attempt; an open that finds IRIS_CORE_ERROR
   now returns -EINVAL via the exit label without changing the state. Check for regressions: can any path now leave the
   core in IRIS_CORE_ERROR forever with nobody to tear it down (list every place that sets IRIS_CORE_ERROR and who cleans
   up); IRQ depth at iris_remove() (probe requests the IRQ with IRQF_NO_AUTOEN); the sys error handler calling
   iris_core_deinit() then iris_core_init(); and anything else that is a real bug.
2. patches/linux-7.2.7/0156-iommu-arm-smmu-qcom-ROG5-SM8350-report-stream-routes-the-hypervisor-did-not-take.patch: now only
   reads back entries with s2cr->type == S2CR_TYPE_TRANS && s2cr->count. Correct and quiet at boot?
Answer briefly with concrete blocking findings (file:line) or say there are none. Do not modify anything.


## Round 4 brief

Final short check (read-only) of patches/linux-7.2.7/0154-media-iris-power-the-core-off-when-the-firmware-does-not-come-up.patch
after your round-3 finding (/tmp/claude-1000/-home-deck-Projects-rog-phone-linux-migration/2cc1c994-1a4f-4a0b-aca7-41804577680f/scratchpad/video-review-sol-r3.md):
the iris_core_init() error unwind after power on now sets IRIS_CORE_ERROR, drops core->lock, disable_irq(), retakes the lock,
skips (enable_irq + exit, state untouched) if init_attempt changed or the state is no longer IRIS_CORE_ERROR, else unloads
(if loaded), powers off, enable_irq(), frees the queues and sets DEINIT. Kernel source with 0001-0153:
/home/deck/.local/state/rog5-kernel-7.2.7-build-r113/source. Any real bug left (IRQ depth, double teardown, a core stuck in
ERROR with no owner, lock misuse)? Answer briefly; say "no blocking findings" if none. Do not modify anything.
