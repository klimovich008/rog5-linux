# Display60 V10 pre-switch acceptance

Result: **display registration PASS; direct fallback PASS**.

- Exact target boot: `e42ea9e1-2303-43df-b934-0bd8eccb509a`.
- Final read-only runtime preparation passed before observation.
- Signed NCM record proved `present` for REFGEN, DSI, DRM, `/dev/fb0`, one
  backlight, and all minimal status-screen executables/service files.
- Backlight: `ae94000.dsi.0`, maximum 1023, sampled brightness 1023.
- Dmesg first logged DSI PLL lock failure, then bound DSI, initialized MSM DRM
  1.13.0, and registered `msmdrmfb` on fb0.
- The target rebooted directly before `switch_root` or persistent-state mount.
- Fresh V11 `ef544ace-25a3-4359-b998-6dce9d6239b6` returned with strict SSH,
  p24 read-only, battery Good at 8.559 V and 30.0 C.
- V10 is irreversibly consumed and must never retry. No phone storage write was
  introduced or exercised.

This accepts the 60 Hz kernel/DT registration baseline and status userspace
composition. It does not yet prove a physical power-button blank/unblank cycle.
