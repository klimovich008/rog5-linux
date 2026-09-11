# Denial native mobile bring-up

The selected goal is Denial Wayland on the ROG5 OLED with touch and accelerated
Adreno graphics. Cellular is excluded. The initial integration base is
`6651d598b9e2ce1f4a83b85630cdddfc2debb377`; the dirty original workspace and
accepted server/recovery artifacts remain preserved.

## r46: reproducible OLED successor payload

`oled-successor-payload-r1` composes a fresh identity over the physically
observed 05941 archive. It reuses the pinned bounded newc parser/writer and
independently reopens each output. Membership and every unrelated byte/metadata
field are preserved; only `trial-descriptor` and `boot-files.sha256` may differ.
Ten small real-newc checks pass in 0.026 s, covering forged catalogs, unrelated
module/runtime/nested-package changes, metadata drift, reused identity, changed
membership and truncated input. No old recognizer was widened.

Both actual archive builds passed in sequential 512-MiB/no-swap scopes, with
host wall times **4.877 and 4.625 s**. Their identical output is 57,774,563 bytes,
SHA `d108d868df3c8ba5f4e8c30bc4da128d73a470379afff4a30be51b121e81e825`.
Of 724 members, 722 remain unchanged, including all 32 loose module copies,
nested radio archive, userspace, firmware and shutdown behavior. Existing
panel `c554d3f5…` and REFGEN `efc31c29…` remain inert. No kernel/module build,
depmod, root-image edit, signing or phone mutation was performed.

The sole new identity is bundle `oled-05941-a2be906cd7b36636`, trial
`b52ead05459f96ae5acde920c903d4ca3138a96083a7b4dbabfc941274fcb242`.
Its profile binds the retained display-only DT `2ee1ed4b…`; the descriptor and
`wrapper-recipe.json` agree on bundle and current release. These are unsigned,
unregistered inputs. The working r2 headless packager must receive a separately
reviewed OLED adaptation; its existing exact-profile refusal is correct.

A **2.045-second authenticated read-only probe** verifies the unchanged phone
boot at 4,347.54 s uptime, early healthy commit, storage/power/readiness and the
restored old selection. Both exact display modules exist in their inert RAM
location and remain unloaded. The current standard module search tree has no
files for this release; there are no DRM/backlight nodes or fb0. This is current
runtime evidence, not qualification of future display-DT early probes or the
configured effective-root autoload paths. The screen has not been tested.

Next: adapt the current successful boot wrapper's qualification to the new
identity-only preservation receipts and display DT, retain unchanged module/VM
and root-content evidence where applicable, build/verify signed twins, and
finish the prepared boot/module/blank/frame controller before asking Ready.

## r45: restore selection while retaining the healthy successor boot

`current-target-restore-r1` adds an exact-current-boot generator and one-use
normal-USB SSH coordinator. It reuses the unchanged atomic ARM64 exchange
helper, original custody and pinned descriptor/RAM primitives. The old V9/V11
wrapper and consumed boot claims are unchanged. Before and after exchange it
requires exact boot/release/bundle, sealed tools, protected storage and userdata
geometry, power/thermal thresholds, quiescent rollback timers/healthy writer,
matching transaction records and custody. It verifies original inode restoration
and retention of the replaced new record. Uncertain outcomes never retry.

Offline qualification covers 17 cases using the actual ARM64 helper and sealed
BusyBox/loader under bwrap/QEMU, with physical telemetry, systemd and tmpfs
explicitly simulated. Summed passing case time is 194.746 s. Seven cases passed
before the fixture writer hit a read-only custody file; that harness failure is
retained, and the remaining ten passed after fixing only fixture file mutation.
Lost helper status and unsafe post-helper telemetry leave completed exchange
bytes preserved but refuse success. A repeated restoration also refuses.

A separate private health-module instance expects the restored old selection
while requiring the same target runtime, early healthy commit and boot-bound
markers. Original health inputs and observation bytes are untouched. Eleven
health cases pass in 0.020 s; nine host order/output cases pass in 0.009 s.
The reviewed preparation locks 78 input files to clean source `e98c826b`.
No rebuild, signing, root-image rewrite, fastboot command or password was needed.

The actual one-use run **PASSed all five phases in 7.656 s**: authenticated
preflight; RAM staging; atomic restore; independent read-only state observation;
and full restored-selection health. Boot `de90d177-3532-49e0-9bfd-8f8c65889a8d`
and kernel `7.1.4-g05941d04803f` remained unchanged. Final uptime was 3,548.72 s;
early healthy commit remains 64.957282 s. Current selection SHA is now
`ed3a62d198a2e33d26093e079534315ae86ab28c91f48805463fd025c5b88b75`.
The former new healthy record remains in the transaction exchange slot; old
backup and original custody are retained. RAM restore entry/completion and
persistent restore-intent/completion are consumed and must not be removed.
This restores old boot-selection eligibility, not physical fallback qualification.
The r43 controller result remains FAIL and S06/R01 remain open.

Next-display inspection revalidated existing display-only DT `2ee1ed4b…`,
successor panel `c554d3f5…` and REFGEN `efc31c29…` with exact 05941 vermagic.
No module rebuild is needed. The old display plan/packaging recipe names f17
and f236e710; those identities must not be reused for the successor. OLED adds
L12/L13 children under the RPMh provider, whose source registers them at probe,
so a live overlay is not an established shortcut. Prepare a fresh exact display
DT boot and inert payload, then the bounded module/blank/frame sequence. No
OLED/touch/GPU or Denial hardware acceptance is implied by the recovery.

## r44: integrate host fixes after the successful kernel observation

The r43 controller remains FAIL; its real 23-minute capture and authenticated
kernel health remain independently PASS. Executed private sources were frozen
under `post-trial-driver-fixes-r1/executed-sources` before the proven USB-transition
and fallback-adapter patches were integrated. Transitive source pins were
refreshed; the original live qualification, terminal receipts and consumed claim
were preserved. An actual 30-file input check passed in 0.104 s and the production
launcher still refuses the completed attempt before authentication or mutation.

The first regression batch stopped on an assembly fixture's assumption that no
real execution directory existed. A partial output override then correctly
tripped component-path agreement. The final assembly check preserves existing
directory metadata. Launcher tests use isolated attempt paths and explicitly
simulate the global claim boundary; the production consumed guard is untouched.
All failed test outputs are retained. No expensive kernel, module, package or
full-CI build was repeated.

The separate SSH worker had the same three-value unpacking bug as the fallback
worker. Its old mock duplicated the wrong contract. A real-adapter fixture
reproduced failure before changing the worker; after the two-value fix all 13
worker cases pass in 0.405 s. Final affected checks pass **63 cases in 53.078 s**
including process launch overhead: worker 13, fallback route 19, transport
injection 3, assembly 3, launcher 21 and complete simulated flows 4. Earlier
integrated transition/route/admission checks passed 32/25/24 cases on their
retained pre-sibling-fix sources; do not relabel those bytes as the final source.

One local health invocation failed before transport because it called a
nonexistent worker convenience API; its result is retained. The corrected
read-only call authenticated the unchanged successor at 2,387.56 s uptime in
1.596 s. A subsequent 1.895-second guarded recovery inventory authenticated that
same boot at **2,620.11 s**. It verifies both 390-byte old-selection copies and
matching stage-intent/completion, with restoration not entered and the old RAM
custody directory absent. The existing health predicate still passes all
identity, readiness, service, storage and power checks. Current selection is
still the new healthy record; no phone write or reboot ran in r44.

The retained atomic helper can exchange a matching healthy successor record back
to the exact old selection. The existing outer wrapper only admits V9/V11;
current-target guard, RAM staging, focused validation and review remain to be
prepared before that mutation. This is a recovery plan, not restored eligibility
or physical fallback qualification. Then prioritize minimal OLED scanout before
touch/GPU and Denial. The user's unsolicited Ready was released because no
physical test was prepared; a future human step requires fresh readiness.

## Authentication blocker revalidated

Checkpoint r34 confirms the prepared password probe and five relevant source
hashes are unchanged. The actual r1 attempt remains terminal with
`sudo: a password is required`; no r2 attempt, trial directory, execution
directory or live qualification exists, and no relevant child process is live.
The blocker has recurred across r32–r34. Independent launcher preparation was
completed in r33; repeating its passing tests would add no evidence. Mark the
goal blocked until the user supplies fresh availability for the local password
dialog. No authentication prompt, phone action or new claim was started.

## One-use launcher and credential lifetime

Private evidence: `successor-live-driver-r1/launcher-qualification-r1.json`,
`launcher-tests-r1.stderr`, `launcher-tests-r2.stderr`,
`launcher-regression-r1/result.json`, `launcher-baseline-r1` and
`launcher-review-r1`. While the host password-dialog availability reply remains
pending, the separate kernel trial launcher is now implemented and tested.
It is import-only and cannot register or create a claim. Missing qualification
refuses before creating a trial directory or opening authentication.

The launcher binds the final clean source, qualification and exact registered
claim. Authentication and a first successful noninteractive sudo refresh happen
before consuming the claim. It then assembles the concrete driver, creates the
one-use controller, writes its digest-bound admission record, and runs the trial.
Admission now includes the launcher digest; the input lock includes the new
credential helper. The original source bytes and lock are retained.

The credential helper schedules fixed `sudo -n -v` refreshes every 45 seconds,
bounded by 5400 seconds and the controller context. It uses the same parent as
the detached root launchers, retains bounded subprocess output and fails new
phase gates if credentials expire or the refresh thread dies. It never prompts
for a password. This is prepared behavior: actual sudo refresh is unverified.
The prepared graphical probe remains unchanged and can start immediately after
the user's fresh availability reply.

The new thread made the remaining RAM-transfer Python `preexec_fn` unsuitable.
That transfer now applies its unchanged core/file limits through fixed prlimit.
The driver update is hash-only. A real child reads a four-byte sealed descriptor
and reports zero core limit and one-MiB file limit while another thread is alive.
No production image transfer or phone operation ran.

**14 initial launcher/credential tests PASS in 0.852 s; 15 final tests PASS in
0.806 s.** Fixtures cover authentication loss, initial refusal before claim,
partial claim failure without retry, admission written before run, process and
thread cleanup, and source drift. Review tightened unfinished-recording cleanup:
requiring cancellation always keeps the launcher result failed. Actual controller
construction and admission serialization are used; claim/sudo/phone execution
is explicitly simulated. An actual preparation check refuses the missing final
qualification without creating an attempt.

Affected regressions pass **48 cases in 36.646 s** including launch overhead:
17 RAM callback/process cases, 24 admission boundaries, three admission-driver
cases and four complete assembled flows. No kernel/module/root/image build or
full CI was repeated. Host password/root probe source hashes remain unchanged.
No dialog, live ADMITTED record, new claim, trial directory or phone action exists.
Actual host authentication, root handoff and final registered-claim qualification
remain prerequisites; the goal is still active.

## Complete assembled flows and read-only privilege probe

Private evidence: `successor-live-driver-r1/full-flow-qualification-r1.json`,
`full-flow-tests-r1` through `full-flow-tests-r4`,
`privilege-probe-tests-r1.stderr`, `privilege-probe-tests-r2.stderr` and
`privilege-probe-r1`. The whole-flow harness uses the real controller, callbacks,
source/health/state generators and validators, admission phase/command policy,
parent fallback transport adapter, and actual recording processes/pipes/loopback
TCP. Common artifact/claim admission, USB/SSH, root networking, RAM transfer and
recording time are explicit fixtures. Production recording deadlines remain
1380 seconds; an explicit clock file advances them in the test.

Four scenarios pass on the final harness: target success through full capture
and post-capture health (**5.399 s**), plus early fallback, late fallback and
source abort (**17.454 s** together). Early V11 recovery needs no target
switch-root event or second recording. Late failure closes the target recording,
starts a separate full fallback recording, performs one ordinary reboot and
restores the previously healthy selection state. Pre-reboot refusal restores
both the installed shutdown variant and selection state through actual mutation
callbacks. Successful restoration keeps failed trials FAIL. Child processes are
reaped; no fixture can dispatch an actual phone command.

The first harness run failed at a wrong generator marker (**8.718 s**); the next
passed target success but misclassified inert restore text inside a health
script (**10.739 s**). Both failed receipts and harness versions are retained.
Reply dispatch now uses the admitted phase. Fail-fast execution and targeted
reruns avoid repeating already proven scenarios during fixture repair. Existing
production controller, admission, kernel and image bytes remain unchanged.

The fixed read-only privilege probe reuses the actual controller/launcher pidfd
monitor under both capture and SSH lifetime profiles, then checks a fixed
runuser child as deck and a clean source query. It performs no network, phone,
claim or capture operation. The parent retains process identities and raw output
and requires the original root process to exit. Seven initial preparation tests
pass in **0.629 s**. The actual sudo attempt fails before root execution in
**0.045 s**, with retained `sudo: a password is required`; this is not a kernel
failure or a qualified privilege handoff.

The installed graphical helper is `/usr/bin/ksshaskpass`. The prepared
`--authenticate` option invokes sudo askpass from the same parent as the detached
probes; password input stays between askpass and sudo. This follows sudo's
[parent-process timestamp matching](https://raw.githubusercontent.com/sudo-project/sudo/main/plugins/sudoers/timestamp.c).
Nine final tests pass in **0.691 s**, including authentication failure, ownership,
output retention, exact scope and actual unprivileged root-entry refusal.
Authentication success and real root handoff remain unverified. No dialog has
been opened; request fresh availability before launching it with run ID `r2`.
The phone is unchanged. No live qualification/admission record or boot claim was
created, and no build/full CI was repeated.

## Shared admission verifier and concrete factory

Private evidence: `successor-live-driver-r1/admission-qualification-r1.json`,
`admission-tests-r1.stderr`, `admission-tests-r2.stderr`,
`admission-driver-tests-r1.stderr`, `admission-input-probe-r1.json` and
`admission-actual-entry-r1.json`. The new `live-admission.py` is import-only and
does not register or consume a claim. Its fixed input lock covers 29 existing
sources/artifacts; dependency pin checks also cover their existing producers.
The signed boot image is streamed, while retained build/A01 receipts preserve
their prior qualification. No kernel, root, image or full CI build was repeated.

Admission binds exact record/context bytes, original controller PID/start/UID,
host boot, clean source, a bounded lifetime, current verifier/input identities,
full-flow qualification evidence and the exact consumed claim. The lifecycle
claim verifier is account-relative; root invokes its fixed bounded check as
deck. The new policy checks phase prerequisites, prior durable receipts, source
abort ordering and target/fallback capture closure. It regenerates mutation and
health scripts, derives health boot identity from retained discovery, and checks
per-command intent. Root transport independently checks the durable attempt and
forbids nonzero mutation indices. Root and parent capture checks share a policy.

**24 initial boundary tests PASS in 0.441 s; the final 24 PASS in 0.451 s** after
adding concrete assembly and strengthening root attempt/discovery binding.
These use real files and controller process identities, with explicit fixtures
for artifacts, qualification, claim, root UID and source observations. They
exercise stale identities, altered evidence, exact command refusal, phase skips,
ambiguous reboot refusal, capture closure and early fallback handling. The claim
subprocess command is inspected through a fixture; actual root execution is not
proven. **Three controller/source-abort/factory tests PASS in 4.835 s.** The real
controller and callbacks restore selection after partial staging, using the new
phase/command policy with simulated phone replies. The real factory connects
all authorizers and creates no execution directory or receiver.

The actual input check passes in **0.105 s**, then **0.005 s** with unchanged
metadata. A same-size replacement test invalidates the digest cache. Actual
entrypoint checks on clean source `b4412fb27e685def77f52767537e1f8e5b1d5fb8`
refuse the unregistered claim and absent `live-qualification.json` in **0.339 s**.
Existing source hashes remain unchanged. No live ADMITTED record, claim, sudo
operation, host network change, phone action, receiver or Ready request exists.

Next qualification must cover target success, source abort, early and late
fallback, plus the actual privilege boundaries. A read-only probe of the shared
controller/launcher monitor and runuser boundary can establish privileged
handoff without admitting a live capture or consuming the phone trial. Full
simulated flows must retain their simulated-device scope. Only after that
preparation should the one-use launcher and exact claim be enabled. Keep final
qualification inputs frozen through execution; progress documentation commits
must not be confused with evidence for a different admitted source revision.

## Guarded fallback transport and callback connection

Private evidence: `successor-live-driver-r1/transport-qualification-r1.json`,
`transport-tests-r1.stderr`, `transport-injection-tests-r1.stderr`,
`transport-regression-r1/result.json` and `transport-source-review-r1.json`.
The fallback root entrypoint reuses the controller/launcher identity monitor
with a bounded SSH lifetime. It requires the exact retained request and complete
pinned admission verifier before invoking the existing route core. The parent
adapter retains exclusive raw output files, waits for its child, checks original
root-process exit and ordered cleanup, then projects the existing SSH protocol.
Failed or uncertain mutations cannot retry, including after adapter recreation.
Action, direct health and nested fallback-locator callbacks share this hook.

**16 transport tests PASS in 1.068 s; three injection tests PASS in 3.907 s.**
Tests use actual child sessions, pidfds, process limits and disk output, with
explicit sudo/root/network/admission/phone fixtures. An actual invocation of the
root entrypoint as deck correctly refuses. The source-abort integration invokes
the hook with the exact phase intent; both fallback health paths use link-local.
The six affected regression suites pass **112 cases in 50.460 s** including
launch overhead: actions 27, health 26, fastboot 28, driver 12, capture bridge 16,
bridge/supervisor 3. This is component evidence, not a physical recovery trial.

Review found the outer base64-wrapped diagnostics can exceed the older four-MiB
receipt bound. Raw root stdout now has a separate twelve-MiB disk-file bound;
stderr is checked against 64 KiB and retained even on launcher failure. A real
stream exceeding four MiB passes the focused test. Five existing files change
behavior; nine others change only dependency hashes, verified by normalized
comparison. Prior source bytes are retained in `transport-integration-baseline-r1`.
No kernel/module/image build or full CI was repeated. Complete live admission,
full target/fallback integration and actual privileged handoff remain pending.
No sudo, host network change, phone action, receiver, claim or Ready request ran.

## Fallback route worker and threaded-process limit fix

Private evidence: `successor-live-driver-r1/fallback-route-qualification-r2.json`,
`fallback-route-tests-r1`, `prlimit-baseline-r1`, `prlimit-worker-tests-r1`,
`prlimit-integration-r1` and `prlimit-threaded-source-r1.json`.
The new import-only root route core accepts only the five fallback observation,
staging and restoration phases, with exact source/custody/intent and complete
outer admission. It rejects normal-route requests and Python on V11. An exact
existing link-local route is borrowed; otherwise the existing network manager
prepares and cleans an owned sixty-second route. The fixed `runuser` child runs
the existing SSH worker as deck, preserving source and credential checks.

The root core retains bounded raw child output even on failed commands, checks
cleanup independently, and never retries a mutation. Nonzero remote command
status remains available to the calling phase. Owned cleanup runs after an
admission change, source drift or output/protocol failure. **19 initial tests
PASS in 13.123 s**, including actual `prlimit` child input/output, a four-MiB
output bound and timeout/reaping. Root privilege, network, USB, admission and
the runuser/SSH boundary were explicit fixtures. The guarded privileged
entrypoint and callback transport connection are still required.

Review identified that the shared source-query executor used Python
`preexec_fn`, which is unsuitable inside the new threaded root monitor. It now
uses fixed `prlimit --core=0:0 --fsize=1048576:1048576` before its command. This
changes process-limit setup without changing the one-MiB bound or owned process
cleanup. All prior direct Python sources were retained; fourteen dependent files
changed only pinned hashes, verified by normalized comparison. Existing frozen
kernel/root sources and historical receipts were untouched.

**13 shared-worker tests PASS in 0.436 s.** The changed dependency prompted
focused rechecks: sixteen bridge cases (7.542 s), three bridge/supervisor cases
(2.872 s), twelve assembled-driver cases (9.586 s), and nineteen fallback-route
cases (13.210 s), all PASS including process launch overhead. An actual source
query with a concurrent thread passes in **0.115 s**; its child reports UID1000,
zero core limit and one-MiB file limit. This verifies the deck execution path;
actual root handoff remains unverified. No phone, sudo or host network operation,
physical capture, claim, kernel/module/root build or full CI ran this turn.

## Owned sudo capture bridge and controller-lifetime monitor

Private evidence: `successor-live-driver-r1/bridge-qualification-r1.json`,
`bridge-tests-r1.stdout`/`stderr`, and `bridge-supervisor-tests-r1.stdout`/`stderr`.
The import-only capture bridge launches only fixed `sudo -n` and the pinned
root capture entrypoint. It sends a bounded envelope over stdin containing the
exact request, host boot and original controller/launcher process identities.
It stores the actual process handle before fallible request I/O and retains
ownership even when the launcher exits early. Each role is one-use; another
role refuses while the prior launcher is live. Cancellation uses an owned pidfd,
and final bridge closure requires terminal children before releasing handles.

The root entrypoint checks actual UID, ancestry, process starts and both pidfds,
then requires the fixed execution admission bytes and their pinned
`live-admission.py` verifier. That verifier is not yet implemented: no live
admission is conferred by this entrypoint. The existing worker still performs
its source/USB checks and owns the coordinator lock and temporary network.
The monitor handles loss of either controller or launcher. Parent loss requests
worker cleanup; unresponsive cleanup is bounded by a forced failed exit. Output
writes have a five-second bound, allowing the worker's existing broken-stream
path to complete cleanup. A forced exit proves no cleanup or full capture.

**16 tests PASS in 7.354 s**, with actual child sessions, pipes, pidfds and
controller/launcher exit events. Cases include early launcher failure, unknown
process signaling refusal, one-use roles, missing admission, oversized request,
parent loss before work, worker cancellation, full output pipe and forced
cleanup timeout without a success record. The actual root entrypoint refuses
an unprivileged invocation. Root validation/UID transition and real network
cleanup are not qualified by these process fixtures.

**Three combined tests PASS in 2.625 s**, running the real bridge with existing
supervisor/callback/worker-parser fixtures: target capture, separate fallback
capture, and controller late-failure recovery through both processes. Sudo/root,
network and recording time remain explicit fixtures. The process bridge is
implemented; actual sudo handoff, the root admission verifier, fresh fallback
SSH route transport and full live-driver qualification remain outstanding.

Review: retaining ownership before input delivery prevents a failed launch
reply from becoming an untracked child. Watching both controller and launcher
covers the case where sudo exits while the controller remains alive. The focused
combined cases reuse qualified protocol fixtures without rerunning unchanged
builds or a phone cycle. No sudo call, phone action, live receiver, claim or
Ready request occurred this turn.

## Assembled twenty-two-phase driver and source-abort integration

Private evidence: `successor-live-driver-r1/driver-qualification-r1.json`,
`driver-entrypoint-r1.stdout`/`stderr`, and `driver-tests-r1.stdout`/`stderr`.
The new import-only driver connects all twenty-two exact phase implementations.
Its preflight returns `Route.prepare` directly; source abort retains the existing
source reader. Boot and ordinary fallback reboot share `Route.check`, and their
live-capture callbacks bind explicitly to target and fallback roles on the same
capture provider. Fallback location uses the fastboot locator, whose nested
health reader remains distinct from direct fallback observation.

The driver requires both before-phase and entered-intent admission callbacks
and a complete capture-bridge interface, with no default allow behavior. It
checks shared output paths, including nested modules, before source mutation.
Normal phases recheck source/context/prior receipts; owned capture closure stays
available through the controller's existing cleanup path after admission changes.
There is no CLI, claim registration, automatic execution or privileged bridge yet.

**12 tests PASS in 8.942 s.** The actual imported driver and controller exercise
one-query preflight, arm refusal followed by source reconciliation, and install
refusal after staged state followed by actual state-restoration callback parsing.
The failed trial stays failed after selection restoration. These scenarios use
real generated scripts, parsers and durable receipts, with explicit simulated
phone transport replies. Other cases check all phase bindings, route/capture role
connections, refusing admission, missing bridge, divergent nested evidence paths,
cleanup after admission refusal, execution-directory reuse and unknown callbacks.
The isolated entrypoint constructs all twenty-two bindings with refusing
admission and bridge objects; it issues no transport.

Review: the integration test verifies one combined preflight transport, avoiding
a duplicate source query; no physical speedup was measured this turn. Checking
nested writer paths before any mutation addresses the earlier receipt-namespace
failure class. No phone actions, root capture, target/fallback boot integration,
full CI or repeated kernel/module/root builds occurred. The privileged bridge
and complete execution admission remain outstanding.

## Fresh installed-route verification and actual phone inventory

Private evidence: `successor-live-driver-r1/route-qualification-r1.json`,
`route-tests-r1`, `route-target-tests-r1`/`route-target-tests-r2`,
`route-entrypoint-failure-r1` and `live-route-readonly-r1`.
The import-only route verifier combines fresh authenticated V9 source observation,
streamed hashes of eleven installed files and the read-only boot partition,
with retained exact installed-selector execution evidence. The latter shows V11
selection for new pending and healthy records; it does not prove physical boot.

The actual phone check **PASS in 2.912 s**, on unchanged V9 boot
`7c945aa5-80d0-4af2-aa76-113d68e23ac5`. All eleven files and `/dev/sde35` match;
boot-partition digest remains
`dcc487f17d6b4926ea633cbb242c62b598019e332640a81c1100c2d91087f723`.
Source preflight passes before and after the inventory, including unchanged
selection/custody and storage/power guards. Hashing uses bounded streaming.
Host source was clean `064d7d1693c024f8815736c1bf138b0d7d01be2f`.
This isolated component probe had read-only preflight authorization; it issued
no phone mutation, reboot, claim, receiver or complete controller admission.
Its receipt cannot substitute for a later controller run's fresh preflight.

**12 host tests PASS in 2.348 s**, covering changed boot/file/partition evidence,
nonboolean assertions, historical-only evidence, failed transport retention,
repeat entry, admission refusal and receipt changes. **Six namespace tests PASS
in 0.003 s** test-body time, exercising actual UID-0 regular-file metadata,
streaming hashes, bounds and symlink/hardlink refusal. Network and device access
were isolated; host filesystem remained read-only except private disk scratch.
The actual phone probe additionally exercised block geometry and digest checks.

The entrypoint initially failed on expected empty stderr because the JSON
receipt reader requires nonempty content. A separate bounded raw reader handles
empty streams while preserving descriptor/metadata checks; JSON semantics stay
unchanged. The first namespace runner failed before tests because its bind target
`/fixtures` was absent under read-only root. Binding the existing private scratch
path to itself fixed setup; both failed records are retained.

Review: `Route.prepare` returns the same verified source observation with its
route-receipt hash, so the assembled driver's preflight can use it without a
second source transport. `Route.check` requires that exact fresh preflight and
context; a historical PASS flag alone cannot qualify the route. All twenty-two
phase components exist; privileged bridge, combined-driver integration and
admission remain next. No kernel/module/root build or full CI was repeated.

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

### 2026-09-11: host password dialog failure and prepared correction (r35)

Fresh Ready started read-only privilege probe r2 immediately. It failed after
2.328 seconds with no password supplied, zero root rows and no phone/network/
claim action. The user saw no password window. Journal evidence identifies
ksshaskpass SIGXFSZ and an inherited 8192-byte RLIMIT_FSIZE; core dumping was off.
The exact failing syscall was not traced. Root boundaries remain unqualified.

Authentication now allows 64-MiB GUI files while independently limiting stderr
via a pipe to 8 KiB; overflow refuses authentication and reaps the owned process.
Ten probe cases PASS (0.726 s), including a real 1-MiB memfd and diagnostic flood;
fifteen launcher cases PASS (0.902 s). A real Wayland window remained alive with
three mapped graphics buffers and was stopped/reaped after 2.010 s. An initial
FD-only buffer check failed; retained mappings explain its missing observation.
The noninteractive popup check alone was insufficient to prove buffer creation.
Prior source and evidence are retained in private `auth-gui-fix-r1`.

Only the authentication implementation, focused test and launcher dependency pin
changed. Kernel/images and root-boundary code were not rebuilt. The prepared
next attempt is r3 and requires fresh host availability. No phone Ready is pending.

### 2026-09-11: host input failure and direct-touch preparation (r36)

Fresh Ready started r3 immediately. The user saw the window and opened Steam's
keyboard, but the field stayed empty. Operator cancellation ended the run at
100.254 s, before any root probe, phone, network or claim action. The initial
SIGTERM to sudo launched another askpass; verified group cancellation stopped
and reaped it. No password was received by the controller or stored.

Automatic dummy keyboard tests failed for ksshaskpass and kdialog under X11.
Window focus and an empty focused field were observed; the exact routing cause
is unresolved. A synthetic pointer test also failed. Neither is a human input
pass. The replacement private askpass provides a direct touch keyboard; its
widget callback test passes Shift, symbols, backspace, empty refusal, submit,
cancel and printable ASCII coverage. The 1040x560 layout was visually reviewed.
Ten final probe tests and fifteen final launcher tests pass; detailed timings,
failed input attempts and source snapshots are retained in `auth-input-fix-r1`.

The helper is pinned, owned by deck, mode 0700, core-disabled and requires a
pipe for password output. It never writes credentials to files or clipboard.
Authentication keeps the separate 8-KiB stderr cap and 64-MiB GUI file bound;
it allows five minutes for direct touch entry and kills its owned group on
forced abort. Prepared r4 requires fresh host availability, immediately opening
the touch keyboard; real input/authentication and root handoff remain unverified.
No phone trial, claim registration or Denial build was performed.

### 2026-09-11: successful touch authentication, sudo session fix (r37)

Fresh Ready immediately started r4. Authentication returned 0, reaped, with
zero stderr bytes and no password retained. The following capture-role sudo
returned 1 with “a password is required”; both processes were reaped. Overall
FAIL in 11.161 s, zero root rows/phone/network/claim actions. The host boot ID
is now `e3393ab5-0cf9-43fd-8bcb-020cf78b1f1b`; earlier runtime evidence is historical.

Sudo 1.9.17p1 lists normal wheel authorization; noninteractive validation and
true both refuse without a matching credential. Its timestamp acceptance code
rejects session-ID mismatches. Authentication and checks formerly each called
setsid. Four launching components now preserve the controller SID with separate
PGIDs: probe/auth, credential refresh, capture and fallback transport. Source
snapshots, input lock and dependent pin changes are in `sudo-session-fix-r1`.
Root entrypoints and phone artifacts are unchanged.

Eighty-eight cases PASS across probe, launcher, bridge, fallback transport,
bridge/supervisor, admission and four full flows. Real child fixtures assert
same SID and distinct owned PGID; sudo/root/phone behavior remains simulated.
The initial full-flow run refused an existing evidence directory. Old evidence
was preserved; an upfront directory check and fresh `sudo-session-full-flow-r1`
completed all four cases in 25.566 s. No unchanged build or full CI was repeated.

The unchanged touch keyboard is prepared for r5 on fresh host availability.
Actual post-fix sudo reuse/root handoff still requires that next run. No phone
Ready or physical trial is pending; subsequent device setup needs fresh health
and identity observations after the host restart.

### 2026-09-11: actual privilege success, fresh phone checks, exact claim (r38)

Fresh Ready immediately launched r5. PASS in 10.795 s after one touch-password
entry: capture and SSH guardian profiles each ran with all root UIDs zero,
validated actual deck children, original controller/launcher ancestry and clean
source `7bbd8f4a`, then reaped and verified exit. No phone/network/claim action
ran in the probe. The password stayed between askpass and sudo.

Fresh V9 health PASS in 1.362 s at 77,231.59 s uptime on the same phone boot.
Current-boot healthy/readiness markers and storage/power protections pass.
Fresh staged-file readback PASS in 0.386 s: exact helper/custody/inactive shutdown,
unchanged active shutdown and old healthy boot selection; no state exchange.

Registered the exact new kernel profile at `02b9e9fe`. Record hash
`ad1d8dbfab6d5c2dd10cf3b61191b0d9354557a92a5ce9925601fe58c077e969` binds
image, manifest, composition, A01 proof, device, slot, fallback and one attempt.
No claim consumption, transfer, boot or flash occurred. Registry and primitive
tests prove registration alone cannot dispatch without durable consumption.
Dependent private pins/input lock were refreshed with prior source retained.

Affected tests pass, including all four full flows in 26.317 s. Earlier dirty-
source refusals were resolved by freezing the code commit. Initial child exits
were traced after retaining early stdout/stderr: simulated deadline subtraction
rounded 1380 seconds upward. Integer clock seeds fixed the fixture; no production
recording guard was relaxed. Detailed outcomes and old sources are retained in
`successor-claim-registration-r1`; final flow receipts are in
`registered-claim-full-flow-r3`. Earlier failed attempts remain intact.

Final live admission/installed-route preparation remains before any hardware
availability request. No new prompt is pending. The completed host Ready must
not be reused as presence for a future phone test. Root handoff source facts and
later registry source facts remain distinct; the native Denial goal is incomplete.

### 2026-09-11: final temporary-kernel trial preparation (r39)

Fresh actual installed-route inventory PASS in 2.890 s on the same V9 boot:
eleven installed files and boot_b hash match, original shutdown/selection remain
unchanged, and physical/storage checks pass before and after the streamed read.
This remains read-only evidence, not a physical fallback boot.

Found and fixed a preparation omission: profile registration did not stage the
unconsumed source record. The exact record is now staged with exclusive creation,
file/directory fsync and readback; neither entered guard exists and no claim was
consumed. Launcher preparation now checks it before authentication, and repeats
the check before consumption. All 21 focused launcher cases PASS in 0.824 s.
Old source files and tool output are retained under `final-preparation-r1`.

Final review replays four simulated controller outcomes and raw capture hashes,
actual r5 root/deck process evidence, unchanged source pins, current input lock,
and fresh read-only phone route evidence. PASS in 0.246 s; 26 evidence files bound.
Target/fallback/recording durations in the flows remain explicit fixtures; the
r5 privilege result retains its original source observation at `7bbd8f4a`.
The final qualification binds the subsequently frozen notes revision separately.
The prepared command requires fresh Ready, opens the working local touch keyboard
for authentication, and then controls the single RAM boot/full capture itself.
No current physical trial was started; no builds or full CI were repeated.

### 2026-09-11: combined native-device DT proposal (r40)

While awaiting fresh Ready, composed the previously qualified display DT with
the pinned front-touch and GPU overlays, entirely outside the frozen admission
inputs. Two orders, each built twice, passed in 0.336 s. Exact validators retained
all unrelated properties, boot CPU/reservations, SPI4-disabled and shared L8
always-on policy. The complete parsed trees match between orders; serialized
bytes differ. Canonical order is GPU, disabled touch, touch enable. Its DTB is
110,415 bytes, SHA-256
`6c79982f3c2f8477cdb581640f9c038a4f13fa9071dd55beda92e100752c81b5`.

Five actual encoded mutations (ZAP, SPI conflict, touch rail, touch disabled and
boot CPU) were rejected in 0.106 s. Initial dictionary comparisons were replaced
with real verifier calls; original output/source remain retained. Artifacts and
receipts are private `combined-native-dt-r1`. This is unsigned composition only,
not kernel ABI/probe, scanout, touch or GPU rendering evidence. Physical bring-up
still starts with the prepared headless kernel trial, followed by separately
observed OLED, touch and GPU stages. No phone action, signing, claim consumption
or kernel build occurred. Notes were staged as a patch while the trial source
remained frozen; apply this documentation patch only after the trial completes
or is explicitly retired.

### 2026-09-11: actual successor kernel capture, two host defects (r42–r43)

Fresh Ready immediately started `final-preparation-r1/run-prepared-trial.py
--start`. Local touch authentication succeeded, the pending claim was consumed
once, source-state/exitrd preparation passed, and the exact 134,217,728-byte image
transferred once. Source was `a9161e98`; phone serial remained M5AIKN00F0353YH,
slot B, product lahaina. No flash or second RAM boot occurred.

Real successor boot: `de90d177-3532-49e0-9bfd-8f8c65889a8d`, release
`7.1.4-g05941d04803f`. The initial controller health callback saw fastboot and
failed immediately. Passive capture subsequently observed target USB and
switch-root PASS. Independent strict-key SSH health PASSed in 1.855 s at uptime
108.19 s, with healthy commit at 64.957282 s. The original controller receipt was
not altered or replaced by the independent health check.

Full capture PASS: original deadline 6311.254956229 host monotonic; recording
ended at 6311.392766294. Route, firewall, profile and address cleanup passed in
order; root worker reaped and no owned process remained. Capture stream SHA-256
`8c883d2e7ef4be55db792beccb60bae9d4cc26f7f97b523fb0023d750a9afa14`.
All 32 credential refreshes succeeded and the refresher stopped without failure.
The later fallback location failed before network acquisition or SSH: actual
`NETWORK.command` returned two values, while the caller unpacked three. Its raw
result retains `cleanup_complete=false`, `network_owned=false`, no events and
no deck worker. Do not turn that failed route result into a cleanup PASS.
Original controller, capture and fallback root/launcher PIDs were absent after
termination; overall launcher had no cleanup exceptions, but returned FAIL.

After terminal cleanup, independent strict-key SSH health PASSed in 1.523 s at
uptime 1383.39 s, on the same boot and exact new healthy record. Boot-bound
readiness and physical/storage/power guards passed. Receipts are
`successor-live-driver-r1/actual-successor-health-r1` and `-r2`. The phone remains
on the successor kernel. Old boot-selection eligibility was not restored; signed
fallback remains unmodified but physical fallback/restoration remains unproven.

Both host defects reproduce with original source and pass isolated fixes:
32 health-transition cases in 12.649 s and 25 fallback-contract/process cases in
13.010 s (candidate command wall times 13.691/13.313 s). Read-only route lookup
exercises the real two-value adapter. Candidate sources and patches are private
`health-usb-transition-r1` and `fallback-command-contract-r1`. No executed source
was patched during the capture, no kernel rebuild/full CI repeated, and no
additional phone cycle or claim was created. The combined-DT notes patch was
applied only after execution terminated. Overall automated trial remains FAIL;
physical headless kernel/capture observations passed at their stated scope.

### 2026-09-11: OLED 05941 signed wrapper twins and static autoload (r47)

Private `oled-boot-package-prep-r1` adapts only OLED input/qualification checks
from the retained successor packager. Signed/AVB/cleanup implementations and
sealed verifier remain unchanged. Twenty-two focused checks pass in 0.389 s;
actual input inspection passes in 0.615 s under the required 512-MiB/no-swap cap.
The first inspection used stale larger limits and was refused before key access.

`oled-boot-package-r1` was killed by its cgroup limit during second-side repack.
Kernel evidence shows 503,865,344 dirty file-cache bytes at the 512-MiB cap.
Both completed signature receipts, partial wrapper and unit/kernel logs remain
retained. It has no final qualification; its output must never be reused.

With unchanged source and input hash `96f0fa20…`, a fresh
`oled-boot-package-r2` passed all 18 stages with `MemoryHigh=256M`, unchanged
512-MiB maximum and no swap. Systemd reports about 75 seconds and 361.5 MiB peak;
all stage return codes and cleanup checks pass. Both signatures and all five
bundle-member twins match. Both raw images are 129,966,080 bytes; measured AVB
capacity selects 128 MiB. Boot SHA `08922813…`, manifest `95d0748d…`, recovery
`b9099828…`. Both AVB checks and sealed signature/plan verification pass.
Bundle `oled-05941-a2be906cd7b36636`, trial `b52ead05…` remain unregistered with
no boot admission. The AVB footer uses algorithm NONE; bundle trust comes from
the verified embedded signature, not an AVB signing claim.

`oled-root-autoload-r1` passes in 0.794 s. Inherits the pinned retained root
inventory after exact metadata checks, streams the new 724-member archive and
catalog, checks exact current init/loader source, verifies the two module hashes
and ABI, and repeats four host kmod dry-run refusals. No configured automatic
display loader was found. Host search-path fixtures do not execute Arch coldplug;
retained root inventory is not a newly recomputed full-root content hash. New DT
built-in MDSS probing, effective boot controls and physical panel behavior remain
unqualified. No phone command, reboot, flash, partition write or new claim ran.

After-run improvement: earlier memory throttling solved the observed packaging
failure while keeping its hard limits. Preserve both attempts and successful
artifacts; proceed to new profile/controller qualification without rebuilding
kernel/modules or repeating the completed packaging work. The user's readiness
was released when preparation failed; request fresh availability only after the
entire physical session is prepared.

### 2026-09-11: OLED state, source and recovery components (r48)

`oled-state-exchange-r1` creates exact new records for signed OLED manifest
`95d0748d…`, bundle `oled-05941-a2be906cd7b36636`, trial `b52ead05…`.
Pending SHA `e77c2e20…`, healthy SHA `aea03ea5…`; original V9 SHA `ed3a62d1…`
is unchanged. The Rust algorithm differs only in profile identifiers and fresh
`.oled-05941-transition` names/tokens. Fourteen native Rust tests pass in 0.26 s;
three new tests preserve all six consumed kernel transaction files and reject
prior-kernel pending/healthy states. ARM64 ABI positive/negative compile checks
pass. Sequential static PIE twins build in 1.262/1.004 s, SHA `472dfd36…`,
1,253,144 bytes. Owned build containers terminate and are removed without error.

Six isolated QEMU scenarios pass in 0.563 s using the actual new ARM64 helper
and retained v1/v2 target trial-state helpers. Staging, healthy commit, pending
restoration, wrong-state/missing-gate refusal and lost-reply no-retry paths pass.
The old record inode is restored, and every command preserves the six prior
kernel transaction files. ELF has no interpreter, has RELRO and no executable
stack. Synthetic disk fixtures and QEMU do not qualify physical state exchange.

`oled-state-guards-r1` inherits the exact physical shell guard and recognizes
current 05941 source plus unchanged V11 fallback. Adds exact inventory/metadata/
hashes for retained kernel transaction custody. Thirty-one real ARM64 BusyBox/
loader/helper cases pass in 87.309 s, with six generator-input refusals. Power,
mount/device identity and boot state are explicitly substituted fixtures.

`oled-source-actions-r1` preserves the file/lock/publication algorithm, adapting
only the new namespace and input pins. Sixteen action tests pass in 0.644 s;
22 read-only reconciliation tests pass in 0.391 s, in an unprivileged uid0 user
namespace. Telemetry and reboot are mocked. The first direct deck invocation
failed with 13 ownership errors in 0.178 s; those logs are retained and no guard
was weakened. All five action and three observation scripts generate and compile.
Focused source review is retained in `oled-state-exchange-r1/component-review.json`.

Two actual SSH queries were read-only. The first returned health then failed
because its added helper probe used the root-relative `/usr/libexec` path outside
the exitrd. The corrected query passed in 2.094 s at uptime 5849.97 s, same boot
`de90d177-3532-49e0-9bfd-8f8c65889a8d`. Confirms restored OLD selection, exact
retained transaction, absent new transaction/intents, original shutdown and the
helper at `/run/initramfs/usr/libexec/rog5-reboot-bootloader`. No RAM staging,
phone state exchange, reboot, flash, new claim or profile registration occurred.

After-run review: retain the fast matching-kernel build and exchange algorithm;
change only signed identity/namespace and test cross-trial custody explicitly.
Carry correct user-namespace and exitrd context into the next integration run.
The next dependency is controller assembly and admission around these components,
not another kernel/package build. OLED/touch/GPU and Denial remain unqualified.

### 2026-09-11: assembled OLED controller and closed boot adapter (r49)

`oled-controller-worktree-r1` at `30b72c12` adds exact OLED composition profile
`0fc132e8…` alongside the unchanged default headless profile. Nine tests pass in
0.077 s: old default preserved, exact new selection, mixed-profile refusal,
preservation/module-map checks and refusal before claim lookup when OLED
composition admission is missing. `verified-oled-hardware-boot.py` has no A01 or
composition-source binding yet and cannot authorize execution.

`oled-live-driver-r1` assembles all 22 phases with current kernel 05941 as source,
OLED 05941 as target, and V11 fallback. Controller method/class ASTs are unchanged;
fixed identities, namespaces and source pins differ. New host-only custody owner
`ba670e08f11d4c3f8e2f95573689619f` binds the retained actual r48 source snapshot,
old record and boot. This does not stage phone RAM or create a claim.

The installed selector passes three real ARM64 scenarios in 0.332 s. An initial
0.014-second attempt failed because copied ELF tools lacked execute bits; modes
were corrected, a preflight permission check added, and fresh r3 evidence retained.
The new inventory reader explicitly inherits pinned installed V9/V11 metadata,
while the live route query revalidates those bytes on current source. New source
custody is separate; the first full-flow preflight had incorrectly expected an
old request.json in the new health directory and failed before mutation.

Target capture/post-health passes in `full-flow-tests-r2`. Its next case stopped
because new fallback observation fixtures did not yet exist. Eleven actual ARM64
fallback reader/helper scenarios then passed in 52.193 s, with real tmpfs and
explicit hardware/installed-file fixtures. Only early fallback, late fallback
with separate capture, and pre-reboot source restoration resumed in r3; all three
pass in 17.928 s. Recovery scenarios retain overall FAIL as intended, with old
selection restored. USB, SSH replies, privilege, artifact/claim admission, RAM
transfer and recording time are simulated. Host capture subprocesses are real
and cleanup/reap checks pass. No physical OLED or new root handoff is proven.

Twenty health boundary tests pass in 0.035 s, and the new source predicate replays
the actual r48 health snapshot successfully without another phone query.
Seventeen transfer-boundary/real-child tests pass in 3.675 s. Final import/pin
checks pass; the actual boot adapter refuses `OLED composition admission is not
prepared`. No live execution directory, input lock, qualification, registration,
claim, phone query/write, reboot or flash occurred. Integration receipt is
`oled-live-driver-r1/integration-result-r1.json`.

After-run improvement: keep source runtime, installed inventory and host custody
separate; preserve tool modes and generate current fixtures before full flows.
The dependency-ordered pin map supports corrections without rebuilding the
kernel or package. Reuse completed scenarios when production inputs match.
Next dependency is exact composition/root admission and privileged handoff,
followed by fully prepared physical display testing; Denial remains deferred.

## OLED composition and input binding (r50, 2026-09-11)

`oled-a01-r2` passes all seven offline composition checks in 81.851 s. A01 result
SHA `abcf577d417a2363921f156181e85161efda1fb97ce90351aef6c4ab6ed286f0`,
verifier revision `30b72c121a93c8470ed2907de7e60ac376590698`. Both retained root
images were hashed before and after, remain unchanged, and were read-only in
QEMU. Exact-kernel runtime passed; owned container removal, client reap and
attach-group closure are confirmed with no cleanup errors or VM OOM. Physical
OLED probe/scanout, GPU and touch remain NOT RUN.

The first run is terminal FAIL (23.970 s): ignored Android boot tools were absent
from the new checkout. Five tools/template inputs were streamed/hashed against
the original and frozen copies, then copied with modes. No bytecode caches were
copied. The new runner checks these inputs before the expensive root hashes.
Successful package/kernel/module outputs were reused unchanged.

Q commit `462cef05402e38508bb384494ea6662b40b9f0b4` binds the exact A01 result
and its actual verifier revision in the OLED boot adapter. Only that adapter and
its tests changed after A01. Twelve cases pass in 0.136 s, including missing
composition, unregistered claim and unconsumed claim refusal. The old headless
adapter/default identity is unchanged. No registration or consumption occurred.

New `oled-live-driver-r1/admission-inputs-r1.json` has 31 exact files, SHA
`d905fc124702c195fb8f9dc706d6771fd9360998b28024ed0ff1f02a0c239b6b`;
validation takes 0.098 s. Dependency-ordered pin refresh now ends at r5. The
admission, privilege-fixture and launcher suites pass 24/10/21 cases in
0.447/0.528/0.772 s. Launcher pending-claim tests explicitly simulate registration
for the new profile; they do not alter the real registry. Production qualification
and execution remain absent. Real privileged handoff is still pending.

The touch askpass copy changed from mode 0644 to 0700; code SHA is unchanged and
its metadata/code preflight passes. Actual `privilege-probe-r1` then refused in
0.043 s because sudo requires a password. No authentication window opened, no
root probe ran, its child was reaped, and no phone/network action occurred. Keep
this attempt; prepare the remaining handoff checks before fresh availability.
Final evidence: `oled-live-driver-r1/composition-binding-result-r1.json`.

After-run review: root hashing dominates A01, so missing tool/mode prerequisites
must be caught first. Do not repeat this successful expensive proof for an
adapter binding whose exact source delta is recorded. Next work remains kernel
and display bring-up through prepared root handoff, one-use lifecycle and endpoint
blanking/discovery. Denial/Flutter builds remain deferred. Phone health was not
queried again in r50; r48 is still the latest physical observation.

## Prepared privileged handoff (r51, 2026-09-11)

Previous turn r50 is progress: exact OLED composition proof and 31-file input
binding replaced missing admission prerequisites. No build, A01 rerun, phone
query or repeated sudo-n attempt is needed for this step.

`oled-live-driver-r1/handoff-preparation-r1` now passes 35 focused checks:
16 guardian/bridge (6.926 s), three bridge/supervisor (1.959 s), 16 fallback
transport (0.900 s). Wall times were 7.087/2.170/1.117 s. Real subprocesses,
binary pipes, pidfds, parent-loss cleanup and command receipts are exercised;
sudo/root authority and phone actions are explicit fixtures. These tests do not
satisfy actual privileged handoff by themselves.

`prepared.json` SHA `fd2cabc5f0d3bcad09b4c0b843f3f21c68981d5a4accd03f6e8a76ff2798ae5c`
binds the clean Q revision/worktree digest, current host boot, exact source/mode
pins, input lock and unique `privilege-probe-r2` output. Tk import, graphical
session variables and existing askpass preflight pass. No window opened; no
root, phone, network or claim action occurred. The command is the existing
`run-privilege-probe.py --run-id r2 --authenticate`; it checks capture then SSH
root guardian/runuser paths automatically after local touch authentication.
It is ready for fresh user availability. No physical phone presence is required.

After-run review: the longest check (6.926 s) exercises deliberate process-loss
and backpressure deadlines, not a newly observed slowdown. Keep those bounds.
Use the existing corrected launcher and record its exact prepared invocation;
avoid another wrapper, repeated authentication failures or expensive build/VM
work. On fresh Ready only brief current checks and launch remain. Display
load/discovery/blanking preparation follows; no Denial/Flutter build was started.

## OLED endpoint and blank component (r52, 2026-09-11)

Previous r51 is progress: 35 handoff preparation cases completed and the exact
local authentication command is ready. The automatic continuation is not fresh
Ready; no auth window, root probe, phone query or network action was started.
The prepared receipt remains SHA `fd2cabc5…`, its output is absent and Q is clean.

New independent `oled-display-component-r1/endpoint.py` leaves that prepared
cohort untouched. It reads exact boot/kernel/descriptor identity and validates
one raw backlight, its range, DSI parent, driver and exact panel DT ancestry.
The import-only zero action requires the enclosing admission callback before
opening and again around the write, verifies the opened inode against its path,
submits only zero and requires zero readback. Failures propagate without a
success result. Cleanup may reassert zero; it cannot illuminate, load/unload a
module, open DRM/fb0 or trigger a reboot.

The early blank is independent of framebuffer presence. Later sysfs-only fb0
validation requires zero, the same display subtree, msmdrmfb, 1080x2448 nominal
60 Hz and 32 bpp. This does not establish framebuffer ioctl/pixel layout or
visible output. The compiled current module's panel source is byte-identical
to the audited source SHA `45e8bcb9c608645e76ae888e33f3c4d2e9096338eae95d59c67b56f2f428b892`.
It defaults to brightness 1023 and has no hardware brightness read callback;
zero sysfs readback is therefore kept distinct from optical-darkness evidence.
The pinned DT's panel compatible was independently read with fdtget.

Initial 18 tests passed. Review then added same-display framebuffer ancestry
and short-write refusal; final 20 tests pass in 0.131 s under
`unshare --user --map-root-user`. Tests use actual files/symlinks/FD replacement
and explicit sysfs-store emulation. Wrong boot/descriptor/driver/DT/parent,
multiple backlights, malformed/range values, symlink/replaced brightness,
authorization loss, driver errors, short writes and missing readback refuse.
No real sysfs writes or host-root handoff occurred. Component result SHA
`d3fce3e52e5681ffc94d3aed549b39434024cea14fe9f7a84e0176f305ba68cf`.

After-run improvement: order exact-endpoint blanking before framebuffer checks
and distinguish command success from physical darkness. Do not weaken endpoint
checks or claim hardware behavior from fixture files. Next work is enclosing
module-load/health/monitor/deadline and fixed-frame integration; actual endpoint
discovery still belongs before human display readiness. Authentication remains
prepared for the user's fresh Ready. No kernel/package rebuild or Denial build.

## Rust framebuffer layout and fixed-frame helper (r53, 2026-09-11)

Previous r52 is progress: exact endpoint/zero-brightness component and 20 offline
cases passed. Independent work continued while fresh Deck authentication Ready
remains pending; Q, L and the prepared authentication receipt are unchanged.

`oled-frame-r1` now contains a dependency-free Rust layout decoder and row-wise
fixed-frame generator. It accepts only the bounded 248-byte LP64 little-endian
record framing, exact msmdrmfb packed truecolor 1080x2448 32-bit geometry, bounded
stride/memory, supported RGB/BGR byte orders and alpha semantics, no panning,
interlace or rotation. It emits metadata or one fixed frame, with at most 16 KiB
row buffering. It opens no framebuffer/DRM/backlight device and performs no ioctl.
The caller must still bind actual ioctl data to its admitted same-boot device.

Initial tests failed as expected before implementation; ten passed after it.
Current kernel drm_fb_helper.c inspection added depth24 XRGB alpha offset zero
coverage. Clippy found two idiom warnings, corrected without suppression. More
importantly, ARM64 C ABI assertions rejected the initial vmode/rotate offsets;
those are 132/136, not 136/140. The corrected target C program emits actual
struct bytes for end-to-end parser input, avoiding a shared test-offset mistake.
Final Rustfmt, Clippy (-D warnings), 13 release tests in 0.02 s and ARM64 ABI
checks pass. Earlier terminal failures are retained in their own directories.

The final validation/build took 2.770 s; a separate cross-build took 1.056 s.
Both static-PIE ARM64 binaries match SHA
`ed3e8081da90506bfc085b1fc74aeb59f56644949022dc2133fb9f7f5d4564bf`,
1,252,408 bytes. All owned build containers were removed, no OOM/cleanup error,
and sources stayed unchanged during their runs. The immutable Rust 1.98.0 image
is retained; memory512MiB/no swap/network-none/one CPU limits were used.

Twelve actual native/ARM64 process scenarios complete in 0.340 s. Native render
0.031 s and QEMU ARM64 render 0.125 s produce identical 10,653,696-byte frames
(4352-byte fixture stride), SHA
`859231dae5b6f5c8c80361a0cfcf748cd605f662ee3e9722ab8fda0f377276a8`.
Truncation, extra bytes, bad magic, interlace, rotation, absent CLI option and
/dev/full output failure refuse. A PNG decoded row-by-row using only standard
Python libraries was visually reviewed: up-arrow/TOP, RGB bar, corner markers
and border are readable and correctly oriented. This is generated output,
not a phone image or physical scanout result.

Recurring-tool improvement: the minimal compiler image lacked fmt/Clippy, as
older receipts already recorded. Exact supplementary 1.98.0 tools are now in
`rust-tools-r1`, verified against retained manifest SHA `3f7d139b…`; 2,484,924-byte
Rustfmt and 5,379,668-byte Clippy archives were streamed and hash checked. The
read-only overlay supplies only those tools; the compiler image is unchanged.
No systemwide install or Denial/kernel/module/package rebuild was performed.

Component result SHA `7638ae1d4a168c9c35abe521d9721ed67b3d5d661c553aaead4598b6e1ac54cd`.
Next: guarded actual ioctl collection, same-device frame write and bounded
brightness/blank integration, alongside the already prepared authentication
check. No phone/query/network/claim action or password window occurred in r53.

## Guarded framebuffer capture component (r54, 2026-09-11)

Previous r53 is progress: reproducible ARM64 frame helper, actual C/Rust ABI
integration and pinned Rust validation tools completed. No fresh user Ready
arrived in this automatic continuation; prepared authentication stays unchanged.

`oled-display-component-r1/framebuffer.py` now reads the bounded raw-layout
protocol from an admitted, blanked OLED framebuffer. Exact endpoint/boot checks
precede root-owned character29:0 /dev/fb0 metadata and O_PATH inode validation.
Operational open reuses that checked inode through an owned procfd, read-only.
The only ioctl requests are GET_FSCREENINFO (80 bytes) and GET_VSCREENINFO
(160 bytes); two samples must agree. Admission, zero-brightness endpoint state
and node identity are rechecked around collection. Errors propagate and both
descriptors close. No framebuffer write, mmap, mode-set or brightness change.

Current kernel fb_chrdev.c and drm_fbdev_dma.c inspection confirms that open
calls framebuffer driver operations; it is not an ungated routine health read.
The import-only collector still needs the enclosing component deadline, retained
capture, full-health/module-load gate and future frame/brightness integration.

Initial 11 tests passed in 0.126 s. Review added buffer-resize and mid-ioctl node
replacement refusals plus descriptor-leak checks for every test; final 13 pass
in 0.150 s. Real O_PATH/open/close/symlink/inode behavior runs in a user namespace.
Character metadata and ioctl data are explicit fixtures; an unmocked ENOTTY
negative path is included. The collected C-produced record passes the actual
ARM64 Rust decoder in QEMU. All permissions/blank/metadata/changed-sample/error
cases refuse without a success claim. The unchanged Rust binary SHA is
`ed3e8081…`; raw fixture SHA `67417ba4…` is retained independently.

Receipt `oled-display-component-r1/framebuffer-result-r1.json` SHA
`3f75e59a7bcf9d9d5a96f75687b54ca603a8b8d046c3eb2a739f196c896deb6c`.
Physical fb0 open/GET ioctl, scanout and framebuffer writes remain NOT RUN.
No phone/network/authentication/claim action occurred; Q and prepared L inputs
are untouched. After-run improvement: retain the verified inode across open,
check all descriptor exits and distinguish captured data from validated layout
or physical evidence. Continue same-boot frame-write/brightness integration;
no kernel/package/Denial build or repeated authentication attempt was needed.

## Prepared host authentication attempt (r55, 2026-09-11)

Fresh Ready triggered the pinned command immediately after brief receipt, source,
host-boot and file/mode checks. `oled-live-driver-r1/privilege-probe-r2` retained
its exclusive output. Authentication timed out after **300.014 s**; overall FAIL,
no privileged result rows, stderr zero bytes. At 04:56:10.985505 UTC, xwininfo
reported the 1040x560 password window at +120+106. This establishes window
creation, not user visibility, successful interaction or a password error.
The user did not answer the window-status question during the attempt.

Authentication reports returncode -9, timed_out true, reaped true, no log
overflow and password_retained false. The owned authentication group was killed
by the existing timeout path; terminal checks found no remaining dialog/probe
PID or matching window. Capture/SSH root profiles did not execute. There was no
phone query/write, network action, registration, claim consumption or boot.

The user was released from waiting. A fresh r3 output is prepared by
`handoff-preparation-r2/prepared.json` (SHA `99e6ff62…`); its previous-attempt
observation retains the result hashes. Six code/input file pins and modes,
dependency map, clean Q revision, host boot, Tk import, graphical environment
and absent new output passed. The previous 35 preparation tests are reused;
no code changed, expensive test reran, second window opened or timer restarted.
Only a new Ready starts the recorded r3 command. No response is assumed.

After-run review: the proven delay is waiting for authentication, not a build
or known software fault. Preserve the timeout evidence and request window/key
status without collecting a password. The scoped improvement is a fresh,
fully pinned retry receipt so the next Ready again starts immediately. Kernel
and display preparation remain the priority; physical OLED/touch/GPU and root
handoff remain unqualified. Previous r54 remains useful offline progress.

## Actual host handoff and sealed frame integration (r56, 2026-09-11)

Previous r55 supplied new evidence: the prepared attempt timed out and was
cleaned up, with a fresh unique retry prepared. This continuation began with
independent frame work and did not reuse the expired Ready. The subsequent
actual user Ready immediately launched prepared r3 after brief pin/source/boot
checks. **Authentication and capture/SSH privileged profiles PASS, 13.378 s.**

`oled-live-driver-r1/privilege-probe-r3` retains authentication, raw stdout/stderr,
process envelopes and decoded results. Both real root guardians reported UIDs
[0,0,0,0]; their runuser children reported deck UID/EUID/GID/EGID 1000. All
process results report successful reap without forcing or errors; independent
terminal PID/start checks found no original launcher/root/controller or deck
child remaining. Raw results equal decoded rows and stderr is empty. The GUI
closed. The completion receipt is
`handoff-preparation-r2/completed.json`, SHA `b38eff45…`, bound to Q `462cef05`
and the unchanged source digest/host boot. No phone/network/claim action or
admission occurred. The user was immediately released from waiting. No further
password attempt is pending, and the failed r2 remains unchanged.

New import-only `oled-display-component-r1/frame.py` validates the 248-byte
capture framing/hash, boot/bundle/kernel and source scope. It snapshots the
existing pinned 1,252,408-byte ARM64 ELF into a sealed memfd and executes that
owned descriptor. The two child runs have five-second deadlines, bounded stdout
and 4-KiB stderr; exception paths kill/reap the owned helper and close pipes/FDs.
Layout metadata is limited to 4 KiB. Frame output is streamed in chunks of at
most 64 KiB, limited to validated stride*2448 (maximum 40,108,032 bytes), and
must be exact length before seals are installed. No whole-frame Python buffer
is allocated. The returned context-managed Frame owns its sealed descriptor;
its copied receipt binds complete capture, boot, raw record, renderer and frame
hashes. Fresh same-boot/node/layout comparison is still required before write.

The actual ARM64 renderer under QEMU emitted the retained 10,653,696-byte frame
SHA `859231da…`; describe took 0.020685 s and render 0.121756 s. Kernel/package/
Rust binaries were reused without compilation. Initial 12 tests passed in
0.864 s; review added closed-pipe deadline, pidfd failure and sealing-failure
coverage, and an explicit total frame bound. Final **15 tests pass in 1.221 s**
(1.367 s outer runner). Successful rendering, source-path replacement, seals,
record/node/boot mutation, real Rust malformed-layout refusal, timeout, output
limit, stderr, exit, short output and actual /dev/full failure are covered.
Every case verifies descriptor inventory. QEMU only redirects executable launch;
explicit sysfs/char-node/ioctl fixtures are inherited from the collector tests,
and named Python children inject process faults. This proves no actual phone
layout or scanout. All jobs are terminal. Result receipt:
`oled-display-component-r1/frame-result-r1.json`, SHA `787baaa3…`.

After-run review: the actual authentication success removes the known host
handoff prerequisite without speculative GUI changes. Sealed frame preparation
adds a fast reusable operation (about 0.142 s in QEMU), preserves all existing
kernel/display artifacts and avoids whole-frame buffering. Guarded device write,
bounded brightness and the existing load/health/capture/controller integration
are next. Physical OLED/touch/Adreno remain unqualified; no phone was queried or
changed this turn. Denial/Flutter builds remain deferred behind kernel hardware.

## Guarded frame write/readback (r57, 2026-09-11)

Previous r56 is progress: actual host authentication/root handoff passed and the
sealed ARM64 frame component passed. No process was left running, and no Ready
or password request is pending. This turn implements the next device-write
component offline without querying or changing the phone.

`oled-display-component-r1/write-frame.py` imports the exact frame component.
`write_once(frame, capture, boot, authorize, enter)` requires the owner's current
admission/full-health/monitor predicate and durable one-use entry callback. It
verifies sealed bytes against their receipt, consumes in-process frame ownership
before invoking entry, then requires a fresh matching framebuffer GET capture.
It validates an O_PATH descriptor before reopening that owned inode O_RDWR;
1-MiB positioned writes/readback renew the exact endpoint/boot/blank/node/layout
and admission checks. Success requires exact lengths and a matching full frame
hash. There is no brightness write, mode-set, mmap, unload or retry.

Short writes retain their acknowledged count and stop. A write exception records
an uncertain outcome without assuming zero kernel side effects. Durable-entry
uncertainty consumes the local attempt and stops before device open. Cleanup
closes both device and path descriptors; close errors preserve the write/readback
counts and force FAIL. Ten-second between-syscall deadline checks supplement,
but do not replace, the enclosing owner's bounded worker and cleanup.

Exact kernel revision `05941d04803f54208da1e9920a81874edc540ca1` and five
inspected files are unchanged against HEAD: DMA fbdev operations, fb_chrdev,
fb_sys_fops, fb.h and fs/open.c. They establish the source paths for positioned
read/write and deferred damage notification. They do not establish actual driver
binding, damage completion, physical refresh timing or visible OLED output.

Initial 16 tests passed in 3.131 s. Review added mid-write boot/deadline changes
and a close-error case, and fixed cleanup to retain partial/completed-write
evidence. Final **19 tests pass in 3.855 s** (4.022 s runner). The successful
10,653,696-byte fixture frame writes in 11 chunks and reads back the identical
SHA `859231da…`, in **0.096920 s**. Source/capture/entry/authorization refusal,
node replacement, layout/brightness/boot changes, short/uncertain write, corrupt/
short readback, closed frame, changed receipt, timeout, close errors and one-use
refusal are covered. All cases check descriptor inventory. Actual memfds, ARM64
renderer through QEMU, file pwrite/pread and descriptor operations are used;
char-node/sysfs/ioctl, admission and durable entry are explicit fixtures. The
mid-write deadline case advances a simulated clock. No physical framebuffer was
opened. Receipts and logs remain under `oled-display-component-r1`; final result
`write-result-r1.json` is SHA `da73f546…`.

After-run review: the small writer/readback adds about 0.097 s in the file fixture;
no unchanged build or large test was repeated. The useful scoped improvement
was preserving known and uncertain write outcomes through cleanup failures.
Next is bounded brightness/blanking and integration with the existing admitted
module-load/full-health/monitor/entry controller, then complete preparation before
fresh physical Ready. OLED/touch/Adreno remain unqualified. Authentication r3
PASS is retained; no new password attempt, phone/network/claim action occurred.

## Timed low-brightness session and independent blank cleanup (r58, 2026-09-11)

Previous r57 is progress: the entered framebuffer writer/readback passed 19
focused offline cases. This turn connects it to `display-session.py`, an
import-only prepared-owner component. It reuses the exact writer/frame/collector/
endpoint pins and existing ARM64 binary. No compilation or phone action occurred.

`show_once(frame, capture, boot, authorize, enter, cleanup_authorize, armed)`
requires independent cleanup ownership before entering. It carries fixed
brightness32, maximum1023, duration20 s and cleanup0 in the owner's durable intent.
After actual frame write/readback in the fixture, it verifies the exact blank
backlight, opens a nofollow owned brightness FD, writes only 32 newline and checks
readback. A nonblocking `armed` callback queues the observation prompt. The human
response is collected outside this timed loop. It samples identity/brightness
and normal authorization at 0.25-second intervals, then invokes pinned blanking.

Once entry is acknowledged, cleanup runs even after writer failure, ordinary
health refusal, prompt delivery failure or uncertain nonzero write. It uses the
distinct cleanup predicate, verifies exact current boot/device and reports zero
failure independently. A different boot refuses cleanup against that boot. A
failed blank never supplies a blank PASS. All owned brightness FDs close. These
are command/readback checks; physical visibility/darkness, final full health and
admission remain false, and a bounded enclosing worker/monitor is still required.

Initial `session-tests-r1` failed one of 14 cases: a short-write fixture left
b'3' as sysfs readback, omitting the canonical newline. The endpoint correctly
refused that invalid value before blanking. The fixture now exposes b'3 newline'
while retaining its short return. No runtime validation was relaxed. The next
15-case suite passed in 23.719 s, including a production 20-second real-clock
case. Review then added a post-authorization deadline check and slow-callback
regression, preventing a delayed authorization from queuing a late prompt.
Final **16 cases pass in 23.933 s** (24.112 s outer runner).

The final real-clock production-duration fixture took **20.003377 s** from the
nonzero attempt to confirmed zero, **20.094627 s** total, with 80 samples. The
virtual-clock nominal case also covers the full 20-second protocol; a separate
shortened real-clock case exercises the wait path cheaply. Failure cases cover
missing cleanup permission, rejected durable entry, partial frame write, health
loss, late callback, failed/raising/blocking prompt callback, short/uncertain
brightness write, external brightness change, failed zero write and changed boot.
All cases inherit descriptor-leak checks. Real sealed ARM64 frame/file I/O is
used; sysfs store/device/ioctl, admission, entry and monitor are explicit fixtures.
Result `oled-display-component-r1/session-result-r1.json` is SHA `d30d2168…`.

After-run review: rechecking the deadline after callbacks closes a real ordering
hole; preserving independently authorized blank cleanup prevents normal health
failure from disabling the available off path. The repeated sysfs fixture issue
is now recorded as a canonical-store requirement. The slow stage here was the
intentional real-clock 20-second test; keep virtual-clock fault cases and reuse
unchanged timing evidence. Existing module-monitor/protocol/client and physical
backend/admission components were located under the retained CPU state; next is
OLED integration with updated identity/health/capture-closure bindings. They are
historical f17 components, not already valid for OLED. No new receiver family,
boot claim, authentication request or physical Ready is created by this turn.

## OLED component transport adapter (r59, 2026-09-11)

Previous r58 is progress: the timed display session and blank cleanup passed.
New `oled-component-monitor-r1/transport.py` loads the exact existing module
monitor/client/protocol after verifying all three hashes, then gives server and
client separate OLED boot/output contexts. Original files and serving/state logic
are unchanged. The source label is Q `462cef05`; its qualification still belongs
to the prepared owner. The adapter itself creates no phone, boot or health authority.

The 660-second lifetime, 0.5-second samples, one-second freshness limit, latched
failure, exact launcher PID/start/argv, Unix peer credentials/socket identity,
receipt/controller/admission hashes, monotonic append-only journal checks and
cleanup-gated finish are preserved. The caller must supply the production
admission and validated closure/health callbacks. A reviewed `monitor.py` in a
private OLED phase namespace is required and pinned alongside inherited sources
and the adapter. Nonempty output refuses before allocating server resources.

Initial ten tests passed in 2.316 s. Review added a required launcher-file pin,
reused-output preflight and two regression cases. Final **12 tests pass in
2.468 s** (2.622 s runner). Actual child processes, PID/start/argv checks, Unix
sockets, peer credentials, source/receipt/journal checks, signal/reap and FD/socket
cleanup are exercised. Scenarios include disconnect then reconnect (failure stays
latched), wrong boot, changed admission/launcher/journal, wrong socket/PID, finished
or dead process, cross-context independence, wrong namespace/old boot/direct
launcher and finish before cleanup. The retained positive trace has a live probe
followed by FINISHED and child exit zero. All fixture directories/children closed.
USB sampling, admission and physical cleanup/full health are explicit fixtures;
`fixture-child.py` must not become the production launcher. No phone/real-USB/
authentication action ran. Result `result-r1.json` is SHA `1db833c4…`.

After-run review: the inherited loop needed no rewrite or new receiver family;
focused real-process checks completed in under three seconds. Pinning the launcher
and rejecting reused output close concrete gaps in the adapter. Next wire actual
OLED owner/admission, closed full-boot capture, fresh authenticated target health,
real USB sampling and post-component blank/full-health closure into the adapter
and display session. Physical display acceptance and the long-term goal remain
incomplete. No new operator readiness or password request is pending.

## Current-source qualification and exact registry boundary (r60, 2026-09-11)

Previous r59 is progress: the OLED component transport adapter passed real
process/socket tests. Inspection of the existing health/capture callbacks found
the independent successor health predicate and the fixed full-capture closure
records. Before adding another component admission, the existing boot-controller
qualification could now be completed using actual r56 privilege evidence.

The four full-controller paths were replayed at exact current Q `462cef05` in
`oled-live-driver-r1/full-flow-tests-r4`: **4 tests PASS in 14.843 s** (15.749 s
runner). Target COMPONENT_PASS includes full capture and post-health; early and
late fallback and pre-reboot source-abort remain FAIL with selection eligibility
restored in explicit fixtures. Real owned capture subprocesses are used; USB,
SSH, target health, privilege/network/claims and time advancement are fixtures.
No physical capture duration or fallback recovery is claimed from these replays.
The actual r56 root capture/SSH handoff evidence is separately checked against
all retained hashes, matching source/host boot and actual UID/deck/reap results.

The real 31-file admission input reader passes in **0.162347 s**, with input lock
SHA `d905fc12…`, source digest `d374969e…`, verifier `3786d379…` and launcher
`f15ff5da…`. The production qualification reader now accepts
`live-qualification.json`, SHA `a60705b5…`, containing 450 pinned evidence files.
Result is retained at `qualification-preparation-r1/result.json`.

Evidence assembly first stopped on two 1,682,152-byte stage requests, beyond the
reader's1MiB limit. Their exact bytes are retained in four ordered private chunks
and a pinned manifest. The initial written candidate then failed strict metadata:
empty streams and mode0644 artifacts are not accepted as nonempty0600 receipts.
That candidate is preserved as `unvalidated-qualification-r1.json` with its FAIL
record. Three artifacts received byte-identical0600 archive copies and eight
empty streams are explicitly recorded in the manifest. All final references
passed the actual receipt reader before canonical write, and the qualification
verifier then passed. Original evidence and runtime checks were not weakened.
No full-flow, build or privileged check was repeated to resolve archive format.

A subsequent read-only `registered_claim()` check conclusively refuses the OLED
profile: **claim profile is not repository-owned**. The expected-field producer
is ready, but Q's static claim registry lacks the OLED entry. No claim file was
created or consumed. Registration/source and affected pin changes must precede
another final qualification; preserve the present qualification with its actual
source. No trial directory, phone query/write, password request or human Ready
was created. After-run improvement is enforcing the full evidence-file contract
before publication and checking this concrete registry boundary before treating
a green software qualification as a prepared executable hardware trial.

## Exact OLED claim registration and final-source preparation (r61, 2026-09-11)

Q is clean at `538fab85a0cc809f0c9ff20a7ae64dd133d27b63`, source digest
`ef59307b79a087315402c850c0b067474bf5f6ef0ddd2faa84e4fb823434beb4`.
The registry adds only `oled-05941-a2be906cd7b36636`, generated from the verified
expected-field producer. All 227 previous records are byte-identical. The
consumer functions are unchanged. Claim regression tests pass **21 in 0.233 s**
(0.358 s runner), including exact artifacts, exclusive pending creation, no early
entry and permanent retry refusal after consumption in isolated fixtures.

The actual account-relative pending record was prepared through existing strict
root/anchor checks and the exclusive, fsynced writer in **0.022 s**. Its SHA is
`51f8b2bfe2f398b5150881a18cce69c857b8f730ee2a3d724bb87551b907568c`.
Before/after comparison verifies all 627 previous records/global guards unchanged
in content, inode and metadata. The OLED attempt is not consumed. No phone action,
launch directory or controller execution exists. Evidence lives under
`oled-live-driver-r1/claim-registration-r1`.

The r60 qualification and source cohort were archived before derivative changes.
Only four cohort files changed, exclusively digest literals; pin map r7 and two
input-lock code rows were refreshed. The 31-file actual input check passes.
Existing r56 real root/runuser capture/SSH handoff is explicitly inherited for
unchanged entrypoint/process code, with original source and all raw result hashes
retained. This is not a new authentication or proof of current sudo credentials.

Final-source checks pass: boot callbacks **17 in 2.970 s**, launcher **21 in
0.769 s**, admission **24 in 0.447 s**, four complete controller paths **4 in
15.471 s**. Summed runner time is 21.898 s. Target is COMPONENT_PASS; early/late
fallback and pre-reboot abort remain expected FAIL with restoration verified in
fixtures. Real capture subprocesses execute; external hardware/USB/SSH/privilege/
network/claim/time inputs are explicit fixtures. Original r60 results remain
unchanged. No hardware recovery claim follows from these replays.

The production qualification reader accepts **460 pinned evidence files**, SHA
`18b1717fee2bb1425f79565f0f4e8137faefb52756fa9e5c825a22118e578830`.
Every input was validated or archived as exact bounded private chunks/copies;
empty streams are explicit manifest entries. No invalid canonical candidate was
written this turn. Actual read-only launcher `prepare()` now passes in **0.256 s**
with the final source, qualification, registry and unused pending record.

After-run review: registering before final replay avoided another stale-source
qualification cycle. Existing exact-record and archive primitives were sufficient;
no replacement runtime guard or hardware retry was introduced. Next integrate
production module/monitor/display callbacks and full health/capture closure.
Physical availability remains released until the full test is prepared. OLED,
front touch, GPU and real Denial acceptance remain incomplete.

## Fixed module loading and early blanking (r62, 2026-09-11)

Previous r61 is progress: the exact OLED claim became registered/pending, with
current-source qualification and read-only launcher preparation passing. That
source/qualification and its unused attempt remain unchanged this turn.

`oled-display-component-r1/load-modules.py` now implements the target REFGEN →
panel sequence, SHA `ae33fc62674be823a35533f0b5c5692158f4a9c0df1711c8d9607ca9cd69fb9d`.
It verifies exact root-owned payload bytes and keeps directory/file descriptors,
requires durable paired entry and fresh owner/health authorization, then invokes
the existing `module-once` helper once per module. REFGEN binding and regulator
identity precede panel loading. Parent polling watches for the exact backlight
while the helper remains alive and requests zero through the unchanged endpoint
component. Each child has a five-second deadline, two-second reap bound and
4-KiB output limits. Framebuffer discovery is bounded; no framebuffer device is
opened here. There is no unload or retry path.

Failure cleanup uses separate same-boot ownership, including after early blanking
if later brightness/health changes. Changed boots refuse stale cleanup. Uncertain
durable entry consumes the local object; the external owner still must enforce
persistent one-use state across objects/processes. The full owner/admission,
boot-capture, monitor and authenticated health integration remains pending.

The helper was streamed from the retained signed-payload archive, exact size
219,912 and SHA `74436199…`; REFGEN/panel artifacts are unchanged. An initial
incorrect 64-KiB helper-size assumption refused before extraction/execution and is
recorded. No kernel/module/DT/package rebuild occurred. An initial fixture helper
signature error stopped all cases in 0.192 s; it is retained and corrected only
in test setup. The subsequent 15 cases passed in 1.079 s. Review added helper
replacement checking and cleanup for a brightness change after early zero.

Final **17 checks pass in 1.268 s** (1.384 s runner), with real files, owned child
processes, descriptors, timeout/signal/reap and explicit insertion/probe/sysfs/
health fixtures. The positive sequence completed in 0.174 s and issued zero while
the panel child still existed; both children exited/reaped. Negative cases cover
first/panel failures, normal-health loss, changed boot, timeout/output overflow,
missing framebuffer, cleanup refusal, uncertain entry, preloaded module, changed
payload/helper, module symlink and descriptor closure. A late brightness change
receives a separate final zero. Trusted target payload ancestry is substituted
for the test directory, and no real driver insertion is claimed.

The exact ARM64 helper ran through QEMU in a root user namespace and refused one
`finit_module` with errno38 (`Function not implemented` in this execution path).
It exited one and was reaped, with no second invocation. This does not exercise
real hardware or establish kernel driver success. Evidence and results are in
`module-tests-r3.*` and `module-result-r1.json`, result SHA
`a5da3d3e464839bf13974feae6647e9b226d8c2615203d3b44c7e1c9c90afc97`.

After-run review: existing helper and endpoint code were sufficient; active
endpoint observation and independent final zero close specific probing/cleanup
gaps without altering boot qualification. No full-flow or 20-second frame test
was repeated. About 51.9 GB disk remained free. No phone/claim/authentication
operation or human request occurred. Next connect this component and the prepared
frame session to the production monitor/admission and full-health closure.

## Completed OLED boot provenance and fresh component health (r63, 2026-09-11)

Previous r62 is progress: exact module loading/early blanking passed 17 focused
checks. The next integration now has a concrete reader for the existing boot
controller's actual output and a read-only health collector/verifier:
`oled-component-monitor-r1/provenance.py`, SHA
`f4c43495c3927e67bec4b311b27915b2330dc6f570f5815675dcb90bc78231bb`.

`boot_provenance(boot)` uses fixed actual execution/launch paths and verifies the
current source/qualification, exact consumed OLED claim, launcher/phase completion,
128-MiB image transfer, root capture owner identity, original 1380-second lifetime,
raw stream hashes, ordered route/firewall/profile/address cleanup and gone original
processes. The postcapture health intent must follow closure and bind the exact
health script; its raw SSH output runs through the existing full target validator.
Capture events remain unauthenticated; SSH health supplies target identity.
Historical boot admission grants no new component authority.

`collect_health` makes one bounded, exact read-only SSH query into a new private
before/after health directory, retaining entry/raw transport/result. `verify_health`
revalidates those bytes, script, source/host boot, full target health and monotonic
freshness (40-second query budget, maximum age120s). Each numbered output is
exclusive; a fresh numbered health sample may replace an expired prerequisite
without replacing evidence or consuming a hardware attempt. The production owner
still must bind the exact result path/hash and before/after role.

Final **22 provenance/health cases pass in 0.505 s** (0.964 s runner). They copy
retained controller-flow receipts into a private fixture; root UID/time, source/
claim admission and SSH are explicit fixtures. Checks cover incomplete/shortened
captures, missing cleanup, changed raw streams, events after terminal, wrong boot/
image/source, still-present original process, failed launcher, health before
closure, changed scripts and raw health, absent physical guards, expiry, refresh,
namespace bounds, symlinks and no silent retry after a failed query. Initial17
and intermediate20/22-case passes remain retained; no test failure occurred.

The existing transport adapter's only runtime change is source revision462cef05
→538fab85, SHA `7e754d20ef6efcf1e55b0eae34ff524099ff66ca4ab95607c6ebfaab438a4558`.
All **12 real-process/socket checks pass in 2.450 s** (2.579 s runner), retaining
latched failures and process/socket/journal/cleanup checks. The r59 source and
result are preserved in `source-refresh-r1` before the revision update.

The reused original USB sampler passed an actual host-files/route-only check in
**0.036478 s**: mode target, interface `enp4s0f3u1u2`, driver `cdc_ncm`, product
`ROG5 persistent root`, anchor `1-1.2`, serial descriptor absent. The source that
executed this observation is archived; its sampler function is unchanged in the
final file. This does not authenticate the phone's boot/kernel or full health.
No SSH, phone write, module load or monitor run occurred. The exact consumed-claim
read-only check correctly refuses because the OLED pending record still exists.
That record and the r61 boot qualification are unchanged.

Evidence/result: `oled-component-monitor-r1/source-refresh-r1/result.json`, SHA
`4b1d7978992623c80831d10338c93763d0a9a4b92e7155c5f968ec97ad5a779c`.
After-run improvement separates health refresh from one-use hardware attempts,
so readiness delays do not force repeated hardware work. Existing workers,
validators and sampler were reused; no build, full-controller replay or privilege
prompt was repeated. Next connect production component owner/admission, monitor
launch/finish closure and the bounded remote module/frame backend. No physical
Ready request is pending and real OLED/touch/GPU/Denial acceptance is incomplete.

## Owned component monitor lifecycle (r64, 2026-09-11)

Previous r63 is progress: completed-boot/fresh-health readers and the actual
host USB sampler passed. The next host lifecycle now exists in
`oled-component-monitor-r1/session.py` (SHA
`3c32272fd0f6ec4eb98749640114f1833d5452927cd8cf4b0bb5def7334e7a20`)
and its qualified copied `monitor-launcher.py` (SHA
`f7e293117a9e2ecd9c83acc9f47337ded33de47ab622c693a9a9efa5bc6d3645`).

`Owner(phase,boot,health_directory,run_id,qualification_sha256)` checks the exact
current source qualification, completed boot and fresh full health, then takes a
global device-component flock. It creates a numbered private monitor namespace,
binds controller PID/start/argv and the exact source inventory, and owns start,
live probe, finish and stop/reap. A closed, unentered monitor can be replaced by
a new numbered monitor; existing hardware phase entry remains non-repeatable.
No hardware entry or phone action is performed by this owner itself.

The monitor uses the existing transport engine/sampler. Each sample also checks
its live owner, admission hash and lifetime. Finish verifies the same owner/boot/
monitor binding, terminal component status and cleanup, exact zero command,
remote-worker reap and full health newly sampled after component completion.
Cleanup verification works independently of normal owner liveness. It does not
convert a failed monitor to PASS or claim optical darkness. The forthcoming
bounded target backend must supply validated remote and cleanup records.

Final **19 checks pass in 2.155 s** (2.624 s runner). Real host child processes,
Unix sockets and peer PID/argv checks run through owner start/probe/finish/reap.
One test mutates then restores admission; the live sampler latches failure, and
verified cleanup closes it with terminal FAIL/exit1. Other checks exercise actual
flock exclusion within/across phases, immutable entry refusal, code/launcher
changes, stale health/launch admission, missing boot proof, parent loss, zero/
worker/health ordering, boolean brightness and direct-template refusal. Phone
boot/health/USB and the process bootstrap are named explicit fixtures; there is
no production monitor or target action.

The initial cleanup fixture used completion timestamps before its admission,
causing two failures and one error in 0.903 s. The timestamp guard was correct;
fixture ordering was fixed, and all16 cases passed. Two actual owner/monitor
process cases then passed as part of18 tests. Review found phase-local locks
could overlap; the final global lock and cross-phase regression passed19 cases.
The first qualification/source snapshot is retained as historical, and the final
production qualification reader accepts the refreshed fixed qualification file.

Current `component-qualification-r1.json` SHA:
`438a0d20d0a15ce1bd18d211ae00f2c8d1723cd9b93d9992e5ba886aed079e67`.
It pins13 runtime source files and15 evidence references, inheriting the unchanged
endpoint/module/frame component checks. Result `session-qualification-r2/result.json`
is SHA `76df5ebe1171b24c15c7e94c55c740b70cd9d3fc8b05b75a853c3c5a2c598416`.

After-run improvement is device-wide ownership and a real lifecycle integration
case that proves restored bytes do not clear failure. No kernel/package build,
full boot replay, phone health query or password prompt was repeated. Q538fab85,
r61 boot qualification and the unused OLED claim remain unchanged. Next finish
the bounded authenticated SSH backend/coordinator, including target-side timeout,
independent zero cleanup and durable one-use phase records. Physical Ready stays
unrequested until the complete test is prepared.

## Bounded target module supervisor (r65, 2026-09-11)

Current Ready was released after reading the saved state: no complete physical
test was prepared, so no operator timer, password window or phone action began.
The pending r64 docs/checkpoint were finalized, then the fixed target module
backend was implemented at `oled-module-backend-r1/backend.py`, SHA
`303e9075a09bdf2e56717c5897a6b2d6bf9c7c24f5b4c6977385a59e1acdf5bd`.
It loads the unchanged exact endpoint and module-loader components. Its CLI
requires the fixed private root-owned `/run/rog5-oled-modules-<owner>` namespace,
pinned manifest and source inventory; it offers no staging, arbitrary command,
boot, unload or retry interface. The host transport/coordinator is still absent.

The authenticated SSH stream must carry bounded JSON lines with exact boot,
owner, phase, monitor receipt, monotonic sequence and a fixed command. Three-second
leases and a 60-second absolute normal deadline are measured on the target. The
parent takes a global module flock and reserves the run exclusively. The worker
requests entry; the parent durably records the intent once and sends its hash to
the host, which must reserve the host phase before acknowledging it. No insertion
occurs before acknowledgement. Missing/wrong/late acknowledgements leave the
attempt non-repeatable. Child callbacks use bounded socket requests.

All hardware calls run in a separate session/process group. On failure or lost
connection the supervisor kills/reaps that owned group, then after any entry
attempts a separate four-second zero-cleanup worker with exact same-boot ownership
and a two-second reap allowance. Normal monitor failure cannot suppress cleanup.
Changed boot refuses stale cleanup. Parent reap and process-group absence are
recorded separately; a task stuck in kernel sleep cannot be promised terminated.
Failures preserve their status and cleanup evidence. RAM terminal evidence is
saved before output delivery, including when the host stops reading. The result
records target monotonic time; future host health ordering must use the host's
observed completion time, never compare clocks across machines.

Final verification: **22 real process/socket/pipe cases in 4.009 s** (4.129 s
runner), and **six actual root-owned RAM/source checks in 0.008 s** (0.115 s
runner). Hardware identity/sysfs/insertion are explicit fixtures; process and
namespace/file contracts are actual. The positive path reaps both workers and
records zero. Negative cases cover lost lease, EOF, blocked output/worker/cleanup,
module and cleanup failures, changed boot, wrong owner/monitor/ack, duplicate
sequence/start/entry, no start, overlapping owner and prior entry. Source-file
checks cover exact pinned bytes, changed manifest/source, symlink and wrong mode.

The first 16-case process suite passed in 2.606 s. Review retained failed cleanup
process evidence, checked process-group absence and excluded access-time changes
from stable source metadata. The final 22-case suite passed. Root-file setup
initially stopped with PermissionError reading `/proc/1/ns/mnt` inside the new
user namespace (0.114 s, zero cases, before any mount). Exact failed fixture and
output remain at `context-tests-r1`; passing `context-tests-r2` captures the
outer process's mount namespace before unshare. Only the six pending cases ran.

Final result `oled-module-backend-r1/result.json`, SHA
`f14c31c0971b20cbe76bc9377afef6a0d9f548600d29644351457707d9964699`, pins
current sources and final evidence, total 28 checks and 4.243 s runner time.
No kernel, Rust renderer, module or wrapper rebuild, full boot replay, privilege
prompt or phone query was repeated. r61 boot qualification/pending claim and
r64 monitor qualification remain unchanged. The next task is authenticated host
staging/duplex SSH and the module coordinator, followed by the frame supervisor.
Actual OLED boot, completed capture and fresh authenticated health remain required
before module insertion; OLED/touch/GPU/Denial hardware acceptance is incomplete.

## Authenticated module host coordinator (r66, 2026-09-11)

Previous r65 is progress: its bounded target module supervisor passed28 offline
checks and remains unchanged. The missing host staging/duplex/coordinator now
exists in `oled-module-host-r1/coordinator.py`, SHA
`4f2e7e255ba8ff96371879fd3b7c6eca1bc11ca71dac0b65ad5082a306fb85e4`.
It pins r64 owner/monitor qualification and r65 backend evidence, and reuses the
existing OLED SSH worker's credentials, host-key pin, clean source, exact USB
identity/topology and route gates. There is no new network receiver or host-root
operation in the normal path.

The generated staging script carries only the three exact backend/endpoint/loader
sources and fixed manifest. It checks actual target boot/kernel/descriptor before
creating its private RAM namespace, validates root ownership/parent permissions,
writes exclusively and verifies staged context and identity again. Staging uses
the existing35-second bounded SSH worker. Live execution then uses sequenced
JSON records over stdin/stdout with bounded output, no buffering or command retry.
The host module phase is reserved before spawning SSH; any uncertain start remains
consumed. Exact helper, REFGEN and panel identities, order and limits must match
the target entry request before a durable host acknowledgement is sent.

Leases renew every0.75s only after a current monitor probe. Loss of monitor or
protocol validity closes stdin while allowing up to14s for target action/cleanup
closure; total normal host transport budget is78s. Direct target process reap,
absent helper group, exact insertion records, zero/readback identity, terminal
status, raw framing and SSH exit are independently checked. Output is retained
with bounded files. A terminal component result uses host monotonic completion
for later health ordering, preserving target monotonic as separate evidence.
No cross-machine clock comparison is used.

After proven target cleanup/reap, full authenticated health is collected before
monitor finish. Review reproduced a real bug in the initial coordinator: a
`finished=True, failed=True` cleanup reply could produce overall PASS when module
loading itself passed. `monitor-failure-replay-r1` retains the failed assertion,
original code and output. The corrected coordinator requires nonfailed finish,
zero monitor process exit and a matching durable FINISHED result, including the
component-result hash. Target component success remains recorded separately from
an overall monitor/coordinator failure.

Final `tests-r3` passes **17 cases in1.941s** (2.220s runner). The full positive
sequence executes actual RAM staging logic and duplex target supervisor, then
checks health-after-cleanup and monitor closure ordering. Other cases include
monitor loss while a real child is blocked, failed modules with independently
successful zero, changed-boot refusal, wrong intent, immutable host entry,
transport spawn failure, stderr, tampered digest, source/USB/route gate ordering and wrong USB refusal,
missing boot proof and exact terminal insertion/brightness validation. SSH and
phone effects, completed boot and already-qualified monitor/health boundaries are
explicit fixtures. Root-owned files and processes use private user/mount namespaces;
no test authenticates or mutates the phone.

The first suite had12 passes and one staging fixture error. A retained diagnostic
proved its tmpfs `/run` defaulted to world-writable; production correctly refused
`RAM parent`. Fixture mode755 fixed this without changing production guards. Five
remaining/new checks then passed in0.259s. The subsequent monitor regression was
reproduced before correction and justified the final17-case rerun. Only the
qualification-negative test was later adjusted to an isolated directory so future
published qualification/retained runs cannot break that fixture; its focused
check passes in0.001s. All source snapshots and failed outputs remain retained.

Current qualification `oled-module-host-r1/result.json` SHA:
`61ec008fbe17ed3b3269d24603bec1fdc415c01d05678b8272639ba10200b911`.
The actual qualified reader accepts it in0.006434s. It binds current coordinator,
final evidence and unchanged prior component qualifications. The callable entry
is `run(boot,run_id,qualification_sha256)`; direct CLI execution refuses. No real
run namespace or module phase entry has been created. No authentication, live
monitor, phone health query, staging, insertion, boot or claim action occurred.

After-run improvement is preserving latched failure through the final assembly,
with a regression at the real client contract. Reused kernel/DT/modules/renderer,
boot qualification and target backend; no rebuild or unchanged full boot replay.
The next missing component is the bounded frame backend/coordinator and prepared
physical prompt path. Real OLED boot plus completed capture and fresh health must
precede module execution. No physical Ready is requested until the test is ready;
OLED/touch/GPU/Denial acceptance remains incomplete.

## Prepared target frame backend (r67, 2026-09-11)

Previous r66 is progress: complete module host coordinator qualified with17
integration cases, unchanged here. The next target frame worker is implemented
at `oled-frame-backend-r1/backend.py`, SHA
`1087ed7d00e8a0ee019da287184b20fb3054ec1c609dbdffd758f33c45ab21ff`.
It imports an exact private copy of the r65 module backend for framing, owned
fork/reap and independent zero cleanup, installing only a fixed frame worker in
that private module instance. The original module backend and host coordinator
remain byte-identical. All five display-component sources and the1,252,408-byte
ARM64 renderer are copied unchanged, not rebuilt.

The frame worker requests capture-only admission, then calls the actual existing
zero-state GET collector and sealed-frame producer. It holds the sealed frame
while waiting for Ready. Parent verification binds capture bytes, framebuffer
node, frame hash and renderer. A Ready command must match the prepared hash and
current owner/boot/monitor, carry a new caller-supplied token and arrive in the
prepared phase before its deadline. Host coordination must create that token only
from fresh human availability; the target protocol cannot establish human
presence independently. Early, mismatched and repeated Ready refuse.

After Ready, the unchanged writer/display session asks for the exact one-use
frame/brightness32/20-second intent. The target global frame entry is created
exclusively before host acknowledgement. Nonzero brightness readback triggers
an immediate output event and acknowledgement to the fixed display callback;
no callback waits for the user's observation. Production limits:3-second leases,
15-second capture/render,60-second prepared Ready window,35-second active window,
120-second overall bound. The unchanged display component owns20 seconds of
brightness then zero. Outer supervision kills/reaps blocked work and runs the
independent four-second same-boot zero worker with two-second reap allowance.
Uninterruptible kernel work is not promised terminated; incomplete closure stays
FAIL. Zero readback is not optical-darkness evidence.

Preparation entry is deliberately separate from the global frame-write entry.
If readiness expires, capture/render cleanup runs but an image never shown does
not consume the write. The future host must retain aborted preparation evidence,
verify zero/reap and fresh health before a new preparation, and preserve every
actual write entry. It must not treat capture-only cancellation as successful
physical frame acceptance or reuse an expired Ready response.

`tests-r1`: **14 cases PASS in1.840s**,1.971s runner. Real parent/child/socket/pipe
and termination paths run with explicit fixture phone/capture/frame/display
boundaries and shortened phase timers. Cases cover waiting unlit, missing/early/
wrong/duplicate Ready, blocked capture/display despite renewed lease, EOF while
lit, wrong frame intent/prompt, changed boot, cleanup failure, consumed entry and
wrong capture identity. The positive case binds the prepared hash, emits the
prompt, closes the frame, zeros and reaps both worker groups. Missing Ready never
calls the display or creates global write entry.

`context-tests-r1`: **six cases PASS in0.039s**,0.165s runner. Actual root-owned
RAM files in a private user/mount namespace verify current backend/component and
renderer bytes, metadata and manifest. Changed renderer, symlink, wrong mode,
wrong manifest and consumed entry refuse. Both suites passed first time using
outer mount-namespace capture and mode755 parent, carrying forward r65/r66 setup
lessons. The original real ARM64 renderer and20-second component checks are
inherited for unchanged bytes; these faster fixtures do not re-prove that timing
or actual phone scanout.

Result `oled-frame-backend-r1/result.json` SHA:
`f310d724433cca58d1f849a193a7dc68898e10364a7c789ded0771d1444aeddd`.
It pins eight runtime files and the new evidence, totals20 cases and2.136s runner,
and names inherited unchanged qualification results. No real SSH, phone query,
RAM staging, module/frame action, brightness change, boot or claim action ran.
No kernel/module/renderer/package build, full boot replay or authentication was
repeated. The remaining step is the frame host staging/duplex/Ready/prompt
coordinator, including completed-module provenance and after-cleanup health.
Actual OLED boot/capture and module qualification must precede frame preparation;
OLED/touch/GPU/Denial acceptance remains incomplete. No Ready request is pending.

## Complete frame host and current source health (r68, 2026-09-11)

Previous r67 is progress: prepared target frame worker qualified20 offline checks,
unchanged here. The frame host now exists at `oled-frame-host-r1/coordinator.py`,
SHA `b3b23b5b7eaddd46196b09c93b3a69ea4a5643e190c5bef31d085d9611666c74`.
It reuses module-host credential/USB/source/route gates and fixed staging template,
with checked substitutions for the eight frame files, root RAM namespace and
bounded1.34MiB content. The generated source is deterministic and fits the existing
3MiB SSH-worker request. Renderer and all target components remain byte-identical.

Completed same-boot module evidence is checked against its actual phase result,
raw SSH terminal, monitor admission/receipt/closure, absent old monitor process,
source and qualification. A failed module monitor refuses frame preparation.
The frame controller keeps its actual process, qualified monitor and SSH alive
while the sealed target frame is prepared and awaiting availability. Host control
records bind process/start/argv, boot, owner, monitor receipt and prepared hash.
A fresh user reply writes one Ready token, checked again for age/hash/ownership
before reserving the host frame-write attempt and signaling the target. No old
reply or automatic goal continuation may invoke this API.

`ready(output,prepared_sha,user_reply)` checks the live controller and monitor;
`wait_visible(output)` returns the prompt on the nonzero-command event without
waiting for the user's observation. `observe(output,visible_sha,user_reply)`
records that actual report separately. The host keeps a conservative18-second
prompt-validity interval after receipt; the target independently owns20 seconds
of brightness. Host total transport bound is138s, allowing target120s plus cleanup,
with14s cleanup collection after a local failure. Full health follows target/SSH
closure, and final PASS requires a nonfailed monitor reply, zero exit and matching
durable FINISHED result. Cancelled capture-only preparation instead verifies zero,
reap and fresh health, closes its monitor, and preserves the unused write entry.
New preparation requires those records; incomplete old work refuses.

The new host/target flow executed the unchanged actual timed-display component
with real process/RPC, regular-file brightness I/O and prompt delivery:
**20.000655941s attempt-to-zero**,80 samples,20.163687451s coordinator duration.
Framebuffer/capture/render effects, phone identity and monitor/health are explicit
fixtures. This is software timing and control evidence, not phone scanout.
`timer-diagnostic-r1` passed in20.166s (20.448s runner), with exact executed source
SHA `409da91e831e16c4141ea2bdf699e4f33bbe7eb46427f1ce938a5fd981c7df39`
retained. Every existing function/class AST is identical in final source; only
atomic save implementation/import replaces the old save alias. The actual timer
result is inherited within that scope; it was not rerun or relabelled as testing
new publication code.

Final `tests-r2`: **17 cases PASS in3.656s**,3.978s runner, on current source.
They cover current Ready/prompt/transport, private RAM staging, exact module
proof and raw-output tampering, failed module monitor, full after-health/monitor
ordering, retained monitor failure, capture cancellation and refusal after its
health evidence changes, no-overwrite and complete-record publication. Host/target
processes and private root/mount file operations are actual. External SSH, phone
hardware, completed boot and monitor/health boundaries are explicit fixtures.

The first suite passed four cases, then reached its55s harness timeout while the
timer case was still waiting for Ready. Target evidence has no Ready token, no
write entry and brightness zero; after host death it records independent zero and
both worker groups reaped. No exact user-thread exception survived. The fixture
was preserved byte-for-byte under `tests-r1/interrupted-fixture` with15 file hashes.
The harness now records thread errors and stops leases immediately on them.
A separate deterministic blocked-writer regression then proved that the shared
exclusive-file writer exposes a destination before data is complete. That finding
motivates the fix, but does not prove the first timeout's cause. The frame host
now fsyncs a private temporary and publishes by atomic rename-no-replace; focused
positive and overwrite-refusal tests pass. Original replay and sources remain.

Current qualification `oled-frame-host-r1/result.json` SHA:
`c295ea99f852ef99b3e79b9f3c76cfe9719418afa8d6ee652a3b1e4108a2d939`.
The actual qualification reader passes in0.015404s, including unchanged module
host and target qualifications. It records18 unique cases including the scoped
actual timer run. No actual frame-host run directory or frame-write entry exists.

A fresh authenticated read-only source query now passes in **1.432967s** at
**21,829.53s uptime**. Same boot `de90d177-3532-49e0-9bfd-8f8c65889a8d`,
release `7.1.4-g05941d04803f`, bundle `kernel-hw-05941-a607a2bb249c918b`;
old V9 selection SHA `ed3a62d198a2e33d26093e079534315ae86ab28c91f48805463fd025c5b88b75`
is still restored. Current boot health, boot-bound readiness and physical guards
pass. Raw transport and full snapshot are retained in `source-health-r1`. It uses
the existing fixed restored-selection predicate; no phone write occurred.

Actual read-only launcher `prepare()` passes in0.205097s with clean source
Q538fab85, digestef59307b and live qualification18b1717f. `boot-preparation-r1`
retains the exact result. The pending OLED claim remains unused, and no live OLED
trial/recording exists. No kernel/module/renderer/package rebuild, full boot replay
or password prompt was repeated. Next fresh Deck authentication can launch the
fully prepared one-use OLED boot and23-minute observation; this is separate from
later fresh physical Ready after actual frame preparation. OLED/touch/GPU/Denial
acceptance remains incomplete.

## r69: immediate launch, authentication timeout and retained touch audit

Latest r69, 2026-09-11: fresh Ready immediately launched the prepared OLED
session. Authentication timed out after its 300-second limit. The Deck window
was observed, but no user response establishes whether it was visible or usable.
The owned authentication processes were reaped and the window is gone. Launcher
`oled-live-driver-r1/trial-launch-r1/result.json` is terminal FAIL, with no claim
consumption and no controller execution. No phone command or reboot occurred.
Preserve this entered launcher directory; the old launch instruction is no
longer executable. Do not clear it or retry the same entry. The exact pending
OLED claim remains unchanged. Resolve the authentication interaction and prepare
a reviewed fresh launch path before requesting availability again.

The retained successor touch/GPI/GENI twins were independently checked against
their guest receipt and exact 05941 vermagic in 0.022 s; all six copies match.
The earlier successor guest registration/unload result remains 3.797 s, with
GPI retained until guest poweroff. Updated the stale front-touch guide to reuse
these artifacts and distinguish the OLED-only DT, which does not enable touch.
This is cached artifact evidence, not physical touchscreen qualification.

After-run review: the five-minute authentication wait remains the observed
bottleneck. Window presence does not establish focus, visibility or successful
input; no wrong-password or keyboard diagnosis is justified without the user’s
answer. Keep the prepared artifacts and one-use protections. The scoped
improvement corrects stale touch build guidance using existing evidence,
avoiding an unnecessary rebuild while preserving physical qualification gates.

## r70: recoverable authentication before the one-use boot entry

Latest r70, 2026-09-11: the OLED launch is prepared again after the r69
password timeout. Authentication attempts now have separate exclusive receipts
under `oled-live-driver-r1/boot-authentication-r1`. A shared flock excludes
concurrent launches; incomplete attempts, live prior owners and unreaped
credentials refuse. Fresh password availability is required for every retry.
The fixed next boot output is `trial-launch-r2`, created only after successful
authentication. Original r1 failure files remain exact and are checked before
preparation. The original boot execution function and claim-consumption guards
are unchanged; no attempted boot may be retried.

The revised launcher passes 34 focused cases in 0.896 s. Display provenance and
monitor checks pass 22/19 cases in 0.436/1.698 s, and module/frame host checks pass
17/17 cases in 1.937/3.581 s. Their runtime function bodies are unchanged;
only the fixed launch path and dependency pins changed. The previous actual
20-second component test is inherited without rerunning it. Integrated qualified
frame reading passes in 0.017 s and read-only boot preparation in 0.207 s.
No password window, claim consumption, controller execution or display action
occurred in r70. Reuse the existing kernel, DT, modules, signed wrapper and A01.

Fresh authenticated phone health passes in 1.347 s at 23,516.93 s uptime: same
headless 05941 boot, restored old selection, boot-bound readiness and physical
guards. The user has not yet answered whether the previous password window was
visible/usable. Do not infer a password or keyboard diagnosis. On a fresh Ready,
start the prepared launcher immediately; do not reuse the r69 Ready. The future
physical display prompt still requires separate fresh availability after the
new OLED boot, full capture, module loading and frame preparation.

After-run review: the observed 300-second password wait had unnecessarily
entered the boot launcher, despite making no phone action. Separate bounded
authentication receipts now permit a later fresh password interaction without
clearing failed evidence or relaxing the boot claim. Tests cover contention,
incomplete/live/unreaped prior authentication, metadata tampering and changed
source before consumption. Initial integrated preparation refused because an
empty test stdout was listed as nonempty receipt evidence; the retained fix
removes only that direct empty-stream entry and records its empty hash. The
real qualification readers subsequently pass. No new kernel/display build or
unchanged long timer test was needed. Actual password usability remains unknown.

## r71: authentication passes; missing source RAM staging stops preflight

Latest r71, 2026-09-11: fresh Ready immediately launched the prepared OLED
session. **Authentication succeeded**, with no timeout or retained password.
The launcher consumed the exact OLED claim, then stopped at its first read-only
preflight. The controller is terminal **FAIL**; only `preflight` was entered,
no phase completed and no reboot, state exchange, exitrd change, RAM transfer or
partition flash occurred. Preserve `oled-live-driver-r1/trial-launch-r2` and
`oled-controller-r1/execution`. **The OLED claim is consumed and cannot be reused.**
The r70 Ready instruction is now historical; do not launch either old entry.

The exact cause is missing source RAM staging, not a USB link or password
failure. Authenticated SSH completed in 0.734 s, but the generated observer
raised `FileNotFoundError` for the expected `rog5-oled-05941-ba670e08…` namespace.
The controller correctly requires staged recovery helpers before preflight.
The host-only preparation and full-flow fixtures had not established that the
helpers were actually staged on the phone. Do not remove `verify_runtime()` or
weaken that predicate. The missing prerequisite belongs before live admission,
claim consumption and the request for Ready.

Independent authenticated health passes in 1.541 s at 23,822.95 s uptime on the
same headless 05941 boot, with the old healthy selection still restored. The
expected staging path is independently absent. Credential refresh stopped
cleanly; the controller and transport processes are gone. The user is released
and no password or physical-response prompt remains active.

A two-case regression replays the actual staging/observer functions with real
files in a uid0 user namespace: unstaged preflight refuses without mutations;
staging then preflight passes while selection and shutdown bytes remain exact,
and a second staging attempt refuses. Both pass in 0.065 s. Hardware telemetry,
unit state and tmpfs identity remain explicit fixtures; this is not phone staging.
All 64 executed source/evidence files are archived by `oled-preflight-failure-r1`.

The retained kernel warning/error log also contains a boot-time SPMI type read
failure on SID 5, address 0x104, at 0.143 s. The printed 0xcf08 is the arbiter
status offset, not the PMIC register address. PMIC probing returned -EIO; this
requires separate hardware/DT investigation and is not the cause of the missing
RAM directory. Pstore has no records. General health PASS is not a claim of a
warning-free or fully qualified kernel.

Next: prepare a separately reviewed successor experiment with the source RAM
staging step included. Run its exact read-only source/route preflight on the
actual phone and retain the boot/owner/files-bound receipt **before** admission,
claim consumption or requesting Ready. Preserve the consumed OLED profile and
all failed results. Reuse the compiled kernel/modules and passing component
checks wherever their inputs remain exact; determine the new experiment's
canonical claim/identity requirements before packaging or rebuilding anything.

After-run review: software checks and generic health were insufficient proof
of actual device preparation. Require the exact generated read-only preflight
after staging, before asking Ready or consuming a claim. The existing observer
already enforces the correct condition, so changing it to accept an unstaged
phone would hide the preparation failure. The initial diagnostic script suffix
assertion and regression fixture class lookup failed locally before any phone
query/test; corrected collection and the two-case replay are retained. No
expensive kernel build or full unchanged test suite was repeated.

## r72: actual source staging and preflight; reusable sudo terminal preparation

Latest r72, 2026-09-11: the missing preparation now **PASSes on the phone**.
The existing guarded source-staging function copied only its three exact helper/
custody files into a fresh root-owned RAM namespace in **1.323 s**. Owner is
`e7bb639c01a3ee395e7f6c98fd922bf5`; runtime path is
`/run/rog5-oled-05941-e7bb639c01a3ee395e7f6c98fd922bf5`.
No state exchange, shutdown replacement, reboot or partition write occurred.
Preserve the one-use staging result; do not restage this namespace.

The actual generated read-only source/route preflight then **PASSed in 3.011 s**,
authenticated on the same headless 05941 boot. It verifies RAM contents/custody,
original shutdown, absent OLED transaction, old healthy selection, physical
storage/power guards, installed V9/V11 files and the unchanged protected boot_b.
The script differs from the qualified reader only in the exact new owner,
receipt and custody hashes. Evidence is `oled-staged-experiment-r1`; the full
read-only preflight must be rechecked briefly before a future mutation.

The separate integration checkout `oled-staged-controller-worktree-r1` is now
`b0da65a7`. Its new experiment `oled-staged-source-05941-r1` binds the same exact
OLED artifact profile, manifest, trial ID, signed wrapper and A01 as the failed
attempt, with a separate one-use experiment identifier and an explicit staged-
source preparation requirement. Eleven admission tests pass (0.314 s runner),
and all 228 prior claim records remain byte-identical in the source registry.
The old consumed claim stays consumed. No new claim file was registered or
consumed on disk. Kernel, modules, payload, wrapper and A01 need no rebuild.
A new isolated live controller and admission binding remain to be integrated;
this source change alone does not authorize a boot.

The user asked to reuse sudo. A noninteractive check returned password-required
in 0.010 s, so the old authentication is not available to a new process. A live
persistent terminal is prepared: exec session 44286, shell PID/SID 251096,
start 2915076, pts/1, host boot e3393ab5-0cf9-43fd-8bcb-020cf78b1f1b.
Use the same controlling terminal for future sudo-capable launches and test two
child processes after the next fresh authentication. Cross-process reuse is
**not yet proven**. No sudo policy was changed or password window opened in r72.
Keep bounded credential refresh during active work; do not reuse a dead handle
or an old Ready. The next hardware session is not yet ready for the user.

After-run review: the missing prerequisite was fixed by executing the existing
guarded staging function, then its actual read-only observer. This required
1.323 + 3.011 s, not another kernel/package build. Separate experiment identity
from unchanged artifact identity so a corrected, separately reviewed host
experiment can retain existing artifact verification while preserving consumed
claims. Do not mistake source-registry additions for runtime boot admission.
The persistent terminal is intended to reduce repeated password prompts; record
actual reuse evidence after authentication before claiming it works.

## r73: staged-controller admission and actual source recheck

Latest r73, 2026-09-11: the new staged controller imports and validates its
32-file input lock. Preparation is now part of admission: the closed predecessor
and actual RAM staging must match; a fresh read-only route observation must
finish within 15 seconds before admission. Failed observation cannot consume a
boot claim. Its attempt/output remains exclusive. The old trial stays consumed.

**76 focused tests pass** (18 preparation, 32 launcher/credentials, 26 admission).
They exercise actual receipt validators, missing/stale/changed preparation,
process identity, cleanup and refusal before claim consumption. All **four full
flow fixtures pass in 25.574 s**, including source abort and early/late fallback.
Privilege, USB and boot boundaries are explicit fixtures, not hardware proof.
The first flow run found a derivative path to absent selector files; the reader
now uses the exact retained installed-selector inventory. No selector rebuild.

The new Q2 controller's exact generated observer is byte-identical to the r72
phone-tested script. Its actual authenticated recheck **PASSed in 2.883 s** on
boot `de90d177-3532-49e0-9bfd-8f8c65889a8d`. It verifies staged helpers, physical
guards, old healthy selection, original shutdown, no reboot intent, installed
V9/V11 files and unchanged boot_b. The host source is clean `b0da65a7`, digest
`9e8efaba23afb18d3c41649eb3700786db15fe68e44b8748de9eabe563f95725`.
Evidence: `oled-staged-experiment-r1/integration-result-r73.json` and
`source-preflight-recheck-r1`. This diagnostic is not live admission.

No password window, new claim registration/consumption, reboot or phone write
occurred. Privileged handoff qualification and module/frame provenance still
need integration before requesting Ready. New paths are
`oled-staged-live-driver-r1` and `oled-staged-controller-r1`; old executed source
and results are preserved. Keep the kernel, modules, payload, wrapper and A01.
The persistent sudo terminal remains available subject to a fresh identity check;
password reuse across child processes still awaits actual authentication.

## r74: privilege inheritance and new display qualification chain

Latest r74, 2026-09-11: the staged boot controller and downstream display
qualification chain now validate. Eleven privileged handoff boundary sources
match the actually tested predecessors with only exact path/digest substitutions.
The retained actual UID0 guardian / UID1000 handoff remains applicable; this is
scoped inheritance, not a new authentication or current credential proof.
Current process/admission wiring was separately replayed. Live qualification is
`aeb2809792c10bc31d85c304003a7ade78f32846316fb11f90a66de346ddabe6`.

The component monitor now reads only the new staged controller/launcher and Q2
source. Completed boot proof also verifies the original fresh source-preparation
receipt. Tests reject missing preparation and the consumed failed predecessor.
The module and frame coordinators follow this new qualification chain.
**109 additional cases pass**, including 24 provenance, 19 monitor-session,
17 module-host and 17 frame-host cases. The unchanged real 20-second frame timer
was inherited after verifying that frame logic changed only dependency hashes.
No kernel, payload, selector or framebuffer helper rebuild was needed.

Evidence is `oled-staged-experiment-r1/integration-result-r74.json`. Updated
qualification hashes: monitor `93548237db2e9f7a52bdd38049515e231165b5a31ae378ae1d2c6d7ed4055456`,
module `cef925a709308d54c1f544c2abc26e8e5c3c435b384bda706713e1ff32b51397`,
frame `1abda57152e28ec3ebb832ca6b9812626965b77760400837f974a3aa11fb18bf`.
Previous display sources/qualification records are retained under
`display-bindings-before-r1`. Old executed boot source/results remain untouched.

No phone action, password window, claim registration/consumption or reboot
occurred in r74. The last actual phone observation remains the r73 preflight.
Next: complete the fixed same-terminal launch entry and its two sudo reuse
checks, then prepare the exact separate pending claim. Only request fresh Ready
once the complete entry has been reviewed and can start immediately. Privileged
handoff and downstream display binding are no longer pending; current sudo
authorization and actual OLED hardware results are still unproven.

## r75: prepared terminal launch and pending claim

Latest r75, 2026-09-11: **fully prepared; waiting for fresh Ready** to unlock
sudo on the Deck. No old availability reply may start this session. The fixed
entry is `oled-staged-experiment-r1/terminal-launch.py`, SHA
`9f3f39063cfd6827de0fc8a2f99cdef540464bc981699c5bf2cd50f850494589`.
Run it through retained exec PTY **44286** with the command in
`oled-staged-experiment-r1/ready-preparation-r1.json`. Terminal ownership and
foreground/session checks passed from that actual terminal. Shell PID/SID is
251096, start 2915076, pts/1, host boot e3393ab5-0cf9-43fd-8bcb-020cf78b1f1b.

The entry performs the local touch askpass authentication, then two independent
noninteractive sudo validation children in the same controlling terminal, and
only then invokes the qualified trial with authentication disabled. Cached sudo
can satisfy the initial authentication without opening a window. No password
is stored and no sudo policy changes were made. Ten focused tests pass in
0.298 s (2.319 s runner): auth failure, either reuse failure, changed source,
foreign terminal, failed qualification, concurrent owner and reused entry all
refuse before starting another trial. Actual sudo reuse is still unproven.

The exact new claim `oled-staged-source-05941-r1` is registered **pending**, not
consumed: 1393 bytes, mode 0600, SHA
`03e8adafe37cef0a5f78e281cba5ce01df1f21e7a674431246013aa4ffade565`.
The old OLED claim remains consumed. No old record was reset or overwritten.
Full preparation passed in 0.271 s, and the final actual phone
preflight passed in 2.833 s on the same de90d177 headless boot,
with original shutdown, staged helpers, old healthy selection, installed
V9/V11 files and protected boot_b verified. No phone write or reboot occurred.

On fresh Ready, perform only brief terminal/pin checks, immediately dispatch the
prepared command and direct the user to the local password dialog. The user
need not wait beside the phone during the approximately 23-minute automatic
boot recording. Keep USB connected. Do not rerun the exclusive terminal entry
or boot claim after entry; inspect its retained result/owner. Runtime output:
`oled-staged-experiment-r1/terminal-launch-r1`; underlying trial:
`oled-staged-live-driver-r1/trial-launch-r1`, controller:
`oled-staged-controller-r1/execution`. Module/frame qualification is already
prepared; actual OLED boot proof must precede any hardware component run, and
an illuminated frame still requires separately fresh physical readiness.

## r76: PMR735B probe localization while awaiting Ready

Latest r76, 2026-09-11: **r75 remains fully prepared and waiting for fresh
Ready**. No password window or test was started on automatic continuation.
The retained terminal entry hash and pending exact claim were checked unchanged;
its execution directory is still absent. Use the r75 Ready instructions below.

Independent kernel diagnosis localized the boot warning: SID 5 is the declared
PMR735B, and its PMIC_TYPE (0x104) revision read returns -EIO before GPIO and
temperature-alarm children can be populated. Actual authenticated sysfs readback
in 0.363 s confirms PMICs 0-4 bound and SID 5 unbound on the same source boot.
The arbiter's printed 0xcf08 is a status offset. Neither chip absence nor a
specific firmware-access cause is proven. Compare the ASUS stock inventory
before changing this declaration; do not suppress the warning or probe registers.

The exact config also has `CONFIG_QCOM_SPMI_TEMP_ALARM=m`; the metadata query
reported no thermal-zone types beginning pm or battery. Module packaging/load
and alarm binding need a separate audit before claiming PMIC thermal coverage.
These are independent follow-ups, not a diagnosis of the missing staging files
or a change to the prepared OLED trial. Evidence:
`pmic-sid5-investigation-r1/result.json`. No phone writes, driver rebind, module
load, kernel build, claim consumption or reboot occurred.


## r77 — prepared OLED launch and early fallback (2026-09-11)

Fresh Ready immediately entered the prepared terminal wrapper. Local sudo
validation and two independent noninteractive children passed; the bounded
keeper continues to refresh credentials within the same controlling terminal.
No password was retained and no sudo policy changed. The staged-source claim
`oled-staged-source-05941-r1` is consumed and must not be retried.

Source preflight, exact state exchange, RAM exitrd setup, source reboot,
fastboot identity checks and one 128-MiB RAM transfer passed. Transfer completed
in 13.472 s; no partition was flashed. Target-stage observations for boot
`19141e40-a435-4317-ba8b-89cc55133984` reached switch-root PASS. The next four
startup observations showed P2 activating, state and identity inactive, then
an unsuccessful SSH-service query. Every journal query reported error and no
explicit helper failure was received. These are unauthenticated observations,
not target-health proof. USB disappeared 9.021 s after switch-root PASS.

Authenticated discovery 031 returned V11 release `7.1.4-g359318de534f`, bundle
`persistent-native-root-v11`, boot `ee0d166e-5e69-4db7-8bbd-6266352594ea`.
The controller correctly rejected that identity as the OLED target. Preserve
its FAIL outcome even if fallback restoration succeeds. The fixed full capture
and fallback-restoration sequence remain in progress at this interim entry.

Offline diagnosis preserved selected source files from the actual compressed
payload using bounded streaming reads, and enumerated the exact display DT
delta. The shipped startup observer matches the frozen source. Built-in
DRM/MSM/MDSS/DSI can probe enabled DT hardware before the separate panel module
is loaded. The 900-second emergency timer does not explain this early reset;
a panic or another reboot route remains unproven. A retained bounded reset-log
reader is prepared against the authenticated fallback boot and sealed BusyBox,
with shell syntax checked. It must wait for the current controller to close.
Evidence is in `oled-startup-failure-r1`; active controller evidence is in
`oled-staged-controller-r1/execution`. No panel/frame test was entered.


r77 terminal completion: the 23-minute capture reached its original deadline,
cleaned all owned host network state and reaped its root worker. Target trial
and capture remain FAIL. Automatic fallback staging failed with
`RAM parent metadata`; an authenticated read found root-owned tmpfs `/run`
mode 1777 and the staging namespace absent. The prior selection was still
pending. P2/state/identity/SSH services were active on current V11. Mounted
pstore had no records; no reset cause is proven. The exact OLED DT has no
ramoops node. The Deck had 9.6 GiB available RAM, almost all swap free and
46 GiB free disk, so the earlier host memory exhaustion was not present.

Separate recovery `oled-fallback-restoration-r1` preserved every existing
physical/storage/helper guard and relocated its fresh helper/custody namespace
under root-owned 0755 tmpfs `/run/initramfs`. It did not change `/run` mode.
Five ARM64 cases passed: real staging/restore, rejection of writable or linked
private parent, duplicate stage, and partial helper transfer. Their summed
case time was 5.645 s. Five coordinator fixtures passed in a 0.118 s runner,
including failure at every phase and refusal of a second execution. Initial
fixture preparation failures were retained: a guard-injection anchor differed
between stage and restore; moving mounted loader files could not construct the
symlink case. Corrected fixture setup reran only affected/remaining cases;
no production guard was bypassed in the phone run.

Actual recovery PASSed in **10.340 s**: authenticated preflight, RAM staging,
one guarded restoration exchange and final verification. Original healthy
selection `ed3a62d1...` and installed/protected files were verified on unchanged
V11 boot `ee0d166e-5e69-4db7-8bbd-6266352594ea`. Its legacy readiness marker lacks
an embedded boot ID; current authenticated identity is separately checked.
No reboot, flash, panel load or frame write occurred during this recovery.
Its owner is `40c18651355c8690fca8b8afe6b15283`; retain its terminal execution and
RAM/durable records. Original trial stays FAIL. Sudo noninteractive validation
also passed from retained PTY 44286 after the original launcher returned.

Next work is target startup diagnosis and better retained failure evidence,
then a separately qualified controller incorporating the proven private RAM
parent. Preserve existing builds; another kernel rebuild or repeated physical
test is not justified yet. No operator availability remains pending.


## r78 — bounded kernel startup evidence (2026-09-11)

An authenticated read-only journal inventory on V11 confirmed unchanged boot
`ee0d166e-5e69-4db7-8bbd-6266352594ea` and restored selection `ed3a62d1...`.
`systemd-journald` is running; the journal lists only the current boot. Archived
pstore has no files. Evidence is `oled-startup-diagnosis-r2`. The cause of the
OLED reset remains unknown; no new phone write, module operation or reboot ran.

Added a dependency-free Rust log relay and host decoder in isolated source
`9b6de57d57cf8f702353bd16fe67b7e5439cfa6d`. The relay uses nonblocking, read-only /dev/kmsg and UDP with fixed USB
addresses, 1–120 s duration, 8,192 read attempts, 1,024 record/gap events,
512 message bytes and 1,400 bytes per packet. It emits explicit gap, truncation
and terminal accounting. Packets remain unauthenticated diagnostics; the decoder
rejects changed boot/session identity, malformed framing, reordering and impossible
counts. No boot authority or automatic service installation was added.

Ten Rust tests plus formatting/Clippy passed; eight Python decoder tests passed.
The static ARM64 PIE has no interpreter or required dynamic libraries and its
invalid-input entry was checked under QEMU. Full build/check used Rust 1.98 in
the retained no-network builder with 512 MiB and one CPU, taking **2.810 s**.
An ARM64-only independent build took **1.166 s** and produced identical bytes:
`b1be78b8c1c1592d750efef315a5a5818f6706bd4b1d9c10cb36b42216272851`,
1,497,160 bytes. Both containers exited and were removed without OOM. Evidence:
`kernel-log-relay-r1/qualification-r1.json`. These are software/ABI observations,
not a live phone relay or a successful OLED boot.

Initial preparation caught a Path/string mount construction error before a
container ran; Clippy caught a redundant priority comparison. A decoder-test
helper also needed distinct parameter names to inject malformed index/event
fields. Failures were retained and corrected. Reused the known static-PIE
linker and builder; no kernel/module rebuild or repeated full integration CI.
The independent twin repeated only ARM64 compilation.

The active USB firewall zone has a final reject rule. Live UDP observation
needs an owned temporary 8085 allowance and cleanup. Cached sudo has expired;
`sudo -n -v` failed without opening a dialog. No Ready was requested because the
full receiver/privilege entry is not yet prepared. Continue independent startup
integration work; preserve the current V11 source and the r77 recovery records.


## r79 — passive relay prepared before operator availability

The new Ready arrived with an unfinished launcher; the user was released before
independent preparation continued. Authenticated full V11 health/recovery checks
passed in 5.077 s. Exact relay staging plus verification passed in 1.320 s in a
fresh protected RAM namespace. No relay execution or authentication occurred.
The binary remains SHA b1be78b8c1c1592d750efef315a5a5818f6706bd4b1d9c10cb36b42216272851.

Receiver/decoder: 14 checks passed. Coordinator/payload: nine checks passed.
Fault fixtures cover SSH loss with cleanup, failed authentication before phone
work, pre-existing rules, ambiguous add without false ownership, incomplete
cleanup, mismatched SSH/UDP summaries, and one-use refusal. Generated shell syntax
and decoded payload hash match. Retained terminal identity, askpass identity,
USB zone, absent rule and capture port were checked before requesting Ready.
Evidence is `kernel-log-relay-live-r1/preparation-r1` and `review.json`.
The receiver source commit is `5f404597`; frozen kernel and executed controllers
were not changed. The prepared run is five seconds, with independent eight-second
phone timeout, twenty-second receiver deadline and forty-five-second firewall
expiry. Live transport and subsequent startup integration remain unqualified.

After-run review: preparation work, rather than compilation, caused this Ready
handoff delay. Apply the Ready gate to the whole launcher and its cleanup, not
only its binary. The final receipt now pins scripts/tests/staging and records the
exact terminal entry, so the next fresh Ready requires only brief identity checks
and runtime arming. No expensive kernel rebuild was repeated.


## r80 — optional startup relay integration, offline only

While waiting for fresh Ready, added optional relay pairing to the standalone
builder and init runtime in a separate source checkout, commit `8b20fbb3`.
Absent by default; enabling requires an exact binary digest and fresh nonce.
A base already containing relay/config input is rejected. Runtime verifies
ownership, modes, size and hash, stages to a fresh private RAM directory, and
creates an independent sysinit service with 120/125/2-second run/runtime/stop
limits. The composition checker validates both archive members, propagates the
selected kernel release and includes the new unit in verification.

Five new assembly/runtime tests, two standalone composition tests, 57 rescue
composition tests and eight existing startup observer tests pass. Host
systemd-analyze validates the rendered optional unit; no service is started.
Actual ARM64 bytes were assembled twice into explicitly nonbootable fixtures
with identical SHA `0a454ac4d1b32c53029b1ddc0566197f281b5c9d845e48191c3a279e1a8708ad`
and size 688,573 bytes, in 0.229 and 0.222 s. Evidence is
`kernel-relay-startup-r1/qualification.json` and `assembly.json`.
No live relay, exact Arch-root execution, startup packet collector integration,
bootable image or OLED hardware qualification is claimed.

Tests caught an inherited-payload guard relying on set -e across an AND list;
explicit failure now rejects it. The composition driver also needed the selected
release rather than an unset variable. Two older tests now use rendered init
fixtures for this stricter binding. Initial sparse checkout omitted helper and
boot-unpacker dependencies; selected tracked inputs and the exact pinned retained
unpacker were restored without downloading or rebuilding. Final 57-test log is
`kernel-relay-composition-tests-final-r80.log`.

After-run review: no kernel build was needed. Use sparse source checkouts before
materializing historical artifacts; include the selected test dependencies.
Repeat only tests affected by discovered failures. The r79 probe remains pinned,
unexecuted and ready for immediate launch after fresh Ready. No authentication
or phone action occurred during this automatic continuation.
