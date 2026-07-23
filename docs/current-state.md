# Current state — 2026-07-23

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
- PC cross-compilation is active in Docker. Linux 7.1.4 and the ASUS-source 5.4.210 kexec staging kernel both compile successfully on the PC.
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
ACM data and automatic rollback failed. Source fixes now supervise ACM and
hold a timed wake lock with repeated forced-reboot fallback. A fresh Linux
7.1 build exists, but the target/staging initramfs, ASUS wrapper, boot image,
hash pins, and complete verifier have not been rebuilt. There is no current
boot candidate. The raw ramoops reader and bootloader restart-reason helper
remain under `tools/diagnostics/`.
