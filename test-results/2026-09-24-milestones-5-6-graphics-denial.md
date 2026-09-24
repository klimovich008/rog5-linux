# Milestones 5–6: graphics stack and a Denial touch session — September 24

Default kernel `production-7.2.7-r12` (r10 plus the persistent root overlay,
`PERSISTENT_ROOT_OVERLAY=1`). The September overlay image
(`userdata:/rog5/root/root-overlay-v1.ext4`) was inspected read-only first:
same SSH host key, a September `pacman -Syu` over the unchanged lower root,
one harmless enabled unit (rog5-healthd on :8787).

## Persistent root

- t11: both the overlay image and sda23 replayed their journal once; the
  booted P2 attestor rejected the userdata replay (the init accepts it). Fixed
  (`10a93255`); r12 passed P2, then two committed default boots.
- Packages now survive reboots; `pacman -Syu` plus the installs below ran into
  the overlay (rc 0). No kernel package is installed through pacman.
- The previous boot's kernel log survives in the journal on the overlay
  (`journalctl -b -1 -k`), which ramoops cannot give on this firmware.

## Milestone 5: graphics stack — PASS (with the GMU firmware change)

- Mesa 26.2.3 (`mesa`, `vulkan-freedreno`, `mesa-utils`), Weston 15, foot,
  seatd, libinput, libxkbcommon, fontconfig, glmark2, xorg-xwayland.
- EGL on GBM and surfaceless: `FD660`, OpenGL 4.6 core, OpenGL ES 3.2.
- Weston DRM backend (KMS `card1` = msm_dpu, render `renderD128`), GL renderer
  FD660, `DSI-1` 1080×2448.
- Stock GMU firmware v3.1.5: `HFI_H2F_MSG_PREPARE_SLUMBER` fails on every
  runtime suspend (66 ms autosuspend), and one GPU hang (hangcheck recover,
  offending task weston-simple-egl) hit 10 s into a 10-minute run. With the
  GPU held active: 10 minutes, 0 faults.
- linux-firmware 20260916 `a660_gmu.bin` (`8acab7b4…`, v3.1.10), loaded before
  the first GPU open: 10 minutes of weston-simple-egl plus glmark2 with runtime
  suspend on — **0 GPU faults, 0 slumber errors**. glmark2 (fullscreen
  1080×2448): build 3528 fps, refract 147, terrain 156. Shipped as
  `display-firmware-r2` in r13.
- Vulkan (turnip) loads; `VK_KHR_display` plane queries fail because KMS is a
  separate device. Wayland/Vulkan presentation is not yet tested.
- Do not unbind `3d00000.gpu` at runtime: it oopsed in msm's component
  teardown and the phone rebooted (it recovered to r12 by itself).

## Milestone 6: Denial touch session on the OLED — PASS (first session)

- Bundle `denial-bundle-r1` (Denial 85b2303e, engine d728e61e) in
  `/opt/denial`; every runtime library resolves on the phone.
- `seatd-launch -- /opt/denial/deniald --device /dev/dri/card1
  --render-device /dev/dri/renderD128 --output-config /etc/denial/outputs.conf
  --wayland --flutter-bundle /opt/denial` with `DENIA_SHELL_PROFILE=mobile`
  (`--flutter-bundle` requires `--wayland`; Xwayland is required).
- Impeller GLES on FD660, 1080×2448 at 60 Hz, KMS plane allocated by deniald,
  Xwayland ready, no GPU faults.
- The user saw the Denial mobile shell and swipes worked. At scale 1 the
  top bar was small and opening it glitched; `scale=DSI-1,2.5`
  (`device_pixel_ratio=2.5`) "looks good". The Skia renderer gave a black
  screen.
- Open: one "Could not create the embedder backing store" at startup (after
  "nested Flutter output presentation"); no session D-Bus (notification
  service), no libpulse (audio controls), not yet started at boot. The ROADMAP
  completion criteria (two apps, text entry, three starts, 60 minutes,
  screen-off/wake, recovery, update/rollback) remain.
