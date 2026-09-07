# ROG5 current state

Updated 2026-09-08: V7 startup FAIL; verified signed V11 fallback is running.
V6 and V7 are permanently consumed. Never retry, restage or flash them.

## Goal and authority

Qualify one reliable unattended headless Arch server under the existing
[acceptance contract](release-acceptance.md) and
[mandatory matrix](../configs/release-acceptance.json). Display is optional.
Missing prerequisites/evidence remain BLOCKED or NOT RUN, never PASS.
No new architecture review or goal; unrelated work remains in the backlog.

Exact phone: `M5AIKN00F0353YH`, product `lahaina`, side USB anchor `1-1.2`.
Preserve official WW33 slot A (`33.0210.0210.200`) as charging/rescue.
Stock charging restoration is complete; no super or stock restoration work.
Keep identity/slot/topology, signatures, battery/thermal, scoped storage/backups,
independent fallback and permanent experimental one-use protections.
No new flash, GPT or protected-data operation. Destructive scope is separate.
Private credentials, packages, raw journals and evidence remain outside Git.

## Current phone and installed artifacts

The installed boot-B loader is unchanged:
`dcc487f17d6b4926ea633cbb242c62b598019e332640a81c1100c2d91087f723`.
Retained previous boot B:
`340f639276d9df3dfc073b8614a72f82507ea18c622c9df5d1e60f2c1622ccad`.
Signed V11 fallback manifest:
`a684bad14f84251ba342a87bde07da1f7b9aea412275ad124f7000716e94bbe2`.

Running bundle `persistent-native-root-v11`, kernel `7.1.4-g359318de534f`,
boot `b4dca8ff-bcb6-4b48-abf1-8f45d661634e`.
Authenticated USB SSH `10.77.0.2`, pinned alias `169.254.77.2`, fingerprint
`SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
Read-only fallback proof PASS: exact manifest, 117 physical block nodes,
only sda/sda23 writable, P24 RO; battery Good, below 40°C, USB online.
The 16 GiB persistent upper is unmounted in fallback. Do not mount it just
to inspect logs; bounded read-only debugfs acquisition is already proven.

The failed V7 selector/trial intentionally selects fallback, not another V7
execution. V5 accepted bundle/rollback selector/archived healthy record,
V6 failure records, V11 and all one-use claims remain preserved.
V5's previous healthy boot `660c70d5-f01f-4eda-82fe-4e1d6c9a4a08` ended.
Do not execute a previous restoration or transition script unchanged.

## Current blocker and exact next action

**S01: apply the existing conservative CPU policy early enough at startup.**
V7 boot `c591ab27-9079-4261-9806-80f61e1e04d7` reached local root/systemd.
The persistent journal proves:
- tmpfiles finished at 21.924 s; CPU policy started at 21.926 s;
- at 22.338 s, `thermal_zone13=62400 mC; required <60000 mC`;
- core.run's initial guard refused before its snapshot or CPU cap writes;
- the failure service requested orderly reboot at 24.745 s.

This is an actual thermal refusal, not missing optional telemetry or a host
SSH/parser error. The exact failing-boot zone type and earlier temperature
series were not retained. Do not infer V6's unknown zone/value from V7.
The new diagnostic message worked; it was not itself a thermal fix.

**R2/R4 correction:** `PrivateTmp=yes` adds an implicit tmpfiles dependency.
The two-line unit change uses `PrivateTmp=disconnected` and blocks `/var/tmp`.
It retains P2 ordering, private /tmp, the remaining sandbox and all safety gates.
The deployed systemd 261 manager/client/shared-library bytes reproduced the
old graph and verified its removal in QEMU: **12.843 s**. A separate RAM-only
namespace/ordering test passed in **12.492 s** while tmpfiles remained pending.
This proves the dependency/sandbox behavior, not reduced physical temperature.
No kernel, DT, module, threshold, cap order or watchdog change is proposed.

Correction `4b03207d30f1b1e238fc3fdf3bf1bd4c5125b752` passed full local CI
**548.467 s** and all four remote jobs in **34164958369**. Next: assemble
its target archive with the reused kernel/wrapper. Before any new
candidate, validate the effective deployed runtime, all artifact/admission
boundaries, fallback and power. A new physical attempt must answer whether
earlier capped startup passes the unchanged thermal guard. V7 cannot be reused.

## Evidence and qualification limits

V7 signed manifest:
`4eaeb9f8859f7fa9c64b5e40b3764452da504d0ce5438afd20760305bc23e7b9`.
Other artifact identities derive from its canonical expected record.
Source `9a2188a76aa4712a4b9a25c3d665c0cffbc3fe14`: full local CI PASS
**544.611 s**; all four remote jobs PASS in **34162547059**.
V7 A01/C01/C02 passed **91.137/131.861/74.290 s**, respectively.
However, the retained base root contains systemd 260 while the deployed
persistent upper contains 261. These base-root passes must not be described
as complete deployed-upper qualification. The focused 261 runtime replay
closes only the ordering/namespace question. Final A01 must include the
effective upper/runtime composition; a missing matching input stays BLOCKED.

The complete inactive 16 GiB upper is now retained read-only, SHA256
`dff8988f3c2f4c5204d2e827114f63e54068acc530a75010dd2d522de3795388`.
Single-stream acquisition/verification **40.866 s**, 27 power checks; no phone
mount/write/reboot. A failed earlier transfer remains archived, not accepted.
QEMU with both actual filesystem layers read-only passed the systemd 261 graph
and old-library whiteout checks; **22.477 s** guest/post-hash interval. This is
not full A01: incorporate the upper into the paired successor composition and
C02, keeping fresh complete input hashes. Do not revert to base-only testing.

V7 staging PASS **2.024 s**, no flash; P24 relocked and fallback hashes verified.
One execution only. Startup readiness FAIL at **301.118 s**.
Full capture **1380.703 s**, all route/firewall/profile/address cleanups PASS.
Last target transport stage: switch-root PASS; independent journal identified
the later CPU guard failure. Unplanned fallback is not controlled R01 proof.
Private work/evidence: `rog5-boot-cpu-diag-20260907.cnXiH8My`.

## Mandatory outcomes

Do not combine incompatible releases into one green result.

| Outcome | Current result / next action |
|---|---|
| A01 / C01 / C02 | V7 offline passes; effective-upper limitation above; requalify changed composition |
| H01 / H02 | V11 fallback SSH/power proof; same-release radio-inactive rescue not qualified |
| H03 regulation | NOT RUN for V7; defined firmware-Full method, not absent-field success |
| S01 local startup | V7 FAIL; test corrected CPU startup ordering |
| S02 transfers | V5 PASS only; qualify final release and Wi-Fi margin |
| S03 restart recovery | V5 PASS only; qualify final release |
| S04 durability | V5 PASS only; prior failed-soak scratch preserved |
| S05 repeated boots | V5 three ordinary boots PASS, 313.102 s; not V7 evidence |
| S06 powered-off start | NOT RUN |
| S07 combined load | V5 uncapped FAIL; capped 600.496 s diagnostic is not 60-minute PASS |
| F01 / F02 | Retained offline recovery/Wi-Fi-restart passes; exact-input reuse only |
| R01 recovery | Controlled isolated failed-boot qualification still outstanding |

## Fast loop and retention

Use [development](development.md): impact/dependency selection, exact-target
checks, frozen integration checkpoints and separate development/release results.
Unknown/critical changes stay broad. Documentation/eligible experiments need
not repeat unrelated CI; actual artifacts and safety dependencies still bind.
V7 target twins **9.095 s**, wrapper reuse **0.446 s**, signed packaging **4.828 s**.
Registry CI, root preview and A01/C01/C02 overlapped; no kernel/wrapper rebuild.
Private preparation may overlap pending CI; staging/execution still require
completed exact remote checks. It is not a live-admission waiver.

Preserve the 3 GiB home reserve. Retained preview restoration identities,
archived V4/V6 roots, released duplicate wrapper intermediates, historical
V5/V6 narratives and detailed results are in the
[existing dated report](../test-results/2026-09-05-headless-acceptance.md).
Some retained artifacts/archives remain in volatile RAM: no host reboot yet.
Home has approximately 3.45 GB free after the upper snapshot. The next artifact
plan must preserve the 3 GiB reserve and avoid another unnecessary raw-root copy.
Never remove the failed-soak scratch, accepted payloads or archived claims.
Host port 8081 is unrelated SteamOS CEF; leave it untouched.
