# Native-fence export and status probe — 2026-09-12

Added an explicit `--native-fence` option to the existing GLES probe. After
drawing it creates an EGL native fence, flushes, exports the owned descriptor,
waits up to one second and requires Linux `SYNC_IOC_FILE_INFO` status **1**.
It closes the exported FD on every path and checks producer-sync destruction
before pixel readback and PASS. Plain mode reports `native_fence=NOT RUN`.

Pinned Denial's Flutter renderer uses create/flush/export and treats export
failure as fatal. The [extension contract](https://registry.khronos.org/EGL/extensions/ANDROID/EGL_ANDROID_native_fence_sync.txt)
defines descriptor ownership and flush-before-export. The pinned kernel's
`sync_file_poll()` reports readiness for signaled fences, including error
completion; its status ioctl distinguishes successful completion. The probe
therefore rejects readable error fences, active status, ioctl failures and
non-sync-file descriptors. Interrupted polling retains one original deadline.

**Actual native-fence capability is BLOCKED on both software fixtures:** native
llvmpipe and ARM64 Arch softpipe lack `EGL_ANDROID_native_fence_sync`. Both
requested checks exit nonzero without a PASS receipt. No ordinary EGL fence or
CPU completion is substituted. A660 remains **NOT RUN**.

## Identity and evidence

Started at `d882719688373576eed4fa5e3e6c8f5d39a0a777`, tree
`14c2b936ad2ee85d5050e99bb5b55a8e6c5b0b7e`. Executable source was frozen at
`f2f6f7981714c7eb24a8028acfb6c91d368ad262`, tree
`263a39a7e14dcd513af2ea91a12996ccd165dc56` before integrated tests/builds.

Identical unsigned ARM64 twins are 4,658,448 bytes, SHA256
`9f93abfad3b8b0e7861b679999c921d05ae37ea6df7ded67812592d1c4cdef7c`.
The [qualification receipt](2026-09-12-native-fence-qualification.json) records
commands, tool/build identities, runtime bindings and separate capability
results. Raw logs and exact runtime evidence remain private under
`rog5-native-fence-evidence-20260912-r1`. The prior 369-path library fixture is
unchanged and verified; new results bind the new executable to those bytes.
No package download or kernel rebuild was needed.

| Check | Result | Seconds |
|---|---|---:|
| New option test before implementation | Expected FAIL: unsupported option | 1.707 |
| Focused tests, Python `-O` | 9 groups PASS | 5.064 |
| Selected actual ARM64 executable tests | 6 groups PASS | 3.979 |
| ARM64 loader / plain software rendering / A660 refusal | 3 checks PASS | 0.032 / 0.966 / 0.817 |
| Native software requested fence | BLOCKED: extension absent | 0.165 |
| ARM64 software requested fence | BLOCKED: extension absent | 0.966 |
| Frozen active tier | 83 PASS, 0 FAIL, 0 BLOCKED, 0 suites SKIPPED, 256 NOT_SELECTED | 122.002 |

The active tier separately records three declared optional **subchecks** skipped.
It tests implementation and fixture behavior; it does not run a real native-fence
producer successfully. The two capability blockers above are preserved as
BLOCKED, not included in the active-tier PASS count. `ROG5_LINUX_SOURCE` was
unset. No GitHub CI run is claimed.

New cases cover ordering, extension-token matching, missing export symbol,
creation/flush/export errors, timeout, interrupted poll, poll error flags,
ioctl failure, active/error status and sync destruction failure. Eventfd,
polling and FD closure are real. EGL and sync-file ioctl boundaries are controlled
by an LD_PRELOAD fixture in the no-DRI namespace. The C fixture uses Linux's
actual sync-file header, so the Rust ioctl number/layout are exercised on native
and ARM64 ABIs. It aborts if the exported descriptor is still open when the
producer sync is destroyed. This is a bounded executable fault test, not a
claim that eventfd is a GPU fence.

Previous pixel, GLES-version, mode, timeout, Rust unit and native no-draw mutation
tests still pass. All waits have an external process deadline in addition to the
one-second poll deadline, because EGL/driver calls can themselves block.

## Preservation and next step

All 456 prior artifact sets and historical reports remain unchanged. Only current
GPU fixture pointers advance. Board/module/DT, signed candidate, installed/runtime
and fallback pointers, acceptance contracts and full mobile package graph remain
unchanged. The new fixture grants no admission, signing or execution authority.
Final metadata/preservation checks and ending commit/tree/file hashes are retained
in private `final-checks.json` and `completion.json`.

The retained board config already has `CONFIG_SYNC_FILE=y` and
`CONFIG_DMA_SHARED_BUFFER=y`; these are source/build prerequisites, not proof of
A660 export. Cross-context fence import, KMS in-fence consumption, DMA-BUF
formats/modifiers/sharing and physical acceleration remain unqualified.

The previous turn made progress on GLES context versions; this turn implements
and tests the native-fence producer/completion boundary. No phone operation,
protected-storage mutation, new candidate, claim or production signing occurred.
Touch stays disabled; S06/R01 stay FAIL and phone physical rows stay NOT RUN.
The next smallest phone question remains a separately authorized bounded 60 Hz
scanout/blank cycle. The native-fence option is prepared for a later admitted A660
trial and does not arm one. Rustfmt/Clippy remain unavailable in the cached builder.
