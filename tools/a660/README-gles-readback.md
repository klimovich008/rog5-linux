# Offscreen GLES shader/readback component

`rog5-gles-readback.rs` renders one 4×4 fullscreen triangle in a GLES 3.2 context
(or 3.0 fallback), verifies all
64 RGBA channels to one quantization unit, and completes EGL cleanup before
publishing PASS. It requires EGL 1.5, `EGL_MESA_platform_surfaceless`, an RGBA8
pbuffer configuration advertising GLES 3 support and the runtime `libEGL.so.1` / `libGLESv2.so.2` libraries.
It uses no Rust crates or development GL headers. The version preference
matches pinned Denial 85b2303e: GLES 3.2, then GLES 3.0 if context creation fails.
The actual major/minor version is queried before shader creation and must meet
the requested version. Output records requested/actual versions and the first
EGL creation error when fallback was needed. The simple shader does not qualify
Denial's complete shader set or native-fence/DMA-BUF path. For example, compile offline:

```sh
rustc --edition=2021 -Dwarnings -O tools/a660/rog5-gles-readback.rs -o NEW_OUTPUT
python3 scripts/device/test-gles-readback.py
```

The test requires Rust, a C compiler, bubblewrap and Mesa software runtime
libraries. It executes the actual probe against both fault libraries and real
software Mesa in a private namespace without `/dev/dri`. Missing prerequisites
fail the mandatory suite. The no-draw mutation must fail against real Mesa.
Each probe has a ten-second test deadline; the repository suite has a separate
120-second process-group deadline and runs serialized with namespace tests.
The test accepts an explicit `RUSTC` compiler wrapper for a cached offline
builder. CI records its actual Rust and package versions.

No-argument invocation exits before loading EGL. `--software-fixture` accepts
software renderer identities only and emits `scope=software-fixture-only`.
`--require-a660` accepts exact `FD660`, `Adreno 660` or `Adreno (TM) 660` strings;
unknown names are refused rather than guessed. Renderer strings alone are not
trusted hardware identification. The component must run under the existing
exact-device, module/Mesa identity, power/thermal, admission and recovery process
before a phone result can be interpreted. This source addition grants no such
authority. It is not selected by any current image/trial builder.

Every result keeps physical acceptance and scanout NOT RUN. Buffer sharing is
NOT RUN unless the explicit DMA-BUF mode completes.
A successful authorized A660 readback would prove this offscreen shader path,
not OLED output, sustained rendering, Vulkan, native fences, DMA-BUF
formats/modifiers/export/import, or Denial's complete renderer integration.

Driver calls, including cleanup and readback, are synchronous and may hang.
A future coordinator must enforce an external process deadline, retain stderr
and the exact executable/Mesa/kernel identities, and collect recovery evidence.
The program does not claim an internal GPU timeout. A killed/interrupted run
has no success record; driver-resource release then belongs to process teardown,
not to an observed successful EGL cleanup.

The old Vulkan helper intentionally submits an empty command buffer. Its
historical acceptance scope and sealed callers are unchanged.

## Optional native-fence check

Add `--native-fence` after the explicit renderer mode to require Denial's
create/flush/export sequence after drawing. The exported descriptor must become
readable within one second, with interrupted polls sharing the original deadline.
`SYNC_IOC_FILE_INFO` must identify it as a Linux sync file with status 1; readable
error fences and ordinary descriptors fail. The owned exported FD closes on every
path before the producer EGL sync is destroyed. Pixel readback and PASS follow
only after the fence check succeeds. Destruction failures remain errors.

The optional mode requires `EGL_ANDROID_native_fence_sync` and
`EGL_KHR_fence_sync`; there is no ordinary-EGL-fence fallback. Without the option,
output explicitly records `native_fence=NOT RUN`. Missing support fails a
requested check and is a capability blocker, not a successful native-fence trial.
The external process deadline still covers driver calls that can block.

This checks export, bounded completion and Linux status; it does not prove
cross-context imports, KMS in-fence consumption, buffer sharing or physical
qualification. Offline fault tests use actual eventfd/poll/FD closure with the
EGL and sync-file ioctl boundaries controlled by an LD_PRELOAD fixture. That
fixture is used only in the no-DRI test namespace; it is never a native-fence
hardware proof.

## Optional native-fence consumer check

Use `--native-fence-import` instead of `--native-fence` to add a second,
unshared GLES context and pbuffer. After producer draw/flush/export, duplicate
the exported FD, import it with `EGL_SYNC_NATIVE_FENCE_FD_ANDROID`, and queue
`eglWaitSync(..., 0)` in the consumer context. Create, flush and export a second
native fence after that wait; require its bounded completion and Linux status 1.
Then destroy the imported sync, restore the producer context, destroy the
consumer resources, and check producer status before pixel readback.

The duplicate transfers to EGL on successful import; import failure closes it
in Rust, as in pinned Smithay 812bd33. Every later error attempts independent
EGL cleanup. If restoring the producer fails, GL object deletion is skipped
and context teardown reclaims those objects. Success requires every explicit
cleanup operation to succeed. Each exported-FD wait has a one-second deadline;
an external process deadline must cover the whole run, including driver calls.

Output adds `native_fence_import=PASS` only for the requested, completed path;
plain/export-only modes record `native_fence_import=NOT RUN`. The controlled ABI
fixture covers descriptor exhaustion, import/wait/consumer completion failures,
context restoration, teardown and interruption. Its eventfds are not GPU fences.
A real successful run would prove import/server-wait API operation and consumer
queue completion, not that an unsignaled dependency was exercised: the producer
may already have finished. Shared buffer visibility, DMA-BUF formats/modifiers,
KMS consumption and A660/physical acceptance need separate evidence.

API references: [native fence FD ownership](https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_native_fence_sync.txt)
and [server wait semantics](https://registry.khronos.org/EGL/extensions/KHR/EGL_KHR_wait_sync.txt).
The probe uses the EGL 1.5 core wait entry point, matching pinned Smithay.

## Optional linear DMA-BUF pixel check

Use `--dma-buf` as the single optional mode. It allocates a 4×4 RGBA8 GLES
texture, renders the existing shader through an FBO, and uses `glFinish` for
producer completion. It creates a preserved EGLImage, queries/exports its
DMA-BUF, imports the exported layout into a new EGLImage with explicit linear
modifier attributes, binds a second texture/FBO, and verifies all 64 channels.
Only after pixel validation and all cleanup succeed does it emit `dma_buf=PASS`.

The initial scope is one plane, ARGB8888 or ABGR8888, explicit linear modifier,
and the same GLES context. Unsupported planes, formats or modifiers are refused;
there is no implicit modifier fallback. Query storage accommodates all four
planes permitted by MESA before validating the single-plane requirement.
Stride must hold a four-pixel row and offset must be nonnegative. EGL import
borrows the exported FD; the caller closes it on every path, including partial
export failure. This differs from native-fence import ownership.

The mode requires `EGL_MESA_image_dma_buf_export`,
`EGL_EXT_image_dma_buf_import`, `EGL_EXT_image_dma_buf_import_modifiers` and their
entry points. Missing support fails the requested check. The output records
fourcc, modifier, stride, offset, GLES texture allocation and `glFinish` sync.
That allocator may choose a non-linear layout that this first probe refuses;
its refusal does not establish that the renderer lacks all DMA-BUF support.

The test fixture transports drawn pixels through a real memfd and checks the
actual import attribute ABI, ownership, readback and cleanup. Missing draw or
image binding fails. A separate source mutation exercises the texture/FBO draw
on real software Mesa with DMA-BUF explicitly NOT RUN. Neither a memfd nor
that mutation proves real DMA-BUF operation. GBM allocation, cross-context or
cross-process sharing, tiled modifiers, native-fence synchronization of shared
pixels, KMS scanout and A660 hardware require separate qualification. No phone
operation is authorized by this component.

References: [MESA export and four-plane query ABI](https://registry.khronos.org/EGL/extensions/MESA/EGL_MESA_image_dma_buf_export.txt),
[EGL DMA-BUF import](https://registry.khronos.org/EGL/extensions/EXT/EGL_EXT_image_dma_buf_import.txt),
[explicit modifiers](https://registry.khronos.org/EGL/extensions/EXT/EGL_EXT_image_dma_buf_import_modifiers.txt).
