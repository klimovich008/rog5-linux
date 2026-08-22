# Generation 83 BusyBox od result

Date: 2026-08-22

Result: **consumed; exact tool dialect identified; fallback passed.**

Direct magic remained unknown because sealed BusyBox 1.37 `od -An -tx1`
compresses duplicate output lines to `*`. A host-side execution of the exact
sealed BusyBox reproduced this behavior and proved `od -An -v -tx1` emits the
required 128 lowercase hex characters. Mount status 255/`EINVAL`, exact stock
slot-A fallback, host cleanup, and `FALLBACK_RETURNED` passed. No phone-storage
write occurred. Generation 83 must never be retried.

Private evidence remains outside Git at:
`/home/deck/.local/state/rog5-generation83-live-20260822-r1`.
