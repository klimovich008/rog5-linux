# Iris video, kernel k115 RAM trials A-D (2026-10-02 01:12-02:01)

Bundles `main-k115-d15-261002a`..`d` (same kernel/DTB/kit; the RAM-trial
launcher allows one boot per wrapper, so each boot got its own wrapper).
Firmware `vpu20_4v.mbn` installed with `--runtime` each boot; one H.264
1080p30 10 s clip (300 frames) compared with a software framemd5.
Evidence: `/home/deck/.local/state/rog5-production-boot-20260923/ram-trial-main-k115-d15-261002{a-A,b-B,c-C,d-D}/` (phone-logs).

| Boot | eos_buffer | interframe_pc | runtime PM | Result |
|---|---|---|---|---|
| A | N (0xdeadb000) | Y | pinned on | decode 298/300, then **sys error deadbead**: SFR `Exception: TID = Unknown IP = 0x37574 FA = 0x0 cause = 0x6`; trace: last packet before the fatal is the EOS ETB (0x211004, flags 1, len 0, addr 0xdeadb000), 259 us earlier. Containment OK: no reload, core shut down, no hang. |
| B | **Y (real 4 KiB EOS buffer)** | Y | pinned on | decode **300/300 identical**, second decode **300/300 identical**; then the phone **hung while idle** (journal ends ~11 s after the last session, 154 s), reset by the 900 s trial watchdog. |
| C | Y | **N** | pinned on | first decode hung (0 frames, killed after 60 s); firmware answers nothing afterwards (`session open failed`, `no end acknowledgement (-110) and the firmware is not shut down`); every later open fails REQBUFS -EINVAL; phone stayed up 8 min (10 heartbeats, core clock on). |
| D | Y | Y | **auto** (default) | H.264 **300/300 identical**; 5 min idle: core powered down, no hang; HEVC **300/300 identical**; VP9: every packet -EIO, `session error ... event id:1001` with SFR "Init SFR msg, NOT an error"; GStreamer v4l2h264dec (byte-stream/au caps) rc 0; hw decode to null 2.25 s wall / 0.44 s CPU vs sw 1 thread 1.41 s / 1.5 s; **H.264 encode (NV12 input): hard hang at session start** (journal ends at the encode marker, hypervisor/trial watchdog reset ~2 min later). |

Other: `CPU NOC LPI handshake timed out (0x0)` on every power-off (also when
the core never started) with the clocks and GDSCs off afterwards.
v4l2-compliance (boot C, after the stuck session, so the buffer tests are
not meaningful): dec 40/48, enc 41/48; failures: missing bus_info prefix,
no colorspace set on formats, have_source_change, reqbufs/expbuf.

Conclusions so far: this OEM firmware needs a real EOS buffer
(eos_buffer=1 should be the SM8350 default); host runtime PM must stay
automatic (pinning it on while firmware power collapse is enabled hangs the
SoC); disabling interframe power collapse stops the firmware; H.264/HEVC
decode work bit-exactly; VP9 decode and encode do not work yet, and the
encoder can hang the SoC, so it must stay disabled until understood.
