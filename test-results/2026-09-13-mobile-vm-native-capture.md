# Native/VNC capture comparison — 2026-09-13

**The white editor output is present in Denial's native screencopy as well as
VNC. Visible text editing remains FAIL.** Both the initial and final sequential
capture pairs have byte-identical PNGs. The initial Mousepad title, menus and
empty editor are visible; after the OSK input sequence, the application area is
white and the expected restored `test` is not visible. This narrows the failure
upstream of VNC readback. It does not yet distinguish client pixels, SHM snapshot,
texture upload/cache or composition. No phone operation occurred.

## Source review and identities

The forwarded review concerns repository `410b6935526a977ca727359f23ee43fc4ebe45b2`,
Denial `85b2303e2f09ae7b7b993641f90061a200f03d53` and Smithay
`812bd33259ff58810dadef6086d8385eeac1ca55`. Current patch0001 already contains
strict explicit modifier intersection (`30e296e7`), Invalid-only pool dispatch
(`e709b1c7`) and stored/exported descriptor validation (`1282476b`). The
[allocation regressions](2026-09-12-denial-allocation-contract.md) previously
recorded16 corrected PASS versus10 expected original FAIL. Those historical
results were inspected, not rerun or relabeled here. No duplicate fix was added.

Starting repository commit `aeef98f9ef4a942d27d096c9bfbe969dcd87ef06`, tree
`e1f2862b81df2c9fdf5e6e1ad13724ab20875489`; final executed source
`3fce168222b8ce469ee9f52b7bab9a8e17b1c82a`, tree
`3c5a58408d49fcd4192497a15757a3953350f4dc`. The later evidence commit is separate
from the source used by the successful VM and integrated tier.

The retained native binary remains SHA256
`878ff4c6155279264782523837cf7672273f333a9a45318a7db9cc9fbf7ce19a`, source
`02796f069819b9df2ad11013f69ce3d1ddf39362`; engine remains
`a75c88d8f12d9ec7a24bb107ff9dc0349b6bb2d5b0f18cb4d40b9e54227e9418`, source
`66db5ff08065972bf9cf7e3d2c4b845633170052`. The AOT/runtime, generic VM kernel,
Mesa, GBM flags and synchronization policy were unchanged.

New ARM64 screencopy client SHA256:
`f177b1f523038da2c60f61d7038c6e3209b327e59eee4f1b155868e2f1ccba5e`.
The build provenance records source/XML/generated protocol files, compiler,
linker, scanner, pkg-config, commands, versions and hashes. The exact licensed
XML is retained from wayland-protocols-wlr0.3.12. No full Denial, engine or
kernel rebuild was needed.

The [qualification JSON](2026-09-13-mobile-vm-native-capture-qualification.json)
contains all three exact VM commands/results, both ARM64 build attempts,
focused commands/timings, all90 integrated suite results, capture identities
and explicit visual assessment. SHA256:
`3289dbe1f172922cbb1130c28edc0a2796af6f39125fcf37bc7fa37bea193220`.
Raw evidence remains in private state
`/home/deck/.local/state/rog5-vm-native-capture-20260913-r1`.

## Executed checks

| Check | Result | Seconds |
| --- | --- | ---: |
| ARM64 client build, source99762905 | FAIL: ignored diagnostic write result under Werror | 0.471 |
| ARM64 client build, source520a10e3 | PASS after acknowledging best-effort diagnostic result | 0.385 |
| Production C/real Wayland socket/builder tests, Python -O | 17 PASS | 5.550 wall |
| Native/VNC pairing tests, Python -O | 7 PASS | 0.303 wall |
| Focused prerequisite tests before final additional native case | 22 PASS | 0.204 wall |
| R1 VM, source520a10e3 | FAIL: RCU stall; no capture request/client execution | 120.817 |
| R2 controlled repeat, same source/inputs | FAIL: RCU stall; no capture request/client execution | 120.827 |
| R3 VM, source3fce1682 | Capture/protocol PASS; visible editing FAIL;110 frames/page flips | 102.365 |
| Frozen active tier, including23 prerequisite cases | 90 PASS;0 FAIL/BLOCKED/SKIPPED;255 NOT_SELECTED | 133.865 |

Three declared optional subchecks remain SKIPPED separately from suite counts.
The integrated run used two workers,1GiB/no swap,600-second deadline and388MiB
peak memory. Both shell syntax checks passed. Existing CI results are not
represented as personally executed checks.

After updating evidence/status, five metadata-checker cases pass in0.917 seconds
and eight status cases in0.084 seconds (wall time). Inventory validation passes
in0.090 seconds for498 sets; generated status validation passes in0.040 seconds.
`git diff --check` passes. Exact commands/durations are retained in private
`metadata-result.json`. Both acceptance contracts, the historical current-state
body and all497 prior artifact entries were compared with starting HEAD and
remain unchanged.

R1/R2 record scheduler/timer RCU stalls before native capture ran. The retained
System.map resolves stacks into timer wakeup/scheduler code. The new worker's
request polling originally spawned `sleep` ten times per second; R3 reduced
that to once per second within the unchanged handoff bound. R3 success follows
that change but does not establish the stalls' cause. Both failures remain
retained; there was no kernel, guest memory or renderer-policy change.

## Capture boundary and bounds

The client exercises real wl_shm and zwlr_screencopy protocol callbacks with a
five-second deadline. It accepts one output, validates dimensions/stride/format,
honors Y inversion and writes exclusive RGB PPM output. Host conversion preserves
every pixel. Tests cover protocol versions, real UNIX transport/SCM_RIGHTS,
disconnects, server failure, missing/ambiguous globals, refusal to overwrite,
the actual stalled-server deadline and malformed/oversized output. Missing
mandatory build dependencies fail explicitly.

Only the private `output/native` directory gains a writable guest9p mount;
runtime and payload remain read-only. Host handoff is bounded to8 seconds and
the share is checked against8MiB. Native children join guest cleanup. The VM
retains network-none, only the host render node,1536MiB/no swap,2 CPUs,64 tasks,
8MiB serial bound and120-second harness deadline. All three containers were
removed. The root guest is a fixture, not the intended mobile privilege model.

Initial PNG pair SHA256:
`a00418d730eb8c1e1f13c9d5e093c712fdb7f17fc9779ff1684ac28ea08e2797`.
Final PNG pair SHA256:
`59d0f41f10de668bedd16acaad9a2026d86b5a3600f70e7983730b5e28a1d0db`.
Initial/final native handoffs took0.775/0.755 seconds. The pairs are sequential;
byte equality does not claim matching capture timestamps. The guest delivered
all12 expected key events and reported no rendering errors, but those checks
cannot override the observed visual FAIL.

## Changed files and remaining work

Source/test changes: `scripts/host/build-qemu-screencopy.py`,
`scripts/host/qemu-native-capture.py`, `scripts/host/test-qemu-native-capture.py`,
`scripts/host/test-qemu-screencopy.py`, `scripts/host/test-qemu-virtio-drm.py`,
`scripts/host/test-qemu-virtio-drm-prerequisites.py`,
`scripts/host/test-repository-linux.sh`, `configs/repository-tests.json`,
`.github/workflows/offline-smoke.yml`, `tools/qemu-virtio-drm/guest.sh`,
`tools/qemu-virtio-drm/init.c`, `tools/qemu-virtio-drm/native-capture.sh`,
`tools/qemu-virtio-drm/screencopy.c`,
`tools/qemu-virtio-drm/wlr-screencopy-unstable-v1.xml`, `docs/development.md`.
Evidence/status changes: this report, its qualification JSON,
`docs/development-lessons.md`, `configs/project-status.json`, generated header
in `docs/current-state.md`, `manifests/current-artifact.json` and one appended
fixture in `manifests/artifact-sets.json`. Prior497 sets and historical current
state body remain unchanged.

Visible editing remains the immediate VM blocker. Next, use bounded diagnostic
capture of the actual SHM snapshot and upload/composition boundary, retaining
surface/revision identities and an initial positive control. Do not guess-fix
GL unpack state, cache lifetimes or shell composition from the white image.
The RCU stall cause also remains unresolved. No further VM run was executed.

Phone OLED/touch/A660, suspend/wake, charging and other mobile physical rows
remain NOT RUN. Headless S06/R01 remain FAIL. No phone contact, signing,
candidate generation, admission, claim operation or protected-storage mutation
occurred. Installed bytes were neither queried nor changed.
