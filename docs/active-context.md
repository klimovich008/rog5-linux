# Active ROG Phone 5 Linux context

Updated: 2026-08-30

Read `docs/current-state.md` for the baseline and the latest V11 live result.
Historical generations remain in Git; do not reconstruct them here.

## One current question

Can an independently authenticated Tailscale peer reach the enrolled phone by
SSH? The kernel firewall and installed normal-reboot defects are fixed.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V11 boot
  `9c752d3d-c7c0-490c-a074-ed73029358b3`; slot A remains rescue.
- V11 passes initial systemd running, V49 high-speed UFS, zero UFS errors,
  NCM, stable key-only SSH, p23 state and exact two-node write scope.
- Battery Full/Good, 100%, 8.659 V, 29.9°C; side USB provides positive input.
- Standalone shared mode is `10.77.0.1/30` → `10.77.0.2/30`. Fixed recovery
  management remains a separate `169.254.77.1/30` profile.
- Tailscale 1.102.3 starts automatically from p23 state. It is enrolled and
  online, with no health warnings; its identity survived normal systemd reboot.
- Initial clock is stale, then automatic NTP succeeds before Tailscale connects.
- The empty runtime package keyring causes a separate background WKD parser
  failure. Initial systemd checks are not a long-soak zero-failure claim.

## Just-completed checkpoint

Clean twins match for Image, vmlinux, all 19 modules, initramfs and signatures.
QEMU loads every module and proves the nft check fails on V10 but passes on V11.
Full local and exact-head/merge/QEMU GitHub CI pass for source `7f7621c`.
The p24-only update took 72.816s. The installed standalone shutdown helper
returned Linux without fastboot intervention. See
`test-results/2026-08-30-persistent-tailscale-v11-live.md`.

## Cheapest next action

1. Finish the existing userspace validation client's account login and test
   peer-to-phone Tailscale SSH. Do not re-enroll the phone or treat self-ping as
   peer evidence. Log out/remove the temporary client after successful testing.
2. Repair package-keyring initialization as a userspace/state task, not another
   kernel rebuild. Preserve package-signature enforcement.
3. Continue loaded network/power checks and the remaining standalone server MVP.

Retain V10 and the stable slot-B loader; no DT, wrapper, GPT, or boot-partition
change is needed. Preserve the exact rebuilt module kit and compressed V11 p24
image. Do not repeat the completed p24 transfer.

## Boundaries and Git

Stop on wrong device/topology, unsafe power/temperature, writes outside the
reviewed scope, ambiguous transport during a write or loss of slot-A rescue.
Never expose credentials or private evidence, or retry ambiguous execution.

- Worktree: `/home/deck/.local/state/rog5-haven-clean-ci-20260810`.
- Branch: `agent/linux-recovery-host`; normal pushes authorized, never force-push.
- V11 executable source: `7f7621ce0a11a624d703200e5a65c03127802736`.
- Resolve publication from Git and exact-head CI, not copied last-pushed fields.
