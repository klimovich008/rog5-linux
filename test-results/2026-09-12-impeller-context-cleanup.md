# Impeller context cleanup diagnosis and source correction — 2026-09-12

**Confirmed:** the selected renderer is Impeller OpenGLES, whose pinned surface
destructor is default and does not clear the context. The actual Denial trace
records no raster-thread unbind before main-thread cleanup fails. A source
correction now passes five semantic destructor cases and compiles as a real
ARM64 engine translation unit. **The corrected engine has not been linked or run.**

This corrects the preceding turn's interpretation: the inspected Skia destructor
has explicit clear-current behavior, but the VM was using Impeller. The older
[source observation](2026-09-12-egl-thread-release.md) remains historical evidence,
not authority for the selected renderer. The preceding goal turn was progress:
its standalone EGL test established that bare thread exit does not permit context
transfer on this VM, while explicit unbind/release does.

## Actual trace and remaining failure

The 48.6-second VM session presents 52 raster frames and 52 page flips, but remains
**FAIL** with five backing-store errors and cleanup EGL_BAD_ACCESS. It ran the
unchanged retained engine, kernel, Mesa/QEMU stack and Flutter bundle. The only
Denial change is bounded read-only context ownership tracing.

All 244 records are contiguous and the 2048-record cap was not reached. There
are 63 bind-entry/success pairs, 57 raster-idle entry/exit pairs, one startup
unbind pair, and cleanup-entry/failure. The startup unbind is on main ThreadId(1).
The render context subsequently belongs to ThreadId(10), including the final
raster-idle record; cleanup on ThreadId(1) reports owner ThreadId(10), no current
main-thread context, then bind failure. A distinct resource context is observed
on ThreadId(11); this correction does not qualify that separate final lifetime.

The selected implementation explains the missing callback: `Rasterizer::Teardown`
makes the context current and resets the surface; `GPUSurfaceGLImpeller` has a
default destructor. `EmbedderSurfaceGLImpeller` explicitly clears only during
its initialization, matching the trace. Five inspected engine files match pinned
engine commit `d728e61e7d835e02c453c70ae9523a40f6c03215` byte-for-byte.
No incomplete FBO, Adreno failure or driver defect is inferred from this evidence.

## Correction, exact identities and checks

Starting repository commit: `0c03356573d78c2137c4369ac175924d51478307`.
Diagnostic build/VM source: `09a4d25a1b923347c6bdc97ba9af68a8362b8146`,
tree `8ab081d9ace052f976104ab1a7525d0fb3306f1a`.
Correction and frozen active-tier source: `27f1dedde6544cb2417d66ddaa32d6377701c923`,
tree `190da29c80d93babe372f58747c516cb1e417fd3`.

The Denial patch `0004-trace-egl-context-ownership.patch` records caller, tracked
owner, context handle and actual current-context handle. It does not call
GetError or alter ownership/admission decisions. Cleanup records survive the
regular trace cap. Four actual ContextBinding decision cases pass before and
after; one additional case proves opt-in behavior, bounds and terminal reporting.

The engine patch `patches/flutter-engine-d728e61e/0001-release-impeller-surface-context.patch`
makes the context current for destruction, releases the surface's Aiks/context
references while its reactor can run, then requests clear-current. Invalid
surfaces make no delegate calls; bind and clear failures remain errors. The
actual extracted destructor is compiled against narrow context/resource/logger
adapters: the old implementation fails four cases and passes invalid-surface;
the correction passes all five. Shared resource owners may outlive this surface.
The patch does not replace frame admission, fences, rendering backend or root FBOs.

- Denial ARM64 diagnostic build: PASS, 211.070 seconds;
  binary `84bbe77ce67eea3f784e6341337a4e5b7c37116aea5f3eb3bc68411509d52304`.
- VM diagnosis: full session FAIL, 48.577 seconds;
  raw serial `d17ac5a951dfdfc58a28368016962189240f6ae8e6e8c4979a8d2922df5cb1af`. All owned containers removed.
- Corrected Impeller real ARM64 translation unit: PASS, 4.426
  seconds; object `446eb7a7ab48611f2324bd7eb9682bac1105c5b111ab8285db25328c2ca39378`. Exact command comes from retained Ninja,
  with only source overlay and object/dependency output redirected. Original
  engine source, build cache and library are read-only for this compile. The
  command preparer's first attempt failed before compilation because it assumed
  split --workdir syntax; the corrected command and failure receipt are retained.
- Frozen active tier: 87 PASS, 0 FAIL/BLOCKED/SKIPPED suites, 255 NOT_SELECTED,
  three declared optional subchecks SKIPPED; 134.233 seconds.
- Final metadata: 13 checker/status cases and inventory/generated-header checks
  PASS. The frozen active service peaked at 318.9 MiB with no swap.
- Corrected complete engine link, corrected-engine VM, and phone: **NOT RUN**.

Exact commands, durations, source/input/output hashes and detailed observations
are in [qualification JSON](2026-09-12-impeller-context-cleanup-qualification.json).
The standalone ContextBinding suite is an explicit-source test, separately run;
the destructor suite compiles real method text, not the complete engine. Neither
host test substitutes for the real corrected-engine VM.

## Next smallest experiment and preservation

Relink a separate engine output using the corrected real object and retained
unchanged dependencies, preserving the original engine library. Then run the
same bounded VM with the trace-enabled Denial binary and changed engine only.
Require raster-thread unbind before main cleanup and absence of cleanup errors;
keep any remaining backing-store failures as full-session FAIL. Do not switch
renderers or enlarge permissions to obtain a passing session. The focused
queued-render Pro review remains a separate pending workstream.

Unchanged source files were linked into an isolated diagnostic tree; every
modified file was replaced atomically. All 701 parent source hashes remain
unchanged. Only 33 byte-verified duplicate VM payload files were retired, with
restoration mappings. Unique binaries, logs, initramfs and every result remain.
The mutable Cargo binary fingerprint was archived/removed after the terminal
build to prevent stale source reuse; dependencies and original standalone bytes
remain. Host disk stayed above 3 GiB; heavy stages ran sequentially.

No phone operation, protected-storage mutation, signing, candidate, claim or
installation occurred. ASUS slot A, accepted server/rescue and V11 fallback are
unchanged. S06/R01 remain FAIL; mobile physical rows remain NOT RUN. Both
published review branches remain frozen. This is progress toward the native
phone goal, not completion or phone qualification.
