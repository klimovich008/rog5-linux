# Documentation index

Status lives in one place: [current-state.md](current-state.md), whose
generated block comes from [status/components.json](status/components.json).
When another document disagrees with it, current state wins.

## Start here

- [install-guide.md](install-guide.md): installing on a ROG Phone 5 (all variants), with the
  steps that are scripted, manual or still missing; [fresh-install-rehearsal.md](fresh-install-rehearsal.md)
  is the from-scratch rehearsal and the gap list.

- [current-state.md](current-state.md): installed default and fallback, component status, where to look.
- [whats-left.md](whats-left.md): the short list, the status map and the tests that need the user.
- [user-irritations.md](user-irritations.md): the top annoyances with causes and fixes.
- [development.md](development.md): development loop, builds, RAM trials, making a kernel the default, unattended updates, manual rescue.
- [development-lessons.md](development-lessons.md): recorded failure patterns and checklists; grep for the issue at hand.
- [active-context.md](active-context.md): short pointer (a required entry point).

## Hardware

- [hardware/stock-comparison-plan.md](hardware/stock-comparison-plan.md): stock ASUS 5.4 kernel versus the 7.2.7 production kernel (2026-09-27).
- [hardware/hardware-contract.md](hardware/hardware-contract.md): redacted hardware summary from the stock device tree.
- [hardware/stock-image-analysis.md](hardware/stock-image-analysis.md): unpacking and DT comparison of stock ASUS images.
- [hardware/bootloader-assessment.md](hardware/bootloader-assessment.md): bootloader behaviour and limits.
- [hardware/audio-plan.md](hardware/audio-plan.md): audio hardware (external amplifiers over MI2S/I2C).
- [hardware/front-touch-prototype.md](hardware/front-touch-prototype.md): FTS3658U touch driver.
- [hardware/vcnl36866-als-proximity.md](hardware/vcnl36866-als-proximity.md): light/proximity sensor port.

## Boot chain, storage and recovery

- [recovery-bundle-contract.md](recovery-bundle-contract.md): signed runtime-bundle format and its verifier (`rog5-bundle-verify`).
- [storage-trust-boundary.md](storage-trust-boundary.md): UFS and writable-runtime trust boundary.
- [post-wipe-restoration.md](post-wipe-restoration.md): rebuilding the Linux environment after a factory reset.
- [asus-charging-recovery.md](asus-charging-recovery.md): the completed stock charging repair; guard against repeating it.

## Remote access and licensing

- [security-automation.md](security-automation.md): account boundary for remote AI clients and personal data.
- [licensing-provenance.md](licensing-provenance.md): licensing and provenance inventory.
- Remote desktop today: the headless Sway virtual desktop and the wayvnc phone
  mirror (`configs/rog5-desktop`, `configs/systemd-user`), reached over SSH.
  VNC has no password, so both listen only on Unix sockets in the phone
  user's runtime directory (no TCP port): forward one with
  `ssh -N -L 5900:/run/user/1000/rog5-vnc-phone.sock root@10.77.0.2` (the
  virtual desktop: `rog5-vnc-desktop.sock`) and connect a VNC client to
  `localhost:5900`. `rog5-desktop status` prints both commands.

## Reviews

External read-only reviews, each brief with the reviewer's answer:

- [2026-09-28 brief](reviews/2026-09-28-external-review-brief.md) and [answer](reviews/2026-09-28-gpt-6-astra-review.md): storage rollback, watchdog lifecycle, suspend.
- [2026-09-29 brightness brief](reviews/2026-09-29-brightness-review-brief.md) and [answer](reviews/2026-09-29-gpt-6-astra-brightness-review.md).
- [2026-09-29 DisplayPort brief](reviews/2026-09-29-dp-review-brief.md) and [answer](reviews/2026-09-29-gpt-6-astra-dp-review.md).
- [2026-09-30 device-profile brief](reviews/2026-09-30-device-profile-brief.md) and [answer](reviews/2026-09-30-gpt-6.1-sol-device-profile.md): per-phone values in the boot sources.
- [2026-09-30 install-guide brief](reviews/2026-09-30-install-guide-brief.md) and [answer](reviews/2026-09-30-gpt-6.1-sol-install-guide.md).
- [2026-10-01 device-profile follow-up brief](reviews/2026-10-01-device-profile-followup-brief.md) and [answer](reviews/2026-10-01-gpt-6.1-sol-device-profile-followup.md).

## History

[history/](history/) keeps superseded documents as they were: the
July-September status log (`history/current-state-log-2026-07-to-09.md`), the
7.1.4, network-root, headless-server and recovery-era documents, the Codex
era, the repository restructure plan and the
[2026-09-29 cleanup](history/cleanup-2026-09-29.md) with the list of archived
files ([history/archived-files.tsv](history/archived-files.tsv)). Test results
are indexed by month in [../test-results/README.md](../test-results/README.md).
