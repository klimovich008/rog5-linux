# Active ROG Phone 5 Linux context

Updated: 2026-08-30

Read `docs/current-state.md` for the authoritative baseline. Historical
generation detail is in Git and dated `test-results/`; do not reconstruct it
in this file.

## One current question

Does V10 automatically restore the fixed standalone route and start authenticated
Tailscale from p23 while preserving the accepted V9 kernel, power, storage,
SSH, reboot and slot-A rescue behavior?

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running accepted persistent V9 boot
  `6e9cd42b-4419-41e8-b279-7a3076666ea1`; slot A remains rescue.
- V9 twice passed systemd running, zero failed units, V49 high-speed UFS,
  zero UFS errors, NCM, stable key-only SSH, p23 state and exact write scope.
- Battery is Full/Good and safe; side USB provides positive input.
- Dedicated standalone shared mode is `10.77.0.1/30`; fixed recovery management
  remains a separate `169.254.77.1/30` profile.
- Official Tailscale 1.102.3 archive/binaries and machine state are on p23.
  The same-boot exact helper and transient daemon pass; account login is pending.

## Just-completed checkpoint

Signed V10 bundle twins verify at manifest `307883f5…2970`; target initramfs
twins are `db249f8c…02fb`. The V10 p24 sparse image is `915b4a32…899e`,
unchanged geometry with 3,032,543,232 allocated bytes independently matched.
Focused, initramfs and active tiers pass. No V10 phone write has occurred.

## Cheapest next action

1. Publish the exact V10 source checkpoint and require exact-head GitHub CI.
2. Cleanly stop V9, select slot A, transfer only the verified V10 p24 sparse,
   restore slot B, and prove automatic Tailscale service startup.
3. Complete browser login, verify Tailscale IP/SSH, reboot once, and prove the
   daemon and authenticated state return unattended.

The live kernel result is complete. Reuse the existing signed V9/V10 bundle and
stable slot-B loader; no kernel, DT, wrapper, GPT, or boot-partition rebuild is
needed.

## Stop conditions

Stop on wrong device/topology, unsafe power or temperature, a write outside
p23 service-state scope, loss of pinned SSH, ambiguous transport during a
write, or loss of slot-A rescue. Never expose credentials or private evidence.

## Git checkpoint

- Worktree: `/home/deck/.local/state/rog5-haven-clean-ci-20260810`.
- Branch: `agent/linux-recovery-host`.
- Last pushed checkpoint: `e9d4409db1a55acd7b302eccca40ca39656bbdd0`.
- V10 source checkpoint: `39d1e12e217bf24b5de144e032f0ceddd8ad1717`.
- Standing GitHub authorization permits normal pushes to this branch; never
  force-push.
