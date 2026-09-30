# Night review 2026-09-30 → 10-01

The user asked, before sleeping, for every issue so far to be analysed with
agents and GPT-6.1-Sol (fix / improve / reimplement), plus a GNOME test by
an agent using the desktop like a person. Five area agents (display, USB and
storage, audio and sensors, power and kernel, system and apps) worked
read-only on the phone. Each wrote briefs for GPT-6.1-Sol, and every claim
below was checked against the source or the phone before it was used. The
agents' full reports and proposal files stayed in the session scratchpad; the
condensed findings are here.

## Fixed tonight (committed; live on the phone unless marked "next boot")

| Area | Problem | Fix |
|---|---|---|
| Security | Desktop mode started GNOME (no lock screen) from a **locked** phone: Phosh's `GetActive` only means "panel blanked", and Phosh's boot lock never reached logind | `rog5-desktop-mode` requires a logind LockedHint yes→no of the same session (fails closed), debounce 21 s off / 6 s on; phosh 0.57.0-1.2 (0002) sends the startup lock to logind (installed, next session) |
| Data | `rog5-update` pruned `snapshots/<id>/failed-upper` (a rollback's newer data, e.g. /home) at the next update | kept; test (next boot) |
| Data/UX | three restore paths rebooted during use; `bb reboot -f` fallback | idle rule + no forced reboot; plus: no reboot while sound plays, 01–06 reboot window, `MemoryHigh=2G`; tests (next boot) |
| Crash | phoc SIGSEGV at phoc+0x4446c on DP unplug (inert layer surface) | phoc 0.57.0-1.2 (0001, alpha/draggable/stacked), packaging now in `packages/phoc` (installed, next session) |
| Reset | 09-29 17:29 phone reset: `dwc3_qcom_read_usb2_speed()` dereferenced a NULL hcd after an xHCI unbind | kernel 0117 (next boot) |
| Storage | udisks could unmount/format the loop devices backed by the UFS root/state images, and create RAID over UFS | polkit rule refuses them; loops get `UDISKS_IGNORE` (live + next boot) |
| Power | USB runtime PM stayed off after every dwc3 rebind by the reconnect helper | udev rule on `bind` |
| Audio | `alsactl restore` ran after our route and restored the last shutdown's mixer (-12 dB at boot) | `rog5-audio-route.service` from udev after the restore (+ WirePlumber re-probe); analog gain explicit |
| Audio | bottom amp's interrupt went silent with PLL events latched, so its faults would go unreported | kernel 0115 masks unused sources and the PLL IRQs like stock (next boot) |
| Audio | PipeWire failed a capture probe on MultiMedia1/2 at every login | DT: playback-only front ends (DTB r5, next boot) |
| Sensors | proximity ignored (no `PROXIMITY_NEAR_LEVEL`) | udev rule, 239 from this unit's factory calibration |
| Sleep | desktop mode on battery would suspend (only the monitor's power prevented it); link-local IPv6 SSH not seen | lit external display keeps the phone awake; address parsing fixed |
| Boot | Wi-Fi radio waited ~16 s per boot for SoC junction zones < 60 °C | thermal gate covers board zones only (next boot) |
| Memory | no swap; THP `always` (1.6 GiB in huge pages); zram fell back to lz4; OOM of an SSH command stopped sshd | 5.2 GiB zram zstd, swappiness 100, THP madvise, dirty 64M/256M, MGLRU + TEO governor (next boot), sshd `OOMPolicy=continue` |
| Tailscale | ramdisk tailscaled failed every 60 s; two daemons contend for tailscale0/table 52 | skips while usb0 is down and while the packaged tailscaled runs; fallback via `OnFailure=` |
| Perf | performance thermal trips only by hand | `rog5-perf-mode auto` (performance on external power with a DP display), set as the phone's mode |
| Steam | installer still called `unzip` (backslash names), could write through a symlinked dir | extractor used, symlink escape refused, refuses while Steam runs |
| Kernel | SIGBUS on instruction fetch (r193): arm64 gives BUS_OBJERR only for a synchronous external abort, not a page-cache failure | 0116 logs every user SEA with its PFN (`rog5_sea.retire=1` optional) (next boot) |
| Display | the "latched" blue screen isn't latched: at 453-469 MHz (1-2 % or no margin over the 460 MHz core clock) every frame underran; the counter only stops once the encoder IRQs are off after idle | 0114 (modes above ~438 MHz rejected) kept, wording fixed; 0118 logs underruns with mode and core clock (next boot) |
| Display | HDMI hub dark at HBR2 | 0119: opt-in `msm.dp_async_msa` / `msm.dp_sink_power_cycle` (Steam Deck behaviour), 8 bpc floor behind HDMI/DVI converters, logging (next boot; test with the user) |
| Display | 4-lane DP needs to know what the monitor offers | 0120 logs the ADSP's DP pin assignment on every plug-in |

## Needs the user (morning)

1. **GNOME human test**: starting GNOME for the tester was refused by the
   permission system (it would have left an unlocked desktop overnight). Run it
   while the user is present, or approve it.
2. **USB -71 one-replug test** (`morning-test.sh` from the USB agent): the
   monitor was in standby overnight (no DP, no USB). Decides between a kernel
   enumeration retry (usbcore) and the dwc3 glue session-override fix, which
   would retire the reconnect helper's rebind.
3. **Speakers**: stock loudness needs the CS35L45 protection firmware. It was
   extracted from the stock OTA; the plan (per-amp firmware names patch,
   calibration values, DSP routing) needs a daytime listening test.
4. **Desktop mode after the Phosh patch**: boot with the monitor on, unlock with
   the PIN; GNOME must start only after the unlock.
5. **Display T1** (5 min, GNOME at 3840x1080@60): set the DPU core clock to
   200/300/460 MHz via debugfs `core_perf/fix_core_clk_rate` and watch the
   underrun count: tells whether the ~1 pixel/clock limit (H1) holds, i.e.
   whether 4-lane DP could ever give 5120x1440@60.
6. **Display T2**: GNOME without the 460 MHz / 15.5 GB/s pin (5 starts, 5
   replugs); if clean, drop the pin (saves DDR power all session).
7. **HDMI hub**: the 0119 knob sequence (sink D3/D0, then async MSA) at HBR2.

## Open, with a plan

- **Standby** (DDR/CX never collapse): boot-time bisects: SLPI off, then no
  ADSP, then load CDSP/SPSS; last resort a stock RAM capture (needs fastboot
  approval).
- **SIGBUS root cause**: hypotheses are the ASUS wrapper's TZ SHM bridge
  surviving kexec, or hypervisor-bridged PAS buffers; 0116 plus the exec
  scanner name the PFNs next time.
- **Bottom USB-C port stage B**: mainline RT1715 (tcpci_rt1711h) + TCPM on
  i2c13 for automatic 5 V instead of `rog5-usb-bottom on`.
- **Updater snapshots** copy /home: exclude user data from rollbacks.
- **Loop direct I/O** for the root image (1 GB of page cache is duplicated).
- **Steam title-bar drag**: mutter ignores the move request (likely CEF root
  coordinates); needs an `xev` capture while the user drags.
- **DP audio to the monitor**, sensor factory calibration via hexagonrpcd, USB3
  on the side port, 4-lane DP (after T1), HDR (staged port of stock's
  VSC/HDR-metadata SDPs, 350-600 lines), a GNOME output helper so the phone
  panel stays out of the layout for new monitors: proposals in the reports.

## Verified on r197 (booted 2026-10-01 05:03; kernel r100 = 0001-0120, DTB r5)

- 0 failed units (after the rog5-perf-mode start-limit fix), 0 SMMU faults.
- Locked phone at boot: logind LockedHint=yes (phosh 0002), desktop mode (auto)
  stayed in Phosh with the monitor attached and awake.
- Speakers 0 dB / 19 dBV, routed after alsactl restore (55.8 s); no PipeWire
  capture-probe errors.
- CS35L45: masks as predicted (0x5ffdfe7f, banks 5/8 0xffffffff), IRQ1_STATUS 0
  on both amps, PLL IRQs not requested.
- Wi-Fi radio ready at 49.9 s (65.4 s on r194).
- zram zstd 5.2 GiB, MGLRU on (min_ttl 1000 ms), TEO available, THP madvise.
- UFS-backed loops carry UDISKS_IGNORE; ramdisk tailscaled skipped
  (exec-condition), packaged tailscaled active.
- `rog5-perf-mode auto` picks performance (monitor power + DP).
- Side-port USB at boot: first attempt found nothing, retry 1 (88 s)
  re-initialised, keyboard/mouse hub up at 103 s.
- New logs: the MSI 491C offers DP pin assignment **C** (3 = 4-lane DP-only),
  so 4 lanes is possible with it; Phosh's first DP enable at 3840x1080@60 with
  a 335 MHz core clock underran 8-15 times, then stayed clean (the known
  first-enable burst).

## GPT-6.1-Sol review of the display/desktop-mode patches (05:27)

`2026-10-01-gpt-6.1-sol-display-patch-review.md`. Checked against what shipped:

- Its "cross-session bypass" applies to the display agent's PID-based switcher
  variant, not the shipped one (which binds `seen_locked` to the logind session
  id). Left: a few-ms race if the phone auto-locks exactly while a monitor is
  plugged in.
- phosh 0002: lock notifications are connected only after the session-bus name
  is acquired; at boot that can only lose an unlock (fails closed). Worth
  fixing before sending upstream.
- 0119 `dp_async_msa` flips the clock-mode bits but keeps static M/N (amdgpu
  measures M): an experiment only; Sol suggests refusing the knob until
  measurement exists. Also: the 8 bpc floor should reject (not override) a
  6 bpc ceiling; `msm_dp_link_psm_config()` returns 0 when every D0 write
  failed. Follow-ups for the next kernel.
- 0118: say "requested core clk", READ_ONCE/WRITE_ONCE on the field (cosmetic).

## Display addendum (display agent + Sol DPU-clock run, ~05:40)

- The switcher bypass Sol found (a lock seen in one session vouching for a
  new one) was in the display agent's PID-based variant; the shipped switcher
  uses only the logind session id, so auto mode stays on. Shared remaining gap:
  a lock within the 3 s poll window. The agent's revised phosh 0002 also
  publishes from `on_name_acquired` (an unlock at boot can otherwise be lost,
  which only keeps GNOME off): take it at the next phosh build.
- 0118/0119 follow-ups prepared by the agent (scratchpad): "requested core
  clk" + READ_ONCE; the converter 8 bpc floor rejects instead of overriding a
  lower ceiling; `msm_dp_aux_link_power_up()` reports failed D0 writes;
  `dp_async_msa` marked experimental (static M/N).
- DPU clock (`2026-10-01-gpt-6.1-sol-dpu-clock.md`): "latched" confirmed not a
  latched state. Sol ranks QoS/fetch latency at first enable (H3) above 6 bpc
  (H2) and the full-pixel-rate limit (H1): mainline's SM8350 QoS tables differ
  from stock's 60 Hz set (CREQ 0x0011222222335777 vs 0x0011223344556677; no
  VBIF OT limits). 0114 is a quarantine of two failing modes, not a proven
  limit. New tests: bit depth (dp_max_bpc 6/8/6 at the 460 MHz pin), and in the
  failing state raise bandwidth vs clock separately; candidate fix: port stock's
  60 Hz QoS tables, then drop the GNOME pin. 0101's commit text is wrong (INTF
  timing starts after the CTL flush).

## Sol standby and USB re-reviews (05:20-06:00)

- `2026-10-01-gpt-6.1-sol-standby.md`: leading suspects ADSP firmware sleep
  policy (charger PD, no island mode in mainline) and the SLPI sleep set; no
  single MC/SH/ACV voter proven. Stock's `ddr: ddr_log` AOP control is the one
  untested QMP difference. The boot-time bisects stay the plan.
- `2026-10-01-gpt-6.1-sol-usb-review.md`: agrees with 0117 (mechanism; "confirmed
  cause" too strong without an oops record), p2 (femto HOST_SS checks), p4;
  p3 (usbcore retry) to revise before adoption; p7 incomplete. Storage
  correction applied: udisks falls back to the device path for the `drive`
  detail, so the first rule already refused **all** loops, including a user's
  ISO; the rule now decides loops by backing file first (UFS images refused,
  unreadable backing refused, other loops default rules) and also refuses
  `cancel-job-other-user`. Checked with pkcheck: UFS loops/partition refused,
  a user image loop and a USB stick allowed.
