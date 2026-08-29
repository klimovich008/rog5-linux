# Active ROG Phone 5 Linux context

Updated: 2026-08-29

Read `docs/current-state.md` for the authoritative baseline. Historical
generation detail is in Git and dated `test-results/`; do not reconstruct it
in this file.

## One current question

Can the accepted v8 Arch system obtain stable routed Internet through the
existing side-port NCM link while preserving charging, thermals, strict SSH,
and exact storage scope?

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Slot B Linux is running on boot
  `bf9aa234-327f-4b50-acaa-40e98a94c421`.
- Gadget: `ROG5 persistent root`, high-speed NCM, target `169.254.77.2/30`.
- Host profile `rog5-fallback-usb-ssh` autoconnects only for standalone mode
  and assigns `169.254.77.1/30`; attended recovery keeps its deferred mode.
- Systemd is `running` with zero failed units.
- Stable pinned key-only SSH passes.
- Battery is full and safe; side-port input is online.
- Target currently has no default route, so Internet access is expected to
  fail until a bounded host forwarding/NAT setup is applied.
- `/persist` has about 3.9 GiB free and `/dev/net/tun` exists.

## Just-completed checkpoint

The observer-only liveness cycle passed 7,200 target samples and 670 host
checks through 7,831 seconds target uptime. It did not reproduce the earlier
47-minute NCM timeout. Exact evidence is in
`test-results/2026-08-29-persistent-ncm-two-hour-pass.md`.

Conclusion: accept v8 for MVP development. Do not make a speculative USB
kernel or DT change. Keep the observer available for any future first failure.

## Cheapest next action

1. Record the host's current forwarding/firewall/NCM state.
2. Apply one reversible, project-scoped route/NAT configuration.
3. Add a target default route and DNS only for this live userspace test.
4. Prove outbound IP, DNS, strict SSH, charging, and thermals.
5. If those pass, download and verify the official ARM64 Tailscale package to
   persistent project storage. Do not authenticate an external account unless
   an existing project credential or explicit user interaction is available.

Changed layer is userspace/host networking only. No kernel, module, DTB,
initramfs, wrapper, trust, admission, storage-layout, or phone boot change is
needed. Use focused checks only; do not run full CI or rebuild anything.

## Stop conditions

Stop on wrong device/topology, unsafe power or temperature, a write outside
p23 service-state scope, loss of pinned SSH, ambiguous transport during a
write, or loss of slot-A rescue. Never expose credentials or private evidence.

## Git checkpoint

- Worktree: `/home/deck/.local/state/rog5-haven-clean-ci-20260810`.
- Branch: `agent/linux-recovery-host`.
- Evidence checkpoint before this compaction:
  `47676f2e7261f85431e940604ba882a7ef6b6dfe`.
- The branch is ahead of the remote and must not be pushed until the exact new
  HEAD and destination are authorized.
