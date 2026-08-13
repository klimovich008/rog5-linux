# Generation 51 read-only local-root stage result

Status: **consumed; exact Alpine fallback returned; never retry or flash**.

The sole RAM-only Generation 51 cycle transferred all 45,806,987 bytes of the
exact signed bundle and executed Linux `7.1.4-gae717d919f87`. The target
reported one boot identity and these latest completed entry boundaries:

| Host monotonic time | Sequence | Stage |
| ---: | ---: | --- |
| 134699.216976 | 2 | `ufs-ready` |
| 134705.248868 | 6 | `userdata-resolved` |
| 134707.262092 | 8 | `userdata-mount` |
| 134709.272724 | 10 | `root-verify` |

This proves the four-module UFS path, exact 116-node physical read-only lock,
dynamic userdata identity, and the sole `ro,noload` block-backed mount passed.
No later stage appeared. The target NCM gadget remained present and reachable,
so the earliest demonstrated blocker is the complete 181,242-entry,
5,594,331,332-byte root rehash. It did not finish within the target's
600-second rollback window.

The watchdog returned the exact Alpine fallback with a new boot ID. Strict
fallback identity, host-profile restoration, intent resolution as
`FALLBACK_RETURNED`, and host cleanup passed. No persistent phone write
occurred. Pstore was unavailable, which remains inconclusive. PMIC evidence
reported `PS_HOLD`, `HARD_RESET`, and no watchdog marker; that does not override
the direct stage and USB evidence.

Exact identities:

- repository checkpoint used for the live cycle: `53ce7a63bb4ad4090fe95ae0cebb646321e17c4c`
- target boot ID: `5fe8ac90-79c4-438b-87c0-1ea4f9227dc6`
- fallback boot ID: `9fba7baf-f87f-4449-8cda-54f211682d70`
- target manifest SHA-256: `53afa65bb7134e7d5acccc2126aa8764fd3918c7cab02c61417f4be1572aad27`
- temporary recovery SHA-256: `3fbcf296b054460a4a5a48092e55e4df080c6e308430177cf999d42ff6ef39cc`
- retained private evidence: `rog5-generation51-live-20260813.A39YFp0p`

Generation 52 changes only the boot-time root admission cost; it preserves the
same read-only mount, volatile OverlayFS, key-only SSH, and rollback path.
