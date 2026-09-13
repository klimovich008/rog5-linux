# XR24 readback preparation — 2026-09-13

The GBM probe now requests and verifies XRGB8888/explicit LINEAR with rendering
usage, matching Denial's render-source format request. Both existing GBM modes
used ABGR8888 before this change. The coordinated request/returned-descriptor
change preserves strict layout refusal, FD ownership, pixel checking and cleanup.
The independent GLES texture-export mode retains its previous format scope.

Starting commit `8a09b7fa466d058c6d8bdc048fe84ba68353e914`, tree
`75f698ab3a7a48d423e0b6a812a038ce7f39281b`.
Executed source `c889faeace59b40172fec3ab129092e3b162e7b7`, tree
`461923ef3a302212b4c3fb1479f1a5bdf378b4a8`.
The final publication commit adds evidence/current-pointer metadata only.

| Check personally executed | Result | Time |
|---|---|---:|
| New XR24 regression against old request | Expected FAIL, both GBM modes | 3.290s |
| Full host readback suite | 16 test groups PASS | 12.343s |
| ARM64 optimized twins | Identical bytes, PASS | 1.468s / 1.417s |
| ARM64 ABI fixture build | PASS | 0.766s |
| Actual ARM64 binary against ABI fixtures | 11 groups PASS | 9.628s |
| Real ARM64 Mesa softpipe shader/readback | PASS, software only | 1.017s |
| Software renderer refused by A660 mode | Expected refusal PASS | 0.766s |
| Prior runtime package-file identities | 117 match retained tree | 0.862s |
| Frozen-source active tier | 93 PASS; 0 FAIL/BLOCKED/SKIPPED; 255 NOT_SELECTED | 138.581s |

The active tier used two workers, a 1GiB/no-swap ceiling and a 600-second
process-group limit; peak memory was 285.3MiB. No unrelated kernel rebuild,
Flutter rebuild, graphics VM or existing CI result was used as evidence.
The loader check passed separately in 0.064s. Software Mesa reported GLES3.1
after the existing GLES3.2-to-3.0 request fallback; DMA-BUF/native fences and
scanout remained NOT RUN in that software run.

Both compiled ARM64 twins SHA256:
`bfb8edc07d91cf487da7abace8175edd5f41a734abacc66c852dec44b4fd2531`.
The historical ABGR probe `77c98c27e8bb2f8913bbfddc5429cebf5495161da7e3e6a86fdc7761cafecffa`
is retained unchanged with its original qualification. No image or trial builder
was changed to select the new binary. The new current pointer is an unsigned,
unadmitted component fixture, not a phone candidate.

The [qualification JSON](2026-09-13-xrgb-readback-qualification.json) retains
commands, timings, source/tool/output identities, negative-test observations,
initial preparation failures, runtime binding and bounded test summaries.
The new regression rejects returned ABGR and implicit layouts before EGL import,
and checks that the allocated BO is destroyed. Existing corrupt-pixel, absent
server-wait, FD ownership, context restoration and teardown cases still run.
RGBA readback uses logical GLES channels; opaque XRGB alpha is not a test of
stored alpha preservation or blending.

## Exact kernel and Denial scope

The corrected production source/config includes MSM GPU/KMS, DMA shared buffers,
sync files, render nodes, sync objects and timeline sync objects. MSM submission
contains input/output sync-file paths; DPU format handling includes XRGB8888 and
LINEAR for supported plane formats. These are source/config observations, not
proof that the physical GPU initialized or an active plane accepts this buffer.
A targeted C compile against those raw UAPI headers confirms host structure,
ioctl and fourcc values; it is not an ARM64 kernel execution.

Retained Denial `kms_state.rs:24` uses RENDERING alone when render and display
devices differ; a shared device also requests SCANOUT. Its buffer allocation at
line493 uses Xrgb8888, and its selector separately intersects plane and renderer
formats. This probe tests import/render/readback and selected synchronization
on **one EGL device**. It does not qualify actual cross-device PRIME, local
SCANOUT usage, full modifier negotiation, framebuffer registration, atomic KMS
checks or OLED presentation. Independent read-only review confirmed that scope.

Preparation failures stopped before useful runtime tests: the first compiler
output path was outside its writable mount; the first full-root ARM64 fixture
used mount targets outside private `/tmp`. Both were corrected and their original
failures retained. Raw UAPI headers also needed explicit userspace annotation
removal for the isolated layout compile; kernel source was not edited.

## Retention and next boundary

Reclaimed 60,313,600 bytes from 33 duplicate staging files belonging to a terminal
historical VM. Each was hashed against its retained canonical source; no open
handle was observed, no container remained, and no matching local mount existed.
The restoration map preserves every removed path, source, hash, size and mode.
Historical VM logs, results, canonical Denial/engine/AOT and runtime bytes remain.
Host free space stayed above the 3GiB floor.

Changed source files: `tools/a660/rog5-gles-readback.rs`,
`tools/a660/test-fake-gles.c`, `tools/a660/README-gles-readback.md`,
`scripts/device/test-gles-readback.py`, `docs/development-lessons.md`.
Publication changes are this report, qualification JSON, the two artifact
manifests, structured project status and generated current-state header.

Next: bind this component to a host-only recording/cleanup fixture for the
corrected production cohort. Do not substitute it into the frozen older trial.
Actual A660 XR24 allocation, fences and pixel readback remain the next physical
question, requiring separate authorization and exact reviewed trial inputs.
No phone/USB operation, signing, admission, claim, candidate, installation or
protected-storage mutation occurred. Physical rows stay **NOT RUN**, S06/R01
stay **FAIL**, and the long-term native-phone goal remains incomplete.

Publication validation PASS: five metadata regression cases (0.816s), eight
mobile-status cases (0.018s), artifact inventory and generated-status checks.
All510 prior artifact records, both acceptance contracts, historical status
body and old ABGR binary bytes were verified preserved. The inventory now
contains511 sets.
