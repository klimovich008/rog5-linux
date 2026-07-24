# Current state — 2026-07-24

## Hardware and boot

- Device: ASUS ROG Phone 5, codename `anakin`, SM8350 / Snapdragon 888, Adreno 660.
- Bootloader: unlocked; verified boot reports orange.
- Active Android slot during the recorded tests: slot B.
- Stable 5.4 baseline userspace: Alpine 3.24 on the userdata-backed root filesystem.
- Target userspace: Arch Linux ARM with systemd and minimal Plasma. The locked
  archive passed its historical suite but contains the previous module set;
  restaging with the accepted kernel is mandatory before first boot.
- Stable experimental kernel: `5.4.210-qgki-perf #20`.
- Boot method: temporary `fastboot boot`; the experimental kernel has not been flashed.

## Passing baseline

The 5.4.210 #20 smoke test currently passes:

- UFS root and initramfs startup
- USB NCM and SSH at the private debug address
- DSI DRM connector and panel backlight
- FocalTech touch input
- ADSP startup and the real Qualcomm battery charger driver
- native UPower battery reporting
- Plasma Mobile on the physical panel using software rendering
- power-button screen toggle and default OLED blanking
- Wi-Fi client and AP/hotspot after delayed radio startup
- modem stability with supervised `rmtfs` and patched `tqftpserv`

At the last baseline capture the battery was full, the panel backlight was zero, zram was 3 GiB and unused, and the server remained reachable with the physical screen off. The screen toggle now applies Wayland DPMS as well as backlight zero, and restores DPMS plus the saved brightness on wake.

## Display modes

The vendor DRM connector publishes these mode names:

```text
1080x2448x144x150024cmd
1080x2448x120x150003cmd
1080x2448x90x150007cmd
1080x2448x60x138333cmd
```

The mode names encode the intended 144/120/90/60 Hz panel profiles. Generic `modetest` calculates misleading refresh values because the vendor command-mode timings are not conventional desktop timings. The connector capability blob explicitly reports no qsync, dynamic FPS, or dynamic bit-clock support, so the safe UI is a fixed-mode selector. The low-power default should be 60 Hz; 90 Hz is the balanced interactive profile; 120/144 Hz should be opt-in.

The live KScreen mapping is verified as 144 -> ID 1, 120 -> ID 2, 90 -> ID 3, and 60 -> ID 4. The current default is the 60 Hz server profile with DPMS off.

## GPU blocker

The extracted A660 firmware loads and Mesa 26.1.1 Turnip can identify `Turnip Adreno (TM) 660` on a fresh boot. It is not stable.

Reproducer:

1. First raw `O_RDWR` open of `/dev/kgsl-3d0` succeeds.
2. Close it.
3. A second raw open fails with `ETIMEDOUT`.
4. Kernel log reports GMU HFI error `115 902 PwrLimitsExitIdl` and a CP read-translation page fault at a varying low address.

The same failure occurs on 5.4.134 and 5.4.210 #20. It remains with ACD, BCL, and IFPC disabled and with rail/clock/bus/no-nap debug forces enabled. This proves the current blocker is the vendor KGSL/GMU open/idle transition, not KDE, Zink, Xvnc, or a Turnip command submission.

GPU tests are intentionally a separate opt-in tier because the failure poisons KGSL until reboot.

## Desktop and RAM

- Plasma Mobile, Plasma Desktop, Plasma NetworkManager, Discover, and the Alpine APK backend are installed.
- The physical session currently forces Qt Quick and OpenGL software rendering.
- noVNC/Xvnc is also a software path and should remain an emergency/admin interface, not the GPU validation target.
- Repaired localhost-only remote-session launchers are installed. The nested KDE/Chromium session remains stopped during the thermally limited native kernel compile.
- Recorded memory usage was about 0.85 GiB without the full physical UI and about 1.4 GiB with Plasma Mobile, radio services, and caches active. The device has roughly 11 GiB usable RAM, so reliability and idle power matter more than aggressive memory trimming.

## Known operational constraints

- Radio startup is delayed to avoid a low-battery boot power spike.
- The current vendor kernel has BPF and uprobes but no `/sys/kernel/btf/vmlinux`; GodShell cannot run its CO-RE eBPF programs on this baseline.
- The boot image is not persistent. Any normal reboot returns to the installed fallback kernel.
- PC cross-compilation is active on Nobara Linux under rootless Podman. Linux
  7.1.4 and the ASUS-source 5.4.210 kexec staging kernel both compile
  reproducibly with container networking disabled.
- The connected fallback system enumerates as USB gadget `1d6b:0104` and
  `/dev/ttyACM0`. Android platform tools 35.0.2 are installed and the user is
  configured in `dialout`; the current desktop login has not refreshed that
  supplementary group, but a temporary group shell verifies access.
- A non-autoconnecting host-only USB profile at `169.254.77.1/16` reaches the
  fallback server at `169.254.77.2`; ICMP and TCP/22 pass. After explicit
  approval, the recovery key was copied only to host tmpfs and used for
  read-only fallback inspection and the authorized reboot to fastboot.
- Credentials and private identifiers are deliberately excluded from this repository.

## Mainline recovery status

The historical header-v3 v2 image temporarily booted and produced staging and
target logs. Those logs include Linux 7.1.4 entering `/init`, mounting
configfs, configuring NCM and ACM, binding the `a600000` UDC, creating `usb0`,
and later returning through rollback. Ramoops from that run also supported the
TLMM GPIO 52-59 reservation and built-in Qualcomm SNPS FEMTO USB2 PHY changes.
These remain useful historical observations, not a passing recovery gate.

A later live and artifact audit found that the v2 staging `/` was a writable
physical UFS filesystem. Its target DTB also enabled the UFS controller, UFS
PHY, and QMP/SuperSpeed PHY. The earlier “zero storage mounts” and USB2-only
claims were therefore false. Nothing was flashed, but every v2 boot artifact
is superseded and must not be booted again.

The later v6 candidate embedded the staging initramfs in the ASUS 5.4 kernel
and carried a USB2-only target DTB with UFS, QMP/SuperSpeed, and the secondary
USB controller disabled. It passed its then-current offline suite, but live
ACM data and automatic rollback failed. Later source fixes supervise ACM and
use repeated forced-reboot fallback.

Recovery v12 was rebuilt reproducibly but remained unbooted after a final
safety audit found that it did not lock block devices before USB exposure.
Recovery v13 added an all-block-device `BLKROSET` gate and passed duplicate
offline builds. Its first `fastboot boot` transfer succeeded, but the exact
recovery USB identity never appeared; the known fallback gadget returned 21
seconds after fastboot disconnected. No intervening recovery USB product was
recorded, no image was flashed, and kexec was not attempted. V13 is rejected.

Recovery v14 retains the pre-USB rejection of any block-backed mount but locks
only physical disks and their partitions. This covers seven fallback-visible
UFS LUNs and 109 partitions while excluding 33 volatile loop, RAM, and zram
objects. Both initramfs layers, two fresh ASUS wrapper builds, and two
header-v3/AVB repacks are byte-identical. The expanded `acm-only` verifier
passes, and the host now requires exact product `ROG5_recovery` rather than
accepting the shared vendor/product ID. Its live attempt still returned to
fallback after the same 21-second interval, so v14 is rejected and no live
recovery gate is accepted.

Recovery v15 is a reproducible diagnostic-only image. It keeps USB closed on
failure and adds 10/30/50-second rollback delays for PM wake-lock failure,
block-backed mount detection, and physical-device lock failure respectively.
Its live temporary boot returned to fallback in exactly 31 seconds, proving
that `/init` ran and the wake-lock branch failed before storage isolation.
Kexec was not loaded or executed.

Recovery v16 removes the wake-lock gate and timing-only delays. The wrapper
configuration has `CONFIG_PM_AUTOSLEEP` disabled, and the initramfs has no
userspace power manager, so no automatic suspend path needs that lock. The
forced-reboot watchdog, block-backed-mount rejection, physical-device
`BLKROSET` verification, USB-closed failure paths, and exact host identity
check remain. V16 reached exact recovery USB, working NCM, and automatic
rollback to a changed fallback boot, but ACM returned no bytes.

The separately authorized local v17 SSH diagnostic proved a RAM-backed
`rootfs`, zero block-backed mounts, 116 physical disks/partitions read-only,
and live watchdog/ACM supervisor processes. Its configfs ACM function exposed
`/sys/class/tty/ttyGS0`, but `/dev/ttyGS0` was absent. A live RAM-only
`mdev -s` created the node and the supervised ACM shell worked immediately.
The diagnostic then rolled back automatically; it was never published and
kexec was not attempted.

Recovery v18 adds that explicit rescan, requires the character node, and
repeats storage isolation before ACM or UDC binding. Both initramfs layers,
two independent ASUS wrapper builds, and two boot-image repacks are
byte-identical; the strengthened network-isolated verifier passes. Two live
credential-free staging/rollback cycles also pass: both reported RAM root,
zero block mounts, 116 read-only physical nodes with zero failures, live
watchdog/ACM, no authorization or SSH, configured NCM, and automatic return to
a changed fallback boot identity. A subsequent attended kexec loaded the
hash-verified payload and booted `7.1.4-g7a5cef0db479`. The target again passed
RAM root, zero block mounts, zero physical block devices, watchdog/ACM/NCM,
no-credential/no-SSH, and zero fatal-log-signature checks before automatically
returning to a changed fallback boot identity. The next gate is read-only UFS
discovery.

The read-only UFS discovery v1 bundle passed its complete offline gate and
then safely reached Linux `7.1.4-g44fd886a77b8` through temporary boot and
kexec. It enumerated 7 UFS disks and 109 partitions with all 116 physical
nodes independently read-only, a RAM root, zero block-backed mounts, the
Qualcomm host bound, and recovery USB/watchdog services live. The live gate
was rejected because runtime PM attempted three auto-BKOPS `SET_FLAG`
queries. The compile-time command gate blocked every query, but the resulting
UFS fatal-recovery state also stalled orderly reboot. An authorized SysRq
reset returned the phone to the exact fallback kernel; no storage was mounted,
written, or flashed.

The three-patch replacement source at commit `cfd385a1c754` / tree
`d2f03d205522` retains the UFS runtime reference, forbids host and WLUN
runtime PM, disables auto-hibern8, and returns before discovery suspend or
shutdown transitions. Its patch/config/object verifier passes. The next gate
is two clean mainline builds, two clean ASUS wrapper builds, complete
network-isolated bundle verification, and only then another attended
temporary boot requiring zero blocked queries and orderly rollback.

The raw ramoops reader and bootloader restart-reason helper remain under
`tools/diagnostics/`.
