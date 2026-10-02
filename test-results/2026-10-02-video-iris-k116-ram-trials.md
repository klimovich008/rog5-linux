# Iris video, kernel k116 RAM trials E1/E2 (2026-10-02 13:34-13:51)

Bundles `main-k116-d15-261002a` (E1), `-b` (E2, aborted), `-c` (E2 retry).
Evidence: `/home/deck/.local/state/rog5-production-boot-20260923/ram-trial-main-k116-d15-261002{a-E1,b-E2,c-E2b}/`.

## E1 (defaults: OEM mode, encoder hidden, VP9 off, real EOS, autosuspend) - PASS

- Boot: `SM8350 OEM firmware mode: encoder off, VP9 off`; one node
  (`qcom-iris-decoder`); no `CPU NOC LPI handshake timed out` on the
  no-firmware power-off any more.
- H.264 300/300 IDENTICAL, HEVC 300/300 IDENTICAL, H.264 again 300/300
  IDENTICAL; GStreamer v4l2h264dec rc 0; after every session and after
  compliance: `mark: power off: handshakes done: 0` / `done: 0`,
  video_cc_mvs0(c)_clk 0, mvs0/mvs0c GDSC off.
- **v4l2-compliance decoder 48/48** (k115: 40-41/48).
- 5 min idle, then H.264 300/300 IDENTICAL; hw decode to null 2.64 s wall,
  0.48 s CPU (10 s 1080p30); 0 SEA / context faults.

## E2 (VP9, experimental_vp9=1)

- Wrapper b: `modprobe -d /run/rog5-modules -r qcom_iris` succeeded, the
  re-`modprobe ... experimental_vp9=1 markers=1` then **reset the phone**
  within seconds (journal not flushed; no log). Driver unload/reload is a
  bug to fix. (The documented `modprobe -r qcom_iris` without `-d` fails:
  modules live under /run/rog5-modules.)
- Wrapper c: option set through /etc/modprobe.d at boot instead (removed
  afterwards): `VP9 EXPERIMENTAL`. H.264 control 300/300 IDENTICAL before
  and after. VP9 (libvpx 1080p30 clip): **no more "CP mode" errors** (0
  lines; SECURE_SESSION=0 fixed that stage) but every FTB is rejected:
  firmware `vDec_FillThisBuffer: Buffer validation failed for
  pPacketbuffer=0xc7c00000!`, `session error ... event id:1003`, trace:
  FTBs on **stream 0** (w3 = 0) with alloc_len 0x302000 (H.264 FTBs go to
  stream 1, 0x2fd000); `stop/release failed: -5`. Contained: power off
  clean, no hang, 0 SEA; ffmpeg itself aborts on an assertion.
  Likely VP9 is configured without OUTPUT2/multistream (stock uses split
  mode for VP9 too) - for the next round.

Encoder not tested (wrapper d reserved for the dedicated encoder boot).
