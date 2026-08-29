# Active ROG Phone 5 Linux context

Updated: 2026-08-30

Read `docs/current-state.md` for the authoritative baseline. Historical
generation detail is in Git and dated `test-results/`; do not reconstruct it
in this file.

## One current question

After browser enrollment, does V10 return authenticated Tailscale and SSH
unattended across a clean reboot while preserving slot-A rescue?

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V10 boot
  `75a07173-cb47-43b1-8586-2d0ea2cdab15`; slot A remains rescue.
- V9/V10 pass systemd running, zero failed units, V49 high-speed UFS,
  zero UFS errors, NCM, stable key-only SSH, p23 state and exact write scope.
- Battery is Full/Good and safe; side USB provides positive input.
- Dedicated standalone shared mode is `10.77.0.1/30`; fixed recovery management
  remains a separate `169.254.77.1/30` profile.
- Official Tailscale 1.102.3 archive/binaries and machine state are on p23.
  V10 automatically prepares tmpfs binaries, 10.77 routing, TUN and the daemon;
  browser account login is pending.

## Just-completed checkpoint

V10 p24 transfer completed 6/6 chunks in 72.639 seconds. Automatic routing,
stable SSH, Tailscale unit/helper, UFS, systemd, storage scope and power all
pass. Backend state is `NeedsLogin`; no code or hardware blocker remains.

## Cheapest next action

1. Complete the active browser login.
2. Verify assigned Tailscale IP, control connectivity and Tailscale SSH.
3. Cleanly reboot once and prove automatic authenticated daemon return, then
   verify exact slot-A rescue at the milestone boundary.

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
- Last pushed checkpoint: `7d1b903238d036ca2df433a2636b2f3d1754afe1`.
- V10 source checkpoint: `39d1e12e217bf24b5de144e032f0ceddd8ad1717`.
- Standing GitHub authorization permits normal pushes to this branch; never
  force-push.
