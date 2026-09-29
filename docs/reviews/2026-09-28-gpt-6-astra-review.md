I reviewed HEAD `a02a8d2f`, the relevant patches and scripts, the r71 kernel source, stock references and the supplied evidence. No phone commands or file changes. **The main concerns are storage rollback semantics, watchdog lifecycle gaps, and conclusions that overstate what the suspend experiments ruled out.** This was a focused review, not an audit of all 300 commits.

1. **High — C: online growth is reasonable, but the boot contract needs a staged migration.**

   The correct order is: install and verify compatible default **and fallback** ramdisks while the image is still 16 GiB; then enlarge the backing file, refresh the existing loop device’s capacity, and grow the inner ext4 filesystem. Online ext4 growth is supported. [Kernel documentation](https://cdn.kernel.org/doc/html/latest/admin-guide/ext4.html)

   Specific gaps:

   - The pinned userdata partition is **about 195 GiB**, so accepting 256 GiB as a generic bound cannot mean this phone can safely allocate it. A sparse 256 GiB file could pass a length check and later exhaust its backing filesystem.
   - Preserve ownership, mode, link-count, UUID, backing-path and partition checks when relaxing size. Require file length and loop capacity to agree; validate filesystem geometry too.
   - There is another size declaration: `rog5-root-overlay.manifest` contains `image_bytes=17179869184`, and init verifies its exact size and checksum. Decide explicitly whether this becomes a legacy creation record or gets a versioned migration. Casually updating it will fail boot verification.
   - Merely rebuilding fallback is insufficient: the installed, selected fallback must accept the grown image. Old retained ramdisks will reject it.
   - A reset between file growth and filesystem growth must remain bootable. Do not require the filesystem to fill its backing file exactly.

   The likely failure is loss of both normal boot paths, rather than damage to the bootloader. Never try to recover by truncating a filesystem that has already grown. See [size checks](~/.local/state/rog5-prod-boot-20260923/initramfs/persistent-root-init:1907), [attestation](~/.local/state/rog5-prod-boot-20260923/initramfs/persistent-root-attest:249) and [manifest creation](~/.local/state/rog5-prod-boot-20260923/scripts/device/stage-persistent-root-overlay.sh:32).

2. **High — the updater’s “snapshot” is neither application-consistent nor limited to operating-system state.**

   `make_snapshot()` locks pacman, then copies the live upper tree. Databases, containers, browsers and other services continue writing. `sync` does not make that copy an atomic snapshot.

   Rollback replaces the entire upper tree, so it also rolls back user files and server data written after the copy. The failed upper is retained, which helps manual recovery, but the next update’s pruning can remove it. The seal checks names and entry count, not file contents or application consistency.

   For the server goal, the simplest improvement is to put persistent service data outside the OS rollback tree and use application-aware backups. Quiesce relevant writers if whole-tree copies remain. Enlarging the overlay and capping journald do not solve this. [Copy implementation](~/.local/state/rog5-prod-boot-20260923/initramfs/rog5-update:164), [restore implementation](~/.local/state/rog5-prod-boot-20260923/initramfs/persistent-root-init:1750).

   Separately, updater “idle” means **backlight brightness is zero**. That can reboot an actively serving phone; `reboot_now()` even falls back to forced reboot when `systemctl reboot` fails. Server maintenance policy needs something stronger than screen state. [Relevant code](~/.local/state/rog5-prod-boot-20260923/initramfs/rog5-update:384).

3. **High — E: 0088 proves recovery from an awake hard hang, but leaves important lifecycle holes.**

   The kernel configuration supports the intended indefinite kernel petting: `WATCHDOG_HANDLE_BOOT_ENABLED=y`, `WATCHDOG_OPEN_TIMEOUT=0`. Keeping softdog under PID 1 is sensible given the observed Haven idle behaviour.

   The gaps are:

   - **Suspend coverage:** the driver disables Haven in its ordinary suspend callback. A subsequent hard hang during suspend, or before its resume callback, has no Haven watchdog. This matters especially given the charger-attach hang already observed.
   - **Ignored errors:** suspend returns success even if stopping fails; resume returns success even if restarting fails. These can respectively leave an unexpectedly armed watchdog or silently remove protection.
   - **Probe failure:** hardware starts before `devm_watchdog_register_device()`. If registration fails, probe has no explicit cleanup to stop the now-unserviced watchdog.
   - **Restart inconsistency:** `gunyah_wdt_restart()` still programs `bark == bite == 1`, precisely the relationship the Haven investigation found problematic.
   - **Core coordination:** the driver does not request `WDOG_NO_PING_ON_SUSPEND`. Its hardware stop/start sequence is not coordinated with cancellation of the watchdog core’s timer/work.

   I would fix error handling and cleanup first, then qualify aborted suspend, prolonged suspend/resume, shutdown and kexec. Ordinary CPU load is not the main spurious-reset concern; these transition paths are. Also choose softdog by verified identity rather than assuming `/dev/watchdog1` from registration order. [Driver](~/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/watchdog/gunyah_wdt.c:143), [device selection](~/.local/state/rog5-prod-boot-20260923/initramfs/persistent-root-init:2416).

4. **High — the committed RPMh diagnostic contradicts the documented read-safety rule.**

   The notes say only resources previously written by this kernel are read. The committed tool still lists `ddr.lvl`, `qphy.lvl`, clock buffers and `IP0`, including explicit “NOT managed upstream” comments. `votes_show()` checks command-database presence, then issues the read; it does **not** check prior writes.

   Stopping after the first timeout cannot prevent that first request from wedging a transaction. Patch 0035 protects request-memory lifetime; it does not guarantee the hardware transaction completes.

   This needs a known-safe allowlist or actual write-history gating before further diagnostic use. “Read-only” is misleading here: obtaining the value submits a hardware transaction. [Resource list and reader](~/.local/state/rog5-prod-boot-20260923/tools/rpmh_sleep_blockers/rog5-rpmh-sleep-blockers.c:43).

5. **A: DDR_AUX identifies the dependency holding CX up, not necessarily the original DDR blocker.**

   I cannot identify the remaining root cause from the retained evidence. Three exclusions should be weakened:

   - **ADSP/SLPI:** their stop experiments leave AUDIO/SENSOR votes asserted. Your bottom-port report correctly calls this inconclusive; the review summary should too.
   - **Display/GPU removal:** the headless run introduced a persistent HLOS vote because `sync_state` did not finish. Failure to reach collapse under that new blocker cannot decisively exonerate the removed stack.
   - **Deepest APSS state:** genpd usage accounting occurs after its power-off callback, but the PSCI callback merely records the state to request. The actual PSCI call happens afterwards. These counters support software-path execution, not proof that Haven/firmware physically delivered the requested residency. [PSCI callback](~/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/cpuidle/cpuidle-psci-domain.c:32).

   The most useful next investigation would distinguish **a DDR request that remains asserted** from **firmware declining collapse despite released requests**. Prioritize a known-good stock baseline with the same firmware, then compare handoff state and supported DDR/BCM observations. Stopping wrapper-started subsystems does not erase every inherited firmware vote or configuration.

   Also correlate DDR transitions with actual suspend-residency windows and interrupt deltas. An aggregate “14 transitions/minute” can include entry, exit and observation traffic. Disable diagnostic monitoring for a control measurement. I would avoid another broad register-read or vote-clearing experiment until it answers a specific missing observation.

6. **B: the orientation diagnosis is strong; the dark-screen and hang diagnoses remain partly unproven.**

   Restoring the connector graph, SBU mux and PHY orientation handling is the right direction. Verify the complete module/dependency closure before UCSI, and validate actual GPIO polarity against the board—the current overlay and combined notes describe selection differently.

   0091’s connector assignment fixes a concrete NULL-pointer defect. Its `power_on` guard is also a reasonable correction. But the historical hang has not yet been demonstrated to originate from that exact write; describe it as a source-supported fix pending reproduction, not a confirmed causal result.

   The reconnect helper remains racy: DRM `connected` status can lag Type-C/altmode negotiation, or change between the check and unbind. For the next diagnostic run, disable the helper for the whole run. Longer term, coordinate recovery with Type-C/PHY ownership. [Helper](~/.local/state/rog5-prod-boot-20260923/scripts/device/rog5-usb-reconnect:60).

   **The 10-bit theory is plausible, but “333 MHz exceeds HDMI-1.4-class capability” is not generally valid.** HDMI 1.4b implementations can support 340 MHz; establish this converter’s limit and advertised deep-colour support. [TI confirmation](https://e2e.ti.com/support/interface-group/interface/f/interface-forum/733075/sn75dp126-sn75dp126-can-or-not-support-hdmi-clk-up-to-297mhz)

   A clean 1080p picture alone would not separate bandwidth, colour depth and mixer routing. Use the same stable connection to compare:

   | Mode | Purpose |
   |---|---|
   | 1920×1080, 8 bpc | Basic picture baseline |
   | 1920×1080, 10 bpc | Colour-depth path |
   | 3840×1080, 8 bpc | Wide/multiple-mixer path with less bandwidth |
   | 3840×1080, 10 bpc | Combined case |

   Verify the **applied** mode, bpp and successful training—not just EDID, `wlr-randr` requests or pre-populated link parameters. If adding `max_bpc`, use it consistently in bandwidth validation and stream configuration.

7. **Medium — 0080 changes allocation preference; it does not encode the underlying routing constraint.**

   `!num_dsc` is treated as “allocate from the top” for every applicable DPU, not specifically this DP output. It avoids the observed panel collision but does not reserve a compatible DSC route or prove LM4/5 → MERGE_3D_2 works.

   Keep it labelled as a board mitigation. A durable fix should represent the actual block compatibility constraint in allocation/catalogue logic. At minimum, scope the workaround and test both enable orders, panel blank/unblank, and single-/dual-mixer DP modes. [Patch](~/.local/state/rog5-prod-boot-20260923/patches/linux-7.2.7/0080-drm-msm-dpu-ROG5-keep-the-panel-pipeline-when-DP-enables-first.patch).

8. **D: capacity data plus uclamp is defensible, but the current boost is broader and less deterministic than described.**

   `uclamp.min=400` exceeds A55 capacity, but **both A78 and X1 can satisfy it**. It does not guarantee X1 placement.

   The script boosts the phone user’s systemd manager, so inheritance can extend to background services and future nongraphical work. It misses already-existing descendants not explicitly matched, has no screen-off restoration, and exits successfully even when individual `uclampset` calls fail. Kernel-created GPU worker threads do not inherit a userspace parent’s clamp.

   “Idle is unaffected” is too broad. Fully sleeping tasks do not consume CPU, but periodic background work still receives the floor, influencing placement, shared-policy frequency and energy. [Script](~/.local/state/rog5-prod-boot-20260923/scripts/device/rog5-session-boost:20), [uclamp semantics](https://kernel.org/doc/html/latest/scheduler/sched-util-clamp.html?highlight=util+clamp).

   Prefer declarative clamps on the compositor/session and intended application cgroups. Keep background work outside that group. Compare frame deadlines and energy over representative use; glmark2 improvement alone does not establish the best power/performance policy. Stock coefficients are a useful starting model, not measured validation of this Linux workload.

9. **Medium — the thermal policy is not implementing the fixed caps described in its comments.**

   `<cpu4 THERMAL_NO_LIMIT 6>` permits cooling states **0 through 6**. Under `step_wise`, cooling increases incrementally; it does not immediately cap frequency at state 6 when crossing 42 °C.

   Likewise, `<gpu THERMAL_NO_LIMIT THERMAL_NO_LIMIT>` permits cooling all the way to maximum state. It does **not** mean “GPU unlimited” in the performance sense. The kernel explicitly substitutes zero and `max_state` for these bounds. [Thermal maps](~/.local/state/rog5-prod-boot-20260923/dts/qcom/sm8350-asus-rog-phone5-skin-thermal.dtso:169), [bound interpretation](~/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/thermal/thermal_core.c:769).

   Decide whether the intended policy is gradual cooling or fixed ceilings, then express and test that policy. Raising the stock skin threshold also needs sustained charging-plus-load evidence. The connector `hot` trip currently reports an event; this overlay supplies no connector power-cut policy.

10. **Medium — 0089’s timeout rollback cannot work in its most important failure case.**

    An OEM request timeout marks the shared channel poisoned. The enable error path then tries to send “off,” but the request function immediately rejects poisoned channels. Thus an “on” request that reached firmware but lost its acknowledgement can leave the boost internally enabled.

    GPIO4 remaining low on failed enable provides useful connector isolation, but the claimed source rollback is not assured. Similarly, clearing `btm_otg_on` after a failed disable conflates “no longer wanted” with “confirmed off.” Track desired state separately from confirmed/unknown hardware state. [Request poisoning](~/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/power/supply/qcom_battmgr.c:440), [regulator operations](~/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/power/supply/qcom_battmgr.c:565).

    Stage A is useful bring-up, but without CC/role policy it is not yet a general-purpose phone USB-C port. Eight enumeration cycles do not cover powered hubs, detach during suspend, ADSP restart or sustained storage writes.

11. **Medium — charge-limit enforcement has a suspend limitation.**

    The threshold decision runs on `system_freezable_wq`; firmware receives bypass/input-suspend commands, rather than the complete percentage policy. If the phone sleeps below its limit and then starts charging, this worker cannot enforce the threshold until resume. Removing the charger-wake patch makes that scenario particularly relevant.

    Already-asserted bypass may persist, but “charge limit works” should distinguish that from crossing the threshold while asleep. [Worker](~/.local/state/rog5-kernel-7.2.7-build-r71/source/drivers/power/supply/qcom_battmgr.c:1716).

12. **Medium — the firewall protects host input, not all server exposure.**

    The rules contain only an input chain. Forwarded traffic to containers and routed networks needs a separate policy. Also, `Before=network-pre.target` orders startup but does not make successful firewall loading a requirement for networking.

    Trusting every packet from `usb0`, `tailscale0` and the hotspot may be intentional; it should not be described as restricting service access on those interfaces. [Rules](~/.local/state/rog5-prod-boot-20260923/configs/firewall/rog5-firewall.nft:9), [service](~/.local/state/rog5-prod-boot-20260923/configs/systemd/rog5-firewall.service:1).