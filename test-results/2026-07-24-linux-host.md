# Native Linux host result

Status: **PASS** for build and local USB-link preparation; **PENDING** for a
fastboot-mode device and live recovery boot.

## Host checks

- Nobara Linux 44 runs the repository from native Btrfs.
- Rootless Podman 5.8.4 built and verified recovery v12 with networking
  disabled.
- Fedora/Nobara `android-tools` 35.0.2 supplies `adb` and `fastboot`.
- The development user is listed in `dialout`. The current desktop process
  predates that change, but `sg dialout` proves read/write access to
  `/dev/ttyACM0`; a new login will inherit it normally.
- `recovery-v12-linux.sh` passes a fake-device positive preflight, rejects an
  absent fastboot target, rejects an unmanifested image, and refuses to invoke
  boot without `ALLOW_TEMPORARY_BOOT=1`.

## Connected fallback

- USB NCM and ACM enumerate as gadget `1d6b:0104`.
- The NCM carrier is up.
- A non-autoconnecting host profile assigns `169.254.77.1/16` only to the USB
  link.
- The fallback server responds at `169.254.77.2` with zero packet loss over
  three probes, and TCP/22 is reachable.
- The current ACM endpoint produced no shell data during a bounded probe.
- Neither ADB nor fastboot currently lists a device.

No credential was used, no partition was mounted or written, and the phone was
not rebooted during these checks.
