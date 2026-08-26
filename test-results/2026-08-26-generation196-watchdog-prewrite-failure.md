# Generation 196 watchdog prewrite failure

Result: **FAIL-CLOSED; consumed; never retry.**

Generation 196 completed signed recovery handoff and exact 117-node UFS, then
returned the terminal target stage:

```text
stage=ufs-ready
state=FAIL
detail=hardware-watchdog
```

No target SSH host key was published and the p24 clone command was never
reachable. Exact slot-A fastboot fallback and host cleanup passed; the durable
intent resolved as `FALLBACK_RETURNED`.

The exact built config contains `CONFIG_QCOM_WDT=m` and
`CONFIG_WATCHDOG_SYSFS=n`. Linux 7.1 `watchdog_dev.c` defines the `timeout`
attribute only under `CONFIG_WATCHDOG_SYSFS`. The helper had already loaded the
stock-address-grounded module, created `/dev/watchdog0` and started BusyBox
`watchdog -F -T 30 -t 5`; its subsequent read of the optional timeout sysfs
attribute was the incompatible predicate.

Generation 197 removes only that sysfs read. Exact driver, compatible, device,
foreground watchdog process, 30-second timeout request and five-second ping
remain required before the clone can become reachable.
