# Headless battery-series oracle: offline result

Date: 2026-07-31

Outcome: **PASS for the hardware-free sustained telemetry contract; phone
collection and charging acceptance remain HOLD**.

No phone, fastboot/ADB transport, PolicyKit action, NFS/firewall service,
credential, signing key, charger control, sysfs/device write, reboot, or
phone-storage access was used.

## Implemented

The future H3 `battery-charging` capability now names one hardware-free CI
gate. The target collector:

1. fails before inspection without an explicit read-only collection guard;
2. accepts only `unplugged`, `usb-online`, or `wireless-online`;
3. fixes live collection at 21 samples and 30-second intervals;
4. binds its source hash, deployment candidate, boot ID, and kernel release;
5. requires exactly the three SM8350 battery-manager power supplies;
6. requires mode-`0444` battery telemetry, online state, and USB input-current
   limit;
7. refuses charge-control thresholds and Type-C control devices;
8. validates raw units without interpreting charging safety; and
9. emits one canonical `OBSERVED` record to standard output.

The host verifier binds record metadata and pathname identity, validates every
header and sample, and compares same-boot unplugged/USB observations. It
requires distinguishable opposite-sign median current but derives either
possible driver sign convention instead of assuming one.

## Verification

Focused results:

```text
test-headless-battery-series.py: 11 passed
test-core-compatibility-oracle.py: 34 passed
test-core-source-dtb-contract.py: 53 tests, 1 optional skip
verify-core-compatibility-oracle.py --metadata-only: PASS
Python and shell syntax: PASS
git diff --check: PASS
test-repository-linux.sh ci: PASS
```

The source/DT suite used the repository's pinned
`build/ci-host-tools/dtc`. A direct invocation without that path failed only
because no system `dtc` is installed; rerunning through the CI tool path
passed all 53 tests. The complete repository Linux CI then passed, including
QEMU, recovery protocol and state, rollback, network, bundle, and battery
gates.

## Independent review

A bounded, safe-mode, tool-free, nonpersistent Claude Opus review received the
complete collector and verifier sources. It returned `NO_BLOCKERS`.

## Limits

This result does not prove:

- telemetry on the corrected deployment candidate;
- charger detection or current direction on real hardware;
- the dual-cell topology;
- battery thermal safety or cutoff policy;
- sustained idle/load power;
- charging control; or
- rollback after a battery-series collection.

Those remain H3 hardware gates after the minimal H2 strict-SSH path passes.
No live, credential, signing, boot, flash, wipe, storage-write, or retry
authority is granted.
