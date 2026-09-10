# Persistent slot-B loader v3 — offline checkpoint

- Question: does the corrected ASUS-wrapper USB bring-up expose the Loader ACM stage channel?
- Source commit: `45c075835a6d88f2b39a6531e969f3e7aa2f3fde`.
- Delta: set exact `a600000.ssusb` peripheral mode before ConfigFS, wait boundedly for one exact `a600000.dwc3`, prove two stable snapshots, bind, and verify the bound/current UDC. No storage, bundle, watchdog, kexec, fallback, or slot policy changed.
- Regression: the pre-fix test exited 1. The corrected test passes exact ordering plus zero/multiple/wrong/renamed/changing UDC fixtures.
- Loader initramfs clean twins: `d9290d14e030b1bc476b1948a090154ededda5f31b39fe3c5d0d01574803b061`, 7,604,181 bytes.
- ASUS wrapper clean twins: Image `5c1dd3ece9323c5ce34a2f978ef974166606e403207f498ec898871e1707d11e`; raw boot `fc859f891712de6074a88a18d5ba0a173ce0b28da5678a3fb2c81b617473bf47`, 58,109,952 bytes; AVB boot `806933a8fb98b118127fc72d703620e38e41bd94da56257df362c8a425a1a313`, 100,663,296 bytes.
- Wrapper cache: input `ea167b4f4d412fd8bb4a4c76d52c6aadba51cc441a0f0457178447cedac28b8f`; entry `7c352efa12359298f037805776325d5d61b66c62a9f9ace58447d07a78346820`.
- Focused test: PASS in 4.768 seconds. Active tier: PASS in 74.038 seconds. Full local CI: PASS in 445.807 seconds.
- State: v3 is unbooted and not yet live-eligible. Loader v2 is permanently consumed. `boot_b` remains untouched.
- Next gate: exact-head GitHub CI on the final commit, then one fresh RAM-only v3 execution record from true fastboot.
