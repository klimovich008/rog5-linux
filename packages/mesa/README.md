# vulkan-freedreno (Turnip) for the ROG Phone 5: 8-bit storage on the A660

DXVK 3.0 and later hard-require `storageBuffer8BitAccess` (dxvk commit
701579e6, "Hard-require 16-bit and 8-bit storage buffer access", in
`src/dxvk/dxvk_device_info.cpp`). Turnip in Mesa 26.2.3 only exposes it on
a7xx (`storage_8bit` in `freedreno_devices.py`), so DXVK 3.1.1 in Proton
Experimental logged (BioShock Remastered, 2026-09-30)

    Found device: Turnip Adreno (TM) 660 (turnip Mesa driver 26.2.0)
      Skipping: Device does not support required feature 'storageBuffer8BitAccess'
    DXVK: No adapters found

and no D3D game started. That run was x86_64 Proton under FEX, whose driver
is FEX's x86 Mesa 26.2.0 (see "Not covered"); a native ARM64 Proton uses the
system driver, i.e. this package. `storageBuffer8BitAccess` is the only DXVK
3.1.1 hard requirement the A660 misses (checked with `s8test features`, below). DXVK asks for
`shaderInt8` too (already exposed on a6xx); it does not ask for
`uniformAndStorageBuffer8BitAccess` or `storagePushConstant8`, which stay off.

## What the patch does

`0001-tu-enable-storageBuffer8BitAccess-on-a6xx-gen4.patch` sets
`storage_8bit = True` in the `a6xx_gen4` props (A660, A690, 7c+ Gen 3,
FD643/644/663). Nothing else changes: the 8-bit path added upstream for a7xx
(Mesa MR 28254 and MR 39124) is generic ir3/Turnip code.

- Every SSBO descriptor gets a second, R8_UINT buffer descriptor (the SSBO
  descriptor size grows from 1 to 2 descriptors, as on a7xx; a6xx gen4 has
  `has_isam_v`, which that code asserts).
- 8-bit SSBO loads and stores are scalarized and emitted as typed
  `ldib`/`stib` through that descriptor, i.e. exactly what an
  `imageLoad`/`imageStore` on an R8_UINT texel buffer does, which a6xx
  already supports. There is no read-modify-write in the shader; on the
  A660 the store behaves as a true byte store and does not clobber
  neighbouring bytes written concurrently by other invocations (tested
  below, with a racy-RMW control that does fail).
- Upstream only enabled a7xx because the Qualcomm driver doesn't expose the
  feature on a6xx (Mesa issue 9979); no hardware limitation is recorded.

`PKGBUILD` is Arch Linux ARM's `mesa` 26.2.3-1 PKGBUILD cut down to the
`vulkan-freedreno` split package: only `-D vulkan-drivers=freedreno` is built
(no gallium, GL, EGL, GBM, LLVM or layers; ~5 minutes on the phone at -j4) and
the package ships the same three files as Arch's (`libvulkan_freedreno.so`,
`freedreno_icd.json`, license). The drirc files stay in `mesa`. `pkgrel=1.1`,
same epoch, so it replaces the installed `vulkan-freedreno 1:26.2.3-1`.

## Build and install

On the phone as the desktop user (needs `python-yaml`; the other
makedepends are already installed):

    sudo pacman -S --needed --asdeps python-yaml
    makepkg -f --nocheck
    sudo pacman -U vulkan-freedreno-1:26.2.3-1.1-aarch64.pkg.tar.xz

Add `vulkan-freedreno` to `IgnorePkg` in `/etc/pacman.conf` (next to `phoc
resources phosh gtk2`), otherwise the next Arch mesa update puts the stock
driver back. When Arch moves to a newer mesa, rebuild this package on the
same version (the Turnip ICD and the rest of mesa should match), or drop it
once upstream exposes 8-bit storage on a6xx. Running Vulkan applications keep
the old driver until restarted.

To try it without installing, point the loader at the built library:

    printf '{"ICD":{"api_version":"1.4.354","library_path":"%s"},"file_format_version":"1.0.1"}\n' \
        "$PWD/pkg/vulkan-freedreno/usr/lib/libvulkan_freedreno.so" > /tmp/tu8.json
    VK_DRIVER_FILES=/tmp/tu8.json <program>

## Tests (A660, 2026-09-30)

All with the new driver loaded through `VK_DRIVER_FILES` (nothing installed),
on the phone's Adreno 660, kernel r202.

- `s8test features` (`s8test/`): the stock driver misses exactly one DXVK 3.1.1
  requirement, `storageBuffer8BitAccess`; with the package's driver every
  requirement is present (Vulkan 1.3, 256 bytes of push constants,
  robustness2, maintenance5/6, ...).
- `s8test run`: 1 MiB compute dispatches with 8-bit loads (restrict/readonly
  and plain, `uint8_t` and `int8_t`), byte stores from adjacent lanes into the
  same 32-bit words, byte stores where the 4 bytes of a word come from 4
  different workgroups, 3-of-4-byte stores that must leave the 4th byte
  alone, 4 consecutive byte stores per invocation across word boundaries
  (immediate offsets), a dynamic-offset SSBO and robustBufferAccess2 on a
  13-byte range. 400 iterations (200 with and 200 without robustness, ~420 M
  byte checks) on the dev build and 10 on the packaged library: 0 mismatches.
  The negative control `s8rmw.spv` (byte stores replaced by a 32-bit
  read-modify-write) fails with ~4 M mismatches per 10 iterations, so the
  test does see lost neighbouring bytes. The ir3 disassembly shows the byte
  accesses as `ldib.b.typed.1d.u16` / `stib.b.typed.1d.u16` (no RMW).
- dEQP-VK 1.4.6.1 (the CTS version Mesa 26.2 CI uses), built on the phone:
  - every `spirv_assembly` and `ssbo` case with 8-bit types (4491 cases):
    1840 Pass, 2651 NotSupported (uniformAndStorageBuffer8BitAccess,
    storagePushConstant8, float64, NV_raw_access_chains, untyped pointers),
    0 Fail/Crash. With the stock driver 1804 of those passes are
    NotSupported. Includes `compute.8bit_storage.*`, `graphics.8bit_storage.*`
    (vertex/tess/geometry/fragment) and all 625 `ssbo.layout.random.8bit.*`.
  - regression set, since every SSBO descriptor is now two descriptors
    (16817 cases): all of `ssbo.layout`, `ssbo.readonly`,
    `robustness.buffer_access`, `binding_model.descriptor_buffer`, every 10th
    `robustness.robustness2.*storage_buffer*` and every 5th
    `binding_model.shader_access.*storage_buffer*`: 11203 Pass, 5614
    NotSupported, 0 Fail/Crash. Stock driver on the same list: 11023 Pass,
    and all 11023 still pass; 180 more run now.

Not tested yet: a D3D game through DXVK 3.x with this driver (needs a native
ARM64 Proton; x86 Proton uses FEX's own Mesa: `packages/mesa-fex`).

## Not covered

- x86 Proton (Proton Experimental x86_64 under FEX) uses the x86 Mesa in
  `/usr/share/guestos/fex-mesa` (Mesa 26.2.0, `usr/lib` and `usr/lib32`; FEX's
  Vulkan thunks are off and there is no 32-bit one), not this package. The
  same one-line change for that root, x86_64 and i686, is `packages/mesa-fex`
  (install with `steam-fex-turnip-8bit`; `steam-fex-rootfs-install` reapplies
  it to a new root).
- Other a6xx gen4 GPUs get the feature too but were not tested.
