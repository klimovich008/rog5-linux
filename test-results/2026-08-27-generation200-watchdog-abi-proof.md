# Generation 200 watchdog ABI proof

Result: **PASS; read-only; consumed; never retry.**

Mainline UFS, NCM, runtime and key-only SSH passed. At 7.90 seconds the probe
recorded the watchdog PID absent, no watchdog class/device/driver, no loaded
`qcom_wdt`, and the exact 65-byte BusyBox error:

```text
watchdog: can't open '/dev/watchdog0': No such file or directory
```

A bounded read-only dmesg capture then proved the preceding `insmod` failure:

```text
module qcom_wdt: .gnu.linkonce.this_module section size must match the kernel's built struct module size at run time
```

The rejected module was built from a reconstructed Clang-20/no-BTF config and
had `struct module` section size `0x4c0`. A clean twin external build against
the exact retained g359 output, Clang/LLD 18.1.3, pahole 1.25 and running BTF
ABI hashes identically at `3fcea56e...` and has section size `0x500`.

The false `ARMED` record was a separate shell bug: calling the function under
`if !` suppressed `set -e`, allowing failed predicates to continue. Every
predicate now returns explicitly, and watchdog admission waits through the
first 5-second ping before publishing `ARMED`.

Exact slot-A fastboot returned at 8708 mV and durable intent resolved
`TARGET_ACCEPTED`. No phone-storage write path existed.
