# ROG Phone 5 Linux Development Lessons

Status: active prevention guide  
Audit source: main Codex chat and its recorded project results through 2026-08-20 04:14 UTC  
Intended repository location: `docs/development-lessons.md`

## Why this file exists

The project has made real low-level progress, but several expensive live-device cycles were lost to repeatable integration and process defects rather than new kernel or hardware limitations. This file records those patterns and converts them into lightweight rules.

Use the relevant R1–R10 sections for routine work; read the complete pre-build
and pre-live checklists before creating a successor or executing a phone cycle.
Update only when a failure reveals a reusable lesson. Current state and task
authorization take precedence over historical operating assumptions here.

## Executive finding

Yes, the project has repeated the same classes of mistakes.

The dominant avoidable costs were:

1. The same candidate identity was duplicated across many allowlists, tests, profiles, and hand-maintained hash pins.
2. Offline tests validated source components but sometimes did not validate the exact installed composition and mutable host state used by the live cycle.
3. Recovery and fallback capabilities were assumed instead of derived from the exact booted artifact.
4. Parent and child timeouts were changed independently.
5. Device model, firmware generation, slot, and boot-chain coherence were occasionally treated as separate facts.
6. Live phone cycles were used to discover host parser, path-normalization, or environment-state bugs.

The correct response is not to remove the protections that prevent wrong-device writes or loss of recovery. The faster path is to keep a small set of critical guards and eliminate duplicated policy, manual identity propagation, stale host state, and tests that do not replay real observations.

## Failure classes and prevention rules

Mobile snapshot, 2026-09-12: use the supplier's actual trust model. Arch Linux
ARM signs packages, not repository databases; retain TLS snapshot identities
and require signed package metadata rather than waiting for unavailable database
signatures. libalpm print-only preparation independently checked the exact
selected set. Include the ARM keyring explicitly. Read both desc and depends
records even for a single added package: the initial keyring-only extraction
omitted pacman and was correctly rejected before publication. Preserve unselected
malformed records and distinguish direct signer allowlists from master-key
owner-trust files. Reusing 15 identical cached archives avoided downloads; 315
complete signature/metadata checks took about 28 seconds. Keep large archives
outside Git and preserve the old graph as evidence rather than editing its pins.

Mobile archive audit, 2026-09-12: cache filenames and a resolved graph do not
prove package identity or closure. Fourteen exact pins authenticated; a newer
Mesa archive remained outside the graph. Compare signed `.PKGINFO` as well as
hashes, and declare verifier tools in CI. Exercise cancellation before freezing
for expensive qualification: a short SIGTERM check found an owned-child leak
after the first CI run had started, costing a 329.738-second interrupted run.
The correction defers signals across child ownership/cleanup and verifies
SIGTERM/SIGINT reaping. Eighteen focused checks took 1.657 seconds; final archive
verification took about four seconds. Keep these checks before full CI and
reuse unchanged board/target artifacts.

Offline review, 2026-09-12: distinguish the persistent acceptance linearization
point from a success message or RAM file alone. Test the real state helper across
publication/syscall failures and timer races, including the actual automatically
created probe timer. Timer cancellation itself can remove recovery protection.
Keep current-boot acceptance fresh and fence rejected commits before another
primary selection.

Compile extracted actual driver callbacks against exact DRM behavior before
hardware tests. Vendor byte order needs tracing through every transform: ASUS
inverted-DBV handling made its low-byte-first helper emit high byte first on the
wire. Regenerate only patch headers/statistics, never globally replace line-count
numbers in patch payloads. The new binding identity check caught a description
corruption before publication; driver resolution bytes were unchanged.

Keep process exit failure stronger than textual SKIP/BLOCKED output. Reserve a
test leader PID until group cleanup and defer repeated interrupts during cleanup.
The reporter review reproduced both masked exit42 and interrupted reaping.
A JSON failure count is insufficient if summary/cleanup returns success: the
summary exit status must propagate through the actual shell cleanup. Validate
physical receipt scope and aggregate status as well as hashes and row IDs.
Prepare schema dependencies with a Python installation that includes headers:
the host Python lacked Python.h; a separate bundled-Python environment succeeded.
Archive extraction is a measurable build cost; reuse only a verified immutable
base archive, while preserving source/input drift refusal.

IOMMU r137: isolated flow tests must relocate subprocess scratch as well as
receipt outputs. Fastboot metadata checks also see the namespace mount root;
verify the real host path separately, and substitute that boundary in every
loaded fixture copy. Keep those changes out of production. Resolve inventory
pins through declared PATHS/symbolic dependencies instead of assuming every key
is a state-relative filename. Hash stability excludes access time, not mtime or
ctime.129 final inputs and the19-file session cohort validated in0.133 s.80 final
launcher/admission/full-flow/handoff checks passed; select only new handoff cases
rather than inheriting and rerunning unrelated suites. Next live entry must keep
authentication, both root probes and launch in the same parent/session so one
password entry can be reused without storing it. Do not claim that entry exists
yet or ask for user presence before it is prepared.

IOMMU r136: compose cleanup by the last dispatched hardware phase. A lost
display result must never inherit provider-only cleanup. Demonstrate that refusal
before changing classification. Budget logger closure as well as action time;
reserve recovery after the entire combined session, not only at session entry.
The final500-second session requires2300 seconds at admission and330 seconds
before starting its300-second logger.31 coordinator tests and10 logger tests pass.
Avoid duplicated expensive input checks where the same immutable closure is
already revalidated by admission on every lease check; retain initial cohort
membership and exact input SHA. ARM64 test runtime extraction should follow
actually imported extensions: scanning all optional Python extensions reached
uninstalled Tk although every required graphics-test import worked.81 ARM64
fixture cases pass. Apply the installed systematic-debugging skill: locate the
failing boundary, establish a regression, make a scoped fix and verify it. These
results qualify software paths, not real GPU DMA, scanout or acceleration.

IOMMU r135: replace historical fixed-boot provider receipts with a protected
same-owner, same-boot handoff when composing successive hardware phases. Reject
stale/incomplete handoffs and reobserve IOMMU attachment immediately before each
subsequent operation; a previously successful provider is insufficient if its
GPU group disappears. The113 focused cases passed on their first attempts after
staging fixtures and using each suite's correct namespace. Check combined timing
before wrapping independently qualified components: the old single-phase logger
caps duration at180 seconds, and the new target handoff expires after180 seconds.
The combined coordinator must bind the display's provider-result hash to its own
successful provider transport result and explicitly budget both phases, health
reads and logger closure. Module and kernel rebuilds were unnecessary.

IOMMU r134: driver binding alone did not prove GPU IOMMU attachment on the
previous phone run. Check both GPU and GMU group links, reciprocal membership
and exact DT streams before display/query; keep this proof separate from actual
DMA/acceleration. New input pins come from the qualified archive and selected DT,
not the old module inventory.37 provider tests include the observed missing-GPU-
group failure; supervised transport and proof checks bring the total to101.
Unittest discovery skipped hyphenated filenames entirely; explicit module loading
now enforces exact counts. Backend fixture files must be root-owned in a user
namespace; an ordinary-host invocation failed before READY. Carry namespace
requirements alongside test commands and verify counts before interpreting PASS.

IOMMU r133: qualify the final test file after broad fixture substitutions. An
r131 replacement intended for engine coverage silently broke a non-engine test
after its initial pass; rerunning only engine cases missed it. The prior claim
of unchanged remaining cases is superseded by the corrected full 39-case run
(5.297 s). Inspect the final diff and discover the complete affected test class.
Stage all referenced child fixtures before bridge tests; missing guardian-fixture
caused six early failures. Correct integration fixtures using actual command
receipts and phase intents; the combined 51-case policy suite passed in 8.268 s.
These were harness defects: no kernel rebuild or repeated ARM64 qualification
was justified. Preserve failed evidence and distinguish fixture privilege from
an actual root handoff. Prefer bounded sudo authorization reuse; never store the
user password in scripts or evidence. A persistent helper needs a root-owned
code/dependency boundary, not a passwordless rule for user-writable launchers.

### R1. Duplicated candidate identity and policy

IOMMU r132: read the current profile through its real loader when adapting a
consumer. The new profile uses kernel_refresh; gpu_preservation belongs to the
older GPU profile. The loader returns immutable MappingProxyType recursively,
so a mutable-dict check also rejected valid input. Both failed attempts stayed
offline. The corrected boot binding checks the exact immutable relay contract
against the capture producer before attempt intent or snapshot; two refusal
cases and the existing boot suite pass (21 cases,3.481 s). Full admission should
call that same check before consuming the trial. Preserve the frozen mapping
contract instead of adding broad schema fallbacks.

Observed pattern:

- A new recovery profile was added to the host packager/verifier but omitted from the sealed recovery fetcher and control-process allowlists.
- The power-observer candidate booted through NCM, NFS, systemd, and SSH, but the runtime collector omitted its candidate ID.
- A later build caught another stale recovery bundle allowlist.
- Tests repeatedly assumed exactly two allowed candidates or two allow rows after a third candidate was added.
- Artifact, compatibility, retention, source, helper, and executor hashes repeatedly became stale one link at a time.

Cost:

- Valid live candidates were consumed by metadata or policy defects.
- Multiple full CI runs were needed to discover a hand-maintained identity chain sequentially.
- Kernel-level success was obscured by post-boot acceptance failures.

Prevention:

- Define every candidate once in one canonical machine-readable manifest.
- Generate runtime allowlists, recovery allowlists, admission rows, and tests from that manifest.
- Replace literal candidate counts with set equality against the canonical manifest.
- Replace scattered literal hash pins with one generated lockfile and one deterministic refresh command.
- CI must fail if regenerating policy or pins produces a diff.
- Before an expensive wrapper build, run a dependency-closure test that searches every consumer for the new candidate ID and rejects both missing and obsolete IDs.

Rule: **No candidate name, profile, claim state, or artifact hash may require manual propagation to more than one source file.**

### R2. Source validation did not always prove deployed composition

IOMMU r131: after moving or appending test methods, inspect unittest discovery
before relying on a green result. Six recovery methods were accidentally outside
a TestCase; review caught this before execution. The corrected six and three new
controller-to-action recovery cases all passed. Final discovery records25 basic,
8 engine and6 target cases. Use the current source record in migrated fixtures:
the older OLED record correctly failed the new preflight hash guard in4.286 s.
Correcting the fixture, without weakening the guard, yielded21 ARM64 action cases
in350.543 s. Keep completed emulation replies for fast host callback testing;
rerun only affected integration cases after changing their fixtures.

OLED r60: qualify evidence against the reader's actual metadata contract before
creating the canonical record: mode0600, nonempty and at most1MiB per file. Retain
larger bytes in ordered pinned chunks, normalize copies without changing original
evidence, and represent empty streams explicitly. Check repository-owned claim
registration before treating software qualification as executable admission.
Complete registry/source/pin changes before final-source replays; retain older
qualified evidence with its actual source instead of relabeling it.

OLED r59: reuse the pinned monitor engine with independent explicit boot/output
contexts, retaining process/peer/socket and permanent-failure guards. Pin the
new launch script as well as inherited modules; otherwise a live guard can miss
a changed entry point. Reject nonempty output before core server allocation.
Transport liveness is not target health: production admission, capture closure
and final health/blanking need their own validated bindings, never fixture callbacks.

OLED r58: normal health admission and zero-brightness cleanup need distinct
ownership checks. Failure of normal work must still reach independently authorized
blanking after entry. Queue physical prompts without blocking for a response and
recheck time after callbacks; a pre-callback time check alone permits a late
prompt. Keep one real-clock production-duration test alongside fast virtual-clock
failure cases. Sysfs fixtures must return canonical newline-terminated values
even when simulating partial write results; ordinary-file formatting errors can
otherwise masquerade as cleanup failures. Neither stored zero nor a timed fixture
proves physical darkness or a hard bound on stuck device operations.

OLED r57: preserve partial-write evidence even if descriptor cleanup fails.
Track acknowledged bytes separately from a syscall whose result is uncertain;
never continue a short write or retry an entered frame. Check the exact sealed
frame against a fresh device capture, then retain zero brightness and renewed
boot/node/layout/admission checks during both chunked writes and memory readback.
Positioned I/O and readback support come from the exact kernel source; neither
readback nor a between-syscall deadline proves visible scanout or bounds a stuck
kernel call. Keep the enclosing worker deadline and final hardware observation.

OLED r56: bind rendered output to the entire captured boot/node/layout record
and execute a sealed copy of the pinned helper, so later source-path replacement
cannot change the frame. Stream bounded output into a sealed descriptor; verify
exact length before release. Exercise child cleanup after closed pipes, pidfd
failure and output/sealing errors using actual processes and FD inventories.
The existing ARM64 renderer needed no rebuild (0.021/0.122 s describe/render
under QEMU); keep this small reusable step separate from kernel packaging.
Actual touch authentication and both root handoffs passed on the next Ready in
13.378 s. The prior timeout does not establish a persistent keyboard defect;
retain that FAIL without speculative authentication code changes.

OLED r55: distinguish an authentication timeout from a demonstrated keyboard or
password failure. Window-tree evidence proves creation only. Keep the existing
bounded cleanup, verify dialog/probe disappearance, preserve the terminal
attempt and prepare the next unique output before requesting another Ready.
Reuse unchanged passing tests and pins; do not reopen a prompt on expired
availability or change working authentication code without failure evidence.

OLED r54: a read-only framebuffer open is still a driver operation. Gate it on
the admitted blanked display state, not merely a matching filename. Verify an
O_PATH handle's character-device identity before reopening that owned inode;
compare device/boot/brightness and two GET-only layout samples before accepting
a capture. Test descriptor closure on every branch, including actual ENOTTY and
node replacement. Do not label an ioctl fixture or raw capture as physical
layout/scanout qualification; pass its record through the separate exact decoder.

OLED r53: independently compile framebuffer structure offsets against target C
headers before releasing an ARM64 decoder. Tests built from the same hand-written
offsets missed vmode/rotate errors; the C assertions caught them. Emit actual C
records and feed them through the real ARM64 parser, with independent interlace
and rotation refusals. Read current DRM source for valid XRGB alpha conventions.
The known missing fmt/Clippy tools recurred once; their exact 1.98.0 components
are now staged from the retained pinned manifest in `rust-tools-r1`. Reuse this
read-only overlay with the unchanged compiler image and explicit compiler sysroot.

OLED r52: blank the verified backlight before waiting for unrelated framebuffer
qualification. The panel registers default brightness 1023, so a later fb0/mode
failure must not suppress the available zero-brightness action. Keep exact
endpoint/boot/authorization checks and propagate failed/short writes. The driver
has no hardware brightness reader: zero sysfs readback confirms the stored
request, not physical darkness. Report those scopes separately and retain the
full-health and human visual checks. Filesystem fixtures must explicitly emulate
the sysfs store callback rather than treat an ordinary file write as hardware.

OLED r50: a clean Git checkout can still lack required ignored inputs. The first
A01 run spent 23.970 s before discovering missing Android boot tools. Stage only
the five pinned tools/template files after verifying their frozen-source hashes;
check them before scanning large roots. Do not copy cache trees. The prepared
rerun passed in 81.851 s without kernel/package rebuild. Preserve executable
modes as well as bytes: the copied touch askpass needed 0700, verified before
any authentication attempt. A later adapter-only commit must retain the actual
A01 verifier revision; record its narrow source delta instead of claiming the
older proof was produced by the newer commit.

Post-trial regression lesson (r44): retained execution directories and consumed
global claims are normal host state after a physical trial. Import-only assembly
tests should verify that this state stays unchanged; prerequisite tests should
use isolated output paths and explicit claim-boundary fixtures. Keep a separate
actual check that the consumed production launcher refuses reuse. Removing old
evidence or weakening one-use guards is not a test fix. The initially partial
output-path substitution tripped component agreement; preserving the real
read-only assembly paths avoided that unnecessary fixture complexity.

For an unchanged-kernel hardware trial, separate identity changes from module
rebuilds. R46 reused the physically observed 05941 payload and exact display DT;
streaming composition changed only descriptor/catalog and proved preservation
of the other 722 members. Twins took 9.502 s total with 512-MiB/no-swap bounds;
no kernel, module, depmod or root-image rebuild was necessary. Reuse the current
successful packager as the adaptation base, not the older display-specific
recipe with stale kernel/source identities. A fresh identity still needs exact
new-wrapper and hardware admission; preservation alone does not grant it.

Recovery after a controller error need not reboot a healthy target. In r45,
a separate exact-boot wrapper reused the proven atomic helper and old custody,
checked quiescent writers, and restored selection in 7.656 s with final health.
Keep the original trial failed and use an explicitly different health predicate
for the restored selection; never substitute observation bytes or erase consumed
entries. Offline fixture tampering must make its own read-only file writable
before changing it. Preserve partial test evidence and resume only untested
cases when production source is unchanged; r45 retained seven passing cases
and ran the remaining ten after that fixture fix.

When an adapter return-shape bug is found, inspect sibling consumers. Both route
workers expected three values from the real two-value network adapter; mocks
hid one defect by returning the same incorrect shape. Exercise the real adapter
and replace only its external subprocess result. The corrected SSH-worker suite
passes 13 cases in 0.405 s; full affected integration passes 63 in 53.078 s.
Archive executed sources before integration and keep old qualification historical.

Observed pattern:

- A normal systemd/SSH profile was paired with a diagnostic reporter-bearing initramfs; the verifier correctly rejected the composition late in the build.
- The live bundle store still exposed an old charging-rescue payload.
- The bundle store was a read-only bind mount, so replacing files did not change the served source.
- The fallback NetworkManager profile retained `autoconnect=no` from an earlier repair period.
- Installed target-side gates did not initially contain a profile already accepted by host tooling.
- A storage manifest declared a 900-second recovery timeout, but the exact
  repacked boot image still carried the generic wrapper's 300-second cmdline;
  sealed init rejected it before USB enumeration.

Cost:

- Builds and live preflights operated on stale or incoherent installed state even when repository source was correct.

Prevention:

- Admission must inspect the exact served bundle, installed controller, initramfs contents, and wrapper bytes—not repository source alone.
- Record a single deployment receipt containing hashes for the wrapper, bundle, manifest, trust key, controller, network profile, and bind-mount source.
- Connected preflight must compare that receipt with the currently installed and served bytes.
- Candidate assembly must be atomic: build in a fresh directory, verify, then switch one pointer/bind source.
- Parse the exact final boot image and compare its cmdline, embedded ramdisk,
  kernel, and AVB descriptor against the candidate manifest before admission.

Rule: **The object admitted for a phone cycle is the installed byte composition, never merely the Git commit that was intended to produce it.**

### R3. Exact recovery capabilities were assumed

Observed pattern:

- Alpine lacked `findmnt`; a pre-transfer check failed on the live fallback.
- The Alpine fallback kernel lacked `CONFIG_KEXEC`; `kexec_load` returned `ENOSYS` after transfer.
- BusyBox rejected shell syntax that worked on the host.
- A killed recovery watchdog remained as an inert zombie while PID 1 waited
  for the storage executor; a host fixture had incorrectly assumed `/proc/PID`
  must disappear immediately.
- Recovery created its armed marker before setting `umask 077`; normal init
  umask produced mode 0644 while the sealed disarm helper required 0600.
- The storage executor collapsed every sealed watchdog-helper predicate into
  one generic S32 reason, allowing multiple live cycles to remain
  non-discriminating even when fallback worked.
- The host watchdog fixture depended on procfs `children`, but the exact ASUS
  wrapper had `CONFIG_PROC_CHILDREN` disabled.
- Tools such as `/usr/bin/time` and command options such as `cmp -r` were assumed to exist on the build host.
- BusyBox `modinfo` required `/lib/modules/$(uname -r)/modules.dep` even for an
  explicit `.ko` pathname. QEMU user emulation passed only because it could see
  the host's module index; the sealed phone initramfs could not. Test exact
  applets with the target filesystem namespace, not only the target binary.
- A reduced module-build kit kept headers and scripts but omitted
  `tools/bpf/resolve_btfids/resolve_btfids`; compilation succeeded and final BTF
  processing failed. Validate the finalizer before compiling, and retain it
  with the exact vmlinux/header kit.
- ACM tooling required a canonical sysfs location while a short USB path was supplied.
- A fixed `restart2("bootloader")` helper rebooted mainline, but the PMK8350
  SDAM and NVMEM reboot-mode drivers were modules absent from the sealed
  initramfs, so Linux could not persist the bootloader reason.

Cost:

- Live cycles and build attempts were spent discovering basic capability mismatches.

Prevention:

- Generate a capability manifest from each exact fallback/recovery artifact: kernel config, syscalls, binaries, BusyBox applets, accepted command options, filesystems, and device paths.
- Test scripts against the extracted exact initramfs/rootfs with its shell and utilities.
- Use POSIX/BusyBox-compatible commands in recovery unless a packaged binary is explicitly verified.
- Preflight every required capability before transfer or candidate consumption.
- A reboot command is usable only when the exact target proves its underlying
  reboot-mode provider is bound before any failure that may invoke it.
- Create every helper-owned marker under its required umask before spawning
  the process that publishes or consumes its identity.
- Propagate bounded machine classifications from sealed helpers instead of
  replacing them with a generic stage failure.
- Do not require optional procfs entries when PID, start time, parent, stopped
  state, and a root-owned lease already prove the process being terminated.

Rule: **A capability is available only if the exact booted artifact proves it; host availability and prior recovery versions do not count.**

### R4. Timeout budgets were not maintained as a lattice

OLED r68: files used as cross-process signals must be published complete. A
blocked-writer replay proved the shared exclusive writer exposed the destination
before its bytes existed. The frame host now fsyncs a private temporary and uses
atomic rename-no-replace; both visibility and no-overwrite regressions pass.
Do not attribute an earlier lost Ready to that race without its missing thread
error: the earlier55s test stopped while waiting, unlit, and its cause is unproven.
Surface fixture thread failures promptly and stop leases rather than waiting out
the entire availability window. Reuse the completed20s result for unchanged timer/
RPC function bodies; validate the changed publication path with focused cases.

OLED r67: separate acknowledged zero-state capture/render from the one-use frame
write. Availability can expire after preparation without a frame ever being
shown. A real process/RPC test proves no Ready leaves brightness zero and no
frame-write entry, while independent cleanup/reap still runs. New preparation
requires verified cleanup and fresh health; never clear an actual write entry.
Leases maintain ownership but cannot extend preparation, Ready or active deadlines.
Reuse the qualified framing/fork/reap/zero worker rather than creating another
transport family. The14 lifecycle plus6 exact-file checks passed first time,
using the already-correct private namespace setup and mode755 parent.

OLED r66: a monitor accepting cleanup does not mean monitoring passed. The actual
client returns a finished reply even when failure is latched. A negative assembled
replay reproduced an incorrect coordinator PASS; require the nonfailed reply,
zero monitor exit and matching durable FINISHED result. All17 integration cases
then passed in1.941s. Keep transport input closure separate from force-killing SSH
so the independent target cleanup can still report its outcome. Make namespace
fixtures match real parent permissions: tmpfs defaults can create a world-writable
`/run`, which the production staging guard correctly rejects.

OLED r65: test the outer deadline with real blocked workers and pipes, while
keeping phone effects explicit fixtures. Reaping the direct child alone does not
prove its helper group is gone; retain both checks. Failed zero cleanup must keep
its own process/reap evidence, and cannot become PASS just because the action
worker closed. The 22-case supervision suite passed in 4.009 s. Capture the host
mount namespace before entering a user namespace; host PID1 namespace reads can
be permission-denied there. After that fixture-only failure, rerun just the six
root-file checks (0.008 s), preserving the already-passing process suite. Avoid
reopening human availability while the remote transport is still unprepared.

Observed pattern:

- A 180-second outer recovery rollback could not contain a 260-second fetch path plus margin.
- A 320-second controller deadline could not contain 260 seconds of prepare, 90 seconds of cold-NFS readiness, and cleanup margin.
- An independent watcher expired shortly before target SSH became available.
- Timeout changes caused stale expectations in observer and lifecycle fixtures.

Cost:

- Recoveries rolled back while valid transfers or verification were still running.
- Evidence collectors stopped just before the event they existed to observe.

Prevention:

- Keep every timeout in one timing-budget file.
- Derive parent deadlines from child deadlines and an explicit cleanup/USB-enumeration margin.
- Add assertions such as `outer >= prepare + readiness + cleanup_margin`.
- Use measured p95 or worst observed durations from retained traces, not guesses.
- A live sampler should outlive the lifecycle controller and rollback window.

Rule: **No timeout literal may be changed outside the central timing budget.**

### R5. Device, firmware, slot, and boot-chain identity were not always treated atomically

Observed pattern:

- Firmware `18.1220.2202.206` was later identified as ROG Phone 5S firmware while the target is a ZS673KS ROG Phone 5.
- Slot A was assumed to be a usable stock rescue, but its `boot_a` and `vendor_boot_a` came from different firmware generations.
- A lifecycle still assumed a persistent Alpine slot-B fallback after restoration changed the actual fallback topology.
- A rehearsal initially selected a 32 MiB auxiliary UFS LUN instead of the 236 GiB userdata LUN; the resolver rejected it before a live write.

Cost:

- Charging and rollback hypotheses were built around invalid boot chains.
- Obsolete fallback assumptions created physical recovery work.

Prevention:

- Maintain one golden device manifest containing serial, USB topology, product, commercial model, SKU, board/SoC, storage LUN GUIDs, active slot, and hashes/build IDs for every boot-chain partition.
- Validate boot, vendor_boot, DTBO, vbmeta, and relevant vendor partitions as one compatible set.
- Recompute the fallback topology after every restore or slot operation.
- Never infer firmware compatibility from filename, slot label, or Android version alone.

Rule: **“Stock slot A” is not an identity. A complete, mutually compatible boot-chain manifest is an identity.**

### R6. Mutable host state repeatedly leaked between cycles

Observed pattern:

- `/var` ran out of space during staging or bundle rotation more than once.
- Global AArch64 binfmt state became stale or conflicted with the sealed private builder.
- TCP 8081 retained an old listener.
- NetworkManager autoconnect and firewalld zone state persisted from earlier work.
- The bundle path retained a read-only bind mount to an old payload.
- An obsolete network profile could claim recovery NCM.
- A source shell file was edited while its long-running build was reading it, producing inconsistent line offsets and an unbound variable.

Cost:

- Clean source produced non-clean execution because the host was not in a known state.
- Long builds and one-use cycles were restarted for environmental reasons.

Prevention:

- Add one idempotent `host-doctor` command that reports disk/inode headroom, bind sources, listeners, binfmt state, NetworkManager profiles, firewalld output, route state, compiler/container identity, and active build processes.
- Add one reversible `host-reset-for-cycle` command that changes only project-owned state and produces a before/after receipt.
- Require sufficient free space before build and deployment, including temporary twin-build peak usage.
- Budget BTF/link memory as well as compiler memory. A 3 GiB container killed
  pahole on the combined server kernel; the retained 6 GiB build allowance
  completed it. Preserve the memcg evidence and resume only exact-state objects;
  do not disable BTF or change kernel configuration to hide a host OOM.
- Build from an immutable source snapshot. Never edit files used by an active build.
- Keep each candidate in a fresh output directory and never reuse partial outputs.

Rule: **A live cycle starts from a declared host-state receipt, and an expensive build reads an immutable source snapshot.**

### R7. Live cycles discovered host-only parser and normalization bugs

Observed pattern:

- ADB exposed a short USB key while the lifecycle compared it to a canonical full sysfs path.
- Firewalld returned canonical text `no zone`, but the parser treated the embedded space as a malformed zone.
- The target correctly reported `root=local-ext4-overlay-tmpfs`, while the host expected only `root=overlay-tmpfs`.
- The runtime collector rejected a valid new candidate name after target SSH was already working.
- A module-level preflight list replaced the `gate_events()` callback in an
  assembled controller. Fragment-only tests omitted that shared namespace.
- A storage collector attached after the target had already started raw GPT streaming, so binary payload bytes were parsed as an overlong framed line before ACK.
- Sending host readiness immediately after ACM open raced target initialization and produced an exact target-side readiness mismatch.
- The mismatch persisted after target-S30 ordering, while the exact sealed AArch64 BusyBox/PTY exchange passed, isolating physical gadget-ACM input behavior from shell semantics.

Cost:

- v1, v2, and v3 power-observer wrappers were consumed or abandoned for host-control defects rather than kernel defects.

Prevention:

- Preserve real command outputs and lifecycle transcripts as sanitized regression fixtures.
- Replay every parser, path normalizer, and state transition against those fixtures before a new wrapper is issued.
- Check bindings in the complete assembled controller, and execute callback
  tests with the actual preflight bindings in the same namespace. Isolated
  function tests alone do not prove that the assembled program can call them.
- Test canonical, short, missing, whitespace-containing, delayed, duplicated, and stale forms.
- Run the whole controller with fake fastboot/ADB/NCM/firewalld/NetworkManager endpoints through PREPARE, COMMIT, target SSH, and fallback.
- For mixed framed/binary transports, require an exact operation-bound host-ready record before the target emits the first binary byte.
- Order the rendezvous in both directions: parse the exact target-ready stage before sending host-ready.
- When physical ACM still disagrees with PTY, tolerate only a bounded number of pre-token records and emit finite non-secret mismatch categories; never normalize the accepted token without evidence.
- When the exact token is proven as a suffix behind stale leading bytes, send one empty separator record before it; consume contamination as a separate bounded record instead of stripping token bytes.

Rule: **A new phone-observed string or state transition must become a replay fixture before the successor candidate is built.**

### R8. Rollback and COMMIT semantics were occasionally over-assumed

Observed pattern:

- After COMMIT returned `CLAIMED`, STATUS timed out and the outcome was unknown.
- A userspace rollback timer did not restore the phone after the control plane froze.
- Review later clarified that successful kexec destroys the old userspace timer, so absence of rollback did not prove the old kernel was still running.
- Logging before emergency reset could itself delay the reset path.
- A post-ACK disarm helper killed the exact rollback watchdog but then rejected
  its unreaped zombie, leaving the failure path without the marker or timer.
- Repeating terminal evidence to an ACM endpoint after the collector closed
  blocked the target before its bootloader restart.

Cost:

- A consumed attempt produced ambiguous evidence and required physical intervention.

Prevention:

- Define protocol states explicitly: accepted, prepared, commit-received, execution-started, target-alive, rollback-started, fallback-proven.
- Make COMMIT idempotency and outcome recovery explicit; never equate an ACK with target execution.
- Keep rollback at a level that survives the transition being tested, or use an independent hardware/bootloader watchdog.
- Emergency reset paths must perform the reset before optional logging.
- Treat an exact same-PID/start-time zombie as inert, but reject every live,
  changed, or ambiguous process identity.
- Emit one post-ACK terminal record while the collector is attached, then
  execute the bounded fallback; do not make fallback depend on repeated TTY
  writes.
- Independent USB and power observers must record transitions even if the control plane dies.

Rule: **Rollback must be owned by a component that survives the failure boundary under test.**

### R9. Expensive validation sometimes ran before cheap closure checks

Observed pattern:

- Full CI repeatedly advanced to the next stale identity pin, requiring another complete run.
- Wrapper builds sometimes began before all candidate consumers and installed-state assumptions were checked.
- A late build correctly caught a profile/initramfs composition mismatch that could have been a fast manifest check.

Cost:

- Seven-minute CI runs and long clean-twin builds were repeated for mechanical metadata fallout.

Prevention:

Run gates in this order:

1. Static candidate dependency closure.
2. Generated-policy and lockfile no-diff check.
3. Capability and timing-budget tests.
4. Parser replay and lifecycle simulation.
5. Focused changed-component tests.
6. Candidate composition verification.
7. Expensive kernel/wrapper build only when inputs require it.
8. Full local CI once on a frozen tree.
9. Remote exact-head CI at publication/release checkpoints. Authority-free
   local packaging and offline validation do not require a fresh remote run;
   follow [development](development.md) for the separate trial/release gates.
10. Connected non-consuming preflight.
11. One live cycle.

Rule: **Do not pay for a later gate until every cheaper gate is green on the same immutable tree.**

### R10. Context and objective drift made the current truth harder to see

Observed pattern:

- The thread moved among charging rescue, Android restoration, storage migration, GPU, sensors, networking, and server plans.
- Active context grew to thousands of lines before being compacted.
- Historical fallback assumptions and candidate states survived after the phone topology changed.

Cost:

- Correct historical facts were sometimes mistaken for current facts.
- The main chat spent time rediscovering which artifact, slot, fallback, and goal were authoritative.

Prevention:

- Maintain one short `current-state.md` that contains only current facts and exact evidence references.
- Maintain one active objective with one acceptance test.
- Put GPU, sensors, storage, charging, and server features in separate tracks; only one track owns the next phone cycle.
- Archive superseded state rather than editing history into current instructions.
- At the start of a turn, read current state and the latest incident entry, not the entire historical corpus.

Rule: **One live cycle answers one primary question.**

## Critical guards to keep

These controls have prevented actual damage and should not be removed for speed:

- Exact serial, product, and USB-topology verification.
- Full boot-chain and storage-LUN identity checks before writes.
- Explicit authorization for the exact destructive storage operation; do not
  re-request an already authorized operation whose scope and gates are unchanged.
- One-use candidate/claim accounting when an outcome can be ambiguous.
- Read-only-first inspection and verified backups before repartitioning.
- A fallback whose exact bytes and boot path were proven before the experiment.
- Fail-closed behavior when multiple devices, ACM ports, disks, or identities match.
- Preservation of private signing material and credentials outside Git.

The optimization target is duplicated and hand-maintained process—not these guards.

## Mandatory pre-build checklist

- [ ] The active objective and single acceptance test are written in one sentence.
- [ ] The cheapest host-only test that could disprove the hypothesis has passed.
- [ ] The source tree is frozen; no active build is reading files that may change.
- [ ] The candidate appears once in the canonical manifest.
- [ ] Generated policy/allowlists/lockfile are current and regeneration produces no diff.
- [ ] Exact recovery/fallback capability manifest satisfies every command and syscall used.
- [ ] Timeout-lattice assertions pass.
- [ ] Real-output parser replay and full lifecycle simulation pass.
- [ ] Complete controller bindings and combined preflight/callback namespace pass.
- [ ] Host disk space covers peak twin-build and deployment usage with margin.
- [ ] Reusing an already-proven kernel was considered before starting a kernel rebuild.

## Mandatory pre-live checklist

- [ ] Exact device and full boot-chain manifest match.
- [ ] Current slot and fallback topology were recomputed after the last restore/boot.
- [ ] Installed wrapper, served bundle, controller, trust key, and policy hashes match one deployment receipt.
- [ ] `host-doctor` is clean: storage, listeners, mounts, binfmt, NetworkManager, firewalld, routes, and stale processes.
- [ ] Connected preflight is non-consuming and passes on the exact physical USB path.
- [ ] Battery voltage, temperature, and admission state are safe for the planned duration.
- [ ] Independent observation outlives the longest controller/rollback deadline.
- [ ] The target execution claim is unconsumed. Reuse stable recovery only
  where the existing reviewed lifecycle permits it; never retry COMMIT or an
  ambiguous target outcome. Artifact reuse alone grants no execution authority.
- [ ] Failure classification and rollback behavior are known for every stage.
- [ ] Phone writes remain within the admitted scope (including normal accepted
  server state on p23); no experimental storage write is implicit in a trial.

## Incident entry template

Add an entry only when it creates a reusable prevention rule.

```text
ID/date:
Primary question of the cycle:
Earliest failed stage:
Observed evidence:
Root cause (proven / probable):
Failure class: R1-R10 or NEW
Was the candidate consumed?:
Was phone storage modified?:
Why existing host tests missed it:
New regression fixture/test:
Systemic prevention change:
Successor prerequisites:
```

## Working agreement for the main chat

The 2026-09-10 kernel-first correction adds three prevention rules to the
[feedback loop](development.md#feedback-after-each-run):

- Before starting an expensive build, name the current hardware dependency it
  resolves. Denial compilation must not displace unqualified display, touch,
  GPU or power/recovery work just because a host build is easier to complete.
- A deliberately stopped process can exit137. Bind the explicit stop receipt
  when classifying it; exit137 alone does not prove an OOM or a build defect.
- Reuse exact-input build/test evidence and poll an existing live job. Restart
  only after its authoritative terminal result or missing handle is established,
  and after the reason for retrying has changed. Keep useful caches on disk.
- Record each completed matrix case durably, including raw-output identities,
  before preparing the next fixture. The state-guard harness failed while
  tampering with a read-only custody fixture after 19 passing cases. Fixing
  fixture permissions, recording terminal exceptions and continuing only the
  nine unrun cases completed coverage in another 15.572 seconds. Preserve the
  original failed run and qualify aggregate coverage against unchanged generator
  bytes; continuation must not relabel a partial run as a full PASS.
- Treat the build container and its launcher as separate lifetimes. A launcher
  exit does not prove the container stopped. Bind cleanup to a fresh ownership
  label and exact inspected container ID, stop/kill it independently of client
  state, and collect cleanup failures without skipping terminal evidence or
  client reaping. Nine injected cases now cover the successor kernel runner.
- Changed kernel source requires fresh output state. The existing compiler-cache
  wrapper can reuse matching compilation without importing or relabelling an
  old build tree. Describe twins using that cache as cache-assisted byte
  comparisons; they are not independent uncached compilations. Record cache
  statistics and elapsed times before claiming a speed improvement.
- A configured cache can still miss identical work. The successor's second
  build showed low reuse; a four-compile experiment reproduced CWD hashing
  despite fixed debug compilation paths. Distinct container CWDs missed twice;
  separate host outputs mounted at the same container path produced a direct
  hit and identical objects. Use stable container paths for future twins while
  preserving separate output state and strict cache checks. Do not alter a live
  build's frozen recipe or claim full-build savings from this small fixture.
- Check raw syscall flags, ioctl numbers and FFI layouts against the actual
  target UAPI, even in Rust. The GPU helper's ARM64 compile assertion caught
  an x86-derived `O_NOFOLLOW` value, repeating the earlier helper's architecture
  mistake before device execution. Retain that assertion with the source;
  host-only tests cannot establish a target ABI. Report the original operation
  error separately from a later cleanup error so neither cause is lost.
  The state-exchange prototype repeated this mistake with both `O_DIRECTORY`
  and `O_NOFOLLOW`. Its target-header assertions now derive their expected
  values from the Rust source and reject the previous host values. Include
  that compiler check before building any new raw-FFI helper, rather than
  waiting for an ARM64 operation to report EINVAL.
- The stable-path module runner now has actual timing evidence: 216.131 seconds
  for its first build and 38.580 for the cached comparison, with all 31 raw
  objects identical. Keep that 82.1% elapsed reduction scoped to this run;
  neither the old full-kernel twins nor a future build inherits that speedup.
- Regenerated metadata depends on the exact packaging tool as well as module
  inputs. The first successor composition correctly refused kmod34.2's extra
  `modules.weakdep` file. Preserve the failed output, inspect the actual delta,
  and qualify its exact names/content with a regression before retrying.
  Do not broadly accept arbitrary extra metadata or silently drop new records.
- Inspect the deployment artifact after a small successful build. The Rust GPU
  helper carried 4.1 MB of debug sections; deriving a separate debug-stripped
  copy reduced uncompressed size by 88.3% in 0.063 seconds. Preserve the original
  and verify loaded segments and ABI data before using the smaller copy. File
  size reduction alone does not establish faster transfer or runtime behavior.

- Bound suite concurrency by CPU affinity and inherited cgroup quotas, not
  only host CPU count. Full CI hit an unchanged five-second fixture deadline
  under a two-CPU quota while launching every isolated suite at once; memory
  peaked at 638.8 MiB without swap. Preserve the failure and deadlines, test
  the bounded queue and cleanup, then rerun on frozen corrected source. Drain
  all ready outcomes before refilling so success cannot hide a queued failure.

- Pin locale where production code sorts machine inventories or parses tool
  diagnostics. A desktop service inherited en_US.UTF-8 while the shell used
  C.UTF-8; the same four UFS filenames failed an exact comparison. Test with a
  different caller locale so CI environment normalization cannot hide the bug.
- Verify deployment-tool path semantics as well as bytes. AVB resolves a hash
  descriptor's partition name to a sibling image path; side-labelled comparison
  files need a bound canonical `boot.img` copy. Reuse a retained failed wrapper
  to test this correction before repeating signing. Keep explicit signing-event
  records so a later verification failure does not imply no signature existed.

- Separate authenticated payload members from additions used only in a VM.
  Pass original sealed members into strict inventory recognizers; pass the
  augmented copy into the guest. Do not allow arbitrary fixture prefixes in a
  production recognizer to compensate for mixing those inputs.
- Container client exit is not terminal-container or descendant cleanup proof.
  Record ownership before create, inspect before start and after exit, confirm
  removal, and reap the client group independently. Bound the caller's log read
  as well as the producer; a rejected oversized log must not trigger a full read.
- Launch focused checks with the documented interpreter mode and absolute script
  path. A systemd service does not inherit the shell working directory, and
  Python -I removes sibling-import behavior relied on by existing scripts. Fix
  the harness invocation before treating such launch failures as source bugs.
- Reuse a size-bound RAM snapshot primitive without overriding its module
  globals or inheriting a historical experiment's claim. Bind each new caller
  to its own artifact/trial identity. Check the wrapper's actual control flow:
  an embedded RAM bundle bypasses installed selector fallback, so selector
  recovery evidence alone does not qualify recovery from that RAM boot.
- An ELF DYN header alone does not qualify a static-PIE executable. The pinned
  GNU Rust target supplied `-static -no-pie`; appending `-static-pie` produced
  an image that faulted before its first syscall. Remove only the verified
  conflicting defaults in the pinned linker adapter and test startup and the
  actual operation in a root without shared libraries. Keep both failed and
  corrected artifacts. Check a first binary before investing in its twin.

- Verify the recovery environment's available tools before generating recovery
  actions. V11 has no Python; host-only tests of a Python stager cannot qualify
  it. Exercise the exact sealed ARM64 tools in an empty root without Python.
  Derive fixture device numbers with `os.makedev` from fixture sysfs major/minor
  values instead of copying manually encoded integers.
- Mocked transport tests do not cover production imports. Launch an isolated
  child using the actual fixed repository dependencies before a live probe;
  adding the correct producer directory must not depend on the parent shell's
  Python path. Keep ordinary authenticated SSH usable over an existing route
  without sudo; require privilege before creating any host network resources.

- Include encoding overhead when bounding retained transport evidence. Two
  1 MiB output streams become about 2.7 MiB in base64, exceeding the controller's
  1 MiB receipt limit. Use a separate bounded transport receipt and test both
  full streams on a failure path so the failure itself does not discard logs.
  Validate JSON proof types explicitly: Python equality accepts `0 == False`
  and `1 == True`, which should not qualify a boolean protocol assertion.

- Test root-owned target file operations in an isolated user namespace mapped
  to UID 0 when host sudo is unavailable. Keep the host filesystem read-only
  except the private disposable fixture directory and isolate networking. This
  exercises real metadata and lock checks without weakening target guards or
  creating privileged host fixtures; physical telemetry remains synthetic.
- Reconcile interrupted operations from current record, exchange backup and
  intent/completion bytes together. A missing command reply is insufficient.
  Permit only explicitly recoverable combinations, hold/check record identity
  through the snapshot, and retain unknown partial states for reconciliation.

- Separate a boot's healthy-commit deadline from the time of a later health
  observation. The original startup-only predicate rejected actual healthy V9
  at 50,061 seconds uptime although it committed at 64.143 seconds. A dedicated
  later-health predicate retains the 300-second commit limit and fresh boot,
  runtime, readiness, service and storage/power checks. Leave startup semantics
  unchanged and replay the same observation through both predicates.
- Derive runtime hashes from the packaged artifact. The rollback timer source
  contains `@OUTER_SECONDS@`, while the deployed unit has the resolved 900-second
  value. Compare actual accepted/successor archive members before inheriting a
  hash; do not relax the runtime comparison to accept a template.

- Preserve fixture metadata under the production runner's umask. An ordinary
  readiness-file copy under `umask 077` changed mode 0444 to 0400 and correctly
  failed the target guard. Reproducing both umasks identified the fixture cause;
  `cp -p` fixed it without weakening production metadata checks. Retain the
  failed output, then reuse qualified raw output for host parser tests instead
  of repeating unchanged ARM64 execution.
- Discover retained state paths shallowly before searching a specific subtree.
  A recursive listing crossed copied worktrees/fixtures and generated more than
  100,000 output tokens; a depth-two search found the relevant V11 receipts.
  This avoids excessive discovery output; it is not a measured build speedup.

- Separate bounded initial USB/SSH readiness polling from later health checks.
  A post-capture or post-restoration observation must remain on its recorded
  boot and must not silently become a new boot observation. Preserve discovery
  failures individually, poll only reads, and require one complete health proof
  after discovery. Test actual controller receipt flow as well as isolated
  callbacks; a successful fallback restoration must leave a failed trial failed.

- Give nested callbacks distinct evidence filenames within a shared phase.
  The fallback locator and its health reader both initially wrote the first USB
  observation to the same path. Exclusive creation correctly refused the second
  write. Separate the parent's location observations from the child's health
  observations, preserve the failed run, and exercise both layers together.
  Keep exclusive creation and one-use intents; never fix a collision by allowing
  receipt overwrite. Validate all nested writer paths when assembling the
  driver, before source mutation. Test dispatch should name its intended callback
  subset so adding a production phase does not silently expand a synthetic
  fixture's scope.

- A UID-remapped namespace changes file owners relative to Git's cached stat
  metadata. A source check there timed out while Git reopened retained Images
  and initramfs archives: indexed UID/GID 1000:1000 appeared as 0:0. Capture and
  revalidate source identity on the host, then mark it explicitly as fixture
  input inside the namespace. Keep production checks real, run them as the
  repository owner and bound their subprocess group. Do not solve this by
  weakening source comparison or repeatedly scanning large artifacts.
- Record when observation stops separately from when cleanup finishes. A slow
  cleanup must not make an early-ended recorder appear to have covered its full
  deadline. Emit the terminal result after owned cleanup, reserve log capacity
  for that result, and finish cleanup even if the supervising output pipe closes.

- Distinguish rejection before launch from losing a launch result. Only the
  former can prove there was no child. Retain the owned process before waiting
  for readiness; verify its exit and cleanup evidence independently of later
  source/admission checks. Exercise real child pipes and the actual controller
  recovery sequence, including a separate fallback recorder, before treating
  callback fixtures as complete preparation. Virtual deadlines qualify protocol
  handling, not elapsed physical recording time.

- Verify remaining recorder lifetime after snapshot creation and device queries,
  immediately before transfer. A readiness proof obtained before preparation
  cannot establish the same remaining window afterward. Use a tiny actual
  sealed descriptor and child process to test FD inheritance, timeout and output
  retention; keep full-image identity qualification separate and unchanged.

- Distinguish raw process streams from JSON receipts: successful stderr can be
  empty, while a JSON object cannot. Retain descriptor, ownership, link and size
  checks for both formats. An actual entrypoint replay catches this distinction
  before phone execution. Reuse an observation already obtained by a combined
  preflight instead of issuing another identical source-health query.

- Retain a launched process before writing its request, and use a stable process
  handle for cancellation. Monitor both the original controller and intermediate
  privilege launcher: either can disappear independently. Bound output writes
  so a stalled reader cannot block cleanup. A forced process exit is failure
  evidence, never proof that owned network cleanup completed.

- A process runner reused inside a threaded guardian must avoid Python
  `preexec_fn`. Apply resource limits through a fixed executable wrapper instead,
  verify the actual child limits, and recheck affected process integrations.
  Preserve prior source bytes when refreshing dependency pins; separate the
  behavior change from mechanical hash updates and keep old evidence scoped.

- Account for encoding expansion at each process boundary. A bounded child
  stream can exceed an older JSON receipt limit after base64 wrapping. Keep raw
  output in exclusive, bounded disk files and reference it from a small process
  receipt; test a real oversized stream and failed-launch output retention.
  Reuse the same transport hook in nested recovery readers, and test that wiring
  explicitly before relying on the assembled driver.

- When reusing an account-relative verifier across a privilege boundary, inspect
  how it chooses its home and ownership checks. The temporary-boot claim verifier
  must execute as deck even when called by a root helper; looking under root's
  home would test a different lifecycle. Keep the command fixed and bounded.
  For immutable artifact checks repeated per phase, stream the initial digest
  and reuse it only while inode, ownership, mode, size and timestamps still match;
  test same-size replacement before claiming the cache is safe.

- A generated diagnostic script can contain another operation's text as inert
  data. Simulated replies must dispatch by the admitted phase and exact request,
  not by a substring found anywhere in the script. The full-flow fixture exposed
  this twice before phone execution. Stop at the first failed scenario while
  repairing the fixture, retain its receipts, then rerun affected paths.

- Authentication lifetime must cover later recovery commands as well as initial
  startup. Prepare bounded noninteractive refresh from the same controller
  process, test loss of credentials and shutdown of the refresher, and complete
  its first successful refresh before consuming a one-use claim. Introducing a
  refresh thread requires auditing every subprocess path, including the final
  sealed-image transfer. Keep an already prepared human-assisted probe stable
  while making independent changes to the later trial launcher.

For each successor candidate, the main chat should report only:

1. The single hypothesis being tested.
2. The cheapest test that could disprove it.
3. Which failure class from this file is relevant.
4. Why a new build or phone cycle is necessary.
5. The exact pass/fail evidence after the cycle.
6. The regression or systemic change added before any successor.

If the failure is host-only, do not redesign the kernel. If it is a new hardware observation, preserve the raw evidence and turn it into a replay fixture. If the same failure class recurs, fix the process or source of truth before issuing another candidate.

### Keep GUI buffer limits separate from diagnostic log bounds

On 2026-09-11, the host sudo dialog died with SIGXFSZ in 2.328 seconds because
an 8-KiB diagnostic file limit also restricted its Wayland shared-memory files.
The user saw no dialog. Inspect the process signal before attributing an empty
askpass response to cancellation. Authentication now permits bounded 64-MiB GUI
files, drains stderr through a separately capped 8-KiB pipe, and retains core=0,
timeout and owned cleanup. Verify a real window as well as subprocess fixtures.
Mapped buffers can outlive their closed file descriptors: the first window check
missed them by inspecting only open FDs; `/proc/PID/maps` supplied the evidence.

The follow-up r3 window rendered but did not accept the Steam on-screen
keyboard. Synthetic key injection also failed in X11 mode and a pointer test
failed, so the precise input-routing cause is unresolved. Rendering alone does
not qualify input. A prepared local touch keyboard calls the entry callbacks
directly and has tested Shift/symbol/delete/cancel behavior; real touch input
still needs the user. Do not record simulated injection as a physical pass.
SIGTERM to `sudo -A -v` started a replacement askpass during cancellation.
Terminate the verified owned authentication group on forced abort so the dialog
cannot outlive cancellation; this path runs no privileged phone command.

The r4 touch authentication succeeded, but its subsequent detached sudo child
could not reuse the credential. Reading only sudo's record-match function had
missed the later session-ID check in `timestamp_status`. Follow authentication
through lookup and acceptance. A shared parent PID is insufficient when each
child calls setsid. Preserve the session and create separate process groups
with native `process_group=0`; actual-child tests now assert both properties
for authentication, refresh, capture and fallback transport.

Full-flow evidence destinations must be fresh before execution. A reused
default destination cost 7.781 seconds before refusing the copy; the harness
now checks destination existence before controller.run. The corrected run
preserved earlier evidence and passed all four cases in 25.566 seconds.

The corrected same-session handoff passed on real sudo in r5 after one touch
password entry, for both root guardian profiles. Preserve those observed process
and source identities when reusing the evidence; later registry or documentation
commits are separate source observations.

Full-flow fixtures must retain early stdout as well as stderr. A capture child
returned its failure as structured stdout, leaving stderr empty. That exposed a
frozen-clock subtraction yielding 1380.0000000000002 against a 1380-second cap.
Use whole-second values for this simulated clock so its exact-duration boundary
is representable; keep production timing limits unchanged. All four flows then
passed in 26.317 seconds. Source-gated tests also correctly refused the initially
dirty checkout; freeze the small source change before those integration checks.

Registration and readiness are different checks. The final r39 review found the
exact profile in the repository registry but no unconsumed lifecycle record on
disk. Check that record's bytes, owner, mode and both unused guards before asking
for a password, then recheck before consumption. Six new refusal/preservation
cases and all 21 launcher tests passed in 0.824 s. Read-only final evidence replay
can reuse unchanged component results while retaining their original source and
fixture scope; do not turn a documentation commit into another root prompt or
expensive build. Bind the final qualification only after freezing progress notes.

Overlay order can change DTB bytes without changing hardware semantics. Combined
OLED/touch/A660 composition produced equal complete parsed trees and preserved
boot metadata in both orders, but different hashes. Pin GPU, disabled touch, then
touch enable as the packaging order; twins within each order matched. Compare
all properties and boot metadata, and run actual encoded mutations through the
verifier. Merely checking unequal dictionaries is not a refusal test. Five real
mutations were rejected in 0.106 s. Keep this offline proposal separate from
physical qualification and the already prepared headless trial.

A successful `fastboot boot` can return while USB still enumerates as fastboot.
The actual r42 trace went fastboot → absent → recovery → absent → enumerating →
target, and the kernel committed healthy at 64.957 s. Initial health discovery
must allow that transient only after a verified boot command and before seeing
an authenticated identity, within the original deadline. A post-capture return
to fastboot must still fail. The original source reproduces the refusal; 32
candidate checks pass, including the captured USB state and deadline boundaries.

Boundary mocks must preserve the real helper contract. Fallback tests replaced
`link_ready` wholesale and missed that `NETWORK.command` returns `(code, stdout)`.
The real fallback attempt failed unpacking a third value before acquiring any
network state or invoking SSH. The corrected adapter has six contract cases,
including an unmodified read-only host route lookup; all 25 route/process cases
pass. Keep the original controller failure separate from independently successful
kernel/capture observations. Do not repeat a consumed phone trial just to test a
host parsing fix. Preserve executed sources and stage fixes for the next driver.

Disk-backed output still consumes cgroup memory through dirty page cache.
The OLED packager was killed at its 512-MiB limit with 503,865,344 dirty file
bytes, while the host had about 10 GiB available. Preserve partial signer
receipts and entered outputs; do not diagnose host exhaustion from exit 137
alone. The unchanged runner/inputs passed in a fresh directory with an earlier
`MemoryHigh=256M` threshold, keeping `MemoryMax=512M` and no swap. Its observed
peak was 361.5 MiB over about 75 seconds. Carry this invocation policy forward;
it is evidence for this workload, not a universal prevention guarantee.
Read the runner's enforced limits before launching: a stale README's larger
scope caused a 0.115-second inspect refusal before any key access. Corrected
inspection passed in 0.615 s. No kernel rebuild or unchanged broad CI was needed.

A restored prior selection does not make a consumed transition reusable. The
OLED helper uses a separate durable transaction and exact new pending/healthy
records, while its guard verifies all six prior kernel recovery files. Native
and actual ARM64 tests cover old-record/inode restoration, prior transaction
preservation and rejection of mismatched old trial states. Keep the algorithm
and verified ABI unchanged when only the signed profile changes.
For this phone, discover the reboot helper in the exitrd at
`/run/initramfs/usr/libexec/rog5-reboot-bootloader`; the original root-relative
shutdown path is interpreted after changing root. A wrong host-side probe path
caused one 2.043-second read refusal. File-operation tests require
`unshare --user --map-root-user`: direct deck execution produced 13 ownership
errors in 0.178 s, while the unchanged 16 cases passed there in 0.644 s.
Carry the execution environment with test commands, not just the test filename.

Source runtime identity and installed fallback inventory are separate bindings.
The OLED derivative initially tried to obtain installed-file metadata from its
new source-health receipt, which has a different schema. Reuse the pinned V9/V11
inventory explicitly and verify those files again on the current source; do not
rename installed bundles when changing the running source identity. The first
assembled preflight refusal exposed this before any mutation.
Preserve execute permissions when staging ELF tools. Byte-identical selector
copies without execute bits returned an empty failure in 0.014 s; corrected
modes and an explicit preflight check passed the three cases in 0.332 s.
Generate changed ARM64 observation fixtures before full recovery flows. After
target success, an absent new fallback fixture stopped the next scenario; the
11 current cases passed in 52.193 s and only the remaining three flows resumed.
Refresh transitive source pins in dependency order from the preceding pin map,
keeping each prior result. Do not reapply the initial namespace transformation
over an integrated cohort or reuse its historical qualification/claims.

Complete exact profile registration before final-source qualification. In r61,
one static registry addition preserved all 227 older record values; the existing
pending-record writer and 21 lifecycle tests avoided another helper family.
Preparation preserved all 627 existing claim files/guards and did not consume the
attempt. Refresh transitive digest constants and input rows only after the source
change is final. Archive the previously qualified cohort before editing it.
Actual privilege handoff evidence may be inherited only after an explicit source
delta check shows the entrypoint/process bodies unchanged; retain its original
source in the inheritance record and do not claim fresh credentials. Current
controller replays and the actual read-only launcher preparation then passed.
Validate evidence metadata, emptiness and size before canonical publication; this
turn reused the reader contract and avoided r60's archive failures entirely.

Watch backlight registration while a panel insertion helper is still running.
Waiting only for helper exit leaves a gap between registration and zero request.
The OLED loader reuses the single-syscall helper and checks the endpoint every
50 ms; its child-process fixture proves zero is requested during probing. Early
blanking alone is not the failure cleanup: a later asynchronous brightness change
must also receive a zero request under independent same-boot ownership. A focused
regression now verifies this path, while a changed boot refuses stale cleanup.
Insertion success still needs driver binding, endpoint and independent full health;
a one-use load may not retry or unload after a partial or uncertain outcome.

A completed capture should be consumed as closed evidence, not kept alive merely
to authorize a later component. Bind its original deadline, raw stream hashes,
ordered cleanup, absent original processes and independently authenticated target
health. USB sampling alone never authenticates the gadget's boot or serial.
Keep read-only health freshness separate from hardware one-use state: after a
120-second health expiry, create a new bounded, numbered health receipt and bind
its exact path/hash. Do not repeat a module insertion/display attempt or replace
prior evidence to refresh health while waiting for the operator. The r63 checks
exercise both expiration and refresh, with no new boot or network setup.

Use one ownership lock for the device's module and frame phases, not separate
locks that permit cross-phase overlap. The component monitor's initial phase-local
lock was strengthened before physical admission; a real flock regression verifies
cross-phase refusal. Preserve both the old qualification and final sources.
A restored admission file must not clear a monitor failure: the actual owner/
Unix-socket integration test changes then restores it and confirms failure stays
latched. Independent verified cleanup may finish that failed monitor while the
terminal status remains FAIL. Fixture completion times must follow actual fixture
admission creation; inventing earlier offsets tests the timestamp guard instead
of the intended cleanup path.


### Startup evidence before SSH

The r77 OLED attempt reached switch-root but left no explicit helper failure,
archived pstore or prior-boot journal on V11. A built-in pstore configuration
alone does not establish a working retained-log backend. Collect bounded kernel
records independently of journal/service health and keep packet loss, ring
overrun, truncation and terminal limits visible. Diagnostic delivery never
proves boot health. The r78 Rust helper reused the retained toolchain/linker:
2.810 seconds for focused checks/build and 1.166 seconds for a byte-identical
ARM64-only twin. Keep this incremental path separate from frozen kernel builds.


A compiled helper is not a prepared human-assisted test: finish receiver,
privilege entry, cleanup and actual staging before requesting availability.
The r79 handoff arrived with unfinished host code, so the old Ready was released.
Bind the final launcher and staged inputs in a preparation receipt with an exact
terminal command. For temporary firewall access, use a narrow expiring rule and
prove ownership before explicit removal. A timed-out add is ambiguous, not proof
that nothing changed; retain that uncertainty and never label it cleaned without
an absence observation. Compare diagnostic terminal counts with authenticated
SSH output when both are available.


For optional startup payloads, test both absence and inherited stale inputs.
A standalone `test ... && test ...` is not reliably made fatal by `set -e` when
its first operand fails; attach an explicit failure branch to admission guards.
The r80 archive fixture caught a stale relay being overwritten and now proves
rejection. Preserve exact selected-release parameters in composition fixtures
when adding a unit that consumes them. Use `git worktree add --no-checkout`,
configure sparse source paths and required test dependencies, then populate the
checkout; full checkout needlessly copies historical kernel artifacts. A retained
untracked tool must still satisfy its existing content pin before reuse.


Before adding privilege reuse to a passive diagnostic, check whether the network
flow can be initiated by its receiver. The r81 normal-USB experiment captured the
same 116 kernel records using a bounded, nonce-matched host request and fixed UDP
ports, with no sudo or firewall-rule change. This is measured behavior under the
current host firewall, not a general guarantee for every zone or early boot.
Preserve timeouts, connected-peer filtering and unauthenticated-packet labeling;
use authenticated SSH to compare terminal counts when available. A fresh Ready
for an already prepared test must launch that entry immediately even if an
independent alternative is being developed; never switch the user into unfinished
preparation or rerun the now-consumed entry afterwards.


A short UDP success does not prove an idle 120-second capture will retain its
flow. r82 read the host's actual 30/120-second UDP timeouts and added bounded
20-second keepalive requests. Drain queued target records before classifying a
recovery transition, and bind diagnostics to the separately observed stage boot;
a fallback must not reset the evidence accumulator or erase an incomplete run.
Bind the exact payload's transport config in recorder receipt and live readiness.
For a new empty `--no-checkout` worktree, sparse selection alone may leave it
unpopulated: follow it with `git read-tree -mu HEAD` before editing. Apply that
population step only to the newly created empty checkout, not a user's working
tree. Direct helper imports also need the established scripts/host search path.


A sparse packaging/composition checkout needs `packaging` and `tests` in addition
to scripts, initramfs, configs and the exact ignored tools. r83 lost 48.175 s to
two missing-file refusals after root hashing had started. Add cheap source
presence checks before launching large scans; this does not replace later exact
content checks, and independent root hashing can still overlap actual artifact
validation. Source completeness is separate from the kernel/module build cache.
For a runtime-only change, reuse the qualified standalone builder and compare
the complete archive delta: r83 changed only init plus fresh identity, added the
sealed log pair, and kept all hardware bytes. Two full payloads took 33.191 s
total with no kernel/Rust rebuild. Delete only owned, reconstructible scratch
once durable output identities and receipts are verified; r83 recovered 744 MB.
Use the existing exact phone health observer rather than guessing systemd unit
names: authenticated SSH and the accepted readiness service establish the actual
running health checks. An unsolicited Ready is not permission to replay a
consumed test; release presence when no prepared successor entry exists.

### r84: carry source-runtime capabilities into the short handoff

V11's missing Python was already recorded in older observations, but a new
read-only inventory attempted it again and exited 127. The active V11 shutdown
also differs from the prior kernel-source shutdown, and its Wi-Fi healthy-writer
unit is absent. Keep these exact capability constraints in the latest handoff;
derive source actions from authenticated current bytes and use the already
verified BusyBox/loader for device scripts. Do not treat absent historical unit
names as a current health failure or install Python to preserve stale assumptions.
The new shell staging path passed seven ARM64 cases in 27.248 s, then staged and
independently verified inactive RAM files on V11 in 1.240/0.569 s without reboot.
Its source shutdown and selection checks precede any RAM directory creation.

The initial lint runner also lacked cargo fmt. Reusing the existing pinned
rust-tools directory produced a 0.975 s Clippy pass without a download or changing
the source; formatting applied only to the disposable lint copy. Use those pinned
tools directly for this build image. Preserve the initial failure evidence.
The 35 guard cases cost 106.701 s and are terminal PASS: rerun relevant cases only
when source changes justify it. Qualified r83 payload and A01 bytes were reused.

### r85: continue terminal fixture failures and check the intended refusal

The source-action suite completed ten ARM64 cases before its fixture writer
failed on a retained mode-0400 custody file. The fixture helper now makes its
own copied file writable before injecting corruption, then restores the required
mode. Keep the failed run and executed harness; continue from the first unfinished
case in a new output directory when production source is unchanged. The remaining
eleven cases passed in 131.090 s without repeating completed operation paths.

Review found the first shutdown-replacement test also changed mode through the
fixture's restrictive umask. Its failure proved metadata refusal but did not yet
prove inode replacement detection for identical bytes and mode. Two focused
ARM64 tests now preserve those properties and require the exact shutdown/directory
identity refusal (30.749 s); the locked-record test also requires the recorded
selection-replacement refusal. Check the reason as well as a nonzero exit status.
Source action and observer hashes remained unchanged; no kernel, relay, module,
payload or A01 rebuild was necessary. Phone preflight/reconciliation took only
0.689/1.219 s; retain the actual V11 capability contract in the outer integration.

### r86: migrate fixture clocks, capability scope and protocol identities together

The new recorder fixture initially had no CAP_NET_ADMIN after user/network
namespace creation and stopped in 0.016 s. Add that capability only inside the
isolated namespace; do not involve host sudo or host network settings. Its next
run stopped on `ValueError: capture deadline`: the outer virtual clock had been
patched while the kernel capture's default clock still referred to the original
function. Inject one explicit virtual clock into both layers. The resulting 21
cases used real local TCP/UDP sockets and passed in 0.415 s, including closure
and config mismatch refusal. The supervisor's separate child/probe suite passed
21 cases in 16.667 s; its kernel transport is explicitly synthetic.

The fallback callback fixture reused a source-stage reply without changing its
old selection to the expected pending selection. Strict parsing caught it before
acceptance. Preserve the 24 passing cases and rerun only the three corrected cases
(1.377 s); label transport-fixture identity substitutions explicitly. They are
not new ARM64 or live fallback evidence. Seed successor digest refresh from both
private source history and exact prior repository files: four missing repository
pins caused an import refusal, now covered by the dependency graph. Keep runtime
route/predecessor conversion explicit; successful imports do not prove readiness.

### r87: preserve predecessor identities and read the installed capability contract

The copied route generator assumed 0644/0755, while the pinned installed inventory
requires 0400 bundle files and a 0600 selector. Its local build refused before
phone I/O. Use the exact inventory metadata and sealed V11 shell; Python is absent
on this source. The real inventory completed in 5.806 s with unchanged state,
so there is no reason to rebuild hardware artifacts or relax its 35 s transport
budget. Reuse that raw observation for parser/receipt tests instead of rereading
the phone for each host case. It is historical evidence, not future readiness.

Keep historical predecessor pins in a separately sealed index. A source digest
migration must update the successor's producer graph without rewriting consumed
claim identities or treating an earlier preflight-only failure as the actual
latest trial. Read historical summaries under their exact recorded metadata;
retain stricter live receipt requirements. Preparation now verifies closed r77
capture/credentials, actual restored V11 and consumed r84 staging, then still
requires a fresh bounded read before any new claim. All 21 cases passed in
2.191 s without phone I/O. The fallback fixture's missing copied tool directory
was found before execution; it now verifies the two retained sealed-tool paths
and hashes before allocating cases. No production guard was weakened.

### r88: run the complete command policy before requesting hardware availability

Source callbacks alone passed while the outer admission policy still selected
Python for three shell actions. The full assembled flow refused install, then
restored its fixture selection. Correct the policy's transport without relaxing
exact script/intent comparison; all four flow scenarios passed in 33.400 s.
Retain the failed result and use qualified raw shell replies in host fixtures.
A source-copy operation also lost askpass's required0700 mode despite preserving
its digest. The graph refresher now checks that mode before publishing inputs;
rerun only the four affected privilege tests, preserving the six prior passes.

A live terminal does not prove a live sudo timestamp: session44286 still exists,
but its noninteractive check explicitly requires a password. Finish independent
preparation and ask for authentication only once the intended check can start.
Do not reopen a password window or repeat the same failed noninteractive check
without new evidence. Separate real root-handoff proof from root/network fixtures.

### r89: close the repository-to-private digest edge before final replay

The claim registry changed after component validation. Its previous digest was
not in the private refresh graph, so boot-callback import refused the old pin.
Seed the exact pre-registration consumer edge before final publication; verify
all53 admission inputs and then freeze both repository and private sources.
The final replay took27.433 s and checked its source/metadata snapshot unchanged
before/after. Retain the earlier successful scopes rather than assigning them
new producer identities. Registry addition preserves all227 prior byte records;
registration, pending-file creation and consumption remain distinct operations.

Prepare the privilege probe independently of physical hardware availability.
Its bounded read-only check and local input helper can be ready before asking
for the Deck password window. Never infer authentication from a previous Ready
or from a live terminal; no new window starts without fresh availability.

### r92: complete the handoff without repeating authentication preparation

Prepared local authentication and both real privilege probes completed in9.599 s.
Bind this result to the final source snapshot and reuse unchanged software replay
rather than rerunning builds. The probe's successful timestamp belongs to its
process/session; the boot launcher must authenticate and refresh within its own
lifetime. Save its exact invocation before requesting physical availability.

A legacy host-doctor requires a manifest absent from the frozen controller tree.
For this prepared controller, use its pinned capture-network preconditions and
exact authenticated route proof; do not add a legacy manifest to a qualified
source tree or label the unavailable command PASS. A UID1000 preparation check
cannot open a root0600 recorder lock: inspect the kernel lock table read-only,
then let the unchanged root entrypoint acquire its lock during actual arming.
These observations add no privilege changes and do not weaken runtime admission.

### r93: drain passive diagnostics while synchronous health checks run

The physical startup recorder armed, but the controller waited on SSH without
pumping the recorder pipe. More verbose startup diagnostics exhausted the pipe;
only59 events and no terminal report survived. A real-child >1 MiB burst stalls
under the original supervisor and completes under a serialized background
drainer. Exercise simultaneous busy callbacks and diagnostic bursts, not only
short stage messages or final closure. Keep output bounds, process ownership,
full-duration proof and cleanup checks unchanged. Candidate closure stops and
joins the drainer before returning stream ownership to the final loop.

Current-boot health at73/199/534 s does not convert a failed23-minute recording
into PASS. Present-state network cleanup inspection also cannot replace the
missing original terminal receipt. Preserve the live healthy boot and consumed
claim while preparing the next module test. A refgen supply deferral is expected
while its deliberately staged module remains unloaded; verify actual module
presence/load state before treating the log as a missing DT regulator or building
another kernel.

### r94: match runtime ancestry before module staging

The module loader's no-writable-parent assumption rejected the actual root-owned
sticky1777 `/run`, although both payload directories are root0755. Hold each
no-symlink directory descriptor, accept only that literal sticky root ancestor,
and continue rejecting writable payload descendants. Stage new workers below
root0755 `/run/initramfs`; inspect the actual helper/modules/descriptor before
asking for availability. The same extracted read-only input functions passed on
the phone in0.430 s; no module operation was needed to discover this mismatch.

Namespace fixtures must set modes explicitly despite umask077 and execute
root-only backend tests in their declared root user namespace. Match `/run`
filesystem evidence to its active device number, since a private test mount can
obscure an older mount at the same path. Preserve those failures and rerun only
the affected suites. For new SSH kernel logs, direct bounded disk output avoids
coupling log delivery to synchronous controller callbacks; real-child burst,
closure/cancellation tests and actual same-boot read-only heartbeats are separate
proofs from a hardware module test.

### 2026-09-11 r95: Bind the complete identity in reused phone fixtures

The new module coordinator's first composed tests failed cleanup because the
reused backend fixture returned its historical boot ID, although the surrounding
transport used the current boot. Bind the fixture's full identity from the peer's
explicit expected input, including cleanup. Keep real identity rejection checks;
never relax them to make a fixture pass. The corrected13 duplex/staging cases
passed in3.142 s;13 integration cases passed in2.189 s. Retain the initial failed
logs. Reuse unchanged qualified component results rather than rerunning72 cases.

Pre-stage the exact module scripts and immutable input/health receipts before
asking Ready. In this run preparation took3.008 s and final launch validation
0.694 s; the saved command needs only brief current checks and logger arming.
Keep prepared transport binding explicitly non-live: it cannot substitute for
actual runtime logger liveness. The independent blanking path must remain usable
when the logger lease fails, and a logger terminal failure must keep the overall
result failed. All three are covered by composed tests. Preparation now reaches
a concrete phone RAM namespace instead of another pending integration report.

### 2026-09-11 r96: Read refresh from DRM, retain structured failures

The module trial loaded both display drivers and registered `fb0`, then failed.
The exact endpoint check subsequently reproduced rejection of
`U:1080x2448p-0`. On this compiled kernel DRM fbdev setup clears pixclock, and the
fbdev conversion consequently reports refresh0. Actual atomic DRM state records
1080x2448 at60 Hz. A zero fbdev field must not be treated as60 or as a measured
zero-Hz output. Require the active same-controller DSI mode and retain its source.
The separate new endpoint checks exact identity/timing twice, passes20 existing
endpoint and14 new mode/pipeline cases, and passes read-only on the phone in
0.423 s. Optical scanout remains separate. No hardware retry was used.

The supervisor discarded full worker error details by stringifying a structured
payload and truncating its first2000 characters. Large blanking receipts came
before the root cause. Keep bounded worker/component errors as structured durable
evidence before producing a short user-facing reason. Carry this fix into the
next controller; a successful cleanup must not hide the initiating failure.
Original helper exit details cannot be reconstructed from the truncated result.

The current composed tests ran63 directly defined cases rather than231 inherited
case instances; parent fixtures still provide setup. The measured run took
29.852 s including the deliberate20-second timing case. Reuse the cached ARM64
renderer and unchanged component checks. A negative pipeline test must allow
independent zero cleanup after entry while prohibiting frame writes/illumination.
When embedding imported read-only source, use its own namespace: BOOT in the
endpoint is a regex and can shadow an ad-hoc observation variable.

### 2026-09-11 r97: Discover device permissions and close preparation before Ready

The first frame preparation rejected the actual `/dev/fb0` ownership: udev uses
root:video983,0660, while the reader assumed group0. Preserve the failed attempt,
cleanup and health. The successor accepts the exact observed combination plus
private root:root0600, still rejects other identities/permissions/device numbers,
and checks actual node/sysfs metadata before admitting an open. No phone
permission change was needed. Five node/real-ARM64 cases and the36-case updated
composition (including those5) pass; unchanged cache/context cases are inherited.

The full-error improvement was useful immediately: the bounded original worker
payload is saved before summarizing, then fetched by its hash. Do not flatten
large component receipts into a truncated string that loses the root cause.

Separate capture/render/cache from the operator-dependent display. Actual capture
exchange took1.013 s, rendering0.083 s; full preparation95.345 s includes an
intentional90-second log. After verified cleanup and health, the cached frame
waits without an operator countdown. Ready performs short checks and restores
sealed cached bytes, with no rendering/build/staging. Final launch validation was
0.543 s. Physical timing starts at nonzero brightness, not while the user waits.
This is preparation evidence; visible scanout still needs an actual observation.


### r98: qualify virtual-console ownership before operator readiness

The prepared cached-frame show failed in0.762 seconds after writing and reading
10653696 bytes; it never attempted nonzero brightness. Streaming post-failure
comparison took0.193 seconds and isolated128 changed bytes to the exact8x16
cursor cell reported by vcsa1. Active tty1 remained KD_TEXT and fbcon bound;
cursor_blink was0, so do not describe this as proven blinking. Retained full
worker failure and kernel logs immediately identified the failed boundary.
The warning about virtual address space alone does not prove causality.

The prior preflight validated framebuffer geometry and node permissions but
missed the console as another writer. A new read-only console preflight now
refuses text mode, passes8 focused tests and detects this actual phone state in
0.007 seconds. Integrate a separately bounded graphics-mode ownership and
restoration path before any new Ready request. Keep all-byte comparison and
never rerun the consumed show. Graphics mode alone is not ownership proof.
Read sysfs attributes according to their access mode: rotate_all is write-only;
the first diagnostic failed there, and its evidence remains failed.


### r99: validate console transition and independent restoration while dark

The actual two-second KD_GRAPHICS hold preserved exact framebuffer layout and
60 Hz DRM timing. Parent-retained descriptor cleanup restored KD_TEXT then zero;
30 seconds of kernel recording and final health passed. This removes uncertainty
about the mode transition without asking the operator to wait. Keep the next
cached-frame write/readback validation unlit too: a successful transition is not
a successful framebuffer write, and restoring text mode can redraw the console.

Eight lease cases and five actual-fork/duplex cases ran in 0.116 and 2.712 seconds.
The initial test peer wrongly imported host UID1000 checks inside a root-mapped
namespace; the corrected peer imports only target code. Keep the production UID
checks, test process boundaries, and independent restore/zero failure assertions.
Actual r99 captures equal the retained r97 capture, so reuse cached pattern bytes
after fresh identity/layout checks instead of rebuilding or rendering again.


### r100: qualify the actual corrected pixel path before operator availability

Under owned KD_GRAPHICS, the same cached frame now passes complete10653696-byte
readback in2.062 seconds; console restoration/zero,30-second logging and health
also pass. Keep the exact comparison instead of masking the128 changed bytes
from the previous console cursor cell. This provides stronger evidence than
geometry, ioctl success or an offline renderer test alone. It still does not
prove optical scanout or unchanged pixels after KD_TEXT restoration.

The combined durable intent reserves exact frame bytes and console transition
before mutation. Ten VT/action, seven binding and five real-fork/duplex cases
cover refusal and cleanup. Cached Rust bytes and unchanged low-level writer
were reused; no build/render was needed. Ownership checks add runtime compared
with the prior0.762-second unowned failure, but this2.062-second qualified path
fits immediate-start preparation needs. Do not trade those checks for speed.
Keep all further visible-session build/staging/debugging before fresh Ready.


### r101: prepare visible sessions fully; make brightness phases explicit

The fully staged visible successor reuses r100's exact cached-frame writer and
qualified console cleanup. Setup keeps brightness0; only a callback after
verified pixel readback opens the fixed32/1023 lighting phase. Cache restore and
display must use the same Frame module instance. Forty-second target supervision
bounds the20-second display; stale Ready and failed/missing prompt events refuse.

All47 focused cases passed. Actual cache/layout/console preflight took0.276 s;
local launch validation0.004 s. No live preparation window is held open for the
operator. Stage, discover and validate before asking Ready; only brief health,
logger arming and prepared execution follow it. Preserve every old entry.

A repeated test-context mistake was caught before phone staging: the display
fixture requires root-mapped execution, while host lifecycle tests require the
normal user. Added a five-suite runner with an explicit namespace per suite and
checked its --plan output. Keep production UID checks. Avoid inherited test
repetition and rerunning the unchanged real20-second timer after only a new
phase-entry callback. Initial failed fixture evidence remains in validation-r1.


### r102: reuse exact inputs and inspect firmware placement before GPU activation

The existing display/GPU proposal already matches the current OLED profile's
DTB hash. Rechecking its exact delta and retained source hashes avoids another
DT build. A0.502-second bounded streaming pass over the exact packaged initramfs
found the three locally retained A660 firmware files absent from all726 members.
Do not infer live firmware availability from local recovery or absence from one
archive; carry exact install paths/hashes into a separate qualified successor.
The existing47-case visible preparation remains frozen and awaiting fresh Ready.
Use selected JSON fields for large composition profiles and filename globs for
board searches, avoiding broad matches on the project's own rog-prefixed path.

### r103: retain immediate execution and retire consumed Ready launches

The fully prepared test reached the visible receipt in 4.926 s after Ready,
without a build, render or staging step. Frame readback took 1.453 s; the brightness
interval was 20.008 s; total including a complete 90-second log and health was
94.148 s. Cleanup and health passed with no new kernel messages. Keep setup ahead
of Ready; subsequent logging needs no continued operator presence.

Prominently retire a consumed launch in the latest state and checkpoint as soon
as it finishes; older historical waiting paragraphs must not trigger another run.
Command success and an issued observation prompt do not prove optical scanout.
Keep the raw result immutable and attach the actual user's response by visibility
receipt hash. Exact UI prompt delivery time was not recorded by the messaging tool;
do not present the measured command-receipt latency as measured UI latency.

### r104: firmware packages need an actual early-root lookup map

Twin1.66 MB firmware components took0.028 s; independent extraction/inventory
and six refusal cases passed in0.062 s. A0.484-second exact-archive audit found
lib and usr/lib are separate directories in this early root. The matching kernel
searches /lib/firmware. Preserve canonical component usr/lib paths, but explicitly
map its three firmware files to lib/firmware during newc composition. Never infer
an Arch-style lib symlink in a custom early root. Preserve the Wi-Fi custom path
and use the existing standard fallback. Reuse the retained bytes, existing DT
candidate and built GPUCC module; firmware packaging is not hardware acceptance.

### r105: firmware must survive switch_root; Ready should lead directly to viewing

The r104 early-root map was insufficient for the final Arch namespace. A0.383 s
read-only transport showed firmware_class.path=/run/rog5-native-wifi/firmware;
standard /lib/firmware is absent after switch_root. Reuse the existing preserved
firmware tree and its catalog, avoiding an init change or Wi-Fi path override.
Twin composition took4.811/7.005 s, each peaking at336.1 MiB under512 MiB/no-swap
limits. Verify generated scratch against retained archives, then reclaim it;
this run freed420444688 bytes without deleting old project data.

The user missed the20-second optical window despite the4.926 s command receipt.
That proves no screen outcome. Store the exact missed-window reply separately
from the successful command record. Prepare a longer bounded successor and give
viewing instructions before Ready so attention can stay on the phone. A fresh
Ready alone must not retrigger an already-consumed session.

### r106: bound dirty-file accumulation and reuse completed wrapper stages

The first wrapper job hit its512 MiB cgroup ceiling after9.525 s. Kernel evidence
showed405987328 dirty-file bytes versus110166016 anonymous bytes. Treat this as
measured writeback pressure, not a guessed Python heap leak or system-wide OOM.
Preserve the failed run and inspect completed artifacts before resuming. The
signed side A bundle, recovery and canonical sizing raw were reusable after
exact verification; its incomplete repack temporary was excluded.

The continuation flushes generated regular files and releases clean pages between
stages, while avoiding a second raw-image build. All header arguments, extracted
payloads, signatures, footers and twin hashes still pass. It completed in48.865 s
under the same512 MiB/no-swap limit; writeback took5.775 s. Peak still touched the
cap, so retain bounded serial execution and do not claim universal resolution.
Continue from the verified wrapper instead of repeating completed signing/builds.

### r107: separate exact firmware inventories; prepare ignored prerequisites first

The new GPU files share the retained firmware directory with Wi-Fi. Preserve the
six-file radio inventory and require a registered profile plus exact metadata/
content for all three A660 files before excluding them from radio enumeration.
Unknown extra files must still fail. Pass the same profile into the VM fixture;
registration and file verification do not prove Qualcomm firmware execution.

Fresh worktrees omit ignored boot tools/template inputs. Stage their already-known
pins before the dependent tests, not after predictable missing-file failures.
Historical profiles can acquire real claims; an offline-routing fixture should
isolate its in-memory registry and assert restoration instead of assuming a
permanently unclaimed production profile.78 focused cases and actual A01 passed.
A01 took82.835 s, reusing unchanged builds and the VM fixture; before/after sparse
logical hashes prove both retained roots unchanged. Preserve the frozen integration
source and completed result for the next admission rather than repeating them.

### r108: bind the source transition to the actual running kernel

The old boot controller assumed V11, while fresh1.777 s health proved the phone
is still on the OLED kernel after11842.52 s. Read and pin its actual shutdown,
selection and helper before adapting transition code. Here the shutdown matches
retained source exactly and the reboot helper already exists with its expected
hash; only the final reboot dispatch needs a prepared variant. Preserve teardown
and poweroff byte-for-byte. Do not copy V11 unit/state assumptions into this trial.

Reuse the installed ARM64 selector/function fixture to test the new record bytes.
Four cases took0.443 s and preserved both GPU records while selecting V11. This
is useful fallback-decision evidence, not a physical recovery pass.46 focused
cases passed, including a90 s fastboot timeout with sealed-descriptor closure.
The expected claim registry gained one entry with all228 old entries unchanged;
registration alone is not admission or durable consumption. Keep the next work
on live state/capture orchestration, not unchanged builds or another A01 run.

### r109: reuse the exchange algorithm and discover source service states

Exact current-source records and a new transaction namespace were sufficient for
this Rust helper; source review proves the atomic exchange algorithm unchanged.
Two added tests preserve all three prior namespaces and refuse an old OLED pending
state.16 native tests, Clippy and ARM64 interoperability passed. Retain the fixed
ARM64 flag checks/static-PIE linker; twins took1.012/1.029 s without a kernel build.

Read current service states before adapting the V11 controls. The OLED healthy
service is active/exited, its boot rollback timer is loaded/inactive, and the probe
timer is absent. The exact observed states now drive the source-action checks;
a running healthy writer still refuses.38 guard cases and21 action cases passed,
with separate input-refusal tests. Offline QEMU shell qualification cost121.496 s
and329.853 s versus1.127 s for actual read-only preflight; these are different
execution environments, not evidence that phone IO is slow. Reuse the finished
qualification when inputs are unchanged and focus later checks on changed code.

RAM staging and before/after health completed in6.220 s. Preserve its consumed
entry and exact namespace/custody rather than copying or staging another helper.
No selection/shutdown exchange or reboot ran. Complete recording/recovery
orchestration before admission; isolated fallback decisions and file-operation
fixtures still do not prove physical GPU initialization or fallback boot.

### r110: reuse the proven drain fix and validate the whole binding interface

Reuse r93's retained background-drain fix instead of recreating it. The GPU
adaptation adds a 1 ms inter-read yield and keeps the 8 MiB stream, 16 KiB line,
65,536-byte stderr and original lifetime/cleanup bounds. The burst regression
and complete 22-case supervisor suite pass in 19.355 s. A prior timing failure
has no established cause; do not claim the yield proves a root-cause diagnosis.

A narrow common-module shim omitted PHASES and then the full controller interface.
Use the actual identity-adapted engine, check the complete interface cheaply, then
run the real capture integration. Bind the new relay config to the already-sealed
GPU profile and reject the prior OLED config. Fixtures need their own relay address
and CAP_NET_ADMIN inside the disposable user/network namespace; host networking
must remain untouched. A test's retained-file path also needs inspection before
execution. All 72 cases now pass. Preserve these results and move to root bridge,
target health and GPU initialization preparation; no unchanged kernel/A01 rebuild.

### r111: bind reused process controls and extend runtime health before boot

Keep the tested bridge algorithm and change only fixed identities and producer
pins. Its 16 ownership/guardian cases and three stream integration cases passed
on their first runs in 8.343/4.225 s. The r110 capture components stayed unchanged.
Inspect the complete interface and actual fixture paths first, carrying forward
r110's lesson instead of discovering those prerequisites through failed suites.

GPU health now requires the three retained A660 firmware files as well as the
nine existing runtime files. Compare them to the final candidate inventory and
keep the actual collector/validator unchanged; reject old OLED identity and
missing/changed/unsafe firmware metadata. All 24 cases passed in 0.465 s. This
still does not authenticate firmware execution or initialize the GPU. Fresh
current-source health took 1.778 s on the same boot. Reuse completed builds/A01
and these component results while completing the live driver and bounded GPU
session; a new component pass alone is not a boot-admission or hardware pass.

### r112: keep installed inventory provenance separate from the current trial

The installed V9/V11 catalog was verified against its original healthy record.
Do not substitute the GPU trial's OLD record into that historical inventory check.
Keep the catalog origin pinned while adapting current transaction/owner tokens;
comparison proves all 11 installed entries and boot_b hash unchanged. The 11 ARM64
observer cases pass in 60.968 s; 33 parser replays take 0.064 s. Treat synthetic
installed-image/physical data as fixtures, not physical recovery acceptance.

Use the consumed GPU RAM-stage preparation and stage receipts directly. Their
actual metadata is 0600, with exact content hashes and custody, so no new copy or
restaging is necessary. Three new refusals prove changed or writable custody data
cannot reach command intent/transport. The seven callbacks pass 27 retained cases;
health integration passes 26 more. All suites passed on first execution after
checking dependencies/fixture paths. Keep these results and move to source-abort/
transport/driver integration instead of repeating unchanged kernel or A01 work.

### r113: bind source-read transport provenance and migrate every fixture path

Source-read callbacks checked raw output but lacked the normal-mode/exact-source/
command-invocation checks already used by health reads. They now apply those
checks before accepting evidence; nine focused cases pass in 2.219 s. Actual
read-only source preflight passed in 1.762 s with the original shutdown, absent
GPU transaction and intact staged custody. No live mutation or boot was needed.

Two fastboot cases still referenced historical r2 fixture output. Corrected that
single path to the completed GPU r1 observer and reran only those two cases;
the other 26 passes and initial failure logs are preserved. Inspect all retained
evidence paths in copied suites before execution, not just imports/top-level
constants. No production fastboot check changed. The GPU RAM binding uses
its own gpu_preservation nonce, not the prior startup profile field. Nineteen
RAM-transfer cases pass in 4.677 s. Keep completed 67.488 s ARM64 reconciliation
and other component evidence; move to route/transport/driver assembly, with no
unchanged kernel build or A01 repeat.

### r114: validate concrete interfaces before reusing controller components

The capture and health receipt adapters deliberately have no output directory;
they read explicit receipt paths. The assembled GPU driver checks real writers,
including the capture controller, without adding fake fields to frozen adapters.
A cheap import/interface check passed before the 14 integration cases (11.791 s).
Those cases include rejecting divergent nested/capture writer paths. Apply this
interface check when connecting the remaining admission/launcher components.

The route generator is byte-identical to the qualified version. Reused its
file-reading boundary results and ran one new ARM64 GPU observer-composition
case (17.233 s), plus 15 host cases. Exact source/mode/invocation checks reject
three malformed transport envelopes before accepting a route receipt. The real
read-only phone check took 7.843 s. All 65 new cases passed; no expensive build or
unchanged A01 rerun. Continue kernel bring-up through admission and bounded GPU
initialization; more offline preparation alone is not GPU hardware acceptance.

### r115: bind the actual predecessor outcome without upgrading failed evidence

The previous OLED trial failed at capture closure even though its RAM boot and
current-phone health passed. GPU source preparation now pins that exact failure,
checks controller/worker/launcher disappearance and stopped credentials, then
verifies the actual GPU RAM-stage transport and custody. It does not require or
fabricate a successful old recorder result. Twenty-three preparation cases pass
in 2.170 s. Reuse the retained credential helpers and actual receipt modes.

Cheap interface checks preceded integration; all 92 new cases passed first run.
The four complete flows took 27.880 s with explicit clock fixtures while retaining
production lifetimes. Root-entry tests exercise the actual admission policy at
the caller boundary and reject changed/completed requests. Kernel/GPU hardware
remains the priority: next prepare first-open supervision rather than extending
unrelated boot process work or repeating unchanged builds/physical observations.

### r116: derive GPU discovery from DRM mode and actual platform ancestry

The kernel defaults to shared GPU/display DRM. Do not assume that loading GPUCC
alone creates an independent Adreno render device. The current phone reports
separate_gpu_kms=N and renderD128 under ae01000.display-controller/msm_dpu,
not the display-subsystem parent. The prepared GPU test now loads GPUCC followed
by the already-qualified REFGEN/panel pair and blanking before one GPU open.

A broad read-only inventory failed on connector entries: their device link points
to a DRM card, not its platform device. Keep that failed observation; filter exact
card/render entries for platform ancestry. The corrected read took 0.361 s, and
a connector regression passes. Continue using actual input/output discovery before
live tests. Preserve detailed component cleanup exceptions through outer wrappers;
the added regression passed in 0.165 s. Reuse binaries and unchanged primitives,
then finish session supervision rather than repeating unchanged builds.

### r117: test the actual GPU supervision boundary and admit mutations explicitly

Reusing seven unchanged process/serialization functions reduced new supervision
work. All 56 checks passed in 7.934 s without repeating a build or phone read.
Two composed cases exercised the actual initializer, supervisor and host loop,
including a real query child and ordered progress acknowledgements. Keep hardware
fixtures explicit; a passing transport cannot establish GPU operation. The current
boot controller has only a read-only post-capture health phase. GPU insertion/open
must receive explicit hardware-action admission and recovery ownership, rather
than being added as a hidden side effect of that health callback.

### r118: retain one controller across boot and GPU recovery

The completed boot controller can retain ownership while a separately recorded
GPU hardware session runs. Keeping its credential scope and recovery bridge alive
avoids replacing22 qualified phase bindings or hiding mutations in health checks.
The actual recovery handoff passed in17.814 s with retained explicit external
fixtures and real capture processes; original boot evidence remained unchanged.
A healthy surviving target with verified cleanup does not turn a failed query
into success. A hard hang remains unproven recovery.

Create admission receipts with mode0600 using the existing exclusive writer.
The new lock defaulted to0644 and was correctly refused in two checks before any
phone action. After mode correction, only those affected cases needed rechecking
(2.169 s and2.069 s). Previous sources and failed logs are retained; final sealed
qualification includes the corrected state. Next advance to the autonomous phone
trial rather than extending already-qualified offline infrastructure.

### r119: finish launch preparation before requesting local authentication

One noninteractive sudo check confirmed the timestamp has expired. Prepare the
exact pending claim, launcher, current physical preflight and local touch display
before asking Ready; keep the password window closed until fresh availability.
The prepared launcher owns both authentication and later refreshes. A timestamp
from another process is not a substitute. All341 old claim records were verified
unchanged, and the phone preflight passed in9.442 s without mutation. No repeat
build, test suite or unchanged sudo attempt was needed.

### r122: exercise the generated collector against the actual largest artifact

The GPU trial reached authenticated SSH, then health collection failed before
GPU initialization. The reused binary reader capped files at131072 bytes, while
the sealed A660 ZAP firmware contains1054648 bytes. Synthetic health snapshots
and digest-negative cases had not executed that collector against real firmware.
The original generated reader reproduces the live failure on the packaged file.
The separate candidate uses exact sealed sizes, a2 MiB ceiling and64 KiB streaming
reads, preserving marker limits, no-follow traversal, metadata stability and
digest checks. Its35 focused checks pass in0.199 s. Include real largest-artifact
reads in collector qualification before another expensive phone cycle; errors
should identify the path and boundary. Do not relax an executing run's pins or
reinterpret its failure after fixing a reader.

Local touch authentication succeeded and the original credential keeper refreshed
sudo throughout capture without retaining the password. Routine SSH checks over
an existing exact route require no host sudo. Prefer those checks and a separately
admitted live module session on a verified surviving boot to another build/reboot.
The user's request to reduce password prompts does not require saving a password
in chat, project files or scripts. A future persistent privileged helper needs a
reviewed, narrowly scoped installation; no sudoers change was made in this run.


### r123: inspect current device links before assuming a late module will retry consumers

The live GPUCC-to-SMMU link is dormant and sync-state-only after the early timeout.
Frozen driver-core code shows that this relaxed link does not request automatic
consumer probing. The provider test therefore prepares one bounded explicit SMMU
reprobe if still needed after GPUCC binds, without opening DRM or rebuilding the
kernel. GMU is initialized through a6xx_gmu_init; an unbound platform entry alone
must not become an invented prerequisite. Record actual binding transitions.

Reuse retained process ownership, acknowledgement and lease algorithms while
changing the operation's explicit scope. Here nine backend primitives, four
identity/DT functions and the complete module-I/O helper remain unchanged.
Exercise the actual composed pipeline with real subprocesses and explicit kernel
fixtures. Two residual brightness fixture paths failed after conversion to a
read-only cleanup; fix both assertions and rerun only those two cases. The
production path and the other17 transport checks were unchanged. Keep all80
current checks tied to their source locks, with the failed test log retained.

Once a provider is qualified on the running boot, later sessions must inherit
that fact instead of replaying the all-in-one initializer that requires the
provider to be absent. Preserve one-use entries, and reuse existing modules and
query binaries. Finish the current-boot coordinator before requesting Ready or
attempting the hardware operation; preparation is not a live qualification.

### 2026-09-12 r124 — carry provider proof into the next current-boot test

The live GPUCC/SMMU action completed in0.280 s without a rebuild, reboot or host
sudo; the explicitly retained150 s observation dominated its152.990 s session.
GPUCC binding alone did not retry the SMMU: the verified single-device reprobe
was necessary and succeeded. Future display/query work must inherit this proof
and current bindings, never replay a loader whose entry assumes GPUCC absent.
The session now uses one shared collector retaining entered/transport/snapshot
for every read-only observation. Use that actual layout when creating fixtures;
a guessed older snapshot filename prevented12 tests from even starting. Keep
edits and test invocation in separate checked steps: a failed edit followed by
an unconditional test command caused one redundant0.230 s run. All12 cases passed
in1.976 s once the fixture path was corrected; unchanged80 tests were inherited.
Normal existing-route SSH needs no host sudo. Keep host privilege setup out of
current-boot module tests that do not create network resources. A healthy target
after failure is separate from action success and does not prove fallback recovery.

### 2026-09-12 r125 — supplier binding does not prove client DMA attachment

GPUCC/SMMU provider binding passed, but GPU initialization still returned ENODEV:
GPU had no IOMMU group; GMU had group6. Verify client IOMMU attachment before
loading display modules that trigger shared DRM component binding. A supplier
that appears after deferred-probe timeout can leave an already-bound client
without DMA/IOMMU setup because of_dma_configure ignores non-defer errors.
The isolated kernel fix keeps Adreno pending until an explicitly declared IOMMU
is attached, allowing the normal bus probe to configure DMA on the next trigger.
A targeted ARM64 object compile used the existing read-only configuration and
pinned builder and finished in1.882 s; no full build was needed to check the edit.
DSI, by contrast, remained queued for missing refgen and bound automatically when
REFGEN loaded. Use the actual deferred state instead of adding generic reprobing.
Module insertion success also does not prove panel attach or cleanup: both
display modules inserted, then GPU failure removed the backlight. Preserve the
EINVAL and failed independent blank; an absent backlight is no optical-darkness
proof. All28 focused checks passed first time, but simulated hardware could not
prove the missing GPU IOMMU attachment. Carry that live dependency into preflight.


### r126: retain verified incremental inputs across a kernel-only fix

The earlier full kernel twins took about45 minutes each; the new incremental
twins took138.848 s and265.248 s, with all30 retained output identities equal.
Verified independent copies of the accepted11370-file build trees avoided a
full rebuild; no hardlinks or old execution leases were reused. Restore source
mtimes only where clean Git blobs are identical (93706 files,10.896 s), leaving
the changed Adreno file newer. The logs confirm that changed object compiled.
Preserve original artifacts read-only and include seed code/timestamp provenance
in downstream recipe pins. This is evidence of reproducible incremental builds,
not a clean-build claim. Seed verification/copying and linking remain real costs;
do not attribute every timing difference to ccache without measurement.

Reuse completed generated headers/tools for a separate immutable module kit.
Module twins took210.467 s and37.617 s; keep stable container paths and independent
outputs. The existing54-module verifier needed only successor constants changed:
all19 function bodies remain identical,23 fixture cases pass, and the actual
new selection passes. No repeated full kernel build was needed for module work.

Audit the latest qualified GPU archive before refreshing kernel payloads. Its
736 members already contain the intended OLED/startup/firmware changes; the
existing module map covers all54 identities across32 loose and37 nested copies.
Use that measured coverage to preserve unrelated payload bytes, instead of
rebuilding the historical headless-to-OLED-to-GPU composition chain. New package,
BTF registration and real-phone DMA attachment still require their own evidence.

## 2026-09-12 r127: validate configuration against the retained consumer

Payload and wrapper twins matched even though a newly generated relay nonce had
28 characters and the retained Rust relay requires 32. The producer fixture had
mirrored the incorrect length. Reject that first candidate permanently. The
corrected payload now pins a 0.500 s actual ARM64 relay parser test for both
lengths, stopping at an intentionally wrong release before transport access.
Give extracted executable test copies the mode the real consumer receives: the
first mode-0600 fixture failed without the expected parser message. Preserve that
failed evidence as well as the corrected result. Byte identity alone does not
validate runtime configuration.

A01 also spent 24.019 s before refusing missing repository candidate identity.
Move the existing identity check before large root hashing; an actual subprocess
regression now proves an unknown candidate returns without root_hashes. Register
and check small composition inputs before expensive scans and packaging wherever
possible. The corrected candidate passed all seven A01 checks in 78.989 s.

Reusing the current GPU archive avoided replaying historical payload stages.
Retained writeback draining and canonical raw-image reuse kept corrected wrapper
packaging within its existing 512 MiB bound (84.975 s, 11.408 s writeback). Do not
claim a total speedup against older partial resumes with different work. Next
priority is the new kernel's physical GPU IOMMU attachment, not more unchanged
builds or Denial work.

## 2026-09-12 r128: keep admission tests independent of live claim consumption

The inherited boot-admission test treated the real claim as unconsumed. That
assumption expires after its first hardware run. The new test injects the
unconsumed verifier result explicitly; the unchanged engine's 21 tests continue
to exercise durable entry, concurrency and crash boundaries in isolated fixtures.
Separately verify the actual predecessor remains consumed and the successor has
no durable claim before staging. Nine admission tests and five transition tests
pass without modifying real claim state.

For the successor health reader, change the exact target configuration while
preserving the nine qualified predicates/readers, including the repaired 2 MiB
firmware bound. Reuse needs artifact evidence: streaming verification checked ten
retained files against the corrected final archive in 0.564 s; two root files are
bound to frozen source and corrected A01. Tests reject the actual old-phone
snapshot. This avoids repeating kernel or A01 builds while retaining exact input
checks. Next effort belongs to live staging and GPU attachment, not more tests of
unchanged builds.

## 2026-09-12 r129: exercise the caller with its actual adapter before staging

The ARM64 helper, guards and RAM script passed, but the first controller attempt
failed before upload because its reused save function returned None where the
caller needed SHA256. Component tests did not cover that interface. The corrected
adapter returns the digest of the written receipt. A complete controller test now
uses the real writer and request parser, with mocked transport, through staging
reply and post-health validation; it also proves an existing attempt refuses
replay. Two tests passed in0.046 s, followed by real RAM-only staging in6.146 s.
The failed pre-upload attempt remains terminal and preserved under r1.

The added read-only transaction collector also initially missed imports because
the retained observer runs readers in a separate namespace. Bind imports and
reader functions explicitly instead of assuming the caller has them. The
corrected real read passed in2.359 s and preserved all source state.

Guard tests took153.257 s and RAM tests47.924 s under ARM64 emulation. Reuse them
when the generated scripts, binary and input bytes are unchanged; retest the
changed caller interface directly. The corrected r2 stage inherited those exact
components and passed real pre/post health. New-target restoration is now covered
offline, but still requires RAM helper staging and live controller admission on
that boot; a healthy experimental kernel is not automatically V11 recovery.

## 2026-09-12 r130: recover according to the observed boot identity

A failed recording may leave a healthy experimental kernel running. The prior
engine accepted only V11 after reboot, so it could not use that healthy target
for selection restoration. Add a separate authenticated target branch with exact
boot/health checks, target RAM staging and independent restoration proof; never
relax V11 identity. Eight new failure-injection cases join25 existing cases, all
passing in1.935 s. Recovery never converts the original failure to PASS. Physical
recovery remains unproven until the assembled callbacks run on the phone.

Capture logic was unchanged; update the exact image/nonce/owner bindings and
verify the dependency graph rather than rebuild kernels. Four binding,21 isolated
worker and22 real-child supervisor tests passed. Keep synthetic network/clock
evidence separate from actual hardware: the only phone action this turn was a
2.816 s read-only custody and health check. That check verifies the existing RAM
stage, not just its historical host receipt, before any future selector mutation.

## 2026-09-12: keep schema repairs separate from power-management changes

Exact Linux 7.1.4 schema validation of the compiled ROG5 DTB rejected its existing
`asus,rog-phone5`, `qcom,sm8350` root compatible because the upstream board enum
omitted ASUS. Patch 0041 adds only that enum entry. The actual root-schema check
went from a `oneOf` diagnostic to empty output against identical DTB bytes; both
commands returned zero. Always inspect schema diagnostics as well as exit status.
The final 15-patch production series applied to the exact base and resolved the
same config in 58.799 seconds. Reuse compiled artifacts for a metadata-only schema
repair; the prior cold kernel build took 4457.016 seconds.

The remaining RPMh RSC `power-domains` requirement is a separate unresolved
binding/power-management issue. The board deletes that reference together with
CPU domain references while disabling `ARM_PSCI_CPUIDLE_DOMAIN` (introduced by
b1bbf51a2e8296f758e9c3a65bcc5b3e0e66d988). Restoring `cluster_pd` alone would refer
to a provider that is not built: platform probing attaches the domain before the
RPMh driver can select its existing CPU_PM fallback. Do not restore that reference,
enable the provider, or relax the generic binding merely to silence validation.
The historical ASUS OSI reset explanation is recorded source history, not a newly
observed firmware trace and not evidence explaining S06. Qualifying a board-specific
CPU_PM fallback description or a safe PSCI domain topology remains separate work.

## 2026-09-12: validate composed DTs and transient procfs reads

The standalone production DT compiled and passed schema checks but lacked the
exported labels required by its overlays. A board-specific `-@` flag fixes
composition without changing existing hardware properties. The combined display,
GPU and inert-touch DT exposed two errors missed by the earlier panel-only
schema filter: unsupported TLMM `input-enable` properties and an undocumented
private touch compatible. Exact pinctrl code proves `output-disable` preserves
the OE=0 effect. Full-schema preparation took 70.795 seconds and composition
12.119 seconds; no Image or module rebuild was needed. Keep combined validation
mandatory and validate every expected property, including disabled devices: the
DT validator CLI suppresses some missing-required-property errors on disabled
nodes. Direct schema-library fixtures and exact composition checks cover those.

The first integrated run stopped after 19.356 seconds because its cleanup test
checked `/proc/PID/stat` existence before reading it. Reaping can produce either
ENOENT before open or ESRCH while reading an opened procfs file. Read once and
accept only those disappearance errors or a zombie state; still reject a live
child and permission failures. The first focused correction exposed ESRCH and
remains recorded. The final thirteen-case fixture passes in 0.610 seconds, with
deterministic coverage of both errors and the rejection cases. This changes
only the test observation, not process termination or production deadlines.

## 2026-09-12: regulator failure does not identify remaining ownership

The earlier touch fixture made every regulator failure retain its child vote.
Actual Linux 7.1.4 accounting disproves that assumption: a parent-disable error
can follow consumption of the child vote, while enable unwind can silently fail
to release the parent. The new test compiles the real core and driver callbacks;
five fault cases fail against the old driver while its normal cycles pass.
Use an explicit uncertain state and stop ambiguous retries. This limits damage
within the consumer lifetime; it does not establish rail recovery or survive a
new probe. Preserve those limitations in the trial's abort/cleanup requirements.

For vendor evidence, inspect root selectors and source composition before trusting
a DT filename. Mode thresholds are not load measurements. Missing upstream-supply
properties in stock data do not justify inventing a mainline parent connection.

## 2026-09-12: share real regulator accounting tests across panel and touch

The panel's boolean supply tracking had the same demonstrated child/parent error
ambiguity as touch. Reuse the four exact core functions in both suites, while
retaining separate actual-driver/DRM tests for initialization, DSI and brightness.
The new panel regression rejects the old patch in 0.282 seconds; frozen source
passes both suites. Complete production preparation took 59.630 seconds and the
affected module twins took 2.962/2.811 seconds, avoiding another cold Image build.

Private build preparation initially confused retained Python with PATH-selected
Python, then missed generated module-common dependencies in its pre-build input
inventory. Distinguish verified historical tools from actual command resolution
and include generated control inputs before freezing a twin run. Preserve the
failed receipts; neither failure demonstrated a kernel defect. Reuse the existing
production module-closure checker: an ad hoc comparison falsely treated hyphenated
dependency names as missing underscore-named modules. The existing checker also
checks actual modules.dep coverage and cycles. No duplicate validator was added.

## 2026-09-12: restore failed suspend before returning its error

Linux only schedules a device's resume callback after its suspend callback
succeeds. A consumer that drains IRQ and powers down before a suspend error
must restore inside that failed callback, or explicitly remain quiesced for
recovery. Touch restores only after both votes are known released and preserves
the original error; UNKNOWN never triggers a retry. Test the actual PM table:
the generic sleep macro also maps hibernation, which this prototype refuses.

The unchanged module builder produced matching twins in 2.610/2.560 seconds;
the applicable active tier passed in 109.009 seconds. Use the specific module's
consumed dependencies when checking a retained kit against fresh source. An
unrelated changed panel body initially rejected touch preflight before make;
scoping that comparison correctly preserved the refusal and avoided rebuilding
unchanged Image/DT outputs. Source-only sleep support does not qualify a wake
source, physical provider retention or measured idle drain.

Keep the retained kit's original qualification series separate from later
incremental qualification and current source series. A matching consumed-header
comparison is narrower than a complete kit rebuild; preserve each original
compiled/final patch distinction in its producing receipt.

### Offline GLES preparation: distinguish a query, submission and rendered pixels

The existing GPU query and empty Vulkan submission did not check shader output.
The new readback component exercises real software Mesa with no DRI device and
rejects a no-draw mutation; 25 ABI faults separately check failure and cleanup
paths. Keep these proof scopes separate from A660, scanout and DMA-BUF/fence
qualification. A renderer string is a filter, not device admission authority.
The cached Rust builder compiled each ARM64 twin in about one second; this
userspace change needed no kernel rebuild or new candidate. Namespace tests
stay serialized with explicit per-probe and suite deadlines. Preserve raw
per-test timings and capture an outer monotonic timer when wall time matters;
a sum of parallel test durations is not elapsed integration time.

The ARM64 follow-up ran the retained probe against signed Arch Mesa packages:
software readback took 1.016 s, while package transfer dominated preparation.
Preserve partial downloads for bounded resume, but require the final pinned hash
and signature. Check the target loader before a fault matrix: missing libgcc
caused 33 derivative assertions in the first fixture. Preserve source executable
modes when extracting with debugfs; its dump defaults made a direct loader check
fail. Detect ASCII public keyrings and dearmor them in private scratch. These
were preparer failures, not phone or renderer failures; their original results
remain retained. Keep a newer software fixture separate from an unchanged mobile
package graph when an older pinned archive is no longer on checked mirrors.

Check a renderer probe against the selected compositor's minimum API, not only
whether its simple shader runs. Pinned Denial needs GLES 3.2 or 3.0; requesting
GLES 2 left that prerequisite untested. The corrected probe checks the actual
version, with the fallback exercised by real ARM64 softpipe (3.2 refused,
3.0 requested, 3.1 returned). Reuse verified library bytes but create a new binding
for a changed executable; do not inherit an old lock's probe-specific results.
The active-tier wrapper now captures outer wall time as well as per-test timings.

Native fence readiness is not successful GPU completion: the pinned sync-file
poll path reports signaled fences, while the info ioctl distinguishes status 1
from negative completion. Check both, retain one deadline across interrupted
polls, and close the exported FD on every error path. Native and ARM64 eventfd
fixtures verify polling/ownership with controlled EGL/ioctl boundaries; they do
not prove native GPU fences. Both real software renderers lack the native-fence
extension, so preserve those capability blockers separately from passing ABI
checks. No CPU/ordinary-EGL-fence fallback should silently satisfy Denial's native
export requirement.

Native-fence consumer preparation (2026-09-12): importing/waiting in a second
context adds a cleanup constraint: after failed restoration, never issue producer
GL object deletions in the consumer context. Track successful current-context
state and let EGL teardown reclaim objects on that failure path. The executable
fault test now covers this, imported-FD ownership and descriptor exhaustion.
The 10-group focused run took 6.812 s; ARM64 fixtures 6.472 s, with unchanged
real-software extension blockers. Reuse the cached builder and library identities,
but generate new execution evidence for each binary. A private verifier initially
assumed regular-file metadata for symlinks; check the recorded entry type first
and make successful verification a dependency of subsequent runtime execution.

DMA-BUF preparation (2026-09-12): MESA export query can write four modifier
entries before the caller knows the plane count. Reserve the API's maximum,
then validate the selected one-plane layout. Preserve source-image contents
explicitly and distinguish borrowed DMA-BUF import FDs from transferred native
fence FDs. FD-backed pixel fixtures and missing-draw/binding mutations now test
these boundaries. Real texture/FBO pixels pass independently; software export
extension absence remains BLOCKED. A fixture formatting error stopped -Werror
compilation before tests and was corrected. The expanded focused suite took
9.786 s and frozen active tier 118.638 s; cached component builds avoided an
unrelated kernel rebuild. Texture-only test mutations now explicitly label
DMA-BUF NOT RUN so their diagnostic output cannot be mistaken for sharing proof.

GBM preparation (2026-09-12): successful gbm_create_device does not validate that
an FD is a usable DRM render descriptor. Both real runtimes accepted /dev/null
until allocation; a bounded DRM_VERSION/driver check now refuses it before GBM
backend setup. Exact render-node/device admission still belongs to the external
coordinator. The initial failure is preserved. Final native/ARM64 refusals took
0.024/0.487 s; nine target fixture groups 8.668 s and active tier 119.335 s.
The source correction justified fresh component builds; no unchanged kernel
build was repeated. Lifetime tests now require EGL teardown before BO/device
teardown and keep the borrowed descriptor alive through the latter.

Cross-context pixels (2026-09-12): completion of a fence-only test does not check
buffer visibility. The combined fixture now delays BO bytes until server wait;
omitting that call loses pixels on native and ARM64. Resource lists are drained
for consumer-owned GL objects while that context is current, before restoration.
Split behavior from mutation compilation so ARM64 can reuse the same cases on
its retained executable. The target behavior suite took 9.306 s; the additional
negative target build 1.518 s and execution 0.052 s; active tier 129.924 s.
No unchanged kernel rebuild was needed. Real unsignaled GPU dependencies remain
unproven even if a future small-buffer hardware test passes.


Mobile payload preparation (2026-09-12): restrictive extraction permissions can
make legitimate execute-only package helpers unreadable to the host evidence
hasher. The real 315-package run failed at that boundary in 81.803 s; a tiny
execute-only fixture reproduces it. Normalize permissions explicitly for test-only
trees and record the distinction from installation semantics. The corrected
assembly took 81.434 s and focused regressions 0.435 s. Mount test executables
under an existing writable scratch mount when the payload root is read-only.
A zero exit from Mousepad --version did not imply clean initialization: it logged
missing GSettings schemas. Strict cache generation plus a stderr check closed
that narrower issue in 0.530 s, without package hooks or session claims. Reuse the
exact native binaries and authenticated libraries; no unchanged kernel rebuild
was needed. The active tier took 125.816 s. Compare complete file/link manifests
before reclaiming failed duplicate extraction scratch; retained receipts plus an
identical durable tree preserved evidence while recovering about 1.5 GiB.
