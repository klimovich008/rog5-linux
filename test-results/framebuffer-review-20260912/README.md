# Focused Pro review: initial Denial framebuffer binding in an ARM64 VirGL guest

This is a read-only source/debugging review. The product goal is native Denial
Wayland on ASUS ROG Phone 5 with OLED, touch and accelerated Adreno graphics.
**The failure below is in a generic ARM64 VM using the Steam Deck AMD GPU through
VirGL. It is not an observed phone failure and proves nothing about A660.**
No phone action, signing, admission, claim consumption or installation is requested.

Repository: https://github.com/klimovich008/rog5-linux
Review branch: `agent/pro-framebuffer-review-20260912`.
The handoff supplies the exact review commit; inspect that commit, not a moving
branch tip. Repository source before this packet is
`ab5789b16f88733a25c2ff62b324f2fa6a39f757` (tree
`cb47d94e05e1174be06804d68168ff6990ae15e7`).

## Exact inputs

- Denial: https://github.com/denialwm/denial at
  `85b2303e2f09ae7b7b993641f90061a200f03d53`.
- Smithay Cargo git dependency: `812bd33259ff58810dadef6086d8385eeac1ca55`.
  See Cargo.lock at that exact Denial revision for the upstream URL.
- Linux guest: pristine upstream `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`,
  v7.1.4, `virtio-drm` profile, no ROG5 patches. Image SHA-256
  `34279d12dee925c4c58de9f49411c5e5f9fe85d016214e3939f80cd2f8b797f9`.
- Denial original ARM64 binary SHA-256
  `8698b0716c0ab16ab5c33d618ae52cef0cd8c0966ad356cf2ca49d78a0ba8591`.
- Authenticated Arch ARM64 runtime: 326 packages from
  `packaging/arch/mobile-package-snapshot-20260912-xwayland.json`, SHA-256
  `2f7fc793898dbd18c8732b447bf6965ab98fab7509c003bdec08e80151b31054`.
  Runtime tree SHA-256
  `a8bc7e9fedbf5d8d8c145c5c60fad328bb4ad96b261fa075544d42c3d16418b0`.
- Guest Mesa `1:26.2.2-1`; host Mesa `25.2.8-0ubuntu0.24.04.2`,
  libvirglrenderer `1.0.0-1ubuntu2`; QEMU `8.2.2` Ubuntu
  `1:8.2.2+ds-0ubuntu1.18`. Complete package versions and GL loader hashes are
  attached in this directory. Retained local container ID:
  `d2ea0285ee5edfbf79679684ad70c53c06eb45b705e0fa1cf9967d1560f4023d`.
  This is a local image ID, **not** an advertised pullable registry digest.
- Flutter `d728e61e7d835e02c453c70ae9523a40f6c03215`; shell runtime tree SHA-256
  `e2cfdd7c25fbd00c6a705c0084f0d1a9fb806c00ea2ec3d4c808f93386d6f9de`.
  Flutter engine and shell binaries are unchanged across the runs.

## Newest diagnostic: modifier mismatch observed

The logging-only ARM64 Denial build passed in 214.570 seconds; dependencies and
kernel were reused. Binary SHA-256:
`b3883d00bc8d1904ea2ffe8a499226eaf2b5323e58b6c11b9366691888f79ec4`.
The actual guest reproduced the error in 9.777 seconds and was removed cleanly.
Its initial buffer is XR24 / **Linear**, 640x480, stride 2560, offset zero,
one plane. `renderable=false`. The complete EGL render-format set contains
XR24 / **Invalid**, and no explicit modifiers. Then the same framebuffer error
occurs. Full sanitized diagnostic lines are in `sanitized-vm-evidence.json`.

This establishes a format-membership mismatch at the initial render target.
The exact Smithay code marks that buffer external-only and rejects it before
`bind_texture`; framebuffer completeness is not the first demonstrated issue.
Denial's `compatible_xrgb8888_modifiers` retains explicit Linear when EGL has
no explicit XR24 modifiers, and its implicit fallback also requests Linear.
That assumption does not hold for this actual GBM/EGL pair.

A proposed correction to review is strict explicit intersection, followed by
an **Invalid/implicit allocation request only when every plane and EGL advertises
implicit XR24**. Do not relabel an already allocated explicit buffer. This is
not yet a qualified fix: Smithay/GBM handling of the Invalid request and actual
scanout/import/fence behavior must be checked. The maintainer is preparing an
extracted-function regression independently; no behavior fix is in this review
packet and no phone operation is authorized.

## Relevant implementation

Read `source-excerpts.md` for exact, line-numbered Denial/Smithay excerpts and
full-file hashes. The repository does not vendor those complete projects.
The logging-only `initial-format-diagnostic.patch` applies to pinned Denial.

The path is `startup.rs` → `render_blank_target()` → Smithay
`GlesRenderer::bind(Dmabuf)` → `import_dmabuf()` → `bind_texture()`.
Denial allocates XRGB8888 GBM scanout buffers using an intersection of plane and
EGL render modifiers. Smithay may fall back to legacy GBM allocation, marking
its exported modifier Invalid. Import marks a texture external when its exported
format is absent from `dmabuf_render_formats`. Both external-only rejection and
incomplete GL framebuffer use `FramebufferBindingError` with the same display
text. Check both paths against the observed diagnostic; do not assume an Invalid
modifier is Linear or that extension advertisement proves a working fence.

Repository harness: `scripts/host/test-qemu-virtio-drm.py` and
`tools/qemu-virtio-drm/{init.c,guest.sh}`. Regression classifier:
`scripts/host/test-qemu-virtio-drm-prerequisites.py`.

## Reproduction

The maintainer has retained all exact inputs privately. Pro need not execute
hardware or download/build large artifacts to review this code. The local
container, package archives, materialized runtime, kernel, compiled Denial and
Flutter bundle are **not all downloadable from this branch**. An independent
rerun is BLOCKED until matching artifacts are available or rebuilt; the branch
and source excerpts alone do not constitute a runnable binary bundle.

1. Verify the exact repository/Denial/Linux commits and package graph. Build the
   guest with `QEMU_KERNEL_PROFILE=virtio-drm JOBS=2
   scripts/host/build-qemu-smoke-kernel.sh LINUX_SOURCE build/qemu-virtio-drm`.
2. Authenticate/materialize the exact package snapshot using
   `scripts/host/materialize-mobile-runtime.py`; do not install it on the host.
   Use the matching Denial/Flutter binaries bound above. For the diagnostic
   binary apply the attached patch and build only `deniald` with the existing
   ARM64 cache: Cargo `--locked --offline --release --jobs 1 --features flutter
   --target aarch64-unknown-linux-gnu --bin deniald`. The release profile remains
   thin LTO, one codegen unit. No dependency tracing-feature change was made.
3. Execute the real harness, using explicit retained input paths:

```sh
python3 scripts/host/test-qemu-virtio-drm.py \
  --runtime "$ARCH_RUNTIME" --kernel "$GUEST_IMAGE" \
  --deniald "$DENIALD" --flutter-bundle "$SHELL_BUNDLE" \
  --image d2ea0285ee5edfbf79679684ad70c53c06eb45b705e0fa1cf9967d1560f4023d \
  --render-node /dev/dri/renderD128 --output "$NEW_RESULT_DIR" --deadline 120
```

The host render node is the Deck's, not the phone. The VM sees only virtual DRM,
input and read-only 9P runtime/payload. Container: network none, 1536 MiB RAM,
no swap, two CPUs, 64 PID limit. Guest: 1 GiB RAM, modern Virtio MMIO,
`virtio-gpu-gl-device,xres=640,yres=480`, EGL headless display, no PCI GPU,
`-global virtio-mmio.force-legacy=false`. Serial log bound: 8 MiB.
No host DRM card, USB or block device is exposed.

Guest creates the seatd and D-Bus session services, then runs:

```sh
timeout --preserve-status --kill-after=5 45 /run/payload/deniald \
  --device /dev/dri/card0 --wayland \
  --flutter-bundle /run/payload/flutter --start-locked
```

Omitting `--render-node` selects the separately labelled software path. That
path reaches Flutter but has zero frame/page-flip counters. The corrected
harness treats it as FAIL despite a clean timed exit.

## Observations and hypotheses already tested

- Missing Xwayland was real and fixed by the authenticated 11-package extension.
  The original 315 packages and every prior runtime entry remained unchanged.
- Legacy Virtio MMIO prevented GPU/input probing. Explicit modern MMIO fixed
  discovery on the same guest kernel; 9P alone was insufficient proof.
- QEMU GL device enumeration/ldd missed dlopen dependencies. Adding the exact
  EGL and GL/OpenGL loaders inside the private container fixed initialization.
  Paused QMP graphics initialization passes in 0.479 seconds. Initial QMP stdin
  timeout was fixed with Podman `-i`; this was test plumbing, not graphics proof.
- llvmpipe lacks EGL_ANDROID_native_fence_sync; Flutter backing-store creation
  fails, and terminal counters are zero. No unfenced fallback was introduced.
- VirGL advertises that extension and `has_native_fences=true`, but fails at
  initial blank-target framebuffer binding **before** Flutter engine startup.
  Thus native-fence availability alone does not fix this initial error.
- Error: `deniald: fatal error: Failed to bind Framebuffer`; preceding warning:
  `using legacy fbadd`. Neither identifies the exact failing subpath alone.
- Increasing RUST_LOG did not emit the relevant TRACE calls: the exact Cargo
  dependency enables `release_max_level_info`. A logging-only INFO build is
  used for the newest diagnostic, avoiding a full dependency rebuild.
- `--flutter-offscreen-blit` was inspected but **not tested** as a fix. Startup
  still binds the scanout dmabuf, so it is not assumed to bypass this error.
- Host warning `os_same_file_description couldn't determine if two DRM fds
  reference the same file description` remains. No container capabilities were
  granted to suppress it. Its causality is unproven.
- No modifier, GBM flag, pixel-format or synchronization behavior has been
  changed in the diagnostic. No phone inference is justified by these VM logs.

## Specific questions for Pro

1. From the exact code and newest diagnostic, is the external-only failure path established,
   and which alternatives remain? Cite exact functions/conditions; distinguish
   direct evidence from hypotheses.
2. Does modifier selection, GBM's implicit fallback, export or EGL's advertised
   render-format set form an inconsistent contract? Identify the first boundary
   that could reject or misrepresent the actual buffer. Avoid guessing a modifier.
3. After fixing the demonstrated membership mismatch, what minimal instrumentation would
   distinguish a VirGL/Mesa import problem, invalid GL texture target, or an
   incomplete FBO? Specify exact GL/EGL values and where to capture them without
   consuming or obscuring the original error.
4. Is there a demonstrated Denial/Smithay correctness defect, or only a VM
   capability mismatch? Propose the smallest justified fix and a failing-before,
   passing-after semantic/real-runtime test. Preserve native fences, buffer
   ownership, scanout, cleanup and failure propagation.
5. Which result is transferable to the phone stack, and which must stay VM-only?
   Recommend one bounded next offline experiment and its discriminating outcomes.

Do not return a general roadmap or propose a phone boot/flash/signing operation.
Do not declare support based on extension strings, generic QEMU discovery or a
successful build. If repository access fails, use the attached source excerpts,
patch and sanitized evidence; explicitly name any missing code needed to decide.
