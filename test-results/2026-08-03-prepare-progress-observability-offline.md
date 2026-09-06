# PREPARE progress observability — offline

Date: 2026-08-03

Result: **PASS hardware-free; publication and wrapper integration remain;
no Generation 10 issued or booted**.

## Problem reproduced

Generation 9 completed the signed-bundle transfer, then lost recovery ACM
before a terminal `PREPARED` response. Host replay classification is now
preserved, but it cannot distinguish a fetch return, verifier handoff, kexec
load, prepared-state publication, or response-drain loss without bounded
device-originated evidence.

The new native tests first failed with an empty phase list at every success and
failure boundary. A separate injected send-failure test first observed all five
phases, proving that the responder had no mechanism to suppress later records
after the progress channel became unavailable.

## Contract and implementation

The canonical protocol adds five advisory PREPARE records:

1. `REQUEST_ACCEPTED` after request/session/state/capacity guards;
2. `FETCH_COMPLETE` after fixed-host acquisition succeeds;
3. `VERIFY_COMPLETE` after the plan and three sealed descriptors are accepted;
4. `KEXEC_LOAD_COMPLETE` after the bounded legacy load succeeds; and
5. `PREPARED_PERSISTED` after immutable prepared-state publication.

Each frame binds the exact session, request, bundle, manifest SHA-256, fixed
sequence/phase pair, `watchdog=ARMED`, and canonical body hash. A failed send
turns off all later progress attempts and suppresses every later write on the
possibly partial frame stream. It does not alter the existing PREPARE pipeline
or terminal replay state; a fresh same-session connection returns the terminal
decision without appending it to a poisoned frame or fabricating old phases.

The host accepts fragmented and coalesced records, rejects wrong identity,
duplicate, gap, reorder, and post-terminal records, and keeps one contiguous
prefix for the initial attempt plus one for the sole same-session replay. A
terminal loss reports both sanitized transport failures and both bounded phase
prefixes. Progress cannot run the pre-commit hook, create a durable intent, or
authorize `COMMIT_EXEC`; only a correlated terminal `PREPARED` can do so.

There is no in-band watchdog-exit claim. Every phase proves the watchdog was
armed at that boundary. Actual watchdog reset/fallback remains an independent
lifecycle observation because USB may disappear before an exit frame drains.

## Verification

- `python3 scripts/host/test-recovery-control-reference.py`: 51 tests pass.
- `python3 scripts/host/test-recovery-control-native.py`: 58 tests pass,
  including success order, stage-failure prefixes, exact correlation, replay,
  and injected advisory-send failure.
- `python3 scripts/host/test-stable-recovery-control.py`: 38 tests pass,
  including coalesced/fragmented parsing, hostile identity/order cases,
  initial/replay trace retention, and no-COMMIT behavior.
- `python3 scripts/host/test-recovery-candidate-integration.py`: 2 end-to-end
  signed-bundle composition tests pass with exact success and rejection
  progress prefixes.
- `scripts/host/test-repository-linux.sh ci`: complete repository CI passes.
- A constrained, tool-free Claude Opus review identified the partial-frame
  stream risk; after the response-suppression correction, its targeted
  production-diff re-review returned `NO FINDINGS`.

This increment performs no device discovery, credential use, signing, wrapper
issuance, phone boot, flash, wipe, slot change, or phone-storage access.
