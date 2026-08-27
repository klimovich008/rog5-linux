# Generation 202 inherited watchdog proof

Result: **FAIL with decisive evidence; consumed; never retry.**

The diagnostic driver only mapped and read EN, STS, BARK, BITE and clock rate.
It did not register a watchdog, request an IRQ or write MMIO. Nevertheless,
target NCM disconnected about 12 seconds after enumeration and exact stock
slot-A recovery appeared about 19 seconds later. No target stage frame or
phone-storage write occurred; durable intent resolved `FALLBACK_RETURNED`.

Generation 200 stayed alive when the active watchdog module did not load, while
Generation 201 and this no-write observer both lost the target at the same
short boundary. Therefore an ASUS watchdog is already armed before mainline
reaches the observer and expires while power/UFS/SSH startup runs.

The next read-only successor moves observer load and a compact register detail
onto the existing repeated NCM stage channel immediately after carrier, before
power, UFS and SSH: `wdt-r<rate>-e<EN>-s<STS>-b<BARK>-i<BITE>`.
