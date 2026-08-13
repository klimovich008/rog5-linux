# Generation 48 QMP-UFS PHY-provider live result

Status: **consumed successfully; exact Alpine recovered; no phone-storage
access; never retry or flash**.

The one-use claim was entered at 15:06:54 CEST. Fastboot accepted the sealed
RAM-only recovery, recovery ACM/NCM and the signed bundle transfer passed, and
the exact target release `7.1.4-gae717d919f87` returned its target-originated
proof at 15:07:55.

The target proved that QMP-UFS PHY drvdata assignment and OF PHY-provider
publication returned successfully. NCM became stable in 59.575 seconds and
remained exact for the complete 12.024-second control window. UFS core,
platform, and host modules were not loaded, so no block device was enumerated
or accessed.

The fallback profile was restored at 15:08:37, strict signed Alpine identity
passed at 15:08:39 with a maximum reported temperature of 45.8 C, and the
durable intent resolved `FALLBACK_RETURNED` at 15:08:42. Host cleanup and the
Steam loopback socket restoration passed. No pstore record was present, which
remains inconclusive. The consumed claim record SHA-256 is
`a9937e9b447b41d8833038a05f3b4327834026b96e61ea5c9ccdee10776f2e14`.
