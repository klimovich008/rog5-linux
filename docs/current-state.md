# ROG5 current state

Updated: 2026-09-06. Authoritative handoff, not continuous monitoring.

## Active goal and scope

Qualify one reliable standalone headless Arch server under the existing
[acceptance contract](release-acceptance.md) and
[mandatory manifest](../configs/release-acceptance.json).
Use `scripts/host/rog5-dev accept`; missing prerequisites, skipped mandatory
tests and lost transport are not PASS. Display remains optional.
Use the [development loop](development.md); unrelated findings belong in the
[backlog](../ROADMAP.md), not a new review or goal.

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

## Running RAM rescue and installed recovery

**V11 fallback is running after the consumed server-selector-v3 trial failed.**
Kernel `7.1.4-g359318de534f`; pinned SSH authenticated boot UUID
`fbb0d3e4-96ca-469c-8edc-d26ffbcb5cf8` and bundle `persistent-native-root-v11`.
Fallback manifest:
`a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2`.
Failed primary boot: `655c5d76-02aa-441b-ad5d-7217b0f54f13`, kernel
`7.1.4-gf17befd4ef17`. Never retry it or consumed rescue V8.
Live source `4ba30f3964f7962242bab1f4910a61f8e3489453`, all four CI jobs
passed in run 34058164544. Its single coordinator is terminal at 1380.786 s.
Capture/readiness are FAIL; route, firewall, profile and address cleanup PASS.
Do not restart it. Fallback frames were not accepted as primary success.
V8's earlier H01/H02/H03 passes remain historical same-release evidence, not
qualification of this server or current fallback. Exact identities are in the
[dated evidence](../test-results/2026-09-05-headless-acceptance.md#v8-live-rescue-and-h03-full-maintenance-qualified).

Pinned SSH: `10.77.0.2` (alias `169.254.77.2`), fingerprint
`SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
Wi-Fi intentionally inactive. Rescue uses tmpfs upper over RO/noload P24 and
existing bounded P23 service state; not the primary's persistent upper.
Pre-staging P24 snapshot (not the current raw P24 image):
`e1692971646809ff412363014d69a363aa543336a715e918ec0cc978cafa36c6`.

**Installed boot B remains old/unqualified recovery:**
`340f639276d9df3dfc073b8614a72f82507ea18c622c9df5d1e60f2c1622ccad`.
Signed `persistent-native-root-v11` fallback and stock A remain preserved.
Active selector now names **consumed, failed `headless-server-selector-v3`**:
`0b897e0211fd327c74881a502cab47cc3f614f226716b5c9532cb2c3eb8bf4bd`.
The failed V2 selector is preserved at `selector.rollback-headless-server-selector-v3`:
`353b7a88f56733fe39ee31707981bccd3dd15b6b1d47822ca369b26bab779f99`.
Its exact pending trial `d0fef94cb686b2065311638cbbb9665617e5ca65796a46dc718bf0d7f43e9091`
is archived on P23 as failed-V2 evidence. V3 was executed once; it is not healthy. Do not retry its target or claim.
Earlier healthy-trial/selector archives remain unchanged; see the dated report.
P24 is RO; independent postcheck passed. **Do not perform an ordinary reboot.**
V3's claim is consumed. Never retry failed V2/V3 or rescue V8.
RAM success does not prove installed recovery corrections. Ordinary accepted
release reboot tests follow [distinct operation rules](development.md#experimental-execution-and-stable-operation);
they do not permit retrying an experimental claim.

## Acceptance matrix and current blocker

These are rescue/component results, **not a coherent final server PASS**.
Do not merge older server results or radio-free rescue evidence into server
radio/persistent-root qualification. Detailed failures remain in the dated report.

| Outcome | Result / next action |
|---|---|
| A01 rescue composition | PASS 83.860 s, exact V8 signed archive; reused unchanged packaging evidence |
| H01 capture | PASS 0.416 s; original preboot capture replay, no new execution |
| H02 same-boot rescue | PASS; pinned SSH, deployed runtime and actual watchdog ACK verified |
| H03 charging/regulation | PASS 604.523 s; 61 samples / 600.265 s, firmware-Full maintenance only |
| C01 watchdog handover | Exact V8 kernel/archive: 9 cases PASS 138.299 s |
| C02 late SSH restart | PASS 91.570 s through dispatcher on c2539e3c; only its two isolated guests overlap, unchanged 120 s limit and before/after hashes |
| Server C02 / prior live | V2 offline C02 PASS 77.233 s; live readiness FAIL, automatic V11 fallback SSH recovered |
| V3 composition / staging | A01 PASS 104.639 s; staging/readback PASS; live readiness FAIL, automatic V11 SSH recovered |
| F01 journal/OverlayFS | Exact inputs: disposable-image recovery/corruption tests PASS 75.432 s; not physical UFS crash proof |
| R01 installed recovery | Incomplete; sealed failure helper returns fastboot, not autonomous fallback SSH |
| Persistent server | Local autonomous boots, qualified Wi-Fi, durability, powered-off start and 60-minute soak incomplete |

H03 observed Full/100%, Good, 29.8°C, 8.590 V, battery current 0 µA and
unchanged 5,106,000 µAh counter throughout. USB supplied 172–447 mA at
4.983–5.053 V, below the reported 500 mA limit. Required before/after firmware,
runtime, source and same-boot checks passed. This proves full-charge maintenance,
not programmable limits, sub-full charging or uninterrupted future health.
Unsupported charge-limit controls are not the blocker; none were written.

## Current blocker and exact next action

V3 captured the already-recorded WCN6851 hw1.1 rejection: PCIe powered up and
enumerated, then ath11k returned `-95` for hardware version `1 16`. The radio
service failed; normal service-state/identity never started. Diagnostic SSH
remained available before the failure handler started and USB disappeared.
Automatic V11 fallback was independently authenticated. No crash cause is
inferred from absent pstore or from the driver rejection alone.

The complete-module builder omitted the existing device patch already qualified
in [V15](../test-results/2026-08-31-wifi-late-activation.md#v15-live-firmware-phy-and-scan-pass-consumed).
Its exact-source selector regression reproduces the rejection. The build path
is now corrected to apply that patch and run the selector before compilation.
No new charging policy, PCIe architecture or base-kernel change is needed.

**Next: publish this tested integration and assemble/qualify a fresh successor
using the repaired four-module family.**
Do not reuse V3 merely because its base Image/wrapper remain valid.
The recovered module twins match; 71.871/66.620 seconds, 109,494,272 bytes
combined. Exact-kernel QEMU component PASS 125.827 seconds (guest 43.738 s).
This unsigned fixture is not an A01-qualified candidate or physical Wi-Fi PASS.
A separately signed successor, exact assembly, staging and admission remain.

Private evidence: `rog5-server-startup-20260906.ou4CkDi9`.
Its `live-r1`, `v3-fallback-inspection-r1`, and `hw11-repair` are authoritative;
details and artifact hashes stay in the [dated report](../test-results/2026-09-05-headless-acceptance.md).
The V11 RAM exitrd action-only transition reached exact fastboot in 9.351 s;
only its final reboot request changed. Installed boot B was not flashed.

Reuse combined Image `ece47c7d52627d390bccdbcdab23295fe795820c66174d8de41cbc221cbac74e`
and its exact module kit in `rog5-v7-server-modules-20260906.Ibl4iPCz`.
Preserve all original modules/build evidence; the four replacements are separate.
The V3 host preview and lossless V2 archive remain volatile tmpfs. Their hashes
and recovery procedure are retained in the dated report. Do not reboot the host
assuming these caches are durable. Free host disk is about 3.4 GiB; keep 3 GiB.

Use focused tests during edits, one full CI at relevant integration, and batch
publication. Active PASS 22.196 s; full local PASS 518.605 s (prior 510.782 s).
Exact-head/merge/QEMU checks passed for the live source; this follow-up still
needs its publication CI. Captured controller/artifacts were unchanged; the fix
changes offline module-build instructions/tests and documentation only.
Project-local skills and H03 policy cleanup are complete;
global skills were not changed. Display and unrelated subsystems remain deferred.
