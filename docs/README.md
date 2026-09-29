# Documentation index

Many documents below were written during earlier project phases (Linux 7.1.4,
network root, minimal headless server) and keep their original status lines.
When a document disagrees with [current state](current-state.md), current
state wins. Documents marked *(historical)* describe superseded flows and are
kept because tests or other records still refer to them.

## Start here

- [current-state.md](current-state.md): authoritative handoff; read the generated status block at the top, then grep the long log below it.
- [development.md](development.md): development loop, commands and tests, fast module loop, making a kernel the default, unattended updates, manual rescue.
- [port-status.md](port-status.md): per-subsystem port status table (5.4 baseline versus mainline).
- [development-lessons.md](development-lessons.md): prevention guide of recorded failure patterns and pre-build / pre-live checklists; grep for the issue at hand.

## Development and build

- [builds-and-artifacts.md](builds-and-artifacts.md): version strategy, inputs kept in Git and required build artifacts.
- [kernel-port.md](kernel-port.md): Linux 7.x board-port plan and source-reuse assessments.
- [arch-linux.md](arch-linux.md): Arch Linux ARM userspace image contract (written for the SSH-only server profile).
- [test-plan.md](test-plan.md): *(historical)* detailed tiered test plan; still documents the `quick` tier prerequisites.
- [release-acceptance.md](release-acceptance.md): headless server release acceptance contract and `rog5-dev accept` commands.
- [core-compatibility-oracle.md](core-compatibility-oracle.md): machine-enforced contract derived from ASUS 5.4 behavior for new kernel candidates.
- [core-source-dtb-contract.md](core-source-dtb-contract.md): checks that a kernel source tree still contains the drivers and bindings the DTB needs.
- [artifact-retention.md](artifact-retention.md): retained artifact identities and the artifact-set inventory.
- [repository-governance.md](repository-governance.md): proposed branch protection and required CI checks.
- [steam-deck-host.md](steam-deck-host.md): Steam Deck setup as the x86_64 cross-build and analysis host.
- [host-storage-cleanup.md](host-storage-cleanup.md): plan-driven cleanup of reproducible host build state.
- [licensing-provenance.md](licensing-provenance.md): licensing and provenance inventory; unresolved distribution work.
- [godshell.md](godshell.md): evaluation of the GodShell eBPF observability tool.

## Hardware bring-up

- [hardware-contract.md](hardware-contract.md): redacted hardware summary from the running stock device tree.
- [stock-image-analysis.md](stock-image-analysis.md): offline unpacking and device-tree comparison of stock ASUS images.
- [stock-comparison-plan.md](stock-comparison-plan.md): consolidated plan from comparing the stock ASUS 5.4 kernel with the 7.2.7 production kernel (2026-09-27).
- [audio-plan.md](audio-plan.md): audio hardware research (external amplifiers over MI2S/I2C).
- [front-touch-prototype.md](front-touch-prototype.md): FTS3658U front-touch prototype driver and disabled DT candidate.
- [vcnl36866-als-proximity.md](vcnl36866-als-proximity.md): VCNL36866 ambient-light/proximity sensor port contract.

## Boot chain and recovery

- [recovery-wrapper-cache.md](recovery-wrapper-cache.md): reproducible cache of the ASUS 5.4 recovery wrapper builds.
- [recovery-bundle-contract.md](recovery-bundle-contract.md): first signed runtime-bundle format for stable recovery and its verifier (`rog5-bundle-verify`).
- [recovery-control-plane.md](recovery-control-plane.md): *(historical)* framed recovery control plane and diagnostic generations 0-12.
- [reusable-recovery-claim-model.md](reusable-recovery-claim-model.md): reusable recovery transport versus one-use target claims.
- [storage-trust-boundary.md](storage-trust-boundary.md): UFS discovery and writable-runtime trust boundary audit.
- [dedicated-linux-layout-v1.md](dedicated-linux-layout-v1.md): unexecuted proposal for a dedicated Linux partition layout.
- [post-wipe-restoration.md](post-wipe-restoration.md): private bundle for rebuilding the Linux environment after a factory reset.
- [asus-charging-recovery.md](asus-charging-recovery.md): completed repair of stock charging (`super` metadata); guard against repeating it.
- [minimal-headless-live-cycle.md](minimal-headless-live-cycle.md): *(historical)* one-shot temporary-boot lifecycle runbook.
- [network-root.md](network-root.md): *(historical)* first full-distribution boot over a USB network root.

## Server and networking

- [remote-gui.md](remote-gui.md): loopback-only remote tools reached through SSH forwarding.
- [security-automation.md](security-automation.md): account boundary for remote AI clients and personal data.

## Power

- [mobile-power-policy.md](mobile-power-policy.md): proposed battery-only mobile power and session policy.
- [mobile-trial-plans.md](mobile-trial-plans.md): prepared offline plans for mobile hardware questions.
- [thermal-policy-static-oracle.md](thermal-policy-static-oracle.md): regression gate for the thermal topology in kernel source, config and DTB.

## Reviews

External read-only reviews: each brief and the reviewer's answer.

- [2026-09-28 external review brief](reviews/2026-09-28-external-review-brief.md) and [answer](reviews/2026-09-28-gpt-6-astra-review.md): week of 2026-09-22 (storage rollback, watchdog lifecycle, suspend conclusions).
- [2026-09-29 brightness review brief](reviews/2026-09-29-brightness-review-brief.md) and [answer](reviews/2026-09-29-gpt-6-astra-brightness-review.md): coarse AMOLED brightness steps.
- [2026-09-29 DisplayPort review brief](reviews/2026-09-29-dp-review-brief.md) and [answer](reviews/2026-09-29-gpt-6-astra-dp-review.md): DP alt mode trains but the monitor does not lock.

## History and archive

- [archive/README.md](archive/README.md): superseded documents (minimal headless, network root, recovery candidates, wrapper era, early storage and UI plans) and historical snapshots.
- [archive-index.md](archive-index.md): the `archive/pre-stable-recovery-2026-07-28` tag that preserves the pre-reduction repository.
- [history/codex-era.md](history/codex-era.md): what the user asked for during the Codex era (2026-07-30 to 2026-09-22).
- [active-context.md](active-context.md): short pointer to current state (kept as a required entry point).
