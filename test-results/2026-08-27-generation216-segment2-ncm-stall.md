# Generation 216 segment-2 NCM stall

Result: **FAIL-CLOSED; consumed; never retry; manual recovery required.**

The target passed source admission, canonical extent-20 validation, the p24
write window and softdog arming. It emitted BEGIN for segment 2 at block
1,409,673 for 54,408 blocks, but never emitted PASS. NCM stopped responding
about 224 seconds later. Host evidence retained the exact `ROG5 local image
stage` gadget at USB path `1-1.2`, carrier remained 1, ARP was unresolved, and
the host CDC-NCM driver reported repeated TX watchdog timeouts.

The 840-second softdog did not return fastboot and the independent fallback
wait also failed. Segment 2 is partial/unknown. The next writer must overwrite
only its first 27,204-block half after physical fastboot recovery.
