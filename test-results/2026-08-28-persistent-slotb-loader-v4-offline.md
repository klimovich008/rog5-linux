# Persistent slot-B loader v4 — offline checkpoint

- Question: with exact runtime glob expansion restored, does the Loader ACM stage channel appear and identify the first loader boundary?
- Source commit: `e487779a784c74aa147e303ef8c9b36de84d5ee1`.
- Delta: remove only loader `set -f`; fixed-path UDC and storage globs now execute under the same BusyBox `ash` semantics used by the target. Peripheral-mode, exact-UDC, storage, signature, watchdog, kexec, fallback, and slot policies are otherwise unchanged.
- Regression: corrected fail-first status was 1 on v3. It explicitly proves `single_expected_udc()` fails with glob expansion disabled and passes after expansion is restored, then runs zero/multiple/wrong/renamed/changing UDC fixtures.
- Loader initramfs clean twins: `b29757ca83b7987b108efed069b2bf969d3051ef3ddf01cb0be1a8c756304847`, 7,604,179 bytes.
- ASUS wrapper clean twins: Image `e61a2b675477021457ccd8c5e52a414bc966730725d4d5e50ea610d812c4e266`; raw boot `e8d739e75b2255626bd9519dc76d630e3577914b54033b295f989366ea104ee0`, 58,109,952 bytes; AVB boot `8cd2c82e0abdcb91390dcbb3042e1ac046385bac797c1aee9af104688b3ff24a`, 100,663,296 bytes.
- Wrapper cache: input `17ca79fdb4ff89b1bc593a8508e632c723b565e2dd19fd8f989829c5549c6489`; entry `71c6ea6cb06a8f56d1e996846fee036624b1925d32297a9b27eb121d4fe20a25`.
- Focused test: PASS in 4.503 seconds. Active tier: PASS in 71.775 seconds. Full local CI: PASS in 441.079 seconds.
- State: v4 is unbooted. Loaders v1-v3 are permanently consumed. `boot_b` remains untouched.
- Next gate: exact-head GitHub CI on the final commit, then one fresh RAM-only v4 execution record from true fastboot.
