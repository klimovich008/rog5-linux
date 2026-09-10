# Denial native mobile bring-up

The selected goal is Denial Wayland on the ROG5 OLED with touch and accelerated
Adreno graphics. Cellular is excluded. The initial integration base is
`6651d598b9e2ce1f4a83b85630cdddfc2debb377`; the dirty original workspace and
accepted server/recovery artifacts remain preserved.

## One-use RAM transfer callback

Private evidence: `successor-live-driver-r1/boot-qualification-r1.json` and
`boot-tests-r1.stdout`/`boot-tests-r1.stderr`. The final controller phase,
`boot_once`, now reuses the existing exact 05941 claim and sealed snapshot
primitives. It does not register a claim or modify those producers. The actual
unregistered registry refuses before snapshot preparation or device queries.

After the snapshot, nine bounded device/getvar reads verify serial, USB path,
product, slot, bootloader, battery and download capacity. The callback requires
installed-route evidence and rechecks source and entered claim, then verifies
live target capture with at least 1,320 seconds remaining immediately before
transfer. Target boot cannot use fallback capture evidence. The fixed command
passes only the sealed descriptor to one owned fastboot child; output is bounded
and retained before success interpretation. Timeout closes the owned process
group and reaps the child. Both failure and success close the snapshot.
Exclusive durable intents and an in-memory used flag forbid another attempt
after an uncertain transfer reply. Transfer completion proves no phone health.

**17 tests PASS in 3.696 s.** Thirteen callback cases use real receipt files and
explicit USB, snapshot, admission, capture and transport fixtures. Four process
boundary cases use a four-byte memfd and a synthetic executable: actual sealed
FD inheritance, failed-child output, timeout/kill/reap and unsealed-FD refusal.
No full production image was copied or hashed, and no phone command was sent.
All twenty-two phases now have component implementations; concrete bridge/route
verification, combined-driver qualification and admission remain incomplete.

Review: readiness after preparation prevents snapshot and device-query time
from silently consuming the required recording window. A tiny real sealed-FD
fixture checks execution behavior without repeating full-image or kernel builds.
These timings establish focused preparation cost, not physical boot performance.
No full CI, physical capture, claim consumption or Ready request ran.

## Capture supervisor and four controller lifecycle bindings

Private evidence: `successor-live-driver-r1/capture-supervisor-qualification-r2.json`
and `capture-supervisor-tests-r1`/`capture-supervisor-tests-r2` stdout/stderr.
The import-only supervisor and four capture callbacks retain the launched
process, authenticate its live process group/start identity and local challenge,
record bounded streams, and verify the original recording deadline and ordered
cleanup events before accepting closure. Target and fallback use separate
processes and streams. Closing an owned recorder remains available after source
or admission changes; it grants no new launch authority.

The initial **16 tests PASS in 8.972 s**. Review added explicit handling for a
launch rejected before any child could start, separate from a launch whose
outcome is unknown. Missing process state after launch intent cannot establish
absence. The extended **20 tests PASS in 11.244 s**, including real controller
success and late-failure recovery with two separate capture children. The failed
trial stays failed after fallback restoration. Actual processes, pipes, process
groups, `/proc` identities and loopback challenge/stage traffic were exercised;
clock, privilege, host network, USB, admission, phone boot and health were
explicit fixtures. These timings do not represent a physical 1,380-second run.

Review: retained entrypoint and controller tests provide evidence beyond mocked
callback results. Atomic fixture port publication avoids exposing a partial
port file. No expensive kernel/module/root build or full CI was repeated.
Twenty-one phases now have component implementations; `boot_once`, the concrete
privileged bridge, installed-route verification and full admission remain.
No phone or host network action, live receiver, claim or Ready request occurred.

## Passive capture worker and bounded source observation

Private evidence: `successor-live-driver-r1/capture-qualification-r3.json`,
`capture-worker-tests-r1` through `capture-worker-tests-r3`, the two bounded
traceback directories, `capture-git-trace-r1` and `capture-source-probe-r1.json`.
The import-only root capture core reuses pinned `Receiver` stage parsing and
temporary network ownership. It issues no boot, claim or phone command. Its
request requires the fixed source/owner, role, clean host source and complete
outer admission before acquiring the existing exclusive coordinator lock.

The original lifetime remains **1,380 seconds**, with **1,320 seconds** required
at readiness. The worker streams process/group/start/host/source identity,
original deadline, a local probe challenge, stage events and a final result to
its supervisor. It preserves the 8 MiB output bound with reserved cleanup/result
capacity. Target and fallback roles use their respective releases. Final capture
PASS requires a full recording interval, successful switch-root observation,
no receiver/source errors and completed owned cleanup; it is explicitly neither
authenticated phone health nor release qualification.

Recording end is measured before cleanup. Cancellation, stream loss or an early
transport failure cannot acquire full-lifetime status merely because cleanup
finishes after the deadline. Cleanup still runs when output disappears, and a
missing supervisor before preparation prevents network setup. Git source checks
now run in a ten-second bounded process group as the repository owner. Final
source failure is retained without discarding already-completed cleanup evidence.
The actual isolated source reader **PASS in 0.140 s** as deck, matching clean
`0f722bdef80bcb81aabbccdcb32978568053378c`; the privileged runuser handoff remains
part of the pending real bridge integration.

The first namespace test timed out after **60 seconds**, before recording, in
Git status. Five/eight-second traceback probes reproduced it; disabling fsmonitor
did not help. A bounded syscall trace showed Git reopening retained Images and
initramfs archives. The index records UID/GID 1000:1000, while the same file
appears as 0:0 inside the mapped namespace. Host source identity is now captured
before entry and revalidated after exit, with its namespace use explicitly a
fixture. The initial runner/diagnostic processes and descendants exited; failed
logs and sources remain retained. No source comparison was relaxed in production.

With that fixture boundary, **17 tests PASS in 0.293 s**. After adding bounded
source execution and two supervisor/source-failure cases, **19 tests PASS in
0.388 s** including host revalidation (**0.059 s** test body). They use a real
UID-0 user/PID/network namespace, actual file ownership and advisory lock, and
real loopback TCP with the existing Receiver/parser. Time, source identity and
USB/network setup are explicit fixtures; no 23-minute physical capture occurred.
Cases cover both roles, malformed/failed stages, lock exclusion/metadata,
deadlines, delayed or failed cleanup, cancellation, broken/full output, missing
supervisor, source drift/timeouts and rejected admission/USB/privilege/timing.

Review: this removes an observed large-artifact rescan from the fixture path and
bounds the production source subprocess. It also closes a potential false
full-duration result caused by counting cleanup time as recording time. No
kernel/module/root/ARM64 build or full CI was repeated. The controller still has
seventeen phase implementations: connecting this worker to the four
capture phases, implementing the one RAM boot and completing the privileged
bridge/route verification remain next. No phone or host network action, claim,
receiver launch on the phone connection or Ready request occurred this turn.

## Fastboot transition, fallback location and installed reboot bindings

Private evidence: `successor-live-driver-r1/fastboot-tests-result-r3.json`,
`fastboot-pre-locator-r1`, `fastboot-pre-fix-r2`, the three fastboot test logs,
`health-engine-tests-r2.stderr` and `fastboot-host-entrypoint-r1.json`.
Three additional bindings implement `await_fastboot`, `locate_fallback` and
`reboot_installed`. Seventeen phases have implementations; four capture lifecycle
phases and the single RAM boot remain, together with concrete route/capture
verifiers, privileged transport integration and complete admission.

The bounded command wrapper permits device listing, eight fixed getvars and one
ordinary installed reboot. Flash, slot changes and RAM-boot arguments are refused.
Each command validates fixed executable ownership, source/admission, durable
phase/prior-result receipts and USB identity; it records an exclusive intent,
uses the existing process-group/output-bound worker and retains raw output before
validation. Read identity is checked before and after each command. The fixed
fields preserve product lahaina, USB 1-1.2, slot B, bootloader
`Post-CS10-17-WW-user-AS`, usable A/B slots, battery SOC yes, 8400–8800 mV and
128 MiB–1 GiB reviewed download capacity.

Source-to-fastboot waiting is bounded at 180 seconds and never repeats the source
reboot request. Fallback location can authenticate V11 independently of target
switch-root using the qualified shell observer, or report fastboot only after
installed-route verification. The ordinary reboot rechecks the route and live
owned fallback capture after identity queries. A completed fastboot command is
reported separately from boot success; a failed/lost reply remains one-use.
The route and capture verifiers are required injected boundaries whose concrete
implementations remain pending. Synthetic verifier acceptance is not live authority.

The initial wait/reboot/parser suite **PASS: 23 cases, 8.349 s**. The integrated
28-case run then had **26 passes and two errors in 21.029 s**: the parent locator
and nested health reader both tried to create `locate_fallback-usb-000.json`.
Exclusive receipt creation correctly stopped both early-V11 paths. Original
sources and failures remain retained. The only subsequent production change was
to name the parent's observations `locate_fallback-location-usb-*`; an exact
source comparison verifies this scope. Both failed cases and the fastboot
locator control **PASS in 1.684 s**. Other passing paths were retained without
repeating the full suite.
The combined evidence qualifies all 28 cases; it is not a new full-suite PASS.

Adding the early-fallback health phase also required the existing health-engine
fixture to dispatch only its intended four callbacks explicitly. Its three
real-controller cases **PASS in 2.481 s**, preserving target success, failed-trial
classification after restoration and rejection of unverified restored state.
USB/SSH/fastboot transport, admission, capture and route proofs remain synthetic;
actual generators, validators and durable receipts are exercised.

Isolated imports, producer pins and the actual fixed fastboot executable's
ownership checks pass. An actual host-only `fastboot --version` through the
bounded worker **PASS in 0.015 s**, reporting 35.0.2-android-tools. No USB/device
command, phone write, reboot, claim, receiver or Ready request ran this turn.

Review: the combined early-fallback test found a real evidence-ownership bug
that individual component tests missed. Separating names preserved both records
and all exclusive-write protections. The affected paths were retested without
repeating kernel/module/root builds, ARM64 observer execution or full CI. Next
work is capture/RAM-boot integration and concrete route/privilege handling, with
kernel and non-cellular hardware still ahead of Denial/Flutter builds.

## Concrete target and fallback health callbacks

Private evidence: `successor-live-driver-r1/health-read-tests-result-r1.json`,
`health-read-tests-r1.stderr`, `health-engine-tests-r1.stderr` and
`live-health-discovery-r1/result.json`. The new import-only bindings implement
`observe_target`, `post_capture_health`, `observe_fallback` and
`verify_fallback_restoration` using the qualified health/restore observers.
Fourteen concrete callbacks now exist; the full driver/admission remains pending.

Each binding verifies the clean producer, outer admission, durable context,
exact read-only phase intent and prior result receipts. Initial discovery may
poll USB enumeration and SSH readiness within a 300-second observation window;
it records each attempt, refuses an unexpected identity and never retries a
health/restoration operation. Later checks require the previously recorded boot
and readiness immediately. The target's healthy commit must still precede
300 seconds uptime, including when observed after the full capture. No capture
lifetime is shortened by this component.

Raw transport output is saved before command/health validation. The callback
adds authenticated status only after the pinned SSH worker and matching
discovery/full-observation identity succeed. Target collection uses Python;
V11 uses the sealed BusyBox shell and reports its legacy readiness limitation.
The current worker runs as deck with an existing route; it does not solve the
still-pending privileged fallback network/capture boundary.

The actual isolated entrypoint imports and all producer pins passed.
**23 boundary tests PASS in 6.679 s** with real receipts/generators/validators
and explicit synthetic transport and health. Cases cover all four callbacks,
delayed USB/SSH, expired discovery, rejected admission, wrong mutation flags,
repeated commands, changed boots, incomplete capture, failed health, unverified
restoration, altered raw hashes/source/receipts and unreaped commands.

Three added tests then ran through the real controller engine in **2.601 s**:
target success invokes both health callbacks; a late target failure reaches
fallback restoration while retaining trial FAIL; pending selection readback
prevents a restoration claim. Capture, mutation and admission remain explicit
fixtures. The unchanged 23-case subset was not rerun for these added cases.

The actual discovery script also **PASS in 0.333 s** over existing pinned USB
SSH on V9 boot `7c945aa5-80d0-4af2-aa76-113d68e23ac5`, bundle V9 and kernel
`7.1.4-gf17befd4ef17`, with readiness present. Host producer source was clean
`7699e26577195e3f821da876404f18775739e52a`. Script, request, raw target output
and transport are retained. This qualifies discovery on the existing phone;
it does not qualify a physical successor or fallback boot. No phone write,
reboot, claim, receiver or Ready request occurred.

Review: inexpensive actual-entrypoint and phone discovery checks complemented
synthetic integration tests without repeating kernel/module/root builds or full
CI. No recurring new failure was found. The initial/later observation distinction
is now implemented and tested, preventing readiness retries from accepting a
different boot after capture. Next are fallback location, capture/fastboot
ownership and the scoped privileged transport bridge, with kernel/non-cellular
hardware still ahead of Denial/Flutter builds.

## V11 observation and restoration component

Private evidence: `successor-live-driver-r1/fallback-observation-tests-r1`,
`fallback-observation-tests-r2` and `fallback-parser-result-r1.json`.
The import-only observer uses the exact sealed V11 ARM64 BusyBox/loader and
physical guard without Python or a state-helper invocation. It snapshots the
selection and RAM readiness marker, checks the SSH identity service and exact
installed boot/selector/bundle inventory, and repeats physical and snapshot
checks before replying. Restoration additionally requires the actual Rust
transaction records, custody and helper completion output. It does not provide
transport authentication or controller admission by itself.

The retained signed V11 marker has no attested boot ID. The parser reports that
limitation explicitly and rejects a stale ID when one is supplied. V11 uses a
native ext4 lower with a tmpfs overlay, so the successor's persistent-loop-root
validator is not reused. The future caller must authenticate a fresh V11 boot.
Restored selection eligibility remains separate from release qualification.

The first ARM64 case failed in **2.625 s** on readiness-file metadata. A bounded
diagnostic reproduced mode 0444 with the default umask and mode 0400 under the
runner's `umask 077`. Changing only fixture bootstrap to `cp -p` preserved the
required mode. The production observer stayed unchanged; original failure,
runner and both diagnostic outputs remain retained.

**11 ARM64 cases PASS in 45.476 s**, including pending/healthy observation,
restoration from both states, wrong boot, stale readiness, missing completion,
wrong exchanged record, wrong installed hash, symlinked readiness and inactive
SSH identity service. These use the actual V11 tools, a real tmpfs and actual
Rust stage/restore operations inside isolated fixtures. Device telemetry,
service state and installed-image contents are synthetic, with an explicit
regular-file stand-in for the unprivileged fixture's boot block node. Selection
bytes are unchanged by observation in every case. No phone action occurred.

**33 host parser checks PASS in 0.005 s** by replaying hash-bound retained
ARM64 outputs. They cover protocol/schema limits, state/purpose contradictions,
false restoration, changed inventory, corrupt readiness, stale boot IDs and
legacy/current marker binding. No ARM64 suite rerun was needed. No production
source changed after qualification, and no physical V11 boot is claimed.

Review: metadata preservation fixed a demonstrated fixture cause without
relaxing acceptance. Shallow state-path discovery also replaced a recursive
listing that traversed copied worktrees and emitted over 100,000 tokens; no
build-speed improvement is inferred. The existing standing feedback loop is
retained. Kernel/non-cellular work remains first, with complete callback,
capture/fastboot and privilege integration still pending before a phone trial.

## Health after full capture and actual V9 reader qualification

Private evidence: `successor-live-driver-r1/health-inputs-r1`,
`health-baseline-inputs-r1`, `health-tests-r1`, `live-baseline-health-r1` and
`health-late-replay-r1`. The new `successor-health.py` component keeps the
300-second healthy-commit criterion while allowing a fresh observation after
the full 1,380-second capture window. The original startup-only smoke predicate
remains unchanged; its overall-uptime limit made it unsuitable for this phase.

The reader verifies nine runtime files/units, boot-bound descriptor/healthy/SSH
and readiness markers, exact healthy selection, successful healthy-unit status
and timestamps, inactive rollback timers, required service states, local root
composition and the existing physical storage/power guards. It uses bounded
read-only probes, with physical guards before and after collection. A separate
explicit baseline role can only report V9 baseline health; it cannot certify
the successor. No state helper, reboot, DRM open or service change is performed.

Streaming inspection verified the exact successor payload and extracted seven
runtime/unit members in **0.474 s**. The two healthd files are pinned to frozen
source and still require their physical comparison. The first baseline setup
correctly refused an unresolved source timer template; the original source and
failure reason are retained. Inspecting the accepted V9 archive in **0.474 s**
proved its three packaged health/rollback units match the successor's resolved
units, including `OnBootSec=900s`. The reader now binds those packaged bytes.

**20 tests PASS** in normal/optimized Python (**0.452/0.490 s**) with explicit
synthetic target/baseline observations and actual pinned producers. They reject
late commits, stale boot markers, wrong SSH fingerprints/trials, pending state,
failed units, armed timers, altered runtime bytes, unsafe storage/power, numeric
boolean proofs and nonfinite/ambiguous uptime. Generated role/physical-guard
identity and absence of helper invocation are checked separately.

The complete reader then **PASS** on the actual V9 phone in **2.083 s**. Boot
`7c945aa5-80d0-4af2-aa76-113d68e23ac5` was observed at **50,061.14 s** uptime;
its healthy unit exited successfully at **64.142787 s**. All nine runtime
comparisons, current-boot markers, service/timer states and storage/power checks
passed. Battery health was Good, temperature **30.3 C**, voltage **8.543 V**.
Host producer source was clean `3f2f0291f16d20266cd9c31d7db284558a4c8902`.
Script, request, raw response and result are retained. This is baseline reader
qualification, not a successor boot, physical graphics test or full release PASS.

Replaying that same retained observation in **0.365 s** reproduced refusal by
the old startup-only predicate and acceptance by the new later-health predicate.
No second phone read was needed. Review: these findings prevent predictable
post-capture false failures without changing startup deadlines or rebuilding
kernel/root artifacts. Current-state now leads with a short coordinator handoff
so future turns can read current evidence before opening historical milestones.
V11 health, concrete health callbacks, capture/fastboot, privilege handling and
full admission remain pending. No reboot, state transition or Ready occurred.

## Read-only source reconciliation and physical preflight

Private evidence: `successor-live-driver-r1/observation-tests-r1`,
`live-source-observation-r1` and `source-read-tests-r1`.
The observer uses the qualified source file readers, sealed physical guard and
existing RAM staging inventory. It reads only the source transition state; no
state helper, exitrd writer or reboot command is invoked. It checks rollback
units, holds a nonblocking record lock, identifies the exact transaction and
shutdown state, then repeats guards and compares the snapshot before returning.

Recognized states include untouched V9; staged selection with or without the
stage-completion receipt; patched exitrd with or without the install-completion
receipt; restored exitrd awaiting selection restoration; and completed selection
restoration. Unknown members/owners, reboot intent, a partial next-file
publication, partial restore intent, missing custody or changed record refuse.
Completed source restoration requires the original shutdown and exact old record.
These classifications preserve the actual Rust helper's lost-reply recovery
semantics without treating an ambiguous operation as permission to retry.

**22 tests PASS** in normal/optimized Python (**0.568/0.510 s**). They use actual
files, root ownership, bounded inventory, no-follow readers and real advisory
locks in an unprivileged UID-0 user namespace. The host root is read-only except
the private fixture directory, and networking is isolated. Physical guard,
filesystem-type and unit telemetry are explicit fixtures. Every ordinary case
checks unchanged file inventory/content/metadata; one intentional replacement
case verifies rejection after a record swap during observation.

The actual generated preflight then ran through pinned normal USB SSH on V9 and
**PASS** in **1.694 s**. Boot `7c945aa5-80d0-4af2-aa76-113d68e23ac5`, bundle V9
and kernel `7.1.4-gf17befd4ef17` matched. The exact Rust helper, custody and RAM
completion token remain intact. Physical storage/power guards passed; active
shutdown remains `fc1ce027`, selection remains `ed3a62d1`, and state/exitrd
transactions and reboot intent are absent. The host source was clean
`cf617150ad719ba53b17ecb62daf4265044f0678`. Raw script, request, SSH reply and
result are retained. No persistent write, helper operation or reboot ran.

Three concrete callbacks now bind this observer to controller preflight, source
abort inspection and source abort verification. **12 tests PASS** in
**2.869/3.045 s**, using real saved controller intents and generated scripts with
synthetic admission/transport. They replay the actual phone response, with
explicit altered proofs for negative cases. Exact protocol types, snapshot
consistency, complete restoration tokens and read-only phase intents are required.
These callbacks do not supply the still-pending full controller admission.

Review: this source-state question was resolved by a 1.694-second read-only
phone observation; no kernel/module/root build or full boot cycle was needed.
The user namespace enabled actual ownership/lock fixture checks despite the
unresolved host sudo prerequisite. Keep that distinction explicit: scoped
privileged capture and new fallback routes still need their final bridge.
Next work remains fresh target/V11 health, capture/fastboot ownership and full
admission. The Denial/hardware goal remains incomplete; no Ready is pending.

## Concrete mutation callback integration

Private evidence: `successor-live-driver-r1/callback-tests-r1/result.json`.
`action-callbacks.py` implements the seven mutation callbacks: arm the selection,
install/request/restore the source exitrd transition, restore source selection,
stage the fallback helper and restore fallback selection. Each requires an
outer admission callback, exact existing source/owner, clean host producer,
fixed producer hashes, durable custody and the controller's exact saved context
and entered receipt. A separate exclusive command intent prevents callback retry
even if a caller repeats the same outer receipt. No live CLI is provided.

Source Python actions and sealed shell state operations are generated from
qualified producers. V11 uses only the BusyBox stager and shell wrapper.
Completed state results require exact before/after hashes, boot, operation and
helper output hashes. Reboot requires both its entered event and final result;
a missing/nonzero/timed-out reply cannot become success. All transport evidence
is retained before semantic parsing, including complete failed command streams.
The adapter currently invokes the worker as deck over an existing route. The
privileged bridge needed for a newly prepared fallback route remains a concrete
integration prerequisite; no privilege workaround was introduced.

All **27 tests** pass in normal/optimized Python (**7.304/7.890 s**). Twenty-two
boundary cases exercise actual generators, existing durable custody, real
exclusive/fsynced host receipts and retained ARM64 replies (with explicit fixture
identity adaptation where needed). Five more run the actual controller engine
and these callbacks through success, lost arm reply/source restoration, lost
reboot reply/V11 restoration, target observation failure and capture cleanup
failure. Transport, admission, physical health and capture remain synthetic.
No target script was sent, no phone state changed and no boot claim was used.

Review found two scoped issues before qualification: the generic 1 MiB receipt
limit could discard two valid 1 MiB streams after base64 expansion, and ordinary
Python equality could accept numeric values in boolean proof fields. The adapter
now uses a distinct 4 MiB transport receipt bound and type-sensitive JSON
comparison; full dual-stream failure retention and numeric-boolean rejection
are included in the passing tests. No kernel/module/root-image rebuild or
unchanged full CI was repeated. Continue with actual read-only reconciliation,
capture/fastboot/health bindings, scoped privilege handling and final admission.

## V11 runtime correction and bounded SSH worker

Private evidence: `successor-live-driver-r1`. The earlier Python `stage-v11`
proposal cannot run on V11, where Python is absent, and was never executed on
that phone runtime. `fallback-stage.py` replaces it with the exact sealed
BusyBox/loader and existing static ARM64 Rust helper. Source-side Python staging
on V9 remains valid and completed; preserve its owner and do not repeat it.

Five actual ARM64 namespace cases pass in **33.006 s**: stage/restore from
pending and healthy, wrong-boot refusal, partial-transfer refusal and duplicate
stage refusal. The empty root contains no Python or shared runtime libraries;
`/run` is actual tmpfs. Physical kernel/storage telemetry remains synthetic.
`fallback-tests-r1` failed in 2.387 s on a manually misencoded fixture device
number. Deriving it with `os.makedev` from the fixture's actual sysfs major/minor
fixed the fixture only; the production stager was unchanged. Both runs remain.

The host SSH worker limits each output to 1 MiB using disk-backed files and a
child file-size limit, owns and reaps its command group, preserves nonzero/lost
replies and never retries a command. Existing routes are borrowed without setup
or cleanup ownership. New link-local setup requires root before any network
resource creation and uses the existing four-step owned cleanup. Transport
completion alone never certifies remote-command success.

`live-worker-r1` stopped before execution in **0.034 s** because `sudo -n`
requires authentication. This is a host privilege prerequisite, not an approval
review rejection or a phone failure. The worker was adjusted to run as deck over
existing routes. `live-worker-r2` then stopped locally in **0.074 s** because an
isolated import could not find a generated repository sibling. The fixed loader
adds only the fixed producer directory while importing and restores the search
path. A real isolated-child import regression now complements the mocked network
boundaries. All **13 cases** pass in normal/optimized modes (**0.530/0.569 s**),
including real process timeout/reaping and enforced disk output limits.

`live-worker-r3` passed actual normal USB SSH in **0.611 s** as deck. Exact
boot `7c945aa5-80d0-4af2-aa76-113d68e23ac5` and kernel
`7.1.4-gf17befd4ef17` matched, command status was zero with exact output and no
stderr, and no host network resources were claimed or changed. Host producer
source was clean `d66b0dedddd5fb18d9b9173747e58ef5749d6987`. This was a read-only
continuity probe; no new full power/storage health or successor boot is claimed.

Review: runtime assumptions and mocked-only launch coverage caused avoidable
local failures. Both now have cheap actual-runtime checks; no kernel, module or
root-image rebuild was needed. Keep the remaining work on concrete controller
integration, capture privileges, admission and recovery preparation before any
reboot trial. No user Ready or physical action is pending. The complete concrete
driver remains unimplemented and unadmitted; these are qualified pieces only.

## Successor controller ordering and installed fallback route

Private evidence: `successor-controller-r1/result.json`. The one-use ordering
engine now covers source preflight, state arm, exitrd installation, source reboot,
fastboot, capture, one RAM boot, target observation, full capture closure and
fresh post-capture health. Only that complete successful path retains the healthy
successor for hardware tests. Every failure remains FAIL after restoration.
Before any reboot intent, fresh source reconciliation can restore an authenticated
exitrd patch before restoring the old selection. After reboot intent, no automatic
source abort or repeated reboot request is permitted.

V11 recovery no longer depends on a successful target switch-root event. It
requires exact fresh authenticated V11 identity, physical guards, successor
pending/healthy bytes, staged restoration helper and independent restored-state
verification. If the phone is in fastboot after closed target capture, the engine
requires the verified installed fallback route, a separately owned full fallback
capture and one ordinary reboot of the installed selector. It has no second RAM
boot or flash path. Failed or shortened capture/cleanup prevents state restoration.

All 25 ordering/failure cases pass in normal/optimized Python in 13.156/6.148
seconds. Driver observations and capture lifetimes are synthetic; receipt writes,
exclusive execution directories and fsync are real. The first exploratory run
took 1.566 seconds; the variation's cause was not measured, so no optimization or
Python-mode speedup is claimed. The concrete live driver and admission remain
unimplemented; these tests do not qualify live transport or complete recovery.

The installed selector was extracted from retained recovery archive `4ba0fccd`.
Its loader is `de5e7e78`, and its helper is actual v2 `c1aab57b`. The complete
selector function runs with that ARM64 helper and sealed BusyBox under QEMU;
only the ISA invocation and explicit storage-preparation/cleanup fixtures differ.
Three cases pass in 0.342 seconds: successor pending and healthy choose V11 with
unchanged records, while restored V9 healthy chooses V9 and publishes fresh
pending `958a2fc8`. This confirms the decision path, not a physical boot.
The first test retains FAIL/0.112 seconds because its expected diagnostic used
hyphens where the actual helper prints spaces. Correcting that exact fixture
string preserved all record, cleanup and decision assertions; production bytes
and the generated selector script were unchanged.

Physical read-only installed-boot verification passes in 0.545 seconds on the
unchanged V9 boot. `/dev/sde35`, runtime device `259:19`, is read-only and exactly
100,663,296 bytes with wrapper SHA-256 `dcc487f1`. The old healthy selection is
unchanged and the state-exchange directory is absent. No reboot, state operation
or additional RAM staging ran this turn.

After-run review: bind recovery decisions to the actual installed wrapper and
helper, not whichever loader happens to be in the working checkout. Preserve
the failed diagnostic fixture and the measured timing variation. The next
dependency is concrete driver integration; no kernel/module/A01/full-CI repeat
is justified by this private ordering work.

## Source transition primitives and physical RAM staging

Evidence: private `successor-source-actions-r1/result.json`. Read-only source
inspection passed in 0.343 seconds and confirmed that the running V9 shutdown
matches corrected source `fc1ce027`, not the old R01/V8 input. The retained
fastboot variant `0ee47fb5` differs by one final dispatch command only; its
corrected storage cleanup and fallback suffix remain unchanged. The reboot
helper still matches `68d6a69e`, and the nvmem restart provider is bound.

The original private Python primitives proposed exclusive RAM staging for source and
V11, source exitrd installation, one-use reboot request, and exact pre-reboot
exitrd restoration. Source exitrd operations require the completed Rust state
exchange, both old-record backups, inactive rollback timers, the exited old
healthy writer, sealed tools, physical guards and custody. Directory and record
locks, no-follow path descent, bounded file reads, fsync and path revalidation
protect publication. Reboot intent precedes the single systemctl request; a lost
reply refuses both retry and automatic source restoration. An incomplete install
after publication may restore the old exitrd only if no reboot intent exists.
Partial staging remains visible and refuses same-owner retry.

All sixteen focused tests pass in normal/optimized Python in 0.750/0.749 seconds.
They exercise actual file operations and locks with synthetic telemetry,
systemctl and syntax-command boundaries. They cover lost replies, installation
failure after publication, fsync failure, record/directory replacement, tampered
payload/custody, symlinks, partial state exchange and V11 pending/healthy staging.
The existing exact ARM64 shutdown syntax qualification is reused; no kernel,
module, artifact rebuild or unchanged full-CI run occurred.

The exact generated **staging-only** script then ran on the real phone in
1.368 seconds. All four RAM files are retained in the custody owner's directory
`/run/rog5-kernel-hw-5ff5ab2bf15642c7a07e788a73caefa2`. A separate read-only
program verified their actual hashes/metadata in 0.258 seconds and confirmed the
same V9 boot, original active shutdown, exact healthy V9 state, and absence of
the state transaction directory. No state helper execution, active exitrd
replacement, reboot, protected-storage write or claim consumption occurred.
This qualifies physical RAM staging only. The complete controller, successor
boot and actual source/fallback restoration remain unqualified.

After-run review: inspect the running source before adapting a historical
transition. This inspection prevented importing the obsolete V8 shutdown input;
the already qualified corrected dispatch copy could be reused without another
build. Keep completed RAM staging and its owner across the next goal turn.

## Guarded state exchange and host custody

Private evidence: `successor-state-guards-r1/result.json`. The source-stage,
source-abort and V11-restoration generators use the retained physical guards
and exact static Rust helper. Six positive, twenty refusal and two post-operation
fault cases pass across two runs using sealed ARM64 BusyBox/loader and the
actual helper, with explicitly synthetic kernel/device telemetry. Failed helper
status or unsafe post-operation power preserves the helper logs and remains
FAIL even after a successful state exchange.

The first service took 57.384 seconds and stopped during fixture setup after
19 passing cases: the negative fixture tried to overwrite its mode0400 custody
file. Its original FAIL receipt remains. The scoped fixture fix also adds
fsynced per-case rows and terminal exception results. Only the remaining nine
cases ran again, passing in 15.572 seconds. A separate replay verifies all 28
retained scripts, raw outputs and final fixture states against the unchanged
generator; it does not reconstruct missing first-run process receipts.

Seven durable-host-custody tests pass in normal and optimized Python, including
duplicate keys, source drift, symlinks, reused ownership and partial fsync
failure. Fresh read-only V9 health passes in 1.206 seconds, binding the actual
old selection hash and all eleven installed artifact hashes. Host custody owner
`5ff5ab2bf15642c7a07e788a73caefa2` retains the exact old record and its source
evidence in exclusive, synced files. The new shell guard's read-only subset
passes on the actual phone in 0.972 seconds, on unchanged boot
`7c945aa5-80d0-4af2-aa76-113d68e23ac5`. No state helper was uploaded or executed
on the phone. Controller admission, live state exchange, fallback restoration
and successor boot remain unqualified. No human availability is pending.

After-run review: partial matrix progress should survive fixture errors; keep
raw failures and resume only unrun cases when production inputs are unchanged.
The next hardware dependency is the complete recovery controller. No kernel,
module, paired-root A01 or full CI rerun was justified by this private work.

## Exact059 state exchange prototype

Full source CI for the exact boot helper passes on clean `63a0c1a1` in
602.727 seconds. `source-ci-r8/result.json` binds log SHA
`2c7952545484298c2bb2844038489aed23ff796cb5ec172170df2dc9c4d1f260`.
The compiled payload source remains frozen at f74; later work below is private
and is not claimed to have passed that repository CI.

`successor-state-exchange-r1/result.json` records the Rust primitive's offline
qualification. It keeps the trial record continuously present: sync a separate
old backup and new pending file, atomically exchange the pending file with the
locked original, then sync both directories. Restoration exchanges the exact
old inode back. Exclusive transaction/intent files refuse repeated operations;
failed or interrupted operations retain their records for reconciliation.
The existing trial helper's record format and installed selector are unchanged.

Eleven native test groups pass, including interrupted stage/restore, lost
completion marker, matching new healthy state, symlinks/hardlinks, record and
directory replacement, concurrent locks and prior partial publication. The
test-first placeholder fails five positive groups as expected; that receipt
is retained. ARM64 constants compile against target headers, while the old
host flag values fail the same compiler check.

Static-PIE ARM64 twins match SHA
`9ec0d969eb17dcb18f14a1698dc2c2daa2af256baf337bcd9f1868ac2e97a8c4`
(1,253,144 bytes; builds 1.071/1.119 seconds, each 512 MiB/no extra swap).
Six actual ARM64 namespace cases make 17 process calls in 0.582 seconds;
service runtime is 0.689 seconds, peak 16.2 MiB/no swap. Both retained v1 and v2
helpers accept the new pending identity and mark it healthy; the new primitive
then restores the original V9 bytes/inode. Other cases cover pending restoration,
wrong state, missing controller environment and a lost stage reply. The root
contains no shared libraries. Static glibc retains NSS symbols; these results
qualify the exercised paths, not every linked glibc function.

Failures remain explicit: the first namespace launch referenced an absent
optional repository QEMU path and executed no target. The first PIE build
segfaulted before any syscall due to contradictory compiler/linker options;
its core is retained beside the failed image. A symbol-only shared-library
check was too broad and was replaced by the empty-root operational proof,
with the NSS presence still recorded. The next ARM64 operation refused before
writes because two open flags used host values. Architecture-specific constants
and generated target-header assertions fix that recurring error. The first
lint attempt could not run because the minimal pinned builder lacks cargo-fmt;
fmt/clippy remain unqualified. No physical action occurred.

After-run review: native success missed the target flag error; make the target
compiler assertion part of the build, and run one actual ARM64 operation before
the comparison build. Atomic exchange removes the proposed absent-record window
and provides direct restoration without changing the accepted selector helper.
Physical guards, host custody, controller admission and phone-filesystem
power-loss qualification remain pending. Do not deploy this private primitive
as an independently admitted storage operation.

## Exact059 boot primitive preparation

The import-only `verified-kernel-hardware-boot.py` now binds the one exact 05941
profile, wrapper/trial, retained V11 fallback and completed A01 result. It uses
the already size-bound 128 MiB snapshot and capacity primitives without calling
the R01 boot gate or changing historical globals. A separate exact entered
claim is mandatory; the new candidate is deliberately unregistered until the
controller and storage/recovery preparation are complete.

Nine new test groups exercise every claim field, missing/duplicate/extra data,
unregistered and unconsumed states, wrong device/image, profile drift, raw
capacity replay, one dispatch and FD cleanup on success/failure. Together with
the existing seven R01 and four ordinary helper tests, both Python modes pass.
The actual retained 128 MiB wrapper was streamed into a fully sealed memfd and
closed without transport in 0.184 seconds. `successor-boot-helper-r2/result.json`
records final source pins; service runtime 2.450 seconds, peak 281.8 MiB/no swap.
The first test expected the wrong exception class for the registry's correct
refusal; only that test expectation changed. Review also corrected the proposed
claim's recovery-storage field to read-only: embedded RAM boot bypasses trial
selection. The first focused receipt remains retained.

Source review confirms `decide` only creates a new identity when the record is
absent; `healthy` refuses identity replacement. The atomic exchange prototype
above supersedes the initial archive-then-create proposal. It still needs exact
old-record retention and the existing device, mount, power and storage guards.
The old R01 restoration helper cannot perform that identity migration.
No state write, claim registration/consumption, fastboot or phone action occurred.
Full CI for the new helper subsequently passed as recorded above.

After-run review: reuse the verified 128 MiB primitives without mutable size
overrides; keep admission identity separate from offline recognition. This
avoids duplicating the snapshot implementation. Do not repeat the completed
kernel, module or A01 runs; the next unanswered dependency is controller and
trial-state recovery preparation.

## Exact059 A01 integration

One repository-owned artifact profile binds the signed headless wrapper,
kernel/DT/archive, all 54 modules and their destinations, exact nested metadata,
packaged PDR exception and prior qualification receipts. Its offline candidate
record does not extend the boot-claim consumer. The actual inventory passed in
1.332 seconds at 335.5 MiB with no swap. Profile/helper evidence is retained in
`a01-profile-r1/result.json` (SHA
`166e19bd1bc6f708b9465ec06caec7499b6f13359137f04cceb553237df11b45`).
The 56 composition tests passed normally/optimized before the later bounded-log
correction; that changed method passed separately in both modes.

The explicit fixture-reference format consumes original shim/kernel/module/kit
receipts and both shim objects. Its actual loader passed in 0.865 seconds,
including streamed vmlinux-to-Image equality; no rebuild or VM was needed.
Receipt `successor-a01-fixture-r1/validation-r1.json` is
`274c94f129d45643d47c004e6a4f3a5aa0faa1fc06e896ce4657b85d94d6d7e5`.
Seven fixture tests pass in both modes, and legacy behavior remains unchanged.

The integrated VM helper now separates create/start, persists exact ownership,
requires terminal non-OOM state and confirmed removal, and closes the client
process group independently of its leader. Eighteen tests pass, including a
real surviving-child cleanup fixture without Podman. Host SIGKILL leaves
ownership evidence unconfirmed and requires reconciliation before retry.
Review found an unbounded failure-log read in the caller; the corrected caller
skips failed lifecycle logs and bounds successful reads. Three A01 wiring tests
retain the real runtime-marker predicate, including missing/duplicate hardware
markers and failed runtime. The changed VM method and those tests pass in both
modes in `a01-integration-focused-r1/result.json` (1.762 seconds service time).

Two early focused harness launches did not run tests: systemd used the home
working directory for a relative script, then Python -I excluded existing
sibling imports. The canonical absolute Python -B invocation passed. No source
check, test assertion or import policy was weakened to accommodate the harness.
Actual integrated A01 now passes on clean `f316fe58` in 80.308 seconds. All
seven checks pass, including 51 ordinary loads, two real ENODEV refusals and
the activation split. Complete lower/upper hashes match before and after;
the actual owned VM terminated without OOM and was removed. Controller receipt
`successor-a01-r1/result.json` SHA is
`cdc3edcec154436199519718c0b989068a5b6ccd9081543629f450efcb2ac937`;
A01 result SHA is
`b65597078acd49bf47fadebbf5aff548c64892cc5538aa2aa050472eabd5ddab`.
Full source CI on that same commit passes in 596.538 seconds with source
unchanged; `source-ci-r7/result.json` binds log SHA
`fc65a047e435b66deb35175af4f494d63567f3a0aca9dcbcaaefeb550fd03571`.
Physical admission and hardware qualification remain pending.

## Final source CI

Full CI passed on `492d8cf22071d5aeacc2e9720440af0c883b463f` in 593.246
seconds, with clean unchanged source, 3 GiB memory cap, no swap and CPUQuota200%.
Both previously failing boundaries pass; failed r4/r5 receipts remain retained.
`source-ci-r6/result.json` SHA is `0ab45662a87e65b9f697598b91e61add9a2765ea00cbc611d099a3bf0adf98ef`;
log SHA is `6f74382273594d8759a7f2ac054956b1fa235a91159a542c40d6a714043726c4`.
This closes source CI for the combined scheduler/locale changes. Later notes
updates do not relabel the tested commit or establish real-phone qualification.

After-run review: bounded scheduling avoids unbounded CPU competition; the UFS
verifier fixes its own locale; canonical AVB path verification was tested using
the retained failed wrapper before new signing. Each correction has a focused
regression and preserved failure evidence. Kernel/module builds were not
repeated, and no phone action or human readiness request occurred.

## Signed wrapper twins and service-locale correction

Actual `successor-boot-package-r2/result.json` is PACKAGING_TWINS_PASS,
SHA `4ad975e7568af0e44f6a43496a58c95dad71068aeb6c43f161602ad216352a09`. Service elapsed time was 89.009 seconds with 512 MiB
maximum memory and no swap. Both signed bundles, recovery archives and boot
wrappers match. Raw images are 129,966,080 bytes; measured AVB capacity selects
134,217,728 bytes. Wrapper SHA is
`d21405d94a9eabc4b6b8e1b7990bf7c9f2aef1da0795a39e94761a5a09ab3fa6`;
manifest SHA is
`10c3db91eb265ee9edcce8bb812dcfc26230f1396455d3c2d0258e87b23ee26f`.
The nested authenticated runtime plan passes; this does not replace A01,
paired-root content/runtime qualification or physical admission.

The original wrapper attempt failed at AVB partition-name resolution after
successful side-A signing/repack. Receipt `successor-boot-package-r1/result.json`
is `649a30f8f470db24fb2d1982deaf6ff63d63681fa1393aefd361c164c561903e`.
Its `signed_bundle: false` field must not be read as absence of signing: the
successful sign event and published signature establish that it occurred.
The corrected runner keeps per-side signing records and verifies an exact,
identity-bound copy named `boot.img`. Six focused groups pass in both modes;
the actual retained wrapper passes that verification without repack/signing.

CI `source-ci-r5` on cc53c3ec failed after 255.505 seconds, source unchanged;
receipt SHA `10d93f4e35261da4ab3b291b52285d13575144dd67f89b179ac654aee47cff10`. Its worker cap was two, and the former failing healthy
suite passed all 12 tests in 5.310 seconds with original operation deadlines.
The next failure was UFS synthetic inventory sorting. Actual service locale
is en_US.UTF-8, whereas the interactive shell uses C.UTF-8; the same four
filenames sort differently. The production verifier now pins C for deterministic
inventory and ELF diagnostics, with caller-locale and extra/missing-module
regressions. No module bytes, accepted profile or timeout were changed. The focused test
passed in 1.735 seconds; the old verifier reproduces the real locale failure,
and the controlled regression rejects it even under an outer C locale. Receipt
`ufs-locale-fix-r1/result.json` is
`f295bf6e24981854a5ecdddd0a6fa3bb5c4ad4845681f5900e9339927852c6a5`.

## Remaining module guest and CI follow-up

The separately rebuilt QEMU-only S12 shim twins passed in 4.432/4.027 seconds,
11.957 seconds including source/kit verification. Both 252504-byte objects match
`fe2ec84d7b3b0d3fc0d3b859b4dc9f51047bc12f66a343ef94867b1fb1658d9c`.
They remain outside all production module selections and phone payloads.
Receipt `successor-baseline-vm-r1/shim-run-r1/result.json` is
`fa971df9bf1b72a190f6710abf327023aa8d84effbfe130e3bb769b8a43fdba6`.

The remaining 44-module guest passed in 8.096 seconds, peaking at 232.7 MiB in
its 512 MiB/no-swap controller. It streamed only three small retained archive
members and the bounded guest archive; no Arch root image was read. All 41
ordinary modules loaded and remained live until poweroff. PMIC observer and
real S12 each refused the virtual board with one finit_module call/ENODEV;
activation refused through the accepted test-only shim with counters 1/0/0
(BTF COMING/consumer LIVE/validator calls), then the shim unloaded. Packaged PDR
alone lacked BTF by design. Both source/kernel/module identities and terminal
container cleanup passed. This is loader/refusal evidence, not physical
initialization, a successful real S12 pair or raw-PDR BTF acceptance.
Receipt `successor-baseline-vm-r1/run-r1/result.json` is
`37814bb0ca751e8da1b1ea7e4ff466c875166cbb21457b0acf80e4e813a6db0a`;
console SHA is `71a32e81d3f7e9cbe060ee472cd14be803683bdebf3b99c7080d7730ece9f99a`.

Full CI on exact f74 stopped after 84.809 seconds in
`test_already_healthy_fresh_boot_creates_record_after_timer_stop`: its unchanged
five-second subprocess deadline expired. The run had 3 GiB memory/no swap and
CPUQuota200%; peak memory was 638.8 MiB. The subsequent Killed messages belong
to the test runner's process-group cleanup, not an established OOM. The runner
launched all isolated suites without a worker cap; CPU contention is a likely
cause requiring focused verification. Original source and failure are retained
in `source-ci-r4/result.json`, SHA
`f73055743771612da9669148d73b60ceeda1c693e68255f772c7185191711e20`.
The correction must bound scheduling and preserve the existing test deadlines,
failure checks and descendant cleanup before a fresh full-CI run.

The bounded scheduler correction passed its actual queue contract in 7.616
seconds; the unchanged 12-test healthy suite passed in 3.688 seconds. A barrier
fixture detects the old early-refill behavior, and a real 150% CPU quota clamps
an explicit request for 32 workers to one. Peer review is clear. Receipt
`ci-worker-fix-r1/result.json` is
`f2038c9b088a8898e5da86b722d3575eadecc0c082f7b27d7cd32133421dc0a1`.

## Successor kernel and module execution

The following results supersede the pending build statements in the retained
chronological preparation notes below. Production source remains clean at
`f74e719c287e0e3ad998cba2f0caf40f72093e94` in private `worktree`; progress docs
use the separate `progress-docs-r1` checkout to preserve that sealed input.

Kernel `05941d04803f54208da1e9920a81874edc540ca1` twins passed in
2729.501/2698.331 seconds. All 30 declared artifacts match, including the exact
Image `d9a55229f2e0c67e1b856d13c40715b3ec4e3a6fee2594aaa3947d99639e3fb8`.
Final receipt `kernel-hardware-build-r1/twins-result.json` is
`0304a906b9a8d8e65394297205f9c5d46b914b248a76250cfa54c9a175010ef5`.
Both stages exited0 without OOM or cleanup errors. Final cache totals showed
only161 hits among6445 cacheable calls; the live recipe was not changed.

The matching kit derivation copied3378 files/435221596 bytes in9.701 seconds,
with fresh twin header/tool checks. Completion preserved those original bytes
and added the15 power/USB modules, metadata and complete seal in a2.582-second
service run. Packaged PDR is
`7fef279c8a6a1976746211dac2438439e73c3a933ac33deb43945577c2d67253`;
its raw BTF-bearing twin remains retained. Complete kit manifest SHA is
`ec718e80f70344c95bab8726184a967fac4c4e7f8cdc99a3dc01281cf2dc7388`.

Actual module twins passed216.131/38.580 seconds under2GiB/no extra swap and
two CPUs. They preserve the Wi-Fi selector and explicit diagnostic replacements.
All31 raw outputs match; selecting29 alongside the kernel25 gives54 unique
modules. Receipt `successor-module-build-r1/result.json` is
`78225ad1c57cb152e5b1515d99cd78982ea3e13f49a971771c83cd020e26cfa4`.
The stable-path cached comparison took82.1% less time than the first run.

The full selected54 static check passed in a6.253-second service run, peaking
at101.3MiB with zero swap. It binds13278 actual vmlinux exports, selected ELF
exports, namespaces, GPL compatibility, dependencies and the typed S12 edge.
Receipt `successor-module-closure-r1/verification-r1/result.json` is
`f24622708dde534847ef714be9fdad29a8f5919b88c9e32d6a4d845cb9cc9ae0`.
Review corrected kernel-style hyphen/underscore matching for module namespaces;
23 synthetic cases and an actual25-module parser check pass. Full54 BTF and
generic ABI/hardware qualification remain outside this static result.

The ten-component QEMU guest passed in3.797 seconds with exact new Image and
module twins: ten loads, expected registrations, nine successful unloads and
permanent GPI retained until poweroff. Its complete log SHA is
`fcdaf5f600cbb0583d59978c89e0bbaa3f1b8887653eac828622bbe05f08119c`;
receipt is `successor-components-vm-r1/run-r1/result.json`. No phone DT, disk,
Arch root images or physical hardware probes were used. Cleanup passed.

The initial unsigned refresh attempt is retained as FAIL in
`successor-payload-refresh-r1/composition-a/result.json`: kmod34.2 generated
an additional `modules.weakdep` metadata file, causing the exact old inventory
check to refuse after2.897 seconds. Its55 bytes contain only the tool's comment,
with no dependency entries. This is a host packaging-policy mismatch, not a
kernel/module failure. The reviewed successor must explicitly qualify that
delta while preserving37 nested module identities and all unrelated payload
bytes. No signature, physical claim, module insertion or phone reboot occurred.

The narrow r2 correction explicitly accepts only the observed55-byte
comment-only weakdep file, keeps37 nested modules and rejects unknown metadata
or dependency records. Fourteen fixtures pass in both modes and independent
review found no blocker. Actual unsigned twins then passed in10.216/14.215
seconds under512MiB/zero swap. Each archive is57774555 bytes, SHA-256
`c7d757727bc6e9295087b02d207e90d44e43d9ac2f1ccb345a4923c04365e058`.
Receipt `successor-payload-refresh-r2/twins-result.json` is
`a1102e1335f38b3fca09983d251cb18cc7b8fa9b0b628ed0609f2a2699fde0b8`.
All65 old module copies were refreshed; four new inert hardware copies bring
the payload to32 loose plus37 nested files representing54 modules. Corrected
indicator/runtime/shutdown and other unrelated archive bytes remain unchanged.
The previously reserved descriptor remains unsigned and unconsumed:
bundle `kernel-hw-05941-a607a2bb249c918b`, trial
`288d38241fb98dcb2dbc73a9b237dda45f4c5525f356e1770c667d2d7ff35ef6`.
The retained headless DT is the only admitted composition basis. Wrapper,
paired-root and physical qualification remain separate outstanding work.

## ARM64 GPU probe preparation

The small Rust query helper now compiles twice in the retained offline builder
under 512 MiB/no additional swap and one CPU. Both 4,650,408-byte files match
`64f8075dc9b511c85d0b49d7e42c3f2b0f556e19ef73b3e0f28b4bd3418341cc`;
compile/container cleanup took 1.683 and 1.271 seconds. Static closure against
the retained Arch libc, libgcc and loader passes in 0.403 seconds: all 109 strong
imports across the helper and its dependencies resolve with their required
versions. Ten refusal/closure fixtures pass. Root metadata remains unchanged;
existing full-root hash evidence was reused, while small providers were hashed.

The after-run review found 4,103,239 bytes in debug sections. Separate
`--strip-debug` deployment twins are 542,016 bytes, SHA-256
`9f7bf87f99987cb96030489e1dd995e1eaba13c532731bb24c6229d94387fbb6`.
Packaging and verification took 0.063 seconds. Program headers, described
segment bytes and allocated section payloads are preserved, except the ELF
header's section-table location/count/index. Originals remain retained.
This is an 88.3% reduction in uncompressed binary size; transfer speed was not
measured. Private receipts: `gpu-query-arm64-r1/result.json`,
`package-result.json` and `abi-review/result.json`. No target binary or GPU
operation ran. The existing kernel build remains active; module qualification
must wait for its actual successful twin result.

The first successor kernel/25-module build completed in 2729.501 seconds with
successful container cleanup. Its second output build is running. Low cache
reuse prompted a separate 1.645-second experiment with the same compiler/debug
flags: two different working directories produced misses, while separate host
outputs at one stable container path produced a direct hit. All four objects
were byte-identical. Debug logs identify CWD hashing as the fixture's cause.
Evidence: `cache-path-probe-r1/analysis.json`. This supports stable container
paths for the next module runner; it does not measure full-kernel speedup or
justify changing the live kernel build.

An early QEMU virt boot of completed build A passed in 2.633 seconds, using
Image SHA-256 `d9a55229f2e0c67e1b856d13c40715b3ec4e3a6fee2594aaa3947d99639e3fb8`.
The guest reached the exact successor release with zero taint and powered off;
its log contains no checked panic, BUG, Oops or warning markers. Container
cleanup passed. This check loaded no test modules and used no phone DT, disk
or network. The incidental procfs file-size check does not prove an empty
module inventory; no such claim is made. Combined module registration and
physical boot remain pending. Receipt: `kernel-a-boot-smoke-r1/result.json`.

Prepared next stages: `successor-module-build-r1/validation-r2.json` passes
eighteen mocked fixtures in ordinary and optimized Python, with a clear bounded
review. Parent inspection verifies all 57 static inputs and the live-kernel
refusal without creating a real attempt. The runner checks completed kit
lineage and full file inventory before and after each bounded container; it
compares 31 raw outputs, including the two later replacement variants, rather
than claiming the selected 54-module package is qualified.

`successor-components-vm-r1/validation.json` passes eleven focused fixtures for
the combined ten-module guest, including GPUCC driver registration. It uses
the exact future kernel/module receipts, checks loaded module contents, unloads
nine modules and retains permanent GPI until poweroff. Parent review found no
material blocker for this generic-virt scope. No admission or actual guest run
has occurred; kernel twins and module compilation still precede execution.

## Current phone and display preparation

Kernel-first followup produced an initial external FTS3658U driver in private
`touch-driver-r1`. It accepts only normal ID0x5652, preserves native fractional
coordinates, and performs no firmware upgrade or boot-ROM fallback. Review
removed the alternate3518 ID from this first component and stopped treating
unused UP coordinates as active position data. Optimized and UBSan host runs
each pass24,324 checks; six disabled-DT tests pass. Exact current-kernel module
twins pass in9.062 seconds:373416 bytes, SHA-256
`fc94acd0bc6cd6ce4900e5ccb62c3edb6ca6c17ae332cefdb0ed31d6624bbb60`.
Receipt:`touch-modules-r1/result.json`. No module registration/probe on the phone
is established. Final source review passes; suspend/resume remains explicitly
unsupported in this first component.

Repository integration `e8cebfcd` now carries the identical reviewed C/header,
external Makefile, shared C fixtures and disabled overlay. The portable
`scripts/device/test-rog5-front-touch.py` is linked in the README and wired into
the existing repository runner. Actual integration-tree runs pass eight tests
and 24,324 checks per C build mode under ordinary and optimized Python in
0.573/0.520 seconds. Shell syntax and diff checks pass. Full integration CI
has not run while the kernel compiler is active; the earlier full CI remains
evidence for its own source, not this new driver integration.

The exact f17 GENI I2C/GPI provider builds now pass with identical twins in
16.832 seconds. GPI is SHA-256
`2d80d8a82dd3c8a106fc658f43e5d263603ea144ee2253becc6f6fcbf69b4132`;
GENI I2C is `e02c93504574ca5fb6191359048a7767af1405fb4e29c34e62c694a349256fdf`.
Both have matching vermagic/BTF and built-in symbol providers. The three-module
stack passes exact-V9 guest registration in 2.687 seconds. Touch and I2C unload;
GPI refuses ordinary unload and remains `[permanent]` until guest shutdown, as
its source has no module exit. Receipts: `touch-bus-modules-r1/result.json` and
`touch-stack-vm-r1/result.json`. The VM supplies no phone I2C, DMA or rail proof.

Actual touch DT composition against both V9 and the display candidate preserves
unrelated properties, boot CPU and reservations; twelve hostile-delta cases
pass. Disabled variants add only four nodes and three symbol properties.
Enabled proposals change five statuses, preserve disabled SPI4 and make L8C's
always-on vote effective. Touch unbind releases only its own vote, so it cannot
restore the pre-probe physical rail state. Receipt:
`touch-dt-composition-r1/result.json`, SHA-256
`21ca1f657ca43ad9e77b86e66ec8c54297e3fe2b2400ed2719d1f1b648281812`.

The GPU audit identified one required built-in fix: propagate GMU power-level
probe failure before later initialization. Existing patch 0012 applies directly;
eight extracted actual-source fault-injection cases pass while the baseline
fails. Fixes 0026/0035 are already present; no duplicate or diagnostic patch was
added. Clean successor source `05941d04803f54208da1e9920a81874edc540ca1`
contains only 0012 over f17. Its source/config/compiler/release preflight passed
in 21.955 seconds; the unchanged configuration produces expected release
`7.1.4-g05941d04803f`. Kernel and 25 scoped module builds are **RUNNING** under
private `kernel-hardware-build-r1`; no completed successor is claimed yet.
Separate output directories share the existing verified compiler cache.
The build uses two CPUs, 6 GiB with no additional swap and a 4 GiB disk cache,
with bounded runtime and disk/memory-reserve monitoring. Await the owned runner
and its `twins-result.json`; do not restart it or reuse f17 module evidence as
successor qualification.

Three exact firmware files (1,153,192 bytes total) were recovered from official
linux-firmware 20260622 commit `b2722d241309a1872446c1d00c2e812bad055f89`.
All existing manifest sizes/hashes match; licenses, WHENCE and provenance are
retained. The sm8350 ZAP path is materialized from the upstream qcm6490 link.
Fresh parsing/readelf finds one relocatable 1976-byte segment at file offset
0x101000, physical address 0x1000, needing 4096 bytes within the unchanged
8192-byte reservation. This corrects the earlier audit prose that confused
physical address with file offset. Three malformed-layout fixtures refuse.
Receipt: `gpu-firmware-r1/result.json`, SHA-256
`427bda95710514d1d7060574a66dd969ebe7afae6919f9db11893359d19f54d1`.
There is no SCM authentication, hardware initialization or command-submission
proof. First DRM open initializes the GPU and must be an explicit bounded test.

The after-run improvement is concrete: use the already supported compiler cache
without bypassing exact-output state checks, and stop an owned build container
even if its launcher exits first. Nine cleanup fixtures pass in normal and
isolated modes, including stop/kill, ownership rejection, corrupt CID and
inspection failures. Receipt: `kernel-build-runner-review-r1/result.json`,
SHA-256 `81afd8c5b036815f9f061dd42990b95acd0a6e5d4bf9633fceb52ee39ab1d16f`.
Cache timing/benefit remains to be measured; the preflight and regression
passes do not constitute a full kernel-build result.

While the same kernel build remains active, unsigned GPU DT twins now pass on
both exact base variants. V9+GPU is 107916 bytes, SHA-256
`f6e651c680beb4f222fdcf4aadc0834ddaf28fb6a95ef0808fd5027020b3d6f7`;
display-V9+GPU is 109468 bytes,
`5ce36eecfe49601034e89cb3d98536e3d558b1399d2576004f5eb1aba713b89b`.
The five-property delta preserves all other properties and boot metadata,
including the 8 KiB ZAP region. Eight test groups pass normally and optimized;
the parent independently rechecked all four recorded output files. Receipt:
`gpu-dt-composition-r1/result.json`, SHA-256
`cad40592b18ed03b233a9c4d8e7e1fc12513aa60b859cdb5032bd67ede937c83`.

The new private Rust GPU query helper is ready for ARM64 build preparation.
Fourteen native mock tests pass in both debug and optimized builds, warnings
denied; ARM64 C assertions check the exact UAPI structures, syscall flags and
ioctl encodings. The check caught and corrected the x86 `O_NOFOLLOW` value
before a target build. The helper pins a metadata-only O_PATH handle, then
performs one operational open, VERSION identification and three scalar
GET_PARAM queries with one close. It preserves primary and close failures
independently. The operational open can initialize GPU hardware; the helper
has no admission authority, submission or retries. Stable boot/device binding
and an external deadline remain controller responsibilities. Tests use mocked
ioctls and ordinary-file metadata fixtures; no helper main/device execution or
ARM64 binary build ran. Final reviewed receipt:
`gpu-query-helper-r1/result.json`, SHA-256
`4ede7e7c94f546028babf5077eeee1f036a5cd9e758796198b9f0c03081c14a7`.

The complete successor package needs 54 distinct modules: the current 25
targets, 22 radio outputs and seven additional hardware/helper modules. Four
radio outputs are retained package extras outside the loaded root closure;
they are preserved. The recipe keeps the WCN6851 selector patch and replaces
the two generic power providers with the accepted diagnostic variants. It
forwards matching ccache compiler commands to the unchanged radio builders.
Seven focused tests and review pass; no module build has run. Receipt:
`successor-module-plan-r1/result.json`, SHA-256
`75cdd6078f70f1a46b8d73f5fe0574675e9c2fdd64e8d7db1d98641040502b84`.

The new kit deriver waits for successful kernel twins, verifies exact recipes
and artifacts, and compares generated headers/config markers and executable
tools across completed A/B outputs before and after copying. The accepted
older resolve_btfids twins differ in debug paths/build IDs; only that exact
tool may use the explicitly recorded debug/build-ID normalization on disposable
copies. Raw kit/build bytes remain intact and command metadata is inventoried
separately. Twenty-three fixtures pass normally and isolated, including header,
tool, mode, normalization and copy-time drift. Receipt:
`successor-kit-prep-r1/review-fixtures/result-r2.json`, SHA-256
`d9a914b8355c671c9859974f553433f1dcb1e3409afbb81bcc6f7739c44de41c`.

A separately reviewed completion recipe adds only new-release build metadata
and the 15-module power tree, verifies the packaged-copy-only PDR BTF exception,
runs depmod and seals the complete kit externally. Seven fixtures pass in both
Python modes, including the actual retained old PDR pair and a changed code
section refusal. Receipt: `successor-kit-completion-r1/validation-r1.json`,
SHA-256 `de5c2a93a9ca3ce4efd18cd85e2059dd491fcf79e594a471849968acd7e56f33`.
Neither deriver nor completion has run on a real successor kit. The direct base
metadata is f17; existing external builders therefore use that base's timestamp,
with matching twins, rather than copying the older ancestor metadata.

The configured display autoload audit expanded to2,453 root nodes, selected
effective unit/rule/helper text, the final archive catalog and radio manifest.
Udev's kmod loading is real, but its current-release module index is absent.
Historical7a5 REFGEN remains in the old module tree; dormant display scripts
have no enabled units. Four isolated host-kmod dry-run name/alias lookups refuse
the new modules even when the inert payload is present. These are static
configured-path results, not execution of the actual Arch coldplug path.
Receipt:`display-root-autoload-r1/result.json`, SHA-256
`26a8daf76c0323230867cc3f17c6fb079d3c5bfda703e2b9d59f38324a76f049`.

Packaging review identified a supported embedded signed RAM target route that
keeps the paired root images unchanged, plus concrete remaining integration
work. The target's healthy service still needs a matching pending userdata
trial record; embedded recovery does not create that record. A fresh guarded
operation and backup/readback qualification are required. The wrapper needs
fresh canonical registration and an exact-size admitted boot controller;128MiB
is expected from the comparable retained wrapper, but the new actual size has
not been measured. Do not reuse R01 authority or claim autonomous V11 recovery.

Fresh read-only full health passed in 1.252 seconds on V9 boot
`7c945aa5-80d0-4af2-aa76-113d68e23ac5`, kernel `7.1.4-gf17befd4ef17`.
A separate 0.244-second inventory opened no device nodes and changed no hardware.
There are no DRM card/render nodes, framebuffer or backlight, and only the
three qualified key inputs. MDSS, both DSI controllers, GPU and GMU are disabled
in the current device tree. The inventory preserves absent/error observations;
`/sys/class/drm/version` is an ordinary attribute, not a DRM device directory.

The [earlier 60 Hz result](2026-09-02-display-status-screen-development.md)
proves display/status-screen behavior on its own kernel and DT. Older Adreno
registration/GMU-entry diagnostics do not prove rendering. The current kernel
already has the required MSM KMS/DPU/DSI implementation built in, so the next
display preparation can use external panel and REFGEN regulator modules.

The 448-line panel source extracted from the existing patch is byte-identical
to the historical qualified source, SHA-256
`45e8bcb9c608645e76ae888e33f3c4d2e9096338eae95d59c67b56f2f428b892`.
REFGEN source is unchanged from the exact current kernel. All their undefined
symbols resolve to current built-in exports. Twin external builds used the
read-only exact kernel kit, one compile job and a 2 GiB container limit:

| Module | SHA-256 | Result |
|---|---|---|
| `panel-asus-rog5-ams678.ko` | `5bacaed0279d6e94b08003cc4dfb35f8eb17c33f643190ceef78ef40aa7f0f6c` | identical twins, vermagic/BTF/export closure PASS |
| `qcom-refgen-regulator.ko` | `f0ee47b2f1f5b7bd70fe1c486322a04f6509be04c58c10ecb5890d82a2272fc6` | identical twins, vermagic/BTF/export closure PASS |

Build and verification took 12.967 seconds. Exact-V9-Image QEMU load/unload and
driver-registration checks passed in 2.199 seconds. The VM has no ROG5 panel;
these results do not prove physical probe, scanout or brightness cleanup.
Private receipts are under `rog5-denial-20260910-r1/display-modules-r1`.
No module insertion, display activation, reboot, signing or phone write occurred.

## Denial source and build order

**Priority correction:** the user subsequently requested kernel and hardware
bring-up before Denial. Root stopped the exact live dependency container and
reaped its runner after 796.080 seconds. The bounded stop returned zero;
the raw sync result remains FAIL with exit137 after the stop grace period.
This was a deliberate interruption, not a reported memory-exhaustion event.
`engine-build-r1/priority-stop-entered.json` and `priority-stop-result.json`
preserve the reason and action; cache and partial source remain intact.
Do not follow the older running-job checkpoint below as a restart instruction.
Engine hooks, compilation and AOT assembly remain deferred during kernel-first
bring-up. Minimal hardware test programs remain appropriate for DRM/EGL/input
qualification. The real-phone Denial completion requirements remain unchanged.

Fresh read-only phone health passed in 0.938 seconds on the same accepted V9
boot, with installed identities and storage/power/healthy-selection checks.
Private receipt: `denial-engine-prep-health-r1/result.json` under the CPU-startup
evidence root. No hardware activation or reboot accompanied this check.

Engine preparation has now started in private `engine-build-r1`. The derived
builder image is `237f1e2fbb6bd4007dff61e165c60676e5668f716a4a2397f5e590a2a80303ee`.
It reuses the pinned Rust builder and adds thirteen host-tool packages from its
retained signed apt indexes, with no upgrades or removals. The reviewed plan
downloads 3.536 MB and estimates 13.5 MB additional installed files; actual
provisioning passed in 20.003 seconds with approximately 16 MB disk growth.
The installed-package inventory SHA-256 is
`5f1aef67d2c9a30b84b72f11efaf77df5c46e5e5008a463371bff9962bba34e2`.

Exact detached Flutter `d728e61e7d835e02c453c70ae9523a40f6c03215` and
depot_tools `580b4ff3f5cd0dcaa2eacda28cefe0f45320e8f7` checkouts passed in
22.003 seconds, using approximately 251 MB additional disk. Their origins and
clean tracked files were verified. The initial runner and its original hashes
remain retained; review then added exception-safe cleanup and exact source
checks around dependency synchronization and hook execution.

At the recorded checkpoint, the single dependency-sync container is running,
limited to 3 GiB RAM with zero additional swap, two CPUs and 512 processes.
The watchdog admits sync above 80 GiB free, retains a 10 GiB floor, stops after
60 GiB growth or two hours, and records terminal results. Bootstrap CIPD setup
is quiet because the pinned upstream wrapper suppresses its output; increasing
cache size and measured ingress confirm download progress. Twelve bootstrap
tools have immutable instance pins in the retained manifest. This checkpoint
does not establish a fully resolved or downloaded closure.

The next continuation must resume the existing job and inspect
`sync-result.json` and `sync-source-identities.json` before hooks. Flutter,
Skia, Dart and both depot_tools checkouts must retain exact origins, commits,
tracked cleanliness and the pinned root DEPS hash before hooks execute and
afterward. GN generation, engine compilation, AOT assembly and phone deployment
have not started. No phone action or human readiness request occurred during
this host preparation.

[Denial v0.3.1 source](https://github.com/denialwm/denial/tree/85b2303e2f09ae7b7b993641f90061a200f03d53)
contains its mobile shell, selected with `DENIA_SHELL_PROFILE=mobile`.
The [source lock](../configs/denial/source-lock-v1.json) pins Denial, Flutter,
Skia, depot_tools, Rust 1.98.0 and the Cargo graph. The shallow source checkout
used approximately 36 MiB; no engine or release package was downloaded.

The [build guide](https://github.com/denialwm/denial/blob/85b2303e2f09ae7b7b993641f90061a200f03d53/docs/BUILDING.md)
supports ARM64 source builds, but the supplied reference scripts and checksum
metadata target x86-64. A separate target-aware recipe is required; changing
only a destination path does not make an ARM64 build. The Rust compositor loads
its engine dynamically, allowing native compositor/control-client compilation
before the engine is available. Build that smaller part first, then the matching
ARM64 release engine and host AOT tools, then mobile shell/assets/ICU. A JIT
development bundle needs matching additional engine artifacts and is later work.

The isolated Rust 1.98 cross-builder is provisioned as image
`0f429c6fd38e4400d8638bff1f7da0170375275ab29201e327a3e236ed9df16d`.
Its 280-package plan has SHA-256
`25a81daac5d02cb6012d8b963623b64bedddfabfbf0ea6ac5cf1b8d89be59f0f`;
installed-package and signed-repository inventories are retained privately.
Provisioning passed in 286.036 seconds. No host packages or binfmt registration
were changed. The failed foreign-Python installation and unsupported build CPU
flag are retained; the corrected recipe uses native host tools and cgroup CPU
limits. Exact Rust archives were reused after streaming hash verification.

Locked Cargo fetch passed in 26.010 seconds. Offline ARM64 control-client
compilation passed in 22.010 seconds using one job and a 3 GiB memory cap.
Its 886880-byte binary has SHA-256
`36128080aa4f4f530ab60960eb0d8e184285e39a6a9244662459bd3a02da8eba`.
ELF inspection confirmed AArch64, and help/version passed under isolated QEMU.
It identifies itself as `development`; this is not a published release or a
compositor session. The original
fetch attempt selected unavailable slirp4netns; the successful run uses the
host's installed pasta network backend. Compilation runs without networking.

The full `flutter` feature build of `deniald` and `denialctl` passed in
464.094 seconds with the same one-job/3 GiB limits and unchanged upstream source.
Both final binaries are AArch64, use `/lib/ld-linux-aarch64.so.1`, have no
RPATH/RUNPATH, and passed help/version under network-disabled QEMU in 1.652 seconds.

| Native output | Bytes | SHA-256 |
|---|---:|---|
| `deniald` | 15979872 | `8698b0716c0ab16ab5c33d618ae52cef0cd8c0966ad356cf2ca49d78a0ba8591` |
| `denialctl` with full features | 886872 | `da22a0bd76e183cd25ce45ef532ae3ee533703dd5f6e00809ce2f3415b8566df` |

The earlier control-only binary is retained separately. These checks prove
linking against the prepared target libraries and terminal CLI paths only;
they do not load Flutter, acquire a seat, render, or prove the final Arch
runtime library closure. Private receipts are in `cargo-arm64-r2`.

A subsequent read-only audit of the retained effective Arch lower/upper layers
passes interpreter, library, version and strong-symbol closure for `denialctl`.
Arch glibc 2.43 satisfies the required GLIBC_2.39 floor. `deniald` is missing
`libgbm.so.1`, `libseat.so.1`, `libinput.so.10` and `libxkbcommon.so.0`;
its existing libc/libm/libgcc/libudev providers satisfy the inspected needs.
The effective upper libudev overrides the lower copy. Only 4905097 bytes of
selected ELF files were extracted under 512 MiB/zero-swap limits. Root metadata
still matches the earlier full-hash proof; the large images were not rehashed
or mounted. This is static closure, not target execution. Receipt:
`arch-native-abi-r1/result-r2.json`.

The engine recipe separates the ARM64 embedder graph from x64 host tools.
ARM64 AOT needs an x64 executable generating ARM64 code from the target graph;
the host graph's x64-targeting compiler is insufficient. Unmodified asset
assembly needs host GTK artifacts, which stay outside the phone bundle.
Pinned Flutter compiler/sysroots are separate from Rust's Ubuntu sysroot.
Engine graph generation and compilation remain pending. Hot reload needs a
matching debug/JIT engine and development assets; release AOT cannot supply it.

## Durable build capacity and repository checks

Reviewed cleanup removed 179337 single-link regular compiler-cache/object files
from 31 completed historical build roots: 72174505984 allocated bytes, or
67.218 GiB. All 15559 protected outputs passed post-cleanup checks; critical
Image/config identities were rehashed. Sources, final images/modules, logs,
recovery artifacts and current kits were preserved. Private manifests, deletion
log and terminal receipt are in `capacity-audit-r1` and `capacity-reclaim-r1`.
No visible active references were found. Privileged file descriptors/mappings
were not globally observable; the receipt states that limitation. Only
regenerable intermediates were eligible. Cleanup completed in 99.043 seconds
without errors.

Approximately 82 GiB was free before temporary full-CI fixtures. The estimated
40–80 GiB engine workspace is not a measured minimum. Keep large inputs on
durable storage and preserve the host reserve while measuring actual growth.

The first active-suite run lacked the pinned Android unpacker. Restoring its
exact bytes made all 46 composition checks pass. The workflow's active tier
also omitted that dependency. Both GitHub test jobs now bootstrap the pinned
tools for active checks while skipping the unused canonical boot template.
All 37 workflow/tier tests pass. Full local CI subsequently passed at frozen
source `752742fc2f7aeb1ce19d8389a81658399f1a28fc` in 563.196 seconds, including
the 95 native recovery cases in 31.090 seconds. Source remained clean.
Receipt: `source-ci-r3/result.json`; log SHA-256
`3dc9812709d043d140ef0977a418ec76b5b9975300704536524e1c2d9704dd2e`.
Optional private ARM64 environment replays reported skips; the actual module
and native CLI emulation proofs above are separate completed artifact runs.

The first full-CI attempt hit a Wi-Fi fixture's five-second deadline under an
added two-CPU quota; its focused rerun passed without that quota. The second
attempt progressed further but hit three native recovery fixture timeouts and
a teardown wait error. Responder/test bytes match the earlier 95-test PASS.
The three cases then passed in 7.145 seconds, followed by all 95 cases in
32.321 seconds with unchanged deadlines. External process sampling observed
uninterruptible waits in `fsync`/filesystem journal paths. This supports host
I/O latency as an explanation but does not capture or prove the original failed
wait's cause. All failed receipts remain retained; no production guard or
fixture timeout was relaxed. These failures remain separate from the final CI PASS.

## Remaining hardware boundaries

The current-base display DT must preserve newer buttons, storage, memory and
radio properties; the historical display DT cannot substitute for it. A guarded
display candidate still needs exact package composition and prepared observation
before any physical test. GPU acceleration remains unproven.

The new [current-V9 builder](../scripts/device/build-display-v9-candidate-dtb.py)
and [verifier](../scripts/device/verify-display-v9-dtb-delta.py) pin the current
107878-byte base and reuse the unchanged historical structural comparator.
Unsigned twins match SHA-256
`2ee1ed4b43083bb7e50631269009107efbe0ffed89207acce3c8066f6ba9e4df`:
exactly ten added nodes and fourteen changed properties. Nine focused tests
passed in normal and optimized Python, including rejection of non-display drift,
wrong identities, linked inputs, overwrite and tool failures. Review also exposed
node comparison overlooking boot CPU and the FDT reservation map; the new wrapper
now preserves both and rejects mutations invisible to node comparison. The focused suite
requires the explicitly supplied retained base; these results are not a new full
CI or admission result. Updated private receipt: `display-dtb-r1/result-r2.json`; the earlier, narrower
receipt is preserved.

The [display payload composer](../scripts/device/build-display-trial-initramfs.py)
accepts the qualified corrected-buttons unsigned base, preserves its runtime,
shutdown, radio and buttons bytes, and adds exactly two nested inert modules.
Only the descriptor/catalog change among existing members. It rejects historical
buttons bytes, mismatched inputs, reused identity and existing display opt-ins.
Six composer tests, three display closure/order tests and one actual runtime
installer inertness test pass in normal and optimized Python; six unchanged
indicator tests also pass. The production module bytes match their pins.
The new suite is wired beside the buttons composer in the repository runner.

Actual unsigned initramfs twins composed in 14.745 seconds total after the
frozen-source CI PASS. Both are 56081476 bytes, SHA-256
`3fcbf6d3dfa9dd45719c0ab167940961c76ee10a5500c8913bfd3e76eff294dc`.
The exact corrected-buttons base is SHA-256
`97de4bd3b2a47fa7c6468cbe1fe0116a7288b043279d028c73d234a3c60b33ee`.
Their fresh descriptor/catalog and preserved-member checks pass; no claim,
signature or activation was created. Receipt: `display-compose-run-r1/result.json`.
Temporary full-CI fixtures were removed by restoring the original sparse
checkout; all Git objects remain retained and approximately 81 GiB is free.

Complete boot-image qualification and final paired-root autoload absence remain
pending. Standard current-release module search paths are absent from both Arch
layers and inspected standard autoload configuration contains no panel/REFGEN
entries; that bounded audit does not cover arbitrary services or nonstandard
copies. The new DT enables built-in MDSS/DPU/DSI providers before userspace; unloaded panel
and REFGEN files do not mean all display hardware remains untouched until P24.
A future trial must first qualify the new-DT boot, then load the two modules
under the prepared controller. Physical scanout/blanking remains NOT RUN.

The retained ASUS front-touch source has variant-specific identification,
power sequencing and event decoding. Generic EDT compatibility is not proven
by the shared FocalTech name. Inspect the exact board wiring and protocol before
adding a binding; do not carry vendor automatic firmware upgrade into a first
probe. Touch, physical display and the native Denial session remain NOT RUN.

The private touch audit includes nine passing synthetic frame-decoder cases.
They establish the source-derived parser behavior, not a real controller read.
Retained vendor source now matches ASUS MP2 to the ZS673KS-MP overlay chain and
confirms I2C4 GPIO20/21, reset22, IRQ23, enable131, L3C at3.008 V and shared L8C
at1.8 V, with1080x2448 extents. GPIO131's electrical downstream net and upstream
regulator rails are not specified by that source. Current regulator code permits
omitted upstream supplies through dummy-parent resolution; missing schematic
data does not prohibit preparing a disabled candidate. Keep real L3C/L8C
consumer phandles, do not invent upstream links, and qualify actual power/ID
behavior separately.

The stock firmware's full-update payload metadata and selected operation hashes
now validate an 8 MiB DTBO image, SHA-256
`531af0246723b15181649063fa5e2f5407eec7804e01485920694a8722e09ea0`.
Bounded reads totaled 620184 payload bytes across inventory and reconstruction;
no other partition or complete firmware payload was materialized. This does not
independently authenticate the entire firmware archive. Eighteen payload-reader
and eight table/bounded-hash fixtures passed. Actual runs stayed below 28 MiB
RAM with no swap; source and original/corrected validation receipts are retained.

Only table entry 5 matches ASUS MP2 with board selector100,0, SHA-256
`e00aced418da0d0ad3e3e3e1572ae93468c862f451786a0a6360d8660200a2ba`.
Ordered fragments61→83→142 confirm front address0x38, GPIO22/23/131, ten
contacts, final1080x2448 extent and L3C/L8C consumers with L8C always-on.
The earlier2400 extent is superseded. Base regulator voltages and bus pinctrl
remain source-derived external properties; the DTBO supplies no missing board
schematic. This is offline variant evidence, not a new physical-board reading.
Receipt: `stock-touch-dt-r2/result.json`, with its scope clarification retained.

S06 shutdown and R01 autonomous recovery remain failed independently. The
buttons/LED component result remains accepted. Human tests must be completely
prepared before asking for a fresh Ready, with one prompt at a time and
automatic recording.

Final read-only phone health passed in 1.357 seconds on the same V9 boot
`7c945aa5-80d0-4af2-aa76-113d68e23ac5`. Installed identities, power/storage
guards and healthy selection remain valid. No phone module insertion, signing,
reboot or display/touch activation occurred during this checkpoint.
