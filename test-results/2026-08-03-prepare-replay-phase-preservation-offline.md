# PREPARE replay phase preservation — offline

Date: 2026-08-03

Result: **PASS host-side; recovery-side phases still required; no Generation 10
issued**.

## Problem reproduced

The Generation-9 lifecycle proved that the initial exact ACM connection
delivered PREPARE and triggered a complete bundle transfer. When that transport
later disappeared, `prepare_and_commit()` attempted its permitted same-session
replay. Replay discovery encountered the already-returned Alpine product and
raised the bounded product-mismatch classifier, replacing the original
transport-loss reason.

The new hardware-free regression first failed because ACM discovery had no
phase parameter and no phase-specific exception. A second regression reproduced
the exact shape: initial `recovery ACM departed before response`, followed by
216 `product-mismatch` replay samples.

## Correction

- stable ACM discovery accepts only `initial` or `prepare-replay` and includes
  that phase in its bounded failure;
- PREPARE replay calls discovery with `prepare-replay` explicitly;
- replay failure raises one `TransportLost` record containing the fixed initial
  transport reason plus the sanitized replay classifier;
- unexpected replay exceptions expose only their class name;
- the first serial descriptor is closed exactly once before ownership can move
  to a same-session replay connection; and
- the existing single absolute PREPARE deadline and cross-session refusal are
  unchanged.

`COMMIT_EXEC` behavior is unchanged: no retry occurs after a transmitted intent.
This change performs no device discovery, signing, credential access, phone
boot, or storage operation.

## Verification

`python3 scripts/host/test-stable-recovery-control.py` passes all 33 tests,
including explicit phase validation, Generation-9-shaped replay failure,
deadline sharing, request correlation, and the no-COMMIT preflight path.

Generation 10 remains prohibited. The next hardware-free increment must add a
bounded device-originated phase contract for fetch completion, signature and
bundle verification, kexec load, prepared-state publication, and watchdog exit.
