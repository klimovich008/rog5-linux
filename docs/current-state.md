# ROG5 current state

Updated: 2026-09-06. Authoritative handoff, not continuous monitoring.

## Active goal and scope

Qualify one reliable standalone headless Arch Linux server under the existing
[acceptance contract](release-acceptance.md) and
[mandatory manifest](../configs/release-acceptance.json).
Run `scripts/host/rog5-dev accept` for the formal matrix; missing prerequisites,
skips and lost transport are not PASS. Display and other optional features
remain outside completion. Keep Arch; do not reopen completed source reviews
without materially new evidence. See [development loop](development.md).

## Exact device and authority

Phone `M5AIKN00F0353YH`, product `lahaina`, anchored side USB `1-1.2`.
Preserve official WW33 slot A (`33.0210.0210.200`) as charging/rescue.
[Stock charging restoration](asus-charging-recovery.md) is complete.
Keep identity/slot/topology/boot-chain, signature, battery/thermal, bounded
storage/backups, independent rollback and experimental one-use guards.
No experimental flash, GPT or protected-data change. New destructive storage
requires separately reviewed exact scope and approval. Existing scoped
credentials/build/test authority remains; keep private material outside Git.
Do not delete unique artifacts, source, credentials, evidence or fallback.

## Running RAM rescue and installed recovery

Consumed `headless-acceptance-rescue-v7`, kernel `7.1.4-g601c84c0c3c4`.
Boot UUID: `120b2938-b143-4c17-ade4-69f4304c5802`.
Signed manifest:
`eca02756542e0af41c0ef45479fdcce9cad0e6f06a13ae3253fae139a8cfb18f`.
Source `69a6806188c9957b1bca59206acf92d39746e4f1`, publication run
34027214673 passed all four jobs. Do not reexecute this experimental candidate.
Canonical record and [dated evidence](../test-results/2026-09-05-headless-acceptance.md#v7-physical-ncm-and-current-root-checkpoint)
retain exact boot/archive/recovery hashes.

Pinned SSH is `10.77.0.2` (alias `169.254.77.2`), fingerprint
`SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
Wi-Fi intentionally inactive. Rescue uses tmpfs upper over RO/noload P24 and
existing bounded P23 service state; not the primary's persistent 16 GiB upper.
P24 snapshot:
`e1692971646809ff412363014d69a363aa543336a715e918ec0cc978cafa36c6`.

**Installed boot B is still old/unqualified recovery**
`340f639276d9df3dfc073b8614a72f82507ea18c622c9df5d1e60f2c1622ccad`.
RAM success does not prove installed demotion/watchdog/helper corrections.
Preserved selector:
`c15c77824e3cecf128288f2c273c6bd7f93825e837568c669d8288145541d904`;
previous healthy primary trial:
`bfc82fac0199062bb7244e451299ed11c513c8895c8943ac3c5b86d4dbdb141b`.
Signed `persistent-native-root-v11` fallback and stock A remain preserved.
Ordinary accepted-release reboot testing is allowed by the
[distinct operation rules](development.md#experimental-execution-and-stable-operation),
but this unqualified installed loader is a real prerequisite, not a claim waiver.

## Acceptance evidence and current blocker

Component evidence is not a coherent final-release PASS. Detailed results and
failures live in the [existing incident](../test-results/2026-09-05-headless-acceptance.md);
do not combine the older server's offline passes with V7 hardware passes.

| Outcome | Current result / next action |
|---|---|
| Rescue access | V7 pinned SSH 57.513 s; watchdog current-boot ACK at 902.552 s |
| NCM under load | V7 8 GiB read + 39 SSH checks PASS 125.505 s; complete P24 capture + 118 checks PASS 386.132 s |
| Early capture / H01 | V7 FAIL retained; anchored read/removal correction passes focused/full CI, awaiting new physical evidence |
| H02 | V6 integrated PASS retained; cannot silently transfer to another release/boot |
| H03 | Supervised Full-state collector and offline checks PASS. Live same-release H02/600 s series still required; absent charge-limit controls are not the blocker |
| A01 | Selector v2 full signed offline composition PASS 96.525 s, all seven checks; prospective root, not deployed proof |
| R01 / installed recovery | Incomplete; sealed failure helper returns fastboot, not autonomous fallback SSH |
| Persistent server qualification | Three ordinary boots, powered-off start, storage durability and 60-minute combined soak incomplete |

Last retained V7 health (not continuous monitoring): uptime 21651.68 s, 29.9°C,
8.591 V, zero battery current, Good/USB online, P24 RO, no failed units;
fresh same-boot gate PASS 0.265 s before V8 preparation.
Full/100% and zero current alone do not qualify regulation. Charge-limit
attributes are unsupported by this SM8350 interface; capacity ENODATA is the
separate proven 0038 unit defect. No charging control has been written.

## Frozen work in progress

**Primary question:** can H03 retain a complete same-boot charging window and
reject missing, unsafe or stale measurements using supported firmware telemetry?

The combined kernel restores accepted RPMh/S12 support missing from V7;
builders reject absent/ambiguous built-in readback. Do not mix the two ABIs.

Combined source `f17befd4ef172cfb0ecbffd9e0af87122cfa66bc` preserves accepted
server `1eea8970e87f1e1509fc12a85456f55570cfb4b1` and adds only existing
0038/0039 in two files. Kernel/config/ABI inputs are frozen; use the verified
twins, not a rebuild. Host OOM/kit corrections are in the dated evidence.
Image SHA: `ece47c7d52627d390bccdbcdab23295fe795820c66174d8de41cbc221cbac74e`.
Independent clean B PASS 1715.396 s; all 24 artifacts match A. Results remain
under private `rog5-v7-server-modules-20260906.Ibl4iPCz`; reuse completed outputs.
Matching radio/activation twins and PMIC twins also PASS. No build is pending.
Relevant shared-code local CI passed; no unchanged full rerun is needed.
Host reserve is 3 GiB; no deletion authorized by this checkpoint.
No new live claim, admission or execution. Matching complete server archive twins
`6f9199f5413e6d59bce6cb7973593ef1afa858630af7541c3aa2f0a5a3e73e07`
PASS 73.336 s; 37-module/radio/Arch component PASS 105.604 s (VM 38.939 s).
Proposed `headless-server-selector-v2` was signed through the existing workflow
in 6.084 s; wrapper is byte-identical to the retained selector wrapper. Its
canonical exact record is packaging data, not a created or consumed live claim.
Full signed A01 PASS 96.525 s, all seven checks; no deployment or phone boot.

Published `4b22a9f670c1db44c55fc8fa98e2c6896c6ab6ba` passed all four
jobs, run 34045925726. Working HEAD/status and current CI logs take precedence
over these historical results. Detailed build/test timings are in the dated report.

## Exact next action

Matching radio-free `headless-acceptance-rescue-v8` packaging twins PASS 20.599 s;
full signed A01 PASS 83.860 s on `fcfd15db51c225a67ea1d4c02a85c5d637cb3abb`.
Private recipe/results: `rog5-rescue-h03-20260906.CayoqOsI`. No live claim or boot.
Manifest `2b565dbea7b14ffa90dd7100700f8db2b7554f9ac9f8eb8149d28dde02070e9f`.
Publish this data checkpoint and validate the existing live adapters for V7 →
fastboot → one V8 attempt, then qualify H01/H02/H03. H02 intentionally
rejects radio-bearing server archives; do not mislabel selector v2 as that rescue.
The A01 prospective P24 copy remains under
`/run/rog5-server-preview-20260906-Ibl4iPCz/root.ext4` (not phone evidence).
Preview hash `8f4afbcceed4b2112981392127deaf5a057a9c1d193cb325ef55791810e792c5`;
original P24 snapshot is unchanged. Reuse outputs; do not recompile ASUS.
H03 revalidates H02, runtime/firmware, 61 fresh samples and end-state identity.
It performs no boot, admission, retry or charging-control write. Offline replay
and simulated sysfs are not charging evidence; the physical series remains open.
Active tier PASS 20.197 s; full local CI PASS 498.170 s. Reuse these unchanged
checks; exact-head publication remains separate. See the dated incident for detail.
The capture fix now recognizes only an anchored sysfs-read ENOENT/ENODEV
followed by confirmed absence before any target observation. It keeps unknown,
network/binding and post-target errors fatal and never clears an earlier FAIL.
Historical untagged V7 evidence remains FAIL. Capture fix publication and twins
passed. Free host space is 4.2 GiB; preserve the 3 GiB reserve. The RAM preview
is volatile. A bounded compression exceeded its 1.5 GiB cap; only that incomplete
duplicate was removed. Retain the preview pending staging/retention resolution;
do not reboot the host assuming it is durable. Original snapshot remains intact.

Use focused checks during edits and one full CI per relevant frozen integration;
publish at meaningful checkpoints. Keep one physical coordinator. Scope and
reboot rules are in development; unrelated findings go in the existing
[backlog](../ROADMAP.md). H03, recovery and whole-release qualification remain
open. Empty pstore is inconclusive.

Completed primary/V6/V7 preparation, module/BTF, source-reuse and publication
narratives are retained in the [dated incident](../test-results/2026-09-05-headless-acceptance.md)
and [source assessment](kernel-port.md#bounded-source-reuse-assessment--2026-09-06),
rather than replayed in this handoff. Follow only the relevant linked section.
