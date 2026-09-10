# Generation 105 manual-host race result

Date: 2026-08-23

Result: **CONSUMED; HOST MISSED THE SHORT TARGET WINDOW.** Generation 105 must
never be retried or flashed.

The exact read-only any-prior target passed signed transfer, PREPARE, and
COMMIT. `ROG5 persistent root` NCM appeared at 09:14:32 and departed at
09:14:51. Stock slot A returned at 09:15:10. No target storage write was
permitted.

The manual workflow waited for one tool call to return before starting another
host watcher. The watcher began after target departure, so no stage or probe
verdict was retained. This is an R7/R6 host choreography defect and provides no
evidence that the target probe policy itself failed.

A bounded Opus review incorrectly assumed marker metadata had returned from the
phone; independent review rejected that claim. Its useful recommendation was
to remove cold host attachment from the target window. The repository's
existing continuous persistent-root runner already does so and historically
captured stage records from 14-second writer cycles. The successor therefore
reuses byte-identical target bytes under a fresh identity and must run only
through that lifecycle, not manual tool-by-tool orchestration.
