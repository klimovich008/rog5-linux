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
