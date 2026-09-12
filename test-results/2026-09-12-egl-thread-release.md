# EGL worker-thread release comparison — 2026-09-12

The retained VirGL VM leaves the EGL context unavailable after its owning worker
exits without explicit release. The same context transfers successfully after
worker-side unbinding or `eglReleaseThread()`. Every mode first observed
`EGL_BAD_ACCESS` while the worker remained alive and current. This is a completed
standalone comparison, **not a fixed Denial session or phone GPU evidence**.

| Worker action before join | Main-thread acquisition after join |
| --- | --- |
| Return without EGL release | FAIL, `EGL_BAD_ACCESS` (`0x3002`) |
| `eglMakeCurrent(... EGL_NO_CONTEXT)` | PASS, `EGL_SUCCESS` (`0x3000`) |
| `eglReleaseThread()` | PASS, `EGL_SUCCESS` (`0x3000`) |

The preceding goal turn was progress: a bounded authorization history and a
published focused review. This independent result changes the cleanup hypothesis.
The two review branches remain frozen at their published commits; no new push
or review request was needed for this experiment.

## Exact implementation and execution

Starting repository commit: `e5210ecd8ad6156dbadb028e83ba0878d24f8b0b`.
Probe/build/test source: `ecd4608223cf10f5952e99b27f0c17e79f991dfa` (tree `206915d9e6a6417f3ffbc9a9b51fde4f0ca8b7ee`).
The implementation adds `tools/qemu-virtio-drm/egl-thread-probe.c`, an explicit
mutually exclusive `--egl-thread-probe` harness mode, a three-process guest
comparison and semantic result-parser cases in the existing prerequisite suite.
Existing Denial CLI/shell commands remain available. Probe PASS cannot become
Denial PASS; the result records `deniald_sha256=null` and Denial NOT RUN.
The probe requires the virtual marker and VirGL renderer, uses a condition-variable
handshake to hold the worker current during the collision check, and records
immediate EGL errors. No sleeps determine the ownership ordering.

- ARM64 GCC build with `-Wall -Wextra -Werror`: PASS, 0.615 seconds.
- Virtual comparison: PASS, 12.931 seconds, all three modes.
- Six host prerequisite/classifier cases: PASS, including missing/duplicate
  observations, bad live-ownership control, failed explicit release, and the
  distinction between an observed exit-only failure and a failed experiment.
- Frozen active tier: 87 PASS, 0 FAIL/BLOCKED/SKIPPED suites, 255 NOT_SELECTED;
  three declared optional subchecks SKIPPED, 131.369 seconds.
  Service peak memory 285.5 MiB, no swap. Build and VM containers removed.
- Final metadata: 13 checker/status cases and inventory/generated-header checks
  PASS. The first metadata run failed because the appended artifact set left
  coverage.set_count at 487; deriving 488 from the set list corrected it. The
  failed and passing receipts remain separate in the private evidence directory.
  Historical inventory entries retain their original compact formatting.

The build used retained GCC 13.3.0 in immutable container `0f429c6fd38e4400d8638bff1f7da0170375275ab29201e327a3e236ed9df16d`.
Probe executable SHA-256: `8cd05f3ef196593560595217ed4d49ee4bd777ab7683434eab7032892e2ed994`.
Raw serial SHA-256: `419543c34de7c3023b3d5ccfac00b49a98be77a106c877c5d5c5ddfcfb8df27e`.
The VM reused the authenticated 326-package Arch runtime, Mesa 26.2.2,
QEMU/VirGL container and generic virtual ARM64 kernel from the earlier run.
No kernel, engine or Denial rebuild was performed. Each process has a ten-second
guest deadline; the existing network-off, read-only runtime/payload, render-node-only,
1536 MiB/no-swap container, 120-second harness and 8 MiB log bounds remain.
Host disk remained above 3 GiB; this experiment added only a small executable
and logs. Exact command vectors, tool/input/output hashes and durations are in
[qualification JSON](2026-09-12-egl-thread-release-qualification.json).

## Source implications and remaining boundary

`FlutterGlHandler::destroy_targets()` assumes the joined raster thread cannot
leave the context current elsewhere. The standalone result disproves that general
inference for this VM stack. It does **not** prove which Denial callback left its
context bound, nor prove a driver bug. The pinned Flutter source already calls
`GLContextClearCurrent()` from `GPUSurfaceGLSkia` destruction, and the embedder
forwards that callback. Those four inspected C++ files match engine commit
`d728e61e7d835e02c453c70ae9523a40f6c03215` byte-for-byte.

The [EGL 1.5 specification, section 3.12](https://registry.khronos.org/EGL/specs/eglspec.1.5.pdf)
defines explicit thread-state release and context unbinding. The experiment
measures this implementation's exit behavior; it does not extrapolate it to A660.

Next trace the actual Denial make-current/clear-current/raster-idle/cleanup
callbacks with context and thread identity, preserving successful and failed
unbind returns. Pay attention to callbacks queued after surface teardown.
Do not add unconditional release to `raster_idle`: its host has a synchronous
fallback when posting fails, so its thread ownership must be established first.
The full Denial result remains FAIL (50 frames, eight backing-store errors,
cleanup BAD_ACCESS). Queue-authorization review remains separate and pending.

All phone physical rows stay NOT RUN. Accepted server/rescue, ASUS slot A, signed
fallback, prepared candidate and consumed claims are untouched. S06 and R01
remain FAIL. No phone contact, signing, claim operation, installation or
protected-storage mutation occurred.
