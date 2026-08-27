# Generation 217 segment-2A pass

Result: **PASS; consumed; never retry.**

The target passed source admission, canonical extent-20 validation, the p24
write window and softdog arming. It overwrote segment 2A at offset block
1,409,673 for 27,204 blocks / 111,427,584 bytes. Exact BEGIN/PASS, sync,
all-node relock, softdog disarm and terminal CHUNK_PASS were retained. Durable
intent resolved `TARGET_ACCEPTED`; exact slot-A fastboot and cleanup passed.
The complete cycle took 296.065 seconds.

Segment 2B starts at block 1,436,877 and contains the remaining 27,204 blocks.
