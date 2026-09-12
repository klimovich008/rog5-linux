# Denial implicit modifier correction

Base: denialwm/denial `85b2303e2f09ae7b7b993641f90061a200f03d53`.
Upstream compositor metadata declares GPL-3.0-or-later; retain its source notices.
This patch is not selected by a phone image builder and grants no installation,
execution or admission authority.

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
