# Buttons and headless status indicator

## State

The first Linux 7.1.4 candidate is **offline-ready and live-pending**. It has
no boot, signing, flashing, or runtime authority. It preserves the accepted
headless DTB and adds only three physical buttons plus one default-off green
status LED.

This milestone does not claim that a physical press reaches Linux, that the
LED is electrically correct, or that either input survives suspend. Those are
separate attended runtime gates.

## Evidence-backed mapping

The stock runtime tree and upstream Linux describe the same hardware:

| Control | Linux interface | Stock mapping | Candidate policy |
|---|---|---|---|
| power | `pmic_pwrkey`, `KEY_POWER` 116 | PMK8350 PON power-key IRQ | enable; upstream makes it a wake source by default |
| volume down | `pmic_resin`, `KEY_VOLUMEDOWN` 114 | PMK8350 PON resin IRQ | enable; do not add wake until suspend testing |
| volume up | `gpio-keys`, `KEY_VOLUMEUP` 115 | PM8350 GPIO6, active low, pull-up, VIN/power-source 1, 15 ms debounce and vendor wake flag | enable with standard `wakeup-source`; validate wake/power later |
| alive indicator | LED class, green status LED | PM8350C tri-LED green channel | LPG channel 2; default off; no automatic trigger |

The candidate intentionally exposes only green. Red/blue grouping, LPG
patterns, haptics, display feedback, and suspend behavior remain outside this
delta.

The stock runtime DTB at SHA-256
`1e28208664a9084a4ffde9806206c4c9b86edb4ca4579844938b07187da98962`
maps vendor PWM indices 0/1/2 to red/green/blue. The upstream LPG LED binding
uses one-based `reg` channel numbers, so vendor green index 1 becomes upstream
`led@2`/`reg = <2>`. The physical color remains part of the attended gate.

## Exact DT contract

The accepted base is
`artifacts/network-root-v3/sm8350-asus-rog-phone5-recovery.dtb`:

```text
size=102870
sha256=86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46
```

The overlay adds exactly four nodes:

- `/gpio-keys`;
- `/gpio-keys/key-volume-up`;
- the PM8350 GPIO6 pinctrl state; and
- PM8350C LPG `led@2`.

It changes exactly seven existing properties: the overlay symbol, power-key
status, resin key code/status, and the PWM child-address/status properties.
Every other RAM, CPU, storage, USB, GPU, display, remote-processor, thermal,
and board-identity property remains byte-semantically unchanged.

Build and verify:

```sh
scripts/device/build-buttons-indicator-candidate-dtb.sh \
  artifacts/network-root-v3/sm8350-asus-rog-phone5-recovery.dtb \
  dts/qcom/sm8350-asus-rog-phone5-buttons-indicator.dtso \
  /tmp/rog5-buttons-indicator.dtb

scripts/device/test-buttons-indicator-candidate-dtb.sh
```

The retained output is:

```text
artifacts/buttons-indicator-v1/sm8350-asus-rog-phone5-buttons-indicator.dtb
size=103554
sha256=57216474b4c8979161d964cef2ff3fe5d61500af3cef34598ee06e03e91f967d
```

## Kernel capability contract

The source gate pins:

- clean Linux `7.1.4` commit
  `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`;
- config SHA-256
  `68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f`;
- module archive SHA-256
`5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9`.

Power, resin, GPIO keys, OF/GPIOLIB, the Qualcomm SPMI PMIC arbiter,
SPMI/regmap/pinctrl, PWM, the new LED framework, LED class, and Qualcomm LPG
support are checked at Kconfig, Makefile, driver, OF-table, binding, DTSI,
final-config, and module-archive boundaries. The LPG source proves that
absent optional SDAM pattern storage does not prevent direct brightness
control. It parses every state other than `"on"` as `LED_OFF`, applies that
brightness, and independently clears the tri-LED enable register during
initialization. The candidate declares `default-state = "off"` and defines no
automatic trigger.

Set `ROG5_LINUX_SOURCE` to the clean retained 7.1.4 source root when running
the repository test if source-level integration evidence is required:

```sh
ROG5_LINUX_SOURCE=/path/to/linux-7.1.4 \
  scripts/host/test-buttons-indicator-source-contract.py
```

Without that variable, portable CI still runs every synthetic marker
mutation plus the exact in-repository config/module checks and reports the
retained-source integration leg as skipped.

Run:

```sh
scripts/host/verify-buttons-indicator-source-contract.py \
  /path/to/linux-7.1.4 \
  artifacts/network-root-v3/config-7.1.4-network-root \
  artifacts/network-root-v3/modules-7.1.4-network-root.tar.gz

scripts/host/test-buttons-indicator-source-contract.py
```

## Runtime acceptance order

One attended RAM-only candidate must keep the existing rollback watchdog and
minimal-headless checks armed. It should then:

1. require exactly one `pmic_pwrkey`, one `pmic_resin`, and one `gpio-keys`
   device;
2. load the exact accepted `leds-qcom-lpg.ko`, then require one default-off
   green LED class device;
3. record press and release for each physical key without synthetic events;
4. turn the green LED on briefly from userspace only after the minimal server
   reaches its accepted SSH/health state;
5. prove key presses and LED writes do not stop SSH, alter storage isolation,
   or produce new kernel warnings;
6. reboot normally to the exact fallback and collect the bounded result.

Suspend/wakeup and idle power measurements follow in the H3 lifecycle gate.
Power and volume-up are configured as wake sources from upstream and stock
evidence, while resin wake is deliberately deferred. None is accepted until
the H3 gate measures suspend/wake behavior and idle impact. The first runtime
probe must not add a heartbeat trigger: continuous blinking would add
avoidable idle power and could hide a userspace failure.
