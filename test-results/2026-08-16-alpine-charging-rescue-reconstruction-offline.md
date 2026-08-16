# Alpine 5.4.210 charging-rescue reconstruction — offline result

Date: 2026-08-16

Result: **PASS for exact historical reconstruction and a deterministic,
headless RAM-only rescue payload. Charging remains physically unproven.**

## Corrected diagnosis

The phone's immediate restart also occurs with both USB cables disconnected.
That is not explained by charger insertion. The running fallback uses kernel
`5.4.134-qgki-perf-00001-g6c308144c23e`, while its vendor-ramdisk modules
reject that kernel's symbol versions. `msm-poweroff` is among the rejected
modules and the `msm-restart` platform driver has no bound device. The current
PMIC history identifies a Power-key hard reset; a separate earlier record
identifies a USB-charger trigger. Shutdown failure and charger-triggered wake
therefore remain distinct.

## Recovered historical artifact

Read-only inspection found the retained 5.4.210 build output and two Alpine
ramdisks in the fallback. Repacking build #21 with `ramdisk-new` and the exact
backed-up boot-v3 template reproduced the manifest's historical charger image:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| build-21 Image | 37,915,136 | `6dff1ff234fab4fa37f30ad5862cd58b693c9f4441d9ed242acbe285d559c78f` |
| `ramdisk-new` | 5,830,004 | `64db1bf572e2fb8ac77a8a79ea283e81a57ff8a9a319f0cba68da18f6a8c9841` |
| reconstructed raw boot image | 43,753,472 | `b5805cc29cea05ed13f0e4695ba8ffa50a2893223ff2fc06b6b9c60decf88d86` |

The raw image identity exactly matches the recorded
`rog5-alpine-5.4.210-rtcharger.img`; this is not merely a same-version build.
The matching slot-A vendor ramdisk contains the expected 5.4.210 module
closure, including `qpnp-power-on` and `msm-poweroff`. All six retained
charger/ADSP modules declare exact `5.4.210-qgki-perf` vermagic.

## Headless rescue

The new private payload uses the recovered kernel, matching vendor module
closure, applied ASUS WW33 DTB, Alpine userspace, and only these charger
modules, in the reviewed order:

1. `q6_pdr_dlkm`
2. `q6_notifier_dlkm`
3. `snd_event_dlkm`
4. `apr_dlkm`
5. `adsp_loader_dlkm`
6. `qti_battery_charger_main`

It writes only the required ADSP boot control, waits for the battery
power-supply, samples status/capacity/voltage/current/temperature every five
seconds, and exposes NCM/ACM plus SSH. The diagnostic transport starts before
charger activation so a charger-stack failure remains observable. It contains
no userdata discovery, mount, `switch_root`, desktop, Wi-Fi, or
persistent-install path. A rollback process is armed before candidate identity
validation and forces SysRq reboot after 180 seconds; active slot B is
unchanged.

The initial clean builds took 1,656 ms and 1,643 ms. After moving diagnostics
ahead of charger activation, clean builds took 1,530 ms and 1,522 ms. Every
final output is byte-identical; the initramfs is 8,183,331 bytes with SHA-256
`f01788ef2a73d692d4dd67a74dda9f76d46fe2a13fa820c4ddd39730779b8bde`.
The focused contract, stock charging loader test, repository-runner contract,
and diff check pass.

No phone reboot, kexec, slot change, partition write, signing, or candidate
issuance occurred. The payload does not yet prove net-positive charging,
current direction, thermal safety, or clean physical poweroff.
