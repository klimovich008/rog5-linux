# Boot splash handover: what the panel shows from ABL to the Phosh lock screen

Date: 2026-09-29. Scope: offline analysis of the running default
(`production-7.2.7-r185`: kernel build r86, DTB `platform-cpucap-dp-sbumux-dtb-r2`)
plus read-only phone logs. No reboot, no display access. Branch
`agent/bootsplash` carries 0107/0108 and an unsigned build
`~/.local/state/rog5-kernel-7.2.7-build-r91-splash`; the RAM trial is **NOT RUN**.

## Stage by stage (r185, times from the mainline kernel's dmesg/journal)

| # | When | Who drives the panel | What is on the panel |
|---|---|---|---|
| 1 | ABL | ABL lights the panel (sleep out, display on, DSC, Iris6 in analog bypass), draws its splash into `cont_splash_region` 0xe5000000 (stock runtime FDT) and leaves the MDP autorefreshing it (IOVA == PA) | ABL's last picture |
| 2 | ASUS 5.4 wrapper | Nothing. The wrapper config has no MSM display driver (`CONFIG_DRM=y`, no SDE/`msm_drm`). Its apps SMMU node has `qcom,skip-init`, and `dispcc-lahaina` is built in with a `sync_state`, so 5.4 keeps the MDP clocks and the splash stream alive | ABL's picture, continuous |
| 3 | mainline 0.063 s | The MDSS joins IOMMU group 6 with an empty **DMA** default domain; the MDP's next fetch faults: `Unhandled context fault ... iova=0xe504d700 ... cbfrsynra=0xc20, cb=4` (then 0x820), 0.6 ms after `platform ae00000.display-subsystem: Adding to iommu group 6`. Only 10 lines print (rate limit) | **Glitch 1.** Autorefresh keeps pushing frames built from aborted reads, so the panel RAM gets black/garbage instead of the logo, from a line near the top (fault offset 0x4d700) down |
| 4 | 0.558 s | `clk: Disabling unused clocks` (mainline ignores the dispcc `sync_state`; see the `dsi0_phy_pll_out_dsiclk already disabled` WARN later) gates the MDP/DSI clocks; the GDSC/MMCX stay on (`sync_state() pending due to ae00000.display-subsystem`) | The command-mode panel freezes on the last (faulted) frame for ~25 s |
| 5 | 25.48-25.53 s | `rog5-platform-modules` loads msm (MDSS BCR reset, DSI PHY probe) and `panel_asus_rog5_ams678`. The panel probe takes `reset-gpios` (tlmm 24, active low) with `GPIOD_OUT_HIGH`: **reset asserted** | **Glitch 2.** The panel drops out (black, possibly a flash) |
| 6 | 25.59 s | systemd-backlight restores 10; the panel is not initialized, so 0061 only stores it | no change |
| 7 | 27.93 s | `rog5-phosh.service`: `chvt 7` (no fbcon, dummy console: no visible effect), phosh-session, phoc | black |
| 8 | 30.21-30.59 s | phoc's first modeset: panel prepare (regulators, Iris check, reset pulse, init, PPS, DSC on) then enable (`51 00 00`, `53`, `55`, display on) and `drm_panel_enable()` restores the brightness **before** the first frame is sent (the kickoff comes after the bridge enable) | **Glitch 3.** For a frame or two the panel shows its post-reset RAM content lit; then phoc's first frame (black) |
| 9 | 30.75-34.23 s | phoc shell mode raises its output shield: black with a 32-px (80 px at scale 2.5) spinner until phosh reports `SHELL_STATE_UP` ("Phosh ready after 1,13s" at 34.23 s; gnome-session start takes ~2 s of the gap). `Atomic commit failed: Device or resource busy` x4 at 31.3-32.8 s drop a few spinner frames | black + spinner (phoc's loading animation) |
| 10 | 34.23 s | shield lowered with duration 0 | Phosh lock screen |

The old claim in `boot-modules.list` ("without the fbdev client the bootloader
splash stays up until Denial takes the display over") was only half true:
dropping the fbdev client removed a modeset at msm probe, but the splash was
already gone at 0.06 s (stage 3) and the panel was reset at 25.5 s (stage 5).

Not glitches: the VT switch (dummy console), systemd-backlight (stored only),
the DSI PLL WARNs at 25.5 s (panel RAM is untouched with the MDP stopped),
ABL itself (signed, out of reach). The splash partition (`sde53`, 34 MB) is
all zeros; ABL's picture comes from elsewhere. The stock boot animation is
`system/media/bootanimation.zip` in the WW OTA's system image (sha256
`ccd6f7ca…`, 9.5 MB): `desc.txt` `1080 2340 30`, part0 = 81 PNG frames
played once (the ROG eye glows up, then "REPUBLIC OF GAMERS" appears, 2.7 s),
part1 = one frame looped (the static ROG eye + text on black). The PNGs are
1080x2448 RGB, native panel size. Extracted (stock material, not in Git) to
`~/.local/state/rog5-bootsplash-work/bootanim/`.

## Why the splash can survive to phoc

- The splash buffer is safe: `asus_splash_mem` 0xe5000000+0x2300000 is `no-map`
  in our DT, `reserved` in `/proc/iomem`, and the 5.4 wrapper reserves it too.
- The streams are already in bypass after the SMMU reset: `qcom_smmu_cfg_probe()`
  marks bootloader-valid SMRs BYPASS (the SM8350 hypervisor turns that into the
  bypass bank, see 0064). Only the DMA default domain breaks it. Other Qualcomm
  MDSS compatibles are in `qcom_smmu_client_of_match` for this reason;
  `qcom,sm8350-mdss` is not.
- A command-mode panel keeps displaying its RAM with the link idle, so the
  clock gating at 0.558 s and the MDSS reset at msm probe do not change the
  picture as long as the last frames were good.
- The panel rails are not switched off: L12C/L13C have no boot-on, the RPMh
  regulator reports "unknown" (-EINVAL) and `regulator_late_cleanup()` treats
  that as off, so nothing disables them before phoc's modeset.

## Changes on `agent/bootsplash`

- **0107 iommu/arm-smmu-qcom: identity default domain for the SM8350 MDSS.**
  One line in `qcom_smmu_client_of_match`. The MDP keeps reading the splash
  through the bypass bank until 0.558 s; msm attaches its own paging domain
  at bind as before (as on sm8250/sm8150). Built into the Image.
- **0108 drm/panel ams678: keep the bootloader splash until the first frame.**
  - `handoff` (bool, 0444, default Y): the reset line is requested
    `GPIOD_ASIS`. If it is an output, deasserted, and the Iris6
    bypass-ready line is high, the probe logs `bootloader left the panel on:
    keeping its picture until the first frame` and the first prepare skips the
    reset pulse (regulator votes, Iris check, init sequence, PPS and DSC are
    sent as usual). Otherwise it logs `panel not left on by the bootloader:
    holding it in reset` and asserts reset as before. `handoff=0` restores the
    old probe exactly.
  - `bl_delay_ms` (uint, 0644, default 50): after display on the DBV stays 0
    (dark on this panel) and a delayed work applies the stored level 50 ms
    later, once the first frame is on the panel. `update_status` during the
    hold only stores the level; unprepare/remove cancel the work. This also
    covers every unblank (reset -> display on -> first frame). `0` = old
    behaviour.
- `boot-modules.list`: comment corrected; no module or parameter change.

Expected sequence with both: ABL picture continuously until ~30.2 s (phoc's
modeset; the picture goes dark at display on, ~25 ms before phoc's black
frame), then phoc's black shield with its spinner, then the lock screen at
~34 s. No black gap before phoc, no reset flash, no garbage frame.

## Offline results

- Both patches apply on the r86 source tree (post-0106) with `git apply --check`.
- The patched panel driver builds warning-free out of tree with W=1 against the
  r86 objects (clang-20, LLVM=1).
- `scripts/device/test-production-platform-kit.py`: 18 tests OK with the edited
  `boot-modules.list`.
- Full production build `~/.local/state/rog5-kernel-7.2.7-build-r91-splash`
  (from commit c9e1f9be): **PASS**, 567 s, 0 unreviewed diagnostics, all
  stages PASS. `.config` identical to r86 (`a90f8c5f…`). Image
  `ab95aec8…` (31488512 bytes); `modinfo` of the panel module lists
  `handoff` and `bl_delay_ms`. Unsigned, not packaged, not installed.

## On-phone test (parent)

Build a RAM-trial bundle exactly like r185 (same DTB
`platform-cpucap-dp-sbumux-dtb-r2/board.dtb`, ramdisk rebuilt from the r91-splash
module tree, new bundle name, e.g. `production-7.2.7-r186-splash`). No DTB
change is needed. Then:

1. Before the trial, if possible, film a normal r185 reboot (phone camera,
   ideally 120 fps) from ABL to the lock screen. Expected: the ABL picture,
   then corruption at the kernel start (glitch 1), black at ~25 s after the
   kexec (glitch 2), a flash at ~30 s (glitch 3), the spinner, the lock screen.
2. RAM-boot the r186 wrapper and film it the same way. PASS: the ABL picture
   stays unchanged until the spinner screen, and nothing between the spinner
   and the lock screen.
3. Logs (read-only):
   - `dmesg | grep -c 'Unhandled context fault'` = 0 (was 10 at 0.063 s).
   - `cat /sys/kernel/iommu_groups/*/type` next to
     `ls /sys/kernel/iommu_groups/*/devices`: the `ae00000.display-subsystem`
     group reads `identity`.
   - `dmesg | grep -i 'bootloader left the panel on'` present once.
   - `grep . /sys/module/panel_asus_rog5_ams678/parameters/*`:
     `handoff=Y`, `bl_delay_ms=50`.
   - `journalctl -b | grep -c 'Atomic commit failed'` (r185: 4) and no new WARN
     in `dmesg` besides the two known `dsi0_phy_pll_out_dsiclk` ones.
4. Function (user): lock screen, unlock, brightness slider (3 visible levels as
   before), power-button blank/unblank x3 with no garbage flash on wake,
   suspend/resume once, Desktop mode on the external monitor once.
5. If step 2 shows a disturbance of the logo about 0.5 s after the kexec (the
   clock gating), note it: the fallback is a 0109 that keeps the dispcc MDP,
   byte, pixel and esc clocks out of `clk_disable_unused` until msm binds.
   If the probe logs "not left on", read `grep -E 'gpio(24|84)'
   /sys/kernel/debug/gpio` (not a DRI file) and report it.
   A/B without a rebuild: `panel_asus_rog5_ams678 handoff=0` in the ramdisk's
   `boot-modules`, or `echo 0 > /sys/module/panel_asus_rog5_ams678/parameters/bl_delay_ms`
   (takes effect at the next unblank).

## Options considered (ranked)

1. **Keep the ABL picture until phoc (0107 + 0108).** Small (one SMMU table
   line, ~100 lines in our own panel driver), low risk, no userspace change,
   works with the kexec: the picture lives in the panel RAM and in no-map
   memory, and nothing between ABL and phoc needs to redraw it. Remaining gap:
   phoc's black shield with its spinner for ~3.5 s, which is the compositor's
   own loading indicator. **Recommended.**
2. **Show the picture on phoc's shield too** (patch our phoc build, which is
   already rebuilt on the phone, see `packaging/arch/phoc`): raise the output
   shield before the first commit in shell mode and draw an image (for example
   the first frame of a ROG logo) under the spinner, so the lock screen
   replaces a logo instead of black. Medium effort (a `PhocBling` texture from
   a PNG plus ordering in `phoc_server_start`), low risk, fully seamless only if
   the image matches ABL's picture pixel for pixel. We do not have ABL's image as
   a file (the splash partition is empty); it could be read from 0xe5000000
   once 0107 is in, but not by `/dev/mem` (no-map memory; `read()` refuses it
   and the uncached `mmap` path was not tried on a running phone). Worth doing
   only if the black spinner screen still reads as a glitch after option 1.
3. **Own KMS splash or Plymouth (DRM renderer) from msm probe to phoc.** msm
   loads at 25.5 s from the root, so an animation could run for ~5 s at most;
   it needs a DRM-master handover to phoc without a modeset (same mode, so no
   panel re-init) and adds a package and ordering around
   `rog5-platform-modules`. Moving msm into the initramfs for an earlier start
   touches the GPU/GMU ordering (rog5_gmu_bind, gpucc sync_state). High effort
   and risk for a few seconds of animation after a static logo.
4. **Stock boot animation frames.** Available (see above) at native
   resolution, so no scaling. The part1 frame (static ROG logo) is the natural
   image for option 2's shield; the 81-frame part0 could run under option 3
   or on phoc's shield while phosh starts (~2.7 s fits the ~3.5 s gap).
   ASUS artwork: keep it on the phone/host, not in the repository.
5. **Backlight choreography only** (for example DBV 0 until phosh is up): does
   nothing for glitch 1 (bad frames at 0.06 s) and turns the logo off early;
   the `bl_delay_ms` part of 0108 is the useful piece of it.
