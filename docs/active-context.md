# Active ROG Phone 5 Linux context

Updated: 2026-08-30

Read `docs/current-state.md` for the authoritative baseline. Historical
generation detail is in Git and dated `test-results/`; do not reconstruct it
in this file.

## One current question

Does the narrow conntrack-mark kernel correction and restored standalone
exitramfs provide clean Tailscale firewall health and unattended reboot?

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V10 boot
  `2ca47654-0f36-42bf-8f20-12be0d5b9e98`; slot A remains rescue.
- V9/V10 pass systemd running, zero failed units, V49 high-speed UFS,
  zero UFS errors, NCM, stable key-only SSH, p23 state and exact write scope.
- Battery is Full/Good and safe; side USB provides positive input.
- Dedicated standalone shared mode is `10.77.0.1/30`; fixed recovery management
  remains a separate `169.254.77.1/30` profile.
- Official Tailscale 1.102.3 archive/binaries and machine state are on p23.
  V10 automatically prepares tmpfs binaries, 10.77 routing, TUN and the daemon;
  enrollment is complete and persisted across a RAM-corrected normal reboot.

## Just-completed checkpoint

V10 is enrolled and online. Its default iptables MARK backend fails; native
nftables proves the remaining NF_CONNTRACK_MARK kernel gap. QEMU reproduces
the same failure with the exact deployed Image. Clean A fixes that check and
loads all 19 modules in QEMU. Independent clean B is running; the new kernel
has not contacted the phone. Later systemd degradation is a separate keyring
refresh parser error, recorded in the enrollment/reboot result.

V10's generic builder also replaced the standalone exitramfs with diagnostic
fastboot shutdown. The existing standalone builder is corrected. The reviewed
RAM-only helper returned enrolled V10 in about 60 seconds, but installed V10
still needs the release correction. See the enrollment/reboot result record.

## Cheapest next action

1. Finish clean connmark kernel twins and the matching QEMU capability check.
2. Prove the deployed power/UFS module code and BTF/ABI closure before admission.
3. Publish one corrected standalone bundle, then validate reboot and rescue.
4. Test encrypted peer SSH with another authenticated tailnet node.

Retain V10 and the stable slot-B loader; no DT, wrapper, GPT, or boot-partition
change is required. Only NF_CONNTRACK_MARK and its dependent module metadata
may change in the kernel build. Reuse the reviewed standalone shutdown code.

## Stop conditions

Stop on wrong device/topology, unsafe power or temperature, a write outside
p23 service-state scope, loss of pinned SSH, ambiguous transport during a
write, or loss of slot-A rescue. Never expose credentials or private evidence.

## Git checkpoint

- Worktree: `/home/deck/.local/state/rog5-haven-clean-ci-20260810`.
- Branch: `agent/linux-recovery-host`.
- Resolve the exact published checkpoint from Git and exact-head CI.
- V10 source checkpoint: `39d1e12e217bf24b5de144e032f0ceddd8ad1717`.
- Standing GitHub authorization permits normal pushes to this branch; never
  force-push.
