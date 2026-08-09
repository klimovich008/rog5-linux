# Fallback ramoops transition preflight — offline

Date: 2026-08-09
Starting repository SHA: `e8651255debfa3f1f73b2d58e770148ff61939ae`
Recommendation: **HOLD**

## Outcome

The target → fallback → bootloader → observation-recovery retention proposal
previously verified the diagnostic target and observer identities separately,
but did not provide one action-specific runtime gate for the intervening
Alpine fallback. The normal fallback health check proved an empty pstore; it
did not prove that the fallback reserved the exact same physical window or
that no ramoops platform consumer had bound before the next transition.

`reboot-fallback-to-fastboot.sh retention-preflight` now adds that read-only
gate. It runs the existing exact fallback kernel, PID 1, compatible, ext4,
module, pstore, dmesg, and thermal checks, then verifies:

- exactly one of each accepted ramoops command-line parameter and no other
  `ramoops.*` parameter;
- two-cell reserved-memory addressing and sizing with empty `ranges`;
- exact `/reserved-memory/memory@9b800000` tuple
  `0x9b800000 + 0x400000`;
- no fixed sibling reservation overlapping that range, including multi-tuple
  and unsigned-64-bit overflow cases;
- no ramoops-compatible reserved-memory child, conventionally named platform
  device, or bound driver entry;
- no entry in either fallback pstore path.

All runtime traversal is descriptor-relative and no-follow. Open directories,
properties, and directory inventories are revalidated after inspection, so a
broken symlink, missing platform inventory, pathname replacement, late
optional property/driver/mount appearance, or changing consumer set fails
closed. The embedded interpreter is invoked with `-B`, preventing bytecode
cache writes outside the inspected fixture/runtime tree.

The action cannot request reboot and does not use the reboot authorization
guard. The existing `preflight` and `reboot` behavior is unchanged. No phone,
SSH credential, fastboot device, signing key, candidate, policy row, phone
storage, or boot action was used during this offline checkpoint.

## Hostile regression coverage

The fail-first focused suite rejected the prior helper in 0.070 seconds
because the retention verifier and action were absent. Ten final test
methods cover:

- one exact passing transition fixture;
- missing, duplicate, unknown, and wrong ramoops command-line values;
- wrong address cells, size cells, ranges, tuple, and missing target node;
- contained, enclosing, multi-tuple, past-limit, exact-endpoint-wrap,
  adjacent, and malformed reserved-memory siblings;
- symlinked target and broken sibling paths;
- direct, address-prefixed, compatible-child, driver-bound, and symlinked
  ramoops consumers;
- present pstore records and symlinked pstore roots;
- missing and replaced runtime directories, changing device inventory, and
  properties, driver directories, or mounted pstore appearing after an
  optional-absence snapshot;
- host action wiring, an explicit non-reboot guard, unchanged fixture bytes,
  zero fastboot calls, and a no-write source contract.

The first fixed Python suite passed in 0.594 seconds, but independent review
found incomplete consumer/path/range coverage and a weak no-reboot assertion.
After the first hardening pass, nine tests passed in 1.019 seconds. The
independent re-review then found three remaining defects: optional-absence
inventories were not all revalidated, bytecode writes were not explicitly
disabled, and a range ending exactly at `2^64` was admitted. The final ten-test
suite passed in 1.191 seconds (1.125 seconds inside `unittest`). The complete
existing
fallback reboot suite, including mocked preflight, retention-preflight,
acknowledged/disconnected `RESTART2`, anchored USB, product, serial, and
failure-class tests, passed in 18.347 seconds. Shell syntax, Python bytecode,
and `git diff --check` passed.

## Remaining boundary

This patch creates the gate; it does not supply its physical result. A future
retention experiment must run the action on the exact fallback boot reached
after a separately consumed diagnostic target and retain the result with that
cycle's private boot IDs. A passing result establishes that Linux exposes the
expected reservation and no visible ramoops consumer at that instant. It does
not prove that firmware preserved the prior bytes.

The experiment still requires two distinct one-use admissions: one execution
recovery/target identity and one observation-only recovery identity. Neither
may be replayed after success, failure, or ambiguity. Only the observer's
lineage-correlated `MATCH` or `MATCH_REPEATED` result can prove marker
retention; missing pstore remains inconclusive. Candidate issuance, signing,
credential use, and both physical boots remain separate decisions, so the
recommendation remains **HOLD**.

The pre-re-review complete repository Linux `ci` checkpoint passed in 476.076
seconds (user 153.145, sys 154.127). The final complete result after the three
re-review corrections passed in 475.843 seconds (user 152.405, sys 152.592),
including the ten verifier methods in 1.080 seconds and the complete fallback
helper in 18.331 seconds. The timing-only documentation update did not alter
the tested implementation.
