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

**Consumed `headless-acceptance-rescue-v8` is running; never reexecute it.**
Kernel `7.1.4-gf17befd4ef17`; boot UUID:
`015153cc-86f0-440c-b49f-95a1733316b9`.
Manifest:
`2b565dbea7b14ffa90dd7100700f8db2b7554f9ac9f8eb8149d28dde02070e9f`.
Frozen live/qualification source `d23304c04bc201c7ffb25fbac49b86b187969b31`;
all four publication jobs passed, run 34046603853.
One coordinator completed capture and cleanup; it is no longer running.
Pinned SSH became ready in 59.785 s. H01/H02/H03 now pass on this boot.
Exact artifact identities and private result locators are in the
[dated evidence](../test-results/2026-09-05-headless-acceptance.md#v8-live-rescue-and-h03-full-maintenance-qualified).

Pinned SSH: `10.77.0.2` (alias `169.254.77.2`), fingerprint
`SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
Wi-Fi intentionally inactive. Rescue uses tmpfs upper over RO/noload P24 and
existing bounded P23 service state; not the primary's persistent upper.
P24 snapshot:
`e1692971646809ff412363014d69a363aa543336a715e918ec0cc978cafa36c6`.

**Installed boot B remains old/unqualified recovery:**
`340f639276d9df3dfc073b8614a72f82507ea18c622c9df5d1e60f2c1622ccad`.
Preserved selector:
`c15c77824e3cecf128288f2c273c6bd7f93825e837568c669d8288145541d904`;
previous healthy primary trial:
`bfc82fac0199062bb7244e451299ed11c513c8895c8943ac3c5b86d4dbdb141b`.
Signed `persistent-native-root-v11` fallback and stock A remain preserved.
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
| F01 journal/OverlayFS | Exact inputs: disposable-image recovery/corruption tests PASS 75.432 s; not physical UFS crash proof |
| R01 installed recovery | Incomplete; sealed failure helper returns fastboot, not autonomous fallback SSH |
| Persistent server | Local autonomous boots, qualified Wi-Fi, durability, powered-off start and 60-minute soak incomplete |

H03 observed Full/100%, Good, 29.8°C, 8.590 V, battery current 0 µA and
unchanged 5,106,000 µAh counter throughout. USB supplied 172–447 mA at
4.983–5.053 V, below the reported 500 mA limit. Required before/after firmware,
runtime, source and same-boot checks passed. This proves full-charge maintenance,
not programmable limits, sub-full charging or uninterrupted future health.
Unsupported charge-limit controls are not the blocker; none were written.

## Reuse and exact next action

Keep V8 available. **Next: installed autonomous recovery and server testing.**
C02's serial guest overhead is corrected without dropping validation; original
151.045 s failure and diagnostic 114.037 s replay remain in the dated report.
The source trial helper already rearms healthy primary state to pending, but
the installed old loader and bootloader-reset helper do not prove autonomous
rescue. Advance that existing recovery requirement; do not repeat its review.
Fresh V8 H02 PASS 1.269 s on c2539e3c, same boot, actual watchdog ACK 900.048 s.
The accepted-release ordinary reboot path must not reuse a RAM execution claim.
No additional subsystem work or general architecture review is needed.

Combined kernel source `f17befd4ef172cfb0ecbffd9e0af87122cfa66bc` and twins
are complete; all 24 identities match. Reuse private
`rog5-v7-server-modules-20260906.Ibl4iPCz`; its old build-result OOM failure
is superseded by resume-result PASS, not a reason to restart the build.
Image SHA:
`ece47c7d52627d390bccdbcdab23295fe795820c66174d8de41cbc221cbac74e`.
The separately packaged, unexecuted `headless-server-selector-v2` has full
offline A01 PASS 96.525 s; it is not the radio-inactive V8 rescue.
Its prospective root remains volatile at
`/run/rog5-server-preview-20260906-Ibl4iPCz/root.ext4`,
hash `8f4afbcceed4b2112981392127deaf5a057a9c1d193cb325ef55791810e792c5`.
Do not reboot the host assuming that preview is durable. Original snapshot
remains intact. Host free space is about 4.1 GiB; preserve the 3 GiB reserve.

Use focused checks during edits, one full CI per relevant frozen integration,
and meaningful publication batches. Active/full implementation checks already
passed 20.197 / 498.170 s; do not rerun unchanged code for this evidence update.
The focused C02 harness regression passed 17 tests / 1.084 s and its active
tier passed 20.595 s. No kernel/recovery/runtime bytes changed or were rebuilt.
Project-local skills now distinguish proven fixes from unexplained failures;
no global skills changed. Historical V6/V7, build, source-reuse and workflow
narratives remain in the [existing report](../test-results/2026-09-05-headless-acceptance.md).
Empty pstore remains inconclusive.
