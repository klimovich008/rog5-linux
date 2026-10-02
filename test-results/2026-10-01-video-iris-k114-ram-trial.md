# Hardware video (Iris) RAM trial of main-k114-d15-261001a (2026-10-01 23:13-23:41)

RAM-only trial (user-approved) of `main-k114-d15-261001a` (k114 + d15), run
by the coordinator. Firmware installed for that boot only with
`install-rog5-video-firmware --runtime`. Evidence:
`~/.local/state/rog5-production-boot-20260923/ram-trial-main-k114-d15-261001a-2/`
(`phone-logs/dmesg-trial-boot.txt`, `boot.json`, `health.json`, `kmsg.log`,
`stages.log`). Analysis: [GPT-6.1-Sol trial debug review](../docs/reviews/2026-10-01-gpt-6.1-sol-iris-trial-debug.md).
After the hard hang the phone came back on the installed chain (main-k113-d13).

## What worked

- Boot: `video-modules loaded videocc_sm8350 qcom_iris` (dmesg 55.5 s); the
  opens before the firmware was installed failed cleanly at
  `request_firmware` (-2) with `core init failed`.
- No patch-0156 warning: the hypervisor took the SID 0x2100 route.
- TrustZone accepted the OEM image: `qcom/sm8350/vpu20_4v.mbn authenticated
  and out of reset (PAS 9)` (630.8 s).
- Formats as expected; `v4l2-compliance` decoder 41/48, encoder 42/48 (the
  failing tests were not captured).
- `ffmpeg -c:v h264_v4l2m2m` decoded 300/300 frames of the 1080p test clip,
  framemd5 identical to the software decoder.

## What failed

- The end of every decode session raised a firmware fatal error:
  `sys error (type: 1, session id:ff, data1:1, data2:deadbead)` (6 times,
  first at 726.3 s), that is HFI_EVENT_SYS_ERROR, HFI_ERR_SYS_FATAL and a
  firmware-private marker. No SFR text was printed (the gen1 driver never
  reads it).
- The driver then reloaded the firmware at once (`authenticated and out of
  reset` 0.1 s after each fatal error) while the instances kept their old
  session ids: `session error for command: 0, event id:1004` (0x1004 =
  HFI_ERR_SESSION_INVALID_SESSION_ID, "command 0" = no offending command
  reported) and `no valid instance (pkt:20007)` (a SESSION_END answer after
  removal).
- Later sessions hung in poll: ffmpeg got 299/300 frames and then hung;
  GStreamer `v4l2h264dec` hung twice; `v4l2h265dec` worked once.
- `WARNING ... vb2_buffer_done` from `iris_hfi_gen1_session_stop` ->
  `iris_helper_buffers_done` on the close of a killed process (1542.4 s).
- About 4 minutes after the last fatal error (1609 s) the SoC hung hard and
  the watchdog reset it.
- Encoding failed with EINVAL only because the input was yuv420p; the Iris
  encoder takes NV12 (and QC08C).

## Conclusions and next step

Firmware choice, DT and platform values held (authentication, decode
correctness). The driver's handling of the firmware's fatal error made
things worse: immediate reload with stale sessions, waiters never woken,
buffers completed twice, and teardown paths that remove power before
quiescing the interrupt. Kernel k115 adds patches 0157-0161 (diagnostics
with SFR and HFI trace, instance lifetime, fatal containment without
reload, buffer/answer fixes, switchable EOS-buffer and power-collapse
experiments); the next trial decodes once per boot and stops at the first
fatal error ([docs/hardware/video.md](../docs/hardware/video.md), "k115 trial").

