# Slot-B external loader failure and canonical-recovery successor

- External-loader result: consumed and permanently non-retryable. Exact fastboot accepted AVB boot `dc59b4ab35ea33fd3393dd387aa5e40969e125616e20aed0b69f42e45f1ca280`; no phone partition or slot metadata was written.
- Timeline: fastboot detached at 16:12:56.421 UTC. No loader USB identity or ACM byte appeared. Stock slot-A recovery returned at 16:13:53.993 UTC, 57.572 seconds later, with no transient USB enumeration.
- Conclusion: using the exact Generation-233 kernel did not make a replacement standalone `/init` observable. Freeze all standalone loader-init variants. The failure follows replacement of the proven canonical recovery platform, not kernel rebuilding alone.
- Architecture correction: retain canonical recovery init for early storage isolation, rollback watchdog, exact DWC3 selection, ACM/NCM, postmortem, and reboot handling. Add one sealed `persistent-slotb-loader-v1` mode that executes a local signed-bundle loader only after recovery USB is ready.
- Source commit: `7e0201ce6f97617b67c659d309c9b0f73c5c6f04`.
- Focused test: PASS in 2.281 seconds. Active tier: PASS in 77.090 seconds. Full local CI: PASS in 460.921 seconds.
- Recovery-loader initramfs twins: `31c4c0750f979783d9184194d4038c595bfda7622c6608d1d33581d8ed0b3a87`, 7,499,505 bytes.
- Exact proven wrapper kernel: `838425a8bc0d49cd92a62df843ca939c3376b879c02faa8bab930d80913c7783`.
- Raw boot twins: `f235719b2041615ef7d8d044538ad6f5da0589e18bbbdcce2385deb4e91a641b`, 58,003,456 bytes.
- AVB boot twins: `5a8b3424ec088b70195788e3c6ffcb221446d11ee895d528ae7a3cd97b8913d1`, 100,663,296 bytes; algorithm NONE, rollback index 0, flags 0.
- Composition: exact header-v3/cmdline; canonical recovery owns USB/watchdog; executor mounts only exact p24 `ro,noload`, verifies the root-owned selector and signed local bundle, deactivates exact Haven watchdog, then kexecs. No raw-write, formatter, partition, SSH, ADB, or host-fetch path is packaged.
- State: unbooted. `boot_b` remains untouched. Next gate is exact-head CI, then one RAM-only cycle asking whether canonical recovery USB appears and which local-loader stage follows.
