# ROG Phone 5 Linux Development Lessons

Status: active prevention guide  
Audit source: main Codex chat and its recorded project results through 2026-08-20 04:14 UTC  
Intended repository location: `docs/development-lessons.md`

## Why this file exists

The project has made real low-level progress, but several expensive live-device cycles were lost to repeatable integration and process defects rather than new kernel or hardware limitations. This file records those patterns and converts them into lightweight rules.

Use this document before creating a candidate, before starting an expensive build, and before every phone cycle. Update it only when a failure reveals a reusable lesson. It is not a chronological diary and must not become another large status document.

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

Observed pattern:

- A normal systemd/SSH profile was paired with a diagnostic reporter-bearing initramfs; the verifier correctly rejected the composition late in the build.
- The live bundle store still exposed an old charging-rescue payload.
- The bundle store was a read-only bind mount, so replacing files did not change the served source.
- The fallback NetworkManager profile retained `autoconnect=no` from an earlier repair period.
- Installed target-side gates did not initially contain a profile already accepted by host tooling.

Cost:

- Builds and live preflights operated on stale or incoherent installed state even when repository source was correct.

Prevention:

- Admission must inspect the exact served bundle, installed controller, initramfs contents, and wrapper bytes—not repository source alone.
- Record a single deployment receipt containing hashes for the wrapper, bundle, manifest, trust key, controller, network profile, and bind-mount source.
- Connected preflight must compare that receipt with the currently installed and served bytes.
- Candidate assembly must be atomic: build in a fresh directory, verify, then switch one pointer/bind source.

Rule: **The object admitted for a phone cycle is the installed byte composition, never merely the Git commit that was intended to produce it.**

### R3. Exact recovery capabilities were assumed

Observed pattern:

- Alpine lacked `findmnt`; a pre-transfer check failed on the live fallback.
- The Alpine fallback kernel lacked `CONFIG_KEXEC`; `kexec_load` returned `ENOSYS` after transfer.
- BusyBox rejected shell syntax that worked on the host.
- Tools such as `/usr/bin/time` and command options such as `cmp -r` were assumed to exist on the build host.
- ACM tooling required a canonical sysfs location while a short USB path was supplied.

Cost:

- Live cycles and build attempts were spent discovering basic capability mismatches.

Prevention:

- Generate a capability manifest from each exact fallback/recovery artifact: kernel config, syscalls, binaries, BusyBox applets, accepted command options, filesystems, and device paths.
- Test scripts against the extracted exact initramfs/rootfs with its shell and utilities.
- Use POSIX/BusyBox-compatible commands in recovery unless a packaged binary is explicitly verified.
- Preflight every required capability before transfer or candidate consumption.

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
- Build from an immutable source snapshot. Never edit files used by an active build.
- Keep each candidate in a fresh output directory and never reuse partial outputs.

Rule: **A live cycle starts from a declared host-state receipt, and an expensive build reads an immutable source snapshot.**

### R7. Live cycles discovered host-only parser and normalization bugs

Observed pattern:

- ADB exposed a short USB key while the lifecycle compared it to a canonical full sysfs path.
- Firewalld returned canonical text `no zone`, but the parser treated the embedded space as a malformed zone.
- The target correctly reported `root=local-ext4-overlay-tmpfs`, while the host expected only `root=overlay-tmpfs`.
- The runtime collector rejected a valid new candidate name after target SSH was already working.
- A storage collector attached after the target had already started raw GPT streaming, so binary payload bytes were parsed as an overlong framed line before ACK.
- Sending host readiness immediately after ACM open raced target initialization and produced an exact target-side readiness mismatch.

Cost:

- v1, v2, and v3 power-observer wrappers were consumed or abandoned for host-control defects rather than kernel defects.

Prevention:

- Preserve real command outputs and lifecycle transcripts as sanitized regression fixtures.
- Replay every parser, path normalizer, and state transition against those fixtures before a new wrapper is issued.
- Test canonical, short, missing, whitespace-containing, delayed, duplicated, and stale forms.
- Run the whole controller with fake fastboot/ADB/NCM/firewalld/NetworkManager endpoints through PREPARE, COMMIT, target SSH, and fallback.
- For mixed framed/binary transports, require an exact operation-bound host-ready record before the target emits the first binary byte.
- Order the rendezvous in both directions: parse the exact target-ready stage before sending host-ready.

Rule: **A new phone-observed string or state transition must become a replay fixture before the successor candidate is built.**

### R8. Rollback and COMMIT semantics were occasionally over-assumed

Observed pattern:

- After COMMIT returned `CLAIMED`, STATUS timed out and the outcome was unknown.
- A userspace rollback timer did not restore the phone after the control plane froze.
- Review later clarified that successful kexec destroys the old userspace timer, so absence of rollback did not prove the old kernel was still running.
- Logging before emergency reset could itself delay the reset path.

Cost:

- A consumed attempt produced ambiguous evidence and required physical intervention.

Prevention:

- Define protocol states explicitly: accepted, prepared, commit-received, execution-started, target-alive, rollback-started, fallback-proven.
- Make COMMIT idempotency and outcome recovery explicit; never equate an ACK with target execution.
- Keep rollback at a level that survives the transition being tested, or use an independent hardware/bootloader watchdog.
- Emergency reset paths must perform the reset before optional logging.
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
9. Remote exact-head CI.
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
- Explicit authorization immediately before destructive storage changes.
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
- [ ] Candidate and wrapper have never been used.
- [ ] Failure classification and rollback behavior are known for every stage.
- [ ] No phone-side write occurs unless that write is the explicit purpose of this cycle.

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

For each successor candidate, the main chat should report only:

1. The single hypothesis being tested.
2. The cheapest test that could disprove it.
3. Which failure class from this file is relevant.
4. Why a new build or phone cycle is necessary.
5. The exact pass/fail evidence after the cycle.
6. The regression or systemic change added before any successor.

If the failure is host-only, do not redesign the kernel. If it is a new hardware observation, preserve the raw evidence and turn it into a replay fixture. If the same failure class recurs, fix the process or source of truth before issuing another candidate.
