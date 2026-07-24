# Native Linux host result

Status: **PASS** for build, local USB, real fastboot preflight, and safe
fallback return; **REJECTED** for the v13 and v14 live recovery identities;
**PENDING** for the v15 timing diagnostic.

## Host checks

- Nobara Linux 44 runs the repository from native Btrfs.
- Rootless Podman 5.8.4 built and verified recovery v15 with networking
  disabled.
- Fedora/Nobara `android-tools` 35.0.2 supplies `adb` and `fastboot`.
- The development user is listed in `dialout`. The current desktop process
  predates that change, but `sg dialout` proves read/write access to
  `/dev/ttyACM0`; a new login will inherit it normally.
- `recovery-linux.sh` passes a fake-device positive preflight, rejects an
  absent fastboot target, rejects an unmanifested image, and refuses to invoke
  boot without `ALLOW_TEMPORARY_BOOT=1`.
- The detector now requires `ID_MODEL=ROG5_recovery` and rejects the Alpine
  fallback gadget even though both intentionally share `1d6b:0104`.

## Connected fallback

- USB NCM and ACM enumerate as gadget `1d6b:0104`.
- The NCM carrier is up.
- A non-autoconnecting host profile assigns `169.254.77.1/16` only to the USB
  link.
- The fallback server responds at `169.254.77.2` with zero packet loss over
  three probes, and TCP/22 is reachable.
- The approved recovery key works against the fallback server from a
  mode-0600 host tmpfs copy.
- The authorized helper successfully rebooted to exactly one fastboot target.

## V13 live attempt

- The manifest-pinned image passed the real preflight and `fastboot boot`
  completed without flashing.
- No exact recovery USB product appeared. The fallback gadget returned 21
  seconds after fastboot disconnected.
- A VID/PID-only detector initially misidentified that fallback ACM endpoint;
  direct kernel/root/marker inspection caught the error immediately.
- Kexec was not loaded or executed.
- Standard pstore had no retained record; an older unguarded diagnostic module
  was deliberately not loaded.

V14 repeated the same exact result: fallback returned 21 seconds after
fastboot disconnected with no recovery product. V15 is limited to one
USB-closed timing measurement and cannot proceed to kexec.

The credential was not copied into the repository or recovery image. No
partition, filesystem, slot, or persistent boot state was intentionally
written.
