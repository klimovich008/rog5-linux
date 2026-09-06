# Generation 197 watchdog generic failure

Result: **FAIL-CLOSED; consumed; never retry.**

Generation 197 removed the Generation-196 dependency on optional watchdog
sysfs attributes. It still stopped before target SSH and before every p24 write
with:

```text
stage=ufs-ready
state=FAIL
detail=hardware-watchdog
```

Exact slot-A fastboot fallback, host cleanup and durable intent resolution as
`FALLBACK_RETURNED` passed. p24 remains the Generation-195-proven zero/non-ext4
destination.

This was the second non-discriminating failure at the same boundary. The
explicit systematic-debugging workflow and a bounded Opus review were invoked.
Independent binary/DT inspection disproved Opus's two leading guesses: the
module's platform-driver string is `qcom_wdt`, and the staged DT contains one
exact `qcom,kpss-wdt` compatible string. The valid recommendation retained is
to expose every remaining arm predicate in one read-only cycle.

Generation 198 packages the read-only p24 postmortem and emits finite failure
reasons for module metadata, `insmod`, `mdev`, watchdog class count/path,
`/dev/watchdog0`, driver, compatible read/value, foreground process liveness,
and status-record publication. No storage-write command is packaged.
