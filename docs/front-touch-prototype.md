# Front-touch prototype

The ASUS ROG Phone 5 MP2 FTS3658U prototype provides a small normal-mode input
driver and a disabled DT candidate. **Physical touchscreen behavior remains
unqualified. System suspend returns `-EBUSY`; suspend/resume and wake gestures
are not implemented.** No accepted image or activation policy selects it.

Source is in [tools/rog5-fts3658u](../tools/rog5-fts3658u/README.md). The private
draft compatible is `asus,rog5-mp2-fts3658u`; it is not an upstream binding or a
generic EDT alias. The [disabled overlay](../dts/qcom/sm8350-rog5-mp2-front-touch-disabled.dtso)
keeps I2C4, its touch child, L3C and L8C disabled, and leaves SPI4 disabled.

## Focused host test

Requirements: Python 3, `dtc`, and a C compiler with UBSan support. From the
repository root:

```sh
python3 scripts/device/test-rog5-front-touch.py
```

`CC` may select a compiler executable. `ROG5_TEST_TMPDIR` may select an existing
or new scratch directory; by default the test uses `build/`. Temporary outputs
are removed after the test. No device, kernel kit or proprietary stock image is
required. The test compiles the actual shared C decoder in optimized and UBSan
modes and checks the actual compiled disabled DT. It does not build a kernel
module, access hardware, enable a regulator, or prove kernel cleanup behavior.

## Exact protocol scope

The first component admits only normal firmware ID A3/9F=`56/52`. The vendor's
separate 3518 mapping (`54/52`) is excluded. The driver writes only one-byte I2C
register pointers followed by reads; it sends no register-value writes, HID
conversion, bootloader commands, factory controls or firmware payloads.
Identification uses A3 and 9F; reports read 62 bytes from register 01. Both I2C
messages must complete. Transport errors stop identification immediately;
unknown IDs have at most 20 attempts in a 1-second retry window, plus completion
latency of the already-started I2C pair. GENI timeout/abort latency is additional.

Reports preserve native 1/16-pixel coordinates: X 0–17279 and Y 0–39167 correspond
to 1080×2448 pixels, with 10 multitouch slots. There is no assumed axis rotation.
The parser validates the whole frame before publishing contacts. Reserved
events, duplicate IDs, bad active coordinates and invalid count conditions are
rejected. UP coordinates are unused and do not invalidate another valid contact.
The vendor does not impose equality between reported count and active/total
records; the prototype preserves that behavior. Error frames release stale
slots. No undocumented checksum or automatic controller reset is added.

## Board and power contract

The retained stock MP2 overlay corroborates the model and board selector 100,0,
front address 0x38, reset GPIO 22, IRQ GPIO 23, GPIO 131 I/O enable, L3C/L8C consumers
and final 1080×2448 geometry. This is archived board data, not a fresh physical
controller identification. The source uses active-low reset and active-high
GPIO 131, with native input ranges 17280×39168.

Power uses real L3C at 3.008 V and L8C at 1.8 V. GPIO 131 remains a driver-controlled
enable, not a fabricated fixed regulator. The driver acquires only its own
consumer votes and checks GPIO/regulator failures. It never force-disables L8.
Unknown upstream rail phandles are left unspecified; electrical headroom,
retention and actual rail state are not established by that omission.

L8 is shared/always-on. The disabled regulator node makes that property inert.
In an enabled candidate, registering L8 can establish an always-on vote **before
the touch driver probes**. Touch unbind or probe failure does not remove that
provider/core vote or prove the pre-boot rail state was restored. Cleanup needs
separate health and rail/GPIO readback. The driver disables/synchronizes IRQ
activity before managed input and power resources are released; offline guest
registration does not exercise physical resource teardown.

## Provider and kernel qualification

The touch module alone is insufficient. Its closure also requires the matching
`i2c-qcom-geni.ko` and `gpi.ko`, the QUP wrapper, GCC clocks, IOMMU, pinctrl and real
RPMh providers. GENI chooses FIFO/SE-DMA or GPI from hardware state. It requires
GPI if FIFO is disabled. If the serial-engine protocol is invalid, the upstream
provider requires a separately qualified wrapper `firmware-name` and firmware
asset. No such property or asset is invented by this prototype; a different
valid protocol is rejected. Touch firmware and serial-engine firmware are
separate concerns.

The retained kernel at `f17befd4ef172cfb0ecbffd9e0af87122cfa66bc`, release
`7.1.4-gf17befd4ef17`, was built without enabled Rust support. C uses its existing
external-module ABI without reconfiguring the kernel. This does not preclude a
future Rust implementation on a suitably configured kernel.

Offline progress recorded on 2026-09-10:

- Shared decoder: 24,324 checks passed in each of optimized and UBSan modes;
  six compiled-overlay checks passed, and kernel checkpatch was clean.
- Matching f17 GENI I2C/GPI module twins passed in 16.832 s.
- Combined GPI/I2C/touch guest registration and consumer unload passed in 2.687 s.
  GPI was deliberately retained until guest reboot. This is registration/ABI
  evidence, not a physical touchscreen or power test.
- Disabled DT compositions against current V9 and the separate display
  candidate were identical in repeated builds. Four nodes and three symbol
  entries were added; unrelated property payloads and boot metadata survived.
  Twelve composition tests passed. A separate offline enabled proposal changed
  only touch, I2C4, GPI0, L3C and L8C statuses; no phone activation occurred.

The successor kernel `05941d04803f`, release `7.1.4-g05941d04803f`, now has
its own matching module twins and retained registration evidence. A 2026-09-11
read-only audit rechecked both copies of touch, GENI I2C and GPI against the
successor guest's pinned inputs and exact vermagic in 0.022 s. Touch SHA begins
`44aaf514`, GENI I2C `064edd21`, and GPI `8fdb109b`. Reuse these artifacts;
the historical f17 results above remain separate.

The successor component guest passed registration and consumer unload in
3.797 s, including all three touch modules; GPI remained until guest poweroff.
The retained static selected-module export closure also passes. Neither result
proves physical bus operation, touch identification, interrupt delivery or power
cleanup. The prepared OLED-only DT keeps I2C4 and GPI0 disabled and has no touch
child or L3C/L8C nodes at the proposed touch paths. OLED boot success therefore
cannot qualify touch. A separate exact-DT touch trial remains necessary.

## Remaining gates

Follow the [development workflow](development.md) for any future build or trial.
First qualify the complete module/provider/firmware closure and composed DT
against one exact kernel and base. Before asking for a touch, establish normal
`5652` identification, unique expected input/IRQ ownership, current boot/health,
real regulators and an independent bounded cleanup/fallback path. Only then
request fresh operator readiness and capture actual touch/release, native ranges,
IRQ activity and cleanup. Unknown IDs or bus failures do not authorize firmware
commands or blind retries. Production use also requires suspend/resume work.

This document imports no private device logs, proprietary DT blobs, signing
material or live admission into the repository.
