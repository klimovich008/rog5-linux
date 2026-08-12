# Active development context

Use this page to resume current work. It intentionally links to detailed
contracts and evidence instead of repeating their history.

## Objective

Turn the ASUS ROG Phone 5 into a dedicated, persistent Arch Linux server.
The temporary Linux 7.1.4/NFS/USB-NCM/key-only-SSH path is proven. The current
critical path is stable mainline UFS, a faster local Arch root inside one
bounded `userdata` image, and eventual dedicated Linux partitioning after
verified backups, restoration rehearsal, and final confirmation of the exact
destructive operation. Android usability is no longer a requirement.

Buttons/indicator, sensors, audio, suspend, GPU, display, desktop, and browser
automation are frozen at their current checkpoints while storage and local
boot are advanced. Kernel and recovery remain RAM-only through the bounded
image phase; NFS and exact Alpine remain recovery paths.

The operator's [standing authorization](operator-standing-authorization.md)
permits the agent to satisfy those action-scoped guards, use the admitted
project credentials, and perform other in-scope actions without asking again.
Continue until a genuine technical, safety, platform, input, or scope blocker
is reached. The operator reaffirmed this no-reprompt instruction on 2026-08-04:
routine authorization gates may be satisfied from the standing directive and
must not cause another consent pause. This latest directive supersedes stale
goal or historical gate wording that requests fresh consent; it does not relax
artifact admission, rollback, evidence, cleanup, protected-partition, or
Phase-3 final-confirmation boundaries. The bounded Phase-2 image write is now
explicitly in scope; raw storage changes are not. The operator reaffirmed the
same directive again on 2026-08-05; the standing-authorization record is the
canonical wording.

GPU, display, desktop, browser automation, hotspot, and unrelated subsystem
expansion remain frozen until local-root Arch reaches repeatable key-only SSH.

## Proven boundary

- **Storage Phase 1 passed on 2026-08-12.** A fresh read-only inventory found
  seven UFS LUNs and 109 partitions with valid primary/backup GPT CRCs and
  exact sysfs geometry. All 14 GPT metadata ranges and all 107 non-`super`,
  non-`userdata` partitions have source/host hash-matched private backups; an
  offline sparse restoration rehearsal recovered all seven GPTs and 109
  entries. UFS `sd*` names changed across boots and are forbidden as stable
  identity. See [storage migration Phase 1](storage-migration-phase1.md).

- **Generation 22 is consumed and never reusable.** Its signed bundle and
  correlated COMMIT completed, recovery USB disconnected, no `ROG5 persistent
  root` USB product ever enumerated, and exact Alpine returned 25.255 seconds
  later. The lifecycle then mislabeled that rapid return as a deferred-profile
  cleanup failure. A temporary pstore mount contained no records; that remains
  inconclusive. No target storage write occurred. See the
  [live result](../test-results/2026-08-12-generation-22-persistent-root-storage-live.md).

- **Generation 23 is consumed and never reusable.** Its sole RAM-only cycle
  completed signed transfer and COMMIT, but no target USB appeared before
  exact Alpine returned after 25.330 seconds. A measured forced-Alpine reboot
  took 18.162 seconds from disconnect to USB, leaving about 7.168 seconds for
  the mainline leg. That strongly matches the five-second invalid-command-line
  branch plus startup, but does not prove the branch. Generation 23 configured
  USB only after command-line and release checks, so it did not provide the
  intended precheck observation. No phone storage write occurred. See the
  [live result](../test-results/2026-08-12-generation-23-persistent-root-storage-live.md).

- **Generation 24 is consumed and never reusable.** Its sole RAM-only cycle
  reached signed transfer and correlated COMMIT, but no target USB appeared
  before exact Alpine returned after 25.567 seconds. Because rollback and NCM
  setup preceded command-line/release checks and all userspace UFS work, this
  disproves the Generation-23 ordering explanation and narrows the failure to
  kernel/initramfs entry or USB setup before successful binding. No phone-
  storage write occurred. See the [live result](../test-results/2026-08-12-generation-24-persistent-root-storage-live.md).

- **Generation 25 is consumed and never reusable.** Its sole RAM-only cycle
  completed signed transfer and COMMIT, but no target USB appeared before
  exact Alpine returned after 25.038 seconds. It obtained no UFS inventory and
  performed no authorized phone-storage write. The result rejects the payload
  Image as the sole explanation but does not distinguish kernel entry from
  failure before target USB setup. See the [offline](../test-results/2026-08-12-generation-25-ufs-image-control-offline.md)
  and [live](../test-results/2026-08-12-generation-25-ufs-image-control-live.md)
  results.

- **Generation 26 is consumed and never reusable.** Its sole cycle restored
  the RMTFS reservation and omitted ramoops, but no target USB appeared before
  exact Alpine returned after 25.333 seconds. No UFS inventory was obtained
  and no phone-storage write occurred.

- **Generation 27 is consumed and passed its pre-UFS discriminator.** The exact
  Generation 20 Image/DTB plus the persistent initramfs reached stable
  `ROG5 persistent root` NCM in 65.057 seconds, then the deliberate release
  mismatch returned exact Alpine. No UFS or phone-storage access occurred.
  This clears the persistent initramfs/configfs path and a payload-independent
  residual kexec state; the failure boundary is the changed target Image/DTB.

- **Generation 28 is consumed and passed its DTB cross-pair.** The live-proven
  Generation 20 Image plus Generation 25's UFS-enabled DTB reached stable
  target NCM in 59.723 seconds from lifecycle start. The deliberate release
  mismatch then returned exact Alpine. No UFS or phone-storage access occurred.
  Together with Generation 27, this clears the persistent DTB and its enabled
  nodes when no UFS driver can bind; the remaining early regression follows
  the UFS Image/config lineage.

- **Generation 29 is consumed and passed its no-storage Image control.** The
  rebuilt UFS Image from Generations 25/26 plus Generation 20's live-proven
  UFS-disabled DTB reached stable target NCM in 58.780 seconds. The expected
  no-UFS rollback then returned exact Alpine. No UFS or phone-storage access
  occurred. Together, Generations 27–29 prove the persistent initramfs,
  UFS-enabled DTB, and rebuilt Image work independently; the early regression
  requires active UFS binding or probing with that Image.

- **Generation 30 is consumed and reproduced the active-UFS early failure.**
  The retained accepted persistent-root Image plus the enabled UFS DTB never
  exposed the target USB identity before exact Alpine returned. This confirms
  that the failure is not peculiar to the reconstructed Generations 25/26
  Image. No target-side storage access was observed.

- **Generation 31 is consumed and reproduced the pre-USB failure.** Moving UFS
  core, platform glue, and the Qualcomm host driver to three sealed modules did
  not expose target NCM before exact Alpine returned. No target-side storage
  access was observed. The
  [live result](../test-results/2026-08-12-generation-31-deferred-ufs-probe-live.md)
  leaves the QMP-UFS PHY as the remaining built-in UFS-specific layer.

- **Generation 32 is consumed and cleared the pre-init USB boundary.** Moving
  `CONFIG_PHY_QCOM_QMP_UFS` from built-in to a sealed module exposed stable
  target NCM in 60.616 seconds. Target USB remained enumerated for 11.276
  seconds, then disappeared before exact Alpine returned. This proves the
  built-in QMP-UFS PHY registration/probe was inside the earlier failure
  boundary, but the four-module cycle did not identify the final transition.
  [Live result](../test-results/2026-08-12-generation-32-deferred-qmp-ufs-phy-live.md).

- **Generation 33 is consumed and narrowed the failure to QMP-UFS PHY module
  insertion or platform binding.** Target NCM disappeared 11.419 seconds after
  enumeration, before its 15-second control window completed. No UFS core,
  platform, or host module was loaded and no storage access occurred. The
  [live result](../test-results/2026-08-12-generation-33-qmp-ufs-phy-control-live.md)
  records the exact timing and observation-race correction.

- **Generation 34 is the active no-bind discriminator.** It reuses the exact
  Generation 33 Image, modules, and initramfs, but its one-property overlay
  disables only `&ufs_mem_phy`. Loading the same QMP-UFS module can therefore
  register the driver without binding or probing the platform device. The UFS
  host remains enabled but its module is absent. The cycle performs no UFS
  enumeration or storage access.

- **The temporary Arch Linux + key-only SSH MVP passed on real hardware on
  2026-08-12.** Generation 20 mounted NFSv4.2 read-only at target boot
  4.930 s, verified the sealed root at 350.038 s, reached systemd at
  359.043 s and sshd at 372.046 s, and passed strict key-only SSH/runtime
  acceptance at 379.548 s. Its reporter stayed fault-free until the intended
  watchdog rollback, then exact Alpine fallback, cleanup, and Steam socket
  restoration passed. Generation 20 is consumed, absent from boot policy, and
  never reusable. See the [live result](../test-results/2026-08-12-generation-20-arch-ssh-mvp-live.md).

- The shell-free framed recovery protocol, signed runtime bundle, one-shot
  controller, rollback, and fallback cleanup pass hardware-free tests.
- The accepted Linux 7.1.4 source, corrected DTB, and minimal Kconfig pass the
  [compatibility oracle](core-compatibility-oracle.md) and
  [source/DTB contract](core-source-dtb-contract.md). The retained real source,
  DTB, configuration, modules, buttons/indicator contract, and complete
  phone-free successor gate were
  [revalidated together](../test-results/2026-07-31-accepted-core-baseline-revalidation.md).
  The current host source/DTB pair was
  [revalidated again](../test-results/2026-08-02-core-baseline-current-host-revalidation.md)
  after storage inventory exposed a stale retained-volume reference. Local
  repository CI now discovers the canonical retained source automatically and
  fails closed on a stale, dirty, linked, or wrong-identity tree; clean GitHub
  checkouts retain the hardware-free synthetic suite without requiring the
  ignored source.
- The corrected DTB keeps UFS and USB3 isolated while preserving CPU/RAM,
  USB2/NCM, PSCI, and static thermal topology.
- A credential-clean SSH-only Arch root and fixture-key v3 package/candidate
  reproduce offline. Fixture identities can never pass deployment admission.
- The [88-field runtime gate](minimal-headless-runtime-acceptance.md) checks
  CPU/RAM, exact NFS/OverlayFS mounts, zero phone-storage exposure, USB/NCM,
  key-only SSH, thermals, and the armed rollback process.
- Local CI and GitHub Actions cover the generic QEMU boot, recovery protocol,
  candidate packaging, runtime parsers, rollback, and repository policy. The
  local full-system gate additionally executes the production-generated stage
  130/140 units under real AArch64 `systemd 260.2-2-arch`, starts OpenSSH
  10.3, accepts one disposable Ed25519 key login over loopback, executes the
  authenticated command, and rejects a keyless login.
- The board-neutral Linux 7.1.4 QEMU kernel now also includes its NFSv4.2
  and OverlayFS prerequisites and completes real TCP mounts using the exact
  `network-root-init` option string and `169.254.77.2/30` client identity.
  Ganesha's VFS backend exports a private tmpfs tree read-only with numeric
  NFSv4 ownership; the matching client disables ID mapping. The test guest
  proves that a client-requested read-write mount receives `EROFS`, retains
  the direct read-only probe, and invokes BusyBox plus the
  `mount_network_root()` function extracted verbatim from the current
  production init. That path emits stages 70, 75, 80, 90, and 100 exactly
  once, verifies the NFS lower and writable tmpfs upper, then runs the
  production `prepare_shutdown_root`, `handoff_network_root`, and
  `switch_root` sequence. The sealed ARM64 runtime reaches real systemd as
  PID 1 and real key-only OpenSSH; its terminal helper revalidates exact
  OverlayFS/NFS/tmpfs topology and proves that upper writes never reached the
  lower. The QEMU-only kernel disables NFSv4.2 `READ_PLUS`, and the fixture
  disables directory delegations, because Ganesha 4.3 does not implement
  either operation correctly for this path. One restricted TCP/2049 forward
  keeps the fixture independent of host storage. Thirty-nine hostile
  mutations cover listener isolation, server-side read-only enforcement,
  owner mapping, option drift, production handoff, sealed runtime hashes,
  live zero-block topology, terminal QEMU status, password-only rejection,
  post-switch-root topology, OverlayFS capability, and invocation drift.
  This remains hardware-free evidence only. See the
  [QEMU NFSv4.2 result](../test-results/2026-08-08-qemu-network-root-nfs-v42-offline.md).
- A compile-only Linux 7.1.4 suspend diagnostic now exposes exactly the
  `pm_test=devices` callback checkpoint with a 30-second DPM watchdog.  The
  pinned-source oracle proves return before platform/CPU/PSCI entry; the
  one-shot gate consumes before its sole state write, restores
  `pm_test=none`, and classifies post-return USB/link loss exactly.  Two clean,
  network-isolated builds are byte-identical at Image
  `93e00f68…704e0` and modules `f650f51f…99315`.  This is
  [offline evidence only](../test-results/2026-08-09-suspend-pm-test-devices-offline.md):
  no phone boot or real suspend occurred, and missing pstore lineage is never
  proof of no crash.
- The active minimal root no longer depends on the historical Python-only,
  power-only input monitor for future H4 acceptance. A guarded POSIX gate now
  covers exact power, volume-down, and volume-up identities, press/release
  pairs, bounded IRQ deltas, power/volume-up wake policy, resin non-wake
  policy, and unchanged USB/NFS/storage/kernel state. Its hostile fixture
  suite is hardware-free; no physical key has yet passed on the phone.
- The first H4 sensor source oracle is now exact. The retained ASUS 5.4
  ZS673KS chain inherits one Capella VCNL36866 on QUPv3 SE0/I2C `0x980000`,
  address `0x60`, GPIO89 active-low IRQ, and PM8350C L7 at 3.3 V through MP5.
  Its 8-bit-register/little-endian-16-bit protocol identifies register
  `0xf6` as chip ID `0x62`, with raw ALS/proximity at `0xf1`/`0xf4`.
  Accepted Linux 7.1.4 has no VCNL36866 match or binding and is classified
  `port-required`; VCNL4040 is not treated as compatible. The future
  read-only IIO contract is hostile-tested, but no driver, DT candidate,
  kernel build, phone boot, or hardware acceptance exists yet.

These facts do not prove the Generation-24 successor on the phone.

## Critical-path history

The guarded production builder's detached-checkpoint boundary is now
[corrected offline](../test-results/2026-08-10-deployment-checkpoint-input-staging-offline.md).
The old launcher entered an exact Git worktree but omitted every fixed
Git-ignored release input, so a synchronized source checkout still failed on
the absent static QEMU inside the sealed builder. Both fixed launchers now
copy only literal path/size/mode/SHA-256-pinned inputs with no-follow source
opens, no-replace destinations, streaming identity checks, fsync, and Git
state revalidation before credential use. Signing-input preflight remains
copy-free and artifact-free. Exact-head CI passed at `05c58459`.

The subsequent authorized offline production build exposed a narrower
[Android boot-tool closure defect](../test-results/2026-08-10-deployment-boot-tools-closure-offline.md):
both clean ASUS wrapper builds completed byte-identically, but release
repacking failed after 2,253 seconds because `mkbootimg.py` imports the omitted
`gki/generate_gki_certificate.py`. Both deployment allowlists and the wrapper
cache identity now bind that exact helper, and the wrapper gate rejects it
before compilation if absent or changed. The failed build published no output
and created no claim, policy row, phone action, or boot authority. The helper
closure fix passed full and exact-head CI at `223ac2d`; a fresh guarded build
then completed two byte-identical production outputs in 2,270 seconds. The
[production refreeze](../test-results/2026-08-10-production-retention-execution-refreeze-offline.md)
binds project key `f10ca076…`, recovery initramfs `ab0a3ee2…`, wrapper Image
`8a600acf…`, raw image `ea9e90fd…`, and unsigned AVB `cba4e6e8…` to the joint
execution/observer HOLD profile. Commit `adef485` and exact-head run
`31363962284` are green. Claims remain undefined, policy has zero `allow`
rows, and no phone action occurred, so admission stays **HOLD**.

The current offline increment closes the next gate-integration gap. The
stable-recovery live gate previously recognized only historical recovery
profiles and could not apply `exact-a600000-v1` with the repository-owned
current init. Its new production HOLD profile accepts only identity-only
`policy-preflight` and hardware-free `artifact-preflight`; connected preflight
and boot fail at profile selection before host, policy, USB, credential, or
fastboot inspection. The real retained production bytes pass, while a
co-varied initramfs mutation fails at the independent archive hash before the
exact-init verifier. No claim or policy row was added; the
[offline gate result](../test-results/2026-08-10-current-production-recovery-live-gate-offline.md)
does not grant phone or boot authority.

The distinct observation recovery now has the matching
[offline-only HOLD gate](../test-results/2026-08-10-current-observation-recovery-live-gate-offline.md).
It pins the current observer AVB `3c9b2820…`, all 22 verifier inputs, and the
retained verifier report, while connected preflight and boot fail before host
inspection. Hard-linked retained outputs are intentionally rejected; tests
use an independent fixed-file copy-on-write snapshot. This adds no claim,
policy row, lifecycle selector, credential, or phone action. The two exact
consumable claims and the sequence-enforcing retention runner remain
undefined, so admission stays **HOLD**.

The follow-on
[two-claim sequence reference](../test-results/2026-08-10-retention-sequence-reference-offline.md)
now defines the missing transaction semantics without creating a runnable
path. Two distinct draft record hashes bind the exact execution/observer AVBs,
candidate, manifest, and one cycle digest, but remain absent from the generic
consumer. A pure hostile-tested model enforces rollback-armed boots, exact
fallback, ramoops preflight, same-port bootloader and observer handoff, one
lineage-bound read, irreversible failure dispositions, and no retry. Its
11,923-byte source `97075ed7…` is pinned by the HOLD profile. No claim, policy
row, credential, device action, or live runner was added; admission remains
**HOLD**.

The next [offline transaction journal](../test-results/2026-08-10-retention-cycle-transaction-offline.md)
turns that pure order into one private append-only, hash-chained crash record
without adding a live entry point. It durably binds host boot ID, USB location,
target and fallback boot IDs, both claim dispositions, the exact fastboot
product/serial, both recovery intents, and the one observer-read budget.
No-follow single-link events are exclusively created and file/directory
`fsync`ed under a nonblocking cycle lock. Reopening an ambiguous action intent
permits only an inconclusive terminal record, never action retry. The profile
pins the 39,553-byte source `a7018537…`; 9 transaction and 22 joint-admission
hostile groups pass. No helper consumes the journal yet, no claim is
registered, and connected gates remain closed, so admission stays **HOLD**.

The follow-on [callback adapter fixture](../test-results/2026-08-10-retention-cycle-adapter-offline.md)
now proves six fixed helper descriptors are exposed only after the matching
fsynced journal intent: execution claim/boot, fallback reboot, observer
claim/boot, and the one correlated postmortem read. All six injected callback
failures leave the intent nonretryable; hostile results, type aliases, invalid
lineage, and callback-side journal mutation cannot advance it. The profile
pins the corrected 10,260-byte adapter `c36b4bfa…` to journal `a7018537…`;
fallback transition now names the accepted nonce-framed ACM helper rather than
the legacy SSH-key helper. Seven adapter and 25 joint-admission hostile groups
pass. The separate 14,560-byte pure executor contract `8705c7fd…` pins all six
helper identities, fixed interpreters, a parent-independent environment,
per-action allowlists, separate bounded output streams, deadlines, and
process-group cleanup. Its three boot actions request the canonical
`rog5-retention-boot-result-v1` record and carry only the reviewed fastboot
serial/USB-location lineage. It accepts one canonical unopened fallback
host-pin path and no private-key input. Neither module can execute, open
credentials, or provide a CLI; both recovery gates still reject connected
actions and draft claims/policy remain empty, so admission stays **HOLD**. See the
[executor-contract checkpoint](../test-results/2026-08-10-retention-cycle-executor-contract-offline.md).

The [pure executor-boundary checkpoint](../test-results/2026-08-10-retention-cycle-executor-boundary-offline.md)
now pins descriptor evidence for every program and interpreter plus one
caller-owned public Ed25519 fallback host-pin snapshot. Eleven hostile groups
exercise no-follow flags, descriptor/path identity, symlink-target
revalidation, owner/mode/link/content checks, bounded process outcomes, exact
claim output, canonical postmortem JSON, and one exact terminal boot-result
record. The boundary now decodes all six actions only when descriptor
attestation and every journal-required value match. The fallback helper has a
guarded producer grounded in the actual same-port fastboot serial/product and
the inspected public host-pin bytes. The selected execution and observer
profiles still have no successful producer because both remain HOLD. The
source has no process, filesystem, credential, device, CLI, or
connected-admission surface. See the
[boot-output checkpoint](../test-results/2026-08-10-retention-cycle-boot-output-contract-offline.md).

The next [offline runtime fixture](../test-results/2026-08-10-retention-cycle-runtime-closure-offline.md)
holds the real intent/program/interpreter and optional public-pin descriptors,
then proves fresh empty CLOEXEC pipes, a kernel nonce, devnull/closed-FD child
isolation, bounded streams/deadline, and process-group cleanup. Thirteen hostile
groups include all six actions in one journal, with each preparation released
only after one exact result event whose canonical data equals the fresh-pipe
decoded result and whose descriptor-relative pathname still names the held
event. The fixed writer does not invoke the held
production descriptors, so its decoded wrapper is adapter-ineligible and
production descriptor execution remains explicitly unproven. No host-pin
admission, live entry point, claim, credential, policy row, recovery-gate
wiring, or phone action was added; **HOLD** is unchanged.

The [held-descriptor execution checkpoint](../test-results/2026-08-10-retention-cycle-descriptor-execution-offline.md)
adds a separate harmless successor rather than claiming the fixed writer ran
the real helpers. Its pinned runner `fexecve`s the held Python interpreter and
runs the held probe as `/proc/self/fd/198`; canonical evidence proves exact
program/interpreter identity, argv/environment, descriptor-held cwd, `0077`
umask, devnull/FIFO plumbing, session/process group, and open FDs
`0,1,2,198`. Nine hostile groups cover path/context mutations before and after
exec, parent-FD leaks, timeout/descendant PID and pipe-EOF cleanup, overflow,
nonzero exit, proof substitution,
and malformed output. Fixture descriptor execution is proven, but all six
production helper executions, adapter wiring, claims, credentials, policy,
and phone authority remain absent; **HOLD** is unchanged.

The latest
[retention exact-claim registry checkpoint](../test-results/2026-08-10-retention-claim-registry-offline.md)
removes the last Generation-11/12 record-template assumption from the generic
one-use consumer. Its literal repository-owned lookup preserves both consumed
historical records byte-for-byte and can later represent distinct execution
and observer records without another copied consumer. No future record,
claim, policy row, signature, candidate, or lifecycle authority was added.
Final production artifact identities must precede two exact claim definitions,
and a complete sequence-enforcing retention runner still does not exist, so
admission remains **HOLD**.

The latest
[offline fallback reset-evidence checkpoint](../test-results/2026-08-10-fallback-pmic-pon-postmortem-offline.md)
adds a signed, read-only, truly byte-bounded PMIC PON summary to future
fallback postmortems. It selects only the last complete known FIFO cycle and
keeps unknown, unavailable, or ambiguous data inconclusive. The retained
ASUS 5.4.210 source proves the oracle semantics and separates the read-only
PMIC history reader from the write-only next-boot `qcom-reboot-reason`
notifier. It does not prove that the installed 5.4.134 fallback includes that
reader, and no Generation-12 reset reason exists retrospectively. No phone or
candidate action occurred; admission remains **HOLD**.

The 2026-08-09
[offline network-root readiness review](../test-results/2026-08-09-critical-network-root-readiness-review-offline.md)
reproduced the host/target readiness race window in a hardware-free ordering
model and added monotonic host transition evidence plus a bounded exact
TCP/2049 rendezvous before the sole diagnostic NFS mount. It does not establish
that this race caused Generation 12. Physical USB-NCM timing and current-cycle
pstore survival remain unproven, so candidate admission is **HOLD**. Thermal,
suspend, keys, battery, display, and sensor expansion remain frozen. The
uncommitted VCNL36866 set is preserved as an
[isolated WIP](../test-results/2026-08-09-vcnl36866-working-tree-review-offline.md),
not integrated or candidate-ready.

The final review caught and fixed one evidence-path defect: the three new
host-port terminal reasons were absent from both the native reporter and host
parser. The clean-twin reporter is now `26249252…bafa`, and the clean-twin
offline diagnostic initramfs is `94edd625…cffc`. The host model also measures
the current 50 ms address-before-drop-zone ordering window under injected
delay and fails closed on zone-transition or listener-scope faults. That
number is not a packet-exposure measurement: the unprivileged fixture does
not exercise active/default-zone packet filtering while the interface changes
zone. These are offline components only; no new candidate contract, signed
bundle, wrapper, policy row, or boot authority exists.

The follow-up
[independent-observability review](../test-results/2026-08-09-independent-observability-review-offline.md)
proves a latent SoC-side GENI debug-UART route at `0x98c000` on GPIO18/19 and
now binds that exact route in signed-DTB verification. It does **not** prove
ASUS routed those pins to USB-C or accessible pads. Ramoops transition
retention is likewise still unproven, stable recovery has no GENI console,
and the target's enabled serial Magic SysRq makes any eventual electrical
probe receive-only. No independent postmortem channel is currently claimed.

The subsequent
[recovery postmortem-lineage checkpoint](../test-results/2026-08-09-recovery-postmortem-lineage-offline.md)
closes an offline integrity gap in that latent ramoops path. The native
recovery responder now validates the complete private pstore snapshot against
its status before opening a session, recognizes the accepted target's exact
console and panic-dmesg printk prefixes, and exports only bounded marker hashes
and multiplicity. A separate read-only host action compares that hash with an
operator-supplied exact candidate/boot ID and distinguishes absent,
ambiguous, stale, unique-match, and repeated-match evidence without emitting
the reversible pstore tail. Clean-twin AArch64 responder builds and hostile
QEMU tests pass. This makes a future retained snapshot correlatable; it does
not prove that the DRAM region survives the physical transition. Admission
therefore remains **HOLD**.

The follow-on
[complete recovery refreeze](../test-results/2026-08-09-recovery-postmortem-refreeze-offline.md)
now embeds that responder in byte-identical 7,601,886-byte initramfs twins and
two clean sealed ASUS 5.4 wrappers. Kernel `4b30cfff…9495`, raw boot-v3
`5141f0d0…deab`, and unsigned AVB `b004e500…c218` reproduce exactly with the
fixed 4 MiB ramoops command line. These are ignored test artifacts with a
disposable trust input, no policy row, no candidate record, and no boot
authority. Physical transition retention is still unproven, so the critical
path remains **HOLD**.

The next recovery-control-plane hardening removes the remaining arbitrary UDC
fallback from stable recovery. The
[offline exact-UDC result](../test-results/2026-08-09-stable-recovery-exact-udc-offline.md)
accepts only one stable exact `a600000.dwc3`, revalidates it before and after
configfs binding, and hostile-tests zero, delayed, wrong, renamed, multiple,
and changing candidate sets. Twin 7,602,307-byte initramfses reproduce at
`afc55f96…d790`. They are ignored unsigned composition evidence only; no
wrapper, candidate, policy row, phone action, or boot authority exists. The
critical path remains **HOLD**.

The next
[observation-only recovery checkpoint](../test-results/2026-08-09-observation-only-recovery-offline.md)
separates future postmortem inspection from payload execution at two layers.
A packaged root-owned, mode-`0444` marker starts the responder as
`observation-only-v1`; that mode serves only `HELLO` and `STATUS`, refuses
`PREPARE` and `COMMIT_EXEC` before state or ledger mutation, and rejects a
nonpristine startup. Its byte-identical 5,371,780-byte initramfs twins
`613d6e3e…70db` contain no bundle fetcher, verifier, public trust key, kexec
binary, or bundle root. This is reproducible initramfs composition only: no
ASUS wrapper, candidate, signature, policy row, credential, phone action, or
retention result exists. Admission remains **HOLD**.

The subsequent
[fallback-transition preflight](../test-results/2026-08-09-fallback-ramoops-transition-preflight-offline.md)
closes one remaining offline choreography gap without contacting the phone.
The existing identity-pinned fallback helper now has a separate read-only
`retention-preflight` action. In addition to normal fallback health, it
requires the exact seven-parameter ramoops command line, exact two-cell
`0x9b800000 + 0x400000` reserved-memory tuple, no overlapping fixed sibling,
no visible bound ramoops consumer, and empty pstore. Ten hostile groups,
including late optional-path and exact `2^64` endpoint cases, and the complete
existing reboot-helper suite pass. The action neither requests
reboot nor accepts reboot authority. It has not been run on the phone, so
physical preservation and candidate admission remain **HOLD**.

The follow-on [two-identity retention review](../test-results/2026-08-09-retention-cycle-two-identity-review-offline.md)
now fails closed unless the exact full execution recovery and distinct
observation-only recovery form one reviewed target → fallback → bootloader →
observer sequence. It verifies their signed-bundle, initramfs, boot-v3, AVB,
ramoops, claim-consumer, and empty-policy identities without contacting the
phone. The two future claim records remain intentionally undefined and
physical retention remains unproven, so the critical path remains **HOLD**.

That review has since been
[refrozen with the Haven-aware responder](../test-results/2026-08-10-haven-retention-observer-refreeze-offline.md).
The profile now pins the repository init and a reproducible AArch64 responder
build record through exact source, builder script, image/toolchain, and output
identities, then proves that both the execution and observation archives embed
those bytes. Distinct clean-twin ASUS wrappers pass the joint verifier with
zero policy rows and no claim records. This closes an offline stale-responder
gap only; physical ramoops retention and reset cause remain unproven, so the
critical path remains **HOLD**.

## Current observability increment

Generation 10 is consumed after ACM exposed only `REQUEST_ACCEPTED` despite a
complete host-side bundle transfer. The new
[receive-only NCM progress contract](recovery-ncm-progress.md) now has a
bounded device sender, exact production namespace test, hash-pinned privileged
broker/controller, irreversible root-to-operator collector, and private
post-COMMIT lifecycle assessment. Missing, malformed, mismatched, partial, and
complete evidence remains `authority=NONE`; absence cannot gate COMMIT, while a
listener-ownership conflict still fails closed. The 8 runtime, 21 collector,
38 controller, 18 broker/socket, 63 native-control, and 69 lifecycle tests pass,
as do the complete local Linux `ci` and provisioned `quick` tiers. See the
[offline integration result](../test-results/2026-08-04-generation-11-ncm-progress-host-integration-offline.md).

Commit `2b90a0e` passed exact-head GitHub Actions run `30887436984`; the fixed
privileged files were then installed from that checkout, byte-verified, and
exercised through the read-only empty-export proof with SteamOS read-only mode
restored. A clean sealed-container rebuild reproduced the accepted QEMU kernel
Image `cf318b…b4d98`, and the local QEMU 8.2 gate crossed the real AArch64
`systemd` stage-130/140 units. A fresh recovery initramfs then embedded NCM
responder `242ac7fc…149e7`; two clean ASUS wrapper builds reproduced raw image
`44c43e27…12b2`, and two offline Generation-11 issuances reproduced AVB
`8472b206…bcf562`. See the
[wrapper result](../test-results/2026-08-04-generation-11-ncm-progress-wrapper-offline.md).
Its exact recovery and unchanged signed-target tuple passes immutable offline
profile `headless-diagnostic-generation11-offline-v1` against both retained
trees; see the
[profile result](../test-results/2026-08-04-generation-11-offline-profile.md).
The one-shot lifecycle now selects the identical tuple through distinct
`headless-diagnostic-generation11-live-v1`; see the
[offline transition](../test-results/2026-08-04-generation-11-live-profile-offline.md).
Direct connected actions and absent or malformed policy fixtures reject before
host inspection. A separate
[central-policy admission](../test-results/2026-08-04-generation-11-live-admission-offline.md)
added the sole `allow` row for one exact connected-preflight-gated RAM-only
lifecycle. The issuer/evidence checkpoint was published at `5293e56`;
exact-head GitHub Actions run `30899370666` passed recovery-core in 3m53s and
QEMU in 35s. The reviewed profile and its CI-race correction were published at
`98f8d27`; exact-head run `30904224177` passed recovery-core in 3m57s and QEMU
in 37s. The live-profile transition passed focused and complete local CI,
Claude Opus review, and independent Codex review. It was published at
`2a483ec`; exact-head run `30908649494` passed recovery-core in 3m49s and QEMU
in 40s. Admission-focused and complete local CI pass offline, and independent
spec and standards reviews report no findings. The admission was published at
`8e22bc5`; exact-head GitHub Actions run `30916646825` passed recovery-core in
3m47s and QEMU in 37s. Exact key and
[connected preflight](../test-results/2026-08-04-generation-11-connected-preflight-live.md)
then passed after strict fallback health proof and an anchored
`RESTART2("bootloader")` transition to one same-port `lahaina` fastboot device.
At that preflight checkpoint the artifact was unbooted, no Generation-11 claim
existed, and Steam's temporarily released port-8081 socket was restored.
Independent spec and
standards review and complete local CI passed; commit `7b76733` published the
evidence and exact-head GitHub Actions run `30921019231` passed recovery-core
in 4m01s and QEMU in 39s. Publication commit `04132f0` then passed exact-head
run `30921533485`.

The [sole Generation-11 lifecycle](../test-results/2026-08-04-generation-11-progress-listener-confinement-live.md)
entered its durable private claim and booted exact recovery in RAM. Recovery
ACM/NCM passed, but the privileged `serve-progress-deferred` host path rejected
its newly started TCP 8081 collector as not uniquely confined before the
bundle-server ready marker. The capture remained `PARTIAL/NO_ADMISSION` with
zero records and `authority=NONE`; recovery control never started, so no
PREPARE, bundle transfer, COMMIT intent, NFS, or target occurred. The armed
target collector independently rejected with zero frames because diagnostic
ACM never stabilized. Exact Alpine fallback, strict SSH, profile restoration,
host cleanup, and Steam socket restoration passed. Generation 11 is consumed,
absent from boot policy, permanently claimed, and never reusable. A
[production-faithful host-only reproduction](../test-results/2026-08-04-generation-11-progress-listener-scope-reproduction-offline.md)
captured the real `SO_BINDTODEVICE` listener as
`169.254.77.1%enp4s0f3u1u2:8081`; the controller had required an unscoped
substring. The correction parses one exact `ss` record and requires the scoped
endpoint, sole launched `python3` PID/fd owner, a live process, and no IPv6
conflict. Its 38 hardware-free controller cases cover hostile scope, address,
owner, duplicate-record, delay, absence, and IPv6 races. Complete local CI and
installed-host verification pass; implementation commit `1f3cc66` passed
exact-head GitHub Actions run `30931511061` (recovery-core 4m02s; QEMU 37s).
The distinct
[Generation-12 offline successor](../test-results/2026-08-04-generation-12-host-confinement-successor-offline.md)
now has two deterministic trees at AVB `615d7498…d72cf6`. It preserves the
exact Generation-11 raw recovery, kernel, config, and NCM-capable initramfs.
Immutable profile `headless-diagnostic-generation12-offline-v1` passes both
trees. Independent review and complete local CI passed; commit `52ce322`
published the authority-free checkpoint and exact-head GitHub Actions run
`30935842119` passed recovery-core in 4m11s and QEMU in 35s.

The live-admission transition added exact profile
`headless-diagnostic-generation12-live-v1`, selected it from the one-shot
lifecycle, and added the sole central-policy `allow` row for exact path
`build/stable-recovery-generation12-host-confinement-fix-20260804-a/repack/stable-recovery-a.avb.img`.
Direct `preflight`/`boot` still reject without the lifecycle guard. `boot`
must additionally validate and irreversibly enter the controller's private
Generation-12 `BOOT_CLAIMED` record before any host inspection. Eleven
claim-consumer cases and hostile policy/inventory fixtures exercise canonical
root confinement, symlinked passwd-home canonicalization, reuse,
content/metadata/link races, missing or duplicate
rows, wrong basis, denied status, consumed/altered role, tracked-state drift,
and trailing fields. Commit `328b33c` published that transition and exact-head
run `30942517411` passed recovery-core in 4m10s and QEMU in 52s. Strict pinned
fallback SSH proved Alpine health, the anchored helper reached exact
`lahaina` fastboot, and connected preflight passed after temporarily stopping
and exactly restoring Steam's TCP-8081 socket. Commit `1ee5508` published the
[connected-preflight
result](../test-results/2026-08-04-generation-12-connected-preflight-live.md),
and exact-head run `30944062957` passed.

The [sole Generation-12 lifecycle](../test-results/2026-08-04-generation-12-nfs-mount-disconnect-live.md)
then entered its durable claim, transferred all 46,163,787 signed-bundle
bytes, and accepted correlated PREPARE/COMMIT. Forty valid receive-only target
frames had zero dropped USB events or target updates: reporter stage 10,
address stage 50, then repeated stage 70 `nfs-mount-begin` from 3.544 through
12.547 seconds. USB disconnected before stage 80 `nfs-mount-ok` or a terminal
fault frame. The exact 37,735-entry read-only NFS export had been verified and
was ready. This isolates the next investigation to the first NFS mount or a
lower kernel/USB/network boundary, but does not prove a panic. The watchdog
returned exact Alpine fallback; strict SSH, profile restoration, NFS/firewall
cleanup, Steam socket restoration, and `FALLBACK_RETURNED` intent resolution
passed at 43.1 C.

Generation 12 is consumed, removed from central boot policy, exact consumed in
artifact inventory, and permanently claimed. Production diagnostic actions
now reject before guards, credentials, repository, host, or phone inspection;
the retained offline profiles and twins are regression evidence only. The
outer lifecycle parser correction is complete at `606303a`; exact-head run
`30952333022` is green. The published host-only successor inserts stage 75
`nfs-mount-returned`, records same-port NCM/link counters, kernel NFS-RPC
totals, and exact target-specific NFS TCP states/queues/current unrecovered RTO
timeouts in private
evidence v2, and writes one candidate/boot-ID lineage marker to `/dev/kmsg`.
Its historical sealed static reporter is `dc53932d…a10`. Fallback-side
current-cycle pstore
acquisition/correlation is now implemented host-only: a strict same-port SSH
action reads at most 64 records/4 MiB without deleting them, signs a summary
bound to the target candidate/boot ID, distinguishes lineage and fatal-token
states, and runs before unchanged strict fallback health. The host rejects
symlink/type/inode/mount races and cross-probe fallback boot-ID changes; 64
fallback, 27 collector, and 80 lifecycle tests, complete local CI, and
independent review pass in the
[host-only stage-75/postmortem
checkpoint](../test-results/2026-08-05-stage75-postmortem-host-integration-offline.md).
Implementation commit `eeb157b` is published with green exact-head GitHub
Actions run `30988099391` (`qemu-system` 37s; `recovery-core` 4m03s). The
host-only publication gate is closed. The distinct, unissued
`headless-netroot-early-diag-v2` write-side candidate now binds the
host-port-classifying reporter `26249252…bafa` and 6,013,458-byte bounded
rendezvous v3 initramfs `94edd625…cffc`, plus the accepted Image, corrected
DTB, and sealed Arch root. The prior v2 payload and disposable-key wrapper
tuple are retained only as superseded offline composition evidence and are not
the current candidate. Central boot policy remains empty, the profile is
offline-only, and
no production credential or phone was used. This stage-75/current-cycle-
postmortem successor is the active work and has no boot authority. Generation
12 is consumed and must never be retried. A separately reviewed, exact-head-CI
qualified one-shot generation would be required before any connected preflight
or temporary phone boot. See the
[v2 offline result](../test-results/2026-08-05-stage75-v2-candidate-offline.md)
and the
[host-only admission
result](../test-results/2026-08-04-generation-12-live-admission-offline.md).

The superseded v2 candidate checkpoint is published at
`9088c8ff70e24c1c71c3b3b806f7161848dd7320`; GitHub run `31256569397`
passed exact-head, merge-compatibility, QEMU, and candidate-publication jobs
for those historical bytes.
The guarded SSH and diagnostic deployment launchers now refresh the exact
tracked branch before accepting their repository checkpoint. This closes the
remaining stale-`origin` path before a sealed implementation or signing input
can be admitted; the test advances a bare remote behind the clone's stale
tracking ref and requires an exact refusal. This is host-only and grants no
credential, generation, connected-preflight, or boot authority.

At historical local checkpoint
`afc0e9e94bbc6edea1aa0c2ace17b2b5d00cef83`, that superseded v2 candidate also
passed one complete disposable-key build: two clean ASUS wrappers were
byte-identical, the single-attempt target tuple and manifest were exact, the
temporary private key was destroyed, and authority remained `none`. The
2,332.019-second build establishes clean wrapper compilation as the dominant
unattended release cost. Its 10.09 GB duplicate output tree was removed after
recording hashes. See the
[historical v2 disposable twin-build result](../test-results/2026-08-08-stage75-v2-current-disposable-build.md).
Neither old checkpoint validates the current v3 payload. Current-candidate
composition evidence is solely the
[v3 offline rebind result](../test-results/2026-08-09-host-rendezvous-v3-candidate-rebind-offline.md),
with candidate admission still on hold.

The superseded interactive recovery ACM path is now retired from active
operation. `network-root-acm.py`, both persistent-root ACM helpers, and the two
old P2 live-gate runners terminate before authority, credential, host, USB, or
phone inspection. Their helper bodies remain tracked as historical evidence,
while hostile tests make the framed stable-recovery lifecycle the only active
target-execution path. This change is phone-free and grants no candidate or
boot authority; see the
[offline retirement result](../test-results/2026-08-08-legacy-acm-retirement-offline.md).

The active key-bound minimal root now has an exact package-closure gate rather
than relying on a short deferred-package denylist. The retained source archive
and sealed network root both expose the same 152 sorted package/version rows,
SHA-256 `13586291…f8b`; every future stage compares that tracked closure with
both its recorded inventory and fresh Pacman database output. Twelve hostile
add/remove/version/order/format/link mutations fail. Existing root and
candidate bytes are unchanged, and no credential or phone was used. See the
[offline package-closure result](../test-results/2026-08-08-headless-package-closure-offline.md).

## Historical deployment chronology

Historical checkpoint (2026-08-02): generation 1 reached signed-bundle
`PREPARED` and one commit claim, exposed a missing host NFS gate, returned to
exact signed same-port Alpine fallback at 41.8 C, and is consumed. The durable
intent is resolved `FALLBACK_RETURNED`. The fail-closed host fix passes 20
recovery-control and 39 lifecycle tests, independent review, complete local
CI, and GitHub Actions run `30745676057` at exact commit `77336ed`.

Distinct generation-2 AVB `70fd77f7…fc72b1` then passed artifact and connected
preflight and booted exactly once. Recovery returned correlated `PREPARED`,
but the one-transfer HTTP server never completed, so the exact NFS handoff was
absent and control failed before `COMMIT_EXEC`. No intent, target execution,
diagnostic frame, mount, or phone-storage write occurred. Watchdog fallback,
same-port profile restoration, and strict pinned Alpine SSH passed. Generation
2 is consumed and absent from boot admission. Offline inspection proved the
exact booted archive contains no bundle; the remaining gap was an unevidenced
same-boot bundle-cache success path plus a lifecycle mock that hid the real
PREPARE-to-transfer dependency. The offline correction now makes `/run` tmpfs
fatal, forbids pre-existing final bundles, fixes the fixture, and stabilizes
both host cleanup and the exact deferred-profile observation. Forty-one
lifecycle tests, complete local CI, Claude review, and GitHub Actions run
`30750260056` pass at commit `1af3275`. A fresh production twin build now pins
generation-3 AVB `eb514a57…d77b6`, raw wrapper `f1a7c5ad…6a4ce`, and recovery
initramfs `144f1cfd…e4ec`. Its exact artifact preflight passes. The immutable
`headless-diagnostic-generation3-offline-v1` profile still rejects connected
actions; a distinct `headless-diagnostic-generation3-live-v1` profile
bound the lifecycle to the same exact chain. Its
[connected preflight](../test-results/2026-08-02-generation-3-connected-preflight-live.md)
passed against one exact `lahaina` fastboot device. The sole generation-3
cycle then reached verified `PREPARED` after fresh fetch, signature/artifact
verification, and kexec load, but the host's 70-second transfer service never
emitted its completion receipt. NFS therefore never started, the control gate
failed before COMMIT, no target ran, and exact strict-SSH Alpine fallback plus
clean host state passed. The device-side fetch permits 190 seconds, exposing
the historical 70/75/95-second host timeout chain. Generation 3 is consumed
and its allow row is removed. Source
now uses an explicit 180/190/195/205/220/260/320-second nested deadline
lattice. Hardware-free tests enforce every margin and prove that PREPARED plus
forged receipt text and a nonzero host exit cannot start NFS or COMMIT. Commit
`4c2da4b` passed local CI, Claude review, and GitHub Actions run `30785558945`;
its exact controller and server are installed and hash-match their sources.
Distinct generation-4 AVB wrapper `220e8556…270d` was issued twice over
unchanged raw recovery `f1a7c5ad…6a4ce`, admitted once, and consumed by one
RAM-only lifecycle. Connected preflight passed. Recovery reached verified
ACM/NCM with rollback armed, and both the receive-only collector and bundle
service became ready. The bundle service did not emit its independent
completion marker before control's 45-second NFS-readiness deadline, so NFS
never started, COMMIT was never sent, and no target ran. The phone returned
automatically to Alpine. Initial cleanup proof failed while the root-owned
controller remained alive under its 205-second watchdog and the shared `/30`
was outside the exact managed profile; after watchdog exit, fixed anchored
profile restoration and strict fallback preflight passed with no project
server/export residue. Generation 4 is absent from boot policy and must never
be retried or flashed. The required hardware-free correction now models the
exact PREPARED/control-exits-first stall, performs one anchored fallback
restoration and strict-SSH proof without an intent or retry, and still proves
host cleanup when fallback proof fails. PREPARED is flushed before the NFS
gate, artifact progress is non-authoritative, and the real server/fetcher pair
passes with the Generation-4 artifact sizes. Complete local CI and GitHub
Actions run `30793088424` pass at implementation commit `38b6019`; no
Generation-5 image was built or admitted at that checkpoint. See the
[offline choreography correction](../test-results/2026-08-03-generation-4-choreography-fix-offline.md).
The corrected controller/server are now installed with byte-exact hashes; the
real 37,735-entry deployment-root preflight and retained diagnostic-bundle
preflight pass through the installed boundary with no project residue. See the
[host-install result](../test-results/2026-08-03-choreography-host-install-live.md).
Distinct Generation-5 AVB `abe4501f…beb1a` is now independently reproduced
twice over the unchanged recovery payload and passes the complete artifact gate
under `headless-diagnostic-generation5-offline-v1`. See the
[offline issuance](../test-results/2026-08-03-generation-5-choreography-offline.md).
The lifecycle selected the same exact tuple through
`headless-diagnostic-generation5-live-v1`; direct boot remained lifecycle-only.
Central policy admitted exactly one connected-preflight-gated RAM-only cycle.
See the
[profile transition](../test-results/2026-08-03-generation-5-live-profile-offline.md)
and [one-shot admission](../test-results/2026-08-03-generation-5-live-admission-offline.md).
The admission implementation passes complete local CI and GitHub Actions run
`30796577338` at exact commit `51f3bf0`. No phone action occurred.
The exact Alpine fallback later passed guarded health preflight and
acknowledged one SSH-issued `RESTART2("bootloader")`, but disconnected without
re-enumerating during the fixed 45-second and additional 60-second windows.
It subsequently appeared as exact ASUS fastboot at the same physical port;
the cause of that later appearance is not inferred. The standalone reboot
helper now pins that port and
classifies every terminal transition without runtime test overrides. See the
[anchored transition result](../test-results/2026-08-03-fallback-to-fastboot-anchored-diagnostics-live.md).
The subsequent exact Generation-5 connected lifecycle preflight passed at
commit `4c55b1c`: deployment key admission, artifacts, installed host surfaces,
rollback prerequisites, and one `lahaina` fastboot device were clean. The
exact pushed checkpoint `3e7ff47` then passed GitHub Actions run `30799181863`
before the sole lifecycle. Recovery reached verified `PREPARED` and the host
sent all 46,163,787 signed-bundle bytes, but the independent completion-to-NFS
handoff did not make the exact NFSv4.2 listener ready before COMMIT.
`execution_started` remained `NO` and no target ran. After the root controller
left its fixed watchdog, anchored profile restoration, exact Alpine strict
SSH, both installed preflights, and final residue checks passed. Generation 5
is consumed, absent from boot policy, and must never be retried or flashed.
See the
[connected preflight](../test-results/2026-08-03-generation-5-connected-preflight-live.md)
and [live result](../test-results/2026-08-03-generation-5-nfs-readiness-live.md).
Private timestamp reconstruction now proves all 46,163,787 bytes were sent
about 46 seconds before that rejection. The host broker had restored signal
handlers but not its blocked `SIGHUP`/`SIGINT`/`SIGTERM` mask before `Popen`,
so the controller, watchdog, and cleanup descendants inherited blocked TERM.
The controller therefore waited for the full 205-second watchdog instead of
publishing its completion receipt. A test-first correction restores the exact
caller mask before spawn, forwards cancellation to the child process group,
and avoids a stale direct-PID fallback. Thirteen broker, 25 controller, and 47
lifecycle tests and complete local CI pass. Do not increase the NFS deadline.
The replacement GitHub run `30803393832` is green at exact head `c9e3285`, and
the corrected broker is now installed at exact hash `fbafce24…cc42c`. Both
real host-only bundle/root preflights pass and final host residue is empty.
See the
[offline signal correction](../test-results/2026-08-03-generation-5-signal-mask-choreography-fix-offline.md)
and [host installation](../test-results/2026-08-03-generation-5-signal-mask-host-install-live.md).
Distinct Generation-6 AVB `6aa47517…d398` is now twin-reproduced over that
same accepted raw recovery, with exact generation record `bff8432e…52a2`.
Its immutable offline profile, `headless-diagnostic-generation6-offline-v1`,
passes exact artifact and mutation gates but rejects connected preflight and
boot before host inspection even when every live authorization flag is
present. See the
[offline Generation-6 result](../test-results/2026-08-03-generation-6-signal-fix-offline.md).
The lifecycle now selects the same exact tuple through
`headless-diagnostic-generation6-live-v1`; direct boot remains lifecycle-only,
but Generation 6 is now consumed and absent from boot policy. Its connected
preflight passed, then one RAM-only boot transferred the complete signed
bundle while recovery control produced no output or `PREPARED` record.
Independently, the collector expired with zero target frames. No COMMIT intent
existed and no target ran. Alpine restoration and strict SSH passed. Automated
final cleanup returned FAIL on a host-verifier bug; independent residue checks
were clean:
production fallback udev reports `ROG_Phone_5_Linux_Server`, while the
interface classifier accepted only a `ROG5_` prefix. The
[offline udev correction](../test-results/2026-08-03-fallback-udev-model-classification-fix-offline.md)
now uses an exact four-model set, makes the lifecycle fixture emit the real
fallback model after fallback proof, and rejects prefix, suffix, whitespace,
case, empty, missing, and embedded lookalikes. This correction is not yet a
new live cleanup proof. See the
[offline profile transition](../test-results/2026-08-03-generation-6-live-profile-offline.md)
and [one-shot admission](../test-results/2026-08-03-generation-6-live-admission-offline.md),
[connected preflight](../test-results/2026-08-03-generation-6-connected-preflight-live.md),
and [live result](../test-results/2026-08-03-generation-6-recovery-control-silence-live.md).
Private evidence timestamps and NetworkManager journal records subsequently
proved the lifecycle rejected the post-transfer host state after its exact
10-second cleanup-stabilization window, then entered fallback roughly 102
seconds before the collector expired. NetworkManager had already deactivated
the profile and made the interface unmanaged, but retained the exact profile
UUID as historical association data. Because the lifecycle checks deferred
host state before waiting for recovery control, it terminated the still-empty
control process on that false rejection. The
[offline choreography correction](../test-results/2026-08-03-generation-6-deferred-profile-association-fix-offline.md)
admits only an empty association or that one exact UUID after independently
proving no addresses, unmanaged ownership, exact profile/interface identity,
and autoconnect off. Wrong, duplicate, mixed, or unsafe-state associations
remain rejected through a continuous clean dwell. This explains the empty
host log; it does not manufacture a live `PREPARED` result.
Distinct Generation-7 AVB `d3d4cdb9…12901` was independently issued twice
over unchanged raw recovery `f1a7c5ad…6a4ce`, with generation record
`8127197d…799e`, then passed connected preflight and booted once in RAM. The
complete 46,163,787-byte signed bundle transferred, but recovery control
produced no `PREPARED` record and the fixed collector deadline expired with
zero target frames. No COMMIT intent existed, NFS did not start, and no target
ran. Anchored Alpine profile restoration and strict SSH fallback passed. The
controller exposed a remaining host cleanup-verifier deadline/association
defect; independent read-only residue checks were clean. Generation 7 is
consumed, absent from boot policy, never reusable, and never flashable. See the
[issuance](../test-results/2026-08-03-generation-7-deferred-profile-fix-offline.md)
and [live-profile transition](../test-results/2026-08-03-generation-7-live-profile-offline.md),
the [one-shot admission](../test-results/2026-08-03-generation-7-live-admission-offline.md),
[connected preflight](../test-results/2026-08-03-generation-7-connected-preflight-live.md),
and [consumed live result](../test-results/2026-08-03-generation-7-acm-stability-live.md).
The subsequent
[offline cleanup correction](../test-results/2026-08-03-generation-7-cleanup-snapshot-fix-offline.md)
reproduces the final deadline failure without the phone: one strict host
observation required about 5.72 seconds because it launched roughly 23
sequential firewalld queries. Three coherent fail-closed snapshots reduce that
to about 1.11 seconds while preserving the 10-second deadline, one-second
dwell, and all residue checks. The installed NetworkManager source and a
byte-level read-only host probe then reproduced the remaining association
rejection: `nmcli -g` renders a NULL `GENERAL.CON-UUID` as one empty field plus
newline, which Python parses as `[""]`, while the lifecycle accepted only
zero bytes or the exact historical UUID. The narrow correction accepts that
one empty field only after every existing identity, address, ownership,
profile-binding, and autoconnect check; `--`, duplicate, mixed, and foreign
values remain rejected. See the
[empty-field correction](../test-results/2026-08-03-generation-7-nmcli-empty-field-fix-offline.md).
That exact correction is published at `61c6ddd`; complete local CI and GitHub
Actions run `30821583020` pass. The subsequent
[Generation-8 pre-issuance checkpoint](../test-results/2026-08-03-generation-8-host-fallback-readiness-live.md)
re-hashed the installed host boundary, verified the 37,735-entry sealed export
and retained bundle, passed strict-SSH credential admission, and proved exact
connected Alpine through one signed ACM health probe. No Generation-8 image,
signature, profile, policy row, or phone boot exists at this checkpoint.
The next
[test-first issuer checkpoint](../test-results/2026-08-03-generation-8-issuer-readiness-offline.md)
audits the retained generation-zero/Generation-7 inputs and extends the
deterministic issuer regression through Generation 8, including same-run A/B
identity and non-reuse of every Generation 1–7 twin. It creates only
disposable synthetic outputs; at that checkpoint retained Generation-8
production output was still absent.
The subsequent
[offline Generation-8 successor](../test-results/2026-08-03-generation-8-nmcli-empty-field-successor-offline.md)
was issued twice on this host as byte-identical AVB `f102d53c…f2415` trees
over unchanged raw recovery `f1a7c5ad…6a4ce`. Its exact offline-only profile
pins the complete
tuple and both retained trees pass artifact preflight. The issuance record and
artifact inventory retain `authority=none` and `unbooted`; the prospective
live profile is unsupported, the lifecycle still selects consumed Generation
7, and temporary-boot policy still has zero `allow` rows.
The separate
[Generation-8 live-profile transition](../test-results/2026-08-03-generation-8-live-profile-offline.md)
now selects the identical tuple through the one-shot lifecycle. Both profile
names pass exact policy and artifact preflight. Direct connected preflight or
boot requires the lifecycle guard and then an exact central-policy row before
host inspection. The separate
[Generation-8 one-shot admission](../test-results/2026-08-03-generation-8-live-admission-offline.md)
was published at `c667718`, and exact-head GitHub Actions run `30832269180`
passed. Strict-SSH fallback control moved the phone to same-port exact
`lahaina` fastboot and connected preflight passed. The sole Generation-8
RAM-only boot then reached verified recovery ACM/NCM and transferred the full
signed bundle, but recovery returned no PREPARED record. Its terminal
identity-stability rejection did not label initial versus replay discovery;
Generation-9 timing makes watchdog-fallback replay plausible but does not prove
the Generation-8 phase. No COMMIT intent or target execution existed. Exact
Alpine fallback returned; the final host proof exposed a separate
root-owned mode-`0600` empty NFS export-table inspection defect while
independent checks found no host residue. Generation 8 is consumed, absent
from boot policy, never reusable, and never flashable. See the
[live result](../test-results/2026-08-03-generation-8-recovery-acm-stability-live.md).
The host-only successor moves the exact export-table read into the fixed root
broker. Its argument-free `network-export-state` request opens the fixed path
with `O_NOFOLLOW`, revalidates the opened and named inode, accepts only
root-owned mode `0600` or `0644` with one link and a bounded size, requires
zero bytes, emits only a canonical empty-state proof, and never changes the
table. The lifecycle uses this proof in production while retaining its local
fixture reader for hardware-free tests. No phone boot is part of this fix.
Commit `dc2313f` and exact-head GitHub Actions run `30836080889` pass. The
fixed controller is installed; two production proofs accepted the real
root-owned mode-`0600` zero-byte table without changing its inode or metadata,
and independent host residue checks remain clean. See the
[host export-proof install result](../test-results/2026-08-03-generation-8-host-export-proof-install.md).
The next pre-Generation-9 host-only correction replaces the generic recovery
ACM stability timeout with a bounded non-sensitive classifier. It records only
one of eight fixed inventory states per sample, saturated counts, at most 16
state transitions, and fixed identity-field labels when exact observations
change. An opaque ACM node fails closed; one exact read/write character device
must still retain the same path, device number, `DEVPATH`, `ID_PATH`, and
`ID_SERIAL` through the two-second dwell and final revalidation. Twenty-nine
focused recovery-control tests, all 62 lifecycle tests, and complete local
repository CI pass. No phone, credential, signing key, generation artifact,
or private evidence was used.
Commit `77543ee` and exact-head GitHub Actions run `30838804593` pass. The
lifecycle uses this controller from the synchronized repository checkout; it
is intentionally not part of the root-installed broker bundle, so no host
reinstall is required.
See the
[offline result](../test-results/2026-08-03-generation-9-recovery-acm-classifier-offline.md).
The next test-first checkpoint extends the disposable AVB-generation oracle
through Generation 9: two runs and both twins must reproduce, raw recovery
must remain exact, and every Generation 1–8 wrapper identity must differ. It
created no retained output or boot authority; see the
[issuer-readiness result](../test-results/2026-08-03-generation-9-issuer-readiness-offline.md).
The separately issued Generation-9 successor is AVB `b458e64b…d008` over
unchanged raw recovery `f1a7c5ad…6a4ce`. Admission commit `eea0989` and
exact-head GitHub run `30847253087` passed. Key and connected preflight then
passed, followed by the sole RAM-only lifecycle. Exact recovery ACM/NCM served
all 46,163,787 signed-bundle bytes, but recovery returned no `PREPARED`
response before watchdog fallback. The complete transfer and USB timeline make
same-session replay discovery after the original transport loss, when Alpine
was already present, the best interpretation of the final 216-sample
`product-mismatch` trace; the controller did not label the phase directly. It
does not contradict the initial exact ACM connection that delivered PREPARE.
No COMMIT intent existed and no target ran. Exact Alpine fallback and final
host cleanup passed. Generation 9 is consumed, absent from policy, permanently
`BOOT_CLAIMED`, and never reusable.
Clean-checkout CI skips only the ignored retained-tree checks. Exact-head
GitHub run `30841980164` passed at issuance commit `6193056`. The separate
live-profile transition selects the identical tuple through the lifecycle and
passed exact-head GitHub run `30843398402` at commit `4979581`. Unguarded
connected actions fail on the lifecycle guard; missing, duplicate, or
wrong-basis policy rows fail before host inspection. See the
[offline successor](../test-results/2026-08-03-generation-9-acm-classifier-successor-offline.md)
and [live-profile transition](../test-results/2026-08-03-generation-9-live-profile-offline.md),
the [one-shot admission](../test-results/2026-08-03-generation-9-live-admission-offline.md),
and the [live result](../test-results/2026-08-03-generation-9-prepared-response-gap-live.md).
The host-side pre-Generation-10 correction now gives ACM discovery an explicit
`initial` or `prepare-replay` phase and, when replay discovery fails, raises one
bounded terminal error containing both the original PREPARE transport loss and
the sanitized replay classifier. Thirty-three focused tests cover phase
validation, the exact Generation-9-shaped product-mismatch replay, shared
deadline, correlation, and no COMMIT intent. See the
[offline result](../test-results/2026-08-03-prepare-replay-phase-preservation-offline.md).
The next hardware-free increment is now implemented: the native responder
emits body-hashed, request-correlated `REQUEST_ACCEPTED`, `FETCH_COMPLETE`,
`VERIFY_COMPLETE`, `KEXEC_LOAD_COMPLETE`, and `PREPARED_PERSISTED` records.
The host accepts only a contiguous prefix per attempt, restarts sequencing for
the sole same-session replay, and retains both attempt traces beside the
initial and replay transport classifiers. Progress remains advisory and no
COMMIT intent can exist without the terminal correlated `PREPARED` response.
An injected progress-send failure proves that later phases are suppressed
while safe preparation and replay semantics continue. Watchdog exit remains
out-of-band because reset may remove ACM before a final frame can drain. See
the [offline result](../test-results/2026-08-03-prepare-progress-observability-offline.md).
The updated responder is now byte-verified inside twin identical initramfses,
ASUS 5.4 wrapper Images, raw header-v3 images, and unsigned AVB test wrappers.
The responder is `67b4f012…c167`, initramfs `dd0c7729…1642`, wrapper Image
`30ce237f…b50c`, raw image `a2f0f10d…f876`, and test AVB image
`cb23bc4f…a448`. The build used a disposable key, retained
`authority=none`, and created no Generation 10 artifact or phone action at
that checkpoint. See
the [offline wrapper integration](../test-results/2026-08-03-prepare-progress-wrapper-integration-offline.md).
The guarded external signing-key/candidate-record preflight and synthetic
Generation-10 issuer regression pass; see the
[issuer-readiness result](../test-results/2026-08-03-generation-10-issuer-readiness-offline.md).
The subsequent guarded production operation bound the same responder to the
existing production trust root, signed the diagnostic runtime bundle, and
produced two clean byte-identical ASUS 5.4 wrappers. The production recovery
initramfs is `99046d30…6e31`, wrapper Image `bb49b405…5f98`, raw wrapper
`27f4dbcc…73b3`, and canonical source AVB `b2ada6b8…ba83`. The private key
snapshot was destroyed and the external inputs remained unchanged.

Two independent issuer invocations now retain exact 11-file Generation-10
trees at AVB `b983e89b…8b51`, salt `5f62ef87…d3ee`, and generation-record
`cb999cd8…3b6d`. Cross-tree and A/B equality, pinned `avbtool`, an independently
recomputed salt-plus-raw digest, unchanged raw bytes, and distinct retained
Generation 4–9 identities all pass. The synthetic regression covers
Generations 1–9. No phone interface was used. Generation 10 is unbooted and
retains `authority=none`; see the
[offline successor result](../test-results/2026-08-03-generation-10-prepare-progress-successor-offline.md).

This issuance was independently reviewed, published at `d04b804`, and passed
exact-head GitHub Actions run `30865091104`. The subsequent immutable
`headless-diagnostic-generation10-offline-v1` profile now pins the full tuple,
rejects connected actions before host inspection, and passes both retained
issuer trees plus generation-record mutation rejection on this host. Clean CI
skips those ignored trees. Artifact inventory records `unbooted` and
`authority=none`; temporary-boot policy is unchanged with zero `allow` rows.
See the
[offline profile result](../test-results/2026-08-03-generation-10-offline-profile.md).
Constrained re-review and complete local CI passed; publication at `edae5d1`
and exact-head GitHub Actions run `30867110893` are green. The subsequent
`headless-diagnostic-generation10-live-v1` profile now selects the identical
tuple through the lifecycle. Direct connected actions require the lifecycle
guard, and missing, duplicate, or wrong-basis policy states reject before host
inspection. That transition was published at `adc4123` and passed exact-head
GitHub Actions run `30869110964`. A separate central-policy checkpoint then
admitted exactly one image and exact one-shot basis for a
connected-preflight-gated RAM-only lifecycle. Inventory retained issuance
`authority=none` at that checkpoint. See the
[live-profile result](../test-results/2026-08-04-generation-10-live-profile-offline.md).
The admission's focused and complete local suites pass, constrained Opus
re-review returns `NO FINDINGS`, and publication at `a9c012c` passed exact-head
GitHub Actions run `30870594823` (`recovery-core` 3m58s; QEMU 35s). See the
[admission result](../test-results/2026-08-04-generation-10-live-admission-offline.md).
The first connected-preflight transition began from exact Alpine fallback.
Fallback health and the authenticated `RESTART2("bootloader")` request passed,
but USB disconnected without any anchored-port mode returning during the fixed
45-second window or an additional 30-second read-only check. No recovery image,
payload, boot command, boot claim, or consumption occurred. Exact fastboot
appeared later on the same connection after those bounded observations ended;
the cause is not inferred. A fresh Generation-10 connected preflight at clean
pushed commit `70d2f36` then passed the deployment-key chain, exact artifacts,
installed host surfaces, rollback prerequisites, isolated USB profile, and one
`lahaina` device. No phone boot, payload transfer, SSH connection, or privileged
server was started. See the
[transition result](../test-results/2026-08-04-generation-10-connected-preflight-transition-live.md)
and
[connected-preflight result](../test-results/2026-08-04-generation-10-connected-preflight-live.md).
That result was reviewed and published at `f4b9e1c`; exact-head GitHub Actions
run `30872608193` passed (`recovery-core` 3m47s; QEMU 43s). The sole
Generation-10 RAM-only lifecycle then reached exact recovery ACM/NCM, emitted
correlated `REQUEST_ACCEPTED`, and transferred all 46,163,787 signed-bundle
bytes. The ACM response transport then closed before any later progress or
`PREPARED` response reached the host; the exact device-side boundary remains
unknown. Replay was explicitly `phase=prepare-replay` and observed 216 stable
fallback/product-mismatch samples with no identity changes. NFS reached
pre-COMMIT readiness, but no COMMIT intent existed and no target ran. Exact
Alpine fallback, strict SSH, profile restoration, and final host cleanup
passed. Generation 10 is permanently `BOOT_CLAIMED`, absent from boot policy,
consumed in inventory, and never reusable. See the
[live result](../test-results/2026-08-04-generation-10-request-accepted-transport-gap-live.md).
At that live checkpoint, the next increment was hardware-free reproduction of
this exact progress/transport/replay sequence and an independent device-side
progress path that survives ACM loss. That implementation and its distinct
Generation-11 wrapper and separate one-shot central admission pass offline;
connected preflight now passes, and the current pre-boot publication boundary
is recorded in the observability section above.
The Generation-4 offline issuance passed focused/complete local CI,
Claude review, and GitHub Actions run `30786957283` at exact implementation
commit `e3a47a8`. The Generation-4 live-profile transition passed
focused/complete local CI, constrained Claude Opus review, and GitHub Actions
run `30787774104` at exact implementation commit `f058d47`. See the
[generation-4 live result](../test-results/2026-08-03-generation-4-nfs-readiness-live.md).
Historical context remains in the
[live NFS-bypass result](../test-results/2026-08-02-diagnostic-nfs-handoff-bypass-live.md),
[generation-2 live result](../test-results/2026-08-02-generation-2-fresh-fetch-gap-live.md),
[generation-3 production build](../test-results/2026-08-02-generation-3-fresh-fetch-production-build.md),
[generation-3 live result](../test-results/2026-08-03-generation-3-transfer-timeout-live.md),
[generation-3 admission](../test-results/2026-08-02-generation-3-live-admission-offline.md),
and [generation-4 offline issuance](../test-results/2026-08-03-generation-4-timeout-lattice-offline.md).
The successor profile transition is recorded in the
[generation-4 live-profile result](../test-results/2026-08-03-generation-4-live-profile-offline.md).
The separate one-shot authority change is recorded in the
[generation-4 admission result](../test-results/2026-08-03-generation-4-live-admission-offline.md).
That live result also records the consumed disposition.

The complete non-fixture identity chain is built and passes hardware-free
admission:

- a dedicated Ed25519 SSH public key is embedded in the minimal root;
- the sealed v3 root, candidate, signed manifest, recovery trust root, and
  reproducible wrapper are mutually bound;
- the exact hashes are pinned by `headless-ssh-deployment-v3`; and
- the real artifact preflight passes without contacting the phone.

See the
[deployment-chain result](../test-results/2026-07-31-headless-ssh-deployment-chain-offline.md).

The consumed signed bundle has now been replaced by the distinct
`headless-ssh-network-root-v3-r2` transfer identity. One guarded production
build from clean pushed checkpoint `81d2736` produced byte-identical twins,
destroyed its private signing-key snapshot, and reproduced manifest
`9ea27452…d630`. The unchanged public trust root and the exact recovery AVB,
raw image, kernel, initramfs, control, fetcher, verifier, host verifier, and
configuration hashes are pinned by the deployment live gate. Its real
artifact preflight passes without fastboot discovery; see the
[signed r2 result](../test-results/2026-07-31-headless-ssh-successor-r2-signed-build.md).

The host deployment boundary now passes:

- the reviewed SteamOS export-store remediation is pushed and installed;
- the no-replace v3 lower is published below the root-owned `/home` store;
- local key admission, sealed-root, fixed NFS, artifact, and
  connected-fastboot checks pass; and
- the first guarded temporary boot reached stable recovery and transferred
  the exact signed bundle, but recovery rejected PREPARE with `FETCH_FAILED`
  at the former 60-second fetch deadline; no commit or kexec occurred.

The lifecycle now uses the dedicated client key over the fallback USB-NCM
link. A persistent, no-gateway NetworkManager profile assigns only
`169.254.77.1/30`; Alpine remains fixed at `169.254.77.2`. Recovery, target,
and fallback now share one host prefix, removing the route replacement race.
This `/30` profile and the single-session SSH transition pass host and
hardware-free gates but have not yet completed a phone cycle; see the
[USB transition result](../test-results/2026-07-31-usb-ssh-transition-hardening.md).
The preceding live fallback proof used the former `/16` profile.
The controller
requires strict host-key checking, sends one nonce-bound read-only health
probe over non-interactive SSH, verifies Alpine's Ed25519 signature, and then
revalidates the exact product, NCM driver, physical recovery USB location,
direct route, and interface. The protocol binds kernel/init/compatible/root,
modules, pstore, dmesg, thermals, Python, boot ID, and physical USB location.
The normal lifecycle no longer enters the legacy BusyBox shell, eliminating
the ACM echo/framing race and shell-history side effect. Read-induced ext4
atime changes remain separately guarded. The signed ACM path remains
available for emergency diagnostics only. The strict-SSH host-only
preflight validates the client key, host pin, fixed tools, wait range, and the
3,600-second contact-start/7,200-second anchor-age contract without phone
contact. The recovery anchor is revalidated after the SSH proof to cover host
suspend.
Nonce-bound phone errors retain their failure class through the last bounded
serial read. Host cleanup validates the root-owned canonical NFS export table
directly; it no longer mistakes unprivileged `exportfs` lock diagnostics for
an active export.

Forty-six fallback transport tests and all twenty-six lifecycle methods
pass. A physical reboot restored the supervised ACM reader. The fresh signed
exchange then exposed a stale thermal assumption: the installed fallback now
publishes 96 contiguous zones, including unsupported auxiliary channels,
rather than exactly 70 universally readable temperatures. The controller now
requires a bounded contiguous topology, a stable readable quorum, named core
CPU/GPU/system sensors, and the unchanged hard temperature ceilings while
ignoring unreadable temperatures only for an exact observed auxiliary-type
allowlist, plus zero and Qualcomm-inactive values.
One fresh nonce-bound preflight passed and its mode-`0600` signed proof is
retained outside Git. After the rejected recovery attempt, the watchdog
returned the same port to Alpine and a second fresh signed fallback proof
passed. See
the [live acceptance](../test-results/2026-07-31-fallback-acm-preflight-live-accepted.md)
and preceding
[reader rejection](../test-results/2026-07-31-fallback-acm-preflight-live-rejected.md).

The first guarded lifecycle attempt is recorded in the
[live fetch-failure result](../test-results/2026-07-31-minimal-headless-live-cycle-fetch-failure.md).
The host completed the one-shot transfer six seconds after control started,
but the old helper returned only generic `FETCH_FAILED` at its exact
60-second end-to-end deadline. PREPARE stayed `IDLE`, so no COMMIT, durable
intent, or kexec occurred. The attempt also exposed an unprivileged-to-root
NFS cancellation bug; the exact process was terminated once with root
authority, full host cleanup was verified, and the temporary PolicyKit rule
was removed. The active fix preserves exact fetch-stage errors, uses coherent
nested budgets, and gives the fixed root server authenticated cancellation.
The real-host
[cancellation integration](../test-results/2026-07-31-network-root-cancel-host-integration.md)
then found and fixed the parent/zombie wait boundary. Its final rerun passed
through the public launcher, removed every NFS artifact, restored SteamOS
read-only protection, and removed the temporary PolicyKit rule.

The rebuilt recovery then completed fetch, PREPARE, and one durable COMMIT in
the [strict-SSH fallback cycle](../test-results/2026-07-31-minimal-headless-live-cycle-ssh-fallback.md).
Target host-key bootstrap rejected Linux's legitimate indented `cache` route
continuation before SSH acceptance. The watchdog returned the same port to
Alpine, the persistent USB profile restored its then-configured fixed `/16`,
strict SSH verified a signed fallback record at 44.1 degrees C without ACM,
and the intent resolved `FALLBACK_RETURNED`. The profile is now standardized
on `/30`. The target parser accepts only the same bounded cache continuation
already covered by the fallback parser.
The consumed v3 manifest is now denied before private-key inspection. A
hardware-free r2 successor keeps the accepted target/root tuple and changes
only the signed bundle identity; base/r2 twin packaging proves all other
manifest fields remain equal. The predicted r2 manifest identity is pinned in
the [offline successor result](../test-results/2026-07-31-headless-ssh-successor-r2-offline.md),
and the real external r2 candidate is now staged outside Git. A
credential-free check binds it to the retained package, exact
Image/DTB/initramfs bytes, and predicted manifest identity; see the
[real-candidate checkpoint](../test-results/2026-07-31-headless-ssh-successor-r2-real-candidate.md).
The reusable preflight and its 22 hostile tests are pushed at
`773a1196cbfad33ab87124c47ed9772f6251c40c`; the formal run against all three
external inputs passed at that exact clean, origin-synchronized checkpoint
with no credential or phone access.
That exact r2 candidate is now signed and twin-built. It reproduced the
predicted manifest, reused the existing public recovery trust root, and its
recovery-wrapper, verifier, and configuration identities are pinned. The
review/publish gates are green. The signed r2 bundle is now installed through
the no-replace path, the consumed predecessor is retained in a private
recoverable archive, and the aggregate key, artifact, privileged-host,
fallback-SSH, and connected-fastboot preflight passes from clean pushed
checkpoint `e635257`. The temporary PolicyKit authorization was removed and
the final host residue audit is clean; see the
[r2 host preflight](../test-results/2026-07-31-headless-ssh-successor-r2-host-preflight.md).
The first r2 temporary boot completed the signed recovery transfer, PREPARE,
and one durable COMMIT. Linux 7.1 exposed the expected USB-NCM product on the
same physical port, then physically disconnected 23 seconds later before the
target host key could be pinned. The watchdog returned the unchanged Alpine
fallback, strict SSH accepted one fresh signed identity record, and the
durable intent resolved `FALLBACK_RETURNED`. A short NetworkManager/udev
observation race in final cleanup is now covered by a bounded continuously
clean dwell; all non-identity cleanup failures remain immediate. r2 is
consumed and must not be retried. See the
[r2 target USB-loss result](../test-results/2026-08-01-minimal-headless-r2-target-usb-loss.md).

The active hardware-free successor is now the distinct
`headless-netroot-early-diag-v1` diagnostic profile. Its shared-init branch is
fixed-identity gated and adds only a write-only ACM reporter, monotonic stage
updates, two volatile post-handoff units, and a bounded five-second terminal
dwell. Normal network-root mode remains reporter/ACM/unit/dwell-free. The
sealed reporter and optional archive integration twin-build locally; the
native bundle verifier requires the helper for the diagnostic profile and
forbids it elsewhere. The corrected Linux 7.1.4 QEMU profile enables the
demonstrated FUTEX, MEMFD_CREATE, SHMEM, and TMPFS requirements. Its clean
local full-system run enters the sealed Arch runtime under real AArch64
`systemd 260.2-2-arch` and executes the exact generated stage 130/140 units.
The hardware-free successor now starts real OpenSSH 10.3, accepts one
disposable Ed25519 key login over loopback, executes the authenticated command,
and rejects a keyless login. Phone hardware remains outside this evidence. See
the [real OpenSSH QEMU
result](../test-results/2026-08-08-real-openssh-qemu-gate-offline.md).
The receive-only host collector now starts kernel-event capture before target
enumeration, binds one diagnostic ACM interface to the recovery anchor's port,
parses only validated frames through the shared oracle, and writes one bounded
mode-`0600` JSON record outside Git. Its hostile tests, deterministic
subprocess lifecycle test, and real unprivileged journal-reader smoke pass.
The collector emits one exact flushed supervisor-ready line after journal
startup and before enumeration, and none when journal startup fails. See the
[collector result](../test-results/2026-08-01-early-target-host-collector-offline.md).
Before production signing, a disposable Ed25519 key completed the same full
wrapper/twin-build/native-verification path. Independent standards and spec
reviews closed its signing-input, lifecycle, collector-readiness, evidence-
binding, and no-replace publication gaps. See the
[offline candidate result](../test-results/2026-08-01-early-target-diagnostic-candidate-offline.md),
[offline lifecycle result](../test-results/2026-08-01-early-target-diagnostic-lifecycle-offline.md),
and [signing-readiness result](../test-results/2026-08-01-early-target-diagnostic-signing-readiness-offline.md).

The controller's diagnostic path starts the receive-only collector before the
non-retryable recovery boundary, refuses before COMMIT unless the collector is
ready, never substitutes normal SSH acceptance, and resolves only after exact
fallback and cleanup. Direct boot and lifecycle admission reject both consumed
normal manifests. The prior reviewed checkpoint is published in draft PR
[#1](https://github.com/klimovich008/rog5-linux/pull/1), with both jobs green in
[GitHub Actions run `30700630487`](https://github.com/klimovich008/rog5-linux/actions/runs/30700630487).

The first production diagnostic lifecycle temporarily booted and anchored the
exact stable recovery, then rejected before bundle transfer because the
graphical PolicyKit request for the fixed bundle controller exceeded the
server-ready window. No recovery control or `COMMIT_EXEC` occurred and the
diagnostic candidate remains unexecuted. The independent 180-second recovery
watchdog returned the same USB port to Alpine; strict SSH accepted a fresh
signed fallback record at 42.5 C and no project process or listener remained.
The [live result](../test-results/2026-08-01-early-target-diagnostic-host-auth-timeout.md)
records the private evidence hashes. Runtime PolicyKit is now replaced by one
operator-owned mode-`0600` systemd socket whose root broker accepts only the
fixed bundle/NFS protocol and verifies the connecting UID plus installed
controller hashes before dispatch. Commit `aa39503` passes both GitHub jobs,
is installed on SteamOS with read-only mode restored, and completed the real
37,735-entry deployment-root preflight through the socket without a prompt.
The [host-control result](../test-results/2026-08-01-steamos-prompt-free-host-control-live.md)
records the exact installed hashes and cleanup evidence.

The next admitted lifecycle proved the prompt-free socket path but rejected
before listener or transfer: the active bundle root still contained consumed
r2 beside the diagnostic bundle, and the authoritative server refused its
`unexpected bundle-root inventory`. No recovery control, intent, NFS, or
target execution occurred; automatic same-port fallback and a fresh signed
strict-SSH record passed at 43.1 C. Consumed r2 is now in a private recoverable
archive. The launcher remediation invokes the same descriptor-based sole-root,
artifact, and manifest validation during preflight without opening a listener.
Commit `76439d9` is published and reinstalled with exact source/installed
hashes; the real bundle preflight preserved all atimes and left no listener or
process, and the 37,735-entry prompt-free NFS preflight passed without residue.
See the [inventory rejection](../test-results/2026-08-01-early-target-diagnostic-bundle-inventory-rejected.md).

A separately admitted lifecycle then transferred the response header and
manifest, but recovery rejected `PREPARE` as `FETCH_FAILED/FETCH_MANIFEST`
before signature/artifact completion, intent creation, NFS, or `COMMIT_EXEC`.
The signed manifest correctly binds the diagnostic profile to the same Arch
trust tuple required by the contract, packager, host server, native verifier,
and target cmdline; only the recovery fetcher incorrectly required the
persistent profile's zero/`none` tuple. An exit-50 native regression reproduces
the live failure and passes after the one-branch correction. The run also
proved that controller cleanup reactivated the fallback NetworkManager profile
while recovery remained connected. Review rejected an unbounded in-controller
deferral, so that secondary cleanup race remains pending a separately tested
bounded lifecycle design. Exact strict-SSH fallback passed at 43.5 C.
The used recovery wrapper is removed from temporary-boot admission; the target
candidate remains unexecuted. See the
[manifest rejection](../test-results/2026-08-01-early-target-diagnostic-fetch-manifest-rejected.md).

The corrected fetcher has now passed the complete hardware-free deployment
composition from clean synchronized checkpoint `2653e61`: disposable-key
bundle signing, two byte-identical stable-recovery initramfs and ASUS 5.4
wrapper builds, header-v3/test-AVB packing, native artifact verification, and
the real gate logic in an ignored identity-parameterized fixture. The test-only
AVB twins are `2a44a908…62c53`, the corrected fetcher is
`f410ca87…b5d13d`, and the run retained `authority=none`; no production key or
phone interface was used. The old `9c060a27…204ef` wrapper remained consumed
and denied in the fixture. See the
[corrected disposable build](../test-results/2026-08-01-corrected-diagnostic-recovery-disposable-build.md).
Production twin signing and the bounded fallback-profile cleanup correction
were the two preconditions before any new temporary phone lifecycle.

The first precondition is now complete. A guarded production-key operation
from clean synchronized checkpoint `84a9cc8` produced byte-identical corrected
wrappers at AVB SHA-256 `f710bbcd…97b0ef`, raw SHA-256
`2f460aa0…628a01`, ASUS `Image` SHA-256 `7fac4dda…728ed`, stable-recovery
initramfs SHA-256 `fec72c4d…1c57a`, and the unchanged production trust root
`f10ca076…c57b`. The complete artifact preflight passes and the new wrapper is
exactly admitted for one RAM-only boot. The source seals match, the candidate
and external key remain unchanged, no private snapshot survived, and no phone
interface was contacted. The old wrapper remains consumed and refused. See
the [corrected production build](../test-results/2026-08-01-corrected-diagnostic-recovery-production-build.md).
The second precondition is now accepted offline. The lifecycle-only bundle
mode disables profile autoconnect before transfer, cleans the recovery link
without reattaching the `/30`, and later asks the fixed root broker to restore
the profile only after one exact Alpine NCM product is stable at the anchored
physical USB location. The restore is monotonic-time-bounded, serialized,
idempotent, revalidates USB identity around activation, and rolls every
partial failure back to profile-down/autoconnect-off/unmanaged state.
Twenty-two controller, eleven socket, forty-seven fallback, and thirty-seven
lifecycle tests pass, as does complete repository Linux CI. No host install,
credential, or phone interface was used.
See the
[bounded restoration result](../test-results/2026-08-01-bounded-fallback-profile-restoration-offline.md).
That boundary was crossed on 2026-08-02. Reviewed publication, local and GitHub
CI, installed-hash verification, and connected preflight passed. Recovery AVB
`f710bbcd…97b0ef` then booted once, but the root-owned bundle controller
rejected Steam's unrelated `127.0.0.1:8080` listener before transfer or
`COMMIT_EXEC`. The independent watchdog returned to same-port Alpine and
strict pinned SSH passed. The wrapper is consumed and absent from boot
admission; the signed target bundle remains unexecuted. The active boundary is
now the scoped privileged-controller correction, exact reinstall, and a
distinct deterministic signed AVB successor. See the
[live result](../test-results/2026-08-02-corrected-diagnostic-bundle-listener-rejected.md).

The host correction now accepts unrelated loopback-only TCP 8080 listeners
while rejecting wildcard, fixed recovery-address, IPv6 wildcard, and mapped
conflicts before and after server startup. Twenty-five controller tests, full
local CI, independent review, and GitHub Actions pass at checkpoint `d35c734`.
A dedicated atomic issuer then produced generation-1 AVB wrapper
`332889a8…b51830` from the exact consumed generation-zero wrapper while proving
the raw recovery, kernel, initramfs, trust root, signed diagnostic bundle, and
all AVB structure except salt/digest are byte-identical. Its complete artifact
preflight passes and it is the sole temporary-boot allow row. This is a new
one-shot identity, not a new signature; the bootloader wrapper still uses AVB
algorithm `NONE`. The corrected root-owned controller is now installed at
exact source/install SHA-256 `9f3be8e9…90894`, its socket is active, SteamOS
read-only mode is enabled, and complete local CI passes. Reviewed publication,
GitHub CI, and connected preflight passed, then generation 1 booted once.
Recovery fetched and verified the signed bundle, returned `PREPARED`, and
claimed one `COMMIT_EXEC`, but the host control client's hard-coded NFS bundle
set omitted the diagnostic bundle. Commit therefore preceded NFS startup; no
diagnostic frame arrived, and exact same-port Alpine fallback passed. The
durable intent is resolved `FALLBACK_RETURNED` and generation 1 is consumed.
The host fix adds diagnostic to the exact v3 NFS policy and rejects unknown
handoff requests before device discovery; 20 control and 39 lifecycle tests,
independent review, local CI, and GitHub CI pass at `77336ed`. Generation-2 AVB
`70fd77f7…fc72b1` later booted once, failed before COMMIT when PREPARED lacked
a corresponding host transfer completion, returned to exact fallback, and is
consumed. See the [successor result](../test-results/2026-08-02-listener-successor-avb-generation-offline.md),
[live NFS-bypass result](../test-results/2026-08-02-diagnostic-nfs-handoff-bypass-live.md),
and [generation-2 live result](../test-results/2026-08-02-generation-2-fresh-fetch-gap-live.md).

An earlier generation-2 connected attempt passed the exact credential-chain
gate and fresh signed Alpine ACM health preflight, then the guarded
`RESTART2("bootloader")` request detached USB without any phone mode returning
during the bounded observation. No recovery boot occurred in that attempt.
The host now classifies this terminal transition by
observed same-port USB phase while retaining the unchanged strict fastboot
success gate; see the
[offline transition result](../test-results/2026-08-02-fallback-fastboot-transition-diagnostics-offline.md).
The next action is a manual fastboot entry followed by the exact connected
diagnostic preflight, not a boot.

Manual fastboot then exposed exact ASUS `0b05:4daf` on the pinned physical
path and product `lahaina`. The generation-2 connected diagnostic preflight
passed from clean pushed commit `32ce8b1` after local and GitHub CI, using the
canonical installed no-replace bundle root. No boot or server was started by
the preflight itself; the later single live cycle is recorded above. See the
[connected preflight result](../test-results/2026-08-02-nfs-gated-generation-2-connected-preflight.md).

See the
[real-host deployment result](../test-results/2026-07-31-steamos-deployment-preflight-live.md).
The replacement fallback control boundary is recorded in the
[authenticated ACM result](../test-results/2026-07-31-fallback-acm-control-offline.md).

The reproducible commands and credential metadata rules are in
[Build the non-fixture chain](minimal-headless-live-cycle.md#build-the-non-fixture-chain).

The [standing operator authorization](operator-standing-authorization.md)
records the current no-reprompt directive and supersedes older goal or runbook
wording that required fresh action-scoped authorization for an otherwise
in-scope action. Invocation-time guards, exact preflights, one-shot candidate
consumption, rollback, cleanup, and the no-flash/no-phone-storage boundaries
remain mandatory.

The authoritative procedure is the
[minimal-headless lifecycle runbook](minimal-headless-live-cycle.md).

## One-cycle acceptance

The controller must:

1. verify one `lahaina` fastboot device and the exact recovery artifacts;
2. use temporary boot only;
3. anchor the recovery and target USB gadgets to the same physical port;
4. transfer one signed bundle, then close the bundle server;
5. start the fixed read-only NFSv4.2 export and issue one non-retryable
   `COMMIT_EXEC`;
6. pin the volatile target host key without TOFU;
7. collect and verify one strict-SSH runtime record while rollback stays
   armed;
8. retain one bounded signed current-cycle pstore summary when the target boot
   ID is known;
9. verify the returned Alpine fallback through its strict-SSH signed,
   nonce-bound health record;
10. prove all host network/export state is removed; and
11. resolve the durable intent as accepted or fallback-returned.

Transport loss without enough correlated evidence remains `UNKNOWN`; it
never authorizes another execute.

## After the core cycle

If the core runtime passes, continue in this order:

1. physical power/volume keys and bounded default-off indicator pulse;
2. read-only dual-cell topology observation, then sustained battery telemetry
   and charger-state comparison;
3. CPU cooling, PMIC alarm registration, and bounded thermal fallback;
4. panel-off operation, suspend/wake, SSH continuity, and idle power;
5. implement and build the VCNL36866 ALS/proximity port under its frozen
   contract, then inventory IMU/compass, then audio, WCN6855 enumeration, and
   Wi-Fi client mode.

See [ROADMAP.md](../ROADMAP.md) for completion gates and
[port-status.md](port-status.md) for subsystem evidence.

## Safety invariants

- Never flash an experimental partition.
- Never mount phone storage or write it. The active strict-SSH lifecycle does
  not invoke the legacy interactive shell; any emergency ACM use retains its
  bounded BusyBox-history/atime effects under the standing authorization.
- Never reuse a consumed live payload or retry an ambiguous execute.
- Keep private keys, host pins, firmware, and live evidence outside Git.
- Follow the [credential-isolation policy](security-automation.md).
- Keep rollback armed until fallback has been independently verified.
- Treat QEMU, static DT checks, and green CI as hardware-free evidence only.
- Publish changes only after focused tests, full CI, and independent review.

Historical detail remains available through the
[archive index](archive-index.md),
[current-state evidence ledger](current-state.md), and dated files under
`test-results/`.
