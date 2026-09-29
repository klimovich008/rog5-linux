# GPT-6-Astra: DP -> HDMI follow-up (2026-09-29)

Brief: [2026-09-29-dp-hdmi-followup-brief.md](2026-09-29-dp-hdmi-followup-brief.md). Codex CLI 0.158.0, gpt-6-astra, reasoning high, read-only sandbox. Links point at local paths on the development host.

**I would test applied clock/bandwidth and NoC QoS first. I also found a definite bug that invalidates some proposed HBR2 swing-floor tests: patch 0097 can leave the PHY at 0/0 despite a configured floor.**

Everything below is read-only analysis of the supplied notes, patches, r91 source and archived stock source. I modified no files and performed no phone I/O.

**Corrections to the current reasoning**

- **“Latched underrun” remains an observation, not an established hardware mechanism.** Underruns on every frame could mean persistent starvation or a stuck pipeline. Recovery after a modeset fits both.
- **Debugfs performance writes do not immediately change hardware.** The `perf_mode` setter only changes a variable; clock and bus updates remain conditional on calculated `new_perf` versus `cur_perf`. Changing fixed votes during an unchanged stream therefore does not prove that the requested resources were applied. See [dpu_core_perf.c:403](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/disp/dpu1/dpu_core_perf.c:403).
- **0101’s ordering explanation is incorrect for this source.** `msm_atomic_commit_tail()` commits planes before modeset enables. `atomic_flush()` already calls the performance update, and video timing starts in `handle_post_kickoff()`, after CTL flush—not in the encoder’s enable callback. Thus “votes precede encoder enable” does not identify the original failure. See [msm_atomic.c:247](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/msm_atomic.c:247), [dpu_crtc.c:999](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/disp/dpu1/dpu_crtc.c:999), and [dpu_encoder_phys_vid.c:650](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/disp/dpu1/dpu_encoder_phys_vid.c:650).
- **Stock’s 2.5 GB/s figure is a MNOC floor, not a uniform DDR floor.** Stock separately initializes MNOC/LLCC/EBI peak votes to 2.5/0/0.8 GB/s. Its power-enable path applies those before enabling regulators. Mainline’s end-to-end paths and late performance votes are not directly equivalent. See [sde_power_handle.c:459](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/display/msm/sde_power_handle.c:459) and [power enable:754](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/display/msm/sde_power_handle.c:754).
- XR24 and XR30 both occupy four bytes per pixel in these linear buffers. Changing output bpc does not isolate memory-fetch bandwidth. The pattern tests already substantially weaken a format-decoding explanation.

**Ranked DPU hypotheses**

| Rank | Hypothesis | Evidence and limitations |
|---|---|---|
| 1 | Insufficient memory-service latency guarantees: NoC urgency forwarding and SSPP QoS | Large bandwidth votes curing failure is consistent with overcoming poor arbitration or latency. Stock explicitly programs urgency forwarding; mainline previously did not. However, absence of driver programming does not establish the actual reset/firmware register state. |
| 2 | Performance application or transition problem | Normal and fixed mode reportedly differ despite matching later readbacks. Debugfs updates are deferred; runtime suspend clears ICC votes; the bus-update function ignores `icc_set_bw()` errors. First-frame history matters more than a steady-state snapshot. |
| 3 | Core-clock sensitivity or a clock/bandwidth interaction | High combined pinning works, but that intervention changes two variables. Patch 0099 is a reasonable empirical mitigation; full pixel clock is not, by itself, a demonstrated universal minimum for this widebus pipeline. |
| 4 | Persistent CTL/INTF/SSPP state after the initial failure | Modeset recovery and restart dependence support investigating this. It becomes a leading explanation only if **verified** resource restoration during the failed stream cannot recover it. |
| 5 | Programmable fetch, CDP, OT limits, or rotator-specific timing | These deserve register checks, but the inspected source supplies less evidence for them than for the preceding candidates. |

The useful stock/mainline differences are specific:

| Setting | r91 mainline | Stock Lahaina, 60 Hz |
|---|---|---|
| Linear CREQ LUT | `0011222222335777` | `0011223344556677` |
| Linear danger LUT | `0003ffff` | `0000ffff` |
| Linear safe LUT | `fe00` | `fff0` |
| VBIF RT remap | `3 3 4 4 5 5 6 6` | Same |
| CDP RT read enable | Enabled | Enabled |

Mainline’s danger/safe values match stock’s **120 Hz** row, while its linear CREQ LUT comes from SC7180. That is a concrete catalog mismatch, although its effect needs testing. Sources: [mainline catalog:334](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/disp/dpu1/catalog/dpu_7_0_sm8350.h:334), [shared LUTs:698](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/disp/dpu1/dpu_hw_catalog.c:698), and [stock DT:195](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/arch/arm64/boot/dts/vendor/qcom/display/lahaina-sde-common.dtsi:195).

Consequently:

- **0106 is the best isolated stock-equivalence experiment.** Its offsets and priority/urgency values agree with stock. Verify the resulting registers; do not infer success from inclusion in the build.
- **CREQ and danger/safe come next**, changed separately.
- **VBIF remap is a restoration/readback question**, since the intended values already match.
- **OT tuning is lower priority:** this mainline VBIF catalog supplies no default OT limits, and the inspected stock Lahaina DT does not supply them either.
- **Do not transplant stock’s “always enable programmable fetch” behavior into DP on this evidence.** Its caller explicitly gates that configuration to DSI. Mainline also distinguishes the bandwidth model’s `min_prefill_lines=40` from INTF’s `prog_fetch_lines_worst_case=24`; changing one does not change the other. See [stock video setup:470](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/display/msm/sde/sde_encoder_phys_vid.c:470).

Regarding recovery: mainline’s underrun callback counts and captures a snapshot; it does not initiate recovery. But ordinary video disable already waits for timing disable and calls cleanup, which resets CTL and clears merge-3D configuration. A blanket assertion that “mainline forgot the reset” is unsupported. Stock’s inspected reset-error path does request recovery after a **CTL reset timeout**, which is a narrower condition than receiving an underrun IRQ. See [underrun callback:1491](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/disp/dpu1/dpu_encoder.c:1491), [cleanup:2257](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/disp/dpu1/dpu_encoder.c:2257), and [stock timeout handling:957](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/display/msm/sde/sde_encoder_phys_vid.c:957).

**Smallest decisive DPU experiments**

These are proposed experiments, not actions performed.

Use the same failing GNOME configuration, HBR, exact 1080p60 timing, DSI off, fixed plane assignment and cursor policy. Begin each trial with a verified complete disable. Keep the simple KMS pattern as a control; it cannot substitute for reproducing GNOME’s failure.

Capture actual core rate, both ICC consumer requests and return codes, first CTL flush/timing enable, and underrun/vsync deltas. A useful initial pass criterion is correct moving content and zero underruns over at least 300 frames, repeated across three independent enables.

1. **Separate clock from bandwidth using a fixed-mode 2×2 matrix.**

   Use the observed normal achieved clock—likely the 200 MHz OPP after 0099—and 460 MHz. Use 4,000,000 and 15,500,000 for both fixed AB/IB settings.

   | Trial | Clock | AB/IB settings |
   |---|---:|---:|
   | A | Normal achieved rate | 4,000,000 |
   | B | 460 MHz | 4,000,000 |
   | C | Normal achieved rate | 15,500,000 |
   | D | 460 MHz | 15,500,000 |

   Set values while fully disabled, then enable and verify application.

   - B alone curing A implicates clock.
   - C alone curing A implicates memory/interconnect resources.
   - Only D passing indicates an interaction or insufficient intermediate settings.
   - A passing while normal mode fails with the same applied values implicates transition/update behavior.

   These settings are not identical per-path AB and IB: the driver divides AB across its two paths and leaves IB undivided. ICC units are kB/s. [Driver implementation:304](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/disp/dpu1/dpu_core_perf.c:304), [kernel ICC documentation](https://docs.kernel.org/driver-api/interconnect.html).

2. **A/B 0106 with identical clock and bandwidth.**

   Compare otherwise identical variants, with one failing resource setting established above. Read `QOSGEN_MAINCTL_LO` at port offset **+8** for all four ports, before first enable and after any relevant PM transition.

   - Repeated success only with verified urgency forwarding supports QoS causality.
   - Identical registers in both variants mean this is not a valid QoS intervention.
   - Changed registers with unchanged failures weakens urgency forwarding as a sufficient fix.

   Two subtleties: mainline also clears priority-forward-disable bit 24, whereas the inspected stock writer touches only priority and urgency; stock defers programming until a nonzero vote, while 0106 uses probe-time setup. Neither proves a defect, but both belong in the readback comparison. [Mainline writer:31](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/interconnect/qcom/icc-rpmh.c:31), [stock writer:66](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/drivers/interconnect/qcom/qnoc-qos.c:66).

3. **Test stock LUTs only if QoS alone is insufficient.**

   Hold NoC and resource settings constant. First change only linear CREQ to `0011223344556677`; then separately test the 60 Hz linear danger/safe pair `ffff/fff0`. Verify the actual active SSPP registers and danger-enable bit.

   Success confined to one intervention identifies the useful policy change. No improvement with confirmed programming moves attention toward transition/pipeline state.

4. **Distinguish persistent starvation from a recovery defect.**

   After reproducing failure, force a serialized hardware update to the known-good clock and votes **without resetting the display**. Existing debugfs setters alone are insufficient for this experiment.

   - Recovery without disable means the apparent latch was resource-dependent.
   - Continued failure, followed by recovery through a full disable/re-enable at unchanged resources, supports persistent pipeline state.
   - Capture CTL reset/flush status, INTF status/line progression, SSPP QoS and VBIF halt state before reset. Test a narrower reset only after that evidence identifies the boundary.

I would defer prefill/CDP/OT sweeps until these four steps discriminate the leading causes.

**HBR2: what to compare and test first**

The leading explanation is **marginal high-speed signal integrity or inadequate applied TX drive**, potentially specific to a lane/contact/orientation. Another host working with the hub reduces suspicion of a universally broken hub; it does not establish adequate margin on this phone-to-hub channel.

My ranking is:

1. Lane-specific electrical margin, including the phone connector and hub cable.
2. Training settling at an insufficient drive level, compounded by the broken floor experiment.
3. Orientation-dependent PHY lane-group configuration.
4. Rate-dependent PLL/SSC behavior.
5. Logical lane permutation or AUX/SBU routing.

AUX/SBU does not carry the main-link pixel symbols. Reliable AUX plus clean HBR video makes it a poor direct explanation for HBR2 errors on one main-link lane.

The earlier comparison mostly holds: selected HBR2 PLL values and TX values at 0/0 and 1/0 agree with stock. They are **not entirely identical tables**: mainline’s selected pre-emphasis table has `0x1b` at swing 0/emphasis 3, versus stock `0x1a`. That difference cannot explain a failure observed at 0/0. See [mainline tables:2077](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/phy/qualcomm/phy-qcom-qmp-combo.c:2077) and [stock tables:77](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/display/msm/dp/dp_catalog.c:77).

The cheap sequence is:

| Step | Change | Observe and decision |
|---|---|---|
| 1 | For an experimental DT, restore HBR2 capability and lift the runtime cap; keep 1080p60 RGB8 | Confirm the **final trained rate** is HBR2. The current DT prevents raising it merely through `dp_max_rate`. |
| 2 | Use the working DP TPG, widebus off, and compare HBR/HBR2 in both plug orientations | Valid symbol errors at HBR2 despite TPG isolate the fault from DPU fetch. Orientation dependence implicates the physical channel or selected PHY group. |
| 3 | Repair floor application; compare actual 0/0, 1/0, 2/0, then suitable pre-emphasis combinations | Read TX drive/emphasis registers after the final training pass. Repeatable error elimination supports drive/margin. More drive is not automatically better. |
| 4 | Substitute a known-good adapter/cable on this phone at the same mode/rate | One adapter failing isolates interoperability/channel margin; multiple failing adapters strengthen phone/PHY suspicion. |
| 5 | Test coherent SSC-off, with actual PLL SSC readback | Improvement supports SSC interaction. No register change means no physical SSC experiment occurred. |

Use timestamped, short error-count intervals, verify validity and counter saturation behavior, and do not derive precise error rates from the snoop’s nominal labels. AUX transaction time makes those labels approximate.

For this PCON, `SINK_STATUS=00` and unsupported CRC are already contradicted by working HBR video. Neither should remain a success gate.

**Concrete patch defects and review findings**

1. **0097’s swing/pre-emphasis floors can be bypassed completely.** Training resets levels to zero and checks for success before calling `msm_dp_link_adjust_levels()`. Both stages can succeed without ever applying the floor. Apply the validated/clamped floor during initial reset as well as subsequent adjustment, preserving valid swing/emphasis combinations. This is the highest-priority diagnostic fix. [Training:1481](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/dp/dp_ctrl.c:1481), [floor and reset:1149](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/dp/dp_link.c:1149).

2. **0096’s runtime rate cap is incomplete.** Mode validation and bpp selection still use `panel->link_info.rate`; lane-count fallback resets the rate from that same uncapped value. The DT cap currently masks these defects. Use one effective supported-rate limit consistently for validation, selection and fallback, and reject unsupported arbitrary rates. [Fallback:1555](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/dp/dp_ctrl.c:1555).

3. **The polarity fix remains disabled by default.** Moreover, turning the knob off after enabling it leaves previously copied polarity fields intact. Correct polarity should be copied unconditionally; any diagnostic override should explicitly assign both fields. [dp_display.c:660](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/dp/dp_display.c:660).

4. **0094 accepts unsupported intermediate depths.** `dp_max_bpc=7` or `9` can generate 21 or 27 bpp for bandwidth/TU calculations, while the MISC depth helper falls back to 8 bpc. Restrict values or round down to supported depths. Its PCON writer also checks only “DP 1.3+ branch,” which is too broad; confirm an applicable HDMI/DVI downstream converter before writing those controls. [bpp selection:219](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/dp/dp_panel.c:219), [depth encoding:1197](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/dp/dp_link.c:1197).

5. **0096’s CRC/work lifecycle needs completion.** Cancellation before the final sample skips the CRC-stop write. The remove path has no explicit final snoop cancellation before submodule teardown. Add teardown ownership and stop CRC when AUX remains usable; this is not evidence that snooping caused the reported userspace crash. [worker:618](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/dp/dp_display.c:618), [remove:1286](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/msm/dp/dp_display.c:1286).

6. **0101 is not a demonstrated sequencing fix.** Besides its incorrect explanation, it ignores the update result. The underlying bus-update function already discards ICC errors and returns success. Fixing that observability is more useful than adding further unverified early-vote calls.

I found no definite offset/value bug in 0106. Treat 0099/0100 as mitigations until the independent resource tests establish what is necessary.

**Hub noise and unplug crashes**

The noise is plausibly a hub power-conversion component responding to a phone-dependent load. Both inductors and ceramic capacitors can produce audible noise under switching-regulator operating conditions. [TI explanation](https://www.ti.com/document-viewer/lit/html/SSZT873/GUID-F869923A-36E8-46F8-AA4D-DD41F8856E62).

Compare one variable at a time: supported lower refresh, link rate at unchanged display timing, hub external power if supported, and the other host at identical settings. Record sound alongside link errors and HPD events. A noise change alone does not identify the DP fault. SSC is lower priority, especially because this PHY does not consume the requested SSC option.

Kernel hotplug behavior can expose compositor lifetime races, but a userspace segfault still requires a userspace bug unless there is separate evidence of kernel corruption. Long HPD-low events should produce disconnect/reconnect behavior. The inspected bridge path sets connector status, notifies bridges and emits the hotplug event; it does not destroy the DRM connector object on unplug. [drm_bridge_connector.c:158](/home/deck/.local/state/rog5-kernel-7.2.7-build-r91-splash/source/drivers/gpu/drm/display/drm_bridge_connector.c:158).

For a focused unplug test, compare HDMI-only removal with whole-hub removal, without concurrent `wlr-randr` requests. Correlate raw GLINK notifications, connector status/events and the crash backtrace; repeat with snooping disabled. Look for contradictory state, repeated transitions or teardown delays. A clean single disconnect followed by the same GObject crash strongly favors the Phosh lifetime bug already under investigation.