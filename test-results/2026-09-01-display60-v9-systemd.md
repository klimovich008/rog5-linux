# Display60 V9 systemd observer failure

Result: **target handoff PASS; display evidence unavailable; fallback PASS**.

- Source exitrd entered the exact target. Boot
  `17b55df1-3c5e-46f6-aaef-70847871edd9` reached final read-only storage proof
  and `switch-root PASS` over the prestarted stage collector.
- The observer was attached to `sysinit.target` before `basic.target` and
  persistent state, but emitted no record before the 180-second deadline.
- The unchanged target remained until the late rollback boundary, then fresh
  V11 `87070bfc-6b14-4dcc-87aa-5c7d9034d059` returned with strict SSH,
  p24 read-only, battery Good at 8.559 V and 30.1 C.
- V9 is irreversibly consumed. V8 was obsolete and never issued. No phone
  storage write path was added or exercised.

The repeated V7/V9 result retires post-switch observation. The replacement runs
the signed reporter in initramfs after final read-only verification, before
`switch_root`, and directly reboots after sending. The failed systemd unit was
deleted from the active composition.
