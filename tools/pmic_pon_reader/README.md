# Fixed-bank read-only PMIC PON snapshot

This optional inspection module reads only the PMK8350 PON-log SDAM at
`/soc@0/spmi@c440000/pmic@0/nvram@7400` on the ROG Phone 5. The bank and
offsets come from the retained ASUS `lahaina-pmic-overlay.dtsi`, `pmk8350.dtsi`
and `drivers/soc/qcom/pmic-pon-log.c`.

It has no address parameter or write API. It resolves the fixed OF path, then
requires exactly one matching NVMEM provider. Do not compare `np->full_name`
with an absolute path: in the current kernel that member stores the local FDT
node name. The reader compares the resolved node identity instead.

Build with the exact kernel/module kit. After exact-device and matching-module
verification, load it and privately capture:

```sh
cat /sys/kernel/debug/rog5-pmic-pon-readonly/snapshot > PRIVATE_SNAPSHOT
rmmod rog5_pmic_pon_readonly
python3 tools/pmic_pon_reader/decode.py PRIVATE_SNAPSHOT
```

The snapshot is root-readable only and is captured once at module load. It
contains a versioned header, two equal push-pointer reads, and 117 FIFO bytes.
The reader rejects a moving or invalid pointer. It does not change the existing
SDAM provider, its size, or any PMIC register. Kernel NVMEM reads still go
through the provider's validated read callback; sysfs's advertised 128-byte size
does not expose the complete peripheral-relative FIFO at 0x4b..0xbf.

The decoder preserves unknown records and labels empty data inconclusive.
History has no target boot ID. Correlate before/after snapshots with observed
device resets; do not attribute an old event to a candidate solely by proximity,
or treat a missing fault record as proof of no crash.
