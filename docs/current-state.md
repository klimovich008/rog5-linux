# ROG5 current state

Updated: 2026-09-07. Authoritative handoff; live capture is still running.

## Active goal and scope

Qualify one reliable standalone headless Arch server under the existing
[acceptance contract](release-acceptance.md) and
[mandatory manifest](../configs/release-acceptance.json).
Use `scripts/host/rog5-dev accept`; missing prerequisites, skipped mandatory
tests and lost transport are not PASS. Display remains optional.
Use the [development loop](development.md); unrelated findings belong in the
[backlog](../ROADMAP.md). Do not reopen completed reviews without new evidence.

## Exact device and authority

Phone `M5AIKN00F0353YH`, product `lahaina`, anchored side USB `1-1.2`.
Preserve official WW33 slot A (`33.0210.0210.200`) as charging/rescue.
[Stock charging restoration](asus-charging-recovery.md) is complete.
Keep identity/slot/topology/boot-chain, signatures, battery/thermal,
bounded storage/backups, independent rollback and experimental one-use guards.
No experimental flash, GPT or protected-data change. New destructive storage
requires separately reviewed exact scope and approval. Scoped credentials and
reversible diagnostics remain authorized; private material stays outside Git.
Do not delete unique source, artifacts, credentials, evidence or fallback.

## Running server and installed recovery

**V4 is running successfully from its sole RAM-only execution.**
Bundle `headless-server-selector-v4`, kernel `7.1.4-gf17befd4ef17`,
authenticated boot UUID `17ff6c19-3ed1-4441-92ef-b6bdbfacfeb8`.
Pinned normal SSH became ready in **84.957 s**. The physical hw1.1 correction
worked: ath11k firmware/PHY started, Wi-Fi associated and received an address.
Persistent state/SSH identity, Wi-Fi WPA/DHCP, healthd and Tailscale are active.
The exact same-boot healthy record and persistent trial state are verified.
The trial helper stopped the startup rollback timers after healthy acceptance.

V4's execution claim remains **permanently consumed**, even though its runtime
trial is healthy. These are different states; never reexecute the RAM claim.
Failed V2/V3 and rescue V8 also remain consumed. Earlier narratives and exact
identities are retained in the [dated report](../test-results/2026-09-05-headless-acceptance.md).

Pinned SSH: `10.77.0.2` (alias `169.254.77.2`), fingerprint
`SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
Native lower P24 is RO/norecovery; persistent upper and service state use the
existing bounded P23 images. Startup attestation: 117 block nodes, only the
accepted write scope, zero UFS errors and strict-key-only SSH.
Pre-staging P24 snapshot `e1692971646809ff412363014d69a363aa543336a715e918ec0cc978cafa36c6`
is historical, not a hash of the now-staged physical partition.

**Installed boot B is still old/unqualified recovery:**
`340f639276d9df3dfc073b8614a72f82507ea18c622c9df5d1e60f2c1622ccad`.
Its older trial helper does not rearm a previously healthy primary before the
next attempt. Existing offline evidence already demonstrates the defect.
Do not perform an ordinary reboot or rediscover it with another uncontrolled
phone failure. Signed V11 fallback and stock A remain preserved.
Fallback manifest:
`a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2`.

## Current exact artifacts and evidence

V4 manifest:
`a6296549c855e3c8a1fd9c2e807e196207d1be4ff48fe36db4a2627528fd0966`.
Target archive:
`a5ff5c003b44cb073b78990487c8ffc810e6ef635e85c8b0ab40ab18b67e2e8f`.
Selector:
`4c84b0c137408dbababe161f392fb9b0507e6bbad12050e7ab3ba6e30b44895a`.
Image:
`ece47c7d52627d390bccdbcdab23295fe795820c66174d8de41cbc221cbac74e`.
RAM wrapper:
`dcc487f17d6b4926ea633cbb242c62b598019e332640a81c1100c2d91087f723`.
Other hashes derive from the canonical record and private deployment receipt;
do not create another manual identity source.

Private current work: `rog5-server-hw11-20260906.Lo7km1SL`.
`live-r1`, `publication.json`, `deployed-r1`, `server-snapshot-r1` and
`stage` bind the actual bytes, source, physical boot, backups and readbacks.
The sole supervisor remains active for its fixed 1380-second capture window.
Do not restart it, shorten the window or change its loaded inputs.
Live source is **`3e90756f936f44df8d495695d3890a58c00ca646`**;
all four GitHub jobs passed run **34063760646** before staging/execution.
Later documentation does not relabel that source or create new authority.

## Acceptance matrix and remaining blocker

These are component outcomes, **not a coherent final server PASS**.

| Outcome | Result / next action |
|---|---|
| V4 A01 composition | PASS 106.750 s on exact signed bytes |
| V4 C01 watchdog handover | Nine cases PASS 133.953 s |
| V4 C02 late SSH restart | Both cases PASS 82.750 s on clean `a86c228c`; original fixture FAIL retained |
| V4 staging / readback | PASS 2.124 / 0.538 s; P24 relocked, old records preserved |
| V4 server startup | Pinned SSH PASS 84.957 s; radio and same-boot healthy trial proven |
| V4 deployed userspace | Six exact files PASS 0.297 s; component snapshot PASS 0.379 s |
| H01/H02 completed capture | Preboot capture verified; final timeline/cleanup not yet evaluated |
| H03 regulation | Earlier V8 Full-maintenance PASS; not a same-release V4 PASS |
| F01 disposable recovery | Prior exact-input PASS 75.432 s; not physical UFS crash proof |
| S01 standalone boot | BLOCKED on qualified installed recovery; current boot used host fastboot |
| S02–S07 | Final transfers/restarts/durability/three boots/off-start/60-minute soak incomplete |
| R01 physical recovery | Controlled isolated failure qualification outstanding; no installed corruption |

Latest V4 component telemetry: Full/100%, Good, 29.8°C, about 8.581 V,
zero battery current, USB online supplying 253 mA below reported 500 mA.
Earlier startup briefly drew battery current; these snapshots are not a
10-minute H03 series. H03's firmware-Full protocol is already defined;
unsupported charge-limit controls are not a blocker and none were written.
The existing H03 rescue protocol requires inactive Wi-Fi; do not call this
radio-active snapshot a qualifying substitute or collect the same absent fields.

## Exact next action and development loop

Finish the existing passive capture and evaluate its original startup/cleanup
evidence. Keep this healthy server accessible; no ordinary reboot.
Then advance S01/R01 from the retained installed-helper-v1 versus tested-v2
comparison and exact working wrapper. A reviewed, verified installed recovery
path must precede autonomous repeated boots. Do not start a new architecture
review, invent another charging/kernel fix or flash an experimental payload.
The physical hw1.1 issue is closed for this boot; full networking qualification
and repeatability are separate acceptance outcomes.

Current-state/skills cleanup is complete. Use focused reproduction for proven
bugs and full investigation only for unexplained/repeated/cross-component ones.
Run active/focused checks during edits; full CI once for relevant integration.
Current active PASS **20.650 s**. Full local CI on unchanged production
`8a9c0318` PASS **507.876 s**, explicitly reused across reviewed test/docs-only
changes with checked receipts; current exact-head remote CI remains separate.
No kernel/wrapper rebuild was needed for the C02 fixture correction.

Preserve the combined kernel/module kit, signed package, V4 root preview and
lossless V2/V3 preview archives. Some are volatile tmpfs; do not reboot the host
assuming they are durable. Keep 3 GiB disk reserve; no ad-hoc deletion.
See the dated report for restoration commands, peak sizes and prior failures.
