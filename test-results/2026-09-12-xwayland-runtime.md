# Authenticated Xwayland runtime and virtual session qualification

Offline progress; native phone acceptance remains incomplete. No phone operation,
protected-storage mutation, signing, candidate generation, admission, claim or
production installation occurred. The optional VirGL run exposed only the Deck
render node to a bounded, network-isolated guest container. No host display-control,
USB or block device was passed through. No host packages were installed.

## Source and scope

Starting source: `7b0a310890745fdf22199fcfb3c4b852a8e47e05`, tree
`837de3852ec4bb08bca78d1c281eb795161a3187`. Frozen executable source:
`756481ca35592149b9ef8951de8ee595b7a065eb`, tree `128dafd8ae9809d1b2766f6d733c12cd353d9c9e`. The subsequent documentation/pointer commit carries this
report; its identity is in Git and the private completion receipt.
The source fixes are NOT INSTALLED. Signed candidate, fallback and observed-runtime
pointer fields remain identical. All 482 previous artifact sets are preserved;
one new fixture set records this runtime and its retained failures.

The reviewed `4bd1a817` files were not restored. Existing changes include boot
acceptance (`3f0f1c25`), screen transition errors (`7e0db9c7`), panel brightness
and lifecycle (`a4f93763`), and regulator ownership (`fce7a989`). Their original
qualification remains separate from this turn's execution. Current exact-board
qualification and its historical failures remain unchanged. This work closes the
next demonstrated runtime prerequisite and test-reporting defects, not every
mobile acceptance row.

## Confirmed and fixed

- Xwayland was unconditional in pinned Denial startup but absent from the old
  package graph. The explicit successor adds 11 authenticated packages without
  changing any of the previous 315 pins. The retained repository databases resolve
  326 packages/1467 edges; independent libalpm print-only resolution agrees.
- All 326 archive signature/hash/metadata checks pass. Materialization took
  113.625 seconds without package hooks. All 55,666 prior filesystem entries are
  unchanged; 145 were added. Xwayland actually starts in the successor guest.
- The old shell test reported PASS after a clean timeout with zero raster frames
  and page flips. Its raw receipt is retained; the new classifier returns FAIL
  on that exact log. It requires one unambiguous terminal summary, positive counts
  and no observed rendering errors. Five focused cases cover prerequisites,
  counter/error semantics and render-node validation. The guest also creates its
  session bus before launching Denial.
- VirGL's dynamically loaded host GL dependencies were missing despite successful
  device enumeration. Exact package inventories and container IDs are retained.
  A direct QMP graphics initialization passes in 0.479 seconds using the complete
  container. No production runtime library or host package was replaced.

## Executed integration results

| Check | Result | Seconds | Meaning |
|---|---|---:|---|
| Full software guest | FAIL under corrected classifier | 50.752 | Historical runner said PASS for exit only; zero frames/flips and missing native fences |
| VirGL first container | FAIL | 1.332 | Missing runtime-loaded EGL library |
| VirGL second container | FAIL | 3.560 | Missing GL/OpenGL loader |
| Complete VirGL container | FAIL | 12.745 | Initial framebuffer bind fails before Flutter startup |
| Targeted trace guest | FAIL | 10.129 | Same boundary; TRACE compiled out in retained release |
| Frozen repository active tier | PASS | 130.727 | 87 PASS, 0 FAIL/BLOCKED/SKIPPED suites; 255 NOT_SELECTED |

After the metadata update, 19 optimized metadata regressions passed in 2.022
seconds. The inventory/current-state validators and git diff whitespace check
also passed. Both acceptance contracts, all previous artifact records and the
historical current-state body were compared byte-for-byte or as parsed records.

Three declared optional subchecks were SKIPPED. Active-tier peak memory was
366 MiB, swap zero. Exact per-test deadlines, commands, durations and selection
are in the JSON/JUnit references. These are personally executed host results;
no new GitHub CI run is claimed. Generic QEMU is not phone hardware evidence.
The first QMP attempt omitted interactive stdin and timed out; the corrected
request and all preparation failures remain recorded, including the initial
container-build postcheck failure. Do not repeat the completed kernel build.

## Remaining issues, ordered by severity

1. Real phone display/touch/A660 rendering and a usable mobile session remain
   NOT RUN for the corrected source. S06/R01 remain FAIL. No virtual result closes
   these rows; the installed/signed bytes have not changed.
2. Full virtual Denial rendering fails. VirGL advertises
   EGL_ANDROID_native_fence_sync, but actual fence export/use is not reached.
   Smithay can emit the same framebuffer error for an external-only imported
   texture or an incomplete framebuffer. The logs do not yet distinguish them.
   Do not change modifier selection or weaken synchronization based on a guess.
3. Existing TRACE callsites are disabled by Denial's release_max_level_info.
   A diagnostic build is required to record the actual exported dmabuf format,
   supported render-format membership and framebuffer status. Reuse the exact
   kernel, runtime and compiler cache; first restore adequate disk headroom.
4. The host AMD file-description warning remains unexplained. No additional
   container capabilities were granted. Software llvmpipe lacks the required
   native fence extension and cannot substitute for this integration proof.

No reviewed finding was disproved by this new virtual run. The missing-Xwayland
blocker is resolved; whole-session rendering is still FAIL. Further diagnostics
are constrained by disk headroom, not phone authorization. No physical test is
authorized here. After this offline boundary is understood, the next *separately
authorized* hardware question remains whether the exact corrected display path
can scan out and perform bounded brightness/blank transitions with the preserved
rescue/fallback process. Do not request Ready or consume a claim in this task.

## Identities and evidence

The reused Linux guest is `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`;
Image SHA-256 `34279d12dee925c4c58de9f49411c5e5f9fe85d016214e3939f80cd2f8b797f9`.
Denial remains `85b2303e2f09ae7b7b993641f90061a200f03d53`, binary SHA-256
`8698b0716c0ab16ab5c33d618ae52cef0cd8c0966ad356cf2ca49d78a0ba8591`.
The runtime tree SHA-256 is `a8bc7e9fedbf5d8d8c145c5c60fad328bb4ad96b261fa075544d42c3d16418b0`.
The graph SHA-256 is `2f7fc793898dbd18c8732b447bf6965ab98fab7509c003bdec08e80151b31054`.

[Qualification JSON](2026-09-12-xwayland-runtime-qualification.json) binds all
executed commands, receipt/log hashes, container versions and per-test results.
Private evidence remains in
`/home/deck/.local/state/rog5-xwayland-runtime-evidence-20260912-r1`.
[Current artifact pointer](../manifests/current-artifact.json) selects the new
runtime while preserving older evidence and all hardware identities.

Changed files in this checkpoint:

- `configs/project-status.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
- `docs/development.md`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`
- `packaging/arch/mobile-package-snapshot-20260912-xwayland.json`
- `scripts/host/test-qemu-virtio-drm-prerequisites.py`
- `scripts/host/test-qemu-virtio-drm.py`
- `test-results/2026-09-12-xwayland-runtime-qualification.json`
- `test-results/2026-09-12-xwayland-runtime.md`
- `tools/qemu-virtio-drm/guest.sh`
