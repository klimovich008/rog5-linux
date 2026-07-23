# USB recovery-contract verification — 2026-07-23

Result: **PASS** for read-only connector discovery and the disabled offline DTS contract. This is not permission to boot the mainline DTB.

## Live baseline

The known-good `5.4.210-qgki-perf` system was queried over its existing private USB SSH link. No file, setting, partition, or runtime state was changed.

- `usb_1` was configured in device mode at high speed.
- `usb_2` and the additional vendor UDC were unattached.
- The only exposed USB role switch belonged to `usb_1` and reported device mode.

## Offline vendor-tree comparison

The allowlisted inspector confirmed:

- `usb_1` uses DWC3 at `0x0a600000`, the primary HS PHY, the primary USB3/DisplayPort QMP PHY, and a PMIC UCSI endpoint.
- `usb_2` uses DWC3 at `0x0a800000`, the secondary HS and USB3-only PHYs, a board redriver rail, and separate switching controls.
- USB1 HS supplies resolve to PM8350 L5, PM8350C L1, and PM8350 L2.
- USB1 QMP supplies resolve to PM8350 L6 and PM8350 L1.
- The voltage ranges match the pinned upstream SM8350 board representation.

The ASUS manual states that only the left-side Type-C connector supports DisplayPort. Combined with the primary combo-PHY and UCSI topology, this maps `usb_1` to the left-side connector and leaves `usb_2` outside the first recovery tier.

## Compile gate

The ASUS DTB passes preprocessing, compilation, round-trip parsing, artifact hashing, exact memory-reservation checks, and exact UFS/USB checks. The source and compiled DTB keep UFS, USB1, both USB1 PHYs, and USB2 disabled. DWC3 is predeclared as peripheral-only for the eventual recovery gadget.

Artifact: `dist/linux-7.1.4/sm8350-asus-rog-phone5.dtb`, 102,627 bytes, SHA-256 `3e4c6ecdd87e2a07819dd7c5a4e231c38140079be160a46fcda585130b3471fa`.
