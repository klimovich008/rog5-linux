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
| H03 | BLOCKED until supported firmware evidence and executable observation are qualified; do not repeat absent-control inventory |
| A01 | Older server PASS 110.953 s / VM 39.505 s; final combined kernel composition still required |
| R01 / installed recovery | Incomplete; sealed failure helper returns fastboot, not autonomous fallback SSH |
| Persistent server qualification | Three ordinary boots, powered-off start, storage durability and 60-minute combined soak incomplete |

Last retained V7 health (not continuous monitoring): uptime 15373.21 s, 29.9°C,
8.594 V, zero battery current, Good/USB online, P24 RO, no failed units;
fresh same-boot gate PASS 0.291 s during this continuation.
Full/100% and zero current alone do not qualify regulation. Charge-limit
attributes are unsupported by this SM8350 interface; capacity ENODATA is the
separate proven 0038 unit defect. No charging control has been written.

## Frozen work in progress

**Primary question:** can the exact final server composition preserve accepted
RPMh/S12 support while incorporating the proven capacity and NCM corrections?

V7 lacks built-in `rpmh_read` and the accepted ASUS S12 selector point.
Matching config/vermagic is insufficient for server radio. Both S12/activation
builders now reject missing/ambiguous built-in readback before compilation;
ten fail-first negative cases plus valid input are covered. No policy change.

Combined source `f17befd4ef172cfb0ecbffd9e0af87122cfa66bc` preserves accepted
server `1eea8970e87f1e1509fc12a85456f55570cfb4b1` and adds only existing
0038/0039 in two files. Kernel/config/ABI inputs are frozen. Build A's BTF
step hit a confirmed 3 GiB container OOM after 1600.559 s. Exact-state resume
with the previously proven 6 GiB allowance PASS 176.750 s, BTF intact, 19 modules.
Image SHA: `ece47c7d52627d390bccdbcdab23295fe795820c66174d8de41cbc221cbac74e`.
Independent clean twin B is running under private
`rog5-v7-server-modules-20260906.Ibl4iPCz`; inspect live processes and terminal
results before advancing. Do not restart builds or edit their inputs.
Full local CI passed in 589.229 s for the builder correction and 630.297 s
for the later shared capture correction; no unchanged rerun. This is
not a claim that the final assembled release or new kernel has passed A01.
Host reserve is 3 GiB; no deletion authorized by this checkpoint.
No new candidate is issued, signed, admitted or executed. Derived module-kit
ARM64 headers were corrected before any deployment; Wi-Fi module A PASS
223.630 s, module twin/activation builds still running in the same directory.

The V7-only in-tree capacity module twins (`998c30ca…`) and QEMU PASS 6.325 s
remain in `rog5-battmgr-module-20260906.R8ZllyeH`; do not mix that ABI with
the new combined kernel. Older source/builds/evidence are preserved.
Published `1ad38a4ecba0bbdc29e17a0f1ba19bdcf312ea90` passed all four
jobs, run 34040091326. Working HEAD/status and current CI logs take precedence
over these historical results. Prior full CI 498.829 s; final workflow active
PASS 28.337 s (previous 21.207 s under different load).

## Exact next action

The bounded instruction/H03 clarification is complete; collect the running
build outcomes. Assemble and test the coherent final kernel/module/archive
for A01; reuse verified outputs, do not recompile ASUS for host/doc changes.
H03's predeclared plan is in the acceptance contract; its Full-state evaluator
passes offline but still needs same-release supervised collection and H02.
The capture fix now recognizes only an anchored sysfs-read ENOENT/ENODEV
followed by confirmed absence before any target observation. It keeps unknown,
network/binding and post-target errors fatal and never clears an earlier FAIL.
Historical untagged V7 evidence remains FAIL. Publish the tested capture fix
and finish kernel/module twins before another phone cycle.

Use focused checks during edits and one full CI per relevant frozen integration;
publish at meaningful checkpoints. Keep one physical coordinator. Scope and
reboot rules are in development; unrelated findings go in the existing
[backlog](../ROADMAP.md). H03, recovery and whole-release qualification remain
open. Empty pstore is inconclusive.

Completed primary/V6/V7 preparation, module/BTF, source-reuse and publication
narratives are retained in the [dated incident](../test-results/2026-09-05-headless-acceptance.md)
and [source assessment](kernel-port.md#bounded-source-reuse-assessment--2026-09-06),
rather than replayed in this handoff. Follow only the relevant linked section.
