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

**V11 fallback is running after the consumed server-selector-v2 trial failed.**
Kernel `7.1.4-g359318de534f`; pinned SSH authenticated boot UUID
`61d60a1b-e4cd-472c-b439-590c1d31baa5` and bundle `persistent-native-root-v11`.
Fallback manifest:
`a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2`.
Failed primary boot: `8fac081d-65ba-4c6b-878d-d4acd0eda02d`, kernel
`7.1.4-gf17befd4ef17`. Never retry it or consumed rescue V8.
Live source `96e97de0716ebd12cacd391e1730a68b48de5f08`, all four CI jobs
passed in run 34050866675. Its single coordinator is terminal after 1380.713 s;
route, firewall, profile and address cleanup all passed. Do not restart it.
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
Active selector now names **staged, unissued `headless-server-selector-v3`**:
`0b897e0211fd327c74881a502cab47cc3f614f226716b5c9532cb2c3eb8bf4bd`.
The failed V2 selector is preserved at `selector.rollback-headless-server-selector-v3`:
`353b7a88f56733fe39ee31707981bccd3dd15b6b1d47822ca369b26bab779f99`.
Its exact pending trial `d0fef94cb686b2065311638cbbb9665617e5ca65796a46dc718bf0d7f43e9091`
is archived on P23 as failed-V2 evidence. Active trial is absent; V3 is not healthy.
Earlier healthy-trial/selector archives remain unchanged; see the dated report.
P24 is RO; independent postcheck passed. **Do not perform an ordinary reboot.**
No V3 host claim or target execution has occurred. Never retry failed V2.
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
| V3 composition / staging | A01 PASS 104.639 s; staging PASS 2.324 s, readback PASS 0.602 s; live trial NOT RUN |
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

Preserve V11 access. **Next: verify the current V11 RAM exitrd-to-fastboot path,
finish the V3 coordinator/publication inputs, then one captured RAM-only trial.**
The primary reached UFS, OverlayFS, systemd and authenticated diagnostic SSH
at `169.254.77.2`; `10.77.0.2` never resolved. State/identity services stayed
inactive behind radio qualification. USB disappeared about 158 seconds after
host execution began, then installed recovery booted V11. The radio failure
handler can request this reboot, but its actual result was not captured.
No previous journal or pstore was retained; reset cause remains unproven.
Latest fallback power snapshot: Full/100%, Good, 29.9°C, 8.586 V, zero battery current.
Private evidence/coordinator: `rog5-v7-server-modules-20260906.Ibl4iPCz/server-live-v2`.
V2 staging and claim are terminal. Host diagnostics are published at
`793a1ccf1ded9ba1be566a6eea3f09a38099735c`; all four CI jobs passed, run
34053338818. This diagnostic-only mode cannot satisfy readiness or weaken
partial-radio-failure rollback. Its focused checks passed
21 tests in each Python mode; active took about 24 s, full local CI **526.057 s**.
The complete sealed-BusyBox probe passed present/absent/wrong-boot fixtures in
9.325 s, with systemctl/IP stand-ins. No kernel rebuild was needed.
V3 signed target twins are prepared with only trial-descriptor/identity changes;
the exact kernel, modules, DTB, radio policy and timers are unchanged. Existing
verified recovery/wrapper twins are reused. Canonical registration is not a
live claim, staging proof or execution authorization. Private preparation:
`rog5-server-startup-20260906.ou4CkDi9`; exact hashes are in the dated report.
Its read-only startup watcher and assembled coordinator pass 11 replay tests.
V3 A01 now passes all seven checks under the unchanged 120-second deadline.
The first complete run exceeded it at 121.543 s; retain that FAIL. Host archive/
cache preparation preceded the 104.639 s rerun; no criterion or artifact changed.
V11 inspection, actual-Arch tmpfs utility checks and bounded staging/readback
passed. The stager preserved failed V2 records and all existing bundles.
The source trial helper already rearms healthy primary state to pending, but
the installed old loader and bootloader-reset helper do not prove autonomous
rescue. Advance that existing recovery requirement; do not repeat its review.
The accepted-release ordinary reboot path must not reuse a RAM execution claim.
No additional subsystem work or general architecture review is needed.

Combined kernel source `f17befd4ef172cfb0ecbffd9e0af87122cfa66bc` and twins
are complete; all 24 identities match. Reuse private
`rog5-v7-server-modules-20260906.Ibl4iPCz`; its old build-result OOM failure
is superseded by resume-result PASS, not a reason to restart the build.
Image SHA:
`ece47c7d52627d390bccdbcdab23295fe795820c66174d8de41cbc221cbac74e`.
V3 prospective root: `/run/rog5-server-preview-20260906-ou4CkDi9/root.ext4`,
SHA `599a79a6b1cb02fa6eb2dc4674a74c1040c0e96706078b067f5045e05fe1d4ee`.
This is a host A01 image, not the now-staged physical P24 raw digest.
The old V2 RAM cache was losslessly archived and only its redundant raw file
removed. Exact archive/restore proof is in private `archive-result.json`; all
old raw bytes are recoverable. Both current preview and archive are volatile.
Original disk snapshot remains intact. Do not reboot the host assuming tmpfs
is durable. Host free disk is about 3.7 GiB; preserve the 3 GiB reserve.

V3 registration `ddd6ac41fb96ae00d4a0edfe0cdc3fc2a0d52dcc`: active **20.808 s**,
full local **510.782 s**, and all four remote jobs PASS in run 34055998034.
Use focused checks during edits, one full CI per relevant frozen integration,
and meaningful publication batches. Reuse unchanged implementation CI for this
evidence-only update. No kernel/recovery/runtime bytes changed or were rebuilt.
Project-local skills now distinguish proven fixes from unexplained failures;
no global skills changed. Historical V6/V7, build, source-reuse and workflow
narratives remain in the [existing report](../test-results/2026-09-05-headless-acceptance.md).
Empty pstore remains inconclusive.
