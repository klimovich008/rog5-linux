# AMS678 60 Hz display offline checkpoint

Result: **PASS offline; hardware not yet tested**.

## Scope

- Linux release: `7.1.4-rog5-display60-v1`.
- One Samsung AMS678 ER2 1080x2448 command-mode DSC mode at 60 Hz.
- Pixelworks Iris6 is used only in verified analog bypass; no PQ command blob.
- DSI0, 7 nm PHY, MDSS/DPU, PM8350C L12/L13, and four reviewed GPIOs.
- Existing tty1 status renderer: time, active Wi-Fi interface/IP, and battery.
- No desktop, compositor, GPU acceleration, higher refresh rate, or phone write.

## Exact artifacts

- Kernel `Image.gz` SHA-256:
  `52f77ba83e9c70f58195f6ad5a4100b4ec78ace9270697f4d83f5f53eec97637`.
- Kernel config SHA-256:
  `fc2200306d2db811d7f0102b9f0db9e3f3ed1ca52e466eaea97bc038070d8125`.
- `Module.symvers` SHA-256:
  `f8505a2439e0b822a407af036ff9d8c87db8d9b322acaa00440b97781123e313`.
- Display DTB SHA-256:
  `1806104ab0efa1a80cc1c55f81e236f8f9f8cde055c6cb2dad3cea303869ba96`.
- Base Wi-Fi DTB SHA-256:
  `8b1250cefd69870662edb9131190f005f492b4c93c192ee7e2b89b9a121f22da`.

The kernel embeds and installs modules under exactly
`7.1.4-rog5-display60-v1`; automatic Git-derived release naming is disabled.

## Validation and timing

- Standalone ARM64 panel object build: 3.080 seconds.
- Binding check: PASS; warm recheck 0.683 seconds.
- Focused panel contract: PASS in 0.451 seconds.
- Exact deterministic DT delta and hostile mutations: PASS in 0.475 seconds.
- Status-screen userspace: PASS in 0.243 seconds.
- Kernel compile phases: 705.634 + 1,973 + 210.49 = 2,889.124 seconds.
- Final private build/module/DT checkpoint size: approximately 6.3 GiB.

No candidate, claim, signing operation, phone contact, or persistent storage
change occurred during this checkpoint.
