# Selector-v2 loader repeated RAM-only PASS

Result: **two RAM-only passes; no selector or partition write**.

- Reproduced selector-v2 loader-initramfs twins in 2.070 seconds, SHA-256
  `8adfa1642a7f7281efb1e5603b6505ae72c5c7f75944f447fc197d159ebb7e2e`.
- Repacked the retained ASUS wrapper without rebuilding its kernel. Raw twins:
  `b82fc040cf87b07127dc233acea3af068ad6146b260a6216a7ef4c1996585015`.
- First AVB `ca2393cf…` and byte-distinct repeat AVB `eadfc39f…` each booted
  through `ROG5 recovery` into the unchanged selector-v1 V11 bundle.
- Fresh strict-SSH V11 boots: `e15d82d4-451a-4cce-a67f-768fed9de47e` and
  `04ff021c-123c-4e5a-9c5a-b04bfbe24514`.
- Both passes retained selector-v1, V11 manifest `a684bad1…`, p24 read-only,
  exact 117:2 storage scope, Good battery, and safe temperature.

The installed boot_b remains the older selector-v1 loader. The new loader is
not flashed. Next build the signed Wi-Fi primary and selector v2, then RAM-test
their full try-once/fallback decision before any persistent loader transaction.
