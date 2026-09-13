# Denial implicit modifier correction

Base: denialwm/denial `85b2303e2f09ae7b7b993641f90061a200f03d53`.
Upstream compositor metadata declares GPL-3.0-or-later; retain its source notices.
This patch is not selected by a phone image builder and grants no installation,
execution or admission authority.

`0008-use-logical-window-content-size.patch` fixes shell presentation sizing:
the surface tree already maps logical content, so its outer frame, status bar
and preview aspect must use that logical size rather than backing-buffer pixel
dimensions. The local Flutter app path supplies its existing logical layout
size explicitly. Buffer sampling and surface/input coordinate mapping remain
unchanged. The manual regression executes the production widget-construction
method, metrics, content mapping and matching Flutter `applyBoxFit` with value
adapters; it does not execute Flutter rendering or qualify a phone:

```sh
python3 scripts/host/test-mobile-content-sizing.py --source EXACT_DENIAL_TREE \
  --flutter-box-fit EXACT_FLUTTER/packages/flutter/lib/src/painting/box_fit.dart \
  --dart BOUNDED_DART_EXECUTABLE --output FRESH_DIRECTORY
```

Keep its source/tool hashes with the result. This exact-source check is manual;
ordinary repository tiers do not silently count it as executed. The patch is
not selected by any phone image builder. A matching shell AOT build and bounded
VM observation are separate checks.

An actual ARM64 VirGL guest exported XR24/Linear while Smithay’s EGL-derived render-format set contained only
XR24/Invalid. Smithay consequently imported it as external-only and refused
render-target binding. The patch intersects explicit formats strictly, requests
Invalid only for shared implicit support, and preserves that request through
scanout-pool allocation. Before framebuffer registration it checks that the
BO and exported dma-buf agree on XR24 and a requested modifier. Unexpected
explicit or implicit results fail with both descriptors; they are not relabeled.
Native fences are unchanged. Smithay inserts implicit entries into its derived
set; that membership permits an attempt and is not a raw EGL query result.
Pool dimensions, memory limits, explicit preference/fallback, allocation errors
and partial-allocation destruction remain in the existing path.

Run the manual exact-source regression with a retained upstream checkout:

```sh
RUSTC=rustc python3 scripts/host/test-denial-modifier-selection.py \
  --source /path/to/exact/denial --output /path/to/fresh/test-output
```

This compiles the actual selected functions from the pinned Git object before
and after patch application. Sixteen cases cover modifier compatibility, allocation
routing, failure cleanup and unchanged guards. Only data types and allocator
boundary effects are adapters; no real GBM/EGL/DRM operations run. The original
fails ten cases; the corrected functions pass all sixteen. Allocation cases
check returned/exported descriptors, original export errors and resource release
before DRM registration on failure, through both same-device and PRIME routes. Missing exact source or
compiler cannot pass. This explicit-source test is not silently run by ordinary
repository tiers; real ARM64 build and VM results remain separate evidence.
The logging-only diagnostic used in VM comparison lives in the review packet,
not in this behavior patch. Neither VM result proves phone GPU or scanout.


`0002-distinguish-render-target-refusals.patch` is a separate diagnostic patch.
With existing `DENIA_RENDER_AUDIT=1`, it distinguishes missing view/size pool,
missing render authorization and no reusable slot, preserving the old aggregate
counter and all broker decisions. It also exposes existing authorization expiry
at INFO level only while auditing. It does not extend deadlines or admit frames.
Use the same source/output arguments with
`scripts/host/test-denial-broker-refusals.py`; seven actual-function cases cover
refusal identity, unchanged consumption/expiry and audit counter aggregation.
The two patches apply in numeric order; neither is selected by a phone builder.


`0003-trace-render-authorization-history.patch` adds an audit-only sequence of
at most 512 grant/consume/expire/cancel/refusal records, including render view,
request serial, authorization age and current slot state. It does not change
admission. Apply after 0002. The same broker runner now checks nine cases,
including expiry followed by a fresh explicit grant and concurrent trace bounds.

`0004-trace-egl-context-ownership.patch` adds audit-only ownership observations
around actual bind/unbind, raster-idle and post-engine cleanup. Each record gives
the caller thread, tracked owner, EGL context handle and current-context handle;
it does not consume EGL errors or change ownership decisions. Regular records
are capped at 2048; terminal cleanup records remain visible after saturation.
Use `scripts/host/test-denial-context-ownership.py --source EXACT_DENIAL_GIT
--output FRESH_DIRECTORY` with the retained Rust compiler. Four actual-function
cases pass before and after instrumentation; one additional test covers the
opt-in query/log cap and terminal exception. EGL effects are adapters in this
host suite; the real ARM64 build and VM trace are separate. No phone builder
selects these patches. Apply in numeric order for the combined diagnostic.

`0005-clear-current-io-resource-context.patch` corrects callback dispatch for
Flutter's IO resource-context release. It selects the resource context only when
that context is actually current on the caller thread, and retains the existing
ContextBinding ownership check and failure propagation. Render-context dispatch
is otherwise unchanged. Apply with engine patch 0002; neither correction alone
closes the IO shutdown path. The joint actual-method regression command is in
the [engine patch notes](../flutter-engine-d728e61e/README.md).


Patch 0006 replaces view-only grants with nonzero, process-unique work IDs.
Admission must precede backing-store acquisition on the same raster thread;
expiry and completion cannot revoke that admitted span. Late completion cancels
only unused grants for its own work. It requires engine patch 0004 and its two
new exported functions; older libraries fail loading. Apply all patches in
numeric order. The manual `test-render-work-broker.py` runner uses a fully patched
Denial source tree and executes actual broker, handler and FFI methods. Its host
PASS does not qualify queued engine execution, GL, the VM or phone.

Patch 0007 constructs the host lifetime owner before registering callbacks, so
registration failure followed by failed shutdown retains the complete callback
and configuration graph. The actual startup-tail test has two failures before
and six passes after the correction. This is injected-error contract hardening;
the pinned matched runtime has no demonstrated path to that pair of failures.
Run `test-engine-registration-ownership.py --source-before BEFORE_SOURCE
--source-after AFTER_SOURCE --output FRESH_DIRECTORY`. The two supplied trees
must differ by patch 0007; the runner checks that identity before extracting
the actual startup and shutdown methods.

Patch0013 uses one frame-sampled keyboard animation position for the sheet,
content translation and native input regions. Target/drag state still controls
the spring. It also aligns scroll-strip eligibility and starts interrupted drags
at the displayed position. The prior0.001 sheet cutoff is applied centrally,
so spring residue cannot leave an invisible native keyboard region. Apply after
0012 to the matching shell source; this is not selected by a phone builder.

Run `scripts/host/test-keyboard-animation-geometry.py --source PATCHED_SOURCE
--dart PINNED_DART --output FRESH_DIRECTORY`. It executes actual Dart viewport,
controller, scheduling and native-layout methods with geometry/widget/scheduler
adapters. It does not execute Flutter rasterization, Riverpod or real native
input delivery. The prior source can be supplied to reproduce the mismatch.
Use a real matching shell frontend build separately to check complete types.
This correction retains manual panning; caret rectangle transport and client
resizing are separate work, not claims of this patch.

Patch0014 publishes optional committed Wayland caret geometry and activation
identity through the existing bridge. Coordinates are relative to the owning
window's logical content origin, independent of viewport movement. Zero width
is valid. Same-editor touches retain unchanged committed geometry; focus,
enable/disable, destruction and lock transitions prevent stale publication.
Caret publication can precede the corresponding window snapshot, so consumers
must retain pending ownership and use it only after matching window data arrives.
Generated Rust/Dart bindings use the pinned FlatBuffers25.9.23 tool; regenerate
with `FLATC=/path/to/flatc tools/generate-denial-wire`.

`test-denial-caret-state.py --source PATCHED_SOURCE --output FRESH_DIRECTORY`
executes the actual state machine and publication-cache equality with host Rust.
`test-denial-caret-wire.py --source PATCHED_SOURCE --source-before PRIOR_SOURCE
--flatbuffers-rlib MATCHING_ARM64_RLIB --output FRESH_DIRECTORY` compiles actual
encoders and generated old/new readers. Set `RUSTC` to the matching compiler and
`ROG5_ARM64_RUNNER` to a bounded ARM64 userspace runner. It uses thin LTO to match
the retained bitcode-only dependency. These explicit-source tests do not run
implicitly in repository tiers or qualify the full compositor, shell or phone.
