# Generation 212 direct chunk timeout

Result: **FAIL-CLOSED; consumed; never retry.**

Source admission, the p24 write window, and exact-ABI softdog arming passed.
Extents 1–17 emitted exact BEGIN/PASS pairs, proving 443,023,360 bytes. Extent
18 emitted BEGIN for 10,427 blocks but no PASS before the 840-second softdog
bound. The host command timed out at 850 seconds, exact slot-A fastboot and
cleanup passed, and durable intent resolved `FALLBACK_RETURNED`.

Failure class: **R4**. The 670,892,032-byte group exceeded measured same-device
throughput. Extent 18 is partial/unknown and Generation 212 is permanently
non-retryable. The smallest successor overwrites only extent 18, preserving
the proven 1–17 prefix and deferring extent 19.
