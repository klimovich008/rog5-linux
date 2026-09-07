# ROG5 current state

Updated: 2026-09-07. S01–S04 batch passed on unchanged V4 artifacts.
S05's three ordinary boots, pinned dispatcher replay and full local CI passed.
All exact-head remote checks passed. S07's bounded soak worker is being
qualified; the server remains running and the hour-long test has not started.

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
Current authenticated boot: `24db7908-5479-4d1a-a9cd-eeccbf1cb564`.
Three consecutive installed boots reached exact root, pinned SSH and healthy
trial commits in **94.908/96.612/97.400 s**; total sequence **311.524 s**.
Post-capture-cleanup SSH/root check PASS **1.026 s** on the third boot.
Last telemetry: **Full/100%, Good, 29.8°C, 8.563 V, 0 mA**.
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
| S05 three boots | Physical sequence PASS 311.524 s; dispatcher PASS 0.315 s at `2efa7cdf` |
| S06 powered-off start | Requires verified off interval and physical start; ordinary reboot is not a substitute |
| S07 combined soak | Worker/observer and exact phone Python fixtures pass; frozen CI then physical hour pending |
| R01 recovery | Controlled isolated failed-boot qualification outstanding |

H03's firmware-Full method is already defined; absent charge-limit controls
are not a reason to repeat sysfs inventories or change charging controls.
Review the stated radio-inactive prerequisite before collecting a V4 series.
The first S03 SSH reconnect refusal is already fixed by bounded read-only
reconnect; do not restart services or re-review the kernel for that incident.

## Latest checkpoint and exact next action

Frozen S05 live source: `93d6ee17c5d93de9e44925c261538861cca133e0`.
`s05-three-boots-r1` is terminal: three requests, exit 0 each; three distinct
new boot IDs, healthy records, capture closure and all four host cleanup steps.
Each capture was armed for the full failure window before its ordinary reboot.
Only proven healthy startup allowed owned early closure; ambiguity or failure
would keep full observation and forbid another reboot. No new RAM claim, flash,
slot, GPT or raw-storage operation occurred. Do not repeat these boots.

The S05 consumer replays pinned full S01 baseline, actual preflights, commands,
raw root/health/stage evidence and closure. It checks original dependency bytes
and timing against the observed revision; replay is not a new physical run.
Private input: `s05-evidence-inputs-r1.json`, SHA-256
`7a9bc83e1ca7006992fe64de3f8d0fae1abec5a9d0f9b70fc068b4f41f526a7c`.
Do not count smoke evidence as full S01/R01 or final release qualification.

S05 consumer `2efa7cdf` is pushed; full local CI PASS **497.398 s**, dispatcher
PASS **0.315 s**, total unchanged-artifact assessment **49.920 s**.
Remote **34092855927** passed all four checks. S07's worker, observer and private
coordinator now have focused coverage; run one frozen local/exact-head checkpoint
before the combined load. S06 still needs physical
off/start conditions; do not silently substitute another ordinary reboot.
Full S04 evidence and the earlier failed R7 capture remain in the
[dated report](../test-results/2026-09-05-headless-acceptance.md).
The mutable GitHub merge-ref race is fixed and verified at `93d6ee17`; do not
reopen it without new evidence. No repository security setting was changed.

## Fast loop / validation checkpoint

Use [the proportional workflow](development.md) and the project fast-loop skill.
Impact/dependency selection admits only reviewed observer/userspace leaves to
the local development path; critical or unknown changes retain stronger checks.
Broader tiers include narrow tests. Development PASS is never release PASS.
Freeze active test inputs; batch fixes; reuse unchanged evidence with its
original source, not a newer label. No kernel/wrapper rebuild occurred here.

S05 smoke integration `93d6ee17`: full local CI **496.400 s**;
all four exact-head/merge/publication/QEMU jobs PASS **34088992649**.
Seven private coordinator failure/ownership tests passed normal/optimized.
The consumer's nine tests pass normal/optimized; 47 dispatcher, 12 existing
runtime, 14 durability and 35 selector/workflow regressions pass.
No kernel/module/wrapper rebuild; all five release artifact identities unchanged.
The impact/dependency selector checkpoint `d75359b7` and receiver correction
`884a1a41` remain complete. Historical timings and preserved failures are linked
from the dated report, not another active ledger.

S07 read-only preparation PASS **0.917 s** on the current boot: scratch namespace
absent, **3.974 GB** available, 726 contiguous kernel records, all three relevant
ext4 error counters present/zero, cache-advice support available. The early SPMI
WARN is the previously recorded boot warning, not a new failure. Private draft
worker tests pass on disposable filesystems; exact phone Python **3.14.7** tests
PASS **13.787 s** normal/optimized with verified `/run` tmpfs cleanup. All five
tested source hashes still match. No persistent soak write has run. Observer
tests cover logs, counters, actual I/O and the 3600/3900 s timing contract.
Four private coordinator tests pass normal/optimized, including refusal before
writes, ambiguity, endpoint mismatch and log loss. The private runner is
`s07-combined-soak-r1.py`; it must verify current full local and exact-head CI
before any credential use. Use one new private `/tmp` output directory because
home has only about 5 MiB above the 3 GiB reserve; retain raw logs and archive
them durably before host reboot. Do not delete build/evidence data or reduce the
reserve to run a test. Next freeze this batch, validate, then run S07 once.
