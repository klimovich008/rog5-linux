# Buttons and green status indicator — offline

Date: 2026-07-30

Result: **PASS hardware-free; deterministic candidate packaged; hardware
acceptance unproven; live authority=none**

## Outcome

The accepted corrected headless DTB now has one exact, additive candidate for
power, volume-down, volume-up, and a low-power headless status indication.
The candidate enables only the stock-evidenced PMK8350 PON inputs, PM8350
GPIO6 volume-up path, and PM8350C LPG green channel 2. The LED is off by
default and has no automatic trigger.

Stock mapping evidence is the runtime DTB at SHA-256
`1e28208664a9084a4ffde9806206c4c9b86edb4ca4579844938b07187da98962`:
its tri-LED node maps vendor PWM indices 0/1/2 to red/green/blue. Upstream LPG
LED child numbering is one-based, which maps vendor green index 1 to
`led@2`/`reg = <2>`. Physical color remains live-pending.

The exact verifier output is:

```text
base_sha256=86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46
added_nodes=4
changed_existing_properties=7
PASS exact buttons and green-indicator DTB delta
```

Recorded artifact metadata is:

```text
candidate_size=103554
candidate_sha256=57216474b4c8979161d964cef2ff3fe5d61500af3cef34598ee06e03e91f967d
status=offline-candidate-live-pending
authority=none
```

Two independent builds compared byte-for-byte equal.

## Kernel and module result

The capability verifier passed against:

```text
source_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
config_sha256=68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f
modules_sha256=5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9
modules_size=300439504
buttons=power,volume-down,volume-up
indicator=pm8350c-lpg-channel-2-green-default-off
```

The accepted config has built-in OF, GPIOLIB, the Qualcomm SPMI PMIC arbiter,
SPMI, GPIO keys, and PM8941/PMK8350 power-key support. Qualcomm LPG is modular
and its exact regular `.ko` is present in the accepted module archive.

## Hostile coverage

The DT suite rejects:

- any changed base size/hash, board property, unrelated node, or missing
  approved node;
- wrong PON status or key code;
- a disabled SPMI/PMIC/PON/GPIO parent or malformed GPIO/interrupt provider;
- resin wake behavior not established by stock evidence;
- wrong PM8350 GPIO number, polarity, debounce, pull-up, or wake property;
- wrong LPG channel/color/function/default state;
- an automatic heartbeat trigger;
- duplicate/invalid phandles and wrong `pinctrl-0`/`gpios` references;
- linked and truncated input.

The source/config/module suite rejects:

- the wrong source commit or tracked source modifications;
- missing driver, Kconfig, Makefile, binding, DTSI, wake, direct-brightness,
  or default-off source markers;
- missing/wrong final Kconfig values and duplicate config symbols;
- altered or linked config input; and
- a module archive without the exact regular Qualcomm LPG module.

Both focused suites are part of the `ci` and `quick` repository tiers.

## Remaining hardware gate

No physical press, LED write, suspend/wake cycle, boot, reboot, or phone
connection occurred. The next attended RAM-only gate must bind real press and
release events, one default-off LED class device, a bounded userspace health
blink, unchanged SSH/storage/rollback state, clean logs, and exact fallback
return. A passing offline contract cannot promote runtime acceptance.

See the [implementation and runtime contract](../docs/buttons-indicator.md).
