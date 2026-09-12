# Offscreen GLES shader/readback component

`rog5-gles-readback.rs` renders one 4×4 GLES2 fullscreen triangle, verifies all
64 RGBA channels to one quantization unit, and completes EGL cleanup before
publishing PASS. It requires EGL 1.5, `EGL_MESA_platform_surfaceless`, an RGBA8
pbuffer configuration and the runtime `libEGL.so.1` / `libGLESv2.so.2` libraries.
It uses no Rust crates or development GL headers. For example, compile offline:

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

Every result keeps physical acceptance, scanout and buffer sharing NOT RUN.
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
