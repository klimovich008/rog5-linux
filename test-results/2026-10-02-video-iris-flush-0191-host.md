# Iris gen1 CAPTURE streamoff: patch 0191

The driver bug is **using the DRC output-only flush for ordinary CAPTURE
streamoff while input is active**. This selection is already in the pristine
7.2.7 Iris driver, not introduced by patches 0154–0190. Patch 0191 follows
Venus: ordinary streamoff uses FLUSH_ALL; CAPTURE reconfiguration during DRC
keeps FLUSH_OUTPUT. Closing also selects ALL if DRC is pending.

The firmware-internal reason for the stall is not observable here. This is a
source-proven command-selection fix and a strongly supported trigger diagnosis,
not a hardware-qualified cure.

| Operation (split decoder) | Stock msm_vidc | Upstream Venus / 7.2.7 |
| --- | --- | --- |
| CAPTURE streamoff, OUTPUT still streaming | No HFI flush or STOP | DECODING: FLUSH_ALL, wait; DRC: FLUSH_OUTPUT, wait; DRAIN/SEEK: no new flush |
| Last queue off / close | STOP → wait → RELEASE_RESOURCES → wait; close then END → wait. No automatic pre-STOP flush | Queue release stops CAPTURE first: normally ALL → wait, then OUTPUT ALL → wait; final buffer cleanup does STOP → unload → unregister/free internal buffers → END, with command waits |
| Separate vendor flush ioctl | CAPTURE-only flags → HAL_FLUSH_OUTPUT → HFI_FLUSH_OUTPUT; both flags → HFI_FLUSH_ALL | Stateful streamoff chooses by decoder state |

References: stock [streamoff and close](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/msm_vidc.c:1128),
[close](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/msm_vidc.c:1803),
[flush ioctl](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/msm_vidc_common.c:5574),
[transition waits](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/msm_vidc_common.c:4137),
and [Venus streamoff/release](/home/deck/.local/state/rog5-kernel-7.2.7-build-r122/source/drivers/media/platform/qcom/venus/vdec.c:1232).

**OUTPUT2 is not the fix.** Stock's packetizer sends OUTPUT even for secondary
display mode; its flush-done parser does not accept OUTPUT2. Venus likewise
uses OUTPUT for DRC with split DPBs. The buffer port ID and flush selector
are distinct protocol choices.

Neither reference first drains all pending ETB/FTB acknowledgements before
issuing flush: the flush is the buffer-return boundary. Stock marks the affected
ports flushing, rejects their QBUFs, cancels batch work, returns deferred/RBR
buffers locally, and submits flush after earlier HFI packets. Its flush ioctl
is asynchronous: FLUSH_DONE is a V4L2 event, not a synchronous command wait.
Returned split DPBs are validated and requeued at FLUSH_DONE outside DRC.
Venus streamoff blocks for FLUSH_DONE before its following transition.
Iris already waits for all counted flush replies before streamoff returns;
0191 preserves that wait, and STOP/RELEASE/END ordering. No ETB/FTB is transmitted
after the failing flush in the retained k122 ring.

**A new session's INIT while another session flushes is allowed by stock.**
[session_flush](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/hfi_common.c:2416)
and [session_init](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/hfi_common.c:1956)
hold the device lock only for packet submission; there is no core-wide
flush-pending barrier. Flush flags and lifecycle waits are per instance.
Stock does not enforce a universal FLUSH_DONE-before-any-command rule.

The supplied [k122 ring](/home/deck/.local/state/rog5-iris-k120-work/ramtrial-k122d-223514/vstress/k122-local/dmesg.log:1627)
shows OUTPUT flush, one final display FBD 1.865 ms later, INITs at +23.826 and
+44.158 ms, then ABORT at +1031.633 ms. None receives a flush/init/abort reply;
SFR is clean. Successful DRC/seek stress and the OUTPUT-first GStreamer runs
support changing ordinary teardown, retaining the working DRC flush.
The k116 `stop/release failed: -5` cannot identify its first failed command.

[0191](../patches/linux-7.2.7/0191-media-iris-flush-all-ports-on-normal-gen1-capture-streamoff.patch)
changes one condition in one C file (+6/-4), appended to `series.production`.
No knobs, frameworks, fixtures or harnesses. Trial source r122 is untouched.

Validation, first attempt both checks: full production series **PREPARED** on
pinned v7.2.7 `f42acb3678424d1e08f6ed27c0d8ba8a125e14d6` (145.0 s);
all 30 Iris compilation units plus `qcom-iris.o` **PASS** with
`ARCH=arm64 LLVM=1 W=1 -j4` (54 s), zero warnings/errors, AArch64 ELF.
Patch creation to compiled result: 216 s; no check failures or cache reuse.
Only `iris_hfi_gen1_command.c` differs from r122's Iris directory.
[Preparation receipt](/home/deck/.local/state/rog5-iris-flush-0191-prepare/result.json),
[compile log](/home/deck/.local/state/rog5-iris-flush-0191-compile.log).
No full kernel build, boot, install or commit. Fresh-boot Chromium close/reopen
qualification remains pending; expect ALL → FLUSH_DONE → STOP → STOP_DONE →
RELEASE → RELEASE_DONE → END → END_DONE for the affected close order.

Commit message:

```text
media: iris: flush all ports on normal gen1 capture streamoff

Reserve FLUSH_OUTPUT for paused dynamic resolution changes. Use FLUSH_ALL
for ordinary CAPTURE streamoff and close, matching Venus and avoiding the
SM8350 OEM firmware stall observed with pending compressed input.
Keep the existing flush completion wait and teardown ordering.
```
