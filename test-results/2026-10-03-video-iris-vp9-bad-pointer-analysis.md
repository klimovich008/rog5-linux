# k123 VP9: the rejected pointers belong to OUTPUT2

**The log identifies CAPTURE/OUTPUT2 pixel pointers, beginning at `0xbdc00000`,
as the rejected buffers. The leading explanation is an OUTPUT2 NV12 contract
mismatch, not missing DPB extradata or a VP9 input frame-size table.**
The exact proprietary validation predicate remains unproven; this is a ranked diagnosis and a concrete stock-based correction, not a hardware-qualified fix.

Evidence: [dmesg](/home/deck/.local/state/rog5-iris-k120-work/vp9-g2-k123/vp9-g2-002402/dmesg.log:1303),
[FFmpeg](/home/deck/.local/state/rog5-iris-k120-work/vp9-g2-k123/vp9-g2-002402/ffmpeg.log:1).
Session `0x12d6a000`: 32 stream-0 DPB FTBs, 20 stream-1 CAPTURE FTBs,
20 BAD_POINTER events. Firmware explicitly names `0xbdc00000`, `0xbd800000`,
etc. ([line 1555](/home/deck/.local/state/rog5-iris-k120-work/vp9-g2-k123/vp9-g2-002402/dmesg.log:1555)); these match stream-1 packets, not DPBs `0xb8c00000` onward.
First BAD_POINTER is 00:24:03.048524; EBD `0x1001005` is logged later,
00:24:04.634677. That EBD error is undefined in the supplied stock headers;
do not equate it with `0x1005` INVALID_STREAM_ID or `0x1001001` OUTPUT_PENDING.
The event packet is EVENT_NOTIFY `0x21001`, event ID **2**, error data **0x1003**.

Setup below is in captured order; types 1/2/3 are INPUT/OUTPUT/OUTPUT2.
Property packets have header `size,0x11001,sid,1,property,payload` and stock-compatible lengths.

| Log line(s) | Packet/property and decoded payload | Exact stock comparison |
| --- | --- | --- |
| 1303 | INIT `0x10007`: domain 2, codec `0x4000` | Decoder, VP9; matches. |
| 1306 | `0x1011` SECURE_SESSION = 0 | Matches explicit nonsecure initialization. |
| 1309 | `0x2002` VIDEOCORES_USAGE = 1 | Core 1; stock decides core before loading. |
| 1312,1315 | `0x1003` FORMAT: type 2 `0x8002`; type 3 `2` | UBWC DPB / linear NV12 display; stock configures display first. |
| 1318 | `0x201002` type 3, two image planes | **Mismatch:** see exact constraints below. |
| 1321–1327 | `0x201001` counts actual/min-host: 1=32/32, 2=32/32, 3=9/9 | Stock uses negotiated input count, DPB count, actual CAPTURE count. |
| 1330,1333 | `0x1003001` MULTI_STREAM: type 2 off, type 3 on | Same final state; stock enables 3 before disabling 2. |
| 1336,1339 | `0x1001` FRAME_SIZE: types 1,3 = 1920×1088 | Same property/types; actual requested dimensions depend on client. |
| 1342,1345 | `0x20100c` sizes: type 2 `0x312000`; type 3 `0x2fd000` | DPB matches; **plain stock NV12 display needs `0x480000`**. |
| 1348,1351 | `0x1015` WORK_MODE = 2; `0x1017` WORK_ROUTE = 4 | No pointer payload; consistent with four-pipe decode. |
| 1354 | SET_BUFFERS `0x11002`: type 5, `0xbf000000`, `0x8d6f00` | PERSIST_1; stock `0x8a5f00`, one buffer. Iris is larger. |
| 1357 | SET_BUFFERS: type 6, `0xbe000000`, `0xbf4000` | SCRATCH; stock same size/count. |
| 1360 | SET_BUFFERS: type 7, `0xbdf80000`, `0x63500` | SCRATCH_1; stock `0x53600`, one buffer. Iris is larger. |
| 1363,1366 | LOAD_RESOURCES `0x211001`, START `0x211002` | Stock also registers internals before load/start. |
| 1372–1402 | Repeat format/constraints/counts/multistream/sizes after discovery | Type 3 count becomes 32/32; stock would send actual 20 CAPTURE buffers. |
| 1405–1414 | RELEASE_BUFFERS types 6,7; SET_BUFFERS again | SCRATCH unchanged; SCRATCH_1 becomes `0x62f00`, still larger than stock. |
| 1417–1423 | WORK_MODE/ROUTE again; CONTINUE `0x21100d` | Stock continues after reconfiguration properties/internal buffers. |
| 1426–1467 | 32 DPB FTBs: stream 0, pixel `0x312000`, extra `0xbdf7c000/0x4000` | Matches stock's shared DPB extradata pair. |
| 1513–1532 | 20 CAPTURE FTBs: stream 1, pixel `0x2fd000`, extra **0/0** | Stock supplies its display pixel size plus per-buffer 16 KiB extradata. |
| 1565 | ABORT `0x210001` | k123 failure containment, after the errors. |

The critical distinction is **plain NV12 versus NV12_128 in the ASUS header**.
`msm_comm_convert_color_fmt(V4L2_PIX_FMT_NV12)` returns `COLOR_FMT_NV12`, not NV12_128.
Stock [layout functions](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/include/uapi/vidc/media/msm_media_info.h:813)
and [conversion](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/msm_vidc_common.c:3757) give:

| OUTPUT2 NV12 at 1920×1088 | k123 wire/allocation | Stock plain NV12 |
| --- | --- | --- |
| Y constraints: stride multiple / max / height multiple / address alignment | 128 / 8192 / 32 / 512 | 512 / 8192 / 512 / 512 |
| UV constraints: same fields | 128 / 8192 / 16 / 256 | 512 / 8192 / 256 / 256 |
| Actual stride / Y scanlines / UV scanlines | 1920 / 1088 / 544 | 2048 / 1536 / 768 |
| UV offset / pixel allocation | `0x1fe000` / `0x2fd000` | `0x300000` / `0x480000` |
| Extradata | no CAPTURE backing pointer | separate 16 KiB per CAPTURE buffer |

Stock derives the complete constraints from VENUS functions, not just the luma address alignment ([constraints](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/msm_vidc_common.c:7412)). Patch 0170 fixed only that alignment field.
This makes the **OUTPUT2 pixel pointer/alloc_len pair** the strongest suspect;
the null OUTPUT2 extradata pointer is the next distinct stock mismatch.
Iris explicitly requests smaller constraints, so source comparison alone cannot
prove whether VP9 firmware ignores them or rejects a different part of the FTB.

Stock Iris2 calculates only SCRATCH/SCRATCH_1/PERSIST_1 for VP9, each count 1;
SCRATCH_2 and PERSIST remain zero. PERSIST_1 holds probabilities, fixed COMV,
superframe-header space, UDC headers and tile offsets. No additional host buffer
for a VP9 frame-size table is missing. Stock registration order is SCRATCH →
SCRATCH_1 → PERSIST_1; capture uses PERSIST_1 first, with no reported rejection.
Stock dynamic output mode skips DPB SET_BUFFERS; adding them is not justified
([allocation](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/msm_vidc_common.c:3832), [packetizer](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/hfi_packetization.c:374)).

Other absent stock initialization: PROFILE_LEVEL_CURRENT (P0 maps to 1),
VDEC_OUTPUT_ORDER (display), VDEC_THUMBNAIL_MODE (0), CONFIG_REALTIME,
VDEC_CONCEAL_COLOR, crop/interlace/concealed-MB metadata, VPX_COLORSPACE and
HDR10_HIST extradata enables ([sequence](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/msm_vdec.c:1487)). None is individually proven to cause BAD_POINTER.
No BUFFER_ALLOC_MODE packet is sent by stock's decoder setup either.

Decoder ETB is the same 60-byte structure in stock and Iris, with input extra
address/size zero. Retained ETB: `packet_buffer=0xdc000000`, offset 0,
alloc_len `0x10e0000`, filled_len `0x5a3d`; these are valid stock-sized fields.
Stock decoder superframe control is fixed at zero; its raw-frame batching path
is not VP9 superframe-index preparation. Forward compressed frames/superframes,
including their native index; no host-added size table or input metadata.
The log lacks compressed bytes, so their contents cannot be verified here.
Stock nonsecure IOVAs use `[0x25800000,0xe0000000)` for all these buffer types;
every captured buffer is inside it and highly aligned. Internal DMA alignment
is 256 bytes; stock allocation/mapping rounds to 4 KiB. No VP9-specific low-IOVA
placement or stronger base-pointer alignment appears in stock.

**Proposed minimal first correction:** restore stock OUTPUT2 NV12 constraints,
pixel sizing and actual stride/scanline reporting together, scoped to OEM VP9.
At this resolution send pixel `alloc_len=0x480000`, stride 2048 and UV offset
`0x300000`; keep visible/coded dimensions separate from the padded layout.
If that still rejects the same CAPTURE pointers, supply independent 16 KiB
CAPTURE extradata address/size pairs with buffer-owned lifetimes, as stock does.
Do not reuse the shared DPB metadata as per-CAPTURE metadata.
No kernel patch remains: changing size alone or metadata alone is insufficiently
supported, and the full layout correction needs consistent V4L2 negotiation.
No kernel compilation, full build, boot, install or commit. Suggested implementation commit message: `media: iris: match OEM VP9 OUTPUT2 NV12 buffer requirements`.
