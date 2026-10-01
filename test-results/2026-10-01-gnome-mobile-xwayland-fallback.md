# GNOME Mobile: Xwayland crash, watchdog fallback, stride fix (0005)

Date: 2026-10-01 19:59-20:15, bundle `main-k113-d13-261001a`.

- 19:59:39 the user started Steam in the GNOME Mobile session. mutter-mobile
  logged `DMABuf stride of 8704 corrected to 8576`, Xwayland failed
  (`failed to import supplied dmabufs: EGL failed to allocate resources`,
  protocol error), mutter: `X Wayland crashed; attempting to recover`.
- The shell then did not answer on its bus for 45 s: at 20:00:35 the
  watchdog fell back (`no answering shell for 45 s`), Phosh came up locked
  at 20:00:47 and the selector went back to phosh (next boot too). The
  watchdog worked as designed.
- Cause: the mobile-shell fork's `meta_wayland_dma_buf` "create" overwrites
  plane 0's stride with ALIGN(width * 4, 128) for every client buffer. Stock
  mutter does not: earlier boots with desktop-mode GNOME and Steam logged no
  such line and no Xwayland crash.
- Fix: `packages/gnome-mobile/mutter-mobile/0005-…` drops the override
  (mutter-mobile 50.5-1.1).
- Meanwhile the stock mutter/gnome-shell were restored with
  `rog5-gnome-mobile-install rollback` (gdm removed) so desktop mode works,
  and the "Phone mode" launcher override was removed again. GNOME Mobile is
  reinstalled with the fixed mutter once it is built, then the selector is
  set back to gnome-mobile.
