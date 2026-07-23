# Current state — 2026-07-23

## Hardware and boot

- Device: ASUS ROG Phone 5, codename `anakin`, SM8350 / Snapdragon 888, Adreno 660.
- Bootloader: unlocked; verified boot reports orange.
- Active Android slot during the recorded tests: slot B.
- Linux root: Alpine 3.24 on the userdata-backed root filesystem.
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

The header-v3 ASUS 5.4.210 staging kernel now boots temporarily and provides
authenticated USB NCM/SSH recovery. The live gates verify its kernel identity,
payload manifest, rollback timer, and zero storage mounts. A global `set -e`
in the recovery init was the cause of the earlier immediate fallback; optional
vendor-module failures are now logged without aborting recovery.

Both legacy `kexec_load` and `kexec_file_load` accept exact self-kexec and Linux
7.1 payloads. Execution still fails before the target USB/SSH recovery
interface appears. The only live watchdog is the Haven hypervisor watchdog;
disabling it succeeds. With that watchdog disabled and `panic=0`, the phone
remains nonresponsive instead of returning to fallback, and `reset_devices`
does not change the result.

A 4 MiB unused ASUS debug reservation is now used temporarily by the standard
ramoops driver. The current attended test is waiting for its preserved record
to be read after a forced restart into fastboot. Linux 7.1, its recovery DTB,
and the mainline GPU tier have therefore not passed a hardware boot gate yet.
