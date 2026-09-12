# Non-wakeup touch sleep implementation — 2026-09-12

The FTS3658U prototype now has ordinary system-sleep callbacks. The old callback
deliberately refused every suspend; a successful-suspend regression fails against
those exact old bytes. Suspend now drains IRQ activity, releases contacts and
releases its power votes. Resume repeats the existing power and normal `5652`
identification sequence before enabling input. Nine existing power, packet,
probe and shutdown functions remain byte-identical.

This advances the driver implementation, not phone qualification. The DT stays
disabled. Physical touch, suspend/resume, rail retention and idle drain remain
**NOT RUN**. Touch cannot wake the phone; gesture wake and runtime PM are not
implemented. Hibernation is explicitly refused. No phone operation, signing,
claim, candidate, module loading, installation or protected-storage mutation
occurred. ASUS slot A, signed fallback, installed/runtime pointers, accepted
headless baseline and historical S06/R01 **FAIL** results remain unchanged.

## Correctness and error handling

Exact Linux 7.1.4 `device_suspend()` marks a device suspended only after its
callback succeeds. `device_resume()` skips a device whose suspend failed.
Failed-suspend restoration must therefore happen inside the driver callback.
If a GPIO off operation fails but both regulator votes were released, the driver
attempts one normal power/ID restoration and still returns the original error.
It never attempts restoration after UNKNOWN regulator ownership. Failed
restoration or resume leaves touch quiesced and refuses later PM retries;
shutdown while asleep cannot restart it.

The actual callback table is tested, including freeze/poweroff/restore refusal.
This avoids the generic sleep macro's automatic hibernation mappings. Ordinary
callbacks preserve ordering with GENI's adapter suspend/resume in the noirq
phase. The PM dispatch observation is a precise source counterexample, not
execution of the complete PM core. The harness executes the actual driver,
IRQ-disable and multitouch extracts with controlled hardware boundaries.

An independent source review found no new ordering or ownership defect. A
separate packet/input review disproved a missing `BTN_TOUCH` concern: the exact
input core supplies it for `INPUT_MT_DIRECT`. No redundant driver code was added.
The fixture still does not verify actual evdev/libinput delivery.

## Identity

- Starting commit: `254e81380d932ce45225c9291bb4da1d2cf1bb9e`.
- Starting tree: `07c5f5fbf0af6cda1090de11173e659cfa2ba81e`.
- Frozen source/build commit: `034ef34cd2f4551130ef9b8b3f521ba71ceb1acd`.
- Frozen tree: `e8d6ce7b7aad72c6704903b048449a567c3327d0`.
- Pinned Linux: `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`, v7.1.4.
- Driver SHA256: `d2ff4063df516a316b3716c841b99d82643474bfc07c63a946cdb8bed706c59f`.
- Config SHA256: `277bc74e104bcdec8e6eda8a345e2a4e7bb15be5118bb829741742e97d8a174c`.
- Identical 17,448-byte twins: `0a191f48fccfebbe08902e25ba63127b2e86c2a60d727234b53a1e8f83c9b59f`.
- Vermagic: `7.1.4-rog5-production SMP preempt mod_unload aarch64`.

The [qualification receipt](2026-09-12-touch-sleep-qualification.json) records
commands, tools, source/kit distinctions and proof hashes. The
[current pointer](../manifests/current-artifact.json) selects this unsigned touch
fixture separately from unchanged board and signed artifacts. The prior
16,544-byte prototype remains retained. Ending commit/tree and every changed-file
hash are recorded after the metadata commit in private `completion.json`.

## Executed checks

| Check | Result | Seconds |
|---|---|---:|
| Old driver with successful-suspend regression | Expected FAIL | 0.515980 |
| Actual lifecycle callbacks and exact-source comparison | PASS: 24 groups, six mutations | 4.106083 |
| Lifecycle suite without external source | PASS; external comparison NOT RUN | 4.106932 |
| Protocol/disabled-DT checks, Python `-O` | PASS | 0.438151 |
| Actual regulator-core faults with exact source, Python `-O` | PASS | 0.645688 |
| Kernel checkpatch on driver diff | PASS: zero errors/warnings/checks | 0.275568 |
| Twin A W=1/modpost build | PASS | 2.610 |
| Twin B W=1/modpost build | PASS | 2.560 |
| Twin orchestration, input and ABI checks | PASS | 6.394269 |
| Frozen-source active tier | 82 PASS, 0 FAIL, 0 BLOCKED, 0 suites SKIPPED, 256 NOT_SELECTED | 109.009398 |
| Final metadata, status, inventory, links and preservation checks | PASS | 0.366147 |
| Corrected series-label bindings and inventory | PASS | 0.098690 |

Lifecycle coverage includes 20 sleep cycles, in-flight IRQ drainage, stale-slot
release, both GPIO off failures, both regulator off failures, eight initial
resume errors, failed-resume cleanup with UNKNOWN ownership, three failed
restorations and shutdown while asleep. Distinct suspend `-EIO` and restoration
`-ENODEV` verify original-error preservation. Six mutations reject skipped
identification, retained resume eligibility, missing failed-suspend restoration
and the three existing unsafe behaviors. Physical effects remain fixtures.

The active tier records three declared optional **subchecks** skipped; no whole
suite skipped. JSON and JUnit receipts are retained. `ROG5_LINUX_SOURCE` was unset
for that tier; explicit exact-source lifecycle/regulator checks ran separately.
Focused checks used working bytes subsequently frozen by hash. Module builds
and the integrated tier ran from the clean frozen commit.

All 31 imports resolve against pinned `Module.symvers`; the only new import is
`enable_irq`. There are no module dependencies or firmware requests. The read-only
kit preserved 760 checked files. All 740 consumed inputs were covered, including
698 source files within the 715-file fresh-source comparison. No Image, DT/schema
rebuild, guest module load or remote CI was run. The unchanged production board
qualification and historical Q6 schema FAIL remain distinct.

Final review corrected a series label: Q6's qualification records `1544f250…`,
the later incremental production qualification records `b027af87…`, and current
source records `6ecab159…`. These are now separate fields. Q6's compiled/final
patch delta remains in its immutable receipt; matching consumed touch headers
does not mean the retained kit was rebuilt with the current complete series.

The builder was unchanged. First private preflight rejected an unrelated panel C
input imported from a broader inventory, before compilation. The corrected
preflight uses touch dependencies and build controls; both receipts are retained.
Tool records distinguish PATH-selected host Python from Q6's bundled Python.
Child execution tracing was NOT RUN. Builds used two jobs sequentially in a
1.5 GiB/no-swap scope; the active tier used two workers in a 3 GiB/no-swap scope.
More than 7.5 GB of host disk remained free. Full arguments, logs and durations:
`/home/deck/.local/state/rog5-touch-sleep-evidence-20260912-r1/`.

## Remaining limits and next experiment

UNKNOWN ownership or failed restart still needs independent recovery. Inhibition
lasts only for the current instance; it does not survive rebind or prove physical
restoration. L8C's upstream supply, runtime GENI mode and DMA ownership, normal
hardware ID/input events and actual wake behavior remain unresolved. All 28 mobile
physical rows remain **NOT RUN**.

The next smallest hardware experiment remains one bounded 60 Hz scanout/blank
cycle after separate exact-artifact composition and execution authorization.
Touch stays disabled for that display question. A later touch/sleep trial must
first establish provider, power, identity and independent wake/recovery
prerequisites. No Ready prompt or test arming occurred.

## Changed files

- `tools/rog5-fts3658u/rog5_fts3658u.c`
- `tools/rog5-fts3658u/README.md`
- `scripts/device/test-rog5-touch-lifecycle.py`
- `scripts/device/fixtures/fts3658u/cases.c`
- `scripts/device/fixtures/fts3658u/stubs.h`
- `configs/mobile/trial-plans.json`
- `configs/project-status.json`
- `docs/front-touch-prototype.md`
- `docs/current-state.md`
- `docs/development-lessons.md`
- `manifests/current-artifact.json`
- `manifests/artifact-sets.json`
- `test-results/2026-09-12-touch-sleep-qualification.json`
- `test-results/2026-09-12-touch-sleep.md`
