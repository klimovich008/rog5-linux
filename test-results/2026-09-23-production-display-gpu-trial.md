# Production display/GPU trial d1 — September 23

The first bounded OLED + Adreno 660 trial on `7.1.4-rog5-production`. It ran
as a RAM boot with no flashing, under the standing authorization for
hands-free phone tests. Question: with the production kernel and modprobe
ramdisk, do the DSI panel and the A660 come up through the upstream msm
driver?

Answer: **yes for both, with one visual check pending.** The GPU initializes
and runs its first commands with the stock ASUS zap. The DSI link runs and
frames reach the panel. No human has looked at the screen yet.

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

## Visual check

Pending: a person looks at the screen for up to 90 s at brightness 255 and
reports the band order.

## Changes from this run

- `production-display-trial.py`: the SMMU step reprobes through
  `drivers_probe`, requires the driver link, and no longer stops the display
  steps when it fails. gpu-open waits up to 5 s for the render node. Every step
  now checks its own success marker in the step output.

## Open

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
