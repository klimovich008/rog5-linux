# ROG5 current state

Updated: 2026-09-07. S04 file/reboot/readback passed; full qualification remains
blocked by a pre-target host capture classification. The phone is accessible.

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
Current authenticated boot: `355266ac-6ec4-4880-8fa7-a2e2d6589dad`.
The latest ordinary installed boot reached strict-key SSH/local root in
**86.377 s**; the preceding ordinary boot took **85.531 s**.
Post-capture-cleanup SSH/root check PASS **0.780 s** on the same new boot.
Last telemetry: **Full/100%, Good, 29.9°C, 8.567 V, -7 mA**, USB online.
This snapshot is not H03 charging-regulation qualification.

USB SSH: `10.77.0.2`, pinned alias `169.254.77.2`.
Host-key fingerprint: `SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
Native P24 lower is RO/norecovery; persistent upper and service-state images
remain on authorized P23. Attestation checks 117 block nodes and exact write scope.
Wi-Fi transfers, service restarts and Tailscale previously worked; do not
relabel those observations as fresh tests on the latest boot.

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
| S01 local boot | Earlier complete acceptance PASS 0.266 s; latest boot capture returned FAIL as described below |
| S02 transfers | Physical PASS 298.494 s; dispatcher PASS 3.522 s |
| S03 service restarts | Physical PASS 33.648 s; dispatcher PASS 0.215 s |
| S04 durability | Physical file component PASS 93.252 s; full capture/dispatcher qualification incomplete |
| S05–S07 | Three boots, powered-off start and 60-minute combined soak outstanding |
| R01 recovery | Controlled isolated failed-boot qualification outstanding |

H03's firmware-Full method is already defined; absent charge-limit controls
are not a reason to repeat sysfs inventories or change charging controls.
Review the stated radio-inactive prerequisite before collecting a V4 series.
The first S03 SSH reconnect refusal is already fixed by bounded read-only
reconnect; do not restart services or re-review the kernel for that incident.

## Latest S04 cycle and exact next action

Frozen live source: `23afc6a497db56be1d0ce5af6225359e8ee24af4`.
`s04-ordinary-boot-r1` is terminal: supervisor **1387.232 s**,
receiver **1380.780 s**, receiver return **1**. Never restart this operation.
One 64 MiB owned file passed fsync, initial readback, one ordinary reboot,
identical-hash readback and exact cleanup. No scratch file/namespace remains.
No flash, slot, repartition or raw-storage command was performed.
All route/firewall/profile/address cleanup steps passed.

The sole capture failure was a tagged USB `product` read ENODEV during recovery
teardown, before target observation. Its immediate follow-up was recorded as
`enumerating`; the next poll saw `absent`, then the exact native NCM target.
Independent udev records the anchored parent removal at that transition.
The old receiver only tolerates a tagged read error followed immediately by
`absent`. Preserve its actual FAIL; later SSH alone cannot erase it.
See private capture/events, USB udev trace and the dated report.

Offline reproduction now covers this expected teardown. The correction allows
up to three read-only rechecks within 150 ms, capped by the capture deadline;
only classified pre-target descriptor loss followed by actual absence qualifies.
Unclassified errors and identity/network/post-target failures remain fatal.
Next: frozen integration checks, then the next independently required ordinary
boot using fresh evidence. Do not boot merely to fix this parser or relabel the
old capture. Changing this producer invalidates old S01 dependency reuse.
The S04 replay draft and synthetic tests are private; the pending integration
patch is **not applied**. Its complete-evidence builder correctly refuses the
failed capture. Resolve that evidence question before admission/qualification.
The old scratch plan is bound to the prior boot; do not reuse it on this boot.

## Fast loop / validation checkpoint

Use [the proportional workflow](development.md) and the project fast-loop skill.
Impact/dependency selection admits only reviewed observer/userspace leaves to
the local development path; critical or unknown changes retain stronger checks.
Broader tiers include narrow tests. Development PASS is never release PASS.
Freeze active test inputs; batch fixes; reuse unchanged evidence with its
original source, not a newer label. No kernel/wrapper rebuild occurred here.

At `23afc6a4`: 27 file/adapter/phase tests PASS normal/optimized.
Exact phone Python/tmpfs fixtures PASS **5.686 s**, cleanup verified.
Full local CI PASS **490.798 s** (previous **493.111 s**).
All four remote jobs PASS **34078827158**; local/remote work overlapped.
The earlier selector checkpoint `d75359b7` is complete; do not restart it.
Historical implementation detail and timing are in the dated report.
