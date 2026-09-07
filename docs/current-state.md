# ROG5 current state

Updated: 2026-09-07. S01 replay, USB/Wi-Fi transfers and service restart observations passed.

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

**V4 is running from the newly verified installed boot-B loader.**
Bundle `headless-server-selector-v4`, kernel `7.1.4-gf17befd4ef17`,
authenticated boot UUID `26f9f5e7-a3e1-463f-b9e5-7e6ba3bdaaf7`.
Pinned SSH/local root became ready in **85.531 s** after one ordinary reboot.
The prior sole RAM boot reached SSH in 84.957 s. The physical hw1.1 correction
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

**Installed boot B now has the verified v2 rearming trial helper:**
`dcc487f17d6b4926ea633cbb242c62b598019e332640a81c1100c2d91087f723`.
User-approved boot-B-only replacement completed once; exact physical readback
PASS 1.477 s includes fresh root/healthy-trial/power checks. The old image and
both verified backups remain `340f639276d9df3dfc073b8614a72f82507ea18c622c9df5d1e60f2c1622ccad`.
Ordinary installed boot works; three-boot qualification and controlled recovery remain
unqualified. Signed V11 fallback and stock A remain preserved.
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
The original RAM supervisor is terminal after 1380.640 seconds, receiver exit 0.
Route/firewall/profile/address cleanup passed; do not restart that coordinator.
Original startup replay PASS 0.027 s and post-cleanup same-boot SSH PASS 0.203 s.
Live source is **`3e90756f936f44df8d495695d3890a58c00ca646`**;
all four GitHub jobs passed run **34063760646** before staging/execution.
Replacement source is `d559b95cdeb757b5ed978ea74b5c09b4d88e90d4`;
all four GitHub jobs passed run **34068234458** before the operation.
Later documentation does not relabel either observed source.

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
| H01/H02 capture component | Original startup replay PASS 0.027 s; all cleanup PASS; radio-free H02 qualification not claimed |
| H03 regulation | Earlier V8 Full-maintenance PASS; not a same-release V4 PASS |
| F01 disposable recovery | Prior exact-input PASS 75.432 s; not physical UFS crash proof |
| F02 acceptance | PASS 0.816 s replay, 47.366 s including exact artifact verification; original live source/boot preserved |
| S01 standalone boot | Acceptance dispatcher PASS 0.266 s; original 85.531 s to SSH/root, complete capture/cleanup |
| S02 transfers | Physical PASS 298.494 s; public replay PASS 3.415 s; dispatcher integration qualifying |
| S03 restarts | Physical PASS 33.648 s; public replay PASS 0.069 s; first reconnect-race FAIL retained |
| S04–S07 | Durability/three boots/off-start/60-minute soak incomplete |
| R01 physical recovery | Controlled isolated failure qualification outstanding; no installed corruption |

S02/S03 evidence is retained under `s02-transfer-live-r1` and
`s03-services-live-r2`. Exact endpoint/boot, payload hashes, service invocation
identities and power guards passed. Pinned dispatcher bindings now exist;
full integration qualification follows the frozen checkpoint. Do not substitute
an aggregate final-release PASS. See the dated report.

Latest installed V4 telemetry: Full/100%, Good, 30.0°C, about 8.569 V,
battery current 0 mA, USB online; this snapshot is not regulation qualification.
Installed boot also survived the 900-second watchdog checkpoint: current-boot
P2/SSH acknowledgement at 902.493 s. This is healthy-path evidence, not R01.
Earlier startup briefly drew battery current; these snapshots are not a
10-minute H03 series. H03's firmware-Full protocol is already defined;
unsupported charge-limit controls are not a blocker and none were written.
The existing H03 rescue protocol requires inactive Wi-Fi; do not call this
radio-active snapshot a qualifying substitute or collect the same absent fields.

## Exact next action and development loop

Keep the server accessible. `recovery-reuse-r1/ordinary-boot-r1` is terminal:
supervisor 1385.867 s, receiver exit 0; route/firewall/profile/address cleanup
all PASS. Never restart this exact operation. Original clean source:
`d75359b781e9386561474004df7db980435bab6b`. Post-cleanup pinned SSH/root PASS
0.862 s on the same boot. The separate approved boot-B replacement is complete.
Next: qualify the frozen S02/S03 bindings, then S04 durability and repeated-boot
qualification. Preserve the first S03
failure: immediate post-restart SSH refusal needed bounded read-only reconnect,
not another restart or kernel fix. Corrected case: SSH recovered in 2.561 s.
Replay needs no new boot or build. Durability/repeated-boot tests will need
ordinary installed-release reboots, not flashes or experimental claim reuse.
Passive installed-reboot capture now separates the authenticated source boot
from a new boot after observed disconnect; 28 focused regressions pass.
Read-only GPT verification passed: B is active, with the Qualcomm-style
boot-success bit unset. The zeroed AOSP-style `misc` location is not a valid
slot record. Exact ASUS retry behavior remains unproven; no metadata was written.
`rog5-dev check-standalone-boot` binds pinned completed capture, installed bytes,
original source, A01 and authenticated local-root evidence. Missing data is
BLOCKED, not PASS. It cannot boot or retry. Host 8081 is SteamOS CEF proxy;
its upstream unit has no overrides. Leave this unrelated service untouched.

The exact approved boot-B replacement/proposal and old readbacks are archived
in the dated report and private `recovery-reuse-r1`; that operation is complete.
Stock A, signed V11, GPT and data remain unchanged. Do not repeat the flash or
reopen the resolved hw1.1 issue without new evidence.

Current-state/skills cleanup is complete. Use focused reproduction for proven
bugs and full investigation only for unexplained/repeated/cross-component ones.
Run active/focused checks during edits; full CI once for relevant integration.
Impact-selector checkpoint **`d75359b7` full local CI PASS 477.118 s**
(previous 480.583 s). All four remote checks passed **34072737998**; prior
receiver run **34071546898** also passed. Eligible development observers and
isolated userspace need applicable local checks, not unrelated remote waiting;
critical/unknown dependencies remain broad. Broad tiers retain narrow coverage.
Representative earlier active tier: 23.879 s; selector 0.077 s, NOT a test PASS.
S01 checkpoint **`f641fec9be5bf4d5d4a776f4245e6faaabab77d0`**: full local CI
PASS **515.382 s**, overlapping artifact verification and phone tests.
Remote run **34075265459**: all four jobs PASS, including qemu-system.
24 replay/44 dispatcher focused tests pass, including optimized validation.
Kernel/wrapper build count zero; no accepted target/cache inputs changed.
All new live observations retain original clean source `f641fec9`.

Preserve the combined kernel/module kit, signed package, V4 root preview and
lossless V2/V3 preview archives. Some are volatile tmpfs; do not reboot the host
assuming they are durable. Keep 3 GiB disk reserve; no ad-hoc deletion.
See the dated report for restoration commands, peak sizes and prior failures.
