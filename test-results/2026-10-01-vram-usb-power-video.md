# GNOME desktop-mode graphics memory, USB-C power via the hub, CPU video (2026-10-01 21:40-22:05)

Bundle `main-k113-d13-261001a`, GNOME desktop mode on the MSI MPG 491C at
1920x1080@120 (gdctl), phone panel off.

## Graphics memory (shared RAM; no dedicated VRAM)

`rog5-mem-report snapshot` (gem/clients debugfs only):

| | MiB |
|---|---:|
| GPU (msm 3d00000) GEM total | 292 (resident 288) |
| of it gnome-shell | 220 (45 shared) |
| Resources / Xwayland / mutter-x11-frames | 30 / 12 / 12 |
| display controller (msm-kms) GEM, all held by gnome-shell | 147.5 |

msm-kms buffers: 4 x 8.0 MiB (1920x1080 XRGB8888, the swapchain), 2 x 28.1
MiB (5120x1440, an earlier mode), 2 x 10.2 MiB (1080x2448, the panel that is
off), 4 x 4.8 MiB (512x2448 x 4 B), 2 x 1 MiB (cursor), 1.9 MiB. About
95 MiB do not match the current output setup; mutter keeps them. Verdict:
~440 MiB in total is normal for GNOME on a large monitor; the leftovers are
not worth a fix while 11 GiB are available.

## USB-C power through the monitor hub

- `qcom-battmgr-usb`: 8.83-8.97 V, 0.30 A (idle) to 0.95 A (GNOME), so
  2.7-8.4 W; `current_max` 2.0 A, `input_current_limit` 1.4 A (~12.5 W,
  read-only, set by the ADSP). Battery 89 % above the 80 % limit: bypass,
  battery current 0.
- The hub's source PDOs (2026-09-30): 5 V/3 A, 9 V/2.45 A, 15 V/2.87 A,
  20 V/2.75 A, no PPS; the phone sinks 5 V and 9 V fixed or PPS. The "90 W"
  is the hub's 20 V pass-through rating; this phone gets at most ~22 W from
  it, and the ADSP takes 12.5 W today. Gaming while docked can need more.
- Incident: a multi-command UCSI `GET_PDOS` probe through
  `/sys/kernel/debug/usb/ucsi/pmic_glink.ucsi.0/command` left the PPM
  answering no command (`echo 0x10012 > command`: ETIMEDOUT, still after
  60 s; no task blocked in the kernel). PD, charging, DP and the hub USB
  kept working; USB role changes on the next re-plug may not. Recovery: a
  reboot. Do not send GET_PDOS through debugfs again; the connector status
  (0x10012) alone was safe on 2026-09-30.

## Video

No `/dev/video*`: the kernel has `CONFIG_VIDEO_QCOM_IRIS=m` and
`CONFIG_VIDEO_QCOM_VENUS=m`, `videocc-sm8350`, but no SM8350 video-codec DT
node and no SM8350 match in either driver. CPU only (ffmpeg, 10 s
testsrc2 1080p30 clips, Nice 5, GNOME running):

| codec | decode | encode |
|---|---|---|
| H.264 | 9.76x realtime | libx264 veryfast 57 fps, medium 32 fps |
| HEVC | 7.65x | libx265 ultrafast 31 fps |
| VP9 | 8.43x | libvpx-vp9 realtime cpu-used 8: 57 fps |
| AV1 | libdav1d present (no AV1 encoder to make a sample) | none |

ffmpeg hwaccels listed: vdpau vaapi drm opencl vulkan amf (none usable
here; Turnip has no Vulkan Video).
