# ROG5 current state

Updated: 2026-09-07. S01–S04 batch qualification passed on unchanged V4
artifacts. The server is running; repeated-boot S05 qualification is next.

## Goal and authority

Qualify one reliable standalone headless Arch server using the existing
[acceptance contract](release-acceptance.md) and
[mandatory matrix](../configs/release-acceptance.json). Display is optional.
Use `rog5-dev accept`; missing, skipped or incomplete mandatory evidence is not PASS.
Keep unrelated work in [the backlog](../ROADMAP.md), not another review.

Exact phone: `M5AIKN00F0353YH`, product `lahaina`, anchored side USB `1-1.2`.
Preserve official WW33 slot A (`33.0210.0210.200`) for charging/rescue.
[Stock charging restoration](asus-charging-recovery.md) is complete.
Preserve identity/topology/slot/boot chain, signatures, power/thermal, bounded
storage/backups, independent fallback and experimental one-use protections.
No new flash, GPT or protected-data operation. New destructive storage needs
separately reviewed exact scope. Credentials/private evidence stay outside Git.
Ordinary accepted-release reboots are distinct from experimental claim retries.

## Installed release and current access

Bundle `headless-server-selector-v4`, kernel `7.1.4-gf17befd4ef17`.
Current authenticated boot: `7979945f-e6bc-46b6-aa5f-26091f1aed1c`.
The latest ordinary installed boot reached strict-key SSH/local root in
**87.113 s**; previous ordinary boots took **84.956/85.531/86.377 s**.
Post-capture-cleanup SSH/root check PASS **0.919 s** on the same new boot.
Last telemetry: **Full/100%, Good, 29.7°C, 8.566 V, 0 mA**.
This snapshot is not H03 charging-regulation qualification.

USB SSH: `10.77.0.2`, pinned alias `169.254.77.2`.
Host-key fingerprint: `SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
Native P24 lower is RO/norecovery; persistent upper and service-state images
remain on authorized P23. Attestation checks 117 block nodes and exact write scope.
S02 Wi-Fi/USB transfers and S03 service-restart evidence retain their original
boot/source identities; batch replay is not a new execution of those tests.

The approved boot-B replacement is **already complete**. Installed image:
`dcc487f17d6b4926ea633cbb242c62b598019e332640a81c1100c2d91087f723`.
Its rearming trial helper supports ordinary accepted-release reboot testing.
The old image and verified backups remain preserved:
`340f639276d9df3dfc073b8614a72f82507ea18c622c9df5d1e60f2c1622ccad`.
Signed V11 fallback manifest:
`a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2`.
Do not repeat the flash. V4's experimental claim is permanently consumed,
as are failed V2/V3 and rescue V8; runtime health never resets consumption.

## Artifact identity and retained work

V4 manifest:
`a6296549c855e3c8a1fd9c2e807e196207d1be4ff48fe36db4a2627528fd0966`.
Target archive:
`a5ff5c003b44cb073b78990487c8ffc810e6ef635e85c8b0ab40ab18b67e2e8f`.
Kernel Image:
`ece47c7d52627d390bccdbcdab23295fe795820c66174d8de41cbc221cbac74e`.
Other identities come from the canonical record and private release receipt.
Historical source/boot/backup identities remain in the
[dated report](../test-results/2026-09-05-headless-acceptance.md); do not relabel them.

Private work prefix: `rog5-server-hw11-20260906.Lo7km1SL`.
Preserve the combined module kit, signed package, V4 root preview and lossless
V2/V3 preview archives. Some inputs are volatile tmpfs: do not reboot the host
assuming they are durable. Keep 3 GiB disk reserve; no ad-hoc deletion.
Host port 8081 is the unrelated SteamOS CEF proxy; leave it untouched.

## Mandatory outcomes

These component results do **not** constitute one qualified final release.

| Outcome | Current evidence / next action |
|---|---|
| A01 V4 composition | PASS 106.750 s on signed bytes; lower-image VM alone does not reproduce Python installed in persistent upper |
| C01 watchdog handover | Nine cases PASS 133.953 s |
| C02 late SSH restart | PASS 82.750 s; original failed fixture preserved |
| F01 disposable recovery | Exact-input PASS 75.432 s; not physical crash/power-cut proof |
| F02 Wi-Fi restart | PASS replay 0.816 s on unchanged artifacts; original live source retained |
| H01/H02 | Capture/startup components exist; radio-inactive same-release H02 not qualified |
| H03 regulation | Earlier V8 Full-maintenance PASS, not a V4 same-release PASS |
| S01 local boot | Fresh full capture/cleanup PASS; dispatcher PASS 0.215 s at `e2cbf147` |
| S02 transfers | Physical PASS 298.494 s; unchanged evidence replay PASS 3.471 s |
| S03 service restarts | Physical PASS 33.648 s; dispatcher PASS 0.215 s |
| S04 durability | New file cycle PASS 95.589 s; full capture/cleanup and dispatcher PASS 0.465 s |
| S05–S07 | Three boots, powered-off start and 60-minute combined soak outstanding |
| R01 recovery | Controlled isolated failed-boot qualification outstanding |

H03's firmware-Full method is already defined; absent charge-limit controls
are not a reason to repeat sysfs inventories or change charging controls.
Review the stated radio-inactive prerequisite before collecting a V4 series.
The first S03 SSH reconnect refusal is already fixed by bounded read-only
reconnect; do not restart services or re-review the kernel for that incident.

## Latest checkpoint and exact next action

Frozen live/assessment source: `e2cbf147700d5588c929a86cefee1083e7e1a430`.
`s04-ordinary-boot-r2` is terminal: supervisor **1387.360 s**, receiver
**1380.604 s**, exit **0**. All four host cleanup steps passed. One new 64 MiB
owned file passed fsync/readback, one ordinary reboot, identical-hash readback
and exact cleanup. No scratch file/namespace remains; no flash, slot, GPT or
raw-storage action ran. The earlier R7 capture failure remains FAIL in the
[dated report](../test-results/2026-09-05-headless-acceptance.md); never retry it.

Private `s04-r2-batch-acceptance` records S01/S02/S03/S04 PASS, total **91.868 s**.
It batches unchanged artifact verification; older observations retain original
attribution. Unselected mandatory outcomes remain NOT RUN, `qualified=false`.
The 900-second rollback and complete independent capture were not shortened.

Next: bind the tested ordinary-smoke helpers to pinned evidence and the single
coordinator, then run S05's three-boot sequence. The full capture is 1380 s per boot, incompatible
with S05's 1080 s total deadline. Read-only evidence on the current boot confirms
the exact healthy record and successful trial commit at **58.603 s** target
uptime; no target watchdog/kernel change is indicated. A future smoke closure
must require same-release full-watchdog evidence, fresh current-boot health,
normal source→target continuity and complete cleanup. Failed/ambiguous boots
retain full recovery observation and prohibit another action. This shorter
mode is **not connected to live execution or qualified yet**; do not improvise it.
Do not count smoke evidence as full S01/R01 qualification or relax boot deadlines.

The new `ordinary-boot-smoke.py` component validates fresh healthy records,
safe closure/cleanup and three consecutive boots; 22 tests PASS normal/optimized.
Timing comes from `defaults.ordinary_smoke`, fitting the unchanged 1080 s budget.
It cannot grant S01/S05/release PASS. Full integration and exact-head CI are pending.
Documentation CI `34087645077` failed only merge checkout: the moving merge ref
resolved to a regenerated commit with the same parents. A failing regression now
passes with checkout pinned to the event's merge SHA; exact-head verification
and required checks remain intact. No phone action followed that CI failure.

## Fast loop / validation checkpoint

Use [the proportional workflow](development.md) and the project fast-loop skill.
Impact/dependency selection admits only reviewed observer/userspace leaves to
the local development path; critical or unknown changes retain stronger checks.
Broader tiers include narrow tests. Development PASS is never release PASS.
Freeze active test inputs; batch fixes; reuse unchanged evidence with its
original source, not a newer label. No kernel/wrapper rebuild occurred here.

S04 integration `e2cbf147`: 14 evidence tests PASS normal/optimized,
47 dispatcher and 12 runtime regressions PASS. Full local CI **523.219 s**;
all four exact-head/merge/publication/QEMU jobs PASS **34084953097**.
Exact current phone Python/tmpfs tests PASS **14.188 s**, cleanup verified.
No kernel/module/wrapper rebuild; do not rerun full CI for this narrative update.
The impact/dependency selector checkpoint `d75359b7` and receiver correction
`884a1a41` remain complete. Historical timings and preserved failures are linked
from the dated report, not another active ledger.
