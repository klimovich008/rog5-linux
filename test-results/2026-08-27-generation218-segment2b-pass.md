# Generation 218 segment-2B pass

Result: **PASS; consumed; never retry.**

The target passed source admission, canonical extent-20 validation, the p24
write window and softdog arming. It overwrote segment 2B at offset block
1,436,877 for 27,204 blocks / 111,427,584 bytes. Exact BEGIN/PASS, sync,
all-node relock, softdog disarm and terminal CHUNK_PASS were retained. Durable
intent resolved `TARGET_ACCEPTED`; exact slot-A fastboot and cleanup passed.
The complete cycle took 294.734 seconds.

The next uncopied extent-20 range starts at block 1,464,081.
