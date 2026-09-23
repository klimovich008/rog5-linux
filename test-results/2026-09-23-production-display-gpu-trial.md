# Production display/GPU trial d1 — September 23

The first bounded OLED + Adreno 660 trial on `7.1.4-rog5-production`. It ran
as a RAM boot with no flashing, under the standing authorization for
hands-free phone tests. Question: with the production kernel and modprobe
ramdisk, do the DSI panel and the A660 come up through the upstream msm
driver?

Answer: **yes for both.** The GPU initializes and runs its first commands
with the stock ASUS zap. After the brightness fix found in d2–d7 (below,
patch 0043), the user saw the test bands in the right colors and order on
the OLED.

## Image (private, `~/.local/state/rog5-production-boot-20260923/`)

| Item | SHA-256 |
|---|---|
| Image (build-r2, unchanged from r3) | `0789c10855e74c2f54caee7437864235f5872118e9f697782cc8547b286d406a` |
| DTB `display-dtb-r1/board.dtb` | `de1cce47f963642b4436deabcd6ecf0c1128105551d2ecf9367bb965a6fdb9e6` |
| Ramdisk r5 (r4 plus the display firmware) | `aa5b1970db5beea8fb4d4268ade6b3952faba919dad053afb16d2604d99813f2` |
| Firmware `display-firmware-r1/SHA256SUMS` (stock ASUS a660 GMU, SQE, split zap) | `25e5a47792bd62083bc84e262718bb205e9bb328ef6ba5e05539862bac91842b` |
| Signed manifest `production-display-r1` | `b08f9e91c631344557660a5afcc731854b6ec5e14455daef9a9720c762d7aae1` |
| 128 MiB RAM wrapper (`package-r5`) | `73b9b028499c01d1f3d7b614f18e1a107f8c9a8e55dfdee57ef845e22d1a6519` |

The DTB is `scripts/device/compose-production-display-dtb.sh` applied to the V9
headless DTB. It adds the display-60hz-reviewed overlay (TE pad as
`mdp_vsync`, `te-gpios` dropped) and the gpu overlay (zap
`qcom/sm8350/a660_zap.mdt`), and enables GMU, GPUCC and the GPU SMMU.

## Boot

Fastboot accepted the RAM boot at 15:18:12Z. The target enumerated at
15:18:29, stage records arrived from kernel-verified through overlay PASS, and
SSH health was at 15:18:56. The boot then stayed up with no rollback.

## Step runner (`production-display-trial.py`, evidence `display-d1/`)

| Step | Result |
|---|---|
| refgen, gpucc | loaded |
| smmu-bind | **EPERM**: arm-smmu suppresses bind attributes. The runner wrongly reported ok (its check read the exit code of a trailing `ls`); fixed below. |
| msm `separate_gpu_kms=1` | loaded; KMS alone on card0; `no GPU device was found` |
| panel `panel_asus_rog5_ams678` | loaded; `card0-DSI-1 connected enabled 1080x2448`; fbcon `msm-kmsdrmfb`; backlight `ae94000.dsi.0`, max 1023, default 10 |
| brightness | 255 for 20 s, then 0. Not observed by a person. |
| gpu-open | no render node, because the SMMU was unbound |

## Follow-up on the same boot (manual SSH, read-only except sysfs probe/backlight/fb0)

- **GPU SMMU.** `echo 3da0000.iommu > /sys/bus/platform/drivers_probe` at
  133 s probed it (SMMUv2, 7 context banks). The deferred-probe trigger then
  bound adreno as a separate DRM device: `Initialized msm 1.13.0 for
  3d00000.gpu on minor 1`, `renderD128`.
- **GPU start.** The first open of `renderD128` at 230 s loaded
  `a660_sqe.fw` and `a660_gmu.bin` (GMU firmware v3.1.5). debugfs `gpu`
  shows `gpu-initialized: 1`, revision 660 (06060001), rbbm-status 0 and
  ringbuffer rptr = wptr = 11: the CP consumed the init packets. There was no
  `Zap shader not enabled` fallback warning, so the zap went through PAS. Every
  later resume (debugfs reads, a second open) initializes cleanly.
- **Open GPU error.** Every runtime suspend logs `HFI_H2F_MSG_PREPARE_SLUMBER
  returned error -2004318072` (0x88888888). It is not fatal, and resume works.
- **DSI PLL.** `DSI PLL(0) lock failed, status=0` plus two clk
  `already disabled/unprepared` WARNs at 40.8 s come from
  `clk_core_reparent_orphans` in `dsi_phy_driver_probe`. The dispcc byte/pixel
  RCGs left on by the bootloader get reparented before Linux programs the PLL.
  The modeset then locks it. clk_summary shows dsi0vco 723.53 MHz, bit clock
  361.76 MHz, byte 45.22 MHz, pclk 60.29 MHz, esc 19.2 MHz and mdp 200 MHz, all
  enabled. The clock tree is consistent with a 4-lane DSC link, so the
  non-bonded divider regression (revert `44784327815b`) shows no visible
  effect here. It stays a candidate cherry-pick.
- **Frames.** DPU plane-0 on crtc-0 scans the fbcon buffer (XR24
  1080x2448, pitch 4352). msm-kms, dsi_isr and pingpong-done interrupts
  count, with no pp_done timeouts or underruns.
- **Test pattern.** Streaming four color bands (red, green, blue and white,
  top to bottom in memory) into `/dev/fb0` read back with the exact SHA-256
  `f499d5e9…`. Pingpong-done rose from 434 to 451 through damage commits. The
  phone-side backlight auto-off timer was verified at brightness 1.
- **Remaining SMMU faults.** The early `15000000.iommu` context faults at
  0.093 s (SIDs 0x820/0xc20) are probably the MDP still fetching the
  bootloader splash when the apps SMMU resets. All 10 are at 0.093 s; none
  occur later.


## Changes from this run

- `production-display-trial.py`: the brightness step uses max_brightness;
  a quarter of it is dark on this panel (only DBV[9:8] takes effect).
- `production-display-trial.py`: the SMMU step reprobes through
  `drivers_probe`, requires the driver link, and no longer stops the display
  steps when it fails. gpu-open waits up to 5 s for the render node. Every step
  now checks its own success marker in the step output.

## Open after d1

- GMU `PREPARE_SLUMBER` ack error with the stock v3.1.5 GMU firmware. The build
  has `INIT_STACK_ALL_ZERO=y`, so 0x88888888 is what the GMU wrote, not stack
  garbage. KGSL fails the ack only when the error is 1; upstream fails any
  nonzero value and then runs `a6xx_gmu_force_off`, so every suspend is a hard
  GMU power-off. Next candidate: linux-firmware `a660_gmu.bin` (`8acab7b4…`,
  55252 B; stock is 54700 B). The GMU image is not TZ-authenticated.
- The SMMU deferred timeout could be removed by loading gpucc in the display
  ramdisk before the 10 s deadline, or by keeping the runtime reprobe.
- `fb0: sys_imageblit/Framebuffer is not in virtual address space` warnings
  appear, but fbcon draws (the readback shows glyphs).
- No mesa on the root, so there is no userspace GPU workload yet.

## Visual check and the black-screen root cause (trials d2–d7)

Visual result: **PASS on d6.** At brightness 1023 the user saw four bands, red,
green, blue and white, top to bottom. That is the framebuffer layout, so the
colors and orientation are correct through DPU → DSC → DSI → Iris analog
bypass → OLED. The first two looks (d1 at 15:32Z and d6 at 16:49Z, both at
brightness 255) were black.

Each trial RAM-booted the same Image, DTB `de1cce47…` and ramdisk r5 under a new
bundle name, so every boot had its own one-use claim. The test panel modules
were built out of tree against the build-r2 objects and loaded with insmod from /tmp.

| Trial | Bundle | Wrapper | What it tested |
|---|---|---|---|
| d2 | `production-display-r2` | `ecfd6c05dea4de3a…` | panel untouched → msm → stock panel; rails sampled each second |
| d3 | `production-display-r3` | `ba148a26c292ff76…` | insmod of the XBL-sequence panel variant |
| d4 | `production-display-r4` | `89741baf32165c69…` | soft-reset variant; probe matrix (the LP/HS split was found here) |
| d5 | `production-display-r5` | `16a184546b540cb0…` | stock panel module + LP brightness |
| d6 | `production-display-r6` | `7ff58cdbbbcdd0ee…` | **0043 panel module; visual PASS** |
| d7 | `production-display-r7` | `54e213d4f3e00c87…` | 0043 + continuous DSI clock (HS long writes still ignored) |

Method: the phone's USB input current served as a light meter, with the
battery full and the input limited to 500 mA. A full-white OLED at high
brightness pushes the input to the limit and discharges the battery (about
−15 mA); a black frame stays at idle (about 230–320 mA). Read-only DCS status
came from a one-shot out-of-tree probe module that fails its own init
(`scratchpad dsiprobe`; not in the repository).

| Finding | Evidence |
|---|---|
| The panel controller is healthy | 0x0A = 0x9C (booster, sleep out, normal, display on), 0x0E = 0x80 (TE on), 0x0F = 0xC0, 0x05 = 0, scanline advances; `err-fg` (gpio27) is high, which ASUS treats as normal (its IRQ is falling-edge) |
| The PPS is right | msm's packed `dsi->dsc` equals the vendor 0x9E payload byte for byte |
| PM8350B AB/IBB/OLEDB (SID 3, 0xF800/0xF900/0xFA00) stay off, even while the panel is lit | STATUS1 = 0 throughout; the rails that UEFI polls are not this panel's supply on these boots |
| **Brightness sent in HS mode is ignored** | HS long `51 03 FF` leaves a white frame at idle current; an LP write of the same bytes draws the input limit plus battery |
| HS short DCS writes do work | HS `34` (tear off) clears 0x0E bit 7; HS one-byte `51 03` lights the panel |
| **Only DBV[9:8] takes effect** | White-frame current steps at 256, 512 and 768 and is flat within each block; `51 00 FF` (255) is dark, `51 04 00` is dark, one-byte `51 FF` is full; confirmed by eye (255 black, 1023 bright) |
| The stock init sequence is fine | d5: stock packaged panel module plus an LP write of 1023 → lit |
| Not needed | DCS soft reset, the XBL init sequence, a continuous DSI clock (d7: HS long writes still ignored) |

The earlier hypotheses in this report's first draft (DSI PLL regression, AMOLED
rails, level-2 registers, soft reset) were each tested and dropped.

## Driver fix

`patches/linux-7.1.4/0043-drm-panel-asus-rog5-ams678-send-brightness-in-LP-mode.patch`:
the backlight callback now keeps `MIPI_DSI_MODE_LPM` for the 0x51 write.
Verified on d6 through sysfs only: a white frame at 1023 drew 496 mA plus
battery current, before and after a full panel power cycle, and a black frame
stayed at idle. Checked offline by `scripts/device/test-ams678-lp-brightness.py`
(applies 0037+0043, checks the one-line change, runs the lifecycle harness).

## Open after d7

- Brightness has four effective steps: 0–255 dark, 256–511, 512–767 and
  768–1023. ASUS sends the same `[hi, lo]` bytes in HS mode, and on Android
  brightness is smooth, so the low byte probably needs a working HS long
  write. Why HS long command packets are dropped (msm command DMA with DSC,
  the Iris analog bypass, or PHY timing at 361 Mbps) is not known.
- `dsi_err_worker: status=5` once at panel bind on d6.
- The GMU `PREPARE_SLUMBER` ack error and the SMMU deferred timeout, as above.
