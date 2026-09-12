# Denial implicit modifier correction

Base: denialwm/denial `85b2303e2f09ae7b7b993641f90061a200f03d53`.
Upstream compositor metadata declares GPL-3.0-or-later; retain its source notices.
This patch is not selected by a phone image builder and grants no installation,
execution or admission authority.

An actual ARM64 VirGL guest exported XR24/Linear while EGL advertised only
XR24/Invalid. Smithay consequently imported it as external-only and refused
render-target binding. The patch intersects explicit formats strictly, requests
Invalid only for shared implicit support, and preserves that request through
scanout-pool allocation. It does not relabel buffers or change native fences.
Pool dimensions, memory limits, explicit preference/fallback, allocation errors
and partial-allocation destruction remain in the existing path.

Run the manual exact-source regression with a retained upstream checkout:

```sh
RUSTC=rustc python3 scripts/host/test-denial-modifier-selection.py \
  --source /path/to/exact/denial --output /path/to/fresh/test-output
```

This compiles the actual selected functions from the pinned Git object before
and after patch application. Nine cases cover modifier compatibility, allocation
routing, failure cleanup and unchanged guards. Only data types and allocator
boundary effects are adapters; GBM/EGL/DRM are not modeled. The original fails
five cases; the corrected functions pass all nine. Missing exact source or
compiler cannot pass. This explicit-source test is not silently run by ordinary
repository tiers; real ARM64 build and VM results remain separate evidence.
The logging-only diagnostic used in VM comparison lives in the review packet,
not in this behavior patch. Neither VM result proves phone GPU or scanout.
