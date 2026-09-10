# Generation 213 direct extent-18 pass

Result: **PASS; consumed; never retry.**

The target passed source admission, opened only the p24 write window, armed
exact-ABI softdog, and overwrote extent 18: 10,427 blocks / 42,708,992 bytes.
Exact BEGIN/PASS, sync, all-node relock, softdog disarm and terminal CHUNK_PASS
were retained. Durable intent resolved `TARGET_ACCEPTED`; exact slot-A fastboot
and cleanup passed. The complete cycle took 174.265 seconds.

Extents 1–18 now have exact PASS evidence totaling 485,732,352 bytes. The next
one-use target overwrites extent 19 only; fsck, grow and seal remain deferred.
