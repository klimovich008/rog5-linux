# Installing ROG5 Linux on an ASUS ROG Phone 5 (alpha)

This guide takes a stock ASUS ROG Phone 5 (ZS673KS, Snapdragon 888 /
SM8350) to the system described in the [README](../README.md): mainline Linux
7.2.7 with Arch Linux ARM, Phosh on the phone, GNOME "desktop mode" on an
external monitor, and Steam.

> [!IMPORTANT]
> **The alpha cannot yet be installed on another phone by following this
> guide.** One phone runs it (the "reference phone", a 12 GB / 256 GB
> ZS673KS). What you build on your PC is scripted, and a from-scratch run of
> it is recorded in the [rehearsal report](fresh-install-rehearsal.md):
> kernel, root filesystem, device profile, RAM map, signed bundles and the
> slot-B wrapper image. The *first* install on a new phone is blocked by
> these missing pieces:
>
> | Missing piece | What it is | Where it is today |
> |---|---|---|
> | Pre-install environment | a RAM-booted Linux on the phone (`fastboot boot`, nothing flashed) with *your* key, to read the bootloader's RAM map, extract firmware, format and partition, and create `/rog5` and `/persist` | the reference used recovery wrappers built from the pieces below |
> | Recovery base | the wrapper's ramdisk: BusyBox, kexec, `rog5-bundle-verify` and your public key | archived builder `scripts/device/build-stable-recovery-initramfs.sh` in tag `archive/pre-cleanup-2026-09-29`, plus pinned Alpine packages |
> | ASUS 5.4 wrapper kernel | built from ASUS's GPL source and `patches/asus-5.4.210` | archived builder scripts (same tag) |
> | Ramdisk base | the boot bundle's ramdisk base: BusyBox userland, kexec, power/USB loaders and the ADSP firmware from the phone | a private file (`bundle-inputs.json` `ramdisk_base`); no builder |
> | Display firmware kit | A660 SQE and zap shader, SLPI images (from the phone) and `a660_gmu.bin` | assembled by hand; no builder |
> | Wi-Fi kit | WCN6855 firmware and board data (from the phone), `wpa_supplicant`, `iw` | no builder |
> | Base DTB | the "V9" `board.dtb` the DTB composer starts from | a private file, pinned by hash |
> | Trial-state helper | `artifacts/persistent-trial-state-vN/` (executable + `SHA256SUMS`) the wrapper embeds | built locally, not in Git |
> | Partitioning executor | format, shrink userdata, write the GPT with p24 | archived, carries the reference phone's GUIDs |
> | Sparse image converter | "allocated-RAW" sparse image for `fastboot flash arch_root_a` | archived `scripts/host/build-ext4-allocated-raw-sparse.py` |
> | Bootstrap boot | a first boot that works before `/persist` and the overlay exist | not defined: every current bundle needs `/persist` |
>
> Each step below is marked **scripted**, **manual**, **missing**
> (knowledge only in history or private files) or **your phone** (needs
> material read from your own phone). Stages 0-5 run today. Stages 6-10
> describe how the reference phone was installed; until the missing pieces
> are published, **do not unlock or erase your phone for this project.**
>
> `scripts/host/rog5-device-profile`, `scripts/host/rog5-dtb-memory` and the
> overlay cap derived from the userdata size (stage 8, variants) belong to
> the device-profile change on branch `agent/install-guide-20261001`
> (commit `99620823`). It changes the boot path and is merged only after a
> trial boot on the reference phone; until then those commands are not in
> this branch.

- [What you need](#what-you-need)
- [Variants](#variants)
- [Warnings](#warnings)
- [Overview and time](#overview-and-time)
- [Stage 0: prepare the PC](#stage-0-prepare-the-pc)
- [Stage 1: record your phone and keep stock firmware](#stage-1-record-your-phone-and-keep-stock-firmware)
- [Stage 2: unlock the bootloader](#stage-2-unlock-the-bootloader)
- [Stage 3: your signing key](#stage-3-your-signing-key)
- [Stage 4: build the kernel](#stage-4-build-the-kernel)
- [Stage 5: build the root filesystem](#stage-5-build-the-root-filesystem)
- [Stage 6: pre-install environment and firmware](#stage-6-pre-install-environment-and-firmware)
- [Stage 7: format and partition (destructive)](#stage-7-format-and-partition-destructive)
- [Stage 8: your device profile](#stage-8-your-device-profile)
- [Stage 9: DTB, bundles and the slot-B wrapper](#stage-9-dtb-bundles-and-the-slot-b-wrapper)
- [Stage 10: first install and first boot](#stage-10-first-install-and-first-boot)
- [Stage 11: set up the phone](#stage-11-set-up-the-phone)
- [Stage 12: Steam](#stage-12-steam)
- [Updates, fallback and recovery](#updates-fallback-and-recovery)
- [Troubleshooting](#troubleshooting)
- [Step inventory](#step-inventory)

## What you need

- An **ASUS ROG Phone 5, model ZS673KS** (the 5, 5 Pro and 5 Ultimate all
  carry this model number; see [Variants](#variants)). Not the ROG Phone 5s
  (ZS676KS) or any other model.
- The phone's **slot A running ASUS stock firmware WW-33.0210.0210.200**
  (an Android 13 build for the WW SKU): the firmware scripts locate
  `vendor_a` at that build's position inside `super` and check files
  against its hashes.
- A **Linux PC** (x86_64 or aarch64) with about **60 GB free** on a real disk
  (not tmpfs), 8 GB RAM or more, internet access, and subordinate user and
  group ids for your user (`/etc/subuid`, `/etc/subgid`). The reference PC is
  a Steam Deck (SteamOS, 8 threads). Root is needed only to install packages.
- A **USB-C data cable** for the phone's side port (the one next to the
  accessory connector): fastboot, the phone's USB network and SSH use it.
- A **charger**. The on-phone storage steps refuse to run unless the phone
  is charging, cool and its battery voltage is at least 8.4 V (nearly full).
- Optional: a USB-C hub with HDMI/DP, keyboard and mouse for desktop mode.

Keep private and never publish: your signing key, inventories, `getvar all`
output, GPT backups, the root image (it carries your SSH key and password
hash) and your device profile.

## Variants

| Model | RAM / storage | Status |
|---|---|---|
| ROG Phone 5 (ZS673KS) | 12 GB / 256 GB | **The reference phone** (one 236 GiB UFS LUN, 11.86 GiB mapped RAM) |
| ROG Phone 5 (ZS673KS) | 8 GB / 128 GB, 16 GB / 256 GB | Unqualified bring-up target |
| ROG Phone 5 Pro (ZS673KS) | 16 GB / 512 GB | Unqualified bring-up target; the rear "ROG Vision" display has no driver |
| ROG Phone 5 Ultimate (ZS673KS) | 18 GB / 512 GB | Unqualified bring-up target; the rear monochrome ROG Vision matrix has no driver |

What differs, and what the tools do about it:

- **RAM map.** The bundle's `board.dtb` carries a fixed `/memory` node (the
  reference phone's 12 GB map), and kexec passes it to Linux unchanged. With
  a different RAM size the kernel would use memory that does not exist (8 GB:
  it crashes early) or ignore memory that does (16/18 GB). Copy *your*
  bootloader's map into your DTB with `scripts/host/rog5-dtb-memory`
  ([Stage 9](#stage-9-dtb-bundles-and-the-slot-b-wrapper)). The map must come
  from a kernel the ASUS bootloader started (stock Android or the ASUS 5.4
  wrapper), which is part of the missing pre-install environment.
- **The "memx" reservation** (64 MiB at `0x34a000000`, DTB feature `memx`)
  keeps Linux off memory that the reference phone's wrapper left
  non-executable. It is specific to that phone. On an 8 GB phone the address
  is not RAM at all (`rog5-dtb-memory` refuses such a DTB). Compose without
  `memx`. `rog5-sea-retire.service` is a bounded mitigation, not a cure: after
  a user program dies with SIGBUS from an instruction-fetch abort, it tries
  to take the affected memory block out of use (pages it cannot move stay).
  If the kernel log shows `rog5-sea` faults at the same addresses on every
  boot, add your own reservation like
  `dts/qcom/sm8350-asus-rog-phone5-exec-abort-memory.dtso`.
- **Storage.** The boot code checks the exact UFS geometry (disk size,
  userdata and partition 24 start and size, number of UFS block nodes), the
  filesystem UUIDs and the sealed root. These values now come from a
  **device profile** made from your phone
  ([Stage 8](#stage-8-your-device-profile)). The overlay (your data) is sized
  automatically: by default userdata minus the 4 GiB `/persist` image minus
  max(6 GiB, 5 %); the boot accepts growth up to userdata minus 4 GiB minus
  max(2 GiB, 1/32 of userdata), in whole MiB (reference phone: 181.3 GiB
  default, 184.9 GiB maximum).
- **Still reference-specific.** The kernel installer's on-phone script, the
  trial commit, the Wi-Fi layer and `rog5-update` expect the main UFS LUN to
  be `sda` (partitions `sda23`/`sda24`). On SM8350 LUN 0 enumerates first, so
  this holds on the phones we know, but it is not checked against the
  profile.
- **Pro/Ultimate hardware.** The rear displays and the Pro/Ultimate's rear
  touch pads have no driver. The base model's RGB logo LED driver
  (`tools/aura`, MS51 MCU at I2C 0x16) is untested on the Pro/Ultimate,
  which have the rear display instead of the RGB logo.
- **Board revisions.** The ASUS device tree has several board overlays
  (EVB/ER1/ER2/PR1/MP). The port follows the reference phone's production
  board.

## Warnings

- **Unlocking and installing erase the phone.** Android userdata is
  reformatted as ext4 for Linux and shrunk. Nothing on Android survives.
- **Never boot slot A Android after the install.** Its fstab expects an
  encrypted f2fs userdata marked formattable: booting stock Android normally
  **formats the partition that holds your Linux data**. Slot A stays on the
  phone only because it cannot be removed safely. Do not pick "Recovery mode"
  in the bootloader menu, do not run `fastboot set_active a`, and check the
  active slot before every `fastboot reboot`.
- **The bootloader may switch to slot A by itself** after repeated failed
  boots of slot B (its retry counters were never recorded on the reference
  phone). Test every new `boot_b` image in RAM first.
- **No cellular, cameras, fingerprint reader, NFC, GPS, earpiece or headphone
  jack.** See [what's left](whats-left.md).
- **The bootloader stays unlocked** (orange warning at every boot, about
  10 s). Anyone holding the phone can boot other code.
- **Keep your signing key private and backed up.** Whoever has it can sign a
  kernel your phone boots; without it you cannot install kernels any more.
- **What is protected and what is not.** The workflow never writes the
  signed early firmware (ROM, XBL, TrustZone, ABL) or calibration
  partitions; it writes `userdata`, the new partition 24 and `boot_b`. Boot
  failures and data loss are still possible: a bad `boot_b` leaves you in
  fastboot, and a fall back to slot A erases your Linux data.

## Overview and time

| Stage | Where | Time (reference PC) | Status |
|---|---|---|---|
| 0 Prepare the PC | PC | 20 min | scripted |
| 1 Record the phone | PC + phone | 10 min | manual |
| 2 Unlock | phone | 15 min | manual (ASUS tool) |
| 3 Signing key | PC | 2 min | manual |
| 4 Kernel | PC | 45-60 min | scripted |
| 5 Root filesystem | PC | 30 min, plus 1-4 h for the patched packages under emulation | scripted, rehearsed |
| 6 Pre-install environment, firmware | phone | - | **missing** |
| 7 Format, partition | phone | 30 min | **missing** |
| 8 Device profile | PC | 5 min | scripted |
| 9 DTB, bundles, wrapper | PC | 20 min | scripted, needs the missing inputs |
| 10 First install | phone | 30 min | manual, **missing** bootstrap boot |
| 11 Set up | phone | 20 min | scripted + manual |
| 12 Steam | phone | 30 min | scripted, rehearsed (download and install) |

Boot chain: ABL (ASUS, signed) starts **slot B**, whose `boot_b` holds a
small ASUS 5.4 kernel with a recovery ramdisk (the "wrapper"). The wrapper
mounts partition 24 (`arch_root_a`) read-only, reads
`/boot/rog5-linux/selector`, checks the Ed25519 signature of the chosen
bundle (kernel Image, `board.dtb`, initramfs, manifest) against **your**
public key and kexecs it. A new default bundle is tried once; if it does not
report a healthy boot, the next boot uses the fallback bundle. The root
filesystem is p24 (read-only) with an overlay image on userdata (p23)
holding everything you change. Details: [README](../README.md#how-it-boots),
[bootloader assessment](hardware/bootloader-assessment.md),
[bundle format](recovery-bundle-contract.md).

## Stage 0: prepare the PC

*Scripted (packages).* Arch Linux:

```sh
sudo pacman -S --needed git python base-devel clang lld llvm bc bison flex \
    openssl libelf kmod swig dtc cpio xz zstd zlib e2fsprogs libarchive gnupg \
    curl openssh qemu-user-static qemu-user-static-binfmt android-tools \
    networkmanager firewalld squashfs-tools
```

Debian/Ubuntu (the CI recipe in `.github/workflows/offline-smoke.yml`, plus
the packaging and phone tools):

```sh
sudo apt-get install --no-install-recommends build-essential bc bison flex \
    clang lld llvm libssl-dev openssl libelf-dev zlib1g-dev kmod \
    device-tree-compiler python3-venv python3-dev libfdt-dev swig git cpio \
    e2fsprogs libarchive-tools gnupg curl openssh-client qemu-user-static \
    binfmt-support fastboot uidmap network-manager firewalld squashfs-tools
```

Then, in a checkout:

```sh
git clone https://github.com/klimovich008/rog5-linux.git && cd rog5-linux
git switch -c my-phone          # your own branch for your registries (Stage 9)
python3 -m venv build/schema-tools
build/schema-tools/bin/pip install dtschema==2026.6       # dt-validate for the kernel build
scripts/host/fetch-android-boot-tools.sh                 # mkbootimg, unpack_bootimg, avbtool (hash-pinned)
```

Check that you can build an aarch64 root without root (on x86_64 this
needs binfmt_misc with the **F** flag):

```sh
grep flags /proc/sys/fs/binfmt_misc/qemu-aarch64          # contains F (e.g. PF, POCF)
grep "^$USER:" /etc/subuid /etc/subgid                   # one range in each
unshare --map-auto --map-root-user true && echo userns-ok
```

Rootless Podman could not run aarch64 binaries on the reference PC, while
`unshare --map-auto` + `chroot` could; the builder uses the latter.

## Stage 1: record your phone and keep stock firmware

*Manual.* Before anything else:

1. In Android, *Settings > System > About phone*: note model, RAM, storage
   and build number. Update to **WW-33.0210.0210.200** first if it is older.
2. Download the matching full firmware ZIP for your SKU from the ASUS support
   site (ROG Phone 5, ZS673KS, *Driver & Utility > BIOS & Firmware*) and keep
   it. Its `payload.bin` holds the stock `boot`, `vendor_boot` and `dtbo`.
3. Back up everything you want from Android. It will be erased.

## Stage 2: unlock the bootloader

*Manual.* The reference phone was unlocked before this project began, and
the repository does not record how. ASUS offered an official unlock app for
the ROG Phone 5 (*Unlock Device App*, from the ASUS support page) and has
limited its unlock service for older models since, so check whether it is
available for yours. **This project cannot help if it is not.** Unlocking
erases the phone and ends ASUS warranty support.

After unlocking, confirm in fastboot (hold **Power + Volume Up** from
power-off until the bootloader menu shows, then connect USB):

```sh
fastboot devices                 # exactly one device
fastboot getvar product          # lahaina
fastboot getvar unlocked         # yes
fastboot getvar current-slot     # a (stock boots from a until Stage 10)
fastboot getvar all 2>&1 | tee ~/rog5-private/getvar-all.txt   # keep, do not publish
```

Nothing else is needed: an unlocked ASUS bootloader skips the verification
of `boot`, `vendor_boot` and `dtbo` ("orange" state). **Do not flash
`vbmeta`** and never touch ROM, XBL, ABL, TrustZone, `persist`, `modem`,
`super` or any calibration partition.

## Stage 3: your signing key

*Manual.* Every boot bundle is signed; the wrapper boots only bundles signed
by the key whose public half it carries.

```sh
install -d -m 0700 ~/.config/rog5
openssl genpkey -algorithm ed25519 -out ~/.config/rog5/signing-key.pem
chmod 0400 ~/.config/rog5/signing-key.pem
openssl pkey -in ~/.config/rog5/signing-key.pem -pubout -outform DER | tail -c 32 \
    > ~/.config/rog5/trust-key.raw        # the raw 32-byte public key the wrapper embeds
sha256sum ~/.config/rog5/trust-key.raw
```

Back up `signing-key.pem` offline. The packagers check that the signing key
matches the key inside the recovery base (`etc/rog5/recovery-bundle-ed25519.pub`);
`install-default-kernel.py` takes the key hash with `--expected-trust-sha256`
(or `ROG5_TRUST_RAW_SHA256`).

## Stage 4: build the kernel

*Scripted.* 45-60 minutes with 8 threads.

```sh
mkdir -p build/linux && git -C build/linux init
git -C build/linux fetch --depth=1 \
    https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git refs/tags/v7.2.7
test "$(git -C build/linux rev-parse 'FETCH_HEAD^{commit}')" = f42acb3678424d1e08f6ed27c0d8ba8a125e14d6
export PATH="$PWD/build/schema-tools/bin:$PATH"
scripts/host/build-rog5-production-kernel.py --prepare-only \
    --config configs/kernel/rog5-production-build-7.2.7.json \
    --linux-git build/linux --output build/prep-check          # under a minute: do the patches apply?
scripts/host/build-rog5-production-kernel.py \
    --config configs/kernel/rog5-production-build-7.2.7.json \
    --linux-git build/linux --jobs "$(nproc)" \
    --output ~/.local/state/rog5-kernel-7.2.7-build-r1          # kernel build k1
```

Expected: `result.json` in the build directory with `"status": "PASS"` and
release `7.2.7-rog5-k1`; `objects/arch/arm64/boot/Image`; the patched tree
in `source/`. The directory name must end in `-build-rNNN` (or pass
`--label kNNN`); the bundle tool refuses unlabelled builds and packages the
modules itself. Another clang than the reference's (Ubuntu 24.04: clang 18;
reference: clang 20) can end with `"status": "FAIL"` only because of new
warnings the pinned warning policy has not reviewed; see "Upgrading the
kernel base" in [development](development.md).

## Stage 5: build the root filesystem

*Scripted, rehearsed.* `scripts/host/rog5-build-rootfs`, as your normal user:

1. downloads the Arch Linux ARM generic aarch64 tarball and checks its
   signature against the Arch Linux ARM build key;
2. installs `configs/rootfs/packages.txt` (the reference phone's explicit
   packages) without a kernel package;
3. builds the patched packages of `configs/rootfs/custom-packages.txt` from
   `packages/` (phoc, phosh, resources, gtk2 and the 8-bit Turnip
   `vulkan-freedreno`) and holds them with `IgnorePkg`;
4. creates the `phone` user and locks root to your SSH key;
5. installs the project's units, rules, settings and helpers with
   `scripts/device/rog5-install-userspace` (manifest
   `configs/rootfs/userspace.tsv`);
6. checks what the boot demands of the root (locked root, no host keys,
   empty keyring and machine-id, the pinned sshd drop-in), seals the tree
   and writes a 32 GiB ext4 image.

```sh
openssl passwd -6 > ~/.config/rog5/phone-password.hash      # the Phosh unlock PIN, digits
scripts/host/rog5-build-rootfs --work ~/rog5-rootfs \
    --ssh-key ~/.ssh/id_ed25519.pub \
    --phone-password-hash-file ~/.config/rog5/phone-password.hash
```

Options: `--skip-custom resources,mesa` (build those later on the phone,
where it takes minutes), `--steps NAME[,NAME]` to redo steps, and
`--image-bytes` if your partition 24 differs from 34359717888 bytes.

Outputs in `~/rog5-rootfs`: `arch_root_a.ext4` (sparse), `fs-uuid` (kept
across rebuilds) and `root-identity.env` (the seal and the systemd, sshd,
`authorized_keys` and `ld.so.cache` identities the boot pins; input to
Stage 8). The seal leaves out `/boot/rog5-linux` (the signed bundles and the
selector, added in Stage 10).

Times on the reference PC under qemu-user: upgrade 8 min, packages 10 min,
gtk2 53 min, phoc 11 min, phosh 30 min, vulkan-freedreno 38 min, the rest
about 10 min; see the [rehearsal](fresh-install-rehearsal.md).

## Stage 6: pre-install environment and firmware

*Missing; your phone.* Before the phone runs this system, something must run
on it to read and prepare it. The reference phone used RAM-booted recovery
wrappers (`fastboot boot <image>`: nothing is written to the phone) built
from the missing recovery base and ASUS kernel. That environment is needed
to:

- record the bootloader's RAM map and storage inventory
  (`scripts/host/rog5-device-profile collect-script`, read-only; it prints
  `memory_source=bootloader` when run under the ASUS kernel);
- read the firmware the boot bundle needs from `vendor_a` (ADSP, A660, SLPI,
  WCN6855) into the ramdisk base and kits (**missing**: no builder);
- run Stage 7.

The project never distributes proprietary firmware. Firmware comes from your
phone's partitions (`vendor_a`, `persist`, `dsp_a`) or, for redistributable
firmware (`a660_gmu.bin`, Bluetooth, `regulatory.db`), from Arch's
`linux-firmware` and `wireless-regdb` packages. After the install, two
scripted installers run on the phone itself (Stage 11):

| Firmware | From | Installer | Checks |
|---|---|---|---|
| Speaker protection DSP (CS35L45) + factory calibration | `vendor_a`, `persist` | `scripts/device/install-rog5-speaker-firmware` | every vendor file against its WW33 hash; calibration range |
| Sensors (SLPI) registry and config, `hexagonrpcd` | `vendor_a`, `persist`, `dsp_a` | `scripts/device/install-rog5-sensors.sh` | the source archive hash and the vendor filesystem label, not each file |
| CDSP (standby experiments only) | `vendor_a` | `scripts/host/fetch-vendor-cdsp-firmware.py` | reference-only: needs the reference display kit as its base |

## Stage 7: format and partition (destructive)

*Missing (archived, reference GUIDs); your phone.* **Everything on the phone
is lost.** This is a record of what the reference phone went through, not a
procedure to copy: the executors (`scripts/device/storage-layout-stage1` and
its host collector in `archive/pre-cleanup-2026-09-29`) carry the reference
phone's disk and partition GUIDs. **Do not run them as they are.**

Stock layout: 22 small partitions, then `userdata` (p23) to the end of the
main UFS LUN (4 KiB blocks). Target layout:

| Partition | Content |
|---|---|
| p1-p22 | unchanged (never touched) |
| p23 `userdata` | same start, GUID, type and attributes; ext4 label `rog5-linux`, shrunk to leave 32 GiB at the end. Holds `/rog5` (root, 0700) with `rog5/boot/` (try-once records), `rog5/state/server-state-v1.ext4` (`/persist`, 4 GiB) and `rog5/root/root-overlay-v1.ext4` (overlay) |
| p24 `arch_root_a` | new, Linux filesystem type, 32 GiB - 20 KiB, the Stage 5 image |

Compute your layout from an inventory taken on the stock phone:

```sh
scripts/host/rog5-device-profile plan --inventory inventory.txt
```

It prints the new userdata size, the p24 start and size, the ext4 block
count to shrink to, and your overlay sizes. For the reference phone it
reproduces the real layout (p24 at sector 427819008, 67108824 sectors).

The reference sequence (August 2026), from RAM-booted environments that
kept every UFS node read-only except the ones a step needed:

1. Stream both GPT copies (and the small partitions) to the PC and verify
   the copies **before** any write. Check the LUN size, the logical block
   size (4096), and that p23 is `userdata` at the expected start.
2. Format userdata:
   `mkfs.ext4 -F -b 4096 -L rog5-linux -U <your uuid> -m 0 -O ^casefold,^encrypt,^verity,^quota,^project -E lazy_itable_init=0,lazy_journal_init=0 <p23>`,
   then create `/rog5` (owner root, mode 0700) on it.
3. Shrink: `e2fsck -f -p <p23>`, `resize2fs <p23> <blocks from plan>`.
4. Write new primary and secondary GPTs with p23 shortened and p24 added,
   built offline with CRC32 (archived `scripts/host/build-storage-layout-gpt-regions.py`;
   `sgdisk` was dropped because its partition-table re-read changed the live
   mapping), then `sgdisk -v` and `e2fsck -fn`.
5. Create `/persist`: `scripts/device/stage-persistent-service-state.sh`
   (rendered for your profile, Stage 8) with
   `ALLOW_ROG5_SERVICE_STATE_STAGE=1` for `stage` (run `preflight` first).
   It wants the UFS read-only except userdata, p24 mounted read-only at
   `/.rog5/root-ro`, and the power gate above.

## Stage 8: your device profile

*Scripted.* The boot code accepts exactly one phone and one root. Its
per-phone values sit between `# BEGIN ROG5 DEVICE PROFILE` and
`# END ROG5 DEVICE PROFILE` in `initramfs/persistent-root-init`,
`persistent-root-attest`, `persistent-service-state`,
`persistent-slotb-loader-init`, `recovery-init` and the two stagers in
`scripts/device/`. The repository holds the reference phone's values
(`configs/device-profiles/reference.env`).

Order: build the root (Stage 5, gives `root-identity.env`) → partition and
format (Stage 7; p24 still empty) → collect the inventory → make the profile
→ build bundles and the wrapper with it (Stage 9) → put the bundles into the
root image and flash it (Stage 10).

```sh
# Read-only inventory, in the pre-install environment on the phone:
scripts/host/rog5-device-profile collect-script > collect.sh     # run it there; save the output as inventory.txt
scripts/host/rog5-device-profile make --inventory inventory.txt \
    --root-identity ~/rog5-rootfs/root-identity.env --name my-rog5 -o ~/.config/rog5/profile.env
scripts/host/rog5-device-profile check ~/.config/rog5/profile.env
scripts/host/rog5-device-profile show-derived ~/.config/rog5/profile.env
```

`make` requires userdata to be the ext4 `rog5-linux`. p24 may be empty; if
it holds a filesystem, it must be the `ROG5_ARCH_A` root whose UUID
`root-identity.env` names. New random UUIDs are picked for the overlay and
`/persist` images (`--base OLD_PROFILE` keeps existing ones). Keep the
inventory's `memory_reg=` line for Stage 9.

Where the profile is used:

- the bundle tool: `"device_profile": "~/.config/rog5/profile.env"` in
  `configs/production/bundle-inputs.json` renders the ramdisk's init,
  attestor and state helper and the RAM-trial wrapper's recovery init and
  selector loader;
- the `boot_b` wrapper: `package-slotb-boot-wrapper.py --device-profile P`;
- the on-phone stagers: `scripts/host/rog5-device-profile render-tree
  --profile P OUT` renders every profiled source; copy the stagers from
  `OUT/scripts/device/`;
- `install-default-kernel.py --profile P`.

Every check stays in place; only the expected values change, and they end
up inside your signed bundle. If you rebuild the root after the `seal` step
changes, remake the profile and the bundles.

## Stage 9: DTB, bundles and the slot-B wrapper

*Scripted, with the missing inputs.*

**Commit first.** The bundle tool builds from `git archive HEAD` and
`install-default-kernel.py --stage` refuses a dirty checkout. Keep your
registry and input changes (`configs/production/*.json`, `docs/bundles.md`)
as commits on your own branch; keep keys, profiles and inventories outside
Git.

**DTB.** Compose from your kernel build without `memx`, copy your RAM map in,
and register the result:

```sh
state=~/.local/state/rog5-production-boot-20260923   # bundle-inputs.json state_dir
mkdir -p ~/rog5-private/dtb "$state/my-dtb-r1"
features=touch,bluetooth,cpuidle,gpubw,bwmon,ddrscale,periph,audio,slpi,usbotg,osi,aoss,qupicc,dp,l3,skin,acd,cpucap,usbbtm,mic,usbbtmtc
scripts/device/compose-production-dtb.sh BASE_DTB ~/.local/state/rog5-kernel-7.2.7-build-r1/source \
    ~/rog5-private/dtb/composed.dtb "$features"
scripts/host/rog5-dtb-memory set ~/rog5-private/dtb/composed.dtb "$state/my-dtb-r1/board.dtb" \
    --memory-reg "0000000080000000...your memory_reg hex..."
scripts/host/rog5-dtb-memory show "$state/my-dtb-r1/board.dtb"
scripts/host/rog5-bundle-registry.py add-dtb --dtb "$state/my-dtb-r1/board.dtb" \
    --features "$features" --base d9          # prints the new id, e.g. d11
```

`BASE_DTB` is the reference V9 `board.dtb` (sha256 `eca5c2c3…`), not
published yet (**missing**); the composer checks it by hash. `rog5-dtb-memory
set` refuses a map whose no-map reservations fall outside your RAM.

**Bundles.** `scripts/host/rog5-make-bundle.py` builds, signs and packages
one bundle (see [bundles](bundles.md) and "Bundle names and the bundle tool"
in [development](development.md)). Bundles are named
`<role>-k<kernel>-d<dtb>-<YYMMDD><letter>`; the reference phone runs
`main-k111-d10-261001a` with the fallback `production-7.2.7-safe-r8`.
Point every entry of
`configs/production/bundle-inputs.json` at your own files and hashes (signing
key, ramdisk base, firmware and Wi-Fi kits, recovery base, ASUS template and
kernel) and add `"device_profile"`. A recovery base other than the
reference one is accepted when pinned there; the packager then requires that
your signing key is the key inside it.

```sh
scripts/host/rog5-make-bundle.py --role safe --kernel k1 --dtb d11 --private-key ~/.config/rog5/signing-key.pem
scripts/host/rog5-make-bundle.py --role main --kernel k1 --dtb d11 --private-key ~/.config/rog5/signing-key.pem
```

Each result is `<state>/package-<name>/` with `bundles/<name>/` and
`boot-ram-128m.img` (a RAM-trial wrapper that embeds the bundle); a `main`
bundle's trial descriptor is `<state>/trial-<name>/descriptor`. A bundle built with role `safe` is only a
candidate: it becomes a proven fallback once it has booted (Stage 10).

**Wrapper** (`boot_b`). `scripts/host/package-slotb-boot-wrapper.py
--device-profile P` builds the 96 MiB `boot_b-96m.avb.img` and its 128 MiB
RAM twin `boot-ram-128m.img` from:

- the **ASUS 5.4 kernel**, built from `ASUS_I005_1-33.0210.0210.200-kernel-src.tar.gz`
  (ASUS GPL download; URL and hash in `docs/history/steam-deck-host.md`) with
  `patches/asus-5.4.210` (**missing** builder);
- a **boot template**: `scripts/host/build-canonical-boot-v3-template.sh`
  makes a synthetic header-v3 template (*scripted*);
- the **recovery base** with your `trust-key.raw` (**missing**) and the
  trial-state helper (`--trial-helper artifacts/persistent-trial-state-vN/...`,
  **missing**).

With a non-reference recovery base the wrapper builder checks the base by the
hash you give and its key member for size; the reference base's verifier,
kexec and key hashes are enforced only for the reference base.

## Stage 10: first install and first boot

*Manual; fastboot; **missing** bootstrap boot.* Reconstructed from the
reference install (2026-08-28 to 09-06); never done on another phone.
Current bundles need `/persist` (`rog5-persistent-state.service`) and, with
`PERSISTENT_ROOT_OVERLAY=1`, the overlay image. `/persist` comes from Stage 7
step 5; a bootstrap bundle that boots without them is not defined yet.

1. **Put the bundles into the root image** and rebuild it (the filesystem
   UUID and the seal stay the same):

   ```sh
   scripts/host/rog5-build-rootfs --work ~/rog5-rootfs --steps boot,image \
       --bundle <state>/package-<main>/bundles/<main> --descriptor <state>/trial-<main>/descriptor \
       --fallback-bundle <state>/package-<safe>/bundles/<safe>
   ```

   With only `--bundle`, the selector is v1 (one bundle, no fallback).
2. **Try the wrapper in RAM first.** In fastboot, check before every
   command that it is your phone and the state you expect:

   ```sh
   fastboot devices; fastboot getvar product; fastboot getvar unlocked; fastboot getvar current-slot
   fastboot boot boot-ram-128m.img          # RAM only; a reset forgets it
   ```

   `scripts/host/production-ram-trial.py boot` automates this with identity,
   slot and one-use checks (see "Tools on your PC" below). A RAM boot must
   reach Linux and answer SSH before anything is flashed.
3. **Flash p24.** ABL mishandled zero-fill chunks in sparse images; the
   reference used an "allocated-RAW" sparse image (**missing** converter)
   with `fastboot flash arch_root_a <image>`. Plain `img2simg` output is
   untested.
4. **Flash the wrapper and select slot B** (only `boot_b` is written):
   `fastboot flash boot_b boot_b-96m.avb.img`, check the result, then
   `fastboot set_active b`, `fastboot getvar current-slot` (must print `b`),
   `fastboot reboot`.
5. **First boot:** the orange warning (about 10 s), the ASUS logo, the
   wrapper (about 17 s), then Linux. Connect the side port; the phone is a
   USB network device at `10.77.0.2` (see "Tools on your PC"); `ssh
   root@10.77.0.2`.
6. **Overlay:** with the rendered stager, as root on the phone:

   ```sh
   export EXPECTED_ROG5_BOOT_ID=$(cat /proc/sys/kernel/random/boot_id)
   export EXPECTED_ROG5_BUNDLE=$(sed -n 's/.*rog5.bundle=\([^ ]*\).*/\1/p' /proc/cmdline)
   ./stage-persistent-root-overlay.sh preflight
   ALLOW_ROG5_ROOT_OVERLAY_STAGE=1 ./stage-persistent-root-overlay.sh stage
   ```

   The image is created at your profile's `ROG5_OVERLAY_CREATE_BYTES`, fully
   allocated; the stager checks power and temperature first.
7. **Default and fallback:** build overlay bundles
   (`PERSISTENT_ROOT_OVERLAY=1`, `PRODUCTION_UPDATE_KIT=1` in `ramdisk_env`),
   commit, then:

   ```sh
   trust=$(sha256sum < ~/.config/rog5/trust-key.raw | cut -d' ' -f1)
   scripts/host/install-default-kernel.py --profile ~/.config/rog5/profile.env \
       --expected-trust-sha256 "$trust" --trust-key ~/.config/rog5/trust-key.raw \
       --bundle-dir <state>/package-<main>/bundles/<main> --descriptor <state>/trial-<main>/descriptor \
       --fallback-bundle-dir <state>/package-<safe>/bundles/<safe> --address 10.77.0.2 \
       --evidence ~/rog5-private/install-<main>-preflight          # read-only preflight
   # the same with --stage and a new --evidence directory
   ```

   A failed or ambiguous `--stage` is never retried: inspect the phone first.
   Reboot twice: the first boot logs `PASS <bundle> committed healthy`
   (`journalctl -u rog5-production-trial-commit`), the second must land on
   the same bundle (`tr ' ' '\n' </proc/cmdline | grep rog5.bundle`). To
   prove the fallback, follow "Making a production kernel the default" in
   [development](development.md) (mask the commit unit for one boot).

**Tools on your PC.** `production-ram-trial.py` expects:

- the phone's fastboot serial in `$ROG5_DEVICE_SERIAL` or
  `~/.config/rog5/device-serial`;
- two NetworkManager profiles on the phone's USB network interface (find it
  with `ip link` after connecting; set `ROG5_TRIAL_INTERFACE` to its name):

  ```sh
  nmcli con add type ethernet ifname <iface> con-name rog5-standalone-shared \
      ipv4.method shared ipv4.addresses 10.77.0.1/30 connection.autoconnect-priority -10
  nmcli con add type ethernet ifname <iface> con-name rog5-fallback-usb-ssh \
      ipv4.method manual ipv4.addresses 169.254.77.1/30 connection.autoconnect no \
      connection.autoconnect-priority 100
  ```

- firewalld (the RAM-trial stage receiver adds a temporary rule);
- your SSH key in `ROG5_SSH_KEY` or `~/.config/rog5/ssh-key`, and a
  `known_hosts` in `ROG5_KNOWN_HOSTS` or `~/.config/rog5/known_hosts`. The
  phone's persistent host key is created on the first boot with `/persist`;
  RAM trials without it have a different, temporary key. Record each key the
  first time you see it over the USB cable; never disable host-key checks.
- the USB port of the phone in `ROG5_TRIAL_USB` (`/sys/bus/usb/devices/<port>`)
  and its resolved sysfs path in `ROG5_TRIAL_ANCHOR` (`readlink -f` of it);
  the defaults are the reference PC's.

## Stage 11: set up the phone

*Scripted + manual*, over `ssh root@10.77.0.2`:

- **PIN.** If you did not pass a hash in Stage 5: `passwd phone` (digits
  only). Root stays key-only: the boot refuses a root password.
- **Wi-Fi.** `rog5-wifi-networkmanager apply` moves the link from the boot
  kit's `wpa_supplicant` to NetworkManager; then connect in Phosh settings
  or with `nmcli dev wifi connect <SSID> --ask`.
- **Firmware** (Stage 6 table):
  `ssh root@10.77.0.2 sh -s < scripts/device/install-rog5-speaker-firmware`,
  then enable the amplifiers in `/etc/rog5/speaker-dsp.conf`; for the sensors
  `tar -C third_party/hexagonrpc -cf - . | ssh root@10.77.0.2 'rm -rf /run/hrpc && mkdir /run/hrpc && tar -C /run/hrpc -xf -'`
  and `ssh root@10.77.0.2 sh -s /run/hrpc < scripts/device/install-rog5-sensors.sh`.
- **Services** (enabled in the image from `configs/rootfs/userspace.tsv`):
  `rog5-phosh` (phone shell), `rog5-sleep-policy` (suspend when idle;
  audio, inhibitors and a lit monitor keep the phone awake),
  `rog5-charge-policy` (70-80 %, bypass when full; `/etc/rog5/charge-policy`),
  `rog5-perf-mode` (performance limits on external power;
  `/etc/rog5/perf-mode`), `rog5-sea-retire`, `rog5-usb-modalias`,
  `rog5-firewall` (on Wi-Fi only SSH and Tailscale come in), `rog5-desktop-mode`,
  `rog5-healthd` (`:8787`; the firewall admits it from USB, Tailscale and the hotspot only). On demand:
  `rog5-usb-reconnect` (monitor hubs after `-71` errors), `rog5-usb-storage@`
  (a disk listed in `/etc/rog5/usb-storage` mounted at boot), `rog5-hotspot`.
  `rog5-install-userspace --check` compares the installed files with a
  checkout.
- **Desktop mode.** With a monitor or hub attached and the phone unlocked,
  tap *Desktop mode* in the app grid: GNOME starts on the monitor and the
  phone screen becomes a touchpad; *Phone mode* returns. Switching closes
  running apps.
- **Optional:** `pacman -S tailscale && systemctl enable --now tailscaled && tailscale up`.
- **Patched packages you skipped:** in a checkout on the phone, as `phone`,
  `cd packages/<dir> && makepkg <flags from configs/rootfs/custom-packages.txt>`
  (install the build dependencies first, as root, with `pacman -S --asdeps`),
  then as root `pacman -U <package file>` and add the package to `IgnorePkg`
  in `/etc/pacman.conf`. The image has no `sudo` rule for `phone`; use the
  root SSH session.

## Stage 12: Steam

*Scripted, rehearsed up to the installed files.* Valve's native aarch64
Steam client runs directly (4 KiB pages, no VM); x86 games run through
Steam's own FEX-Emu compatibility tool.

```sh
# as the phone user, Steam closed: download and verify the client
steam-arm64-install                 # --beta for the beta client
# as root, Steam closed: the x86 guest root for FEX (from rootfs.fex-emu.gg, XXH3-checked)
steam-fex-rootfs-install
```

Requirements: `gtk2` (patched build from Stage 5), `lsof` and `xxhash` (in
the package list). Done when `~/.local/share/Steam/steamrtarm64/steam`
exists, a "Steam" launcher is in the app grid, and
`/usr/share/guestos/fex-mesa/graphics_provider.json` exists (root-owned,
about 4.4 GB). Start Steam from the launcher: `steam-arm64` restarts the
client after its self-update and preloads a small shim that makes the window
draggable in GNOME (`ROG5_STEAM_DRAG=0` disables it).

Proton:

- **Proton 9.0 (DXVK 2.5.1)** under FEX runs DirectX 11 games (BioShock
  Remastered ran). Pick it per game: *Properties > Compatibility*.
- **DXVK 3.x** (Proton 10/Experimental) needs `storageBuffer8BitAccess`,
  which stock Turnip lacks on the A660. Two routes, neither game-tested yet:
  native ARM64 Proton with the patched phone driver (`packages/mesa`,
  `vulkan-freedreno 26.2.3-1.1`, Stage 5), or x86 Proton with the patched x86
  Turnip in FEX's guest root: `packages/mesa-fex/build.sh 1` on an x86_64 PC
  with Podman, copy the result to the phone, `steam-fex-turnip-8bit install DIR`.
- `PROTON_LOG=1 %command%` as launch option writes `~/steam-<appid>.log`.

## Updates, fallback and recovery

- **Package updates** are automatic: `rog5-update` (hourly timer, from the
  boot bundle) snapshots the system part of the overlay, runs
  `pacman -Syu`, checks the result and reboots only when idle (01:00-06:00,
  no remote client, no sound). A failed update arms a restore of the snapshot
  on the next boot; your files are never rolled back. The restore passed
  fault-injection tests but has not yet been needed for real. Commands:
  `/run/rog5-update/rog5-update status|verify-root|resume|rollback`. After a
  manual upgrade run `verify-root`: `openssh`, `systemd` and `shadow` updates
  can change files the next boot checks. Held packages (`IgnorePkg`) need a
  rebuild when Arch moves on.
- **Kernel updates** are new bundles: `rog5-make-bundle.py`, a RAM trial,
  `install-default-kernel.py`. Nothing is flashed.
- **Fallback.** A new default that does not commit a healthy boot is not
  retried: the next boot uses the fallback bundle. Reinstall a default from
  there.
- **Forced reboot** (hang, dark screen): hold **Power + Volume Up** about
  20 s; when it vibrates, release Power and keep Volume Up until fastboot
  shows. On the Qualcomm crashdump screen, hold **Volume Down + Power**
  8-12 s, then do the first step. In fastboot, check `fastboot getvar
  current-slot` (must be `b`) before `fastboot reboot`; if it says `a`, stop
  and do not reboot into Android. Never pick *Recovery* or *Power off* in the
  menus.
- **Back to stock.** Not scripted and not tested; destructive. It means
  restoring the stock GPT from your Stage 7 backup, flashing the stock images
  of your firmware ZIP to both slots and a factory reset through stock
  recovery.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `rog5-build-rootfs`: `Exec format error` | binfmt without the F flag, or Podman instead of `unshare` (Stage 0) |
| pacman in the builder: `Landlock is not supported` / `switching to sandbox user 'alpm' failed` | qemu-user has no Landlock; the builder passes `--disable-sandbox` under emulation only |
| pacman in the builder: `could not determine cachedir mount point` | the root must be a mount point; the builder bind-mounts it onto itself |
| makepkg in the builder: `install: cannot stat '/dev/stdin'` | fixed: the builder's `/dev` provides `stdin`/`stdout`/`stderr` |
| Kernel build ends `FAIL` with only warning-policy lines | new upstream warnings from another clang; see development.md |
| `rog5-dtb-memory set` refuses the map | a no-map reservation (usually memx) lies outside your RAM: compose without it |
| Boot stops in fastboot after the ASUS logo | the wrapper found no valid selector or bundle, or the storage check failed (wrong profile). RAM-boot a known-good wrapper; check `rog5-device-profile check` |
| The phone boots the fallback | the default did not commit: `journalctl -b -1 -u rog5-production-trial-commit` |
| Monitor USB devices gone after replug (`-71`) | `rog5-usb-reconnect` resets the port; it can take a minute |
| Games die with SIGBUS | instruction-fetch aborts: `journalctl -u rog5-sea-retire`; see memx in [Variants](#variants) |
| Wi-Fi slow to reconnect after sleep | known (about 11 s) |
| Only 1080p60 through an HDMI adapter | known: HDMI converters stay dark above HBR |
| Standby drains about 79 mA | deep standby is not reached yet |

More: [what's left](whats-left.md) and [user irritations](user-irritations.md).

## Step inventory

| Step | Status | Command or source |
|---|---|---|
| PC packages, schema tools, boot tools | scripted | Stage 0 |
| Unlock | manual | ASUS unlock app |
| Signing key | manual | Stage 3 |
| Kernel | scripted | `build-rog5-production-kernel.py` |
| Root filesystem image | scripted, rehearsed | `rog5-build-rootfs` |
| Userspace units, rules, helpers | scripted | `rog5-install-userspace` + `configs/rootfs/userspace.tsv` |
| Patched packages | scripted | `rog5-build-rootfs` step `custom`, or `makepkg` on the phone |
| Pre-install RAM environment | **missing** | recovery base + ASUS kernel builders |
| Bootloader RAM map, inventory | scripted, needs the pre-install environment | `rog5-device-profile collect-script` |
| ADSP firmware (ramdisk base), display kit, Wi-Fi kit | **missing**, your phone | no builders |
| Speaker, sensor firmware | scripted, your phone | Stage 11 |
| Layout plan | scripted | `rog5-device-profile plan` |
| Backups, format, shrink, GPT, `/rog5` | **missing** | archived `storage-layout-stage1` (reference GUIDs) |
| `/persist` image | scripted, needs the pre-install environment | `stage-persistent-service-state.sh` (rendered) |
| Device profile | scripted | `rog5-device-profile make/check/render-tree` |
| RAM map in the DTB | scripted | `rog5-dtb-memory` |
| DTB composition | scripted, **missing** base DTB | `compose-production-dtb.sh` |
| Bundles | scripted, **missing** inputs | `rog5-make-bundle.py` |
| Wrapper image | scripted, **missing** inputs | `package-slotb-boot-wrapper.py --device-profile` |
| Bundles + selector in the root image | scripted | `rog5-build-rootfs --steps boot,image` |
| p24 sparse image | **missing** | archived allocated-RAW converter |
| RAM trial, flash `boot_b`, `set_active b` | manual | Stage 10 |
| Bootstrap first boot | **missing** | not defined |
| Overlay image | scripted | `stage-persistent-root-overlay.sh` (rendered) |
| Default and fallback install | scripted | `install-default-kernel.py --profile --expected-trust-sha256` |
| Wi-Fi to NetworkManager | scripted | `rog5-wifi-networkmanager apply` |
| PIN | manual | `passwd phone` or the Stage 5 hash |
| Steam | scripted, rehearsed | `steam-arm64-install`, `steam-fex-rootfs-install` |
| Updates | scripted | `rog5-update` (automatic) |
| Back to stock | missing | not tested |
