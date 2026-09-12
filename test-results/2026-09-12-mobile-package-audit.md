# Retained mobile package audit, 2026-09-12

Added real archive verification to the existing native-mobile package graph
checker. The retained cache contains 14 archives matching the graph's pins.
All 14 pass archive/signature hashes, retained-key GPG verification, explicit
trust/revocation checks and signed `.PKGINFO` metadata comparison. The other 298
pins are missing. Only two of 28 root requests (`libdrm`, `wayland`) are verified.
The overall archive audit and mobile runtime closure remain **BLOCKED**.

The cached Mesa `1:26.2.2-1` does not satisfy this graph's `1:26.2.1-1` pin.
It is not substituted or counted as a verified graph member. The graph bytes,
retained repository snapshots and historical `signature_verified: false` fields
are unchanged. New receipts qualify actual bytes separately from that historical
metadata. No package was downloaded, installed or extracted onto a system root.
Small `.PKGINFO` streams are inspected in memory after authentication.

Starting source: `ebff99d3a1eace10dcd7e01d9f26365b6bb98098`, tree
`aa796146d56c246a0b12d23f7335a0d7789c8718`.
Initial implementation: `9828dcd2e81b54135418b58e940018794fb39add`.
Corrected frozen source: `074a54c8b4efed1db6617bbbdff0d88dda446fce`, tree
`d0ef2eafae7dfabff922ebe6471e3352bef1b6c2`. The later commit records qualification
only; its final commit/tree and clean state are recorded in private completion
evidence. No kernel/module/DT or target candidate was generated.

The verifier streams hashes, rejects nonregular or escaping input paths, checks
input stability, snapshots explicit public trust inputs, requires one acceptable
signature and one regular `.PKGINFO`, and compares name/version/architecture,
dependencies and providers. It rejects duplicate/oversized metadata. Subprocesses
have deadlines, output limits and owned group cleanup. The single-threaded CLI
defers stop signals across child creation and cleanup; it restores handlers and
signal masks afterward. Test keys are disposable fixtures, never production keys.

The new signed-package test fails on the starting implementation because the
archive-audit API is absent. This is a missing capability, not evidence that the
previous metadata-only command claimed to authenticate archives. A separate real
counterexample against the first implementation found that SIGTERM left its
sleeping child alive (state S after parent exit -15). The child was explicitly
cleaned up. New SIGTERM and SIGINT regressions require exit 143/130 and prove the
child has been reaped. The initial full CI run was intentionally stopped for this
fix; its interrupted `test-fallback-acm-control.py` result remains FAIL (signal
15), alongside 197 PASS, 108 BLOCKED, 3 SKIPPED and 30 NOT_SELECTED. It is not a
passing qualification of the corrected source.

| Executed check | Result | Seconds |
|---|---|---:|
| New API regression against starting source | Expected FAIL: capability absent | 0.072 |
| Initial archive fixtures, 9 groups | PASS | 0.369 |
| Metadata/archive focused suite, 15 groups | PASS | 1.102 |
| Initial final focused suite, 17 groups | PASS | 1.194 |
| Real SIGTERM counterexample | FAIL: child survived; explicitly cleaned | 0.073 |
| Corrected focused suite, 18 groups | PASS, including SIGTERM/SIGINT reaping | 1.657 |
| Runner reporting fixtures, 18 groups | PASS | 1.685 |
| Final cache audit | 14 PASS, 0 FAIL, 298 BLOCKED; exit 2 | 4.009 |
| Corrected frozen full CI tier | {'PASS': 306, 'FAIL': 0, 'BLOCKED': 0, 'SKIPPED': 3, 'NOT_SELECTED': 30} | 622.624 |

Final optional subcheck counts: `{'SKIPPED': 39}`. Whole-suite
SKIPPED results are declared optional historical checks, not missing mandatory
verification. All per-suite commands/timings and source-section results are in
JSON/JUnit. Runner contract, source syntax/link/secret and descendant checks
completed as part of this full tier. The interrupted first run took 329.738 s.
Final audit JSON SHA256: `79d42707b3d9a8553132df4adec6609cd15365e93c5c164171bebc3b322cb237`.


The active tier now includes the metadata/archive suite. Its manifest declares
git, GPG tools, bsdtar and the existing vercmp prerequisite, with a 300-second
suite deadline and serialized resource class. Ubuntu CI explicitly installs
gnupg/gpgv and makepkg; the latter supplies vercmp. Actual host tool versions and
hashes are recorded. GitHub CI and clean-Ubuntu execution were **NOT RUN** here.
Generic QEMU fixture checks do not establish phone hardware behavior.

Commands, individual integrated-suite durations/statuses, input and output
hashes, trust/tool identities and partial-run evidence are bound by the
[qualification JSON](2026-09-12-mobile-package-audit-qualification.json). Private
raw logs, full 312-package audit, JSON/JUnit and completion evidence are under
`/home/deck/.local/state/rog5-mobile-package-evidence-20260912-r1` (`E`). The focused
command was `TMPDIR=E/tmp python3 -O scripts/host/test-review-metadata-checkers.py`.
`python3 E/run-final.py` records the exact cache-audit command and public `ci`
tier invocation with two workers, 3 GiB memory and no swap. No unrelated kernel
or Denial/Flutter rebuild was needed.

Changed implementation/integration files: `scripts/host/check-mobile-package-closure.py`,
`scripts/host/test-review-metadata-checkers.py`, `scripts/host/test-repository-linux.sh`,
`scripts/host/record-ci-environment.sh`, `configs/repository-tests.json`,
`.github/workflows/offline-smoke.yml`, `docs/development.md`.
Qualification files: `configs/project-status.json`, `docs/current-state.md`
(generated header only), `docs/development-lessons.md`,
`manifests/current-artifact.json` (new audit pointer only), this report and its JSON.
All prior artifact-set entries and all existing artifact-pointer fields remain
unchanged. The original dirty checkout and other worktrees are untouched.

Remaining blockers, in order: obtain a coherent authenticated ARM64 repository
snapshot and the 298 missing archive/signature pairs; qualify keyring freshness;
complete matching Denial engine/AOT/ICU assets and runtime composition. The cached
newer Mesa requires its own coherent reviewed graph, not a pin substitution by
filename. Archive authentication is not installed-session or mobile UX proof.

All mobile physical rows remain **NOT RUN**; historical S06/R01 remain **FAIL**.
Board, signed/installed artifacts, fallback, touch and GPU qualifications are
unchanged. No phone contact, boot, power operation, production signing, claim,
admission or protected-storage mutation occurred. No physical session is armed.
The next smallest physical question remains separately authorized corrected
display scanout and blank cleanup using the existing reviewed plan; this audit
does not authorize it or require it before further safe offline work.
