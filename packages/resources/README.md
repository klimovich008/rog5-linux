# resources (GNOME Resources) for the ROG Phone 5

Patched build of [Resources](https://gitlab.gnome.org/GNOME/Incubator/resources)
1.10.2 so it shows the SM8350 GPU and CPU correctly, hides unused firmware
UFS LUNs and monitors the separate Qualcomm Iris video engine. `PKGBUILD` is
the Arch Linux packaging (1.10.2-1) with `aarch64` added, `pkgrel=1.3` and
three patches.

## What the patches do

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

`0002-hide-udisks-ignored-drives.patch` (on top of 0001):

- Drives
  - A block device whose udev database entry (`/run/udev/data/b<MAJ>:<MIN>`)
    has `E:UDISKS_IGNORE=1` is left out of the drive list, the same hint
    udisks/Nautilus/GNOME Disks use to hide it. The initramfs sets it on every
    `sd*` (`/run/udev/rules.d/10-rog5-p2-storage.rules`) and udisks sets it on
    `ram*`/`zram*`.
  - Exception: an ignored drive stays listed while it is in use, i.e. the
    disk or one of its partitions is a mount source (by `MAJ:MIN` or
    `/dev/<name>` in `/proc/self/mountinfo`), is an active swap area
    (`/proc/swaps`) or has holders (dm/md). So the main UFS LUN `sda`
    (236 GiB; `sda23`/`sda24` back the root overlay) is still shown with its
    I/O, while the unmounted read-only LUNs `sdb`..`sdg` (8 MB x3, 2.3 GB,
    32 MB x2) are hidden. Unit tests use the phone's mount layout.

`0003-qualcomm-video-engine.patch` (on top of 0001 and 0002):

- Adds a **Video engine** sidebar entry beside the GPU, with a busy-percentage
  graph, **Active/Idle** state, **Codecs** (decoder/encoder nodes present) and
  **Current users** (application/process names and PIDs).
- Discovers `/sys/class/video4linux/video*/device/driver` named `qcom-iris` or
  `qcom-venus`, including a platform driver on an ancestor device. Groups the
  nodes by their codec device, so decoder and encoder share one page. The
  entry appears only when matching nodes exist and disappears when removed.
  Node roles come from the V4L2 `name`, e.g. `qcom-iris-decoder`; the Codecs row
  lists available node roles, not supported formats or enabled codec sessions.
- Reads the codec device's `power/runtime_status`, `runtime_active_time` and
  `runtime_suspended_time`. On SM8350 this is
  `/sys/bus/platform/devices/aa00000.video-codec/power/`. Busy percentage is
  `100 × Δactive / (Δactive + Δsuspended)` between refreshes. It measures
  runtime-PM residency, including autosuspend delay, rather than throughput or
  separate encode/decode utilization. State is Active for `active`, Idle for
  `suspended`; transient or unreadable states show N/A. The first sample,
  missing/reset counters or a zero-length interval show N/A for busy usage.
- Scans readable `/proc/<pid>/fd` symlinks for `/dev/videoN` once per refresh,
  in the existing background worker. Uses Resources' application names when
  available, then process names, with `/proc/<pid>/comm`/`exe` as fallbacks.
  Multiple matching fds count once per process per engine. Permission errors
  and processes exiting during a scan are skipped; **None detected** is best
  effort. The scan only reads symlinks and never opens a video device or wakes
  it to probe formats. No root or privileged helper is required.

## Validation (host, 2026-10-02)

The series applies to upstream `v1.10.2`. The new data reader compiles in a
standalone test harness using cached Rust 1.75 and a standard-library
replacement for `read_parsed`; all three tests pass (runtime counter deltas
and resets, Iris/Venus grouping and power discovery, best-effort fd scanning
and deduplication). The complete GResource bundle compiles and the new UI XML
passes `xmllint`.

**The full application was not compiled.** `cargo check --locked` could not
run (`cargo: command not found`); this host also lacks GTK4/libadwaita
development packages and the required Rust ≥1.85 toolchain. The standalone tests do not
validate GTK/Rust integration. `makepkg` on the phone builds that integration
and runs the included tests. No phone access or installation was performed.

## Rebuild (on the phone, as the `phone` user, never as root)

    pacman -S --needed rust appstream meson git       # as root, once
    cd /home/phone/build/resources/pkg                # copy of this directory
    makepkg -f                                        # as phone; runs the unit tests too
    sudo pacman -U resources-1.10.2-1.3-aarch64.pkg.tar.*

Restart Resources after installing. On Iris/Venus systems the Video engine
entry should appear after the first refresh, with a busy graph after the
second. During hardware video use it should show Active and any readable
processes holding a node; after autosuspend it should settle to Idle and 0%.
Systems with no matching V4L2 device get no entry.

`/etc/pacman.conf` has `resources` in `IgnorePkg` (next to `phoc`) so a repo
update does not replace it. To move to a new upstream version, bump `pkgver`,
take the new upstream b2sum from the Arch packaging repo
(gitlab.archlinux.org/archlinux/packaging/packages/resources), and refresh the
patch series and checksums.
