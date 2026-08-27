# Generation 209 bounded clone timeout

Result: **FAIL-CLOSED; consumed; never retry.**

Mainline passed runtime, bounded source admission, `clone WRITE`, and
`watchdog ARMED`. The `e2image -ra` operation then hit its exact 420-second
bound and emitted `terminal FAIL reason=clone`. Cleanup returned to exact
slot-A fastboot; intent resolved `FALLBACK_RETURNED`; battery remained 8712 mV.

p24 was writable and is therefore partial/unknown. No successor may write it
until a fresh read-only postmortem classifies its ext4 identity, size, UUID,
cleanliness, allocation state, and seal ancestry.
