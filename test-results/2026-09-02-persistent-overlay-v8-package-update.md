# Persistent-overlay V8 package update

Result: **PASS** after two fail-closed pre-commit package checks and one
post-update userspace idempotence fix.

- Boot: `5cec9d09-2491-4ca7-a72e-3c276727667b`.
- Bundle: `persistent-native-root-wifi-overlay-v8`.
- Pre-update inventory: 152 packages, SHA-256 `13586291…251f8b`.
- Post-update inventory: 163 packages, SHA-256 `032f6e00…47de1a`.
- Added tools: Python 3.14.7, Git 2.55.0 and tmux 3.7c.

Pacman 7 initially refused before download because the live kernel lacks
`CONFIG_SECURITY_LANDLOCK`. The target retains `CONFIG_SECCOMP=y`,
`CONFIG_SECCOMP_FILTER=y`, `DownloadUser = alpm`, and now uses only pacman's
documented `DisableSandboxFilesystem` compatibility exception. Future
persistent-root builds require `CONFIG_SECURITY_LANDLOCK=y`; no kernel was
rebuilt or booted here. Failure class: R3.

The first retrieval timed out on two mirror objects and committed nothing. The
second attempt downloaded every object but committed nothing because local GPG
ownertrust for the exact repository signer
`68B3537F39A313B3E574D06777193F152BDBE6A6` was absent. Repopulating the
installed `archlinuxarm` keyring restored its repository-owned trust value.
A download-only full-upgrade then verified all 73 package signatures before
the real transaction.

The named systemd transaction completed in 48.115 seconds with 890.8 MiB peak
memory. It upgraded 73 packages, including systemd and OpenSSH, with zero
pending updates afterward. P24 remained read-only; exactly `sda` and `sda23`
remained writable; battery stayed Full/Good at 29.9 C; and no fatal kernel,
ext4 or UFS signature appeared.

The systemd package hook re-enqueued the already-accepted Wi-Fi health oneshot.
Wi-Fi reacquired the same lease in about six seconds, but the health script
failed after `already-healthy` because its rollback timer units were already
disarmed/unloaded and its exact healthy record already existed. A fail-first
fixture now proves that a same-boot `already-healthy` rerun accepts only
inactive timers and an exact root-owned record. A fresh boot without that
record must still disarm both timers before creating it, and a first commit
still refuses a missing timer. The final script (`e9d0169c…f7584`) was
hot-deployed to `/run` and passed an explicit rerun; systemd returned to
`running` with zero failed units. Failure class: R7.

Observation evidence:

- 140 consecutive pre/update samples over 25m40s had zero NCM, Wi-Fi, SSH,
  storage or kernel failures; the deliberate package load peaked at 56.7 C.
- The observer then classified the transient missing Wi-Fi address before the
  six-second DHCP recovery and stopped fail-closed.
- A separate post-fix soak passed 60/60 samples over 11m42s with zero failures,
  29.9 C battery temperature and 34.5–37.8 C thermal samples.
- Private log hashes: original `1f23d08b…4b558`, post-update
  `74851b83…4097a`, package commit `d397cf97…54fde`.

Final focused tests passed in 3.440 seconds and the active tier in 4.008
seconds. Full local CI covering the kernel/config checkpoint passed in 476.020
seconds; the final target-only state-machine tightening used the active tier as
required by repository policy. The existing V8 signed bundle does not yet
contain the health-script fix, and the live kernel does not yet contain
Landlock; those source changes take effect with a future rebuilt target.
