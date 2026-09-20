# FTS3658U input-handler boundary — offline companion regression

Repository baseline: `1e13857a766e973edad77c95fd39fc83a6230bc7`.
Linux v7.1.4 source: `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`.

This is an additive host regression, not a driver change or a replacement for
`test-rog5-touch-lifecycle.py`. The previous 27 cases / 8 mutation controls remain
unchanged, with their historical evidence. They are not rerun by this command.
No module, phone, root, USB, network, DT, signing, candidate, admission, claim,
production artifact or rescue/headless baseline operation is performed.
Physical touch and the provider/rail/cleanup qualification gates remain NOT RUN
or unresolved exactly as before. Synthetic successful ID reads are fixture
inputs, not observations of a normal-mode controller ID.

## Confirmed gap and the changed observation point

The old `stubs.h` defines `input_event()` to update fixture state and immediately
append capability-filtered requests to `input.events`. It aliases
`input_handle_event` to that function. Thus exact MT helpers were running, but
input.c's state-change filtering, slot staging and batching were absent. For
example, the old tests expect one repeated tracking-ID request on a move; a
handler must not receive that unchanged value.

The new runner removes that entire API sink and its alias from the generated
translation unit, without editing the retained source file. It reuses the
hardware/devres fixture definitions, actual driver functions through the PM
callback table, the existing 14 exact MT/IRQ extracts, and existing C helper
functions. The original C test main is renamed and never called. The legacy log
fields remain only so the unused legacy functions compile; no new oracle reads
them and nothing appends requests to them.

The event path executed by the new cases is:

```
production probe / IRQ / release / suspend / resume
  -> exact input_report_abs / input_sync / input_mt_* helpers
  -> exact input_event
  -> exact input_handle_event          <- also called directly by DROP_UNUSED
  -> exact input_get_disposition / input_handle_abs_event
  -> exact input_event_dispose
  -> exact input_pass_values
  -> handle->handle_events
  -> input_handler.events = observe_events
```

`observe_events()` has the pinned unsigned-count return signature. It is the
only producer of the delivered log, copies the borrowed values before reuse,
and returns count. The exact `input_handle_setup_event_handler()` chooses this
callback from the actual handler structure. An ungrabbed, open handle is placed
on the fixture's immutable ordered list. The production `input_pass_values()`
body traverses it, checks `open`, and invokes the callback. This is not a fake
`input_pass_values()` function that forwards each API request.

## Exact source and deliberate substitutes

A supplied packet or local retained Linux source is mandatory. No source is
fetched and there is no source-less fallback. `source-pins.json` retains hashes
from the packet manifest. Packet mode authenticates the entire packet and all
19 sections, not merely their links. With `--packet-manifest`, that supplied
manifest's identities and complete section-pin list must match as well.
Local-source mode hashes nine complete input source/header files and compares
only the complete `disable_irq` body from manage.c; it does NOT claim that the
omitted remainder of manage.c was supplied or independently authenticated.
The repository files from the packet must still match the review baseline.
This deliberate baseline pin must be explicitly reviewed when those files change.

The generated, unmutated unit is checked to contain each of 32 exact function
bodies exactly once. Whitespace inside copied bodies is not normalized:

* The original 14 are disable_irq; six MT header inlines (get/set value,
  active/used, new tracking ID, slot); and copy_abs, slot initialization, finger
  count, pointer emulation, slot-state reporting, drop-unused and frame sync.
* The 15 new input.c bodies are is_event_supported, input_defuzz_abs_event,
  input_start_autorepeat, input_stop_autorepeat, input_pass_values,
  input_handle_abs_event, input_get_disposition, input_event_dispose,
  input_handle_event, input_event, input_set_abs_params,
  input_handle_events_default/filter/null, and input_handle_setup_event_handler.
* Three new inlines are input_report_abs, input_sync, and input_is_mt_value.

The exact accessor-generating macro and `val` invocation are taken from input.h,
not reimplemented from memory. The exact input_value, clock enum, input_absinfo,
input_mt_slot, input_handler and input_handle declarations are extracted too.
`types.h.in` is expanded automatically by the runner, not a file needing manual
placeholder replacement. The entire pinned input-event-codes.h is written to
scratch and included instead of the host's Linux event-code header. Other input
constants, including BUS_I2C, come from the supplied source. The old fixture's
BUS_I2C placeholder value 1 becomes the pinned 0x18 in this generated unit only;
no device-ID matching is claimed. The exact existing sign-compare pragma around
input_mt_init_slots is retained; warnings elsewhere remain errors.

Boundaries intentionally NOT replaced with whole kernel infrastructure:

| Boundary | Substitute and limit |
| --- | --- |
| I2C, GPIO, regulators, IRQ control, devres, sleeps | Original fixtures. No new hardware qualification or real timing. The new cases are serial, even though pthread-backed IRQ-drain helpers remain compiled. |
| input_dev and MT allocation | Reduced host input_dev representation; matching scalar types for the exercised fields; ten fixed slots; fixed zeroed absinfo and event storage. No kernel layout/ABI or slab ownership claim. |
| input_alloc_absinfo | Checks that the preallocated array exists; exact input_set_abs_params updates it. Allocation failure remains outside this new semantic boundary. |
| registration/open/list insertion | Fixture sets EV_SYN, attaches one open handler and runs the exact callback selector. No actual input_register_device/handle, open_device, sysfs or device core execution. |
| lists and RCU | Bounded ordered host array; a single lexical scoped_guard iteration with break support; direct pointer dereference. No intrusive-list, concurrent traversal, RCU lifetime, filter ordering, grabbing or grace-period qualification. |
| spinlock guard/lockdep | Existing no-ops. No lock safety proof. |
| bit operations | Explicit serial host bit arrays and OR/XOR operations. No kernel atomics, barriers or architecture bitops proof. |
| timers | EV_REP remains unsupported. Exact autorepeat helpers are compiled; arming/deleting a timer fails closed. The timer_delete name is mapped to a host fixture to avoid the unrelated libc timer_delete(timer_t) declaration. |
| timestamps/randomness | Only ktime_set(0,0) invalidation is supported; entropy collection is a no-op. No clock-generation or timestamp accuracy claim. |
| event capacity | Normal capacity is an explicit 128-value fixture choice, not input_device_tune_vals's production result. The capacity case injects max_vals=8 and executes the real synthetic-flush branch. |

There are no missing generic bytes essential to this deliberately bounded scope.
Exact generic traversal or locking would be a different claim. Before making
it, inspect the retained Git object for these precise dependencies rather than
inventing their contents:

```
LINUX_COMMIT=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
# GIT_OBJECT_STORE must be an existing local Git repository, not the .git-less export.
git -C "$GIT_OBJECT_STORE" grep -n \
  -e list_for_each_entry_rcu -e rcu_dereference -e scoped_guard -e 'guard(' \
  -e spinlock_irqsave \
  "$LINUX_COMMIT" -- include/linux/rculist.h include/linux/list.h \
  include/linux/cleanup.h include/linux/rcupdate.h include/linux/spinlock.h
```

The precise symbols needed here are list_for_each_entry_rcu, rcu_dereference,
guard(spinlock_irqsave), scoped_guard(rcu), and lockdep_assert_held. Exact slab
cleanup would also require the definitions/dependencies of __free, no_free_ptr
and kzalloc_flex; it is unnecessary for the fixed allocation boundary. The
included input-core-private.h establishes the real input_handle_event signature.
input-compat.h and input-poller.h are supplied and hashed but their paths are not
executed. evdev.c and libinput are intentionally not part of the claim.

## Semantic cases

All event contents, counts and callback boundaries are asserted from the callback
log. Consumer slot, contact IDs, coordinates and pointer state are reconstructed
only from delivered values, preserving the last delivered slot across batches.
Clearing the observation log does not reset that state or erase pending core
values. Assertions use CHECK/exit, not Python assert or C assert removed by -O.

| Case | Observation |
| --- | --- |
| down-move-up | Full initial slot7 contact, five-value move batch with unchanged tracking ID/BTN/area suppressed, three-value UP batch; ignored UP coordinates cannot escape. |
| unchanged-empty | Empty driver frame and repeated input_sync produce no callback; repeated unchanged contact frames also produce no callback; disappearing contact releases once. |
| delayed-slot | Slot-only, unchanged and unsupported values do not deliver. Changed slot1 data remain queued before SYN even after slot9 is staged; delivered values still belong to slot1. Switching to an unchanged slot7 emits nothing, then a change emits the deferred slot7 selection. |
| multiple | Two contacts share one callback; reversing unchanged records emits nothing; changing one/both contacts yields only necessary slot and axis changes. |
| missing | Absent oldest contact is released through exact input_handle_event calls inside DROP_UNUSED; pointer switches to the surviving contact; last missing contact releases BTN_TOUCH. |
| short-transfer / io-error / invalid-frame | Actual IRQ error paths release exactly two active contacts, not ten fictitious UP events; repeated error with no contacts delivers nothing. |
| suspend | Actual suspend releases both contacts; repeated suspend and successful fixture resume emit nothing; recontact gets a new ID even with unchanged per-slot coordinates. |
| wrap-oldest | IDs 65535, 0 and 1; oldest contact is neither the lowest slot nor first record nor numerically lowest ID. Explicit UP transfers pointer emulation to the survivor. |
| ten-contacts | Exactly one 53-value initial batch for slots0..9, then a 22-value missing-all release batch. No capacity flush at the normal fixture limit. |
| capacity | One actual-driver frame at injected capacity8 produces a seven-value SYN_REPORT=1 batch and a three-value SYN_REPORT=0 batch. A later six-change synthetic batch is not followed by a delivered empty explicit SYN. Guard value beyond injected capacity is unchanged. |
| handler-closed | An already-observed contact moves while the handle is closed without delivery; reopening and repeating unchanged input does not replay discarded values. No evdev open-time state synchronization is claimed. |

Tracking-ID tests cover a bounded 16-bit wrap, not signed INT_MAX overflow or
arbitrarily old contacts spanning half the ID space. Nonzero defuzz settings,
keyboard repeat, handler filters, grabbing, device callbacks, pre-registration
seeding and all unrelated input event families are unqualified.

## Mutation controls

Every paired baseline case must succeed. Each mutant is compiled in scratch and
must exit 1 with a semantic FAIL diagnostic. Compilation errors, timeouts,
signals and UBSan failures are NOT counted as kills. No mutant is written to a
production source file.

Eleven input-core controls remove ABS equality filtering, KEY equality filtering,
deferment of slot-only requests, delayed slot insertion, empty-SYN suppression,
explicit report flushing, correct batching before SYN, handler callback delivery,
open-handle gating, timely capacity flushing, or synthetic SYN value 1.

Seven driver/MT controls remove DROP_UNUSED, error release, stop/suspend release,
the tracking-ID mask, masked postincrement, wrap-aware oldest selection, or
pointer emulation. Error-release and pointer-emulation controls intentionally
exercise the *new delivered boundary*: they are not claims that old controls
were previously ineffective or that the unchanged driver is defective.

The input.c-only controls cannot affect the original request sink because it
never executes those input.c bodies. Their new semantic rejection is the direct
coverage distinction, without rewriting the original 27/8 tests.

## Runner cleanup correction (r2)

Current application target: repository HEAD
`8194bcec4da3fabe5dcd6142db8728e249d4b414`, tree
`c419319d806260456834c091f5e4e5b7628e886d`. The six companion files were
untracked, so an empty `git diff` did not imply their absence. Source pins above
remain the original reviewed byte identities; do not replace them with HEAD.

The supplied GCC15.1.1/Python3.13.5 run passed 13 cases / 18 semantic controls /
32 comparisons in 21.771677065 seconds. These semantics are not rerun for this
runner-only correction. The complete unmutated C unit must still hash to:

`9a4aff51520f8ace82384a26711608dab245250c79c35e97f6ad525c1a5061ad`.

The actual-runner SIGTERM regression then showed runner exit -15, a surviving
sleeping compiler, and surviving disk scratch. Its independent fixture cleaned
and reaped its children. This established a runner defect, not a driver defect.
The original run.py's hardcoded checkout paths must not be used against another
checkout. The r2 regression instead constructs private owned copies.

### Ownership and cancellation

`owned_process.py` is private to this one Linux x86_64 host harness. It requires
one thread, no pre-existing children, and default SIGCHLD disposition. It enables
PR_SET_CHILD_SUBREAPER, exactly as the supplied regression did. There is no
competing waiter or parallel command execution. This is not a generic executor.

SIGTERM, SIGINT and SIGHUP handlers only record the first signal. They never
raise asynchronously during Popen, assignment/registration, reaping, or scratch
removal. Checkpoints in the non-reaping wait loop turn cancellation into failure.
No cancellation signal is blocked across fork/exec; child signal masks are not
changed. Repeated signals cannot escape cleanup or turn cancellation into PASS.

Each command is a new session. waitid(WNOWAIT) observes its exit without reaping
its leader. The leader therefore reserves the PID/PGID until after all group
signals. Cleanup sends SIGKILL immediately (no TERM grace delay) and drains the
entire owned tree. Orphans are adopted; even descendants that changed sessions
are discovered once their parents die. A process group is signalled only while
its leader is our unreaped child. Other adopted children are killed individually,
never through a saved/unowned group number. The command leader is held while descendants drain. Its exit is observed before
a fresh child inventory is checked; a final waitid(P_ALL, WNOWAIT) must report
ECHILD after reaping it. A stale /proc snapshot alone is never a drain proof.
No group is signalled after its leader has been reaped. Start ticks in regression
records are evidence, not the ownership mechanism.

Child discovery normally reads /proc/self/task/PID/children. Hosts that omit that
file use read-only /proc/PID/stat PPID discovery. Every discovered PID is then
validated as our waitable child before signalling. The fallback does not signal
unrelated /proc entries or match processes by names. Permission/ownership errors
fail closed. Source hashes and generic Linux input claims are not expanded by
this host-process boundary.

The cleanup finally runs on normal exit, command timeout, cancellation and an
unexpected exception, including one raised after launch but before Popen returns.
A completed command with background descendants is an infrastructure failure,
even if it printed FAIL and exited 1. No infrastructure error is credited as a
semantic mutant kill. The existing rc==1/FAIL/no-UBSan gate is unchanged.

Only after a proven drain is scratch removed. A failed/timed-out drain marks the
owner dirty and retains scratch with an explicit diagnostic; it cannot be erased
by a TemporaryDirectory finalizer. Command logs are copied to --report-dir after
normal drain or after an exceptional drain attempt. A cancelled command does not
reach the success results.json write. A late cancellation after a completed batch
has written that file still yields nonzero exit; that exit dominates the file and
earlier PASS lines. Always retain the outer exit status with the report.
Retained report directories are evidence, not leaked temporary scratch.

The original 85-second batch, 30-second compile, 5-second case, 384 MiB/process,
8 MiB/file, and 60-second CPU limits remain. A drain is bounded to 2 seconds; a
last outer ownership check may make a second attempt after an unproven drain,
without deleting retained scratch. These are not aggregate memory guarantees.
Uninterruptible kernel waits, exhausted resources, filesystem failures, hostile
fork storms and SIGKILL cannot be made universally recoverable by Python finally.

SIGKILL, os._exit, interpreter crashes and power loss bypass Python cleanup.
The unchanged repository reporter sends TERM and then KILL after only 50 ms;
it can cut short cleanup on a stalled/overloaded host. No guarantee is made for
that forced-kill window. The 85-second internal deadline plus cleanup reserve is
below the proposed 90-second manifest deadline for ordinary bounded execution.
An enclosing user-owned cgroup can bound descendants/memory, but cannot make a
killed Python process remove scratch. Do not remove an unproven retained path
until the exact owned tree is independently confirmed gone.

### Repository interface

The reporter invokes `python3 -O SCRIPT` without argv. The harness now defaults
its source from `ROG5_LINUX_SOURCE` only when neither explicit source option was
given. --packet remains independent of that environment default. A missing source
prints BLOCKED and exits 2; mismatched bytes remain a failure, never static PASS.

At direct script startup, a missing -S triggers an in-place exec with -S/-B and
all original arguments (including -O) preserved. PID/session do not change and
no workload/scratch/child exists yet. This removes initial site-created mappings
before the workload limits; it cannot undo initial site-hook side effects or
help an interpreter that never reaches the script. Imported regression adapters
explicitly use -S. The repository framework and legacy command remain unchanged.

Applicability, compilation and behavioral successes now use the exact reporter
prefixes `PASS applicability:`, `PASS compilation:`, `PASS behavioral:`. Existing
NOT RUN lines remain. The mandatory exact-source row belongs only to `board`,
with a 90-second deadline, `high-memory`/`repository` serialization and no optional
whole-suite escape. It is not an active userspace/doc test.

Both public tests are registered in `configs/repository-tests.json` and the
explicit board selector in `scripts/host/test-repository-linux.sh`. The main
input-core test executes the C workload; `test-rog5-touch-input-core-runner.py`
executes the process regressions in the same Python process. Both use mandatory
exact-source board rows and serialize with other resource-sensitive tests.

## Focused commands

The byte-preserved `original-runner.py` is a historical negative-control fixture,
SHA256 `0961c7fc4aac0b454ab525d826106e2332484a6be5df427925b597e1bcc29b83`.
It is copied into an owned private test repository to reproduce the old leak;
it is never selected as the operational runner. Clean CI requires no private
Oracle bundle or saved local file.

Run the public process regression with the retained exact Linux source:

```sh
export ROG5_LINUX_SOURCE=/absolute/path/to/pinned/linux-source
python3 -O scripts/device/test-rog5-touch-input-core-runner.py
```

The wrapper prints a new disk-backed evidence directory under `build/`. For an
explicit report location, the underlying command remains available:

```sh
python3 -S -B -O scripts/device/fixtures/fts3658u-input-core/runner-regression.py \
  --before scripts/device/fixtures/fts3658u-input-core/original-runner.py \
  --output build/input-core-runner-review
```

The output directory must be new and disk-backed. Expected: 20 runner scenarios,
one additional real-SIGINT check during handler restoration, 32 exact comparisons, and the unchanged composed-unit hash. No touch C compilation
or 13/18/27/8 semantic execution occurs. The before-SIGTERM scenario passes by
observing the original expected failure. Another injected drain failure passes
only if the runner fails and retains scratch; the independent fixture then cleans
its owned descendants/path. Neither expected failure is phone evidence.

The scenarios cover runner-only TERM/INT, repeated cancellation during cleanup,
launch-to-registration signal/exception windows, a deterministic stale-inventory
adoption window, internal timeout, unexpected
wait exception, success with background descendants, two generations changing
sessions, cleanup refusal, a synthetic semantic-gate positive control, four
semantic-looking infrastructure negatives, missing source, and the actual reporter
no-argv/missing-source interfaces. Every scenario checks a separately owned sentinel
unrelated to the harness; child/grandchild identities must disappear, including
zombies, before scratch deletion. Test-only adapters assert deletion ordering.
No fixed PID, old operational path, root, phone, VM or real compiler is used.

The standard workload invocation for a subsequent explicitly selected board test
remains (it DOES execute the unchanged 13/18 workload, so it is not needed for the
runner-only regression above):

```sh
CC=/usr/bin/gcc ROG5_LINUX_SOURCE="$ROG5_LINUX_SOURCE" \
  python3 -O scripts/device/test-rog5-touch-input-core.py
```

Explicit --packet/--packet-manifest/--linux-source, --batch, and --report-dir also
remain available. All earlier C compiler flags and semantic oracles remain intact.

An optional unprivileged aggregate bound for the focused runner regression is:

```sh
systemd-run --user --scope --quiet \
  -p MemoryMax=512M -p MemorySwapMax=0 -p TasksMax=32 \
  timeout --signal=TERM --kill-after=3s 90s \
  python3 -S -B -O scripts/device/fixtures/fts3658u-input-core/runner-regression.py \
  --before scripts/device/fixtures/fts3658u-input-core/original-runner.py \
  --output build/input-core-runner-bounded-r2
```

The systemd wrapper requires the host's user manager; it is not assumed available
in every execution environment. A forced outer SIGKILL has the limits above.

## Preservation and rollback

Do not rerun or alter legacy 27/8 or the unchanged touch semantic workload to
qualify this runner correction. The regression authenticates original source
files, compares all case/mutant/function lists with the preserved original, and
re-composes the identical C unit. Production driver/protocol and old fixtures
remain pinned and byte-identical.

If a committed change needs rollback, revert the scoped test/integration commit.
Retain negative evidence and recorded result directories. Reverting the cleanup
correction restores a known leaking runner and is not a qualified operating mode.
Never use broad `git clean`, reset, process-name kills, or scratch-prefix removal
against the real checkout. Recovery images and phone receipts are not involved.

Physical remains NOT RUN. No production driver/DT/configuration, rescue/headless
baseline, provider/rail/cleanup gate, signing material, candidate, admission or
claim is changed or qualified by this runner correction.
