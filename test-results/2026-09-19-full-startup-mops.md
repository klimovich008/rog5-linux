# Full-runtime startup MOPS comparison — 2026-09-19

**Both startup-only qualifications FAIL, at distinct boundaries. Neither run
reproduces the retained RCU stall.** Normal mode completes PAM/logind readiness
and cleanup but times out collecting unit timings. The nomops control times out
waiting for device initialization before PAM. No default MOPS workaround follows
from this pair. Denial rendering and phone operation are NOT RUN in these tests.
Historical S06/R01 FAIL, signed fallback and consumed claims remain unchanged.

Starting repository commit/tree: `f47e087c821693316fdc7d34b55ba8fb1b1312f3` /
`9b2086a8bc6588003b131db2e5fed69e7f8be893`.
Both VMs execute harness source `2f83c7cfdda80c529ab3d870eaee6a5b9973063d`, tree
`f590405f51dcff6c83304280e507e3e1760f4fdb`. Later parser correction `d693210a`
is tested by replay, not retroactively attributed to either VM. Final source
`c8d2b29c` also corrects an existing host test's cancellation observation window.
Exact identities and commands are in the
[qualification JSON](2026-09-19-full-startup-mops-qualification.json).

## Implemented and demonstrated

- `scripts/host/test-qemu-logind.py`: explicit `--disable-mops` appends only
  `arm64.nomops`. Default CPU behavior, kernel, containment and deadlines stay
  unchanged. The existing startup-only mode stages the combined runtime, probes
  authenticated device access and tears down without starting Denial.
- `scripts/host/test-qemu-logind-runner.py`: real parser and extracted production
  command-construction tests cover default/explicit behavior in both basic and
  combined modes. Before implementation the new cases fail on the absent option.
- The same files now reject an explicit failed timing packet even beside a valid
  inventory. The old parser accepted that mixed result in both record orders;
  the new semantic test demonstrates the failure and correction. A timeout now
  reports its code and captured byte count rather than a generic missing-record
  error. Replaying the normal log produces `startup timing query failed
  (code=124, bytes=569); inventory unqualified`. The original VM result stays FAIL.
- `scripts/host/test-launcher-diagnostics.py`: its cancellation test previously
  allowed exactly3s for a helper with a3s watchdog plus1s forced-kill grace.
  GNU timeout owns a separate process group; the function shell may defer its
  trap until that watchdog finishes. An active-tier failure exposed the boundary,
  and an unchanged focused rerun finished in3.010s. Observation now allows5s,
  including1s cleanup scheduling margin. Production timeouts, process signaling,
  nonzero-exit expectation and snapshot-removal checks are unchanged. Three
  optimized focused repeats pass in3.122s each; the full22-case suite passes
  in12.695s. This is a host-test observation correction, not a VM deadline increase.

## Executed comparison

| Arm | QEMU command | Harness including preparation | Qualification |
| --- | --- | --- | --- |
| Normal | 177.294s | 237.636s | FAIL: unit-timing query timeout |
| `arm64.nomops` | 165.670s | 221.625s | FAIL: initialized-device wait timeout |

Both containers exit and are confirmed absent. Both guests power off normally,
without a recorded kernel panic or RCU stall. Full original/mapped runtime bytes
and metadata remain unchanged, as do40 retained inputs from the prior session.
The28 inputs selected by these startup-only runs have identical hashes between
arms. Their21 initramfs members have identical bytes and nonvolatile headers;
archive inode/mtime fields differ, so the initramfs archives are not byte-identical.
Their exact hashes are recorded separately. This is one sequential pair with
changing cache/scheduling conditions, not a controlled performance result.

Normal mode hands off to PID1 at BOOTTIME80.49s. Device readiness completes
143.11→143.66s within its8s limit. PAM authentication/account/credentials/open,
active tty1 session, logind-mediated devices, PAM close/delete/end and scope
removal all pass. The timing diagnostic receives two property replies, then
waits on `systemd-journal-catalog-update.service` when its8s limit expires.
Captured payload contains only hardware-database and linker-cache unit records.
Those records show skipped conditions; they do not establish the duration or
success of the other seven required units. No complete timing inventory exists.

Nomops hands off at BOOTTIME79.93s. Device wait reports begin138.08/end148.61,
status1; its capture succeeds. The bounded post-failure snapshot itself expires
with status124. It records initialized DRM/input devices, then tty1/fuse nodes
without an initialization timestamp in that snapshot. This does not prove those
nodes caused the wait failure. The separate journal records logind observing the
keyboard at monotonic146.434535s; do not subtract across clock domains or infer
that a later snapshot proves readiness at the earlier deadline. PAM is NOT RUN.

Both arms retain max CPU, two guest CPUs, single-thread TCG,1GiB guest RAM,
2GiB container memory with no swap allowance, two-CPU quota,64-task limit,
network disabled, read-only runtime/payload,300s QEMU deadline and bounded logs.
The retained Deck render node remains exposed by existing combined preparation;
there is no physical-phone access or Denial session. Only the kernel argument
changes CPU-feature policy between arms. Compared with the preceding full-session
trial, both also omit interactive observation, its reference image/evidence writer
and settings diagnostic DSO, while selecting the existing startup-only branch.
No Denial/Flutter or kernel rebuild occurred; only the small existing VM probes
were rebuilt during preparation. No installed image or protected storage changed.

## Validation and next action

Initial focused checks pass5 command-mode cases,121 runner cases and8 startup
shell cases. After the parser repair, focused startup/command cases and the full
122-case runner pass; actual normal-log replay remains FAIL with a precise reason.
The first integrated run on sourced693210a records23 PASS,2 FAIL,86 BLOCKED,
255 NOT_SELECTED: the cancellation test times out, and another running suite is
terminated by the runner's fail-fast cleanup. These records remain preserved.
The final integrated run follows the cancellation correction; its result is
appended below. No failed physical or VM result is replaced by host test success.

The next source investigation is the exact packaged udev initialized-device
contract and tty/fuse startup ordering, plus the cost of the timing inventory.
Use the observed stage data before changing dependencies, query strategy or
budgets. Do not remove readiness checks, extend deadlines blindly, claim a MOPS
fix or repeat an unchanged full Denial session. Display/touch/GPU physical
qualification remains separate and requires its authorized process.

The previous goal turn and this turn are progress. This turn exercises the
larger startup workload, distinguishes two failures from the RCU hypothesis,
and fixes contradictory timing-result admission. The cancellation lesson is to
budget a test observer for the helper's existing watchdog and kill grace, rather
than racing exactly the nominal timeout. Preserve actual failed integrated counts
and run a new tier only after a justified correction.

Private evidence: `rog5-full-startup-mops-20260919-r1`; final integrated run:
`rog5-full-startup-mops-20260919-r2`. Reproduction commands and input/output hashes
are retained in the qualification JSON. Use fresh output/service names; do not
replay historical execution directories. All phone actions, signing, admission,
claim consumption and protected-storage operations remain unperformed.

A bounded upstream reference read at systemd commit
`3255daee1572366b74fe92f002a3d60ecbb27103` (v261.3) confirms that
[device_is_processed](https://github.com/systemd/systemd/blob/3255daee1572366b74fe92f002a3d60ecbb27103/src/shared/udev-util.c)
requires database initialization and no active ID_PROCESSING flag. A missing
USEC_INITIALIZED property alone is not an equivalent predicate. This narrows
the next diagnostic to database/processing state; it is an upstream reference,
not a reproduced Arch package build or a demonstrated cause of the VM timeout.

Final local active tier on sourcec8d2b29cc7e4bd9cd54f5591d9b44642a6a7a2ff: **111 PASS,
0 FAIL/BLOCKED/SKIPPED, 255 NOT_SELECTED** in 180.078s.
Three declared optional historical subchecks are skipped separately. Service
peak448.9MiB,0swap. Both VM qualifications remain FAIL. These are local
executions, not imported GitHub CI or phone evidence.
