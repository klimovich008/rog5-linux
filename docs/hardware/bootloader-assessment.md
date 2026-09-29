# Bootloader and fastboot assessment (2026-09-29)

Research only. Nothing on the phone was changed for this report: no fastboot,
no flashing, no reboot, no partition reads. The phone data comes from
read-only SSH (`systemd-analyze`, journal, `/proc`, sysfs) on the running
`production-7.2.7-r185`. The rest comes from host-side trial evidence under
`~/.local/state/rog5-production-boot-20260923/trial-727-*`, the repository,
the ABL image in the archived stock OTA payload, and public sources.

## Short answer

**Keep the current chain.** The bootloader side works and is safe, and a
redesign would buy little. Make three small changes instead, none of which
touches a partition.

- The parts Qualcomm and ASUS own are locked by signatures and fuses. That
  covers ROM, XBL, TrustZone, the Haven hypervisor and ABL. We can't change
  them, and trying is the only real way to brick the phone.
- The only parts we control are `boot_b`, `vendor_boot_b`, `dtbo_b` and our
  own partitions. Today `boot_b` holds our ASUS 5.4 "wrapper". It picks the
  signed kernel bundle from p24 with a try-once rule and a verified fallback,
  then jumps into it with kexec.
- **The main benefit of this design:** a kernel update only writes files on
  p24. It never flashes a partition. A bad kernel falls back to `safe-r6` by
  itself, and every new kernel can be tried in RAM first (`fastboot boot`).
  Every alternative gives up part of that.
- **What the design costs:** about **16–19 s per boot** for the wrapper (the
  5.4 kernel plus the loader). A reboot takes about 75 s to Phosh and about
  100 s to `multi-user`. Booting mainline directly from ABL could save
  roughly 15 s. The price is a partition flash on every kernel update and no
  automatic fallback. A broken image could also make ABL switch to slot A
  (stock Android), and slot A formats our Linux userdata. That trade is bad.
- U-Boot or UEFI (edk2) as a middle stage would give a "standard" boot menu.
  Neither exists for the ROG5 or supports SM8350 well enough, so it would be
  a large porting project for a small gain.
- **Recommended now (low risk, no flashing):**
  1. Add a clean "Restart to fastboot" command. Today `systemctl reboot
     --reboot-argument=bootloader` loses the argument.
  2. The next time the phone is in fastboot anyway, record the slot flags
     with `getvar` (read-only), so the slot-A risk is known and not guessed.
  3. If boot time matters, work on the mainline side first. It has about
     6 s of deliberate waits in the initramfs and a slow shutdown. Those gains
     are bigger than any bootloader change and need no flashing.

## 1. The current chain, stage by stage

```
power/reset
 └ PBL (ROM) → XBL → TZ/Haven hyp/AOP …   Qualcomm/ASUS-signed, fused
    └ ABL (ASUS edk2 LinuxLoader)        signed; unlocked → "orange",
       │                                  skips AVB checks of boot/vendor_boot/dtbo
       ├ Power+Vol-Up / reboot-mode 2 → fastboot (flash, boot-from-RAM, getvar)
       └ slot B: boot_b = our 96 MiB boot-v3 image (ASUS 5.4.210 GPL kernel
          + recovery initramfs, unsigned AVB test footer); DTB from vendor_boot_b + dtbo_b
          └ recovery-init → persistent-slotb-loader:
             find UFS by exact geometry, lock disks read-only, mount p24 ro,noload,
             read selector v2 (primary r185 / fallback safe-r6, try-once),
             copy + Ed25519-verify both bundles, update the p23 try-once record,
             kexec -l, disable Haven watchdog, kexec -e
             └ mainline 7.2.7 (Image + our board.dtb + initramfs)
                └ persistent-root-init → overlay root → systemd → Phosh
```

Slot A holds stock ASUS WW (charging and rescue). Booting it formats the
Linux userdata. Trials don't touch `boot_b` at all: `fastboot boot` of a
128 MiB wrapper that embeds the signed bundle.

### Measured timings

| Stage | Time | How measured |
|---|---|---|
| Reboot: `journald` stops → mainline kernel starts | **41.3 s ± 0.4** (8 reboots today, r179–r185) | previous boot's last journal entry vs this boot's RTC-restored clock minus monotonic time (1 s RTC resolution) |
| of which: shutdown tail (`journald` stop → USB drops) | ~10–11 s (inferred) | 41.3 s minus the USB-measured 30–31 s below |
| USB drops at reset → **fastboot** USB appears | 4–5 s | ~15 `to-fastboot` runs (XBL+ABL up to the fastboot menu) |
| USB drops at reset → **wrapper** USB appears | 19–20 s | ~20 post-trial ordinary reboots in `transitions.jsonl` |
| wrapper USB → wrapper USB gone (kexec) | 10–12 s | same reboots |
| kexec → mainline USB (NCM) | 2–3 s | same reboots |
| `fastboot boot` of 128 MiB: upload | 3.0 s | 60+ trials |
| `fastboot boot`: ABL "Booting" (process + handoff) | **10.38–10.43 s, fixed** | 60+ trials; the fixed length suggests a timer (the unlocked-device warning) more than work |
| ABL handoff → wrapper USB (RAM trial) | 7–8 s | 60+ trials (5.4 kernel boot + recovery-init up to USB bind) |
| mainline kernel → `/init` | 3.7 s | dmesg (trial t170) |
| `/init` → switch_root | ~18 s | dmesg stage records; `ufs-ready` alone is 9.5 s |
| mainline kernel start → Phosh unit started | 28 s | journal (r185) |
| mainline kernel start → `multi-user.target` | 60 s (21.4 kernel+initrd + 39.2 userspace) | `systemd-analyze`, same in all 10 boots today (56.5–61.2 s) |

End to end on an ordinary reboot: **about 75 s to Phosh and 100 s to
`multi-user`**. Of that:

- **Shutdown:** about 10 s. This is the mainline side: `systemd-shutdown`
  plus the exitrd teardown of the 128 GiB overlay and loop mounts. It's
  inferred, not observed.
- **Firmware:** XBL and ABL take about 11–14 s, including ABL's normal boot
  path and its unlocked warning pause. We can't change this part.
- **Wrapper:** the 5.4 kernel plus the loader take about **16–19 s**. This
  is the only part a bootloader redesign could remove.
- **Mainline to Phosh:** about 28 s.

What the numbers can't split yet: inside the wrapper's 16–19 s, how much is
the 5.4 kernel boot and how much is the loader's work (mount, copy and verify
of 2 × 65 MB, the record write, kexec). The loader's S00–S90 progress frames
go to USB ACM `/dev/ttyGS0`, and no host log of an ordinary boot has them. A
host-only capture during one ordinary reboot would split it without changing
the phone.

## 2. What can and cannot be changed

| Component | Who signs it | Changeable? | Notes |
|---|---|---|---|
| PBL (boot ROM), QFPROM fuses | Qualcomm silicon | **No** | Secure boot is fused on retail units, so a changed XBL/ABL doesn't run: hard brick. |
| XBL, XBL config, TZ, Haven/Gunyah hyp, AOP, devcfg, keymaster, … | Qualcomm/ASUS | **No** | Linux always runs as an EL1 guest of Haven: no EL2/KVM, and the Haven vWDT (patch 0088). |
| ABL (`abl_a/abl_b`) | ASUS | **No** | Unlock only relaxes what ABL checks. The fastboot menu, reboot-mode handling, DTB selection, dtbo overlay and orange-state warning stay as ASUS built them. Hex-editing ABL (an XDA idea against the 5 s warning) breaks its signature: brick. |
| `vbmeta_b` | ASUS (checked only when locked) | Yes, pointless | Unlocked ABL logs "Device is unlocked, Skipping boot verification". |
| `boot_b` | nobody (unlocked) | **Yes** (flash) | Our wrapper. A bad image is recoverable via fastboot (Power+Vol-Up), but see the slot-A caveat below. |
| `vendor_boot_b`, `dtbo_b` | nobody (unlocked) | Yes (flash) | ABL takes the DTB from `vendor_boot` (header v3) and applies `dtbo` overlays by board id. The wrapper uses the stock ones, and mainline gets our own DTB via kexec. |
| p24 `arch_root_a` (bundles, selector), p23 userdata (records, overlay) | us (Ed25519 bundle key) | **Yes** (files) | This is where all routine updates happen. |
| slot A (`boot_a`, …) | ASUS | Don't | Stock rescue and charging route. Booting it formats Linux userdata. |

### Slot-A caveat

The ABL strings include "Alternate Slot %s is bootable", "Alternate slot %s,
New slot %s", `slot_b_retry_counter` and `slot_b_unbootable_counter`. So if
`boot_b` stops being bootable (a bad header, or repeated early failures that
ABL counts), ABL may **switch to slot A by itself**, and slot A then formats
userdata. The chain has booted slot B hundreds of times, so the normal path
is fine. But we haven't recorded `slot-successful:b`, `slot-retry-count:b`
and `slot-unbootable:*` (only `slot-unbootable:a/b = no` appears in one old
fixture). This is the main hidden risk of any `boot_b` change, and a
read-only `fastboot getvar all` the next time the phone is in fastboot
answers it.

## 3. Options

### A. Keep the chain as is (recommended)

- **Benefit.**
  - Kernel updates are file writes on p24 with a signed, try-once primary
    and a verified fallback. There's no partition flash, so there's nothing
    for ABL's slot logic to react to.
  - New kernels are RAM-trialled via `fastboot boot` with zero writes.
  - Our DTB reaches mainline exactly as built, with no ABL fixups and no
    ASUS dtbo overlays.
  - The wrapper reports early progress over USB ACM, and returns to fastboot
    on loader failure.
  - The Haven watchdog (0088) now resets a hung mainline, and the next boot
    takes the fallback.
- **Cost.** About 16–19 s per boot, and a second kernel (ASUS 5.4) to keep
  building. It's cached and reproducible, and rarely rebuilt.
- **Risk.** Lowest of all the options. `boot_b` is flashed only when the
  wrapper itself changes.

### B. Make the wrapper faster (possible; not worth a flash on its own)

Candidates:

- Drop fixed sleeps in the loader: `sleep 1` after USB, the 0.3 s and 0.5 s
  report delays, and the 0.25 s reporter loop. That's about 2 s.
- Verify the fallback lazily, after the primary. That's about 1–2 s, but it
  weakens the "fallback is known-good before we commit to anything" property.
- Slim the 5.4 config: fewer initcalls, and no UFS/USB work beyond what the
  loader needs. The gain is unknown until the S-frames are timed.

Realistic total: 3–6 s of about 75 s.

- **Cost.** A new wrapper build and a **`boot_b` flash**, which is the one
  step here that could trigger the slot-A switch.
- **Recommendation.** Only fold these in when `boot_b` has to change anyway.
  Time the S-frames first so that the change is aimed at the real
  bottleneck.

### C. Boot mainline directly from ABL (drop the wrapper and kexec)

- **Feasibility.** Probably possible, not proven on this phone.
  - ABL accepts older boot-image headers: the strings include appended-DTB
    and header-v2 DTB-offset handling.
  - The OnePlus 9 (SM8350) postmarketOS port boots mainline as a header-v2
    image with `--dtb` and an empty dtbo.
  - Our DTB would need the root `qcom,msm-id`/`qcom,board-id` that ABL
    matches. The stock values are `0x19f 0x20001 …`, board-id `0 0`. We'd
    also have to make sure no ASUS dtbo overlay applies, either through an
    empty `dtbo_b` or a board-id that matches nothing.
  - ABL would then add its own `/chosen`, memory, kaslr-seed and
    `androidboot.*` arguments.
- **Benefit.** About 15 s per boot (the wrapper time, less a little more ABL
  load time). One kernel to maintain, and no kexec.
- **Cost and risk.**
  1. **Every kernel update becomes a `boot_b` flash.** Slot A can't hold a
     second Linux, so there's no A/B, no try-once selector and no automatic
     fallback. A bad kernel means a hand reset into fastboot and a reflash,
     and a broken image may push ABL to slot A: wiped userdata.
  2. We lose the Ed25519 bundle check. It only guards against accidents,
     since root can flash `boot_b` anyway, but it has caught real mistakes.
  3. `dtbo_b` probably has to be flashed too.
  4. The hardware would start in ABL's hand-off state instead of the
     wrapper's. That state is probably fine (the Haven vWDT looks disabled
     until a kernel enables it), but it's untested.
  5. A fallback would have to be rebuilt inside mainline, which means kexec
     again.
- **Recommendation.** **No.** It trades the project's best safety property
  for about 20% of boot time. If we ever want the fact for its own sake, a
  zero-write test answers it: `fastboot boot` of a header-v2 image carrying
  mainline and our DTB with the msm-id added. A reset returns to the
  installed chain.

### D. U-Boot or UEFI (edk2) chainloaded from ABL

The idea: put U-Boot or UEFI in `boot_b`. It then boots mainline from p24
with a standard menu (extlinux or systemd-boot), boot counting, and its own
fastboot or USB mass storage.

- **State of the ecosystem.**
  - Upstream U-Boot chainloads from ABL on SDM845, QCM6490 and SM8x50
    boards, as a header-v2 boot image with the DTB appended.
  - Upstream U-Boot has **no SM8350 clock (GCC) driver**. There are drivers
    for SM8250, SM8550, SM8650 and others. Without one, UFS and USB in U-Boot
    need porting work, and there's no ROG5 board support at all.
  - UEFI ports (Renegade, now largely inactive; Project Aloha; Mu-Silicium)
    cover a few SM8350 devices. They are aimed mainly at Windows, reuse
    Qualcomm UEFI binaries pulled from device firmware, and don't cover the
    ROG5.
- **Benefit.**
  - Standard distro boot, and systemd-boot boot assessment in place of our
    selector.
  - Possibly 5–10 s faster than the wrapper, since U-Boot starts faster than
    a 5.4 kernel.
- **Cost.** Weeks of bring-up (clocks, UFS, USB, maybe display), then
  maintaining a third boot component. We'd also have to re-create our
  verified-bundle and try-once guarantees on top of it.
- **Risk.** The same `boot_b` flash risk, and bring-up bugs sit on the boot
  path.
- **Recommendation.** **No for now.** Look again only if upstream U-Boot
  gains SM8350 support, or the project wants "install any aarch64 distro"
  as a goal.

### E. lk2nd

This option doesn't apply. lk2nd targets older LK-based Qualcomm
bootloaders (MSM8916 era), not ABL on SM8350.

### F. Fastboot, update and rollback improvements (recommended)

1. **A clean "Restart to fastboot".**
   - The support is there: the DT has `reboot-mode` (`mode-bootloader = 2`,
     `mode-recovery = 1`), and `nvmem-reboot-mode` is bound on r185.
   - But the production exitrd, `initramfs/persistent-root-shutdown-standalone`,
     always ends in `busybox reboot -f` and ignores
     `/run/systemd/reboot-param`. So `systemctl reboot
     --reboot-argument=bootloader` just reboots normally.
   - The only way to fastboot today is `production-ram-trial.py to-fastboot
     --mode helper`. That calls `restart2("bootloader")` without a clean
     teardown, so userdata replays its ext4 journal on the next mount.
   - The fix: let the exitrd honour `reboot-param=bootloader`, after the same
     clean unmounts, through the existing `rog5-reboot-bootloader`. Then add a
     `rog5-reboot fastboot` command, and optionally a Phosh power-menu entry
     behind polkit.
   - This is an initramfs change (a new bundle through the normal install
     flow), with no flashing.
   - Never expose `recovery` (mode 1) or anything that leads to slot A.
2. **A one-shot "boot the fallback next time" command.** The loader already
   picks the fallback whenever the try-once record is pending and
   uncommitted. Today that takes masking the commit unit for one boot. A
   small tool that arms it and says so is safer for manual rollback tests.
3. **Record the slot state.** In the next planned fastboot visit, save
   `fastboot getvar all` (read-only) in the evidence: slot-successful,
   retry-count, unbootable for a and b, and version-bootloader. That tells us
   how close any `boot_b` mistake is to an automatic switch to slot A.
4. **Check the boot partitions for drift.** From Linux, hash `boot_b`,
   `vendor_boot_b`, `dtbo_b` and `vbmeta_b` read-only on a timer and compare
   them against the pinned values (`boot_b` is `dcc487f1…`). An accidental
   change then shows up before the next reboot depends on it. This needs a
   partition read, so it's a project decision, not something done here.
5. **p24 housekeeping.** p24 holds 97 bundles (6.5 GB). The loader only
   copies two, so this doesn't slow boot, but old bundles should be pruned
   to current, fallback, V11 and the last few defaults. The host keeps them
   anyway.
6. **(Dev loop, optional) kexec reboot from mainline.**
   - The exitrd already has a guarded `native-kexec` path, used in earlier
     Wi-Fi trials. A "warm reboot" into a new bundle would skip XBL, ABL and
     the wrapper, saving about 30 s per development reboot.
   - The risks: devices left running (GPU, ADSP/SLPI/CDSP, PCIe Wi-Fi), and
     the new boot must still go through the try-once record.
   - Useful for iteration, not as the default.

## 4. Where boot time actually goes (for context)

The bootloader side, meaning firmware plus wrapper, is about 30 s of an
ordinary reboot. The mainline side has cheaper wins that need no flashing:

- **Observation waits in `persistent-root-init`.** There's a 1 s stable
  carrier check plus `sleep 3` before the UFS probe when a USB host is
  attached, and a fixed `sleep 2` before switch_root. That's about 6 s with
  USB and 2 s without.
- **UFS readiness.** `ufs-ready` takes 9.5 s, about 4 s of it before the UFS
  PHY probe even starts.
- **Shutdown.** About 10 s from `journald` stop to reset (inferred).
- **Wi-Fi.** `rog5-wifi-radio.service` takes 26.6 s. It gates
  `multi-user.target`, but not Phosh.

## 5. Risk ladder (for any future boot change)

| Action | Worst case | Recovery |
|---|---|---|
| RAM trial (`fastboot boot`) | trial hangs | Haven watchdog or hand reset → installed chain |
| New bundle or selector on p24 | primary fails | try-once → `safe-r6`. If the loader fails, it returns to fastboot. |
| Initramfs or exitrd change (item F.1) | shutdown path misbehaves | sysrq-b fallback already in the script; next boot as usual |
| Flash `boot_b` / `vendor_boot_b` / `dtbo_b` | no boot; **ABL may switch to slot A → userdata formatted** | Power+Vol-Up → fastboot → reflash the known-good image. Userdata may be lost. |
| `set_active a` / boot slot A | userdata formatted | post-wipe restoration |
| Flash ABL/XBL/TZ/hyp/… | hard brick | EDL needs an ASUS-signed firehose we don't have. Never do this. |

## Evidence and sources

- **Phone (read-only, r185, 2026-09-29):**
  - `systemd-analyze`: 21.385 s + 39.168 s.
  - `journalctl --list-boots` plus `rog5-rtc-time` restore lines for boots
    −9…0.
  - `/proc/cmdline` (`rog5.bundle=production-7.2.7-r185
    rog5.target_timeout=600 rog5.recovery_timeout=900`).
  - Selector v2: primary r185, fallback `production-7.2.7-safe-r6`,
    `mode=try-once`.
  - `/proc/device-tree/reboot-mode`; `nvmem-reboot-mode` bound.
- **Host trial evidence.**
  - `~/.local/state/rog5-production-boot-20260923/trial-727-t105…t170/{transitions.jsonl,boot.json,stages.log,dmesg-at-health.txt}`.
- **Repository.**
  - `initramfs/persistent-slotb-loader-init`, `initramfs/recovery-init`,
    `initramfs/persistent-root-init`,
    `initramfs/persistent-root-shutdown-standalone`.
  - `tools/reboot_bootloader/rog5-reboot-bootloader.c`,
    `scripts/host/production-ram-trial.py`,
    `scripts/host/install-default-kernel.py`.
  - `docs/development.md` ("Making a production kernel the default",
    "Manual rescue"), `docs/kernel-port.md` ("Two-stage recovery boot"),
    `docs/recovery-wrapper-cache.md`,
    `test-results/2026-09-28-haven-watchdog-0088.md`.
- **Stock ABL.**
  - Extracted from the archived OTA `payload.bin` (not from the phone) and
    LZMA-unpacked, then string-inspected.
  - Its build path names a ZS676KS (ROG Phone 5s) tree, and the phone reports
    `version-bootloader Post-CS10-17-WW-user-AS`. So treat the string
    findings as indicative for this phone's ABL, not proof.
  - Stock `vendor_boot` DTB selectors come from the archived payload.
- **Public sources.**
  - U-Boot Qualcomm chainloading: <https://docs.u-boot.org/en/latest/board/qualcomm/board.html>
  - Linaro SM8x50 devboards: <https://devboardsforandroid.linaro.org/en/latest/devices/sm8x50.html>
  - FOSDEM 2024 "U-Boot for modern Qualcomm phones": <https://archive.fosdem.org/2024/events/attachments/fosdem-2024-1716-u-boot-for-modern-qualcomm-phones/slides/22104/fosdem24_aDevbas.pdf>
  - U-Boot qcom clock drivers (SM8550/8650, QCS8300 …, no SM8350): <https://www.mail-archive.com/u-boot@lists.denx.de/msg506050.html>
  - postmarketOS OnePlus 9 (SM8350) header-v2 plus `--dtb`: <https://gitlab.com/postmarketOS/pmaports/-/merge_requests/2459>
  - Mu-Silicium: <https://github.com/Project-Silicium/Mu-Silicium>
  - Renegade Project: <https://github.com/edk2-porting>
  - Qualcomm chain of trust (LineageOS): <https://lineageos.org/engineering/Qualcomm-Firmware/>
  - Orange-state 5 s warning: <https://xdaforums.com/t/patched-abl-img-to-get-rid-of-orange-state-warning.4686445/>
