# ROG Phone 5 read-only dual-cell telemetry

Status: **hardware-free source, DT, fixture, and AArch64 object checks pass;
phone execution remains HOLD**.

This increment exposes the two pack-cell voltages needed to interpret the
ROG Phone 5's aggregate battery voltage. It does not enable charging, assess
battery health, set a safety threshold, authorize a phone boot, or produce a
release candidate.

## Protocol boundary

The retained ASUS 5.4 driver is used only as a wire-protocol oracle. Its
`OEM_GET_Cell_Voltage_REQ` request uses PMIC GLINK owner `32782`, opcode
`0x3005`, and a header-only request. The response is exactly one PMIC GLINK
header followed by two little-endian 16-bit millivolt values.

The upstream candidate does not copy the vendor driver's class, debugfs,
GPIO, file, display, or charging-control machinery. Patch
`0018-power-supply-qcom-battmgr-add-rog5-cell-voltage.patch` changes only
`drivers/power/supply/qcom_battmgr.c` and:

- activates only when the parent PMIC GLINK device carries
  `asus,cell-voltage-readonly` and uses the SM8350 protocol;
- registers one separate OEM-owner client while retaining the existing
  owner-`32778` battery manager;
- serializes the request with qcom_battmgr's existing firmware mutex;
- validates exact response length, owner, type, and opcode before decoding;
- revalidates the PMIC service generation and refuses further reads after a
  response timeout until the next service transition, preventing a late
  response from being mistaken for a retry;
- keeps PMIC GLINK callbacks non-sleeping; and
- adds only mode-`0444` `cell_voltages` on `qcom-battmgr-bat`.

The sysfs value is one canonical line:

```text
cell1_voltage_mv=4120 cell2_voltage_mv=4135
```

## DT boundary

`sm8350-asus-rog-phone5-dual-cell-readonly.dtso` adds only the empty
`asus,cell-voltage-readonly` property to `/pmic-glink`. Its verifier pins the
current ADSP + battery-only PMIC GLINK telemetry base at 102,938 bytes and
SHA-256
`3f4305d7fbbd2c74d15c1011bb8a2e8e24b3a5228f31ed86281917d16cf18f11`.
It refuses every other property or node change.

The historical battery telemetry overlay and its live evidence are not
modified. The older convenience builder also retains its historical power-key
expectation; the new hostile test constructs the current pinned telemetry base
directly instead of rewriting that evidence boundary.

## Future read-only observation

`collect-dual-cell-readonly-snapshot.sh` is prepared for a separately reviewed
live candidate. It requires the exact three qcom_battmgr supplies, ordinary
mode-`0444` aggregate and cell-voltage files, and no charging-threshold
surface. It records both cells, their sum, aggregate delta, and imbalance.

The collector accepts cell values from 2,500 through 5,000 mV and requires
the cell sum to be within 300,000 uV of aggregate `voltage_now`. Those are
protocol/topology sanity bounds only. The terminal result is deliberately
`OBSERVED_NOT_HEALTH_ASSESSMENT`; no imbalance value is classified as safe or
unsafe.

## Verification

Run the hardware-free gates with:

```sh
SOURCE_DIR="$PWD/build/linux-stable-v7.1.4-source" \
  scripts/device/test-qcom-battmgr-asus-cell-voltage-patch.sh
scripts/device/test-dual-cell-readonly-candidate-dtb.sh
python3 scripts/host/test-dual-cell-readonly-snapshot.py
```

Hostile fixtures cover wrong owner/opcode/property, non-exact response length,
a writable attribute, private firmware locking, extra patch files, DT control
properties and topology changes, malformed sysfs framing, linked/writable
properties, changed supply inventory, charging controls, range violations,
and aggregate mismatch.

The patched driver compiles as an AArch64 relocatable object with the pinned
Linux 7.1.4 config and qualified offline builder. A release remains gated on
two clean, complete, byte-identical kernel builds through the normal candidate
issuance path. Partial object compilation is not a linked module or boot
authority.
