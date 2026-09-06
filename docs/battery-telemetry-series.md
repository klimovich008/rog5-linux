# Headless battery-series oracle

The battery-series oracle defines the sustained read-only evidence required
before the H3 charger and battery gates can run on the corrected minimal
headless candidate.

Status: **hardware-free implementation passes; phone collection remains
HOLD**.

It does not enable charging, write a power-supply property, interpret the
phone's dual-cell topology, establish a safe charging policy, or authorize a
phone boot.

## Record boundary

`collect-headless-battery-series.sh` accepts one explicit physical phase:

- `unplugged`;
- `usb-online`; or
- `wireless-online`.

A live record is fixed at 21 samples separated by 30 seconds, covering 10
minutes. It is bound to:

- collector source SHA-256;
- `headless-ssh-network-root-v3`;
- one boot ID; and
- kernel release `7.1.4-g7a5cef0db479`.

Before the first sample, the collector requires exactly
`qcom-battmgr-bat`, `qcom-battmgr-usb`, and `qcom-battmgr-wls`. Battery
capacity, voltage, current, temperature, and status plus USB/wireless online
state and USB input-current limit must be mode `0444`. Charge-control
thresholds and Type-C control devices must be absent.

Every sample preserves raw Linux power-supply units:

- capacity: percent;
- voltage: microvolts;
- current: microamps;
- temperature: deci-degrees Celsius;
- status: one canonical power-supply status token; and
- USB/wireless online: `0` or `1`.

The collector writes only its record to standard output. It contains no ADB,
fastboot, module loading, sysfs write, storage, reboot, or charger-control
command.

## Host verification

`verify-headless-battery-series.py single` accepts one canonical observation.
The record must be an absolute caller-owned mode-`0600` single-link file in a
caller-owned mode-`0700` directory. It is opened once with `O_NOFOLLOW`,
bounded to 64 KiB, and rejected if its descriptor or pathname identity changes
while read.

`usb-pair` compares one unplugged and one USB-online record from the same
candidate, boot, and kernel. It requires:

- at least one `Discharging` unplugged sample;
- at least one `Charging` or `Full` USB sample;
- no phase-contradictory statuses;
- median currents of at least 25 mA magnitude with opposite signs; and
- median capacities within 10 percentage points.

The verifier reports `positive-discharge` or `positive-charge` from the
observations. It does not assume the driver convention in advance. Ambiguous
or same-direction current is a refusal, not a charging result.

## Offline tests

```sh
python3 scripts/host/test-headless-battery-series.py
```

The test creates a complete sysfs fixture and executes the real collector.
Hostile cases cover identity fields, framing, ordering, ranges, statuses,
phase binding, evidence metadata and replacement, both current-sign
conventions, ambiguous current, boot mismatch, and incomparable capacity.

The future `battery-charging` capability names this test and core CI runs it.
Passing offline means the evidence format and refusal behavior are ready. It
does not mean battery telemetry or charging passed on the corrected candidate.

## Future live sequence

Only after H2 reaches strict SSH with clean rollback:

1. pass the complete minimal-headless runtime verifier for the same boot;
2. collect an unplugged record while the target watchdog remains armed;
3. establish the reviewed physical USB state without writing a charger
   control;
4. collect the USB-online record on the same boot;
5. verify each record and the pair on the host;
6. return through normal fallback and prove cleanup; and
7. record temperature, status, current convention, and any refusal without
   promoting charging control.

That sequence requires a reviewed lifecycle integration and fresh phone
authorization. The present scripts grant neither.
