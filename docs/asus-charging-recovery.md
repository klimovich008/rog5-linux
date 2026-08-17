# ROG Phone 5 low-battery recovery hold

Use this runbook when the bootloader reports `battery-soc-ok: no`. Keep every
storage candidate unbooted and every one-use claim unconsumed until the gate
passes.

## Proven limits

Neither installed slot is an accepted charging environment:

- Slot B boots the Alpine fallback. Its ASUS/Qualcomm charging stack is
  incomplete, and external power has allowed pack voltage to fall while it
  runs.
- A 2026-08-16 attempt to enter the preserved slot-A recovery transitioned
  the exact phone from fastboot to `05c6:900e` Qualcomm crashdump, with the
  display waiting for a full RAM dump. It did not enter recovery or prove
  charging. A later normal slot-A boot produced the same crashdump result.
  The slot-A crashdump path must not be repeated.

The retained AVB metadata explains why slot A is not a coherent recovery
chain: `boot_a` reports `18.0840.2103.26-0`, while `vendor_boot_a` reports
`18.1220.2202.206-0`. The two slot-A components are from different ASUS
releases. This mismatch is evidence against using the installed slot, not a
reason to flash either component while the battery is low.

The presence of the backed-up ASUS `boot_a` image does not prove that the
installed slot-A companion firmware and recovery chain are complete or
charging-capable. `off-mode-charge: 1` and `charger-screen-enabled: 1` also do
not prove that the current installed operating systems can charge the pack.

## Recover crashdump to fastboot

If the phone displays the full-RAM-dump wait screen:

1. Hold Volume Down + Power for at least 8 seconds; use 12 seconds if needed.
2. Immediately hold Volume Up + Power.
3. At vibration, release Power but keep holding Volume Up until fastboot is
   visible.
4. Do not select Recovery.

After exact serial, product, and USB-topology verification, restore only the
verified fallback slot B as the active-slot metadata. Keep the phone in
fastboot; do not boot Alpine merely to inspect the battery.

## Battery gate

Read only the bootloader telemetry from the exact device:

```sh
fastboot devices -l
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar serialno
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar product
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar current-slot
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar battery-voltage
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar battery-soc-ok
```

Refuse Stage 1 unless `battery-soc-ok` is exactly `yes` and voltage has risen
substantially from the recorded low value. A flat or falling voltage remains a
refusal even if external power is attached. Do not leave the phone in Alpine
or fastboot under the assumption that either state will charge it.
After that gate passes, continue only from verified fallback slot B; the
mismatched slot-A crashdump path remains rejected.

## 2026-08-16 bounded charging evidence

The phone uses the side USB-C port for the anchored PC data connection and the
bottom USB-C port for the ASUS wall charger during these measurements. Two
distinct RAM-only ASUS-derived 5.4.210 recovery images preserved slot B and
returned directly to exact fastboot without accessing phone storage:

- `charging-rescue-fastboot-v1-live-v1` is consumed and never reusable. Its
  30-second window moved the bootloader reading from 6.801 V to 6.933 V, which
  then remained near 6.933 V.
- `charging-rescue-fastboot-v2-live-v1` is consumed and never reusable. Its
  five-minute window moved the reading from 6.934 V to 6.931 V.

The first step is too large to represent stored charge over that interval and
the longer cycle did not show a rising trend. A later fastboot soak fell from
6.931 V to 6.925 V over 30 minutes. These voltage-only cycles do not prove
net-positive charging or current direction.

`charging-telemetry-v1-live-v1` is now consumed and never reusable. Its
90-second output-only cycle returned to exact fastboot after 35 complete ACM
frames. Every
frame reported `PSY_COUNT value=0`: the side Type-C controller reached
`Attached.SNK`, but no battery or USB power-supply service registered. The
exact kernel has `QTI_BATTERY_CHARGER` and `QTI_PMIC_GLINK` built in, so adding
modules is not the fix. The downstream source requires the
`PMIC_RTR_ADSP_APPS` RPMsg channel and `msm/adsp/charger_pd` service.

One hybrid ASUS charger experiment followed. Version 1 was canceled before
claim entry when offline review found no charger-class trigger or rollback.
Version 2 paired the exact slot-B 5.4.134 kernel and matching installed
vendor-boot with the preserved ASUS recovery ramdisk, added a charger-only
class and 15-minute bootloader rollback, and was consumed once. It disconnected
USB and returned to exact fastboot about eight seconds later without ADB,
power-supply evidence, or Qualcomm crashdump. It is not a charging route and
must not be retried.

`charging-direct-stock-storage-isolated-v3-live-v1` is also consumed and never
reusable. Its direct ASUS-derived charger boot returned to exact fastboot after
about nine seconds, moving 6.883 V to 6.880 V without ADB, power-supply, or
crashdump evidence. The following normal slot-A boot entered `05c6:900e`; the
hardware-key recovery restored slot B without booting it.

Physical side-port isolation is now disproven as a charging route. Leaving
only the bottom ASUS wall charger connected for about 30 minutes moved the
bootloader reading only from 6.836 V to 6.839 V and left `battery-soc-ok: no`.
The change is within voltage/temperature measurement noise and does not prove
net-positive charge. Reconnecting side USB then reduced the reading to 6.833 V.
For future measurements, physically disconnect the side cable except for brief
exact fastboot reads.
See the redacted
[live charging-rescue result](../test-results/2026-08-16-low-battery-charging-rescue-live.md).

The later USB-free shutdown observation is a separate failure. The phone
powers off and immediately starts again even with both USB cables physically
disconnected. The current fallback's vendor-ramdisk modules reject its custom
5.4.134 kernel symbol versions, including `msm-poweroff`; its matching
`msm-restart` platform device is not bound. A Power-key hold is recorded as a
`KPDPWR_N` hard reset, not a clean shutdown. USB charger insertion remains a
distinct earlier PMIC trigger and is not used to explain the USB-free restart.

The historical 5.4.210 charger experiment has been recovered without a
phone boot. The retained build-21 Image and `ramdisk-new` reproduce the
recorded 43,753,472-byte `rog5-alpine-5.4.210-rtcharger.img` byte-for-byte at
SHA-256 `b5805cc29cea05ed13f0e4695ba8ffa50a2893223ff2fc06b6b9c60decf88d86`.
The matching slot-A vendor ramdisk contains the 5.4.210 poweroff closure, and
the six retained charger/ADSP modules all declare exact
`5.4.210-qgki-perf` vermagic.
This does not make build #21 known-good. Its original manifest described it as
a charger-calibration experiment, not the accepted default, and retained no
successful-boot proof. The different image/kernel #20 is the documented
known-good charging baseline.

An offline successor packages those exact inputs into a headless RAM-only
rescue. It starts no desktop or Wi-Fi, does not discover or mount userdata,
keeps slot B active, exposes NCM/ACM and key-only SSH, records five-second
battery samples, and forces a SysRq reboot after 30 seconds. Two clean builds
produce byte-identical initramfs SHA-256
`7366600f925587613629a2336036dd75321c67a5e51ffa470b43de40fdec74fb`.
The diagnostic transport is brought up before charger activation so a charger
failure remains observable.

Two first live routes are consumed. The installed fallback route stopped
before target execution because its exact config has both `CONFIG_KEXEC` and
`CONFIG_KEXEC_FILE` disabled. The direct bootloader route was accepted at
6.900 V, produced no target USB enumeration during a 66-second blackout, and
returned to exact slot-B fallback; post-cycle voltage was 6.901 V. Empty
pstore is inconclusive. Offline review found that rollback was armed only
after the first `mdev -s`, while every base module was then loaded with an
unconditional `insmod`. The corrected successor arms rollback first, restores
dependency-aware historical `modprobe` behavior, and retains optional base
module failures for diagnosis after USB is up. Neither consumed route may be
retried. The 30-second successor was then consumed once after exact-head CI.
It produced no target USB and returned to exact fallback on the same 67-second
boundary. Because its rollback was armed before `mdev` and modules, that
boundary proves userspace rollback did not control the return and strongly
indicates PID 1 never reached the arm point. The direct build-21 route is
retired.
This is offline construction evidence, not proof of current direction or
net-positive charging. See the
[reconstruction result](../test-results/2026-08-16-alpine-charging-rescue-reconstruction-offline.md).

An official ASUS WW-33.0210.0210.200 full A/B payload is retained privately at
3,859,425,958 bytes and SHA-256
`7d53b6cc78486598e1913ca5a9a48c7292b90527bd9c9ac80dabd5324be14eb4`.
Its complete ZIP passes CRC verification. The extracted `boot`, `vendor_boot`,
and `dtbo` form one package generation; their AVB properties identify
`18.1220.2202.206-0`, and the kernel is ASUS 5.4.210. The same payload includes
matching `dsp`, `aop`, `tz`, `xbl`, and `vendor` content. This is an offline
source for the corrected RAM-only charger design, not permission to write any
phone partition while the battery gate is closed.

The later direct-v5 probe established one concrete defect. It could display
the ASUS charger UI, but its replacement PID 1 disabled every fstab entry and
never ran the stock charger-mode sequence from `init.target.rc`:

1. mount the slot-selected modem firmware read-only at
   `/vendor/firmware_mnt`;
2. load the matching Q6/PDR, notifier, APR, and ADSP-loader modules;
3. write `1` to `/sys/kernel/boot_adsp/boot`;
4. wait for the battery power-supply service.

That omission explains the observed UI with no battery power-supply service;
it does not prove that restoring the sequence will produce positive battery
current.

The corrected offline successor uses the official WW33 Image
`54b8d9d2…17b33`, the exact memory-fixed board DTB `4a62a4b8…78065`, and five exact
`5.4.210-qgki-perf-gc89cd02a7dfe` modules extracted from the same WW33 vendor
image. UFS, DWC3 NCM/ACM, VFAT, PMIC-GLINK, and the battery-charger driver are
built into that kernel. It resolves only the backed-up slot-B modem partition
by `PARTNAME=modem_b`, start sector `1704888`, size `450560` sectors, and VFAT
UUID `00BC-614E`; mounts it read-only with `nodev,nosuid,noexec`; verifies the
mount; creates the stock `/firmware` link; and only then starts ADSP. It never
discovers or mounts userdata. The 30-second SysRq rollback is armed before
device enumeration, while NCM/ACM, key-only SSH, and five-second battery/USB
telemetry remain available for diagnosis.

Two clean payload builds completed in 2.205 and 2.189 seconds and are
byte-identical. Their initramfs SHA-256 is
`22bccf4d3a138cc09c1120d787a0a67a5079c6d7c78dd579468498077c58f639`.
This is still offline evidence: no new candidate has been issued or booted.
See the
[official WW33 rescue checkpoint](../test-results/2026-08-17-official-ww33-charging-rescue-offline.md).

The first publication audit caught two stable-recovery integration defects
before a phone boot: the builder still selected the bootloader-placeholder
DTB whose `/memory` range is zero, and the exact stock profile omitted the
initramfs-required `rog5.charging_rescue=1` token. The corrected builder pins
the already-reviewed explicit memory geometry, while the fixed profile binds
that token and the current rescue initramfs identity.

No currently installed low-battery charging route is proven. A prior official
WW33 stock-charging bundle transferred through stable recovery and entered its
one-use claim, but the post-claim recovery response timed out and target
execution remained unknown; it is consumed and cannot be retried. The retained
evidence now makes ASUS-5.4-to-ASUS-5.4 kexec the leading entry-path defect,
so a distinct successor instead composes the corrected WW33 kernel/initramfs
as one direct header-v3 `fastboot boot` image. It is not the retired direct
build-21 experiment: the corrected payload retains exact modem/ADSP setup,
diagnostics, and rollback. Direct v1 was rejected before issuance because its
slot-A wrapper retained the kexec payload's slot-B assertion. V2 changes only
the two equal-length slot-contract strings inside the direct initramfs and
proves the resulting wrapper, initramfs, and active `vendor_boot` all require
slot A. Clean twins and focused tests pass at the
[offline checkpoint](../test-results/2026-08-17-official-ww33-direct-charging-rescue-offline.md),
but no live charging result exists yet. An inline USB-C power meter remains
the independent physical discriminator.

Do not flash `boot_a`, `boot_b`, `vendor_boot`, `misc`, or any other partition
to solve charging. Do not erase, format, or repartition while the battery gate
is closed. A separately verified, one-use, RAM-only charging-rescue cycle may
run to recover the battery; it does not authorize Stage 1.

## Return to Stage 1

The current private Stage-1 execution record binds the verified fallback slot
B. Once an independently proven charging method has restored the battery,
re-enter fastboot and verify that exact slot plus every original precondition:

```sh
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar current-slot
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar battery-voltage
fastboot -s "$ROG5_FASTBOOT_SERIAL" getvar battery-soc-ok
```

Then revalidate device and USB identity, repository head, candidate size and
hash, private execution record, backup manifests, unconsumed claim, and all
Stage-1 geometry. A slot selection never substitutes for those checks.

## Long-term boundary

Retain the verified Alpine recovery route until native Linux charging or an
independent charging/recovery route is physically accepted. Native charging
requires the complete SM8350/ASUS path: PMIC GLINK charger service, battery
telemetry, USB Type-C/PD role and input-current negotiation, thermal
protection, dual-cell handling, and verified shutdown charging. Read-only
telemetry alone is insufficient. Charging-control writes remain disabled
until voltage, current direction, temperature, and dual-cell behavior pass
hardware validation.
