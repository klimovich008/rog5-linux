# ROG5 current state

Updated 2026-09-08: V8 runs local Arch with authenticated SSH and Wi-Fi.
Startup CPU limiting and the full-hour combined soak passed. Final qualification remains incomplete.

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

Running bundle `headless-server-selector-v8`, kernel `7.1.4-gf17befd4ef17`,
ordinary installed boot `af66d09d-f512-4954-a036-0904616e17af`.
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
Do not retry their RAM execution or issue replacement claims. V8's signed
healthy trial record permits the separately verified ordinary installed-boot
path; it is not full release acceptance. V7's pending failure record and old
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

One coordinator owns this phone. The full S04 observation and all three S05
boots are complete; their independent evidence checks passed. Every owned
receiver is stopped and its route/firewall/profile/address cleanup passed.
The full S07 soak and F02 restart sequence are also closed and independently
qualified. No phone coordinator is pending. Never repeat a consumed claim.

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
No negative candidate was built, registered or executed. The next recovery
experiment must first establish an isolated autonomous path offline.

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
| R01 recovery | Controlled isolated failed-boot qualification outstanding |

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

Home has about 6.07 GB free; preserve the 3 GiB reserve. V5's lossless reverse
delta and durable V7 base must stay together. Unique archives still occupy RAM:
no host reboot until retained safely. Never remove failed-soak scratch, accepted
payloads, private evidence or claims. Leave unrelated SteamOS CEF port 8081 alone.
Schedule heavy A01/C02 separately from full local CI; remote checks and bounded
independent preparation may overlap. No test deadline or release gate is reduced.
