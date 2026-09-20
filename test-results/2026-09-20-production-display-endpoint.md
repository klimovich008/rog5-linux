# Production display endpoint and supervised assembly — 2026-09-20

**Offline host tests only. No phone/VM operation, candidate, signing, claim,
target staging or protected-storage mutation.** The previous turn implemented
the production loader and provider/firmware readers. This turn adds the matching
endpoint, exact-source assembly and a draft supervisor adaptation. It does not
issue a deployable or admitted composition.

Starting commit `7b64dabe38b9bf0654823ef566ed16445c4e855b`, tree `cac057579654ebafd73682ee4a8261824b7d2968`.
Frozen implementation `4aab3b48fa5eb289a9c4aa8a8d5eb6fce6a1f826`, tree `8e9a67165a6abd8ed230307c66b632e635126b54`.
Board artifacts and pointer remain unchanged. Linux remains
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`. No kernel, DT, module, Denial or Flutter rebuild was
needed. The tests compile small host extracts of actual panel/DRM/backlight
callbacks; they do not compile or run the phone kernel.

## Implemented behavior

The production endpoint binds boot, release, bundle, descriptor hash, composed DT
hash and owner from the admitted caller. It independently checks local boot and
release, exactly one matching bundle token and stable protected descriptor bytes.
It copies and retains the binding so mutable callback results cannot replace it.
The caller still owns exact-device, signing, health and recovery admission.

Backlight and framebuffer discovery require the exact panel/DPU, driver, DT node
and reciprocal links. The historical framebuffer ancestry check admitted a
matching-looking framebuffer elsewhere under the common MDSS parent. The new
check requires `ae01000.display-controller/graphics/fb0` and the exact msm_dpu
parent. The endpoint's only write is `0\n`: short writes, EPERM, DSI errors,
authorization changes and failed readback remain errors. Metadata or a zero
property never establishes preparation, scanout or optical darkness.

Exact-source inspection used Linux DRM framebuffer-helper registration, MIPI DSI
device naming, device class glue and the current panel's backlight registration.
The observed API relationships support the sysfs paths used here; actual phone
registration is still NOT RUN. The exact core updates the brightness property
before invoking the driver, so a zero property after EPERM is not command success.

The component assembly hash-checks four source dependencies, then executes those
same bytes rather than rereading a path or accepting cached bytecode. It validates
all 14 ordered insertion receipts, fresh provider checkpoints, exact identity,
bounded elapsed times, framebuffer metadata and the two-byte zero receipt.
The loader and supervisor share a pure entry-intent producer, avoiding divergent
definitions of the operation admitted before insertion.

The draft supervisor patch applies to historical backend SHA256
`840ba5ad5c1bfe2059bfc580fb45da4e8f3fef59f8e6627789cfe5ed38904a0d`.
It validates intent before exclusive durable entry, waits for the matching host
acknowledgment, then permits loading. Success requires validated action and
cleanup receipts and both process groups reaped/absent. Cleanup runs in a separate
process. The draft lifetime is 100 seconds around the 85-second loader, with
separate existing cleanup/reap bounds. Historical identity/source pins and entry
barriers remain deliberately incompatible with production deployment.

## Regressions and personally executed checks

Two tests fail against the historical backend: a KeyboardInterrupt after durable
entry and before ACK publishes a false PASS before propagating, and cleanup loses
the worker's structured EPERM diagnostic. Both pass with the patch. The first is
an imported/direct BaseException path; the historical CLI translates its ordinary
SIGINT/SIGTERM into ValueError, so this is not evidence that normal SIGINT produced
that false PASS. Large cleanup diagnostics are bounded and retain a payload hash.
The historical failing control remains retained: 2 FAIL in 0.017s, run with
`python3 -O scripts/device/test-production-display-supervisor.py --before`.

Endpoint tests include actual-source mutation controls: removing the bundle guard
admits duplicate tokens, and removing exact DPU ancestry admits an unrelated fb0.
They cover boot/owner/descriptor changes, symlinks and replacement, bad topology,
write failures and authorization loss. These are semantic fixtures, not hardware
observations or an assertion that a mutable historical artifact was replaced.

The assembled test runs the actual loader, hash-pinned assembly, endpoint and
patched supervisor with 14 real inert insertion children. It checks durable entry
before ACK, no panel before ACK, bounded terminal receipts, separate cleanup PID
and process closure. Its brightness syscall seam invokes compiled actual panel
and core callbacks. Device registration, firmware, sysfs, ownership, identity and
physical effects are substituted explicitly. The assembled case first passed in
0.679s wall time; the final component suite includes it.

| Focused command (`python3 -O`) | Cases | Wall seconds | Result |
| --- | ---: | ---: | --- |
| scripts/device/test-display-endpoint.py | 34 | 0.500 | PASS |
| scripts/device/test-production-display-supervisor.py | 20 | 3.151 | PASS |
| scripts/device/test-display-component.py | 10 | 2.807 | PASS |
| scripts/device/test-load-production-display.py | 29 | 6.090 | PASS |
| scripts/host/test-select-repository-test-tier.py | 37 | 0.851 | PASS |

Earlier supervisor fixture failures (missing owner and a validator return-contract
mismatch) were corrected; before/after-r1/r2/r3 logs remain retained. They are not
rewritten as clean runs. The assembled fixture uses a 5-second lease and 8-second
lifetime for scheduling slack; production 100/3-second constants and budget
arithmetic are checked separately. It is not a 100-second physical observation.

Frozen `scripts/host/test-repository-linux.sh active`:
**121 PASS, 0 FAIL, 0 BLOCKED, 0 SKIPPED suites**,
255 NOT_SELECTED, 212.257s.
Three declared optional historical subchecks remain separate from suite results.
These are local executions, not imported GitHub CI results. The owner limits were
1 GiB/no swap, two CPU quota, 256 tasks, 600 seconds and two test workers; scratch
was disk-backed. No unchanged expensive build was repeated.

[Qualification](2026-09-20-production-display-endpoint-qualification.json), SHA256
`525884d793f86e9022950a8a9b8f8a34af12660e8b8bd256858acc2ede0dcae7`, records exact sources, commands, individual suite durations and log
hashes. Private evidence is in `rog5-production-endpoint-20260920-r1` under the
host state directory.

## Remaining boundaries, in priority order

1. Requalify the outer host transport and admission against the 100-second
   supervisor/14-insertion scope. Its historical 60-second readiness and
   78-second deadline cannot be reused. Preserve global consumed-entry barriers.
2. Qualify exceptional descendant closure. Existing stop logic can reap a leader,
   report a remaining group, then discard its PID before another stop attempt.
   Normal assembled closure passes, but no descendant-leak experiment was run.
   Do not treat that as complete exceptional process containment or solve it by
   blindly signaling a potentially reused process-group ID.
3. Qualify firmware root transitions against the kernel's init_task.fs reader;
   PID1/userspace root matching and exact file hashes alone are insufficient.
4. Only after those host boundaries and explicit hardware authorization, observe
   whether the exact provider/panel path prepares and accepts zero brightness.
   Firmware import/authentication, probe, scanout, darkness, GPU acceleration,
   touch and all current mobile physical rows remain NOT RUN. S06/R01 and earlier
   Denial VM failures remain FAIL. No Ready is requested.

The smallest next authorized experiment is an offline transport/descendant
failure fixture around this assembled owner, preserving its original error and
one-use record. It needs no new kernel, candidate or phone operation.

Changed implementation files:

- `configs/repository-tests.json`
- `patches/display-controller/0002-production-supervisor.patch`
- `patches/display-controller/README.md`
- `scripts/device/display-component.py`
- `scripts/device/display-endpoint.py`
- `scripts/device/fixtures/display-loader/backend-before.py`
- `scripts/device/load-production-display.py`
- `scripts/device/test-display-component.py`
- `scripts/device/test-display-endpoint.py`
- `scripts/device/test-production-display-supervisor.py`
- `scripts/host/test-repository-linux.sh`

## Metadata and preservation checks

- `python3 scripts/host/check-mobile-status.py`: PASS, 0.041s.
- `python3 -O scripts/host/test-mobile-status.py`: PASS, 0.088s.
- `python3 scripts/host/check-artifact-inventory.py`: PASS, 0.084s.
- `git diff --check`: PASS, 0.013s.

Eight status regressions passed. Inventory validation retained 595 sets; large
and private artifact-byte revalidation remains NOT RUN. Ten preservation checks
confirmed unchanged artifact inventory/pointer, headless/mobile acceptance,
historical current-state body, original loader ordering patch/fixture, and the
sealed private loader/backend source hashes. Integrated service exited cleanly;
peak memory was 308.9 MiB and swap was zero. No phone operation occurred.

Metadata files changed: `configs/project-status.json`, `docs/current-state.md`,
`docs/development-lessons.md`, this report and its qualification JSON. Ending
metadata commit/tree and the complete changed-file list are retained privately
in `rog5-production-endpoint-20260920-r1/end.json` to avoid a self-hash cycle.
