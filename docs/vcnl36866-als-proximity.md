# ROG Phone 5 VCNL36866 ambient-light/proximity port

Status: **exact ASUS source/protocol oracle passes; Linux 7.1.4 is
`port-required`; no driver or hardware result exists**.

This is the test-before-port boundary for the first ROG Phone 5 sensor. It
does not claim that a VCNL36866 is currently exposed by Linux 7.1.4, and it
does not authorize a phone boot.

## ASUS 5.4 oracle

The machine-readable contract is
`configs/compatibility/rog5-vcnl36866-v1.json`. It byte-pins 16 retained ASUS
5.4 files and verifies these facts:

- `ZS673KS-EVB-overlay.dts` creates `vcnl36866@60` below
  `qupv3_se0_i2c`; each successor includes its predecessor through
  `ZS673KS-MP5-overlay.dts`, and none overrides the sensor;
- `qupv3_se0_i2c` is the GENI I2C controller at `0x980000`;
- the device address is `0x60`, its interrupt is TLMM GPIO89 and the vendor
  driver requests it active-low, and its named supply is PM8350C L7 at
  3.3 V;
- registers are addressed with one byte and values are transferred as two
  low-byte-first bytes;
- register `0xf6` must return low-byte chip ID `0x62`; and
- raw ambient-light and proximity words are read from `0xf1` and `0xf4`.

The second GPIO172 pinctrl state belongs to the vendor's optional
back-proximity integration and is deliberately outside this first front
VCNL36866 boundary.

## Why this is a real port

Accepted Linux 7.1.4 contains the generic `vcnl4000` IIO driver and binding,
but neither recognizes VCNL36866. The VCNL36866 register map is materially
different: its identity and data registers are in the `0xf1`–`0xf6` range.
The contract therefore refuses both a partial `vcnl36866` addition and any
claim that `vishay,vcnl4040` is an adequate compatible.

The next implementation must add a dedicated IIO driver, Kconfig/Makefile
integration, a binding, and one ROG5 overlay. The frozen candidate contract
requires:

- exact chip-ID validation and little-endian 16-bit regmap access;
- only `IIO_LIGHT` and `IIO_PROXIMITY` raw channels;
- runtime-PM resume/autosuspend around reads, with explicit regulator
  enable/disable callbacks, to bound idle drain;
- a single `vdd` rail and the exact `0x980000`/`0x60`/GPIO89 topology;
- no `write_raw`, ad-hoc writable sysfs, debugfs, misc/input compatibility
  layer, or reused vendor `qcom,vcnl36866` compatible.

The candidate may internally write the configuration needed to take a
measurement. “Read-only” means that userspace receives only mode-`0444` raw
data and no calibration, threshold, interrupt, or register-control surface in
this first tier.

GPIO89 remains part of the source oracle, but the first polling/raw-data
candidate deliberately does not request the interrupt or expose IIO events.
Interrupt delivery, thresholds, wake behavior, and their power cost form a
separate later gate.

## Runtime boundary

The prepared runtime record remains `observed-not-hardware-accepted`. It
requires exact controller/address/compatible/driver/IIO identity, bounded
16-bit raw values, mode-`0444` `in_illuminance_raw` and
`in_proximity_raw`, no control surfaces, no phone-storage access, and
`authority=none`. Physical plausibility, calibration, interrupts,
suspend/resume, and power impact are later independent gates.

## Verification

Run the focused hostile suite:

```sh
python3 scripts/host/test-vcnl36866-port-contract.py
```

When the canonical retained trees are present, the same command verifies the
real ASUS 5.4 files and exact clean Linux 7.1.4 commit/tree. A clean GitHub
checkout runs all synthetic semantic and hostile cases and intentionally
skips only those retained-tree integrations.

See the
[offline result](../test-results/2026-08-09-vcnl36866-source-port-contract-offline.md).
