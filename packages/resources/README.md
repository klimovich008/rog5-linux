# resources (GNOME Resources) for the ROG Phone 5

Patched build of [Resources](https://gitlab.gnome.org/GNOME/Incubator/resources)
1.10.2 so it shows the SM8350 GPU and CPU correctly. `PKGBUILD` is the Arch Linux
packaging (1.10.2-1) with `aarch64` added, `pkgrel=1.1` and one patch.

## What the patch does

`0001-adreno-and-heterogeneous-cpus.patch` (against tag `v1.10.2`):

- GPU
  - New `Msm` GPU type for Qualcomm Adreno (`adreno` platform driver / `msm` DRM
    driver). Usage from `device/gpu_busy_percent` when present (kernel 0104),
    otherwise from per-process fdinfo. Frequency from the hwmon `freq1_input`,
    falling back to `device/devfreq/*/cur_freq`. Temperature from hwmon
    `temp1_input`, falling back to the maximum of the `gpu*thermal` thermal zones.
  - Non-PCI GPUs get a name from `device/of_node/compatible`
    (`qcom,adreno-660.1` -> "Qualcomm Adreno 660").
  - Non-PCI DRM cards without a render node (the DPU/MDSS display controller,
    card1) are no longer listed as GPUs.
  - GPU hwmon glob `hwmon/hwmon?` -> `hwmon/hwmon*` (hwmon numbers go above 9).
  - fdinfo: `drm-driver: msm` is parsed (`drm-engine-gpu` time,
    `drm-total-memory`), so per-app GPU usage and GPU memory work.
- CPU
  - `lscpu` prints one block per core type on big.LITTLE. All blocks are now
    parsed: name "4× Cortex-A55 + 3× Cortex-A78 + 1× Cortex-X1" (a single name
    when all cores match), cores summed (8 instead of 4), max speed = fastest
    type (2.84 GHz instead of 1.80 GHz). The lscpu regexes are anchored to line
    starts. Adds a unit test with the phone's lscpu output.
  - CPU temperature falls back to the maximum of the per-core/per-cluster thermal
    zones (`cpu*thermal`, `cluster*thermal`) when no known hwmon/zone exists
    (it showed nothing before).

## Rebuild (on the phone, as the `phone` user, never as root)

    pacman -S --needed rust appstream meson git       # as root, once
    cd /home/phone/build/resources/pkg                # copy of this directory
    makepkg -f                                        # runs the unit tests too
    sudo pacman -U resources-1.10.2-1.1-aarch64.pkg.tar.*

`/etc/pacman.conf` has `resources` in `IgnorePkg` (next to `phoc`) so a repo
update does not replace it. To move to a new upstream version, bump `pkgver`,
take the new upstream b2sum from the Arch packaging repo
(gitlab.archlinux.org/archlinux/packaging/packages/resources), and refresh the
patch.
