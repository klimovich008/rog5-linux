# Historical project context

These immutable snapshots preserve superseded active instructions at checkpoint
`c5ff2e327b1e2754db49e602576032c406ae43b1`:

- [Original README](https://github.com/klimovich008/rog5-linux/blob/c5ff2e327b1e2754db49e602576032c406ae43b1/README.md)
- [Original roadmap](https://github.com/klimovich008/rog5-linux/blob/c5ff2e327b1e2754db49e602576032c406ae43b1/ROADMAP.md)
- [Previous current state](https://github.com/klimovich008/rog5-linux/blob/c5ff2e327b1e2754db49e602576032c406ae43b1/docs/current-state.md)
- [Previous active context](https://github.com/klimovich008/rog5-linux/blob/c5ff2e327b1e2754db49e602576032c406ae43b1/docs/active-context.md)

Recover offline with `git show c5ff2e32:PATH`. Do not use historical
permissions, fallback assumptions or candidate states as current instructions.
The dated reports in `test-results/` remain intact.

Large host build archives are private and outside Git. Their archive hashes,
original paths, verification and restoration commands belong in the private
retention record; the redacted consolidation report records measured savings.

## Superseded documents (archived 2026-09-29)

These documents describe the July/August 2026 flows (minimal headless server,
network root, recovery candidates, the stable-recovery wrapper era, early
storage and UI plans) that the production slot-B boot chain replaced. Their
status lines are historical; nothing here is a current instruction. Current
work starts at [current state](../current-state.md) and the
[documentation index](../README.md).

Minimal headless server and early userspace:

- [minimal-headless-host-key-bootstrap.md](minimal-headless-host-key-bootstrap.md): volatile SSH host-key pinning for the credential-free minimal root.
- [minimal-headless-runtime-acceptance.md](minimal-headless-runtime-acceptance.md): runtime gate for one live SSH observation of the minimal root.
- [headless-key-indicator.md](headless-key-indicator.md): power-key status indication for a screen-off headless phone.
- [buttons-indicator.md](buttons-indicator.md): Linux 7.1.4 buttons and status-LED candidate (offline-ready, never qualified).
- [battery-telemetry-series.md](battery-telemetry-series.md): read-only battery-series oracle for the minimal headless candidate.
- [dual-cell-readonly-telemetry.md](dual-cell-readonly-telemetry.md): compile-only dual-cell voltage telemetry candidate.
- [power-display-ui.md](power-display-ui.md): KDE Plasma / KRDP UI and power plan (replaced by Phosh and GNOME desktop mode).
- [a660-acceptance.md](a660-acceptance.md): offline A660 accelerated-desktop acceptance contract from before the GPU worked.

Recovery candidates and the wrapper era:

- [early-target-diagnostics.md](early-target-diagnostics.md): diagnostic-initramfs successor after Generation 12.
- [recovery-ncm-progress.md](recovery-ncm-progress.md): recovery NCM progress channel and Generation-11 wrapper.
- [recovery-refreeze-integration.md](recovery-refreeze-integration.md): plan to replace the v18 interactive recovery with a frozen framed platform.
- [recovery-fetch-contract.md](recovery-fetch-contract.md): fixed recovery bundle transport (`rog5-bundle-fetch`).
- [stable-wrapper-config-slimming.md](stable-wrapper-config-slimming.md): compile-only slim-config experiment for the ASUS 5.4 wrapper.
- [recovery-dts.md](recovery-dts.md): compile-only ASUS recovery DTS skeleton (UFS and USB disabled).
- [ufs-discovery.md](ufs-discovery.md): read-only UFS discovery gate between RAM recovery and the first native root.

Storage and process:

- [persistent-storage.md](persistent-storage.md): early persistent-storage and rollback design (Alpine fallback on `userdata`).
- [storage-migration-phase1.md](storage-migration-phase1.md): storage migration Phase 1 while development was still RAM-booted.
- [operator-standing-authorization.md](operator-standing-authorization.md): Codex-era standing authorization (replaced by the project `CLAUDE.md`).
- [repository-audit-2026-07-28.md](repository-audit-2026-07-28.md): repository audit and reduction plan of 2026-07-28.
