# Generation 199 watchdog-lifetime failure

Result: **prewrite failure; consumed; never retry.**

Generation 199 reached mainline UFS, NCM, runtime and key-only SSH in 7.86
seconds. The APSS watchdog helper had passed its 200 ms init check, but its PID
was gone when clone admission ran. The clone emitted only:

```text
ROG5_NATIVE_CLONE_V1 stage=terminal status=FAIL reason=hardware-watchdog
```

No source-verification marker or p24 write window appeared. Exact slot-A
fastboot, cleanup and durable `FALLBACK_RETURNED` resolution passed at 8711 mV.

The next discriminating experiment is read-only: retain and return the bounded
`/run/rog5-hardware-watchdog.log`, process state, driver identity and watchdog
status after the first 5-second ping. Do not issue another clone until that
evidence explains the process exit.
