# Generation 198 host stage-parser failure

Result: **R7 host-only failure; consumed; never retry.**

Generation 198 booted the read-only watchdog probe. The target armed the APSS
watchdog and advanced to its exact `storage-locked` stage. The host runner
incorrectly allowed `storage-relock`, rejected the valid target frame, closed
the listener, and lost the remaining runtime evidence. This disproves the
working theory that watchdog probe itself stalled the target.

The target remained alive for its bounded 900-second window and returned to
exact slot-A fastboot. The host fallback waiter used the same 900-second
deadline and missed the transition at its final boundary. A later exact
fastboot proof passed at serial `M5AIKN00F0353YH`, product `lahaina`, slot A,
8711 mV, and `battery-soc-ok=yes`; durable intent resolved
`FALLBACK_RETURNED`.

No clone command or p24 write path was packaged. The successor fix accepts
only `storage-locked`, rejects `storage-relock`, samples identity once at the
deadline boundary, and gives the host 930 seconds to contain the target's
900-second fallback plus USB enumeration.
