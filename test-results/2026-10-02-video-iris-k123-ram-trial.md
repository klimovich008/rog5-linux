# Iris decoder under Chromium: k116 / k122 / k123 RAM trials (2026-10-02)

Test: `vstress` (a separate Chromium 153 instance with the V4L2 decoder enabled,
screen unlocked and kept awake): **local** = one MSE player switching
1080p/360p/720p H.264 every segment with seeks (90 rounds), then 40 rounds of
decoders opened and closed mid-stream, up to two at once; **yt** = YouTube
IFrame player (H.264 forced) loading, seeking and switching three videos.
After each run: engine runtime status and an `ffmpeg -c:v h264_v4l2m2m` decode.
Logs: `rog5-iris-k120-work/ramtrial-k122d-*/vstress`, `ramtrial-k123a-*/vstress`.

| Kernel | local ABR phase | local open/close phase | after | yt |
|---|---|---|---|---|
| k116 (installed) | OK | wedge: `stop/release failed: -5`, sessions fail to open, END unacknowledged, `failed to suspend` every 2 s | ffmpeg fails, engine stays on | - |
| k122 (+0210) | OK (3990 frames) | FLUSH 0x1000002 on a closing session unanswered, then two SESSION_INITs time out; ABORT x3, fatal containment | engine off, decoder unavailable until reboot | - |
| k123 (+0211, kernel audit fixes, HDMI 0200-0203) | OK | OK, no Iris messages | engine suspended, ffmpeg OK | OK, 18/18 steps, Iris busy 145 of 150 s, no errors |

Cause: Chromium closes its stateful decoder CAPTURE-first; the driver treated
that as a resolution change and sent FLUSH_OUTPUT while input was streaming,
which this firmware never answers. GStreamer (OUTPUT-first, FLUSH_ALL)
survived 30 sequential, 2x25 and 3x15 concurrent mid-stream closes on k116.
0211 sends FLUSH_ALL for an ordinary streamoff, like venus.

k123 smoke (RAM boot): battery, Wi-Fi, Bluetooth, sensors, speaker protection
on both amplifiers, display, USB gadget, GPU watchdog, no failed units; one
s2idle cycle (woke after 3 s on USB) with Bluetooth, Wi-Fi and the decoder OK
after resume.

## VP9 (k124, k125; 2026-10-03)

Options `experimental_vp9=1 vp9_dpb_extra=1` (modprobe.d, RAM boots only).

| Kernel | ffmpeg 1080p VP9, 300 frames | Chromium local VP9 stress | YouTube VP9 |
|---|---|---|---|
| k123 | 0 frames: BAD_POINTER (0x1003) on every display buffer | - | - |
| k124 (+0212 stock-sized display buffers, per-buffer extradata) | 300/300 bit-exact | - | ~22 s, then firmware Err_Fatal vpx_decoder.c:1132 at a resolution change ("Invalid Internal Scratch address received in ReleaseBuffers") |
| k125 (+0213 release VP9 scratch before restart) | 300/300 bit-exact | 90 switches + 40 open/close rounds, no errors | 150 s, 360p-1080p, no errors |

Open: a VP9 rendition switch stalls ~1 s on hardware (1017 presented frames vs
3921 with software VP9 on the same switch-every-2-s page); steady playback is
~27-30 fps. VP9 stays off by default until that is decided.
