# Generation 47 QMP-UFS PHY-creation live result

Status: **consumed successfully; exact Alpine recovered; no phone-storage
access; never retry or flash**.

The one-use claim was entered at 14:28:06 CEST. Fastboot accepted the sealed
RAM-only recovery, recovery ACM/NCM and the bounded signed bundle transfer
passed, and the exact target release `7.1.4-g3a0a28dcbbc3` returned its
post-`insmod` proof at 14:29:06.

The target proved `devm_phy_create()` returned successfully. NCM became stable
in 59.365 seconds and remained exact for the complete 12.261-second control
window. The target explicitly reported `phone_storage_access=none`; UFS core,
platform, and host modules were not loaded, so no block device was enumerated
or accessed.

The fallback profile was restored at 14:29:48, strict signed Alpine identity
passed at 14:29:50 with a maximum reported temperature of 40.8 C, and the
durable intent resolved `FALLBACK_RETURNED` at 14:29:53. Host cleanup and the
Steam loopback socket restoration passed. No pstore record was present, which
remains inconclusive. The next bounded boundary is OF PHY-provider
registration.
