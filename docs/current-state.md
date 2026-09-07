# ROG5 current state

Updated: 2026-09-07. S01–S04 batch passed on unchanged V4 artifacts.
S05's three ordinary boots, pinned dispatcher replay and full local CI passed.
All exact-head remote checks passed. S07 remains FAIL: its thermal refusal is
unexplained; separate Wi-Fi diagnostics now prove intermittent TCP-connect loss.
The server remains running; USB closure and cached/uncached reads passed.
Preserve the scratch file; investigate Wi-Fi delivery, not another blind soak.

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
Latest read-only diagnostic: **Good, 29.8°C, 8.534 V**, same authenticated boot.
The failed soak's scratch namespace remains intentionally preserved.
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
| S07 combined soak | FAIL: thermal refusal unexplained; separate Wi-Fi connects time out before authentication. Next: isolate wireless delivery delay; retain guards and scratch |
| R01 recovery | Controlled isolated failed-boot qualification outstanding |

H03's firmware-Full method is already defined; absent charge-limit controls
are not a reason to repeat sysfs inventories or change charging controls.
Review the stated radio-inactive prerequisite before collecting a V4 series.
The first S03 SSH reconnect refusal is already fixed by bounded read-only
reconnect; do not restart services or re-review the kernel for that incident.

## Latest checkpoint and exact next action

S05's three boots and the S07 buffered-loop correction are complete; their
source identities and original evidence remain in the dated report. Do not
repeat those tests or reopen the fixed merge-ref race without new evidence.
S07 r2 failed a Wi-Fi upload with lost stderr. r3 stopped after **383.599 s** at
the storage thermal guard; the rejected numeric sample is irrecoverable.
No new kernel records or ext4 errors appeared in captured data. The last file
is preserved and fully hash-verified. All diagnostic workers are stopped.

On unchanged V4 artifacts and source `1b37755b`:

- idle: 60 samples / 30 seconds, peak **35.5°C**;
- cached read/hash: 119 readbacks / **181.828 s**, 357 samples, peak **36.8°C**;
- uncached reads: 111 readbacks / **181.269 s**, 315 samples, peak **42.1°C**;
  **7,449,083,904 bytes** read on both loop1 and UFS, loop writes unchanged.

These are component observations, not S07 or H03 qualification. Subsequent
Wi-Fi-only diagnostics at `89348350` retained exact stderr: one 64 MiB upload
passed in **43.007 s** (peak 37.8°C), but the next connect timed out in **3.008 s**.
A second instrumented attempt also timed out before upload data; phone packet
capture saw no packets, with zero capture drops. A separate successful connect
took **2.055 s**: duplicate SYNs arrived together about 1.8 s after capture began,
then SYN-ACK followed within 0.2 ms. This validates the observer, not the timeout.
USB stayed healthy; no new captured kernel/ext4 errors or boot change.
Host Wi-Fi power saving is on; phone power-save state is not yet observed.
Do not infer which wireless endpoint/AP caused the delay or raise deadlines.
Next obtain the phone's read-only nl80211 power-save state, then choose one
bounded single-variable experiment. No charging/service/storage control changes.
Keep the 60°C guard and original soak duration; detailed evidence is in the report.
Opus review was unavailable because OAuth expired; continue independent work.
S06 needs physical off/start conditions, not another ordinary reboot.

## Fast loop / validation checkpoint

Use [the proportional workflow](development.md) and the project fast-loop skill.
Impact/dependency selection admits only reviewed observer/userspace leaves to
the local development path; critical or unknown changes retain stronger checks.
Broader tiers include narrow tests. Development PASS is never release PASS.
Freeze active test inputs; batch fixes; reuse unchanged evidence with its
original source, not a newer label. No kernel/wrapper rebuild occurred here.

`1b37755ba4710594564d0e0d44f547f4dbf4439a`: full local CI **516.841 s** and
all four remote jobs **34105698682** PASS. Local/remote checks overlapped.
Eight error-evidence worker tests pass normal/optimized **3.156/3.181 s**;
exact phone Python fixtures pass **14.106 s**, owned tmpfs cleanup verified.
Only the actual rejected thermal/power sample is logged; the original guard
and exception remain. No kernel/module/wrapper rebuild or changed release bytes.
Read-only inspection was corrected from 1024 full guard snapshots per file to
the qualified half-second cadence: **30-second timeout → 0.920 s**; forced
start/end checks remain. All historical results and archive hashes are in the
dated report; no older run is relabelled as testing a newer source revision.
`89348350`: selected documentation active checks **53.476 s**, remote
**34108234266** PASS. Unchanged full/kernel checks were reused with their
original identities; diagnostic parser tests also passed on exact target Python.
Keep the 3 GiB host reserve. Ignored Python caches were moved recoverably to
tmpfs, plus one old 66.5 MB kallsyms intermediate (hash verified); final build
artifacts/source/evidence remain intact. Use private tmpfs for new test logs,
then verify a durable archive before reboot. Do not repeat unchanged suites.
