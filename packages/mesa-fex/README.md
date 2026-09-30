# x86 Turnip for FEX's guest root: 8-bit storage on the A660 (DXVK 3.x)

`packages/mesa` fixes the phone's aarch64 Turnip so DXVK 3.x accepts the
Adreno 660 (`storageBuffer8BitAccess`). x86 Proton does not use that driver.
This package builds the same fix for the x86 Mesa in FEX's guest root.

## Which driver x86 Proton uses (checked on the phone, 2026-09-30)

Steam's FEX tool (`steamapps/common/FEX-Emu`, FEX-2607-76-g37265b1) runs x86
Proton with `/usr/share/guestos/fex-mesa` as the rootfs. That is FEX's ArchLinux
image 2026-08-11 from `steam-fex-rootfs-install`. Graphics come from the
guest's own x86 Mesa, not from host thunks:

- `fex-compat-tool` enables thunks only through `STEAM_COMPAT_FEX_CONFIG`
  (`ThunksDB_Vulkan:1`). Nothing sets it: the `fex-emu/AppConfig` directories
  are empty, and every per-game `fex-emu/Config.json` has only RootFS and the
  thunk paths. The ThunksDB stays empty.
- There is no 32-bit Vulkan thunk. `GuestThunks_32` has no `libvulkan-guest.so`.
  BioShock Remastered is 32-bit (`winevulkan.dll` loads at 0x778a0000).
- The Proton log reports `turnip Mesa driver 26.2.0`. That is the guest's Mesa;
  the host driver is 26.2.3.

The guest's `usr/lib/libvulkan_freedreno.so` (x86_64) and
`usr/lib32/libvulkan_freedreno.so` (i686) are FEX's own build of the
`mesa-26.2.0` tag (`26.2.0 (git-9f0a761020)`). The x86_64 one was built with
gcc 16.2.1 and the i686 one with clang 22.1.8 -m32. FEX's recipe is
`Scripts/Arch/build_install_mesa.sh` in github.com/FEX-Emu/RootFS. Both drivers
lack 8-bit storage on a6xx, so DXVK 3.1.1 finds no adapter. Both get replaced
because 32-bit games load the i686 driver unless Proton runs in WoW64 mode.

## The build

`build.sh` builds only Turnip from the official `mesa-26.2.0.tar.xz`. Its
SHA-256 comes from `docs/relnotes/26.2.0.rst`. The build adds
`../mesa/0001-tu-enable-storageBuffer8BitAccess-on-a6xx-gen4.patch` (the same
one-line change as the native package) and runs in a podman container:

- `Containerfile`: `archlinux` pinned by digest, with pacman pointed at the
  Arch Linux Archive snapshot of 2026-08-12. All 203 packages it shares with
  the guest image's pacman database have the same version (gcc
  16.2.1+r23, glibc 2.44+r24, libdrm 2.4.134, wayland 1.26.0, spirv-tools
  1.4.357.0, clang 22.1.8, ...). The only difference is the build-only python.
  The build uses no network (`--network=none`).
- `container-build.sh`: FEX's meson options, minus everything that isn't
  Turnip:
  - `buildtype=release`, `b_ndebug`
  - SSE math and `-mstackrealign`
  - `freedreno-kmds=msm,virtio,kgsl`
  - `platforms=x11,wayland`
  - `shader-cache`
  - `vulkan-drivers=freedreno`, with no gallium, GL or LLVM

  x86_64 builds with gcc. i686 builds with clang via `cross-i686.ini`, which
  follows FEX's `cross_x86`. `VERSION` is set to `26.2.0-rog5.<release>` and
  the git id to the tag's `9f0a761020`:
  - `driverInfo` reads `Mesa 26.2.0-rog5.1 (git-9f0a761020)`.
  - `driverVersion` stays 26.2.0.
  - The pipeline cache UUID changes with the build id.

  It also builds `s8test` from `../mesa/s8test` for x86_64 and i686.
- `check-offline.sh`: runs automatically when the guest image is unpacked at
  `~/.local/state/rog5-mesa-fex/rootfs/guest`.

Run it as the desktop user (no root, about 10 minutes on the Deck):

    packages/mesa-fex/build.sh 1

It writes `~/.local/state/rog5-mesa-fex/r1/`, which is not in git:

- `usr/lib/libvulkan_freedreno.so` and `usr/lib32/libvulkan_freedreno.so`
- `SHA256SUMS`
- `BASE.SHA256SUMS`: the guest drivers this build replaces. They come from
  this directory's `BASE.SHA256SUMS`, taken from FEX's ArchLinux 2026-08-11
  image; the phone's copies have the same hashes.
- `BUILDINFO`, `build-packages.txt`, `storage_8bit.txt`
- `s8test/`
- a copy of `steam-fex-turnip-8bit`

For the offline checks, fetch the guest image once. The URL and XXH3 come from
`https://rootfs.fex-emu.gg/RootFS_links.json`:

    cd ~/.local/state/rog5-mesa-fex/rootfs
    curl -fLO https://rootfs.fex-emu.gg/ArchLinux/2026-08-11/ArchLinux.sqsh
    xxhsum -H3 ArchLinux.sqsh          # XXH3_23350f949fc1413d
    unsquashfs -q -n -d guest ArchLinux.sqsh

## Offline checks (r1, 2026-09-30, `check-offline.sh`)

- **Linking.** Each driver has the same ELF class, NEEDED list and exported
  symbols as the guest's. Inside the guest root (bwrap), `ldd -r` resolves
  every library, symbol and symbol version. So nothing needs a newer glibc,
  libstdc++, libdrm or wayland than the guest has.
- **Loading.** Inside the guest root, the guest's Vulkan loader loads each
  driver (x86_64 and i686) through `VK_DRIVER_FILES`, and Turnip creates an
  instance (`TU_DEBUG=startup`). With no Adreno in the host, it then finds no
  device. The guest's own drivers behave the same (control).
- **Unchanged files.** The ICD manifests and `00-turnip-defaults.conf` that
  come out of the build are byte-identical to the guest's, so only the two
  libraries are replaced.
- **The fix itself.** In the generated device table, the `FD660` entry has
  `storage_8bit = true` in both builds. A copy of the table with that one
  field removed fails the check.
- **Reproducible.** Two clean builds of r1 give identical libraries
  (`PYTHONHASHSEED=0` for Mesa's generators):
  `2bad5da1...` for x86_64 and `cfc1a2e2...` for i686. The full hashes are in
  `r1/SHA256SUMS`.
- **Closeness to the original.** The libraries are the same size as the
  originals to the byte: 17745456 (x86_64) and 15853432 (i686). `.text`
  differs by under 1.1 KB and `.rodata` by 576 bytes (build paths).

The real test needs the A660 under FEX (below).

## Installing on the phone

`scripts/device/steam-fex-turnip-8bit` (as root, with Steam closed):

- `install DIR [--force]`
  - Checks DIR against its `SHA256SUMS`.
  - Refuses unless the guest's drivers are the ones in `BASE.SHA256SUMS`, or
    are already the 8-bit build. `--force` overrides this.
  - Copies the payload to `/var/lib/rog5-fex-turnip/payload`.
  - Backs up each original to `/var/lib/rog5-fex-turnip/orig/<arch>-<sha256>.so`,
    outside the guest root.
  - Writes each new driver beside the old one, checks its SHA-256 and
    `rename()`s it over the original, keeping owner and mode. Each file is the
    old or the new one at every moment.
- `restore`: puts the backed-up originals back. It leaves alone a file that is
  neither (for example, after a new root).
- `status`: shows what each driver file currently is.

It takes the same locks as `steam-fex-rootfs-install`. That lock is held
shared by a running `steam-arm64`, so neither script runs while Steam or the
other script is running.

**FEX rootfs updates.** While `/var/lib/rog5-fex-turnip/enabled` exists (set
by `install`, removed by `restore`), `steam-fex-rootfs-install` runs
`steam-fex-turnip-8bit reapply` on the new root before swapping it in. Games
never see the stock driver after an update. If the new image has a different
Mesa, the root goes live unchanged and a warning is printed. Rebuild this
package for that Mesa: change the version and hashes in `build.sh` and
`BASE.SHA256SUMS`. The offline tests are in `scripts/device/test-steam-scripts.sh`.

### Steps

1. Host: copy the build and the two scripts. The updated
   `steam-fex-rootfs-install` carries the reapply hook.

        cd ~/.local/state/rog5-mesa-fex && tar -cf - r1 | ssh root@PHONE 'mkdir -p /var/cache/rog5-fex/turnip && tar -C /var/cache/rog5-fex/turnip -xf -'
        scp scripts/device/steam-fex-turnip-8bit scripts/device/steam-fex-rootfs-install root@PHONE:/usr/local/bin/

2. Optional, before installing, as `phone`. This loads the new driver in FEX
   through `VK_DRIVER_FILES` and changes nothing:

        F=~/.local/share/Steam/steamapps/common/FEX-Emu/usr/bin/FEX
        D=/var/cache/rog5-fex/turnip/r1
        printf '{"ICD":{"api_version":"1.4.354","library_path":"%s"},"file_format_version":"1.0.1"}\n' $D/usr/lib/libvulkan_freedreno.so >/tmp/tu8-64.json
        printf '{"ICD":{"api_version":"1.4.354","library_path":"%s"},"file_format_version":"1.0.1"}\n' $D/usr/lib32/libvulkan_freedreno.so >/tmp/tu8-32.json
        export FEX_ROOTFS=/usr/share/guestos/fex-mesa tu_override_uncached_as_cache_coherent=true
        cd $D/s8test
        VK_DRIVER_FILES=/tmp/tu8-64.json $F ./s8test.x86_64 features   # expect: all DXVK 3.1 required features present
        VK_DRIVER_FILES=/tmp/tu8-64.json $F ./s8test.x86_64 run 10     # expect: RESULT ... 0 mismatches -> PASS
        VK_DRIVER_FILES=/tmp/tu8-64.json $F ./s8test.x86_64 run 2 1 s8rmw.spv   # control: must end in FAIL
        VK_DRIVER_FILES=/tmp/tu8-32.json $F ./s8test.i686 features
        VK_DRIVER_FILES=/tmp/tu8-32.json $F ./s8test.i686 run 10

   As a control, the same `features` run without `VK_DRIVER_FILES` (the guest
   driver) should print `MISSING storageBuffer8BitAccess`. This runs FEX
   directly (default FEX config, no pressure-vessel container), with the root
   and the Turnip override that `fex-compat-tool` sets; the game path in step 4
   is the one that counts.

3. Quit Steam, then install:

        sudo steam-fex-turnip-8bit install /var/cache/rog5-fex/turnip/r1
        steam-fex-turnip-8bit status

4. Start BioShock Remastered with Proton Experimental and the launch option
   `PROTON_LOG=1 %command%`. In `~/steam-409710.log`, expect DXVK 3.1.x to
   list `Turnip Adreno (TM) 660` with no `Skipping: ... storageBuffer8BitAccess`
   line and no `DXVK: No adapters found`.

5. To undo: `sudo steam-fex-turnip-8bit restore` (with Steam closed).

## Alternatives

- **Vulkan thunk.** `STEAM_COMPAT_FEX_CONFIG=ThunksDB_Vulkan:1` would route
  64-bit x86 Vulkan to the phone's patched aarch64 driver. That helps 64-bit
  games only (there is no 32-bit thunk), and FEX's thunks are less tested than
  the guest Mesa.
- **Drop the package.** Remove it when a FEX image ships a Mesa whose Turnip
  exposes 8-bit storage on a6xx.
