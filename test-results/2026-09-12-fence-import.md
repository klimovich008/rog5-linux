# Native-fence consumer preparation, 2026-09-12

Added optional `--native-fence-import` to the Rust GLES readback probe. It exports
the producer fence, duplicates/imports its FD in a second unshared GLES context,
queues a server wait, then exports and checks a consumer completion fence. It
restores the producer before pixel readback. All requested teardown must succeed;
restoration failure avoids GL object deletion in the wrong context. This prepares
one Denial synchronization boundary. It does not establish buffer sharing,
unsignaled-dependency ordering, A660 rendering, or phone qualification.

Starting commit `57b7cd577919bcee7deb71283c4d44fb989894d2`, tree
`185144463a13aa32bbc0cb8d847b21f0e2bc7e4c`. Compiled source is frozen at
`ea638a8aef0f5cafcecc0f54a923dfd7db7eda2e`, tree
`c32e4b658ee34d0c5be3bc472caef51276b5d753`. Subsequent edits only record qualification.
No change to Linux `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` or its retained board outputs.

The two independent ARM64 builds are identical: 4,659,224 bytes, SHA256
`a815ce5f62f53c78319db3dde625007fd6217537a2ee9f7330fe3cb45badc073`.
They use the cached Rust 1.98 builder image
`0f429c6fd38e4400d8638bff1f7da0170375275ab29201e327a3e236ed9df16d`.
No target image, candidate or production signature was created.

| Executed check | Result | Seconds |
|---|---|---:|
| New import test against old source | Expected FAIL: option refused, exit 2 | 1.911 |
| First focused implementation run, 10 groups | PASS | 6.862 |
| Final focused run with additional FD/status cases, 10 groups | PASS | 6.812 |
| ARM64 optimized builds A / B | PASS; byte-identical | 1.167 / 1.167 |
| Native optimized / debug unit compilation | PASS | 1.017 / 0.615 |
| Debug Rust units / ARM64 ELF inspection | PASS | 0.004 / 0.008 |
| Native plain software pixels | PASS | 0.165 |
| ARM64 fixture suite, seven groups | PASS | 6.472 |
| Actual ARM64 loader / Arch softpipe pixels | PASS | 0.032 / 0.966 |
| Actual ARM64 refusal of software in A660 mode | PASS | 0.666 |
| Actual native software native-fence import | BLOCKED: extension absent | 0.165 |
| Actual ARM64 software native-fence import | BLOCKED: extension absent | 0.967 |
| Frozen active host tier | 83 PASS, 0 FAIL, 0 BLOCKED, 0 whole-test SKIPPED, 256 NOT_SELECTED | 120.294 |

Three declared optional subchecks were SKIPPED, separate from whole-test counts.
The two real capability BLOCKED results are separate from the integrated tier.
The before result proves a new capability was absent, not a defect in the old
export-only contract. No GitHub CI run or kernel rebuild is claimed this turn.
Rustfmt/Clippy are NOT RUN: absent from the cached builder.

The actual executable is exercised through the controlled C ABI fixture on
native and ARM64 Linux. It checks context separation, FD duplication/ownership,
server wait ordering, consumer completion, pending/negative status, import and
teardown faults, failed context restoration, real descriptor exhaustion, and
external termination of a stalled server call. Actual eventfd/poll and descriptor
closure are used, but EGL and sync-file status are controlled. Fixture PASS is
not a real native-fence result. The producer may already be signaled even on a
future successful real run; shared-buffer visibility needs separate testing.

Commands and per-build identities are in the
[qualification JSON](2026-09-12-fence-import-qualification.json). Private raw logs,
command records, JSON/JUnit summaries, runtime binding and completion receipt are
under `/home/deck/.local/state/rog5-fence-import-evidence-20260912-r1`.
Focused command: `TMPDIR=E RUSTC=PREVIOUS_E/rustc python3 -O scripts/device/test-gles-readback.py`;
`E` is that evidence directory; `PREVIOUS_E` is
`/home/deck/.local/state/rog5-native-fence-evidence-20260912-r1`.
`python3 -O E/test-arm64.py`, `python3 E/check-runtime.py`,
`python3 E/run-mesa.py` and `python3 E/check-capability.py` produced target evidence.
`python3 E/run-active.py` ran the public active tier with two workers, a 3 GiB
memory limit and no swap. The cached compiler wrapper is byte-identical across
both evidence directories. No host package installation or download was needed.

Changed source/test files: `tools/a660/rog5-gles-readback.rs`,
`tools/a660/test-fake-gles.c`, `scripts/device/test-gles-readback.py`,
`tools/a660/README-gles-readback.md`. Qualification changes:
`configs/mobile/trial-plans.json`, `configs/project-status.json`,
`docs/current-state.md` (generated header only), `docs/development-lessons.md`,
`manifests/artifact-sets.json`, `manifests/current-artifact.json`, this report and
its qualification JSON. All 457 previous artifact sets are preserved. Only the
GPU probe/runtime pointer fields advance; historical runtime execution is not
inherited. The 369 retained library entries are checked for bytes, regular-file
modes and symlink targets before real Mesa execution.

The first private library verifier incorrectly required a mode field on symlink
records and stopped. The separate ABI run still executed and passed; real Mesa
execution followed corrected successful verification. This was a preparer schema
error, not runtime-library corruption. The corrected script now gates subsequent
Mesa execution with fail-fast command dependencies.

Implementation matches pinned Smithay `812bd33259ff58810dadef6086d8385eeac1ca55`
`src/backend/egl/fence.rs` import/wait ownership behavior and the
[Khronos native-fence](https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_native_fence_sync.txt)
and [server-wait](https://registry.khronos.org/EGL/extensions/KHR/EGL_KHR_wait_sync.txt)
contracts. Exact source hashes are retained in qualification.

Open boundaries: GBM/DMA-BUF allocation, format/modifier selection and shared-pixel
visibility; real A660 import/server waits; KMS consumption; stable OLED and touch.
The full mobile package graph remains unchanged. All phone physical rows are
NOT RUN. Historical S06 and R01 FAIL remain unchanged. No phone contact, hardware
operation, claim/admission/signing action or protected-storage mutation occurred.
The next smallest physical experiment remains separately authorized bounded
corrected-display scanout/blank; no session is armed. Offline buffer-sharing
preparation can continue independently.
