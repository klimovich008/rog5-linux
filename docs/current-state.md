# ROG5 current state

Updated 2026-09-08: R01 failed at the early storage gate; its RAM claim is consumed.
Installed V11 authenticated on its diagnostic address; the exact V8 selection is healthy again.
A fresh ordinary V8 boot reached switch-root, but its smoke observation failed.
Host teardown correction and same-boot service verification are pending; final qualification remains incomplete.

## Goal and authority

Qualify one reliable unattended headless Arch server under the existing
[acceptance contract](release-acceptance.md) and
[mandatory matrix](../configs/release-acceptance.json). Display is optional.
Missing prerequisites/evidence are BLOCKED or NOT RUN, never PASS.
No architecture rewrite or competing goal; unrelated work stays in the backlog.

Exact phone: `M5AIKN00F0353YH`, product `lahaina`, side USB anchor `1-1.2`.
Preserve official WW33 slot A (`33.0210.0210.200`) as charging/rescue.
Stock charging restoration is complete; do not repeat super/stock restoration.
Keep identity/slot/topology, signatures, battery/thermal, storage scope/backups,
independent fallback and permanent experimental one-use protections.
No new flash, GPT or protected-data operation. Destructive scope is separate.
Private credentials, packages and raw evidence remain outside Git.

## Running release and recovery

Last accepted bundle `headless-server-selector-v8`, kernel `7.1.4-gf17befd4ef17`,
ordinary installed boot `af66d09d-f512-4954-a036-0904616e17af`. The current
installed recovery emitted boot `96c3e790-a422-4723-b9ca-a5039da2a14a`; its
diagnostic SSH authenticated and exact selection restoration passed. After the
closed connection failure, a fresh ordinary request succeeded and V8 boot
`5a980548-a759-41d2-a566-58b7541e256b` reached switch-root. Its smoke check failed
on a source NetworkManager teardown race and early SSH timeout; full capture
is still active. Current V8 service state has not yet been authenticated.
Signed primary manifest:
`27f18d68cf2f7aaa791efb14de3ccc728506dca6b772b5ef006c890b3a787334`.
Other primary identities derive from the canonical expected record.

Installed boot-B loader unchanged:
`dcc487f17d6b4926ea633cbb242c62b598019e332640a81c1100c2d91087f723`.
Retained previous boot B:
`340f639276d9df3dfc073b8614a72f82507ea18c622c9df5d1e60f2c1622ccad`.
Signed V11 fallback manifest unchanged:
`a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2`.

Pinned USB SSH is `10.77.0.2`, alias `169.254.77.2`, fingerprint
`SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
V8 reached authenticated readiness in **98.215 s**. Local-root component PASS:
P24 RO/no replay, expected persistent overlay, 117 physical nodes, only
sda/sda23 writable, exact deployed userspace and current-boot readiness.
Wi-Fi, Tailscale and persistent-state services started. The full-hour load result is recorded below.

V8's experimental claim is permanently consumed, as are V6 and V7.
Do not retry their RAM execution or issue replacement claims. R01 armed the
accepted V8 record as pending; its exact healthy state was restored only after
fresh authenticated V11 and installed-file guards passed. The normal installed path is separate from a RAM
claim and does not constitute full release acceptance. V7's pending failure record and old
selector were archived during staged V8 installation. V5 accepted payloads,
prior claims, V11 fallback and the failed-soak scratch remain preserved.

## Proven startup correction

V7's CPU guard refused 62.4°C before applying any cap. Its CPU unit had waited
for tmpfiles because `PrivateTmp=yes` added an implicit dependency.
V8 uses `PrivateTmp=disconnected` plus inaccessible `/var/tmp`; all existing
power/storage guards and the 60°C thermal threshold remain unchanged.

Physical journal: CPU unit started at **20.654 s**, before tmpfiles at
**21.485 s**; policy application completed successfully. Verified maxima:
policy0 **1,209,600 kHz**, policy4/policy7 **1,555,200 kHz**.
Later read-only observation: all zones below 60°C, maximum **35.8°C**;
battery Full 100%, Good 29.8°C, 8.593 V, USB online, current 0.
This answers the startup question, not H03 regulation or a 60-minute load soak.

The cycle reused the existing kernel/DT/modules and boot wrapper. No flash.
Staging **2.126 s**, independent postcheck **0.747 s**, orderly V11-to-fastboot
transition **9.327 s**, exact fastboot battery 8.606 V / SOC gate yes.
Full capture completed **1,380.863 s**; route/firewall/profile/address cleanup
all PASS. No further phone execution was requested during that observation.

## Current checkpoint and next mandatory outcome

One coordinator owns this phone. S01–S05, S07 and F02 retain their completed
independent evidence. The failed R01 capture closed its full lifetime and all
host cleanup passed. A separate installed recovery capture is now running after
normal-address SSH timed out; its controller stopped before changing state.
Do not retry the consumed negative candidate or run a second phone controller.

On `f0a3420b`, full local CI passed **520.115 s** and all four jobs passed in
GitHub run **34214045938**: exact head, merge compatibility, publication and QEMU.
The original failed CI and USB-teardown capture remain preserved. The receiver
fix permits only precisely tagged ENOENT/ENODEV followed by positive absence
before target observation, within the existing 150 ms check. Identity mismatch,
permission errors, unresolved discovery and post-target loss still fail.

Fresh S01 reached authenticated local-root SSH in **93.193 s** and completed
its full **1,380.504 s** capture. Fresh S02 passed four 256 MiB USB/Wi-Fi transfer
directions in **303.671 s**; fresh S03 recovered all four services in **35.081 s**.
Both independent replay checks passed on that same boot. Earlier S03 r1/r2
remain FAIL; r3 and its actual producer revision are retained.

Fresh S04 passed **102.744 s**: one 64 MiB file was written/fsynced, survived
one ordinary reboot, read back with the expected hash and was cleaned by exact
file identity. SSH returned in **93.850 s**. The complete **1,380.582 s** capture
had no failed diagnostics, and its independent S01/S04 checks passed. The
original failed S04 capture is not relabeled. Its old scratch, the existing
acceptance namespace and unrelated files remain preserved.

S05 passed three distinct ordinary boots in **330.639 s**. Per-boot closed
observations took **103.910 / 102.807 / 103.412 s**; healthy-state observations
took **102.849 / 101.872 / 102.368 s**. Each started a full failure receiver
before one reboot request. Successful capture closure used the qualified full
S04 baseline plus the new exact healthy record; no failed boot was retried.
The independent three-boot checker passed. Kernel, DTB, signed archives,
installed boot B, selector and V11 fallback are unchanged.

On `af960758`, full local CI passed **526.883 s** and all four GitHub jobs
passed in **34221548267**. S07 then measured **3600.030 s** of combined load;
its full run completed **113 storage windows and 188 transfers**, each 64 MiB.
All workers stopped and exact scratch cleanup passed in **3666.628 s** overall.
The independent S07 checker passed in **68.277 s**. Old failed-soak scratch and
receipts remain preserved; this successful run has fresh identities throughout.

Across 367 heartbeat samples, maximum thermal-zone temperature was **51.4°C**,
battery temperature at most **30.8°C**, minimum pack voltage **8.413 V**.
Final power was Good, 30.8°C, 8.436 V. No new kernel messages appeared during
the measured load; ext4 error counters for loop1, sda23 and sda24 stayed zero.
Backing-device I/O and log continuity passed the original strict criteria.
This is endurance evidence; H03 retains its separate radio-free charging method.

Exact V8 F01 passed **85.412 s** using disposable networkless QEMU disks;
interrupted-update recovery succeeded and genuine corruption was rejected.
The original kernel/archive/root and protected fixture stayed unchanged.
F02 passed WPA/DHCP recovery in **29.141 s**, with three authenticated Wi-Fi
endpoint checks and unchanged radio/core service identities. Independent replay
passed; the sole coordinator closed in **30.104 s**.

The existing `headless-acceptance-rescue-v8` uses the same kernel and base Arch
root as the server. Its sealed runtime still matches all eight historical
runtime files. Fresh paired-root A01/C02 passed **66.261 / 76.473 s**. Its
September-6 original boot, capture, watchdog and 61 charging samples are retained;
the 600.265 s firmware-Full interval reproduces its original result offline.
That rescue claim remains consumed; signed V11 remains the independent fallback.

The dispatcher now supports an explicit `rescue_companion` receipt sharing
the primary's exact kernel and base-root files. Completed H01/H02/H03 replay
checks original producer versions, full capture/cleanup, paired composition,
raw samples and original boot/source identities. It grants no boot authority.
Portable and actual retained-data regressions passed; the integrated focused
suite passed **138 tests per mode in 20.793 s**.

On `be0a8d2e`, full local CI passed **533.795 s**, and all four GitHub jobs
passed in **34229955565**. One explicit paired receipt then passed H01/H02/H03,
S01–S05, S07 and F02 in **153.915 s**. Final source/artifact revalidation passed;
the original producer revisions and distinct rescue/server boots remain intact.
The rescue rows took **1.568 / 1.518 / 1.518 s**; S07 replay took **68.672 s**.
These are offline replay times, not fresh physical observations. Full release
qualification remains false; powered-off startup and controlled failed-boot
recovery remain outstanding.

R01 preparation confirmed that an ordinary watchdog reboot after a RAM-only
failure would still select healthy V8. That alone does not prove return to V11.
The existing trial helper offers a narrower preparation route: healthy-to-pending
rearming followed by a different trial's rejected health acknowledgment leaves
V11 selected at the next loader entry. The new regression passed on the host
and exact ARM64 helper, normally and optimized; all four 17-test suites passed
in **8.978 s** (one ARM-only test skipped in each host run). Retained V8 helper,
health and rollback bytes match current source; its outer timer is 900 seconds.
On `a1f9a10c`, full local CI passed **545.761 s**, and all four GitHub jobs
passed in **34232752925**. Unsigned `headless-recovery-negative-v1` target twins
then matched after **8.225 s**; only the trial descriptor and its checksum
manifest differ from accepted V8. Kernel, root, services and rollback are reused.
No signing, candidate registration, new claim or phone action has occurred.

The private V8 arming primitive passed six isolated ARM64 integration cases
normally and optimized, including namespace containment and lost-reply handling;
six synthetic guard tests per mode cover boot, power and storage refusals.
V11 has no Python, so restoration uses a separate sealed-shell generator.
Its six cases passed in **12.268 s** with the actual V11 BusyBox and canonical
ARM64 helper; kernel, sysfs and mount observations were explicit fixtures.
These are component tests only. A separate passive two-boot receiver now
preserves the original receiver's exact bytes and prior evidence bindings.
It requires an explicit canonical R01 fallback, a completed initial root
handover and positive USB absence before accepting one distinct rescue boot.
Premature/third-boot loss, wrong identity, unclassified teardown, networking
errors and earlier failures remain fatal; the capture lattice is unchanged.
Its 15 portable tests passed normally and optimized, and the original receiver's
33 tests passed. The receiver-only active checkpoint passed **47.789 s**.

The read-only negative-health observer requires the exact helper-refusal journal
sequence within the failed unit's execution, the unchanged installed pending
record, current-boot SSH/core readiness, sealed health/rollback bytes, an armed
900-second timer, and safe power/storage. Its nine focused tests include actual
bounded file reads and pathname replacement; malformed or unrelated failure
cannot qualify. Raw SSH output is retained before post-read topology checks,
including partial output on timeout. The one-shot controller, autonomous timer
stream and complete R01 evidence replay still need integration, followed by
signed packaging, admission and fresh physical preflight. No new phone action,
claim or full release qualification is implied by these observer components.
The combined active tier passed **45.383 s**; both focused suites also passed
optimized, with all recorded runtime/producer inputs unchanged. Full integration
CI and publication remain pending with the controller/evidence work.

Private rollback journal replay now checks the retained Arch catalog's fixed
service-job identifiers, the exact boot, PID 1, job ID, execution ordering and
callback deadline. Eight replay tests per mode and five shell cases passed;
the shell used the unsigned negative target's actual BusyBox timeout under
QEMU with explicit host/synthetic fixtures. The V8 source-to-fastboot RAM
shutdown delta also passed exact sealed-shell syntax and reversible byte checks.
It preserves teardown/poweroff and is separate from the unchanged negative
target shutdown. The first namespace fixture failure remains recorded; no live
transition, state arming, candidate execution or new claim has occurred.

The private controller ordering engine passed nine fault-injection cases per
Python mode. It fsyncs exclusive phase intents before callbacks, refuses phase
re-entry, preserves full capture after ambiguous execution, and requires a fresh
independent V11 guard before restoration plus a distinct healthy ordinary V8
boot afterward. User interruption permits cleanup without later mutations.
The generated source-side arming and RAM-transition scripts then passed eight
namespace execution cases in **0.640 s**, using the real ARM64 trial helper and
sealed BusyBox. Physical guard observations were explicit fixtures; a harmless
recorder replaced reboot. Genuine file metadata, exclusive publication, RAM
replacement, chroot syntax and mount-namespace containment were exercised.
Wrong state/source, symlinks, existing backup state and failed reboot replies
were handled without retry or changes to the original synthetic trial state.
The import-only private driver now implements every controller phase. Eleven
boundary tests cover raw reply retention, timeout/no-retry behavior, claim-account
selection, exact fastboot fields and the twelve-file installed inventory. The
inventory derives payload hashes from canonical primary/fallback manifests and
pins their signature companions. Local admission additionally requires the
exact six artifact roles, canonical restoration helper, unchanged producer
closure and exactly four successful CI jobs. Twenty-two admission cases passed
in **0.651 s**, using explicitly synthetic canonical/CI records and real file
pins, source hashes, primitive compilation and inventory derivation.

Actual driver restoration passed five namespace cases in **43.915 s**, using
the V11 BusyBox and ARM64 helper under QEMU. Lost staging/restoration replies
were not retried; exact fixture state and helper leftovers were retained. Five
execution-child cases passed in **1.217 s** with real disposable claim handling
and sealed-memory snapshots, while a harmless sink replaced fastboot. Failures
after consumption kept those fixture claims consumed. The real V8 claim was
checked read-only under its existing lifecycle account and stayed unchanged.

The offline R01 consumer and matrix dispatcher now accept a pinned completed
input envelope. They independently replay the full ordinary S01 prerequisite,
all raw controller commands, negative state/journal, two-boot capture and later
ordinary health. A regression caught consistent but wrong primary trial IDs;
those now refuse. The integrated checkpoint passed **60.500 s**, including
active **48.502 s**, with all inputs unchanged. Six subsequent tests exercised
the actual Driver/Core phase sequence and public replay with synthetic
transport/clock/admission in **6.581 s**; restoration never converted a failed
experiment into PASS. That checkpoint predates the reset-log binding.

Bounded reset diagnostics read only already-mounted pstore locations before
arming and after full capture on V11. Absence, unsupported mounts, read errors,
truncation and overflow are explicit; empty pstore never proves reset cause.
Twenty cases passed with both actual sealed BusyBox binaries in **6.347 s**.
They caught and corrected disabled glob expansion that had skipped present
records. The original failure and raw logs remain private; fixture bytes were
unchanged. Five public protocol tests cover malformed/stale/ambiguous evidence.

The latest combined checkpoint includes the reset-log binding and passed
**66.838 s**, including active **55.014 s**, with sources unchanged. All six
actual phase simulations passed again against the current producers; no real
transport, receiver process or claim was used.

The fixed root entrypoint now binds all nine private sources and hands closed
evidence to the desktop account only after every owned producer exits. Exact
primary/fallback manifests and signatures were verified from retained artifacts;
27 admission cases passed in **0.659 s**. The complete binding assessment
`r01-controller-bindings-r2` passed **0.103 s**, retaining compatible earlier
restoration coverage and the current full entrypoint simulations.

The full negative target cannot fit beside the unchanged ASUS kernel in the
existing 96 MiB RAM image. A separate R01-only helper requires an exact
**128 MiB** image, its canonical hash and consumed claim, plus a fresh single
unambiguous bootloader download-capacity response before consumption. Existing
96 MiB boot helpers and partition sizes remain unchanged. Seven helper tests,
twelve driver boundary tests, raw replay contradictions and the active suite
passed in **60.939 s** (active **55.566 s**). The actual 128 MiB execution child
passed five cases in **1.704 s**; six current lifecycle simulations passed
**6.976 s**. These use disposable claims and simulated transport, not a phone.

Signed twin packaging passed **24.182 s** with byte-identical outputs and sealed
signature verification. The recovery archive is 77,011,442 bytes; the padded
RAM boot image is exactly 134,217,728 bytes. Its canonical record now binds the
actual image, distinct negative trial and unchanged V11 fallback. Registration
consumer tests passed in both Python modes in **3.275 s**. Exact negative A01/C02/C01 subsequently passed
**77.695 / 96.128 / 134.995 s** on `b00a1b81`, retaining unchanged root/upper
bytes. Subsequent full integration CI and the physical result are recorded below.

The first exact negative A01 ran every functional check successfully but failed
its unchanged 120 s deadline at **146.582 s**. Root/upper hashes remained exact.
A read-only sparse-hash probe reproduced the entire accepted 34.36 GB logical
root digest in **20.903 s**, reading 4.19 GB and hashing 30.17 GB of holes as
zeros. A01 now reuses the already-tested C02 hasher for both root/upper checks
and records timings. The original failure is retained; the corrected exact
A01/C02/C01 run passed. Focused and active
validation passed **55.595 s** (active **55.430 s**), with source inputs unchanged.



Full integration on `c0025810` passed **532.692 s** locally and all four GitHub
jobs in **34266500765**; PR1 remains draft. The first controller stopped during
read-only preflight because its private userdata guard assumed `8:23`. Actual
userdata is `259:58`, with matching partition identity, geometry, mount and
inode. It made no state change or claim. Corrected private guards passed sealed
V11 shell/helper tests, full lifecycle simulations and connected read-only
preflight. All original failed evidence was preserved.

A fixed continuation then consumed the negative RAM claim once. The bootloader
accepted the exact 128 MiB image, but boot
`8f739c2f-c755-4ec7-8fc0-2f346d0fae1f` reported `final-storage FAIL` with
`ufs-q0-s0-j1-e0` before switch-root. It returned to fastboot. Full capture
closed at **1,380.488 s**, all four cleanup steps passed, and 60 files transferred
unchanged to the desktop reader. Independent replay refused qualification.
The journal count identifies one recovery match outside the allowed overlay
exception; it does not identify the filesystem or prove corruption/causality.
R01 is **FAIL**, with no autonomous V11 return and no experimental retry.

A separate normal installed boot reached V11 switch-root, but SSH to `10.77.0.2`
timed out. Its full capture closed with all cleanup checks passing. A pinned
read-only probe of `169.254.77.2` authenticated the same V11 boot and observed
the exact pending record, protected partitions read-only and safe power.
Fresh readiness, all twelve installed hashes and sealed storage/power guards
then passed. The existing helper restored V8 selection to its exact healthy
record and was removed. Assisted restoration cannot convert R01 to PASS.

The later ordinary reboot check could not connect to diagnostic SSH: the passive
receiver classified V11 as the source and skipped preparing its diagnostic
route. No reboot command reached the phone; the failed controller retains its
full observation window. A separately gated ordinary service check must first
verify closed evidence, unchanged source-boot continuity and healthy selection.

The repository observer duplicated the same `8:23`/`2071` assumption. Its
correction binds the runtime allocation to the exact userdata partition and
geometry, then matches mount and pending-record device IDs. A second observer
fix records terminal transport failures once per transition instead of flooding
the log on every poll. Both preserve strict failure classification and the full
capture lifetime. Full local CI for those two fixes passed **498.013 s** on
`91ff9e24`, with terminal completion and unchanged source. Two earlier checkout
setup failures are preserved; the pinned boot tools and canonical 12 KiB template
were restored from verified retained inputs.

Ordinary capture now prepares the diagnostic route before declaring the source
ready. It still rejects source stage frames and requires an observed disconnect
before accepting a new target. All **35** focused receiver/network tests pass,
including pending route convergence and permanent route failure. Full CI for
that correction passed **492.129 s** on `9d4cd138`, and all four GitHub jobs
passed in **34276164597**. A fresh ordinary reboot was then acknowledged and
V8 reached switch-root. During source teardown, repeated source route setup
raced `nmcli -g`; capture retained a permanent failure. The first normal-address
SSH probe then timed out, so the smoke controller is keeping its full lifetime.

The receiver now retains successful source-route preparation until an observed
disconnect instead of repeating NetworkManager setup during source shutdown.
Initial route failures remain fatal, source stages remain inadmissible, and new
target routing still runs after disconnect. A retained-event fixture reproduced
21 setup calls and the failure before the fix; all **36** receiver/network tests
pass after it. This final correction requires full integration CI. Current
service verification must use a fresh read after the failed controller closes,
without another reboot. Kernel, root/upper images, signed payloads and claims
remain unchanged.

## Mandatory results

Do not combine incompatible releases or simulation and physical evidence.

| Outcome | Current result / next action |
|---|---|
| A01 / C01 / C02 | V8 offline PASS; A01/C02 include complete retained upper |
| H01 / H02 | Explicit paired rescue replay PASS on `be0a8d2e`; original rescue boot retained |
| H03 regulation | Paired dispatcher PASS on `be0a8d2e`; all 61 original raw samples revalidated |
| S01 local startup | Fresh V8 full ordinary capture PASS on `f0a3420b`; latest 93.850 s to SSH |
| S02 transfers | Fresh V8 PASS on `f0a3420b`, four 256 MiB directions in 303.671 s |
| S03 service recovery | Fresh V8 PASS on `f0a3420b`, 35.081 s; earlier failures retained |
| S04 durability | Fresh V8 file and full capture PASS; original failed capture retained |
| S05 repeated boots | V8 three-boot sequence and independent replay PASS, 330.639 s |
| S06 powered-off start | NOT RUN |
| S07 combined load | V8 full 3600.030 s observation and independent replay PASS on `af960758` |
| F01 / F02 | Exact V8 F01 PASS 85.412 s; fresh F02 plus independent replay PASS, 29.141 s |
| R01 recovery | FAIL: early final-storage gate; negative claim consumed, full capture retained |

## Evidence, fast loop and retention

Use [development](development.md) for impact-based selection and cache reuse.
Full V8 A01/C01/C02 took **88.128/131.751/104.415 s**; unchanged artifacts reused.
Complete-upper correction `cdfe00572b81fca619231bdba26702bf8982667d` is pushed:
focused **18.252 s**, full local **533.553 s**, all four GitHub jobs PASS in
34172685138 (including exact-head/merge). Retain those original results; do not relabel them as testing later changed code.

Preserve the complete inactive upper snapshot used for composition:
`dff8988f3c2f4c5204d2e827114f63e54068acc530a75010dd2d522de3795388`.
Normal persistent state may change after boot; do not relabel the snapshot.
Private current work: `rog5-cpu-startup-20260908.kjE4IqCf`.
Detailed V6/V7 failures, V8 staging/runtime proof, fixture fixes, original
timings and exact retention procedures are in the
[existing dated report](../test-results/2026-09-05-headless-acceptance.md).

Home has about 6.6 GB free with the two isolated observer checkouts; preserve the 3 GiB reserve. V5's lossless reverse
delta and durable V7 base must stay together. Unique archives still occupy RAM:
no host reboot until retained safely. Never remove failed-soak scratch, accepted
payloads, private evidence or claims. Leave unrelated SteamOS CEF port 8081 alone.
Schedule heavy A01/C02 separately from full local CI; remote checks and bounded
independent preparation may overlap. No test deadline or release gate is reduced.
