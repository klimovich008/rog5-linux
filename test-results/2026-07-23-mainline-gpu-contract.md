# Linux 7.1 A660 GPU contract - 2026-07-23

Result: **PASS** for the compile-only opt-in overlay. It is not included in the recovery boot image.

Linux 7.1.4 already defines the SM8350 Adreno 660 GPU, GMU, SMMU, power domains, clocks, thermal cooling links, and operating points. The ASUS board layer therefore adds no driver or register data. It only enables the upstream GPU node and selects the same SM8350 zap-shader path used by the upstream HDK.

## Gate

- Exactly `&gpu` and `&gpu_zap_shader` are changed.
- Recovery UFS and left-side USB1 remain enabled.
- USB2 and the display subsystem remain disabled.
- No register, rail, memory, OPP, boot-argument, UFS, USB, or display property is introduced by the GPU overlay.
- The combined DTB compiles, round-trips, and passes exact property checks.

Combined DTB SHA-256: `2646b58c1f71890a638f2515961d2ba4b98fea3e4ea548801ff1512fcf3f8d5d`.

The matching `a660_sqe.fw`, `a660_gmu.bin`, and SM8350 `a660_zap.mbn` from `linux-firmware` 20260622 now pass pinned size, SHA-256, path, and ELF-format gates. A locally extracted old ASUS Android 11 set is retained only as a device-signature fallback and is not committed. The GPU tier remains outside the recovery package until base recovery passes on hardware. Repeated render-node open/close, GMU idle, Vulkan, KWin, thermal, and power tests remain hardware gates.
