# Touch input semantics and artifact reuse — 2026-09-20

Starting source `fde58773d47b31aa4d63a0563f33f45964caa97d`, tree
`8161fea2a092c6e9642e48b6c4ffc3fc4fe1a9d9`. Frozen test source
`d75378a638a26b09ccc26c030112b53ed5d228d8`, tree `6c1a1ca7bdada4888b303a65c2f7abc0a791f930`.
Branch agent/review-correctness-20260912. The preceding community recheck was
no implementation progress: live Denial refs were unchanged and no source was
imported. This change completes a concrete offline prerequisite for touch input.
No phone operation, candidate, signing, admission, claim, protected-storage
mutation or ARM64 rebuild occurred. Physical rows remain NOT RUN; S06/R01 FAIL.

## Demonstrated gap and change

The existing driver harness replaced pointer emulation with a no-op and input
capability setup with syntactic checks. It could not observe the missing pointer
emulation behavior. The driver was not shown to be faulty. The new harness runs
its actual probe/IRQ/release/suspend functions with exact pinned Linux slot
initialization, pointer emulation, slot/frame operations and six inline helpers.
Fourteen complete function bodies are compared with Linux
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` when source is supplied.

New cases verify INPUT_PROP_DIRECT, BTN_TOUCH and ABS capabilities/ranges;
contact coordinates and movement; oldest-contact selection across tracking-ID
65535 to0; explicit UP and disappearing-contact release; malformed-frame and
suspend release; and terminal SYN_REPORT API requests. The old fixture's
pre-increment tracking ID was corrected to exact masked post-increment.
Removing the coupled pointer-emulation call now fails the contact assertion.
Removing DIRECT fails the derived capability assertion; the old syntactic flag
check already rejected that mutation, so it is not a newly discovered bug.

The sink records capability-filtered input API requests. It does not implement
input.c event suppression, coalescing or packetization, evdev or libinput.
Locks, fixed memory allocation, GPIO, I2C and rails remain bounded fixtures.
Initial compilation failed on the exact kernel function's signed/unsigned slot
comparison under host -Wextra -Werror. A pragma scoped to that exact extract
preserves source identity and strict warnings elsewhere; the initial log remains.
No driver-source change or hardware fault is inferred from that host failure.

## Executed verification

| Check | Result | Seconds |
| --- | --- | ---: |
| Retained artifact hashes and inert provider contract | PASS | 0.138 |
| Final focused actual driver + exact kernel, Python -O | PASS27 cases /8 mutation controls /14 function comparisons | 6.725 |
| Active integrated tier on frozen source | PASS112 selected tests | 206.728 |

Integrated counts: `{"BLOCKED": 0, "FAIL": 0, "NOT_SELECTED": 255, "PASS": 112, "SKIPPED": 0}`.
Subcheck counts: `{"SKIPPED": 3}`; these
are separately declared optional sections, not whole-suite skips.
These are locally executed tests, not imported CI results. JSON and JUnit plus
per-test durations/source-dependent sections are retained in the private root
`/home/deck/.local/state/rog5-touch-events-20260920-r1/active-report`.
The qualification embeds the summary; full log hashes bind retained evidence.
Active tier lacks external kernel source; its source-dependent NOT RUN sections
remain explicit. The focused command above separately executed14 source checks.
No exact-board rebuild, phone runtime, evdev/libinput or physical trial ran.
Agent development runs and the retained initial compile FAIL are separate from
final frozen test results, with identities and timings in the qualification.

Commands: `python3 /home/deck/.local/state/rog5-touch-events-20260920-r1/audit.py`;
`python3 -O scripts/device/test-rog5-touch-lifecycle.py --linux-source
/home/deck/Projects/rog-phone-linux-migration/repo/build/qemu-linux-source`;
`scripts/host/test-repository-linux.sh active`. The integrated owner command uses
systemd MemoryMax1GiB, swap0, TasksMax256, RuntimeMax600s, CPUQuota200%, workers2
and disk-backed scratch. Exact argv, tool hashes, all executed test durations,
source hashes and log hashes are recorded in the qualification JSON.

## Source, artifacts and remaining boundaries

The production Image, base/composed DTBs, corrected panel module, newer touch
module and relevant cec/drm_display_helper/drm_kms_helper/gpi closure all match
their recorded hashes. Ordered16 production patches and resolved config still
match qualification; touch driver/header/Makefile are unchanged. This is current
byte verification plus reuse of earlier build/ABI proof, not a new compile.

Touch driver SHA256 `d2ff4063df516a316b3716c841b99d82643474bfc07c63a946cdb8bed706c59f`;
retained touch module `0a191f48fccfebbe08902e25ba63127b2e86c2a60d727234b53a1e8f83c9b59f`;
panel module `e7a5ac14d92ded53ca480272f0272d8fe236a38b671c5deabb17ff44ba2a6191`.
The complete unchanged artifact identities and origins are in the qualification.
The inert DT keeps I2C4/touch/L3C/L8C/GPI0 disabled. Runtime protocol/FIFO/DMA,
L8C supply parent and physical rail/reset cleanup remain unknown. A successful
one-byte ID read would not qualify a62-byte event transfer. No module is loaded.

Next: reconcile the corrected display closure with the existing bounded60Hz
scanout/blank recorder and recovery controller, without substituting old composer
hashes. The smallest future hardware question is stable native60Hz scanout and
verified blank/cleanup on those exact corrected bytes. It needs separately
reviewed composition and authorization; no Ready session is armed. Touch and
A660 remain subsequent independent hardware questions. Prior signed136f does
not include these fixes; preserve it and the signed V11/ASUS rescue baselines.

Changed implementation files: `scripts/device/fixtures/fts3658u/{cases.c,
kernel-v7.1.4.c,stubs.h}`, `scripts/device/test-rog5-touch-lifecycle.py`,
`configs/mobile/trial-plans.json` (two touch hashes plus one stale GPU test hash),
`docs/front-touch-prototype.md`. Evidence/status changes: this report, its JSON,
`manifests/artifact-sets.json`, `manifests/current-artifact.json`,
`configs/project-status.json`, generated `docs/current-state.md`, and one lesson
in `docs/development-lessons.md`. Historical acceptance/evidence remain unchanged.

Qualification SHA256 `99a7d755bd4f987292b7ed9138b7e32a68d27ac90f9b29b0377ee079698d0a4b`.

## Post-integration active-plan reconciliation

The preservation check found one pre-existing stale GPU test reference in the
unarmed trial plan: test-gles-readback.py was pinned to
`b8e978386697f7f3d3bc091702cf12f1ed757855e46514ea403e2c8316298aa0`,
while the actual test is
`5cb8716b44cab9e3f6e6ddf5558b67e978ac38d2fc4ff86f3559c1ab5006ff32`.
Its history includes the XRGB8888 contract cases added at c889faea. That exact
current test passed in the frozen active run in12.672s. Update only its active
plan reference, not a candidate or historical receipt. The private failing check
and mismatch record are retained. The qualification JSON binds the frozen source
before this metadata correction; subsequent checks cover the corrected plan.
No unchanged GPU test or full integration tier is rerun for this metadata fix.

Final metadata checks: artifact inventory, generated status and eight mobile
status regressions PASS; whitespace check PASS. All591 previous artifact rows,
previous current-artifact entries, acceptance bytes and historical current-state
tail remain unchanged. All active trial test references match actual files.
The integrated service is terminal: inactive/dead, MainPID0; peak memory482.7MiB,
swap0. Metadata command timings:

- `python3 scripts/host/check-artifact-inventory.py`: PASS, 0.081s.
- `python3 scripts/host/check-mobile-status.py --write`: PASS, 0.047s.
- `python3 scripts/host/check-mobile-status.py`: PASS, 0.041s.
- `python3 -O scripts/host/test-mobile-status.py`: PASS, 0.083s.
- `git diff --check`: PASS, 0.065s.
