# Generation 71 read-only storage preflight

Generation 71 was entered once on 2026-08-14 and is irreversibly consumed.
It must never be retried.

The temporary `fastboot boot` command completed, but the `ROG5 recovery` USB
product never enumerated. The verified Alpine fallback reappeared about 24
seconds after fastboot disconnected. Its latest complete PMIC record reports
`PS_HOLD` and `HARD_RESET`, with warm-reset count zero and no watchdog marker.
That is consistent with recovery calling its intentional rollback path before
USB setup; it does not identify which storage-preflight check failed.

No candidate storage write was observed. Pstore was unavailable in the
fallback, so absent crash evidence remains inconclusive. The supported signed
ACM workflow verified fallback identity; no recovery anchor existed, therefore
the later read-only PMIC/pstore inspection is not described as signed.

The concrete defect is diagnostic ordering: `run_storage_preflight()` executes
before the receive-only ACM reporter, and all check failures return one generic
rollback. The successor must preserve the same read-only checks while exposing
an exact bounded stage and terminal failure before rollback.
