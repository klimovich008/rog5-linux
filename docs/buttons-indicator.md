# Buttons and headless status indicator

## State

The first Linux 7.1.4 candidate is **offline-ready and live-pending**. It has
no boot, signing, flashing, or runtime authority. It preserves the accepted
headless DTB and adds only three physical buttons plus one default-off green
status LED. A dependency-free three-key attended gate is now also available
for the actual minimal root; it has not been run on the phone.

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

This 102,870-byte source-built DTB is tracked because both repository test
tiers must reproduce and hostile-test the additive candidate from a clean
checkout. The test rejects an untracked base or a manifest row not marked
`tracked=yes`; it no longer relies on an incidental local artifact cache.

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
  `5be71d86eafbb43086b901897d812ef3efa6c806a80101fc3194749866cb4fa9`;
  and
- the exact accepted LPG module extracted from that archive:
  `artifacts/buttons-indicator-v1/leds-qcom-lpg.ko`, 368,320 bytes,
  SHA-256
  `5885a9db2a8821f7c0ee9b16d92092d6d44f5c5092561e8e312f6047bb1a246c`.

Power, resin, GPIO keys, OF/GPIOLIB, the Qualcomm SPMI PMIC arbiter,
SPMI/regmap/pinctrl, PWM, the new LED framework, LED class, and Qualcomm LPG
support are checked at Kconfig, Makefile, driver, OF-table, binding, DTSI,
final-config, and module-archive boundaries. The LPG source proves that
absent optional SDAM pattern storage does not prevent direct brightness
control. It parses every state other than `"on"` as `LED_OFF`, applies that
brightness, and independently clears the tri-LED enable register during
initialization. The candidate declares `default-state = "off"` and defines no
automatic trigger.

The same source oracle now pins the real system-suspend IRQ path rather than
stopping at registration: PMK8350 power enables and disables its IRQ as a
wake source around suspend/resume; resin follows the same callback but stays
non-wake-capable because neither its default data nor DT node opts in; and
`gpio-keys` arms only the `wakeup-source` volume-up IRQ through its PM ops.
This is static call-path evidence, not a claim that firmware or hardware wake
works on the phone.

Set `ROG5_LINUX_SOURCE` to the clean retained 7.1.4 source root and
`ROG5_ACCEPTED_MODULES` to the retained exact module archive when running the
repository test if full integration evidence is required:

```sh
ROG5_LINUX_SOURCE=/path/to/linux-7.1.4 \
ROG5_ACCEPTED_MODULES=artifacts/network-root-v1/modules-7.1.4-network-root.tar.gz \
  scripts/host/test-buttons-indicator-source-contract.py
```

Without those variables, portable CI still runs every synthetic marker
mutation plus the exact tracked config and AArch64 LPG-module checks. The
fixture gate checks the module's byte identity, ELF class/type/machine,
accepted kernel release, license, description, and PM8350C OF alias. The
retained-source/full-archive integration leg is reported as skipped. This
keeps every tracked blob below GitHub's per-file size limit without replacing
the separate 300,439,504-byte archive hash check used by full integration.
The v3 manifest reuses the byte-identical v1 archive, so the host keeps one
canonical ignored copy rather than spending another 300 MB on a duplicate.
When that archive is selected explicitly, verification extracts its exact LPG
member and requires it to equal the compact fixture's size, SHA-256, ELF
identity, and module metadata.

Run:

```sh
scripts/host/verify-buttons-indicator-source-contract.py \
  /path/to/linux-7.1.4 \
  artifacts/network-root-v3/config-7.1.4-network-root \
  artifacts/network-root-v1/modules-7.1.4-network-root.tar.gz

scripts/host/test-buttons-indicator-source-contract.py
```

## Dependency-free physical-key gate

The historical `monitor-network-root-pwrkey.sh` remains evidence for the
isolated v5 diagnostic, but its embedded Python reader is not executable on
the active 152-package minimal root and it observes only the power key. It is
not the current three-key acceptance path.

`run-network-root-physical-keys.sh` uses only commands already supplied by the
minimal Arch base. Under one exact guard it requires normal systemd mode, the
active server inhibitor, read-only NFS plus OverlayFS, tmpfs `/run`, zero
physical/block-backed storage, disarmed rollback, one exact `a600000.dwc3`
UDC and unchanged USB address/direct route. It then requires exactly:

- `pmic_pwrkey` / `KEY_POWER` 116 / `pm8941-pwrkey`, wake enabled;
- `pmic_resin` / `KEY_VOLUMEDOWN` 114 / `pm8941-pwrkey`, wake absent; and
- `gpio-keys` / `KEY_VOLUMEUP` 115 / `gpio-keys`, wake enabled.

Each attended key must produce one press and one release in order. Its named
IRQ must advance by at least two and at most sixteen counts, bounding both a
dead path and an interrupt storm. Each evdev node is opened once before its
`READY` line and retained across its press/release pair, so neither a quick
first press nor a fast release can fall into an unowned/open gap. Binary
`input_event` records are staged only in a private `/run` tmpfs
directory and removed on every exit. The gate performs no sysfs, LED,
power-state, block-device, boot, or persistent-storage write. It rechecks
kernel identity, systemd, NFS, storage, rollback, UDC,
carrier, address, direct route, fatal signatures, and the warning digest
afterward, with distinct USB/link classifications.

The fixture backend is accepted only for an unprivileged caller with an
explicit test marker and a caller-owned mode-0700 non-linked root. Hostile
tests cover missing authority, precondition drift, every key identity and
wake policy, duplicate devices, malformed/reordered/repeated events, missing
IRQ movement, IRQ storm, linked fixture input, and post-return UDC,
interface, carrier, address, route, NFS, warning, and fatal changes.

## Runtime acceptance order

The offline runtime half is now implemented by the
[native key-indicator service](headless-key-indicator.md). Its production
binary has no fixture interface, interpreter, Python, shell, network, storage,
display, reboot, or poweroff path. It first requires the exact
`pmic_pwrkey`/`KEY_POWER` evdev device and exact `green:status` class device
backed by `qcom-spmi-lpg`, DT node
`/soc@0/spmi@c440000/pmic@2/pwm/led@2`, maximum brightness 511, brightness
zero, and selected trigger `none`. Only a value-1 `KEY_POWER` event produces
a 180 ms brightness-31 pulse. Shutdown and every error path synchronously
restore zero.

One attended RAM-only candidate must keep the existing rollback watchdog and
minimal-headless checks armed. It should then:

1. require exactly one `pmic_pwrkey`, one `pmic_resin`, and one `gpio-keys`
   device;
2. load the exact accepted `leds-qcom-lpg.ko`, then require one default-off
   green LED class device;
3. run the exact guarded three-key gate and record press/release plus bounded
   IRQ movement for each physical key without synthetic events;
4. run the helper's read-only `--probe`, then enable its bounded pulse service
   only after the minimal server reaches its accepted SSH/health state;
5. prove key presses and LED writes do not stop SSH, alter storage isolation,
   or produce new kernel warnings;
6. reboot normally to the exact fallback and collect the bounded result.

Suspend/wakeup and idle power measurements follow in the H3 lifecycle gate.
Power and volume-up are configured as wake sources from upstream and stock
evidence, while resin wake is deliberately deferred. None is accepted until
the H3 gate measures suspend/wake behavior and idle impact. The first runtime
probe must not add a heartbeat trigger: continuous blinking would add
avoidable idle power and could hide a userspace failure.
