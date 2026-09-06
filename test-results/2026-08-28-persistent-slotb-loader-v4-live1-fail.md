# Persistent slot-B loader v4 — RAM-only test 1

- Result: consumed and permanently non-retryable. Exact fastboot accepted AVB boot `8cd2c82e0abdcb91390dcbb3042e1ac046385bac797c1aee9af104688b3ff24a` from exact commit `6862df881fa3b048fb5eb81ec740a46ce718fce9`; no phone partition or slot metadata was written.
- Timeline: fastboot detached at 16:00:09.164 UTC. No Loader-v4 USB identity, ACM node, or progress byte appeared. Stock slot-A recovery unauthorized ADB appeared at 16:01:06.765 UTC, 57.601 seconds later. Host kernel USB history confirms no transient loader enumeration.
- Hypothesis result: restoring BusyBox glob expansion did not make the rebuilt wrapper reach observable loader init. The shell fix remains valid, but v4 physically falsified it as the pre-init failure's sufficient cause.
- Architecture conclusion: freeze the per-loader embedded ASUS-kernel rebuild path. Generation 233 repeatedly passed with wrapper kernel `838425a8...`; Loader v1-v4 each changed those kernel bytes to embed a loader initramfs and all failed before loader USB. The smallest discriminating successor keeps the exact proven kernel and changes only the external boot ramdisk.
- Successor composition: deterministic external-loader twins use kernel `838425a8...`, corrected ramdisk `b29757ca...`, raw boot `52df68bf...`, and AVB boot `dc59b4ab...`. This is a fresh RAM-only image, not reuse of a consumed candidate.
- Classification: unresolved pre-init wrapper composition/architecture boundary. Do not attribute it to UFS, storage, charging, target mainline, or host lifecycle.
- Review availability: Claude Opus remained unavailable because local OAuth was expired; OpenCode exposed no OX Alpha model in its actual CLI inventory. No external-review verdict is claimed.
- Next gate: one RAM-only external-loader attempt asks only whether the loader ACM stage channel appears. Never build or boot Loader v5 by embedding another custom initramfs into a newly compiled ASUS kernel.
