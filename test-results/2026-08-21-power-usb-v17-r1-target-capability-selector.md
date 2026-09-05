# Power/USB v17 incident: target initramfs selected one candidate instead of the capability

ID/date: power-usb-v17 / 2026-08-21
Primary question: do the restored PAS memory exclusions let ADSP start and expose side-port power/UCSI telemetry?
Earliest failed stage: post-SSH power/USB probe invocation, before ADSP.
Observed evidence: NCM/NFS, systemd, strict key-only SSH, 29-zone runtime acceptance, and rollback passed; `/run/initramfs/sbin/rog5-early-charging-probe` was absent.
Root cause: proven R1 identity-propagation defect. The reused target initramfs embedded V16 as the only power/USB selector. V17 therefore entered ordinary network-root mode, skipped the deferred module policy, and did not retain the probe/firmware in the exitrd.
Was the candidate consumed?: yes. Phone storage modified: no.
Regression: target selection now validates the stable `headless-power-usb-observer-vN` capability family with canonical positive decimal generations. Tests prove predecessor and successor IDs both select mode 2, while empty, zero, zero-padded, and non-decimal lookalikes fail. The generated target lock contains no active candidate identity.
Successor: V18 rebuilds only the target initramfs. Kernel, DTB, firmware bytes, recovery, and probe are otherwise unchanged.
