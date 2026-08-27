# Generation 219 segment-3A hard stall

Result: **FAIL-CLOSED; consumed; never retry; physical recovery required.**

The target passed source admission, canonical extent-20 validation, the p24
write window and softdog arming. It emitted BEGIN for segment 3A at block
1,464,081 for 27,204 blocks / 111,427,584 bytes, but never emitted PASS.

About 158 seconds after target enumeration, NCM stopped responding while the
exact gadget remained configured at the anchored USB path. ARP failed and the
host retained repeated CDC-NCM transmit-queue watchdog timeouts. The
840-second softdog, its 60-second emergency-restart fallback, and the
930-second independent host fallback proof all expired without fastboot.

The p24 subrange is partial/unknown. Do not issue another writer. After
physical fastboot recovery, first capture retained pstore/ramoops and run a
read-only source-versus-destination progress probe. The writable kernel also
still bypasses active-ICC programming and the high-speed UFS gear transition
through the discovery-mode early return; test that separately rather than
assuming it caused this cycle.
