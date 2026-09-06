# Generation 119 pre-storage timing discriminator

Date: 2026-08-24

Result: **CONSUMED; `ncm-address` SELECTED.** Never retry or flash.

The Image, DTB, power/USB modules, stable recovery raw payload, and successful
USB setup behavior are unchanged from Generation 118. Only target failure
observability changes: fixed pre-storage boundaries sleep for distinct 5–85
second intervals before the existing restart2 fastboot return.

The target intentionally stops after the existing power/USB loader. It does
not load UFS, enumerate userdata, run `blockdev`, start SSH, invoke the image
installer, or expose any storage-write path.

Clean-twin target initramfs SHA-256:
`2c8b50fe7e7abe6a4f5cabf417994c1a61f43e5fc04bc16770d56eb3fe841399`.
Signed runtime manifest SHA-256:
`8f4a7343af094b5a2210a7e5e8be6d2e494a6a93f10ee63d6bf540ab43701cb7`.
Generation-119 recovery SHA-256:
`9a3279dd6de28072afba7926b800760dce60bd5e737849b39c48e46af0ebe154`.

The exact host USB journal records recovery departure at
`10:54:24.783508` and slot-A fastboot enumeration at `10:55:41.829522`, an
interval of 77.046014 seconds. Subtracting the independently measured
6.903-second immediate target/restart baseline leaves 70.143 seconds and
selects the fixed 70-second `ncm-address` branch.

Therefore ConfigFS creation, NCM function/link creation, continuously unique
UDC selection, UDC binding, post-bind `mdev`, `usb0` existence, and link-up all
returned success. The exact sealed BusyBox command syntax was independently
replayed in a fresh network namespace and successfully added
`169.254.77.2/30`, so the live failure is runtime state: `usb0` disappeared,
already had an address, had a conflicting address, or rejected the first add.
No target USB product was observed by the host, and no UFS, userdata, SSH,
installer, or storage-write path ran. Fallback and durable intent resolution
passed with battery 8.708 V and `battery-soc-ok=yes`.
