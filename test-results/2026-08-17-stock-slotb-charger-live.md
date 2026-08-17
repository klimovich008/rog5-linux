# Exact stock slot-B charging boot — live result

## Outcome

**HOLD.** The genuine WW `18.0840.2202.231` stock `boot.img` was recovered,
cryptographically matched to the installed ASUS-signed slot-B metadata, and
booted once with `fastboot boot` while slot B remained active. ABL accepted the
100,663,296-byte image, disconnected exact fastboot, and returned exact
fastboot about 19 seconds later. No charger-mode USB, ADB, Qualcomm crashdump,
or sustained charging interval occurred. Bootloader voltage moved only from
6.886 V to 6.885 V and `battery-soc-ok` remained `no`.

The one-use profile `stock-ww18-slotb-charger-live-v1` is consumed and must
never be retried or flashed.

## Stock compatibility proof

The original ASUS CDN package is no longer available: both its global and
China CDN URLs return HTTP 404. A public archive of that removed FullOTA
contains `boot/11-231/boot-231.img`. The mirror is not the trust decision. The
downloaded image is accepted only because its payload reproduces the exact
descriptor in the installed, validly signed `vbmeta_b`:

| Field | Exact value |
|---|---|
| full boot image SHA-256 | `3bd168d7959fcf8070b0b1e9029e635b796c3972ed913514fb64f151247699f1` |
| boot payload size | 55,554,048 bytes |
| signed AVB salt | `2c86224e8273d316b33b1bf59b8933f25efd41e20fccdb466197e5ca7f23dbe5` |
| signed AVB digest | `662e82893429b478dcafed37a200c455bd8b5288414b43fa991c352796b3822b` |
| boot header | v3, 4 KiB page, empty image command line |
| fingerprint | `asus/WW_I005D/ASUS_I005_1:11/RKQ1.201022.002/18.0840.2202.231-0:user/release-keys` |
| OS / patch | Android 11 / 2022-02-05 |
| kernel | `5.4.134-qgki-perf-00001-g6c308144c23e` |
| kernel SHA-256 | `0ba3bbb7487675af9f42fbe0a852ed50ed720bc0b5b37dd68b9779a2876acf6e` |
| stock ramdisk SHA-256 | `2974e191e5c02fb290f1f098300585c7b4e23c5cc32afe4751e947ee6f7ba692` |

`vbmeta_b` passes its embedded SHA256_RSA4096 signature; `vbmeta_system_b`
passes SHA256_RSA2048. Installed `vendor_boot_b` and `dtbo_b` reproduce their
signed slot-B descriptors exactly. By contrast, the persistent Alpine
`boot_b` payload does not match the signed stock descriptor, confirming that
only its boot image replaced the coherent ASUS charger handoff.

The private compatibility report is SHA-256
`3f53ffcad3f8fb00a632bfb31ec2f7afeee2b0c48e2c81ba194fb093ab776c73`.
The consumed claim is SHA-256
`12efa3a26b46180fa375205abad0e4a529468b68101c56ebe048606e827e30f7`.

## Physical timeline

| Host time | Event |
|---|---|
| 07:15:53 +0200 | one-use claim entered; slot B already verified |
| 07:16:06 | ABL accepted the exact stock boot image |
| 07:16:08 | exact fastboot USB disconnected |
| 07:16:27 | exact `0b05:4daf` fastboot USB re-enumerated |
| 07:16:29 | runner verified 6.885 V, `battery-soc-ok=no`, and refused success |

A single bounded Alpine fallback boot collected the postmortem, then returned
to exact fastboot. Pstore was empty and therefore inconclusive. The PMIC log
contained two completed `PS_HOLD` / `HARD_RESET` cycles and no watchdog token;
one covers the stock return and one the subsequent fastboot-to-fallback
transition, so their exact ordering cannot be assigned. No fatal fallback
dmesg token appeared.

## Consequence

The stock image is available and compatible, but ASUS fastboot did not keep
the exact header-v3 boot in charger mode. This closes the requested simple
RAM-only stock route without justifying another hybrid wrapper. The normal
persistent architecture would restore this exact image to `boot_b`, then let
the bootloader perform its natural powered-off charger handoff with the
already matching slot-B companions. That persistent write remains prohibited
while `battery-soc-ok=no`; it also replaces the persistent Alpine fallback and
therefore requires a separately reviewed recovery plan and an explicit change
to the current hard boundary.

No partition, GPT, userdata, vendor-boot, DTBO, or vbmeta image was written in
this cycle. Stage 1 remains prohibited.
