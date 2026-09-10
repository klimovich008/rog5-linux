# Denial native mobile bring-up

The selected goal is Denial Wayland on the ROG5 OLED with touch and accelerated
Adreno graphics. Cellular is excluded. The initial integration base is
`6651d598b9e2ce1f4a83b85630cdddfc2debb377`; the dirty original workspace and
accepted server/recovery artifacts remain preserved.

## Current phone and display preparation

Fresh read-only full health passed in 1.252 seconds on V9 boot
`7c945aa5-80d0-4af2-aa76-113d68e23ac5`, kernel `7.1.4-gf17befd4ef17`.
A separate 0.244-second inventory opened no device nodes and changed no hardware.
There are no DRM card/render nodes, framebuffer or backlight, and only the
three qualified key inputs. MDSS, both DSI controllers, GPU and GMU are disabled
in the current device tree. The inventory preserves absent/error observations;
`/sys/class/drm/version` is an ordinary attribute, not a DRM device directory.

The [earlier 60 Hz result](2026-09-02-display-status-screen-development.md)
proves display/status-screen behavior on its own kernel and DT. Older Adreno
registration/GMU-entry diagnostics do not prove rendering. The current kernel
already has the required MSM KMS/DPU/DSI implementation built in, so the next
display preparation can use external panel and REFGEN regulator modules.

The 448-line panel source extracted from the existing patch is byte-identical
to the historical qualified source, SHA-256
`45e8bcb9c608645e76ae888e33f3c4d2e9096338eae95d59c67b56f2f428b892`.
REFGEN source is unchanged from the exact current kernel. All their undefined
symbols resolve to current built-in exports. Twin external builds used the
read-only exact kernel kit, one compile job and a 2 GiB container limit:

| Module | SHA-256 | Result |
|---|---|---|
| `panel-asus-rog5-ams678.ko` | `5bacaed0279d6e94b08003cc4dfb35f8eb17c33f643190ceef78ef40aa7f0f6c` | identical twins, vermagic/BTF/export closure PASS |
| `qcom-refgen-regulator.ko` | `f0ee47b2f1f5b7bd70fe1c486322a04f6509be04c58c10ecb5890d82a2272fc6` | identical twins, vermagic/BTF/export closure PASS |

Build and verification took 12.967 seconds. Exact-V9-Image QEMU load/unload and
driver-registration checks passed in 2.199 seconds. The VM has no ROG5 panel;
these results do not prove physical probe, scanout or brightness cleanup.
Private receipts are under `rog5-denial-20260910-r1/display-modules-r1`.
No module insertion, display activation, reboot, signing or phone write occurred.

## Denial source and build order

[Denial v0.3.1 source](https://github.com/denialwm/denial/tree/85b2303e2f09ae7b7b993641f90061a200f03d53)
contains its mobile shell, selected with `DENIA_SHELL_PROFILE=mobile`.
The [source lock](../configs/denial/source-lock-v1.json) pins Denial, Flutter,
Skia, depot_tools, Rust 1.98.0 and the Cargo graph. The shallow source checkout
used approximately 36 MiB; no engine or release package was downloaded.

The [build guide](https://github.com/denialwm/denial/blob/85b2303e2f09ae7b7b993641f90061a200f03d53/docs/BUILDING.md)
supports ARM64 source builds, but the supplied reference scripts and checksum
metadata target x86-64. A separate target-aware recipe is required; changing
only a destination path does not make an ARM64 build. The Rust compositor loads
its engine dynamically, allowing native compositor/control-client compilation
before the engine is available. Build that smaller part first, then the matching
ARM64 release engine and host AOT tools, then mobile shell/assets/ICU. A JIT
development bundle needs matching additional engine artifacts and is later work.

Current disk availability is approximately 19 GiB. The private audit's estimated
40–80 GiB engine workspace is a planning estimate, not a measured minimum.
Resolve durable build capacity before engine dependency synchronization. Keep
large inputs out of RAM-backed filesystems and preserve the 3 GiB host reserve.

## Remaining hardware boundaries

The current-base display DT must preserve newer buttons, storage, memory and
radio properties; the historical display DT cannot substitute for it. A guarded
display candidate still needs exact package composition and prepared observation
before any physical test. GPU acceleration remains unproven.

The new [current-V9 builder](../scripts/device/build-display-v9-candidate-dtb.py)
and [verifier](../scripts/device/verify-display-v9-dtb-delta.py) pin the current
107878-byte base and reuse the unchanged historical structural comparator.
Unsigned twins match SHA-256
`2ee1ed4b43083bb7e50631269009107efbe0ffed89207acce3c8066f6ba9e4df`:
exactly ten added nodes and fourteen changed properties. Nine focused tests
passed in normal and optimized Python, including rejection of non-display drift,
wrong identities, linked inputs, overwrite and tool failures. Review also exposed
node comparison overlooking boot CPU and the FDT reservation map; the new wrapper
now preserves both and rejects mutations invisible to node comparison. The focused suite
requires the explicitly supplied retained base; these results are not a new full
CI or admission result. Updated private receipt: `display-dtb-r1/result-r2.json`; the earlier, narrower
receipt is preserved.

The retained ASUS front-touch source has variant-specific identification,
power sequencing and event decoding. Generic EDT compatibility is not proven
by the shared FocalTech name. Inspect the exact board wiring and protocol before
adding a binding; do not carry vendor automatic firmware upgrade into a first
probe. Touch, physical display and the native Denial session remain NOT RUN.

The private touch audit includes nine passing synthetic frame-decoder cases.
They establish the source-derived parser behavior, not a real controller read.
The exact stock DT and regulator topology remain prerequisites for a touch probe.

S06 shutdown and R01 autonomous recovery remain failed independently. The
buttons/LED component result remains accepted. Human tests must be completely
prepared before asking for a fresh Ready, with one prompt at a time and
automatic recording.
