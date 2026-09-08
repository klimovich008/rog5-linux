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
boot `5b3cbfec-7cca-4ed2-bcbb-6dd84bea8f2a`.
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

## Next mandatory outcome

**S01: qualify one ordinary installed-release boot without host boot services.**
Before requesting it, finish qualification and publication of the bounded
complete-upper acceptance-consumer correction. Older consumers expected five
hashes; V8's A01 correctly includes the retained upper as a sixth composition
input. The correction propagates that exact hash through F02/S01–S05 and
rejects missing/altered upper records; it changes no phone payload or policy.

Proposed normal/optimized focused checks passed **18.252 s** in an isolated
filesystem view while the real repository/capture inputs remained frozen.
Run one full local CI plus required exact-head/merge checks at the integration
checkpoint. Rebind ordinary-boot preparation to that tested source; do not
execute the old-source adapter unchanged or relabel historical CI.
Keep the existing one-coordinator capture, healthy/installed/fallback/power
checks and ordinary-reboot semantics. No new experimental candidate is needed.

## Mandatory results

Do not combine incompatible releases or simulation and physical evidence.

| Outcome | Current result / next action |
|---|---|
| A01 / C01 / C02 | V8 offline PASS; A01/C02 include complete retained upper |
| H01 / H02 | Same-release radio-inactive rescue not qualified |
| H03 regulation | NOT RUN for final release; use defined firmware-Full method |
| S01 local startup | V8 startup/root component PASS; ordinary installed boot still required |
| S02 / S03 | Transfers/restart recovery were V5-only; qualify V8 |
| S04 durability | V5-only; preserve prior failed-soak scratch and qualify V8 |
| S05 repeated boots | V5 three boots passed; V8 sequence NOT RUN |
| S06 powered-off start | NOT RUN |
| S07 combined load | NOT RUN for V8; prior capped 600 s diagnostic is not one-hour PASS |
| F01 / F02 | Retained offline passes; reuse only with exact dependency evidence |
| R01 recovery | Controlled isolated failed-boot qualification outstanding |

## Evidence, fast loop and retention

Use [development](development.md) for impact-based selection and cache reuse.
Full V8 A01/C01/C02 took **88.128/131.751/104.415 s**. Full local CI at
`c389e0dfb2cc01be02e46a590f2b3a07a98bb2b9` passed **560.697 s**; all four remote
jobs passed in 34169434998. Docs-only execution checkpoint
`1a934b08dee27e800807563b7742ad7b0b1a6935` passed all four jobs in 34170256521.
These are their original source identities, not proof of newer code.

Preserve the complete inactive upper snapshot used for composition:
`dff8988f3c2f4c5204d2e827114f63e54068acc530a75010dd2d522de3795388`.
Normal persistent state may change after boot; do not relabel the snapshot.
Private current work: `rog5-cpu-startup-20260908.kjE4IqCf`.
Detailed V6/V7 failures, V8 staging/runtime proof, fixture fixes, original
timings and exact retention procedures are in the
[existing dated report](../test-results/2026-09-05-headless-acceptance.md).

Home has about 3.26 GB free; preserve the 3 GiB reserve. V5's lossless reverse
delta and durable V7 base must stay together. Unique archives still occupy RAM:
no host reboot until retained safely. Never remove failed-soak scratch, accepted
payloads, private evidence or claims. Leave unrelated SteamOS CEF port 8081 alone.
Schedule heavy A01/C02 separately from full local CI; remote checks and bounded
independent preparation may overlap. No test deadline or release gate is reduced.
