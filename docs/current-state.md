# ROG5 current state

Updated: 2026-09-07. S01–S04 batch passed on unchanged V4 artifacts.
S05's three ordinary boots, pinned dispatcher replay and full local CI passed.
S07 remains FAIL: its thermal refusal is unexplained. A bounded Wi-Fi on/off/on
comparison supports power-save-off as a server-mode mitigation; both transfers
then passed. The userspace/initramfs correction is implemented, not installed.
V4 remains running with power saving ON. V5's signed bundle/selector is staged;
old V4 selector/trial and signed fallback are preserved, and P24 is read-only.
No V5 admission, live claim or boot yet. Preserve the failed soak's scratch file.
V5 C02 guest cases passed but its total 121.667 s exceeded the 120 s deadline.
The sparse-root hash fixture correction needs a new C02 run; no kernel change.

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
Latest read-only diagnostic: **Good, 29.8°C, 8.532 V, 99%, Full**, USB online,
reported current zero, same authenticated boot. Healthy service is active/exited;
both boot rollback timers are inactive. Staging archived the exact healthy V4
trial after P24 relock; the active trial pathname is intentionally absent until
the first admitted V5 boot. Do not restart the old health writer or repeat staging.
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
| A01 V5 composition | PASS 103.346 s on exact signed target, reused wrapper and paired lower image; not physical qualification |
| C01 watchdog handover | Nine cases PASS 133.953 s |
| C02 V5 late SSH restart | FAIL 121.667 s total despite both guest cases passing; new sparse-hash fixture needs qualification |
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
| S07 combined soak | FAIL; mitigation staged, not running. Qualify V5 watchdog/boot then endurance; thermal cause and preserved scratch remain outstanding |
| R01 recovery | Controlled isolated failed-boot qualification outstanding |

H03's firmware-Full method is already defined; absent charge-limit controls
are not a reason to repeat sysfs inventories or change charging controls.
Review the stated radio-inactive prerequisite before collecting a V4 series.
The first S03 SSH reconnect refusal is already fixed by bounded read-only
reconnect; do not restart services or re-review the kernel for that incident.

## Latest checkpoint and exact next action

S07's exact rejected thermal sample is irrecoverable; improved logging is qualified.
The retained Wi-Fi crossover and successful guarded transfers support a power-save
mitigation, not a unique driver/AP root cause. Earlier experiments and timings are
in the dated report. USB remained healthy; the failed scratch file is preserved.

Source now sets/verifies power-save OFF during server Wi-Fi preparation/restart.
An authenticated ISC-licensed `iw` package is included in the target composition;
the existing musl/libnl, kernel, firmware and module bytes remain unchanged.
V5 private work `rog5-server-wifi-ps-20260907.aSQZz23O` contains the canonical
plan/recipe, signed package, paired preview, A01 and registration results.
At clean `09d22f9d`, A01 and full local/exact-head/merge integration pass.
Healthy-V4 staging PASS **2.223 s**, independent postcheck **0.659 s** at
`779c3173`. The exact Arch lock tests and coordinator replay passed. Deployed
utilities differ from the retained lower image: the final lock proof uses the
authenticated deployed snapshot, not mismatching lower-only binaries.
Next qualify C02 with the corrected fixture, complete required watchdog bindings,
then use the existing supervised transition/admission path for one V5 boot.
Signing, registration and staging alone do not grant boot authority.
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

`09d22f9d`: focused registry normal/optimized PASS **8.875 s**, full local CI
PASS **516.936 s**, all four remote jobs **34121734062** PASS. A01 **103.346 s**.
The preceding selector integration took **503.225 s**; full qualification is
not claimed faster. Reviewed narrative-only checks take **34.958 s** locally;
mixed critical deltas and full PR scope stay broad. Eligible isolated development
experiments avoid unrelated remote waiting, never release gates.
V5 target twins **8.375 s**, sealed syntax **0.727 s**, signing/verifier
**4.649 s**, wrapper-reuse check **0.474 s**, paired preview **62.105 s**.
No kernel/wrapper rebuild. Full identities and original test revisions remain
in the canonical record/private receipts and dated report, not relabelled.
Current-head remote **34123896043** also passed all four jobs at `779c3173`.
The new C02 fixture hashes every logical byte but avoids reading known sparse
zero holes; unsupported filesystems use full reads. Focused tests **24 PASS**,
optimized hash tests **5 PASS**. Full-image digest matched in **21.601 s**;
before/after verification and the 120 s limit remain mandatory. C02 is not yet PASS.

The V5 preview occupies **4.063 GB**; disk headroom remains close to the **3 GiB**
reserve. Recheck capacity before further outputs. Old previews/module-cache inputs
are losslessly archived; exact restoration records are under the private work
prefixes linked in the dated report. Restore old cache paths before using them.
Some archives and active outputs remain volatile tmpfs, not durable backups.
Do not reboot the host yet. No unique evidence or accepted image was discarded.
