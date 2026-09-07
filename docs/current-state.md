# ROG5 current state

Updated: 2026-09-07. S01–S04 batch passed on unchanged V4 artifacts.
S05's three ordinary boots, pinned dispatcher replay and full local CI passed.
S07 remains FAIL: its thermal refusal is unexplained. A bounded Wi-Fi on/off/on
comparison supports power-save-off as a server-mode mitigation; both transfers
then passed. The userspace/initramfs correction is implemented, not installed.
The accepted server remains running with power saving restored to ON.
V5 unsigned target twins are prepared; preserve the scratch file and qualify
the new signed composition before another soak. No V5 claim or boot yet.

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
Preserve the combined module kit, signed package and lossless V2/V3/V4 preview
archives. V4's raw preview is now archived, not at its old path. Some inputs are
volatile tmpfs: do not reboot the host
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
| S07 combined soak | FAIL; power-save mitigation source-only. Qualify refreshed target composition, then resume endurance; thermal cause and preserved scratch remain outstanding |
| R01 recovery | Controlled isolated failed-boot qualification outstanding |

H03's firmware-Full method is already defined; absent charge-limit controls
are not a reason to repeat sysfs inventories or change charging controls.
Review the stated radio-inactive prerequisite before collecting a V4 series.
The first S03 SSH reconnect refusal is already fixed by bounded read-only
reconnect; do not restart services or re-review the kernel for that incident.

## Latest checkpoint and exact next action

S05, buffered-loop correction and cached/uncached thermal isolation are complete;
retain their original evidence in the dated report rather than repeating them.
S07's exact rejected thermal sample is irrecoverable; improved logging is qualified.
Separate packet/SSH observations located intermittent pre-authentication loss,
not a proven kernel cause. USB stayed healthy, with no new captured kernel/ext4
errors. The failed scratch file remains preserved and hash-verified.
The read-only nl80211 query confirmed phone power saving ON. With host settings
unchanged, connection failures were **2/8 ON → 0/8 OFF → 1/8 ON**. OFF connections
all completed below 0.6 s. A separate guarded OFF window passed 64 MiB upload /
download in **40.996/27.553 s**, peak below 37°C; ON restoration and USB closure
passed. This supports a mitigation, not a complete driver/AP root-cause claim.
All temporary controls/helpers were restored/removed; installed files are unchanged.

Source now sets/verifies power-save OFF during server Wi-Fi preparation/restart.
An authenticated ISC-licensed `iw` package is included in the target composition;
the existing musl/libnl, kernel, firmware and module bytes remain unchanged.
Full local/exact-head integration passes. V5 unsigned twins are ready in private
work `rog5-server-wifi-ps-20260907.aSQZz23O`; use its plan, recipe and build receipt.
Next sign/package through the existing workflow, prepare the paired preview
from the verified V4 archive, and run exact A01 before admission or staging.
Do not compare the V4 runtime with the newly edited
source and call the intentional difference corruption; use its retained receipt.
No new boot claim was issued. Keep the 60°C guard and full soak requirement.
Opus review was unavailable because OAuth expired; continue independent work.
S06 needs physical off/start conditions, not another ordinary reboot.

## Fast loop / validation checkpoint

Use [the proportional workflow](development.md) and the project fast-loop skill.
Impact/dependency selection admits only reviewed observer/userspace leaves to
the local development path; critical or unknown changes retain stronger checks.
Broader tiers include narrow tests. Development PASS is never release PASS.
Freeze active test inputs; batch fixes; reuse unchanged evidence with its
original source, not a newer label. No kernel/wrapper rebuild occurred here.

`fa500750`: full local CI **503.225 s**, all four remote jobs **34118625377** PASS.
Selector regressions: 36 PASS normal/optimized **0.746/0.656 s**. The single
reviewed narrative now selects active checks in CI as well as development;
other evidence, unknown paths, mixed critical deltas and full PR scope stay broad.
V5 unsigned twins PASS **8.375 s**, **110.617 MB**; exact sealed syntax PASS
**0.727 s**. Archive:
`c4044bd28a5c9bbfb18ef77113aee4cd3bb56e5ab78350bb2454926d830fbfc0`.
Actual-base tool/library check PASS **4.532 s**; not A01/device qualification.
The extra VM component was interrupted before guest execution: NOT RUN.
Older test/source/incident identities remain in the dated report, not relabelled.

Capacity recovered by verified lossless retention: old temporary source/build
copies (**2.874 GB**) and V4 raw preview (**3.971 GB**) released only after full
archive comparison/restoration hashing. Archives and restoration records remain;
no unique information, phone data or accepted image was discarded. `/run` now
has about **5.02 GB** free. Preserve **3 GiB** on disk and recheck RAM/swap before
the next preview. Restore the old source/build cache before any builder using it.
Private prefix `rog5-server-hw11-20260906.Lo7km1SL` owns both retention records;
archives remain volatile tmpfs, not durable backups. Do not reboot the host yet.
