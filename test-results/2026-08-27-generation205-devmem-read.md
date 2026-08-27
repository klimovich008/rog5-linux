# Generation 205 arm64 `/dev/mem` read classification

Result: **FAIL-CLOSED; consumed; never retry.**

The target returned exact `power-usb/FAIL/watchdog-mmio-en`, then exact slot-A
fastboot and durable `FALLBACK_RETURNED`. No power, UFS, or storage path ran.

The exact Linux 7.1 arm64 source proves the root cause: `/dev/mem` `read()`
calls `valid_phys_addr_range()`, which accepts only mapped memblock RAM. The
watchdog page at `0x17c10000` is MMIO, so the read returns `EFAULT` before any
register access. `CONFIG_STRICT_DEVMEM` and the register address remain
unproven as causes.

The successor replaces only that invalid userspace access method with a
static, no-argument, read-only mmap helper. It distinguishes open, mmap and
bus-fault failures and retains the exact final watchdog tuple.
