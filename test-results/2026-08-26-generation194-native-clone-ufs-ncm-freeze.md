# Generation 194 native-clone UFS/NCM freeze

Result: **AMBIGUOUS; consumed; never retry.**

Generation 194 reached Linux `7.1.4-g359318de534f`, exact 117-node UFS,
side-port NCM and key-only SSH. Runtime acceptance completed at 7.11 seconds.
The target then emitted only:

```text
ROG5_NATIVE_CLONE_V1 stage=source status=VERIFY
```

During the redundant full SHA-256 read of the 16 GiB sparse source image, SSH
timed out at 20:39:17 and the host recorded repeated `cdc_ncm` transmit-queue
watchdog timeouts beginning at 20:39:32. USB carrier remained present while
packet counters stopped. No `stage=clone status=WRITE` marker was observed,
but transport loss means absence of that marker cannot prove p24 was unchanged.

The target's 900-second shell timer did not execute at its nominal deadline.
The gadget finally disconnected at 20:56:17 and exact slot-A fastboot appeared
at 20:56:21, 19m31s after target enumeration. The durable execution intent
remains `UNKNOWN`. This is a demonstrated R8 rollback defect and a target-side
UFS/NCM liveness failure, not a host NetworkManager or parser failure.

Private evidence is retained at
`/home/deck/.local/state/rog5-generation194-live-20260826-r1`.

The immediate successor is Generation 195, a write-free p24 disposition probe.
The corrected clone path removes the full sparse-file hash and instead proves
the source through an exact read-only loop device, ext4 UUID/block geometry and
the already-accepted sealed-tree verifier. No writable successor may run until
p24 disposition is known and rollback survives the demonstrated failure class.
