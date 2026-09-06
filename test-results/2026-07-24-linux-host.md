# Native Linux host result

Status: **PASS** for build, local USB, real fastboot preflight, and safe
fallback return; **REJECTED** for the v13 and v14 live recovery identities;
**PASS** for the v15 diagnosis and v17 live storage/ACM diagnosis;
**PARTIAL** for v16; **PASS twice** for v18 staging/rollback and **PASS** for
one attended Linux 7.1 target/rollback gate.

## Host checks

- Nobara Linux 44 runs the repository from native Btrfs.
- Rootless Podman 5.8.4 built and verified recovery v18 with networking
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
fastboot disconnected with no recovery product. V15 then returned in exactly
31 seconds, selecting the USB-closed wake-lock failure branch and proving
`/init` ran before storage isolation. V16 removed that gate, then passed exact
USB, NCM, and automatic rollback but returned no ACM shell data. The
authorized local v17 SSH diagnostic proved RAM root, zero block mounts, all
116 physical nodes read-only, and a working watchdog. It isolated ACM to the
missing `/dev/ttyGS0` node and proved a live `mdev -s` rescan fixes it. V18
implements that rescan plus a second storage gate and passes duplicate offline
builds. Two credential-free v18 cycles then passed exact USB, ACM/NCM,
RAM-root, zero-block-mount, 116-device read-only, watchdog, no-SSH, and
automatic changed-boot fallback checks.

The subsequent attended loader verified all nested hashes, loaded without
executing, and reported `kexec_loaded=1`. A separate `kexec -e` booted
`7.1.4-g7a5cef0db479`; the target passed RAM root, zero block-backed mounts,
zero physical devices, watchdog/ACM/NCM, no-credential/no-SSH, host
reachability, zero fatal-log signatures, and automatic changed-boot fallback.

The private credential was not copied into the repository, logs, or any
recovery image. Only its public key entered the local never-publish v17
diagnostic. No partition, filesystem, slot, or persistent boot state was
intentionally written.
