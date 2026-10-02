# Chromium/YouTube Iris wedge: host diagnosis and patch 0190

Worktree: `agent/video-iris-wedge`, HEAD `0f356d7434b55779bdf8e4d2832323d76072658a`.
Changes are uncommitted. No phone, boot, install, push or Git metadata writes.

**Found and fixed: failed-session teardown can send STOP after END, consume or
misroute the teardown acknowledgement, and leave an unresponsive firmware
outside fatal containment. The first YouTube rejection is not identifiable
from the supplied log.** Patch 0190 fixes those lifecycle bugs and records the
missing HFI response type/error. It is a host-checked fix awaiting reproduction,
not evidence that YouTube hardware decoding now works.

## Evidence and stock comparison

The [k116 log](/home/deck/.local/state/rog5-sol-tasks/iris-wedge-evidence/kernel-iris-k116-20261002.log:108)
first reports STOP/RELEASE `-5` at 20:32:11.683, then failed opens, END timeouts
and repeated failed power collapse. The supplied successful local clip result
is 711 frames with three resolution-change events. Neither result proves the
exact ioctl order, rejected command, live-session count or buffer ownership at
the first failure. There is no HFI error code/packet type in that first line.

Reference **Iris** below is the source through 0178 at
`~/.local/state/rog5-iris-k120-prepare-r3/source/drivers/media/platform/qcom/iris/`;
the relevant failed-streamoff, wait and close logic is also present in the
read-only running-k116 source. **Stock** is the ASUS source at
`~/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/`.

| Boundary | Stock / Venus | Iris before 0190 |
| --- | --- | --- |
| Resolution change / one port off | Stock `msm_vidc.c:1128` stops/releases only when the other port is off. Venus `vdec.c:1232` uses output flush for DRC; `:1261` flushes all for input streamoff. | `iris_hfi_gen1_command.c:458` flushes when both ports stream: CAPTURE → FLUSH_OUTPUT, OUTPUT → FLUSH_ALL. The last port off STOPs/releases if LOAD_RESOURCES remains set. Normal DRC does **not** unconditionally STOP. |
| Failed session | Stock [`msm_comm_kill_session`](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/msm_vidc_common.c:6292) sends SESSION_ABORT and waits; Venus [`vdec_session_release`](/home/deck/.local/state/rog5-iris-k120-prepare-r3/source/drivers/media/platform/qcom/venus/vdec.c:1313) aborts after release/end errors. | [`iris_kill_session`](/home/deck/.local/state/rog5-iris-k120-prepare-r3/source/drivers/media/platform/qcom/iris/iris_common.c:195) sends ordinary END, without waiting, then marks ERROR. |
| Subsequent streamoff | Stock invalid-state handling avoids a normal STOP transition and kills/aborts the session. | The decoder's non-STREAMING branch still tests LOAD_RESOURCES, including ERROR. Substate changes are ignored in ERROR (`iris_state.c:195`), so that bit can remain set. A second port's streamoff can send STOP after END and overwrite `expected_msg`. |
| END acknowledgement | A completion belongs to the command being waited for; stock uses separate command completions. | `iris_session_close` waits on the same consumable completion. An END arriving before a later STOP may satisfy the STOP wait, or an END arriving afterwards may be rejected by the expected-message filter. Close can then wait for an acknowledgement already consumed. |
| Unanswered teardown | Stock [`msm_comm_session_abort`](/home/deck/Projects/rog-phone-linux-migration/kernel-src/msm-5.4/techpack/video/msm/vidc/msm_vidc_common.c:2895) generates a system error on abort timeout. | Close timeout only marks the instance ERROR. `core->fatal` stays false, so PM keeps asking an unresponsive firmware for normal power collapse. |

The upstream [Venus release implementation](https://github.com/torvalds/linux/blob/master/drivers/media/platform/qcom/venus/vdec.c)
corroborates the abort-on-release-error policy; the exact local version above
is the reference used for the comparison.

An additional qualification matters: [`iris_wait_for_session_response`](/home/deck/.local/state/rog5-iris-k120-prepare-r3/source/drivers/media/platform/qcom/iris/iris_utils.c:134)
returns `-EIO` whenever the instance is ERROR, including an error from an earlier
buffer/event response. Thus `stop/release failed: -5` alone does not establish
that the STOP response carried an error. It can be a secondary failure. The
STOP-after-END path is proven reachable in the code, not proven to have appeared
on the wire in this particular log.

Limits are a possible consequence of leaked firmware sessions, not an established
first trigger. SM8350 advertises 16 sessions and 8K60 aggregate macroblock load
(`iris_platform_vpu2.c:145`); stock has a 16-instance default
(`msm_vidc_internal.h:41`) and checks aggregate load before LOAD_RESOURCES
(`msm_vidc_common.c:3509`). One 1920×1088 60-fps stream uses 489600 macroblocks/s versus
7776000 macroblocks/s in the Iris table. Stock Lahaina's `qcom,max-hw-load`
is 7833600 (`msm_vidc_platform.c:1184`), plus its per-frame margin in the load
check. Iris is slightly more restrictive, not admitting radically more load
than stock. This does not exclude firmware-session leaks or undocumented
firmware limits. Once Linux removes an instance after unsuccessful END, its
firmware allocation may remain while Linux's count drops.

A separate pre-existing admission bug exists in `iris_vidc.c:41`: when the host
list already has 16 entries, `iris_add_session` silently omits the new instance
but open still succeeds. Its responses then cannot be looked up. This deserves
a focused fix if >16 simultaneous opens are required; there is no evidence of
that condition here, so 0190 does not expand into admission-policy changes.

## Patch and containment

[0190 patch](../patches/linux-7.2.7/0190-media-iris-abort-failed-gen1-sessions-and-contain-teardown-timeouts.patch)
is appended to `series.production`. It changes five kernel files, with no new
parameters, sysfs interface, tracing framework, instance fields or state machine.

- A failed gen1 session uses HFI_CMD_SYS_SESSION_ABORT (`0x210001`), whose
  response is HFI_MSG_SYS_SESSION_ABORT (`0x220004`), matching stock/Venus.
  Failed streamoff waits for it before returning its buffers. A session already
  ERROR takes this path directly; a terminated session gets no further STOP.
- END/ABORT uses `complete_all`: both failed streamoff and close can observe
  the same one-time terminal acknowledgement. `end_sent` covers both commands.
- The existing terminal wait is reused. A rejected terminal response, failed
  teardown command submission or terminal timeout invokes `iris_core_fatal`.
  Ordinary STOP/FLUSH failure first gets the stock ABORT opportunity; it is not
  by itself grounds to take down every other session.
- Close explicitly streams off both queues, then waits for END/ABORT or fatal
  containment, **before** releasing their mappings. This is necessary because
  `v4l2_m2m_ctx_release` previously freed them before the END wait.
- One `dev_err` call prints `session …: HFI response … error …` for erroneous
  gen1 answers, including SYS_INIT and buffer returns. FBD's error is at a
  different offset from the ordinary session header; both FBD layouts share
  that offset. Existing event-error logging remains in place.

Containment uses the existing [`iris_core_contain_fatal`](/home/deck/.local/state/rog5-iris-k120-prepare-r3/source/drivers/media/platform/qcom/iris/iris_core.c:306):
fail/wake instances, quiesce IRQ outside the core lock, request PAS shutdown,
then power off/free shared memory only if shutdown succeeds. New flushes of
containment work run without `inst->lock`; otherwise that worker would deadlock
while failing the instance. Close retains the existing `fw_held` policy if PAS
or power-off fails. No automatic firmware reload or forced collapse is added.

This is containment, not transparent recovery: a contained core stays unavailable
for this binding. The known module-removal hang remains separate. A PAS failure
still means holding resources until reboot; this patch does not solve every
inherited buffer-ownership edge case after a failed hardware shutdown, nor does
host testing qualify the firmware's ABORT implementation on this phone.

## Validation

- Full production series through final 0190: **PREPARED**, exact v7.2.7 base,
  config policy PASS; final preparation took **197.4 s**. Result:
  `/home/deck/.local/state/rog5-iris-wedge-prepare-final-r2/result.json`.
- All **64** Iris source files in that fresh preparation match the compiled
  source byte-for-byte. The builder's final patch input SHA-256 also matches:
  `f12d7a0dd5737669ccada7aa330dfcf8f544a4e89baeadbb19511c56638cf527`.
  Comparison record: `~/.local/state/rog5-iris-wedge-work/verification.json`.
- ARM64 `LLVM=1 W=1` Iris objects and combined `qcom-iris.o`: **PASS**, no
  warnings/errors. First directory build **172.2 s**, final incremental build
  **19.9 s**, reusing an independent copy of the existing k120 object cache.
  Logs: `~/.local/state/rog5-iris-wedge-work/compile.log` and
  `compile-final.log`. ELF check confirms AArch64. No Image, module install,
  modpost, signed candidate or ABI/deployment qualification is claimed.
- Existing `test-video-iris-k120.py`: **6/6 PASS** with the final freshly
  prepared source. Its replay now follows successor entries in
  `series.production`, including 0190, rather than stopping at 0178.
- Repository static check and `git diff --check`: **PASS**;
  `test-render-current-state.py`: **4/4 PASS**;
  checkpatch `--no-tree --no-signoff`: **0 errors, 0 warnings**.

The first full preparation took 231.9 s; a later archive-reuse attempt failed
before extraction because the builder had already deleted its temporary base
export (`unsafe base archive`). The final fresh preparation above supersedes
that infrastructure failure. Patch creation to the first compiled result was
about five minutes. Unix sockets are blocked by the supplied environment, so
active tiers/full CI were not attempted and hardware qualification remains
**NOT RUN**. No new test harness was added. These checks verify application,
source identity and compilation, not firmware/browser behaviour.

## On-phone reproduction

Use a fresh boot of a kernel containing 0190; record `uname -r`, firmware identity
and whether VP9/encoder experiments are enabled. Keep the default H.264-only
configuration for this comparison. The existing installed k116 is not patched
by this work. Do not use module removal as a reset between tests: that already
has a separate observed hang.

1. Capture `sudo journalctl -kf -o short-monotonic | tee iris-browser.log`.
   On this successor, optionally enable the **existing** `trace_config` parameter:
   `sudo sh -c 'echo 1 > /sys/module/qcom_iris/parameters/trace_config'`.
   This captures non-ETB/FTB commands without introducing new instrumentation.
2. Repeat the known local 1080p30 Chromium clip. Save `chrome://media-internals`
   entries showing V4L2VideoDecoder/platform decoding and frame counts; playback
   alone cannot distinguish a software fallback.
3. Play the same YouTube H.264/`avc1` 1080p60 video for at least two minutes.
   Switch 360p → 1080p60 → 720p → 1080p60 about every five seconds, then seek
   forward 30 seconds/back 10 seconds repeatedly. Keep a second video tab
   playing briefly, close it, and navigate the first tab between several videos
   (including an ad → main transition when available). Repeat about 20 times.
   Save media-internals before and after any fallback and the first error line.
4. After closing all videos, observe logs/power for at least 30 seconds, then
   retry the known local clip. If ABORT succeeds, new sessions should decode;
   if teardown is unanswered, expect containment and software fallback until
   a fresh binding/boot, rather than a two-second power-collapse retry loop.

For a more controlled stateful V4L2 client, use this sequence (no new harness
is supplied):

- OUTPUT H.264: subscribe SOURCE_CHANGE, REQBUFS/QBUF/STREAMON, feed access
  units; on initial SOURCE_CHANGE, G_FMT CAPTURE, allocate/queue and STREAMON.
- Feed an IDR/SPS transition to another resolution. Drain CAPTURE through LAST,
  STREAMOFF **CAPTURE only**, REQBUFS(0), G_FMT, reallocate/queue/STREAMON CAPTURE;
  leave OUTPUT streaming. Repeat 720p ↔ 1080p. Expected: FLUSH_OUTPUT and
  CONTINUE, with no STOP/RELEASE caused solely by this reconfiguration.
- Seek: STREAMOFF OUTPUT, reset the bitstream to a fresh SPS/PPS+IDR,
  requeue/STREAMON OUTPUT; perform required CAPTURE reconfiguration on its
  SOURCE_CHANGE. Also exercise both-port streamoff in both orders, followed
  by restart. Expected: FLUSH_ALL when stopping OUTPUT with CAPTURE running;
  STOP/RELEASE only on the last port off for a healthy loaded session.
- Repeat on two simultaneous file descriptors and rapidly close/reopen one.
  If a session fails, expected terminal sequence is **one ABORT**, successful
  acknowledgement or contained shutdown, and **no STOP after END/ABORT**.

Interpret the new error log using the local HFI definitions: `0x221003` STOP,
`0x22100a` RELEASE_RESOURCES, `0x221006` FLUSH, `0x20006` SESSION_INIT,
`0x20007` END, `0x220004` ABORT. Errors `0x1006` indicate incorrect state,
`0x1004` invalid session ID, `0x1009` insufficient resources; SYS error `0x5`
in SESSION_INIT indicates maximum sessions reached. Preserve the first error,
not only later failed opens. A silent timeout should produce
`fatal firmware error (session teardown timeout)` followed by
`video core shut down after the fatal error`, or an explicit held-core failure.
The old endless `skip power collapse` pattern should cease after containment.

## Code that could be deleted from 0154–0178

No unrelated deletion is mixed into 0190. The fix replaces 0162's unsafe rule
that **any** END acknowledgement, including an error, permits freeing memory.
It also removes reliance on 0160's asynchronous failed-streamoff END handling.
The terminal deduplication and matched-response mechanism remain necessary.

Once the independent module-removal investigation is finished, 0172's built-in
`drivers/base/rog5_iris_trace.c`/header and the diagnostic call sites scattered
through devres, genpd, driver core, OPP and IOMMU are strong deletion candidates:
they do not fix this browser wedge. Remove their calls/includes/Makefile entry
together, preserving actual lifetime/PM fixes in neighbouring patches.
The `probe_no_video`, `remove_quiesce` and marker-delay experiments in 0173–0175
can then be removed if no longer needed to resolve that removal hang. They are
not part of decoder operation. 0177's verbose transmit logging can also go once
the first rejection is identified; retain the small always-on error log in 0190.
The unsuccessful `stock_buf_counts` experiment from 0170 is another removable
option if abandoned; do not discard the proven stock-sized buffer calculations.

Keep the real EOS DMA buffer (0161/0163), instance references and closing guard
(0158), fatal/PAS/IRQ containment (0159/0162/0168), SM8350 power sequencing
(0167), buffer-list ownership corrections (0160), and frame-format compliance
fixes. These address observed faults or protect memory, unlike the temporary
instrumentation. VP9/encoder experiments remain separate pending work.

## Proposed commit message

```text
media: iris: abort failed gen1 sessions and contain teardown timeouts

Use SESSION_ABORT after failed streamoff and wait before returning buffers.
Keep END/ABORT acknowledgement available to close and prevent further STOP
commands for failed or terminated sessions. Contain rejected or unanswered
teardown through the existing PAS shutdown path before freeing mappings.

Log gen1 response packet type and error_type. Include successor patches in
the existing Iris source replay and document the Chromium reproduction.

The original YouTube rejection still needs an on-phone capture; host checks
do not establish that hardware playback is fixed.
```
