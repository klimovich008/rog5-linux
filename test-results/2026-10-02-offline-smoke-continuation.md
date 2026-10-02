# Offline smoke continuation, 2026-10-02

Scope: host CI, warning-policy tooling and offline tests only. Starting HEAD
was `16221dbb` on `agent/ci-fix-261002`, after the four commits below and
`db5b9d4f`. No push, other-branch/ref changes, phone access, or phone PIN reads.

## Work already committed and verified

| Commit | Change | Verification in this continuation |
|---|---|---|
| `ad4d6bda` | Canonical warning keys, exact header re-pin, reviewed explanations for the six CI warning files, checker/drafter path handling | Replayed the original CI logs: 154 rejected before, zero after; tested hash, configuration, location and count rejection |
| `1b3abb06` | Restore the tracked persistent-trial-state v1/v2/v3 helpers and metadata | All nine files match `b3e4dc25^` byte for byte; artifact and consumer suites pass |
| `b39396e5` | Ubuntu portability, current module/patch expectations, declared optional subchecks, report index | Affected module, idle-power, finalization, installer and helper tests pass; inspected the previous Ubuntu CI/nightly receipts |
| `16221dbb` | upload-artifact v7.0.1, explicit gawk, 30-minute head/merge and 120-minute board budgets | Exact-head workflow regression passes; reviewed action release and workflow dependency/retention wiring |

The previous Ubuntu 24.04 checkout's tracked files match this continuation's
starting tree (apart from local skill links). Its retained real-runner receipts
report CI **111 PASS**, zero FAIL/BLOCKED, with 43 declared skipped subchecks;
nightly **112 PASS**, zero FAIL/BLOCKED, with 44 declared skipped subchecks.
Those are prior-agent results, not new full-tier runs of this commit.

## Root causes

The missing profile suite is a publication omission. Both
`scripts/host/test-rog5-device-profile.py` and the executable
`scripts/host/rog5-device-profile` were added in `914217cc`, exist in local
`33f9f852`, and remain tracked here; the registry legitimately consumes them.
The supplied public `566c3faf` snapshot omitted them while retaining their
registry row. The exact external scrub rule could not be identified: that
public commit is unavailable in local objects, direct network access cannot
resolve GitHub, and web retrieval of the public repository/commit failed.
No public history was fetched into another ref or rewritten.

The board failure is not a warning-count difference caused by clang 18.
Local ccache prints `../source/<file>`, while CI clang prints the absolute
source path. The old policy's drafted keys retained `../source/`, whereas
the old checker stripped the absolute prefix in CI. It therefore rejected
152 initializer overrides plus the fuse and PCA9532 warnings. The retained
44-message traps review also carried an obsolete `esr.h` dependency hash;
its relative-path drafted duplicate masked that locally. The previous agent
fixed the keys, removed duplicate owners and pinned the v7.2.7 header with
specific reviewed reasons. Warning ceilings, source hashes, config guards,
schema rejection and depmod rejection remain enforced.

## Work finished here

- Static preflight now requires the registry, every suite, and every declared
  required input to be a tracked, present, regular repository file. Ignored
  local copies cannot conceal an incomplete publication. Missing tracked
  scripts produce diagnostics instead of a Python traceback.
- Warning normalization changes only the leading diagnostic filename,
  including kernel-doc's `Warning: ` prefix. It preserves message contents.
- The drafter normalizes retained reviews as well as new messages, uses the
  actual object-to-source relative path, drops pins with absent dependencies,
  and preserves the first owner of legacy duplicate reviews. Equal path
  aliases retain their original ceiling; conflicting counts require review.
- Extended the existing registered static and diagnostics suites. Added their
  consumed tooling/policy inputs and all nine helper files to the registry;
  declared `setsid` for the daemon fixtures.
- Daemon fixtures now clean their separate process groups on assertion
  failures and signals as well as success. Their poll sleeps cannot escape
  the test supervisor after a failed fixture.
- Documented checking the clean exported Git checkout before publication.

## Validation

- `python3 scripts/host/check-repository-static.py`: PASS.
- Static regression: 7 tests PASS. Diagnostics regression: 28 tests PASS
  under ordinary Python and `python3 -O` (the registry/CI execution mode).
- The updated drafter migrated the pre-fix policy against the retained r111
  build: two initializer pins and 32 reviewed files retained, no new messages
  drafted, and no duplicate canonical keys. This migration is tooling
  evidence; the checked-in production policy keeps the individual reviews.
- Replayed four original CI logs after verifying each recorded log hash,
  substituting only the source/object build roots with the retained r111
  paths. Of 1,272 diagnostics, the old checker/policy rejected 154 and the
  current checker/policy rejected zero:

  | File | Previously rejected |
  |---|---:|
  | `drivers/perf/arm_pmuv3.c` | 55 |
  | `arch/arm64/kernel/cpufeature.c` | 48 |
  | `arch/arm64/kernel/traps.c` | 44 |
  | `arch/arm64/kernel/cpu_errata.c` | 5 |
  | `fs/fuse/ioctl.c` | 1 |
  | `drivers/leds/leds-pca9532.c` | 1 |

  The CI artifact lacks installed modules and the full source/object trees.
  Replay proves warning acceptance against retained exact files, not a fresh
  kernel build or a complete requalification of installed-module closure.
- Individual affected/consumer suites PASS: device profile (13 tests),
  installer (23), module packaging (4), idle-power votes (9), native Wi-Fi
  finalization (12), standalone rescue composition (4), persistent trial
  state (19, one declared skip), Wi-Fi selector (5), native Wi-Fi boot (42),
  both slot-B loaders, persistent helper artifact, production kernel builder
  (13), charge/sleep policies, workflow, report index, and test-report tooling
  (19).
- Seven affected suites also PASS through the actual CI per-suite driver,
  `repository-test-report.py run`: static checks, optimized diagnostics,
  charge policy, sleep policy, helper artifact, workflow and report tooling.
  The helper's two unavailable private subchecks are recognized as declared
  skips. These receipts verify the real deadlines/output classification and
  daemon descendant cleanup without claiming a complete tier run.
- The complete CI runner was attempted with
  `ROG5_TEST_TMP_PARENT=/tmp ROG5_TEST_REPORT_DIR="$PWD/build/ci-continuation/ci"
  bash scripts/host/test-repository-linux.sh ci`. Static preflight passed, but
  the sandbox forbids binding its Unix socket; all 111 suites remain BLOCKED.
  No checks were weakened to accommodate this sandbox.
- Additional consumer checks exposed the same sandbox restriction:
  headless CPU policy's systemd graph/verify checks fail with `SO_PASSCRED:
  Operation not permitted`; two sealed BusyBox namespace checks fail because
  bwrap cannot create a `NETLINK_ROUTE` socket. Their unaffected extraction
  checks pass. These suites passed in the retained Ubuntu runs, subject to
  the registry's explicit systemd-version skips.
- Qualified AArch64 QEMU replay and private twin rebuild were skipped exactly
  as declared: this checkout lacks the qualified private emulator/image.
  The tracked ELF/hash/metadata checks still passed. Podman cannot start here
  because its runtime directory is read-only.

Logs and JSON receipts are under ignored `build/ci-continuation/`; the original
CI artifact and previous Ubuntu evidence were only read. No kernel rebuild
was needed to answer the path/policy question. Board compilation, board-tier
source checks, QEMU job and panel compilation remain for the published CI run.

The sandbox mounts this worktree's Git admin directory (including its index)
read-only, despite permitting writes to the shared object/ref store. The
continuation commit uses a temporary Git admin directory/index under
`build/ci-continuation/git-admin/`, whose HEAD names only the existing current
branch and whose common directory is the original shared Git store. No other
branch was changed. Working files are verified against the resulting commit;
the original worktree index needs `git read-tree HEAD` outside this sandbox
to remove its stale pre-commit entries. That command refreshes only the index
and preserves the working files and branch history.

## Publication and hardware verification

Publish the complete current source tree, including both profile files and
their reference profile/consumers, all nine tracked persistent helper files,
the reviewed warning policy and checker/drafter together, the registry and
test fixes, and the updated workflow. Publishing only this continuation's
diff onto the incomplete public snapshot would leave the profile files
missing. Do not export by dropping the ignored `artifacts/` parent wholesale.

In a fresh checkout of the prepared public commit, install the dependencies
listed in `head-exact`, bootstrap the pinned boot tools and canonical template,
then run:

```sh
python3 scripts/host/check-repository-static.py
scripts/host/fetch-android-boot-tools.sh
scripts/host/build-canonical-boot-v3-template.sh
ROG5_TEST_REPORT_DIR="$PWD/build/publish-ci" scripts/host/test-repository-linux.sh ci
ROG5_TEST_REPORT_DIR="$PWD/build/publish-nightly" scripts/host/test-repository-linux.sh nightly
```

Both report directories must be new. Use the workflow's exact v7.2.7 fetch,
production build and `ROG5_LINUX_SOURCE` board-tier commands for board
verification. A published run must show successful head-exact and selected
board-production/panel/QEMU jobs, with intentional merge-compat handling for
the event. This session did not publish or claim a green remote run.

No on-phone verification is required for these host/test-only changes.
There are no phone steps to execute for this task.
