# Generation 215 extent-20 segment-1 pass

Result: **PASS; consumed; never retry.**

The target passed source admission, canonical extent-20 map validation, the
p24-only write window and exact-ABI softdog arming. It overwrote segment 1 at
offset block 1,355,264 for 54,409 blocks / 222,859,264 bytes. Exact BEGIN/PASS,
sync, all-node relock, softdog disarm and terminal CHUNK_PASS were retained.
Durable intent resolved `TARGET_ACCEPTED`; exact slot-A fastboot and cleanup
passed. The complete cycle took 480.461 seconds.

The next segment starts at block 1,409,673 and contains 54,408 blocks.
