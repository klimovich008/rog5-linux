# ROG5 current state

Updated 2026-09-08: V8 runs local Arch with authenticated SSH and Wi-Fi.
Startup CPU limiting passed. Final standalone qualification remains incomplete.

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
ordinary installed boot `d903328e-fa57-4625-bb88-7419e04d57b1`.
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
Wi-Fi, Tailscale and persistent-state services started. Endurance is not proven.

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

One coordinator owns this phone. S04's full observation has ended and all owned
host route/firewall/profile/address cleanup passed. No phone coordinator or
reboot is pending. The prepared S05 sequence has **not** been launched.

On `35bd1e6d`, full local CI passed **540.372 s** and all four jobs passed in
GitHub run **34209378375**: exact head, merge compatibility, publication and QEMU.
The preceding interrupted/invalidated and failed CI receipts remain preserved.
The native publication fixture deadline and runner signal-exit fixes are pushed.

S03 r3 passed fresh preflight **4.619 s**, all service recoveries **30.705 s**,
and independent evidence replay. Per-service durations: healthd **2.020 s**,
SSH **2.558 s**, WPA including DHCP **16.498 s**, DHCP **7.546 s**. The radio
unit remained unchanged; recovery stayed within the existing 40-second limits.
R1/r2 remain FAIL. This is physical V8 evidence on the preceding boot.

S04 wrote/fsynced one 64 MiB file, requested one ordinary installed reboot,
reached pinned SSH in **96.095 s**, verified the file and cleaned its exact
owned directory. Its file component passed **105.293 s**. The existing parent
namespace and old failed-soak scratch remain intact.

**S04 remains FAIL.** The full **1,380.774 s** capture recorded a host discovery
error before target observation: the anchored network interface's `driver`
symlink vanished during USB teardown. The immediate recheck was enumerating;
positive USB absence followed **100.313 ms** later. Later successful startup
and file readback cannot erase this failed diagnostic channel.

A filesystem regression reproduces the original failure. The host-only fix
classifies anchored USB/device/driver resolution failures as precisely as
USB descriptor reads. Only ENOENT/ENODEV followed by positive absence before
target observation can use the existing bounded 150 ms removal check.
Unresolved discovery, permission errors, identity mismatch, network failures
and post-target loss still fail; the original capture deadline is unchanged.
Receiver, rescue replay, ordinary startup and smoke replay share the same
explicit operation names. The 100 focused tests pass in both normal and optimized Python (**10.210 s**).
One full local/remote CI checkpoint must pass before a new ordinary-boot
baseline and remaining V8 qualification.
Retain original S01/S02/S03 receipts with their actual producer revision;
changed observer dependencies require fresh validation, not relabeling.

S07's one-hour worker integration is being prepared privately and offline.
It has not run and does not qualify S07. No kernel, DTB, signed archive,
installed boot image, rollback timer or target service has changed.

## Mandatory results

Do not combine incompatible releases or simulation and physical evidence.

| Outcome | Current result / next action |
|---|---|
| A01 / C01 / C02 | V8 offline PASS; A01/C02 include complete retained upper |
| H01 / H02 | Same-release radio-inactive rescue not qualified |
| H03 regulation | NOT RUN for final release; use defined firmware-Full method |
| S01 local startup | V8 ordinary installed local boot PASS, 91.585 s to SSH |
| S02 transfers | V8 PASS, four 256 MiB USB/Wi-Fi hash-verified directions |
| S03 service recovery | V8 r3 PASS on `35bd1e6d`; preserve exact original evidence |
| S04 durability | V8 file component PASS; full capture FAIL on host driver-link teardown race |
| S05 repeated boots | V5 three boots passed; V8 sequence NOT RUN |
| S06 powered-off start | NOT RUN |
| S07 combined load | NOT RUN for V8; prior capped 600 s diagnostic is not one-hour PASS |
| F01 / F02 | Retained offline passes; reuse only with exact dependency evidence |
| R01 recovery | Controlled isolated failed-boot qualification outstanding |

## Evidence, fast loop and retention

Use [development](development.md) for impact-based selection and cache reuse.
Full V8 A01/C01/C02 took **88.128/131.751/104.415 s**; unchanged artifacts reused.
Complete-upper correction `cdfe00572b81fca619231bdba26702bf8982667d` is pushed:
focused **18.252 s**, full local **533.553 s**, all four GitHub jobs PASS in
34172685138 (including exact-head/merge). Do not rerun for this docs-only handoff
or relabel those results as testing later changed code.

Preserve the complete inactive upper snapshot used for composition:
`dff8988f3c2f4c5204d2e827114f63e54068acc530a75010dd2d522de3795388`.
Normal persistent state may change after boot; do not relabel the snapshot.
Private current work: `rog5-cpu-startup-20260908.kjE4IqCf`.
Detailed V6/V7 failures, V8 staging/runtime proof, fixture fixes, original
timings and exact retention procedures are in the
[existing dated report](../test-results/2026-09-05-headless-acceptance.md).

Home has about 6.34 GB free; preserve the 3 GiB reserve. V5's lossless reverse
delta and durable V7 base must stay together. Unique archives still occupy RAM:
no host reboot until retained safely. Never remove failed-soak scratch, accepted
payloads, private evidence or claims. Leave unrelated SteamOS CEF port 8081 alone.
Schedule heavy A01/C02 separately from full local CI; remote checks and bounded
independent preparation may overlap. No test deadline or release gate is reduced.
