# Generation 195 native p24 postmortem pass

Result: **PASS; consumed; never retry.**

Generation 195 reached Linux `7.1.4-g359318de534f`, exact 117-node UFS,
side-port NCM and key-only SSH. Runtime acceptance completed at 6.80 seconds.
The write-free target reported:

```text
ROG5_NATIVE_POSTMORTEM_V1 stage=inspect status=READ
ROG5_NATIVE_POSTMORTEM_V1 stage=terminal status=PASS disposition=non-ext4 prefix_sha256=bb9f8df61474d25e71fa00722318cd387396ca1736605e1248821cc0de3d3af8
```

That prefix hash exactly equals 4 MiB of zero bytes. Generation 194 therefore
did not establish an ext4 superblock or allocated-block clone header on p24.
All UFS nodes remained read-only and no repair or filesystem write command was
present.

The target returned to exact slot-A fastboot and the canonical fallback record
passed. A redundant second live sysfs-path check raced the already-proven
fastboot identity; that host-only check was removed and the durable intent was
resolved as `TARGET_ACCEPTED` without another boot.

Private evidence is retained at
`/home/deck/.local/state/rog5-generation195-live-20260826-r1`.

Generation 196 is the corrected writable successor. It validates the source
through a read-only loop device and the accepted sealed-tree verifier, arms the
stock-grounded Qualcomm APSS watchdog for a 30-second bite, and writes only
p24 using allocated-block restore before UUID, grow, seal and read-only relock.
