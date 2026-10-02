# HDMI converter recovery and HBR2 trials

The converter stays capped at HBR (`dp_pcon_max_rate=270000`) for production.
Patches 0200–0203 have no on-phone qualification; single-training and AHB reset
are default-off RAM trials. Training success alone does not establish a picture.
See the [HBR2 result](../../test-results/2026-09-29-hbr2-and-server-checks.md)
and the [RAM-trial procedure](../development.md).

Use a fresh RAM candidate, a verified fallback and an independent control
connection. Keep the same hub on the side USB-C port, cable, orientation,
compositor and advertised 1920x1080@60 mode; keep HDR and audio off.
Parameters live under `/sys/module/msm/parameters/`; change them with output off.
Use the compositor's normal output control (Phosh: `wlr-randr`, after verifying
its output name and timing). Do not unload active `msm` or read DP debugfs.

1. Before the initial connection, set `dp_pcon_max_rate=0`,
   `dp_link_policy=0`, `dp_max_lanes=2`, `dp_max_bpc=8` and
   `dp_max_rate=270000`. Set `dp_sink_power_cycle`, `dp_pcon_single_train`,
   `dp_pcon_ahb_reset` and `dp_async_msa` to 0. Keep polarity, FIFO, CRC and
   electrical overrides at baseline. Connect the hub and enable 1080p60.
   Require HBR × 2, RGB8 and visible moving content for 15 seconds.
   Stop if this baseline fails.
2. Output off; select HBR2 with `dp_max_rate=0`, leaving the converter cap
   at 0. Cached receiver capability already includes HBR2. Reproduce the
   default failure once, then recover the visible HBR baseline below.
3. From a recovered baseline, try exactly one setting at a time, in order:
   `dp_sink_power_cycle=1` → `dp_pcon_single_train=1` →
   `dp_pcon_ahb_reset=1` → `dp_async_msa=1`.
   Reset all four to 0 between arms; recover visible HBR before each comparison.
   With output off, select `dp_max_rate=0` and enable the same RGB8 mode.
   Require 2 × 540000 kHz, bpp 24, moving content and 15-second stability;
   HBR fallback or rc=0 with a dark screen is not a pass. Preserve bounded
   enable/HPD/error logs, and repeat off/on and recovery for any promising arm.
   Stop after two non-discriminating failures at the same boundary.

## Recovery

Output off; clear all four candidates, set `dp_max_rate=270000` and
`dp_sink_power_cycle=1`, then enable 1080p60. Require checked D3 → D0,
HBR × 2, RGB8 and visible moving content; repeat off/on once without replug
or reboot. Turn the power-cycle setting back off before the next trial arm.
If still dark, stop and preserve evidence. Physical replug and reboot are
separately recorded rescue actions, not successful software recovery.

On completion, turn output off and restore saved settings, especially
`dp_pcon_max_rate=270000`; reconnect the hub to refresh cached capabilities
before normal use. Keep trials in RAM until picture and recovery are qualified.
