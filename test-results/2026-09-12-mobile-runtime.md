# Native mobile payload and ARM64 ABI checks, 2026-09-12

The authenticated 315-package snapshot now has a confined host-test payload tree.
Retained ARM64 Denial, foot, Mousepad and the GLES probe load against those exact
Arch libraries. Denial help, application version commands, software rendering
and explicit refusal of software as A660 hardware evidence pass. This is **not**
a Denial session, installable image, new candidate or physical qualification.
Matching Flutter engine/AOT/ICU and the native touch-first session remain open.

Starting commit `64b5e53d12ea2726f10b34255f95a0637dc5bbc7`, tree
`9dbc7aed4e26121698afa74e2564a155bf75de75`. Initial assembly source was
`d882c49b541c913750346959634e48cfbbbf509b`. Corrected frozen source is
`1205091552cc9cd3b986594c57535468262e266e`, tree
`2865ab6ed02133e220f130030dc0d2555416647d`. Subsequent edits only record evidence,
status and lessons. Final commit/tree are retained in private completion evidence.
The branch remains `agent/review-correctness-20260912`; the dirty original checkout
and all other worktrees were preserved.

The new materializer repeats signature/metadata authentication, checks archive
paths and payload conflicts, reserves 3 GiB free disk, and extracts through
bubblewrap with no network, host private directories or physical device nodes.
It executes no package installation hooks. Package metadata, ownership and
privileged permissions are excluded from this test-only composition. Output must
be new; a failed authentication creates no payload root, and an existing receipt
is never overwritten. Every regular output file is stream-hashed, with symlink
targets and modes recorded separately. The 65,076 archive entries produce 55,666
unique tree entries after shared directories and package metadata are accounted
for. Regular payload bytes total 1,487,110,995.

A real package exposed a correctness gap in the new assembler:
`dbus-daemon-launch-helper` became execute-only under the restrictive extraction
umask. All packages extracted, but the evidence manifest could not read that
helper, so the initial assembly correctly remained FAIL (81.803 seconds). The
new execute-only fixture fails before the fix and passes afterward. Normalization
now makes fixture files owner-readable and directories owner-traversable, stripping
privileged mode bits. It does not claim installation permissions are preserved.
The 11 fixtures also cover metadata exclusion, hardlinks, symlinks, path traversal,
conflicting payloads, archive drift, disk reserve and existing-output preservation.
The symlink-alias attack was already rejected by libarchive: no workaround was
needed. The suite is mandatory and serialized with namespace tests in the existing
public tiers, including Python `-O` and a 120-second deadline.

| Personally executed check | Result | Seconds |
|---|---|---:|
| Focused materializer regressions, final source | 11 PASS | 0.435 |
| Fresh authenticated payload assembly | PASS, 315 packages | 81.434 |
| ARM64 QEMU loaders, CLI versions/help and software GLES/refusal | 11 PASS | 2.598 |
| Strict ARM64 GSettings cache generation and clean Mousepad version | 2 PASS | 0.530 |
| Frozen active repository tier | 85 PASS; 0 FAIL/BLOCKED; 0 whole-suite SKIPPED; 255 NOT_SELECTED | 125.816 |
| Duplicate scratch verification and reclamation | PASS | 23.881 |
| Final metadata checker regressions | 19 PASS | 1.920 |
| Final generated mobile-status regressions | 8 PASS | 0.018 |

The active tier separately reports **3 declared optional subchecks SKIPPED**:
sealed charging archive replay, retained ARM trial-helper replay, and the retained
ARM PMIC rail-reader artifact. These are enumerated in its JSON/JUnit evidence.
The earlier 306-PASS full CI belongs to the preceding package-snapshot source and
is not represented as a new full-CI run. No unchanged board build was repeated.

The first ABI harness attempted to add missing mountpoints under a read-only
root; all 11 commands failed in bubblewrap before guest execution. The corrected
harness mounts its retained executables under private `/tmp` and succeeds. Those
original failures remain recorded. Likewise, the first active-tier wrapper lacked
`/usr/bin/time`; it executed no suite. Bash's built-in timer measured the successful
run without installing another host tool.

Mousepad initially returned version success with missing GSettings-schema
warnings. A separate overlay copies the exact schema sources, runs the package's
ARM64 `glib-compile-schemas --strict` under QEMU, and then requires a warning-free
Mousepad version command. Both pass, with source files unchanged. This explicit
cache step is not an installation-hook run and does not qualify every generated
cache, desktop portal, application interaction or graphical session.

The selected Denial binaries are retained builds of upstream commit
`85b2303e2f09ae7b7b993641f90061a200f03d53`, not newly compiled binaries:
`deniald` SHA-256 `8698b0716c0ab16ab5c33d618ae52cef0cd8c0966ad356cf2ca49d78a0ba8591`;
`denialctl` SHA-256 `da22a0bd76e183cd25ce45ef532ae3ee533703dd5f6e00809ce2f3415b8566df`.
The retained probe SHA-256 is
`77c98c27e8bb2f8913bbfddc5429cebf5495161da7e3e6a86fdc7761cafecffa`.
QEMU proves selected userspace behavior only. The renderer is explicitly softpipe;
no DRM node, phone, accelerated rendering, native fence or DMA-BUF behavior is
inferred. The payload tree was rehashed unchanged after execution.

Tree-manifest SHA-256:
`d0c54597856c2205f6c19abb932182ffcf61102c9c0caaf39df76852fccfd75b`.
Separate generated GSettings cache SHA-256:
`d76471d85118a43eb466b9298e90ff97eb584f11df9520130a565619f6a6f59a`.
[Qualification JSON](2026-09-12-mobile-runtime-qualification.json) records exact
commands, source/tree, tool hashes/versions, input binaries, output and log hashes,
per-check durations and private evidence paths. The artifact inventory adds one
fixture set while preserving all 463 previous entries. The current pointer names
this host tree and cache overlay explicitly; it grants no release authority.

After normalizing only the failed scratch's permissions for comparison, all
55,666 entries matched the successful retained tree. Removing that verified
duplicate reclaimed 1,605,574,656 bytes. Failed receipts and logs remain intact;
no historical artifact was deleted. Approximately 5 GiB remained free afterward.

All mobile physical rows remain **NOT RUN**. Historical S06/R01 FAIL, the headless
contract, accepted rescue/server, kernel/DT/modules, prepared signed candidate,
fallback and consumed claims remain unchanged. No phone operation, protected
storage mutation, signing, admission, claim consumption or candidate generation
occurred. The next offline dependency is the matching engine/AOT/ICU bundle and
its bounded build capacity. The next smallest physical question remains the
separately prepared corrected display/touch/GPU trial under fresh authorization;
this task does not execute or authorize it.

Changed files in this group:

- `scripts/host/materialize-mobile-runtime.py`
- `scripts/host/test-mobile-runtime-materialization.py`
- `scripts/host/test-repository-linux.sh`
- `configs/repository-tests.json`
- `docs/development.md`
- `docs/development-lessons.md`
- `configs/project-status.json`
- `docs/current-state.md`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`
- `test-results/2026-09-12-mobile-runtime-qualification.json`
- `test-results/2026-09-12-mobile-runtime.md`

Final metadata-only commands were `python3 -O
scripts/host/test-review-metadata-checkers.py`, `python3 -O
scripts/host/test-mobile-status.py`, `python3
scripts/host/check-mobile-status.py --write`, `python3
scripts/host/check-artifact-inventory.py`, and `git diff --check`. The final
metadata suites passed after updating the status/evidence pointers; they do not
replace the frozen-source active tier. Preliminary extraction fixtures passed
10 cases in 0.408 seconds before the real execute-only package added case 11.
