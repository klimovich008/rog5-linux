# Current-head targeted recovery follow-up

Result: **PASS focused review; five bounded safety defects corrected; host-only
and no boot authority.**

The review started from clean branch checkpoint
`682b6a1ff0fdb6be8e3cbb401802a733d4e83062`. It rechecked the complete
eight-item recovery request already implemented at the starting head and made
only the residual corrections below. No lifecycle redesign, kernel-config
cleanup, history rewrite, candidate issuance, credential use, phone command,
phone storage access, flash, wipe, erase, slot operation, persistent install,
or phone boot occurred.

Generation 12 remains consumed, removed from boot policy, permanently
non-retryable, and retained only as historical evidence. The active
stage-75/current-cycle-postmortem successor remains unissued, offline-only,
`authority=none`, and absent from boot policy. Missing pstore lineage is not
interpreted as evidence that no crash occurred.

## Concrete defects and regressions

1. `configure_usb()` verified the exact `a600000.dwc3` UDC after binding but
   could then return success after a carrier wait even if the UDC inventory
   changed. It now revalidates both the bound value and sole exact candidate at
   the carrier-success boundary and classifies a late change as
   `udc-bind-failed`. The hostile `late-change` case fails before this fix.

2. Post-NFS address classification accepted an additional IPv4 address as
   long as `169.254.77.2/30` was present. It now requires exactly one IPv4
   address and that exact CIDR. Hostile missing, `/24` lookalike, and extra
   address cases all terminate as `address-failed`; wrong gateway, device, and
   source-route cases terminate as `route-failed`. Diagnostic mode still makes
   exactly one mount attempt, with stages `70 75` on every failure and stage 80
   only after successful read-only verification.

3. The deployment-root builder and minimal runtime-acceptance runner still
   compared `HEAD` with an unfetched `origin/<branch>`. Both now fetch the exact
   branch into its exact remote-tracking ref before comparison. Their stale-ref
   regressions prove refusal before private archive/path inspection and before
   SSH credential or target access. The existing Python signing, export, and
   lifecycle checkpoint regressions remain unchanged and green.

4. The generic claim consumer could publish `.record.entered` through an open
   directory after the canonical claim root had been renamed, then fail final
   pathname revalidation while a replacement root retained an exact source
   claim. A second invocation could consume that replacement. The consumer now
   first requires a lifecycle-account anchor below a parent the lifecycle user
   neither owns nor can write, then publishes and fsyncs one exact no-replace
   profile guard there, validates guard owner/mode/content/link state, and
   publishes the claim-root marker. A hostile root replacement leaves the
   first irreversible guard and permanently refuses the second invocation; a
   writable or lifecycle-owned read-only anchor parent fails before either
   entry. This prevents the lifecycle user from making an accepted `0555`
   parent writable after entry and replacing the anchor.

5. If one explicitly isolated parallel suite failed, the repository runner
   exited without terminating or reaping its remaining parallel suites. Each
   isolated suite now owns a process group; the exit/signal trap sends a
   bounded graceful termination, kills any surviving group, and reaps each
   uncollected group leader. A dedicated supervisor remains the exact process
   group leader after the test reports status, so descendant inspection and
   all group signals occur before that identity is reaped; a missing leader
   refuses the signal instead of risking a recycled PGID. A nominally
   successful suite that leaves a live descendant is terminated and fails.
   Completed empty groups are then cleared only after supervisor cleanup.
   Shared-state suites remain sequential. The hostile runner contract includes
   both a TERM-ignoring descendant and a successful leader that exits before
   its descendant; it fails against the prior source.

The exact PR-head checkout/output verification, intentional merge-ref job,
candidate-publication dependency, workflow cancellation, incremental kernel
reuse/invalidation/locking/ccache contract, and unchanged clean release
identities needed no further implementation changes.

## Before/after focused timing

The first current-head checkpoint took **118,552 ms**. Key timings were NFS/UDC
`2,955 ms`, lifecycle `106,446 ms`, kernel acceleration `2,636 ms`, runner
contract `65 ms`, and generic claim consumer `382 ms`.

After the fixes, the final expanded focused checkpoint took **88,038 ms**:
NFS/UDC `1,496 ms`, exact-head workflow `49 ms`, signing checkpoint `2,696
ms`, export checkpoint `424 ms`, lifecycle `74,866 ms`, deployment-root
checkpoint `76 ms`, runtime checkpoint `452 ms`, kernel rebuild contract `125
ms`, acceleration contract `1,195 ms`, runner contract `6,415 ms`, and the
12-case generic consumer `203 ms`. The expanded runner timing includes both a
TERM-ignoring descendant and a successful leader that exits before its
descendant; the consumer timing includes the replaceable-anchor-parent case.
Timing differences are wall-clock observations, not performance claims. The
final complete CI timing and exact ending commit are reported in the handoff
for this tested tree.
