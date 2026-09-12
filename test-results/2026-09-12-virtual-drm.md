# Offline virtual DRM and Denial startup

The generic ARM64 guest now boots the retained Arch runtime, discovers a virtual
DRM connector and executes the actual Denial CLI. Full shell startup is still
blocked: the pinned Denial starts Xwayland unconditionally, but the authenticated
315-package runtime omits its executable. The new prerequisite check catches
this before another VM starts. No rendered shell frame or phone result passed.

Starting source: `f683be4b9dfdae063e9478600df10f6ab4a5852b`, tree
`14046581b833151fdc4a67cffb8ee78b5953bee1`. Implementation commits are
`8c68dd99932e6d3bcd0704a929967b6f42af4ad0` and frozen
`b63aa1671bec8fda2352d66f16ca25c18b8223aa`, tree
`dbd90d1d2c7e3d989ccd71dd617a2520f5042e4b`, on
`agent/review-correctness-20260912`. The original dirty checkout is untouched.
The old external review commit was not restored; prior repairs remain intact.

The existing QEMU kernel builder now accepts a separately identified
`virtio-drm` profile, verifies all required resolved symbols, and defaults to two
workers. Its normal smoke profile remains available. The new freestanding guest
init and bounded Python runner mount only explicit, read-only runtime/payload
shares. Guest writes go to RAM. There is no host GPU, block device, USB or network
access. A guest marker refuses accidental host invocation. The full-shell mode
uses a separate seatd lifetime and external timeout; process exit alone is never
reported as rendered-frame evidence.

| Executed check | Result | Seconds |
| --- | --- | ---: |
| Initial container build preflight | FAIL: linked worktree Git metadata not mounted | 0.616 |
| Exact upstream guest kernel build after mount correction | PASS | 631.055 |
| Existing QEMU smoke contract and configuration counterexample | PASS | 0.346 combined |
| Guest script invoked outside the marked VM | Expected refusal, PASS | 0.004 |
| Old kernel with new guest init | Expected FAIL at unsupported 9P root mount | 1.322 |
| New kernel, legacy Virtio transport | FAIL: no DRM card | 1.718 |
| Same kernel, modern Virtio transport | DRM discovery PASS; Denial diagnostic FAIL: no active mode | 3.119 |
| Full shell preparation, unsupported seatd option | FAIL | 10.130 |
| Correct seatd invocation, missing X11 socket directory | FAIL | 5.324 |
| Socket directory prepared | Wayland socket created; FAIL at missing Xwayland | 4.125 |
| Final guest discovery and actual Denial CLI | PASS, clean guest shutdown | 2.720 |
| Missing/present shell and base runtime prerequisite selections | PASS, one test/four assertions | 0.002 |
| Frozen repository active tier | 87 PASS | 131.982 |
| Final metadata checker regressions | 19 PASS | 2.647 |

The active tier has 0 FAIL, 0 BLOCKED, 0 SKIPPED suites and 255 NOT_SELECTED.
Three explicitly declared optional artifact subchecks were skipped; their
identities and exact per-suite commands/durations are retained in its JSON and
JUnit summaries. These are personally executed local results, not imported CI.
The final full-shell prerequisite invocation is separately **BLOCKED** on
`usr/bin/Xwayland`, with `vm_started=false`; it is not a passed shell test.
The earlier QEMU capability query also failed because it requested Clang from
the QEMU-only container. The corrected query separates these tool environments.

The precise transport counterexample is the pinned Linux
`virtgpu_kms.c` and `virtio_input.c` requirement for `VIRTIO_F_VERSION_1`.
The retained QEMU reports `virtio-mmio.force-legacy=true` by default. Setting it
false makes both driver types probe without rebuilding the kernel. The old
configuration lacks all nine checked DRM/input/9P prerequisites; the resolved
new configuration retains them. Actual driver objects and the final Image exist.

Denial revision `85b2303e2f09ae7b7b993641f90061a200f03d53` deliberately
requires an existing mode for bounded diagnostic restoration. Its normal
UntilLogout path supports inactive CRTCs. The latter reached portal IPC, keyboard
keymap initialization, output creation and Wayland socket creation before the
unconditional `XWayland::spawn(...)?` call failed. Creating a Wayland socket does
not establish a functioning compositor session. Earlier fatal-error cleanup also
logs duplicate DRM-master drop errors; those diagnostics remain unresolved.

| Exact artifact | SHA-256 |
| --- | --- |
| Guest Image, pristine Linux `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` | `34279d12dee925c4c58de9f49411c5e5f9fe85d016214e3939f80cd2f8b797f9` |
| Resolved guest configuration | `2fb657ae7d113f72d62c5e0238f974747577e8547cee6fb6d0ca025fd233b251` |
| Actual ARM64 Denial binary | `8698b0716c0ab16ab5c33d618ae52cef0cd8c0966ad356cf2ca49d78a0ba8591` |
| QEMU executable, version 8.2.2 | `b511b60cc31479b71dfdd589e6c981ae37b20ef0e75adc5a57bb0d6737e9b30c` |

The guest release is `7.1.4+`; its required drivers are built in. There are no
phone patches or guest modules in this build. Linux source stays clean. Clang
and LLD are 18.1.3 in the retained kernel-builder container. Full commands,
container IDs, build-input/tool hashes, guest logs and generated initramfs hashes
are bound by [qualification JSON](2026-09-12-virtual-drm-qualification.json).
The package tree and shell fixture are linked to their prior authentication and
assembly receipts; this runner does not claim to reauthenticate the whole tree.

Changed implementation files are the existing QEMU builder, new guest runner,
guest init/script, executable prerequisite regression, repository test manifest
and selector. Development instructions explain both modes. Current status and
the current-artifact pointer reference this receipt; the artifact inventory adds
one fixture set while preserving all 481 prior parsed entries and all historical
current-state text. The source fixes are not installed on the phone.

Next, authenticate an explicit Xwayland/dependency extension using the retained
repository snapshot and trusted package signer, then test it with the same
kernel and complete shell fixture. Do not mutate or relabel the old 315-package
graph. EGL/GBM, shell rendering, compositor input and teardown remain separate
unresolved boundaries. No new phone kernel or Flutter build is needed to answer
this next runtime question.

No phone contact, power operation, flashing, signing, admission, claim, protected
storage mutation or new phone candidate occurred. ASUS rescue, signed candidate
and fallback identities are unchanged. S06/R01 remain FAIL. All physical display,
touch, GPU, charging and suspend trials remain NOT RUN; the existing trial plans
require separate phone-operation authorization.
