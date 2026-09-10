# Denial native mobile bring-up

The selected goal is Denial Wayland on the ROG5 OLED with touch and accelerated
Adreno graphics. Cellular is excluded. The initial integration base is
`6651d598b9e2ce1f4a83b85630cdddfc2debb377`; the dirty original workspace and
accepted server/recovery artifacts remain preserved.

## Current phone and display preparation

Kernel-first followup produced an initial external FTS3658U driver in private
`touch-driver-r1`. It accepts only normal ID0x5652, preserves native fractional
coordinates, and performs no firmware upgrade or boot-ROM fallback. Review
removed the alternate3518 ID from this first component and stopped treating
unused UP coordinates as active position data. Optimized and UBSan host runs
each pass24,324 checks; six disabled-DT tests pass. Exact current-kernel module
twins pass in9.062 seconds:373416 bytes, SHA-256
`fc94acd0bc6cd6ce4900e5ccb62c3edb6ca6c17ae332cefdb0ed31d6624bbb60`.
Receipt:`touch-modules-r1/result.json`. No module registration/probe on the phone
is established. Final source review passes; suspend/resume remains explicitly
unsupported in this first component.

Repository integration `e8cebfcd` now carries the identical reviewed C/header,
external Makefile, shared C fixtures and disabled overlay. The portable
`scripts/device/test-rog5-front-touch.py` is linked in the README and wired into
the existing repository runner. Actual integration-tree runs pass eight tests
and 24,324 checks per C build mode under ordinary and optimized Python in
0.573/0.520 seconds. Shell syntax and diff checks pass. Full integration CI
has not run while the kernel compiler is active; the earlier full CI remains
evidence for its own source, not this new driver integration.

The exact f17 GENI I2C/GPI provider builds now pass with identical twins in
16.832 seconds. GPI is SHA-256
`2d80d8a82dd3c8a106fc658f43e5d263603ea144ee2253becc6f6fcbf69b4132`;
GENI I2C is `e02c93504574ca5fb6191359048a7767af1405fb4e29c34e62c694a349256fdf`.
Both have matching vermagic/BTF and built-in symbol providers. The three-module
stack passes exact-V9 guest registration in 2.687 seconds. Touch and I2C unload;
GPI refuses ordinary unload and remains `[permanent]` until guest shutdown, as
its source has no module exit. Receipts: `touch-bus-modules-r1/result.json` and
`touch-stack-vm-r1/result.json`. The VM supplies no phone I2C, DMA or rail proof.

Actual touch DT composition against both V9 and the display candidate preserves
unrelated properties, boot CPU and reservations; twelve hostile-delta cases
pass. Disabled variants add only four nodes and three symbol properties.
Enabled proposals change five statuses, preserve disabled SPI4 and make L8C's
always-on vote effective. Touch unbind releases only its own vote, so it cannot
restore the pre-probe physical rail state. Receipt:
`touch-dt-composition-r1/result.json`, SHA-256
`21ca1f657ca43ad9e77b86e66ec8c54297e3fe2b2400ed2719d1f1b648281812`.

The GPU audit identified one required built-in fix: propagate GMU power-level
probe failure before later initialization. Existing patch 0012 applies directly;
eight extracted actual-source fault-injection cases pass while the baseline
fails. Fixes 0026/0035 are already present; no duplicate or diagnostic patch was
added. Clean successor source `05941d04803f54208da1e9920a81874edc540ca1`
contains only 0012 over f17. Its source/config/compiler/release preflight passed
in 21.955 seconds; the unchanged configuration produces expected release
`7.1.4-g05941d04803f`. Kernel and 25 scoped module builds are **RUNNING** under
private `kernel-hardware-build-r1`; no completed successor is claimed yet.
Separate output directories share the existing verified compiler cache.
The build uses two CPUs, 6 GiB with no additional swap and a 4 GiB disk cache,
with bounded runtime and disk/memory-reserve monitoring. Await the owned runner
and its `twins-result.json`; do not restart it or reuse f17 module evidence as
successor qualification.

Three exact firmware files (1,153,192 bytes total) were recovered from official
linux-firmware 20260622 commit `b2722d241309a1872446c1d00c2e812bad055f89`.
All existing manifest sizes/hashes match; licenses, WHENCE and provenance are
retained. The sm8350 ZAP path is materialized from the upstream qcm6490 link.
Fresh parsing/readelf finds one relocatable 1976-byte segment at file offset
0x101000, physical address 0x1000, needing 4096 bytes within the unchanged
8192-byte reservation. This corrects the earlier audit prose that confused
physical address with file offset. Three malformed-layout fixtures refuse.
Receipt: `gpu-firmware-r1/result.json`, SHA-256
`427bda95710514d1d7060574a66dd969ebe7afae6919f9db11893359d19f54d1`.
There is no SCM authentication, hardware initialization or command-submission
proof. First DRM open initializes the GPU and must be an explicit bounded test.

The after-run improvement is concrete: use the already supported compiler cache
without bypassing exact-output state checks, and stop an owned build container
even if its launcher exits first. Nine cleanup fixtures pass in normal and
isolated modes, including stop/kill, ownership rejection, corrupt CID and
inspection failures. Receipt: `kernel-build-runner-review-r1/result.json`,
SHA-256 `81afd8c5b036815f9f061dd42990b95acd0a6e5d4bf9633fceb52ee39ab1d16f`.
Cache timing/benefit remains to be measured; the preflight and regression
passes do not constitute a full kernel-build result.

The configured display autoload audit expanded to2,453 root nodes, selected
effective unit/rule/helper text, the final archive catalog and radio manifest.
Udev's kmod loading is real, but its current-release module index is absent.
Historical7a5 REFGEN remains in the old module tree; dormant display scripts
have no enabled units. Four isolated host-kmod dry-run name/alias lookups refuse
the new modules even when the inert payload is present. These are static
configured-path results, not execution of the actual Arch coldplug path.
Receipt:`display-root-autoload-r1/result.json`, SHA-256
`26a8daf76c0323230867cc3f17c6fb079d3c5bfda703e2b9d59f38324a76f049`.

Packaging review identified a supported embedded signed RAM target route that
keeps the paired root images unchanged, plus concrete remaining integration
work. The target's healthy service still needs a matching pending userdata
trial record; embedded recovery does not create that record. A fresh guarded
operation and backup/readback qualification are required. The wrapper needs
fresh canonical registration and an exact-size admitted boot controller;128MiB
is expected from the comparable retained wrapper, but the new actual size has
not been measured. Do not reuse R01 authority or claim autonomous V11 recovery.

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

**Priority correction:** the user subsequently requested kernel and hardware
bring-up before Denial. Root stopped the exact live dependency container and
reaped its runner after 796.080 seconds. The bounded stop returned zero;
the raw sync result remains FAIL with exit137 after the stop grace period.
This was a deliberate interruption, not a reported memory-exhaustion event.
`engine-build-r1/priority-stop-entered.json` and `priority-stop-result.json`
preserve the reason and action; cache and partial source remain intact.
Do not follow the older running-job checkpoint below as a restart instruction.
Engine hooks, compilation and AOT assembly remain deferred during kernel-first
bring-up. Minimal hardware test programs remain appropriate for DRM/EGL/input
qualification. The real-phone Denial completion requirements remain unchanged.

Fresh read-only phone health passed in 0.938 seconds on the same accepted V9
boot, with installed identities and storage/power/healthy-selection checks.
Private receipt: `denial-engine-prep-health-r1/result.json` under the CPU-startup
evidence root. No hardware activation or reboot accompanied this check.

Engine preparation has now started in private `engine-build-r1`. The derived
builder image is `237f1e2fbb6bd4007dff61e165c60676e5668f716a4a2397f5e590a2a80303ee`.
It reuses the pinned Rust builder and adds thirteen host-tool packages from its
retained signed apt indexes, with no upgrades or removals. The reviewed plan
downloads 3.536 MB and estimates 13.5 MB additional installed files; actual
provisioning passed in 20.003 seconds with approximately 16 MB disk growth.
The installed-package inventory SHA-256 is
`5f1aef67d2c9a30b84b72f11efaf77df5c46e5e5008a463371bff9962bba34e2`.

Exact detached Flutter `d728e61e7d835e02c453c70ae9523a40f6c03215` and
depot_tools `580b4ff3f5cd0dcaa2eacda28cefe0f45320e8f7` checkouts passed in
22.003 seconds, using approximately 251 MB additional disk. Their origins and
clean tracked files were verified. The initial runner and its original hashes
remain retained; review then added exception-safe cleanup and exact source
checks around dependency synchronization and hook execution.

At the recorded checkpoint, the single dependency-sync container is running,
limited to 3 GiB RAM with zero additional swap, two CPUs and 512 processes.
The watchdog admits sync above 80 GiB free, retains a 10 GiB floor, stops after
60 GiB growth or two hours, and records terminal results. Bootstrap CIPD setup
is quiet because the pinned upstream wrapper suppresses its output; increasing
cache size and measured ingress confirm download progress. Twelve bootstrap
tools have immutable instance pins in the retained manifest. This checkpoint
does not establish a fully resolved or downloaded closure.

The next continuation must resume the existing job and inspect
`sync-result.json` and `sync-source-identities.json` before hooks. Flutter,
Skia, Dart and both depot_tools checkouts must retain exact origins, commits,
tracked cleanliness and the pinned root DEPS hash before hooks execute and
afterward. GN generation, engine compilation, AOT assembly and phone deployment
have not started. No phone action or human readiness request occurred during
this host preparation.

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

The isolated Rust 1.98 cross-builder is provisioned as image
`0f429c6fd38e4400d8638bff1f7da0170375275ab29201e327a3e236ed9df16d`.
Its 280-package plan has SHA-256
`25a81daac5d02cb6012d8b963623b64bedddfabfbf0ea6ac5cf1b8d89be59f0f`;
installed-package and signed-repository inventories are retained privately.
Provisioning passed in 286.036 seconds. No host packages or binfmt registration
were changed. The failed foreign-Python installation and unsupported build CPU
flag are retained; the corrected recipe uses native host tools and cgroup CPU
limits. Exact Rust archives were reused after streaming hash verification.

Locked Cargo fetch passed in 26.010 seconds. Offline ARM64 control-client
compilation passed in 22.010 seconds using one job and a 3 GiB memory cap.
Its 886880-byte binary has SHA-256
`36128080aa4f4f530ab60960eb0d8e184285e39a6a9244662459bd3a02da8eba`.
ELF inspection confirmed AArch64, and help/version passed under isolated QEMU.
It identifies itself as `development`; this is not a published release or a
compositor session. The original
fetch attempt selected unavailable slirp4netns; the successful run uses the
host's installed pasta network backend. Compilation runs without networking.

The full `flutter` feature build of `deniald` and `denialctl` passed in
464.094 seconds with the same one-job/3 GiB limits and unchanged upstream source.
Both final binaries are AArch64, use `/lib/ld-linux-aarch64.so.1`, have no
RPATH/RUNPATH, and passed help/version under network-disabled QEMU in 1.652 seconds.

| Native output | Bytes | SHA-256 |
|---|---:|---|
| `deniald` | 15979872 | `8698b0716c0ab16ab5c33d618ae52cef0cd8c0966ad356cf2ca49d78a0ba8591` |
| `denialctl` with full features | 886872 | `da22a0bd76e183cd25ce45ef532ae3ee533703dd5f6e00809ce2f3415b8566df` |

The earlier control-only binary is retained separately. These checks prove
linking against the prepared target libraries and terminal CLI paths only;
they do not load Flutter, acquire a seat, render, or prove the final Arch
runtime library closure. Private receipts are in `cargo-arm64-r2`.

A subsequent read-only audit of the retained effective Arch lower/upper layers
passes interpreter, library, version and strong-symbol closure for `denialctl`.
Arch glibc 2.43 satisfies the required GLIBC_2.39 floor. `deniald` is missing
`libgbm.so.1`, `libseat.so.1`, `libinput.so.10` and `libxkbcommon.so.0`;
its existing libc/libm/libgcc/libudev providers satisfy the inspected needs.
The effective upper libudev overrides the lower copy. Only 4905097 bytes of
selected ELF files were extracted under 512 MiB/zero-swap limits. Root metadata
still matches the earlier full-hash proof; the large images were not rehashed
or mounted. This is static closure, not target execution. Receipt:
`arch-native-abi-r1/result-r2.json`.

The engine recipe separates the ARM64 embedder graph from x64 host tools.
ARM64 AOT needs an x64 executable generating ARM64 code from the target graph;
the host graph's x64-targeting compiler is insufficient. Unmodified asset
assembly needs host GTK artifacts, which stay outside the phone bundle.
Pinned Flutter compiler/sysroots are separate from Rust's Ubuntu sysroot.
Engine graph generation and compilation remain pending. Hot reload needs a
matching debug/JIT engine and development assets; release AOT cannot supply it.

## Durable build capacity and repository checks

Reviewed cleanup removed 179337 single-link regular compiler-cache/object files
from 31 completed historical build roots: 72174505984 allocated bytes, or
67.218 GiB. All 15559 protected outputs passed post-cleanup checks; critical
Image/config identities were rehashed. Sources, final images/modules, logs,
recovery artifacts and current kits were preserved. Private manifests, deletion
log and terminal receipt are in `capacity-audit-r1` and `capacity-reclaim-r1`.
No visible active references were found. Privileged file descriptors/mappings
were not globally observable; the receipt states that limitation. Only
regenerable intermediates were eligible. Cleanup completed in 99.043 seconds
without errors.

Approximately 82 GiB was free before temporary full-CI fixtures. The estimated
40–80 GiB engine workspace is not a measured minimum. Keep large inputs on
durable storage and preserve the host reserve while measuring actual growth.

The first active-suite run lacked the pinned Android unpacker. Restoring its
exact bytes made all 46 composition checks pass. The workflow's active tier
also omitted that dependency. Both GitHub test jobs now bootstrap the pinned
tools for active checks while skipping the unused canonical boot template.
All 37 workflow/tier tests pass. Full local CI subsequently passed at frozen
source `752742fc2f7aeb1ce19d8389a81658399f1a28fc` in 563.196 seconds, including
the 95 native recovery cases in 31.090 seconds. Source remained clean.
Receipt: `source-ci-r3/result.json`; log SHA-256
`3dc9812709d043d140ef0977a418ec76b5b9975300704536524e1c2d9704dd2e`.
Optional private ARM64 environment replays reported skips; the actual module
and native CLI emulation proofs above are separate completed artifact runs.

The first full-CI attempt hit a Wi-Fi fixture's five-second deadline under an
added two-CPU quota; its focused rerun passed without that quota. The second
attempt progressed further but hit three native recovery fixture timeouts and
a teardown wait error. Responder/test bytes match the earlier 95-test PASS.
The three cases then passed in 7.145 seconds, followed by all 95 cases in
32.321 seconds with unchanged deadlines. External process sampling observed
uninterruptible waits in `fsync`/filesystem journal paths. This supports host
I/O latency as an explanation but does not capture or prove the original failed
wait's cause. All failed receipts remain retained; no production guard or
fixture timeout was relaxed. These failures remain separate from the final CI PASS.

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

The [display payload composer](../scripts/device/build-display-trial-initramfs.py)
accepts the qualified corrected-buttons unsigned base, preserves its runtime,
shutdown, radio and buttons bytes, and adds exactly two nested inert modules.
Only the descriptor/catalog change among existing members. It rejects historical
buttons bytes, mismatched inputs, reused identity and existing display opt-ins.
Six composer tests, three display closure/order tests and one actual runtime
installer inertness test pass in normal and optimized Python; six unchanged
indicator tests also pass. The production module bytes match their pins.
The new suite is wired beside the buttons composer in the repository runner.

Actual unsigned initramfs twins composed in 14.745 seconds total after the
frozen-source CI PASS. Both are 56081476 bytes, SHA-256
`3fcbf6d3dfa9dd45719c0ab167940961c76ee10a5500c8913bfd3e76eff294dc`.
The exact corrected-buttons base is SHA-256
`97de4bd3b2a47fa7c6468cbe1fe0116a7288b043279d028c73d234a3c60b33ee`.
Their fresh descriptor/catalog and preserved-member checks pass; no claim,
signature or activation was created. Receipt: `display-compose-run-r1/result.json`.
Temporary full-CI fixtures were removed by restoring the original sparse
checkout; all Git objects remain retained and approximately 81 GiB is free.

Complete boot-image qualification and final paired-root autoload absence remain
pending. Standard current-release module search paths are absent from both Arch
layers and inspected standard autoload configuration contains no panel/REFGEN
entries; that bounded audit does not cover arbitrary services or nonstandard
copies. The new DT enables built-in MDSS/DPU/DSI providers before userspace; unloaded panel
and REFGEN files do not mean all display hardware remains untouched until P24.
A future trial must first qualify the new-DT boot, then load the two modules
under the prepared controller. Physical scanout/blanking remains NOT RUN.

The retained ASUS front-touch source has variant-specific identification,
power sequencing and event decoding. Generic EDT compatibility is not proven
by the shared FocalTech name. Inspect the exact board wiring and protocol before
adding a binding; do not carry vendor automatic firmware upgrade into a first
probe. Touch, physical display and the native Denial session remain NOT RUN.

The private touch audit includes nine passing synthetic frame-decoder cases.
They establish the source-derived parser behavior, not a real controller read.
Retained vendor source now matches ASUS MP2 to the ZS673KS-MP overlay chain and
confirms I2C4 GPIO20/21, reset22, IRQ23, enable131, L3C at3.008 V and shared L8C
at1.8 V, with1080x2448 extents. GPIO131's electrical downstream net and upstream
regulator rails are not specified by that source. Current regulator code permits
omitted upstream supplies through dummy-parent resolution; missing schematic
data does not prohibit preparing a disabled candidate. Keep real L3C/L8C
consumer phandles, do not invent upstream links, and qualify actual power/ID
behavior separately.

The stock firmware's full-update payload metadata and selected operation hashes
now validate an 8 MiB DTBO image, SHA-256
`531af0246723b15181649063fa5e2f5407eec7804e01485920694a8722e09ea0`.
Bounded reads totaled 620184 payload bytes across inventory and reconstruction;
no other partition or complete firmware payload was materialized. This does not
independently authenticate the entire firmware archive. Eighteen payload-reader
and eight table/bounded-hash fixtures passed. Actual runs stayed below 28 MiB
RAM with no swap; source and original/corrected validation receipts are retained.

Only table entry 5 matches ASUS MP2 with board selector100,0, SHA-256
`e00aced418da0d0ad3e3e3e1572ae93468c862f451786a0a6360d8660200a2ba`.
Ordered fragments61→83→142 confirm front address0x38, GPIO22/23/131, ten
contacts, final1080x2448 extent and L3C/L8C consumers with L8C always-on.
The earlier2400 extent is superseded. Base regulator voltages and bus pinctrl
remain source-derived external properties; the DTBO supplies no missing board
schematic. This is offline variant evidence, not a new physical-board reading.
Receipt: `stock-touch-dt-r2/result.json`, with its scope clarification retained.

S06 shutdown and R01 autonomous recovery remain failed independently. The
buttons/LED component result remains accepted. Human tests must be completely
prepared before asking for a fresh Ready, with one prompt at a time and
automatic recording.

Final read-only phone health passed in 1.357 seconds on the same V9 boot
`7c945aa5-80d0-4af2-aa76-113d68e23ac5`. Installed identities, power/storage
guards and healthy selection remain valid. No phone module insertion, signing,
reboot or display/touch activation occurred during this checkpoint.
