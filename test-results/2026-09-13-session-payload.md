# Denial session payload — 2026-09-13

**The retained ARM64 components are composed and their packaged CLI checks pass.**
This unsigned session-files archive is not installed, not a rootfs/package closure,
and not a phone candidate. Real local logind login/device access remains NOT RUN.

Starting commit `1cf23432031c5772dbf5c1b2ca1252f08536233e`, tree `9af3d242ff08bc84ab395a73b6ef8ab3c3b7ba76`.
Implementation frozen at `f94182682ea43c65320a3fe97e10ed90d44651ce`, tree `dfb7f5b49b32453292263a4155b380d8051609de`.
Subsequent publication changes evidence/status only. No kernel, compositor,
engine or AOT rebuild. Prior phone, fallback and consumed-claim identities remain.

The supplied framebuffer review is already incorporated: strict explicit
intersection, sole-Invalid pool dispatch and returned-descriptor validation.
The exact patch remains `3d05d2d441d32f852c71887bf750aede1a7a5fc959f5a2ac50234a844783b8f1` and its executable
regressions are unchanged from1282476b. Their retained16 corrected PASS and10
original expected FAIL were not rerun. The later non-root ARM64 VM recorded210
frames/page flips and native text input; those are prior VM results, not phone
evidence or a new framebuffer experiment. See the [allocation response](2026-09-12-denial-allocation-contract.md)
and [non-root session](2026-09-13-nonroot-session.md).

| Executed check | Result | Duration |
| --- | --- | --- |
| Missing-required-ICU regression before fix | Expected FAIL |0.003s |
| Real retained-input composition | PASS |5.301s |
| Archive metadata/bytes, ARM64 ELF and three CLI calls | PASS |2.588s |
| Frozen active tier including15 composer fixtures |{'PASS': 96, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 0, 'NOT_SELECTED': 255} |136.023s |

The composer streams qualified input hashes into deterministic USTAR/gzip bytes,
compares measured and published streams and retains the3GiB host reserve.
Archive:26,671,977 bytes, SHA-256 `ef3c36cb6761e4840a86113d225e3fe85e548f871a6f0d0cbcf781ea771cf7a4`.
Manifest records every installed path, hash, size and mode; original source
files are not chmodded. It includes Denial, denialctl, engine/AOT/assets,
upstream launcher/user target, mobile wrapper, desktop entry and session policy.
It excludes machine configuration, accounts, hooks, service activation and keys.

Receipt publication was corrected before freeze: a direct final write could
expose partial JSON. Staging, synchronization and exclusive publication now
preserve existing receipts and remove owned success receipts on caught failure.
The15 focused fixtures cover incomplete inventories, wrong hashes/modes,
unsafe names, output reuse, source mutation, disk reserve, deterministic bytes
and receipt write/synchronization failures. The terminal receipt and matching
archive are both required; this is not a signing or admission protocol.

The archive's actual denialctl help/version and deniald help execute under
qemu-aarch64 against the retained authenticated ARM64 runtime, in a readonly,
network-disabled256MiB/no-swap container with32MiB RAM scratch and45s deadline.
No render device is exposed. CLI source, library entry and Cargo.lock match the
pinned upstream bytes. This checks loader/CLI compatibility, not live IPC or login.
The owned container was removed. No new GitHub CI or graphics VM was run.

66 independent old VM staging files were removed only after streamed identity,
open-handle/mount/active-use checks against retained durable copies. The complete
retired-to-retained map is bound in the qualification.120,332,288 allocated bytes
were reclaimed; all historical FAIL logs/results remain. No unique image deleted.
The prior515 artifact entries, existing pointer fields and historical current-state
body remain unchanged; one fixture set is appended. S06/R01 FAIL remain unchanged.

Changed implementation files: `scripts/host/compose-denial-session-payload.py`,
`scripts/host/test-denial-session-payload.py`, `configs/repository-tests.json`,
`scripts/host/test-repository-linux.sh`, `docs/development.md`,
`docs/development-lessons.md`. Publication adds this report/qualification and
updates the existing inventory, pointer, project status and generated header.

Next smallest authorized experiment: qualify an actual local systemd/logind
session in the isolated generic ARM64 VM with the original PAM package profile.
The current generic kernel lacks namespaces; inspect actual service startup
behavior before deciding whether a separately scoped VM kernel change is needed.
Missing namespaces are a source fact, not an observed logind failure. Real phone
GPU/rendering, touchscreen and every mobile physical row remain NOT RUN.

[Qualification JSON](2026-09-13-session-payload-qualification.json) binds exact
commands, archive and provenance hashes, test summaries, cleanup and limitations.
Private evidence: `/home/deck/.local/state/rog5-session-payload-20260913-r1`. No phone operation, signing/admission/claim, candidate
creation or protected-storage mutation occurred. Previous turn and this turn
made progress; use retained qualified inputs instead of rebuilding unchanged code.

Final metadata checks: five optimized checker cases and eight status cases PASS;
inventory, generated-status and whitespace checks PASS. These took0.939s,0.079s,
0.067s,0.047s and0.029s respectively. A separate comparison verifies all515 prior
sets, prior pointer fields, both acceptance contracts and the historical header
body unchanged. The active tier reports three declared optional subchecks SKIPPED;
no selected mandatory suite was skipped or blocked. Peak memory285.7MiB, swap0.
