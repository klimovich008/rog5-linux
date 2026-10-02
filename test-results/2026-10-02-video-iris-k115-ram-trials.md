# Iris video, kernel k115 RAM trials A-D (2026-10-02 01:12-02:01)

Bundles `main-k115-d15-261002a`..`d` (same kernel/DTB/kit; the RAM-trial
launcher allows one boot per wrapper, so each boot got its own wrapper).
Firmware `vpu20_4v.mbn` installed with `--runtime` each boot; one H.264
1080p30 10 s clip (300 frames) compared with a software framemd5.
Evidence: `/home/deck/.local/state/rog5-production-boot-20260923/ram-trial-main-k115-d15-261002{a-A,b-B,c-C,d-D}/` (phone-logs).

| Boot | eos_buffer | interframe_pc | runtime PM | Result |
|---|---|---|---|---|
| A | N (0xdeadb000) | Y | pinned on | decode 298/300, then **sys error deadbead**: SFR `Exception: TID = Unknown IP = 0x37574 FA = 0x0 cause = 0x6`; trace: last packet before the fatal is the EOS ETB (0x211004, flags 1, len 0, addr 0xdeadb000), 259 us earlier. Containment OK: no reload, core shut down, no hang. |
| B | **Y (real 4 KiB EOS buffer)** | Y | pinned on | decode **300/300 identical**, second decode **300/300 identical**; the live kmsg capture (`kmsg.log`, longer than the journal) then shows HEVC (167.5 s), VP9 (172.2 s, same CP-mode session error as D), GStreamer H.264 (176.1 s) and the speed test, and ends at the **`B encode h264` marker (181.5 s): hard hang at encoder start**, like D; reset by the 900 s trial watchdog. *Corrected 2026-10-02: first reported as an idle hang from the journal, which ends at 154 s.* |
| C | Y | **N** | pinned on | first decode hung (0 frames, killed after 60 s); firmware answers nothing afterwards (`session open failed`, `no end acknowledgement (-110) and the firmware is not shut down`); every later open fails REQBUFS -EINVAL; phone stayed up 8 min (10 heartbeats, core clock on). |
| D | Y | Y | **auto** (default) | H.264 **300/300 identical**; 5 min idle: core powered down, no hang; HEVC **300/300 identical**; VP9: every packet -EIO, `session error ... event id:1001` with SFR "Init SFR msg, NOT an error"; GStreamer v4l2h264dec (byte-stream/au caps) rc 0; hw decode to null 2.25 s wall / 0.44 s CPU vs sw 1 thread 1.41 s / 1.5 s; **H.264 encode (NV12 input): hard hang at session start** (journal ends at the encode marker, hypervisor/trial watchdog reset ~2 min later; the live kmsg has one more line, a controller power-off `CPU NOC LPI handshake timed out` at 385.500 s, 140 ms after the encode marker at 385.361 s). |

Other: `CPU NOC LPI handshake timed out (0x0)` on every power-off (also when
the core never started) with the clocks and GDSCs off afterwards.
v4l2-compliance (boot C, after the stuck session, so the buffer tests are
not meaningful): dec 40/48, enc 41/48; failures: missing bus_info prefix,
no colorspace set on formats, have_source_change, reqbufs/expbuf.

Conclusions: this OEM firmware needs a real EOS buffer (eos_buffer=1
should be the SM8350 default); disabling interframe power collapse stops
the firmware (C; the deep dive points at a firmware/GDSC ownership
mismatch: MVS0 stays under hardware control); H.264/HEVC decode work
bit-exactly; VP9 decode and encode do not work yet. Both hard hangs (B and
D) happened at encoder start, with runtime PM pinned (B) and automatic
(D), so the encoder must stay disabled until understood. Pinned runtime PM
is not shown unsafe: B decoded H.264 twice, HEVC, VP9 (error) and
GStreamer with it pinned before the encoder hang. Automatic runtime PM
stays the default (D: 5 min idle with the core collapsed, no hang).

Correction (2026-10-02): the first version of this file said B hung while
idle, from the journal ending at 154 s; the live kmsg capture shows the
boot went on to the encoder test (GPT-6.1-Sol deep dive,
`docs/reviews/2026-10-02-gpt-6.1-sol-video-k115-deep-dive-idle-pm.md`).
The k116 guard that refused opens with runtime PM pinned was dropped
before k116 was built.
