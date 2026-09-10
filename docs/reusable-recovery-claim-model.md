# Reusable recovery and one-use target claims

Status: design checkpoint; not yet a live-authority change.

## Decision

The signed, byte-identical recovery transport may be reused after a session
ends **before COMMIT** and the host proves clean rollback. A target execution
intent remains permanently one-use: its claim becomes consumed immediately
before the first `COMMIT_EXEC` write and stays consumed after success,
transport loss, timeout, or any ambiguous outcome.

This separates two resources that currently share one claim:

- **Recovery transport** — fixed ASUS wrapper, fixed recovery initramfs, fixed
  trust key, no candidate-specific code. Reusable only after a proven clean
  pre-COMMIT session.
- **Target execution** — exact signed bundle manifest plus one execution
  nonce. At most one COMMIT attempt, forever.

## State model

```text
recovery session:
  NEW -> BOOTED -> PREPARED -> PRECOMMIT_CLEAN
                         \-> COMMIT_BOUND
  any unproven transition -> QUARANTINED

target execution:
  ISSUED -> PREPARED -> COMMITTING -> CONSUMED
                  \-> ISSUED       (only after PRECOMMIT_CLEAN)
```

`COMMITTING` is written and fsynced before the host sends any COMMIT byte.
`COMMITTING` and `CONSUMED` are both irreversible refusal states.

## PRECOMMIT_CLEAN proof

All conditions are mandatory:

1. The host never began the COMMIT write and the durable intent ledger has no
   COMMIT record for the session/request.
2. Recovery returned a signed `ABORTED` or `IDLE` state for the exact session,
   or the exact stock slot-A fallback booted after the recovery watchdog.
3. No target-lineage record exists for that session. Absence of pstore is not
   used as proof of no target execution.
4. The served bundle, NFS listener, firewall rules, addresses, routes, mounts,
   and project processes are gone.
5. The next recovery boot re-verifies exact serial, product, USB topology,
   wrapper hash, recovery hash, trust key, battery, and temperature.

If any condition is missing, the recovery session is `QUARANTINED`. The
target claim may remain unconsumed only when the host can prove it never sent
COMMIT; the same recovery session is still not reusable.

## COMMIT boundary

The host performs these operations in order:

1. Verify the exact target claim is `ISSUED` or `PREPARED`.
2. Create `COMMITTING` with no-replace semantics.
3. Fsync the claim file and containing directory.
4. Revalidate pathname, owner, mode, content, repository checkpoint, device
   identity, recovery session, bundle manifest, and rollback deadline.
5. Send exactly one `COMMIT_EXEC`.
6. Replace `COMMITTING` with terminal `CONSUMED` evidence.

A partial write, timeout, process crash, USB loss, unknown reply, target
appearance, or fallback without correlated intent all remain consumed. No
operator flag may turn those outcomes into retry authority.

## Minimal implementation sequence

1. Add a recovery-session record beside the existing generic exact target
   claim; do not copy a generation-specific consumer.
2. Add one shell-free `ABORT_PREPARED` operation that removes only volatile
   verified bundle state and returns signed/correlated `IDLE`.
3. Make host parser failures before COMMIT request `ABORT_PREPARED`, then run
   the existing fallback and host-clean proofs.
4. Move target-claim consumption from “before recovery boot” to the durable
   pre-send COMMIT boundary.
5. Replay process death before, during, and after the COMMIT write. Only the
   first case may remain reusable.

Until all five steps pass focused and exact-head CI, the current conservative
one-recovery-boot/one-target claim remains authoritative.

## Invariants retained

- Exact device/product/topology and signed-artifact checks.
- Battery, thermal, storage-isolation, watchdog, and fallback gates.
- No target retry after COMMIT or an ambiguous outcome.
- No experimental flash or phone-storage write.
- Stock slot A remains the milestone fallback.
