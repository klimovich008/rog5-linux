# Current-head targeted recovery review

Result: **PASS after one safety correction and two regression-coverage
corrections; host-only, no boot authority.**

The review started from clean branch checkpoint
`23038a27136f458e5f6d628a85c82c3e05692564`. The requested diagnostic NFS,
exact UDC, exact-head CI, refreshed repository checkpoint, Generation-12
status, kernel-build acceleration, test-runner, and generic-consumer changes
were already present in `be33ea844ef0811353da3f46cafb26e884e73229` and
subsequent current-head commits. This pass reviewed those implementations
against the eight-item request rather than duplicating them.

No phone command, phone storage access, credential access, signing, flash,
wipe, erase, slot operation, persistent installation, or phone boot occurred.
Generation 12 remains consumed and non-retryable. The active stage-75/current-
cycle-postmortem successor remains unissued, `authority=none`, and absent from
boot policy.

## Concrete defects and regressions

1. The generic exact-record consumer opened and validated the source record,
   but then created `.entered` by hard-linking the mutable source pathname. A
   same-owner replacement between validation and `linkat(2)` could publish a
   poisoned irreversible marker. The consumer now creates `.entered` with
   descriptor-relative `O_NOFOLLOW|O_CREAT|O_EXCL` from the fixed repository-
   owned bytes, fsyncs and verifies it, revalidates the source fd/path before
   and after publication, and proves the validated source inode was unlinked.
   The hostile replacement regression requires an exact entered marker and a
   permanent second-consumer refusal. Running that regression against starting
   SHA `23038a2` fails with `starting HEAD published poisoned entered claim`.

2. The minimal live-cycle checkpoint implementation fetched the exact origin
   branch, but its fixture only tolerated the fetch. Deleting the production
   fetch would leave the suite green. The new stale-ref regression returns the
   stale SHA before fetch and a different current remote SHA afterward, and
   requires fetch to precede comparison. It fails against pre-fix checkpoint
   `f28f5ee9f63d7f3810f20cbbb548982225aad92f` because the stale ref is trusted.

3. The export-installer checkpoint had the same independent coverage hole.
   Its new behavior regression also requires refresh-before-comparison and
   fails against `f28f5ee9f63d7f3810f20cbbb548982225aad92f` with
   `pre-fix export installer trusted stale origin`.

The existing hostile suites continue to prove one diagnostic NFS attempt and
terminal UDC/interface/carrier/address/route/NFS classifications; zero,
multiple, wrong, renamed, and changing UDC refusal; exact PR-head and
intentional merge-ref CI; clean/incremental/ccache/locking build identities;
explicit test isolation; and consumed-candidate refusal. Current documentation
contains no claim that Generation 12 is unbooted or pending admission and does
not infer no crash from absent pstore lineage.

## Timings

Before timings at starting SHA:

- network-root init: 1,344 ms;
- exact-head workflow: 44 ms;
- minimal lifecycle: 74,826 ms (80 tests);
- kernel rebuild contract: 125 ms;
- acceleration contract: 1,178 ms;
- runner contract: 33 ms;
- exact claim consumer: 132 ms (8 tests).

After focused timings:

- network-root init: 1,331 ms;
- exact-head workflow: 43 ms;
- signing checkpoint: 2,226 ms (13 tests);
- export checkpoint: 424 ms (9 tests);
- minimal lifecycle: 74,815 ms (81 tests);
- kernel rebuild contract: 127 ms;
- acceleration contract: 1,180 ms;
- runner contract: 32 ms;
- exact claim consumer: 150 ms (8 tests).

The final `scripts/host/test-repository-linux.sh ci` timing and the exact ending
commit are reported in the handoff for the commit containing this record.
