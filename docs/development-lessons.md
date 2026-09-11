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

### R1. Duplicated candidate identity and policy

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
