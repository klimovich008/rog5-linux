# Production headless RAM-trial package — September 23

Claude Code took over coordination today. The goal for this step is a
headless first boot of `7.1.4-rog5-production` that answers one question:
does the production kernel plus a modprobe ramdisk reach root, power, USB and
SSH? The package is prepared, signed and verified offline. **Physical: NOT
RUN.** The phone was absent from the approved port 1-1.2 at every check today.

## What changed and why

- **Shared `mdt_loader` resolved by modprobe, not receipts.** Production
  builds `DRM_MSM=m`, which makes `mdt_loader` a module that `qcom_q6v5_pas`
  needs. The hand-ordered 15-module insmod list could never load PAS. The
  power and UFS stage loaders now name each module to `modprobe` against a
  depmod tree for the release read from procfs: 16 power modules with
  `mdt_loader` first, then 4 UFS modules. Every per-step `/proc/modules`
  check is kept. Legacy loose-module archives keep their exact insmod path.
  The earlier receipt and pin-cascade attempt was dropped; its WIP is kept in
  `~/.local/state/rog5-shared-mdt-20260923-r1`.
- **Standalone builder production mode.** A pinned module package
  (`bed63b7b…`, 64 modules) replaces every loose release-bound module and the
  native Wi-Fi payload, so the first boot is headless. The package must hold
  only regular files under `lib/modules/<release>` in the production profile
  (AArch64 REL, exact vermagic, no BTF, no `__versions`). A `modprobe.d`
  blacklist stops alias autoloading of msm, gpucc, panel, refgen, touch and
  ath11k. Archives are now packed in C collation, which the bundle verifier
  requires.
- **One normal p23 journal replay accepted.** `EXT4-fs (sdX23): recovery
  complete` after any unclean stop used to fail final storage and waste the
  boot; R01 ended that way. Repeats, other devices and ext4 or UFS errors
  still fail.
- **Lean packager and launcher.** `scripts/host/package-production-ram-trial.py`
  replaces the private GPU-trial runner. `scripts/host/production-ram-trial.py`
  replaces the dead r137 launcher. RAM boot only, with one claim per wrapper
  hash and no flashing.
- **Manual rescue runbook restored** in `docs/development.md`.

## Artifacts (private, `~/.local/state/rog5-production-boot-20260923/`)

| Item | SHA-256 |
|---|---|
| Image (build-r2, production) | `0789c10855e74c2f54caee7437864235f5872118e9f697782cc8547b286d406a` |
| DTB (installed V9 board.dtb: UFS, USB, ADSP, pmic-glink, buttons and Wi-Fi PMU on; display and GPU off) | `eca5c2c343fc4cd5511490be0c17501d69f4027941e268ff3f95da4672c214f4` |
| Ramdisk r3 (V9 base `5146e22f…` + production tree, UFS gate fix) | `28c1abe07a409bd155b89bb38c5aaad2e53f6be6a4a28da8cdc549773bebd217` |
| Signed manifest `production-headless-r2` | `a177ce48cfc5273ed5acbf1d0c4317e77fef5bdd332ee338c2e9bc0332488e33` |
| 128 MiB RAM wrapper (`package-r3/boot-ram-128m.img`) | `6cafb1ce3001c8d25ee0db32c662896b57ecd528474956c54b3e13a1d55562c3` |

Superseded and never claimed: `package-r2`, bundle `production-headless-r1`,
wrapper `b73721ee…`. Its ramdisk r2 would have skipped UFS entirely: the
init's main-flow gate `deferred_ufs_modules_present` only knew the legacy
loose-module directory. The second investigation round (refusal-chain dry run)
found it before any boot. The fix is `50d7fc00`, with gate tests under the
target BusyBox.

Fixed target command line: `console=ttyMSM0,115200n8 rdinit=/init panic=10
oops=panic loglevel=8 ignore_loglevel printk.always_kmsg_dump=Y
rog5.ufs_discovery=1 rog5.persistent_ro=1 rog5.bundle=production-headless-r2
rog5.target_timeout=600 rog5.recovery_timeout=900`.

## Verification

- The loader replay ran under the target ARM64 BusyBox 1.37 against the real
  production `modules.dep`, in an unprivileged chroot under qemu. It passed
  9 cases, including legacy paths, preloaded modules, a module absent from the
  tree, load failures and unobservable modules. Harness lessons: exec'd
  children need `QEMU_UNAME`, and the chroot needs a bind-mounted `/dev/null`.
  The replay also caught one real bug before any boot: BusyBox ash rejects
  `${var##*<newline>}`.
- The builder test (3 cases, 23 s) covers the real build, three hostile
  packages, a hash mismatch and a byte-identical rebuild. The ramdisk builds
  in 4.5 s and holds 750 members in strcmp order.
- The packager rebuilt the wrapper byte-identically. `avbtool verify_image`
  passed. The exact pinned ARM64 `rog5-bundle-verify` (`c3c5c318…`) with the
  wrapper's trust key (`cc1bca69…`) accepted the bundle under qemu.
- Consumer suites passed unchanged on the worktree. These included the
  persistent-root initramfs, storage-resolution, overlay-runtime, handoff,
  service-state, slot-B loader, native-wifi-boot, rescue-composition and
  release-composition suites. The launcher suite passed 6 cases against fake
  sysfs, fastboot, ssh and nmcli.

## Host and phone preflight (read-only, 14:00Z)

- The phone was plugged in on port 1-1.2 and booted to the V11 fallback,
  `7.1.4-g359318de534f`. SSH answered on 10.77.0.2. Battery was 100% at
  29.7 °C and 8.41 V, with USB online at 5.0 V. No units had failed, and only
  `sda` and `sda23` were writable.
- V11's RAM exitrd ends in plain `reboot -f`, so a normal reboot returns to V11,
  not fastboot. The launcher now requires an explicit `to-fastboot --mode`.
  An automatic edit of the RAM copy of the shutdown script was refused by
  Claude Code's safety classifier (a remote shell write), so the route is the
  user's choice.
- Polkit allows the deck user network-control and settings.modify.system.
  firewalld is running, and the phone interface is in zone `nm-shared`. Every
  host step therefore runs without sudo, including the stage receiver.

## Integrated tier

- `ci` r3 on `28f4d473` ran 294 suites: 294 PASS, then one FAIL. The failure,
  `test-github-exact-head-workflow.sh`, also occurs at the session base
  `57e15aea`: both CI jobs installed `bubblewrap` on one line with another
  package. It was fixed in `0538b05b`, formatting only.
- An earlier run failed because a test was edited in the active checkout
  while CI ran. That lesson is recorded; edits now go to a separate worktree.

## Trial plan (attended; needs fresh Ready)

1. The phone connects on port 1-1.2. `production-ram-trial.py status`
   classifies the port. Any ordinary boot lands on V11, whose SSH answers on
   169.254.77.2.
2. `probe` runs a read-only health read. Then `to-fastboot --mode helper`
   (sync, then the exitrd's restart2 helper) reaches fastboot; otherwise the
   user does rescue step R1.
3. `ROG5_ALLOW_RAM_TRIAL=1 boot --stage-receiver --wrapper package-r3/boot-ram-128m.img --wrapper-sha256 6cafb1ce…`
   checks identity (serial, lahaina, slot b, unlocked, 128 MiB) and consumes
   the claim. It then RAM-boots and observes for up to 20 minutes.
4. The target rolls back by itself within the 900 s recovery window and
   reboots to the installed chain (V11). A hard hang needs the manual rescue R1.

Known limits: no ramoops (pstore is lost across the wrapper boot), Tailscale
lacks `NF_CONNTRACK_MARK`, and Wi-Fi, display and GPU are deliberately absent
from this boot.

## Phone trials (RAM-only, attended by software)

| Trial | Image | Result |
|---|---|---|
| r1 14:27Z | wrapper `6cafb1ce…` (package-r3) | The production kernel ran for the first time: `ufs-ready ENTER`, then rollback to fastboot about 2 s after the gadget enumerated. The failure code was lost because NetworkManager 1.52 silently ignored a second address on the shared profile. |
| r2 14:42Z | same image (reuse recorded in claims/) | `ufs-ready FAIL power-usb-module-qrtr-already-loaded`. With a depmod tree, the kernel's request_module (net-pf-42, from the built-in sysmon QMI socket after ADSP start) loads qrtr before its explicit step. |
| r3 14:48Z | wrapper `b757a9e1…` (package-r4, commit 5b57a603) | **PASS headless.** kernel-verified; power/USB ready at 3.5 s (`qrtr was autoloaded before its step`); UFS by modprobe at 7.5–8.1 s; switch-root PASS at +15 s; sshd running; SSH health at 14:49:09. Up 1206 s later with no rollback (P2 gate passed): battery 100 % at 29.8 °C, USB online, only sda/sda23 writable, load 0.20, 37 °C. |

Capture validation: a normal V11 boot at 14:37Z delivered 8 initramfs stage records and link-local SSH health through the new host path.

Open items from r3:
- `rog5-package-keyring.service` hits its 120 s start timeout; the phone clock reads May 28 because the RTC is not set.
- The live kmsg stream recorded 0 lines; the one-shot dmesg at health time worked.
- `pmic-spmi 0-05` probe -EIO also occurs on V11, so it predates this work.
