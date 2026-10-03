# OEM VP9 Err_Fatal: a superseded SCRATCH registration

The firmware identifies the rejected operation: `vpxDec_SessionReleaseBuffers(1131):
Invalid Internal Scratch address received in ReleaseBuffers command`, followed by
`vpx_decoder.c:1132`. This is an input-internal-buffer registration bug exposed at
source change after STOP/restart. Hardware qualification of the correction is pending.

Evidence is [Chromium dmesg](/home/deck/.local/state/rog5-iris-k120-work/ramtrial-k124a-014114/vstress/run-yt-014805/dmesg.log:1558).
Session IDs are reused after END/INIT: the earlier `0x7cf02000` at line 1132 is a
different session lifetime. The failing lifetime starts at line 1507.

| Failing lifetime: line | Operation |
| --- | --- |
| 1558–1570 | SET PERSIST_1 `d7000000`, SCRATCH `d6800000`, SCRATCH_1 `d67e0000`; LOAD, START |
| 1573–1576 | STOP, RELEASE_RESOURCES (both acknowledged in ring lines 1705/1707) |
| 1624–1633 | SET SCRATCH `d5800000`, SCRATCH_1 `d57e0000`; LOAD, START; **no preceding scratch RELEASE** |
| 1666–1672 | Source discovery: OUTPUT2 1280×736, OUTPUT size `0x16c000`, OUTPUT2 size `0x240000` |
| 1675–1681 | RELEASE SCRATCH **`d6800000`**, size `0x564000`; SYS_ERROR `1/deadbead`; SFR assertion |
| 1759 | Firmware explicitly reports the invalid SCRATCH address |

The last valid SET was `d5800000`, but Iris releases the older `d6800000` first.
`iris_vdec_streamon_input()` destroys only dequeued internals, then unconditionally
creates another set. SCRATCH registrations stay `BUF_ATTR_QUEUED` across STOP;
therefore the old set survives, the new SET supersedes it in VP9 firmware, and the
next `iris_alloc_and_queue_input_int_bufs()` encounters the obsolete list entry.
The earlier successful RELEASE at line 1239 belongs to the preceding session
lifetime; repeated session IDs alone do not prove a double RELEASE.

Stock behavior, from ASUS msm_vidc:

- [Scratch](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/msm_vidc_common.c:5218):
  `check_for_reuse` tests size ≥ requirement and matching count per type.
  **Every scratch registration is RELEASED and acknowledged**, even if sufficient.
  Sufficient allocations stay mapped; insufficient ones are freed. Then
  `reuse_internal_buffers()` SETs retained addresses, or new allocations are SET.
  Reuse means allocation reuse, not skipping the firmware RELEASE.
- [PERSIST_1](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/msm_vidc_common.c:4002):
  resolution-independent; kept registered without RELEASE or another SET on DRC.
  VP9 uses one each of SCRATCH, SCRATCH_1 and PERSIST_1; SCRATCH_2/PERSIST are zero.
- [VP9 DPBs](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/msm_vidc_common.c:5098):
  `force_release=false`; free driver-owned old DPBs, mark firmware-owned ones for
  removal when returned, allocate the new set. Dynamic mode sends no DPB
  SET/RELEASE packets. CONTINUE precedes new stream-0 FTBs.
- [Order](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/msm_vidc.c:944):
  DRC output flush/return boundary → format/count/size/work properties and new
  requirements → scratch RELEASE/wait → scratch SET (reuse or replace) → retain
  persist → prepare DPBs → CONTINUE → DPB FTBs. Restart after both queues stop uses
  STOP/wait → RELEASE_RESOURCES/wait before the next buffer setup/LOAD/START.
  Stock CAPTURE-only streamoff does not itself STOP or flush; the client uses its
  separate flush ioctl. There is no universal pre-RELEASE flush in these helpers.

Iris updates format/count/size before scratch RELEASE/SET and CONTINUE, and
retains PERSIST_1; its work mode/route updates follow scratch SET, unlike stock. It retains queued old DPBs and replaces dequeued ones on capture
streamon; stock additionally marks retained VP9 DPBs for removal. The failing
lifetime has sent no DPB or OUTPUT2 FTB before the assertion, so DPBs cannot explain
this rejected SCRATCH address. The passing FFmpeg run also RELEASEs SCRATCH on
first source discovery without a preceding flush; adding a flush is not this fix.

SCRATCH_1, four pipes and split output (stock `calculate_vp9d_scratch1_size`):

| Coded size | Stock requirement | Stock SET size (4 KiB rounded) | Iris SET size |
| --- | --- | --- | --- |
| 320×240 | `0x13600` | `0x14000` | `0x14000` |
| 640×360 | `0x1da00` | `0x1e000` | `0x1f400` |
| 1280×720 | `0x37d00` | `0x38000` | `0x3f500` |
| 1280×736 | `0x38900` | `0x39000` | `0x40100` |
| 1920×1088 | `0x53600` | `0x54000` | `0x63500` |

Iris adds a QP term and uses 8-line rather than stock 16-line height alignment in
some line buffers; no captured VP9 SCRATCH_1 is undersized. Stock rounds smem
allocations to 4 KiB (`msm_smem.c:357`) and SETs `handle->size`. `0x1291f00` is from session
`0x507f4000`, initialized with codec `2` (**H.264**, line 520), not VP9 (`0x4000`).
The failed release is SCRATCH/type 6, not SCRATCH_1/type 7; no sizing edit is needed.

[0213](../patches/linux-7.2.7/0213-media-iris-release-OEM-VP9-scratch-registrations-before-restart.patch)
adds nine C lines: use the existing synchronous release/wait/allocate/queue helper
on OEM VP9 input streamon. Initial allocation and DRC use that same path; restart
now unregisters the old set before registering its replacement. H.264/HEVC,
PERSIST_1, DPBs, sizing and property/CONTINUE order remain unchanged. Allocation
reuse is an optional optimization, not required to fix the stale registration.

Validation, first attempt: full production series through 0213 **PREPARED** on
v7.2.7 `f42acb3678424d1e08f6ed27c0d8ba8a125e14d6`; all 30 Iris units and
`qcom-iris.o` **PASS**, `ARCH=arm64 LLVM=1 W=1 -j4`, zero warnings/errors,
AArch64 ELF. [Prepare receipt](/home/deck/.local/state/rog5-iris-vp9-drc-0213-prepare/result.json),
[compile log](/home/deck/.local/state/rog5-iris-vp9-drc-0213/compile.log),
[validation](/home/deck/.local/state/rog5-iris-vp9-drc-0213/validation.json).
Patch creation to compiled result: 248 s; fresh Iris compilation: 24 s, no cache.
No full kernel build, boot, install or commit. User changes remain untouched.
Commit message: `media: iris: release OEM VP9 scratch registrations before restart`.
