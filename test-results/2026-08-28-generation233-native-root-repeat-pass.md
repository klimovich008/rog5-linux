# Generation 233 native-root repeat

- Result: consumed successfully; `TARGET_ACCEPTED`; exact slot-A fastboot returned in 249.912 seconds.
- Passed unchanged baseline: native p24, root verification, OverlayFS, switch-root, stable NCM, first-attempt Ed25519 SSH in 0.178 seconds, UFS, full systemd readiness, and zero failed units.
- Artifact identity: target Image, DTB, initramfs, and raw ASUS recovery were unchanged from Generation 232; only signed bundle identity and AVB generation changed.
- Next: freeze this repeated-pass baseline and validate a RAM-only local-bundle slot-B loader before any boot_b write.
