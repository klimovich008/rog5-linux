# HDMI converter recovery and HBR2 trials

Patches 0200–0207 are host-validated experiments for the SM8350 DP controller.
No HDMI picture or recovery is qualified by compilation. The converter cap
stays **270000 kHz (HBR)** by default. Native DP keeps its existing rate policy.

The [hub results](../../test-results/2026-09-29-dp-hub-bringup.md),
[HBR2 failures](../../test-results/2026-09-29-hbr2-and-server-checks.md),
[Deck capture](../reviews/2026-09-30-steamdeck-dp-capture.md), and
[MSI EDID](../reviews/2026-09-30-msi-mpg491c-edid.txt) show HBR video on the
phone, successful HBR2 training with dark HDMI output, and working HBR2 on
the Deck. Replug plus reboot restored the phone's output but did not isolate
which side held stale state. Training success is not a picture-success test.

## Implemented behavior

Required AUX transfers now reject short results, retain negative errno, and
check link configuration, training-pattern changes, downspread/coding,
D0/D3 and converter restoration. Retry exhaustion and insufficient final
link capacity fail; retraining, OPP/clock and video-ready failures stop enable.
The failure path stops clocked blocks, sends training-disable and D3 while
AUX is usable, releases only acquired pixel/link clocks and PHY power, then
exits the host PHY initialization. It preserves the atomic-enable runtime-PM
reference until post-disable. Link-maintenance failures use the same cleanup.

A deferred worker marks the connector's `link-status` BAD and sends a hotplug
uevent after releasing both connector and plug locks. Userspace must issue a
new modeset with link-status GOOD; this is a retry request, not a fabricated
physical disconnect. The next enable wakes the sink and rereads capabilities
and EDID. Ordinary physical HPD handling remains active. A successful enable
whose monitor is dark needs operator-directed recovery: the controller
cannot infer a visible picture from this converter's status bytes.

Rate-limited `DP: training`, `pre-video-training`, `on-link`, `on-stream`, and
`enable-failed` records show errno, actual boot-time timestamp, final lanes,
rate and depth; lane status at 0x202, sink power at 0x600, converter controls
at 0x3050–0x3052 and HDMI TX status at 0x303b. Parenthesized counts are actual
AUX results; only an exact byte count makes a field valid. Zero/NACK at
0x303b is inconclusive for this hub, including on the working Deck.
Clocked snapshots also show MAINLINK_READY, configuration, MISC, M/N, TU and
actual pixel/link clock rates. Snooping is serialized with enable/HPD and
reports actual timestamps as well as its requested delay.

Default snapshots do not consume symbol-error counters. `dp_snoop_errors=1`
opts into read-to-clear 0x210–0x213 sampling. Interpret the validity bit and
elapsed time; zero without validity is not a clean link. FRL-only error/status
reads require advertised FRL capability. `dp_crc` stays off; its opt-in capture
checks CRC support and stops on completion, cancellation or teardown.

## Runtime settings

All parameters are under `/sys/module/msm/parameters/`. Set them with the
external output **off**, then enable it. The new sequencing/MISC experiments
apply only to HDMI/DVI converter branches. Do not unload active `msm`.

| Parameter | Default | Effect / trial |
|---|---:|---|
| `dp_pcon_max_rate` | 270000 | Converter capability cap; set 0 before discovery to allow HBR2. |
| `dp_max_rate` | 0 | Additional source cap; 270000 selects HBR for recovery. |
| `dp_link_policy` | 1 | Set 0 for HBR2 comparison; policy 1 may choose HBR at 1080p60. |
| `dp_max_lanes` | 0 | Use 2 for this hub; never force four lanes under assignment D. |
| `dp_max_bpc` | 0 | Set 8 for RGB8 comparisons. |
| `dp_sink_power_cycle` | 0 | Existing checked D3, ≥200 µs, D0 cycle before fresh enable; D3 on attached shutdown. |
| `dp_pcon_reprobe` | 0 | Reread receiver/downstream/EDID capabilities on the next modeset, after teardown/wake. Use after changing the converter cap or recovering dark video. |
| `dp_pcon_single_train` | 0 | Immediate receiver TP termination at initial success; skip forced duplicate training, retain retraining on bad EQ. Latched at link setup. |
| `dp_pcon_ahb_reset` | 0 | AHB SW_RESET before training with clocks live and AUX transfers excluded; restore AUX/HPD configuration and IRQ masks; defer if HPD is already pending. |
| `dp_async_msa` | 0 | Existing asynchronous signaling experiment; M/N remain static, so success is a compatibility lead, not complete asynchronous qualification. |
| `dp_pcon_clean_misc` | 0 | Rebuild owned MISC depth/colorimetry/clock/VSC fields; remove stale legacy-RGB VSC selection. |
| `dp_polarity` | 0 | Existing mode-polarity copy; returning to 0 clears a prior trial's polarity. |
| `dp_safe_exit` | 0 | Existing stock lane-dependent FIFO threshold experiment. |
| `dp_snoop_errors` | 0 | Explicitly consume symbol-error counters during the five bounded snapshots. |

No source-controlled FRL, SCDC, undocumented 0x3047 write, PHY-table
replacement, audio integration or 420 format-selection change is included.
The [DRM PCON definitions](https://raw.githubusercontent.com/torvalds/linux/master/include/drm/display/drm_dp.h)
and [helpers](https://docs.kernel.org/gpu/drm-kms-helpers.html) describe controls
conditioned on advertised capabilities; this captured converter advertises no
FRL/source-control support. The existing 0x3050/51/52 RGB HDMI settings are
retained and their transfer/readback failures now propagate.

## Exact RAM-trial sequence

The coordinator first packages k121 with a reviewed DP-capable production DTB,
whose side-port endpoint advertises 1.62/2.7/5.4 GHz, into a **fresh** signed
RAM-only candidate using the [production trial flow](../development.md).
Verify build/module identity, DT composition, fallback and an independent
control connection before asking the operator to be ready. The kernel builder
alone does not create this signed candidate. Keep the monitor/hub connected
to the phone's **side USB-C port**, with the same HDMI cable and orientation.
Keep HDR and audio off. Never read `dri/*/DP-*` debugfs files or the phone PIN.

The following are commands for a later authorized session **on the phone**;
they are not host commands and were not executed while implementing the patches.
Root sets parameters; the logged-in `phone` user's Phosh Wayland session runs
`wlr-randr`. Run `wlr-randr` first to verify the external output name and exact
advertised 1920x1080@60 timing. Substitute that output name for `DP-1` below.
Use the same compositor throughout. GNOME needs its own reviewed modeset
control; do not run `wlr-randr` against GNOME.

1. With the hub unplugged, root initializes the fixed RGB8 comparison:

   ```sh
   p=/sys/module/msm/parameters
   for knob in dp_pcon_single_train dp_pcon_ahb_reset dp_async_msa \
       dp_pcon_clean_misc dp_polarity dp_sink_power_cycle dp_pcon_reprobe \
       dp_safe_exit dp_tpg dp_crc; do echo 0 > "$p/$knob"; done
   echo 0 > "$p/dp_link_policy"
   echo 2 > "$p/dp_max_lanes"
   echo 8 > "$p/dp_max_bpc"
   echo 270000 > "$p/dp_pcon_max_rate"
   echo 0 > "$p/dp_max_rate"
   ```

   **User:** select the monitor's HDMI input and plug the HDMI hub into the
   side port. The session operator selects 1080p60:
   `wlr-randr --output DP-1 --mode 1920x1080@60Hz --on`.
   Look for visible moving content for 15 seconds and an HBR×2, bpp=24 log.
   If this baseline fails, stop the HBR2 experiments.

2. For every arm, switch the output off:
   `wlr-randr --output DP-1 --off`. Set all experiment knobs back to 0.
   Root sets `dp_pcon_max_rate=0`, `dp_max_rate=0`, `dp_pcon_reprobe=1`,
   and retains policy 0, lanes 2, bpc 8. The reprobe refreshes the cap without
   requiring another physical unplug. Enable the same 1080p60 mode and
   capture bounded dmesg from the enable through the 15-second snapshot.
   Require the log to show **2 × 540000 kHz**, bpp 24, rc=0 and valid final
   lane status. A fallback to HBR invalidates an HBR2 picture comparison.
   **User:** report whether the monitor shows moving content, stays dark,
   flickers or loses input. An rc=0 log alone is not a pass.

3. First reproduce default HBR2 once, then recover without touching cables:
   output off; root sets `dp_max_rate=270000`, `dp_sink_power_cycle=1`,
   `dp_pcon_reprobe=1`; output on at 1080p60. Look for checked D3→D0,
   HBR×2 RGB8 and visible moving content. Repeat off/on once. This is the
   recovery acceptance test: **no replug and no reboot**. If still dark,
   stop and preserve evidence; D3 is not claimed to reset every hub firmware.
   Physical replug is then a separately recorded rescue action, not a pass.

4. Starting from a visible recovered baseline, run HBR2 with exactly one
   candidate enabled, in this order: `dp_sink_power_cycle=1`, then
   `dp_pcon_single_train=1`, then `dp_pcon_ahb_reset=1`, then
   `dp_async_msa=1`, then `dp_pcon_clean_misc=1`, then `dp_polarity=1`.
   Keep `dp_pcon_reprobe=1` as the common capability-refresh control and all
   other candidates 0. Between arms perform step 3, then turn its power-cycle
   setting back off. Single-training must log `on-link/single-training`;
   `pre-video-training` should appear only if EQ is bad. Reset must log its
   reset marker. Async must show the changed configuration/MISC clock bits.
   **User:** look at the screen for each arm and move a window/pointer.
   Stop after two non-discriminating failures at the same boundary; preserve
   timestamps, validity/counts, HPD and error records before deciding the next
   experiment. Test FIFO/drive/orientation separately only with that evidence.

5. After an arm gives repeatable HBR2 **picture and recovery**, try MSI
   2560x1440@60 RGB8, then 3840x1080@60 RGB8, retaining only that arm.
   Check moving content, 15-second stability, no DPU underruns/timeouts and
   repeated off/on. Four-lane RGB4K60 cannot fit this hub; do not attempt it.
   This MSI EDID does not advertise 3840x2160. A separate suitable sink and
   consistent end-to-end 420 selection are required for later 4K work.

On completion, output off; restore the saved parameter values, especially
`dp_pcon_max_rate=270000`, and set `dp_pcon_reprobe=1` for one HBR enable to
refresh cached capabilities, then restore reprobe to 0. Keep k121 a RAM trial
until picture and recovery are independently qualified. Do not install or
change the default/fallback based on offline results.

## Host verification

`python3 scripts/host/test-dp-pcon-patches.py` executes the added cleanup,
minimal wake and serialized reset helpers with mocked resources/AUX. It
includes a 128-case partial-resource/error matrix with repeated teardown and mutation checks for
unclocked writes and double pixel-clock release. With `ROG5_LINUX_SOURCE`
pointing at the applied source, it also executes the actual training retry,
stream-enable and D0/D3 functions, injecting short transfers, errno,
retraining/TP-disable/video-readiness failures and single-training/EQ cases.
These checks substitute hardware and locking APIs; real concurrency,
electrical behavior and hub firmware recovery still require the RAM trial.
