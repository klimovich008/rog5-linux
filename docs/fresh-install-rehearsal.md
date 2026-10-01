# Fresh-install rehearsal (2026-09-30 to 10-01)

A from-scratch run of the PC side of the [install guide](install-guide.md)
on the reference PC (Steam Deck, SteamOS, x86_64, 8 threads, 15 GB RAM), as
a new owner would do it: no private state directories, no phone writes.
Work files were kept under `~/.local/state/rog5-fresh-install-rehearsal/`.
The phone was only read (inventory, package list, installed file hashes);
nothing on it was changed.

Result: **the root filesystem, the device profile, the RAM-map tool and the
wrapper packaging work from scratch; the first install on a new phone does
not**, because the pieces listed in the guide's opening table are missing.
Every failure found on the way is fixed in the repository unless marked
open.

## What ran

| Step (guide stage) | Result | Time | Notes |
|---|---|---|---|
| ALARM tarball download and signature (5) | PASS | 34 s | 829 MB, `VALIDSIG` by the ALARM build key `68B3537F…2BDBE6A6` |
| Unpack in a user namespace (5) | PASS | 21 s | `unshare --map-auto --map-root-user`; rootless Podman failed (see F1) |
| Keyring, `pacman -Syu` (5) | PASS after F2, F3 | 7 min 40 s | 71 packages upgraded |
| Package list (5) | PASS | 9 min 43 s | 587 installed, 736 in total, 6.2 GB |
| `gtk2` from `packages/gtk2` (5) | PASS after F4, F5 | 46 min + 7 min | `makepkg` with `-j8` under qemu-user: 170 CPU minutes |
| `phoc` (5) | PASS | 11 min | |
| `phosh` + `phosh-debug` (5) | PASS | 30 min | |
| `vulkan-freedreno` 26.2.3-1.1, 8-bit Turnip (5) | PASS | 38 min | |
| `resources` (Rust) (5) | not run | | left for the phone (`--skip-custom resources`) |
| Accounts: `phone` user, key-only root (5) | PASS | 2 s | `alarm` removed, root `!`-locked, one `ssh-ed25519` line, `sshd` enabled |
| Userspace, finalize, seal (5) | PASS after F9, F10 | 2 min | 85 files, units enabled offline, `rog5-kms-reset` compiled in the root; lower-root checks pass; seal verifies |
| First bundles + v2 selector, image (10) | PASS after F11 | 7 min | the installed `main-k111-d10-261001a` + fallback `production-7.2.7-safe-r8` (reference-signed, only copied); seal still verifies; 32 GiB ext4, `e2fsck -fn` clean |
| FEX guest root (`steam-fex-rootfs-install`, 12) | PASS after F6, F7 | 3 min 46 s | ArchLinux 2026-08-11 SquashFS, XXH3 checked, 4.4 GB, root-owned |
| Steam client (`steam-arm64-install`, 12) | PASS | 41 min | as `phone`: 35 packages SHA-256-checked, 2.4 GB, `steamrtarm64/steam` is an aarch64 ELF, `~/.steam/{root,steam}` links, launcher `steam-arm64.desktop`, nothing world-writable |
| Production ramdisk (9) | PASS | minutes | k111 inputs: HEAD `ed73c81f` reproduces the installed `main-k111-d10-261001a` ramdisk byte for byte; the profiled sources differ only in `init`, `rog5-p2-attest` and `rog5-persistent-state`; a 512 GB profile renders 1000204288 sectors, 118 nodes and a 418.3 GiB overlay limit into all three |
| Kernel: fetch v7.2.7, `--prepare-only` (4) | PASS | 3 min 18 s | `PREPARED`; the full build was not rerun (F8) |
| Device profile from the live phone (8) | PASS | seconds | `collect-script` (read-only) + `make` reproduce `configs/device-profiles/reference.env` exactly |
| Layout plan (7) | PASS | | reproduces the reference p23/p24 geometry from the stock layout |
| RAM map (9) | PASS | | reference DTB r9 consistent; a synthetic 8 GB map is refused because memx lies outside RAM; 16 GB accepted |
| Wrapper packaging (9) | PASS | minutes | `package-slotb-boot-wrapper.py` with the reference inputs, without and with a 512 GB profile; the second carries the rendered values in both the recovery init and the selector loader |

## Failures and fixes

- **F1 — rootless Podman cannot run aarch64 binaries** (`Exec format error`),
  although binfmt_misc has `qemu-aarch64` with the F flag. `unshare
  --map-auto --map-root-user` + `chroot` works. The builder uses that; the
  guide says so.
- **F2 — pacman's sandbox needs Landlock**, which qemu-user lacks (`restricting
  filesystem access failed`, `switching to sandbox user 'alpm' failed`). The
  builder passes `--disable-sandbox` under emulation only.
- **F3 — `could not determine cachedir mount point`** and a false "not enough
  free disk space": the chroot root must be a mount point. The builder
  bind-mounts it onto itself.
- **F4 — `makepkg` ran single-threaded** (ALARM's `makepkg.conf` has no
  `MAKEFLAGS`). The builder sets `-j$(nproc)`.
- **F5 — `install: cannot stat '/dev/stdin'`** in `gtk2`'s `package()`: the
  builder's private `/dev` lacked `stdin`/`stdout`/`stderr`. Fixed; this run
  repackaged the already built tree once by hand (`makepkg -R`) and installed
  it with `pacman -U`.
- **F6 — `/run/lock` missing** made `steam-fex-rootfs-install` fail in the
  chroot (a booted system has it). The script now creates the directory.
- **F7 — the FEX guest root was owned by the phone user.** The image stores
  its builder's uid 1000, which is `phone` on this system, so a desktop
  session could modify the x86 system libraries games load; the reference
  phone has this today (checked read-only). The installer now re-owns the
  root to `root` before publishing it (0 non-root files after the rerun).
  The reference phone keeps its user-owned copy until
  `steam-fex-rootfs-install` runs again there.
- **F9 — ALARM's `/etc/hostname` ("alarm") was kept** as a local edit by the
  userspace installer. A fresh root now installs conf files with `--force`.
- **F10 — `IgnorePkg` held packages the run had not patched** (gtk2 was
  missed after a manual repackage, `resources` was held at the stock
  version). Holds now follow the installed version: only a kept patched build
  is held. This rehearsal image still lists `resources` from the earlier run.
- **F11 — packaged bundles are 0500/0400**, so copying them into the staging
  area failed on the second bundle. The boot step copies contents only.
- **F8 — dtschema could not be installed on SteamOS**: building `pylibfdt`
  needs `Python.h`, which SteamOS's read-only image strips. The kernel build
  needs the schema tools, so on SteamOS use a Python with headers (the
  reference uses a separately built CPython 3.12) or build on another
  distribution. `--prepare-only` needs no schema tools and passed. The full
  build is covered by CI (`board-production`, Ubuntu 24.04).

Found by the reviews of the new tools (GPT-6.1-Sol, 2026-09-30 and 10-01) and
fixed before this report: a predictable temporary file in the installer,
`mkfs.ext4` punching holes into the fallocated overlay image (reproduced:
696 of 131072 blocks allocated after a default `mkfs.ext4`), the root image
UUID changing on every rebuild, the seal hash covering directory metadata the
builder changed afterwards, links in the phone user's home being followed as
root, and wrapper packaging not carrying the device profile.

## Root image

`~/.local/state/rog5-fresh-install-rehearsal/build-a/arch_root_a.ext4`:
34359717888 bytes (the reference p24), 12.2 GB used, of which the FEX guest
root (4.4 GB) and the Steam client (2.4 GB) were installed into this root for
the rehearsal; on a phone they go into the overlay after the first boot.
`root-identity.env` holds a 435-byte seal over 251287 entries, a 115615-byte
`ld.so.cache` and the systemd, sshd and `authorized_keys` hashes, all
different from the reference phone's: a root built today needs its own
device profile. Hostname `rog5`, the `phone` user with a PIN hash, root
`!`-locked with one SSH key, an empty pacman keyring and machine-id, no host
keys, `/boot/rog5-linux` 0755 with `bundles` 0700 and `selector` 0600.

Total time on the reference PC: about 3 h 30 min, 2 h 10 min of it the
patched packages under qemu-user.

## Not covered

- **Anything on a second phone.** No partitioning, flashing, first boot or
  bundle install was rehearsed; the missing pieces in the guide's opening
  table block them, and the reference phone was not to be written.
- **The pre-install environment, ramdisk base, firmware kits, recovery base,
  ASUS wrapper kernel and base DTB builds**: no builders exist.
- **A full kernel build** (F8); CI builds it.
- **`resources`** (Rust, hours under qemu-user); it builds on the phone in
  minutes.
- **Running Steam, Phosh or GNOME**: not meaningful under qemu-user.
- **Booting a bundle built with a non-reference profile**: needs a RAM trial
  on a phone with that layout.

## Gap list

Scripted and rehearsed now: the root filesystem (`rog5-build-rootfs`), the
userspace install (`rog5-install-userspace`, paths verified against the
reference phone), per-phone boot values (`rog5-device-profile`, boot sources
with profile blocks), RAM maps (`rog5-dtb-memory`), first bundles and
selector in the image, wrapper and bundle packaging for another profile and
recovery base, `/persist` creation (restored stager).

Still open, in the order a new install meets them:

1. A pre-install RAM environment for a new phone (recovery base with the
   owner's key + ASUS 5.4 kernel builder), to read the bootloader's RAM map,
   extract firmware and partition.
2. Builders for the ramdisk base (with ADSP firmware from the phone), the
   display firmware kit and the Wi-Fi kit.
3. A per-device partitioning executor (the archived one carries the
   reference GUIDs) and the allocated-RAW sparse converter.
4. The base DTB published or the composer rebased on the kernel-built DTB.
5. The trial-state helper built from `tools/persistent_trial_state` in the
   tree.
6. A bootstrap boot that works before `/persist` and the overlay exist.
7. Consumers that still expect the main UFS LUN to be `sda`
   (`install-default-kernel-on-target.sh`, `production-trial-commit`,
   `production-wifi`, `rog5-update`) and legacy paths with a literal 117 UFS
   nodes (native-Wi-Fi, local-image, RAM transaction).
8. A qualified RAM trial and try-once install of a bundle built from the
   profiled sources (reference profile first) before any of this reaches the
   reference phone.
