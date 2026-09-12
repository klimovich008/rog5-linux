# Impeller EGL surface teardown correction

Base: retained Flutter engine fork `d728e61e7d835e02c453c70ae9523a40f6c03215`.
Retain upstream Flutter's copyright and BSD-style LICENSE; this does not change
the project-wide licensing decision.

The retained VM explicitly selects Impeller OpenGLES. Its default
`GPUSurfaceGLImpeller` destructor does not clear the render context. A bounded
actual Denial trace sees startup unbinding only, then the raster thread keeps
ownership until main-thread cleanup fails with EGL_BAD_ACCESS. A separate real
EGL VM comparison confirms that worker exit alone does not permit transfer.
Skia's explicit clear-current destructor is a different implementation and cannot
qualify this path.

Patch 0001 makes the surface context current for resource destruction, drops its
Aiks/context references while the reactor can run, then requests clear-current.
Invalid surfaces perform no delegate calls. Bind/clear failures remain explicit
errors; no foreign-thread unbind, dummy framebuffer, weakened fence, renderer
switch or changed frame-admission policy is introduced. Shared resource owners
can outlive this surface; this patch does not claim to close every GPU resource
lifetime or the separate queued-render authorization defect.

`python3 scripts/host/test-impeller-context-teardown.py --source EXACT_ENGINE_GIT
--output FRESH_DIRECTORY` applies to the exact file and compiles its actual
destructor with narrow delegate/resource/logger adapters. The old destructor
fails four cases and passes the invalid-surface case; the correction passes all
five. The real engine translation-unit build, complete engine link and VM cleanup
qualification are separate mandatory follow-ups before selecting corrected engine
bytes. No active artifact builder or phone candidate selects this patch yet.

The [corrected-engine VM result](../../test-results/2026-09-12-impeller-engine-vm.md)
now records a complete separate link and successful render-context cleanup. The
full VM still fails on backing-store authorization; IO resource-context lifetime
and phone behavior remain unqualified. The original library is preserved.

Patch 0002 forwards the existing IO-thread release hook from PlatformViewEmbedder
to its surface. The Impeller surface disables IO reactor work and clears a
successfully bound resource context on that same thread. A failed clear is logged
and retains the binding flag; a failed initial bind and repeated successful release
do not issue a spurious clear. Other surface backends retain their existing behavior.
Denial patch 0005 is required alongside it: the shared embedder clear callback must
select the resource context when that context is current on the caller thread.

`scripts/host/test-io-context-release.py --engine-source EXACT_ENGINE_GIT
--denial-source EXACT_DENIAL_GIT --output FRESH_DIRECTORY` exercises the actual
methods with narrow adapters. Three engine and two Denial regressions fail before
the corrections; all nine cases pass afterward. This test does not qualify a
linked engine or EGL runtime. The new virtual method affects derived-class vtables;
recompile the complete dependency closure of the changed headers before linking.
No phone builder or candidate selects these patches.

The [coordinated IO release qualification](../../test-results/2026-09-12-impeller-io-context.md)
now records a complete ARM64 dependency-closure rebuild, separate engine link,
and observed IO-thread release in the VM. Raster and main cleanup still pass;
frame-admission errors retain full-session FAIL. Physical behavior remains NOT RUN.

Patch 0003 is an opt-in, additive raster-call diagnostic. With
`DENIA_RENDER_AUDIT=1`, it records at most 4096 events identifying retained-output,
framework-pipeline, last-layer-tree and preparation calls, implicit expansion
selection, and per-view surface attempts/results. IDs identify actual raster
calls, not native reservations or queued submissions. No broker, scheduling,
selection, fence or framebuffer policy changes. The actual helper test covers
disabled operation, nested/thread-local scope restoration, and concurrent bounds:
`scripts/host/test-render-origin-audit.py --source EXACT_ENGINE_GIT
--output FRESH_DIRECTORY`. This diagnostic alone cannot qualify a session.
