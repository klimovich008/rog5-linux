# Eden (Nintendo Switch emulator) for the ROG5

AUR `eden` 0.2.1-3 (Eden v0.2.1, source pinned by SHA-256 from
git.eden-emu.dev), built natively on the phone with `makepkg` as the `phone`
user. Only change: `cubeb` is not in the Arch Linux ARM repositories, so it is
dropped from `depends` and Eden's CMake (CPM) builds its bundled copy.

    pacman -S --needed --asdeps <depends and makedepends from PKGBUILD>
    CMAKE_BUILD_PARALLEL_LEVEL=6 makepkg -f    # 6 jobs fit in the phone's RAM
    sudo pacman -U eden-0.2.1-3.1-aarch64.pkg.tar.*

Games, keys and firmware are the user's own; none are part of this package.
