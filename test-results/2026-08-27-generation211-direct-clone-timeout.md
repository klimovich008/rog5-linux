# Generation 211 direct clone timeout

Result: **FAIL-CLOSED; consumed; never retry.**

The target passed source admission, entered `clone WRITE`, armed softdog, and
then produced no further stage before the 840-second bound. Softdog returned
the phone to exact slot-A fastboot; host cleanup passed.

p24 is partial/unknown again. This is the second throughput failure at the
clone boundary. No new writer is allowed until systematic debugging adds
bounded per-extent progress and identifies whether a specific extent, direct
I/O mode, or same-device read/write interaction consumes the deadline.
