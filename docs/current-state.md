# ROG5 current state

Updated 2026-09-07: V5 F01/F02 and S01–S05 passed on the same artifact set.
Next: prepare the full V5 combined-load soak; retain the remaining power/recovery gates.

## Goal and authority

Qualify one reliable standalone headless Arch server under the existing
[acceptance contract](release-acceptance.md) and
[mandatory matrix](../configs/release-acceptance.json). Display is optional.
Missing prerequisites/evidence remain BLOCKED or NOT RUN, never PASS.
Work the next mandatory outcome; unrelated work stays in the existing backlog.

Exact phone: `M5AIKN00F0353YH`, product `lahaina`, side USB anchor `1-1.2`.
Preserve official WW33 slot A (`33.0210.0210.200`) as charging/rescue.
Charging restoration is complete; do not repeat stock restoration or super writes.
Preserve identity/slot/topology, signatures, battery/thermal, storage scope,
backups, independent fallback and permanent experimental one-use protections.
No new flash, GPT or protected-data operation. New destructive scope requires
separate exact review. Private credentials/evidence stay outside Git.

## Installed release

V5 (`headless-server-selector-v5`) uses kernel `7.1.4-gf17befd4ef17`.
It sets/verifies Wi-Fi power saving OFF at startup and restart. This is a
supported mitigation, not proof of a unique driver/AP root cause for V4's soak.
One experimental V5 boot succeeded; its claim is permanently consumed.
Three consecutive ordinary V5 boots reached verified healthy state in
**97.290 / 95.301 / 96.347 s**; complete sequence **313.102 s**.
Current boot: `96b722da-4ddc-4611-b813-a62149df541f`.
Ordinary accepted-release reboot testing does not reset experimental claims.

USB SSH `10.77.0.2`, pinned alias `169.254.77.2`, host fingerprint
`SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
Native P24 lower is RO/norecovery; persistent upper/service-state images are
on authorized P23. Attestation checks 117 block nodes and exact write scope.
Latest restart snapshot: Good, 30.1°C, 8.559 V, 100%, Full, −23 mA, USB online.
These snapshots are not H03 PASS or proof of net-positive charging under load.
Healthy V5 trial and preserved failed-soak scratch digest were verified.

## Artifact and recovery identities

Installed boot B, already replaced and verified; do not flash again:
`dcc487f17d6b4926ea633cbb242c62b598019e332640a81c1100c2d91087f723`.
Retained previous boot B:
`340f639276d9df3dfc073b8614a72f82507ea18c622c9df5d1e60f2c1622ccad`.
Signed V11 fallback manifest:
`a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2`.
V5 manifest:
`747b669e0a8587de7cc338ab0d82552cdeaad79604fae8c145a6e05b334c743f`.
V5 target archive:
`c4044bd28a5c9bbfb18ef77113aee4cd3bb56e5ab78350bb2454926d830fbfc0`.
Exact remaining hashes derive from the canonical record/private recipe.
The old V4 selector/healthy trial remain archived; do not restage V5.

Private V5 work: `rog5-server-wifi-ps-20260907.aSQZz23O`.
Prior V4 work: `rog5-server-hw11-20260906.Lo7km1SL`.
Historical identities and complete results remain in the
[dated report](../test-results/2026-09-05-headless-acceptance.md).
Do not relabel V4 passes as V5 evidence.

## Mandatory results and next action

These component results do not constitute a qualified final release.

| Outcome | V5 result / next action |
|---|---|
| A01 composition | PASS 103.346 s; exact target, reused wrapper and paired lower |
| C01 watchdog | Nine cases PASS 135.450 s |
| C02 late SSH restart | PASS 93.348 s; first 121.667 s failure retained |
| F01 recovery | PASS 89.422 s; exact V5 inputs, disposable QEMU disks, not physical crash injection |
| F02 Wi-Fi restarts | PASS 29.017 s; WPA/DHCP, lease and SSH endpoints, unchanged radio/core services |
| H01/H02 | Boot capture exists; same-release radio-inactive rescue not qualified |
| H03 regulation | NOT RUN for V5; prior V8 Full-maintenance is not V5 PASS |
| S01 local boot | PASS; 86.540 s startup, full capture/cleanup, canonical replay 0.078 s |
| S02 transfers | PASS 313.126 s; four 256 MiB USB/Wi-Fi directions, exact hashes |
| S03 restart recovery | PASS 36.427 s; health/SSH/WPA/DHCP, no radio reactivation |
| S04 durability | PASS 93.289 s file cycle; full 1385.988 s supervision and canonical replay complete |
| S05 repeated boots | PASS three consecutive ordinary boots; 313.102 s total, clean closures |
| S06 powered-off start | Physical off/start proof required, not an ordinary reboot |
| S07 soak | Full 3600 s V5 combined-load run required; old thermal cause unresolved |
| R01 recovery | Controlled isolated failed-boot recovery still outstanding |

The scratch-namespace correction passed full local/remote CI, exact-target RAM
tests and live S04: a fresh 64 MiB file survived reboot and exact child-only
cleanup; the prior failed-soak file remains preserved. Do not repeat S04.
Next: bind the existing soak runner to V5 and the current pinned namespace,
run its focused checks, then the full 3600 s storage/network observation.
Use the accepted kernel and installed boot path; no new experimental claim.
S02 Wi-Fi upload took 178.391 s against a 180 s bound: PASS with little margin,
not proof of robust endurance. Keep this concern for the combined-load test.
No device test is running at this checkpoint. Keep one coordinator and freeze
its inputs; never retry ambiguous execution. Preserve old failed-soak evidence.
H03's firmware-Full method is defined. The missing same-release radio-inactive
prerequisite is not solved by merely stopping WPA/DHCP; do not repeat absent-field
inventories or alter charging controls to manufacture a pass.

## Fast loop and retention

Use [development](development.md): impact/dependency selection, focused edits,
exact assembled/target checks and coherent frozen checkpoints. Unknown or critical
changes retain stronger local/remote checks; development PASS is not release PASS.
Storage integration source `1bfc86a2c7be57d09adb42c8705ed4edb4e942b0` passed full
local CI **521.345 s** and all four remote jobs in run **34136133422**.
F01/F02/S04/S05 observations bind that source; S01–S03 retain their original
`f5546aad` source, with unchanged artifact/dependency evidence, not a new label.
Exact-target RAM tests took **21.124 s**. Independent F01 ran entirely during
the required S04 capture; **178.586 s** dispatcher time added no serial wait.
Target twins **8.375 s**, signing/sealed verification **4.649 s**, wrapper reuse
**0.474 s**: no new kernel or wrapper build. C02 sparse hashing reduced data read
volume by 88% while retaining both complete logical hashes and the 120 s limit.

Keep the 3 GiB host disk reserve; current headroom is tight. Old preview/cache
inputs are losslessly archived with verified restoration records. Some archives
and the 4.063 GB V5 preview are volatile tmpfs, not durable backups. Do not reboot
the host yet. Do not discard unique evidence, accepted artifacts or credentials.
Host port 8081 is unrelated SteamOS CEF; leave it untouched.
