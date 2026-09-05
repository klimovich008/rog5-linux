# Two-claim retention sequence reference — offline

Date: 2026-08-10

Starting repository SHA:
`a7fa97d0b76c3e474e45ee327f4d71a776077e32`

Recommendation: **HOLD**

No phone, USB device, phone storage, credential, signature, claim issuance,
temporary-boot policy row, privileged host action, flash, wipe, slot operation,
persistent installation, or phone boot was used. Generation 12 remains
consumed and non-retryable. The isolated VCNL36866 work was not touched.

## Concrete defect fixed

The joint retention profile listed the intended physical order, but it did not
define the transaction semantics around two irreversible claims. The existing
execution lifecycle, fallback transition helper, observation gate, and
postmortem reader each enforce their own boundary; no common contract proved
when each claim may be consumed, how target boot-ID lineage crosses the
fallback transition, what survives each failure point, or that one observer
read is the terminal operation.

`retention-cycle-sequence-reference.py` is a pure no-I/O state model for that
missing contract. It cannot inspect a host, read credentials, consume a claim,
invoke a program, contact a device, or boot anything. Its only command prints
one canonical `reference-only`, `authority=none`, `boot_authority=none`,
`HOLD` plan.

## Exact cycle and draft claims

The model binds the final reviewed pair:

| Input | SHA-256 |
|---|---|
| cycle descriptor | `d8a3a085d2dfb474728d16cdf568547e529f026239a37a40881183c04ed8a078` |
| execution recovery AVB | `cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d` |
| observer recovery AVB | `3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b` |
| execution draft record, 557 bytes | `ef0895b7e104a283c44113a67c8f51e826b0088d597b0969ed5ca774e0dc7bbd` |
| observer draft record, 555 bytes | `f0b687163c38fe07c637c6ae863e0244d5cfb2af2d6a97632875473e3c33e345` |
| sequence-reference source, 11,923 bytes | `97075ed7c09cf2c5df5566a971c922d8ea9b1d6b0e53e19f33bed3d220378e44` |

Both draft records bind the cycle digest, both recovery identities, candidate
`headless-netroot-early-diag-v2`, and runtime manifest `54f53420…6efc`.
They differ by role and selected recovery. They are deliberately absent from
the generic consumer. The profile still says `execution=not-defined` and
`observer=not-defined`, and central policy still has zero `allow` rows.

The existing authority-free retention verifier now pins the exact reference
source, cycle digest, and both draft-record digests. It reports
`draft_claims=unregistered`; changing the reference source or any nested
contract field fails closed.

## Enforced order

The model permits one path only:

1. exact execution and observer preflight with no registered claims and zero
   policy rows;
2. irreversible execution-claim entry;
3. exact execution recovery with rollback armed;
4. exact candidate and canonical target boot-ID observation;
5. correlated exact Alpine fallback and resolved execution intent;
6. exact unconsumed ramoops transition preflight;
7. same-port, exact-product, same-serial bootloader proof;
8. irreversible observer-claim entry;
9. exact observer recovery on the same anchored device with rollback armed;
10. exactly one candidate/boot-ID-bound `postmortem-status` read; then
11. terminal result with retries forbidden.

Out-of-order, duplicate, weak-identity, rollback-off, wrong-port, replacement
serial, wrong-claim-body, wrong-lineage, or second-read paths are absent. A
failure before execution-claim entry is `NO_BOOT`; every later failure is
`UNKNOWN`, with the exact already-entered claim set preserved and no retry.
`UNAVAILABLE`, `NO_RECORDS`, `NO_MARKER`, `AMBIGUOUS`, and
`DIFFERENT_MARKER` remain `INCONCLUSIVE`. `MATCH` and `MATCH_REPEATED` prove
only `LINEAGE_RETAINED`; they do not claim that no crash occurred.

## Regression evidence

The fail-first test stopped in 62 ms because the reference file was absent.
After implementation:

- sequence reference: 8/8 hostile groups pass in 0.113 seconds;
- joint retention admission: 21/21 pass in 2.932 seconds and repeat in 2.791
  seconds;
- generic exact-record consumer: 13/13 historical/hostile cases pass in 0.215
  seconds; and
- repository-runner contract: PASS in 5.915 seconds.

The final complete local CI timing is recorded below after the staged tree is
frozen.

## Gaps before a live runner

This model deliberately does not disguise the missing implementation:

- neither draft record is registered or issued;
- both current recovery gate profiles reject connected actions;
- the consumed Generation-12 lifecycle cannot be reused for the new execution
  role;
- the fallback helper proves same-port fastboot only inside its own call, while
  the later image-boot helper does not yet consume the new durable port anchor;
- an [offline transaction journal](2026-08-10-retention-cycle-transaction-offline.md)
  now carries target/fallback boot IDs, both claim dispositions, the fixed
  port/serial, and the one observer read, but no live orchestration adapter
  consumes it; and
- no exact-head-reviewed live profile or policy admission exists.

The minimal next implementation is a hardware-free adapter fixture that proves
the existing fixed entry points are ordered behind the journal's durable
intent records. It must continue to reject real execution until the two exact
claims and both live profiles are separately reviewed and admitted. Neither
the sequence reference nor the journal is that runner. Recommendation remains
**HOLD**.

## Final checkpoint

Starting and ending repository SHA:
`a7fa97d0b76c3e474e45ee327f4d71a776077e32` (the staged offline checkpoint
does not create a commit).

The exact final command was:

```sh
REQUIRE_CURRENT_PRODUCTION_ARTIFACT=1 \
REQUIRE_CURRENT_OBSERVATION_ARTIFACT=1 \
scripts/host/test-repository-linux.sh ci
```

Result: PASS in 332.609 seconds. The preceding complete-CI checkpoint was
313.848 seconds, so this run was 18.761 seconds slower (5.98%). The registered
sequence-reference suite passed 8/8 in 0.118 seconds, and the joint retention
admission suite passed 21/21 in 2.870 seconds. `git diff --check` and
`git diff --cached --check` passed before the run. No phone, credential,
signing, claim-consumption, policy-admission, privileged-host, or retained-build
operation occurred. Recommendation remains **HOLD**.
