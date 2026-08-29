# Active ROG Phone 5 Linux context

Updated: 2026-08-29

Read `docs/current-state.md` for the authoritative baseline. Historical
generation detail is in Git and dated `test-results/`; do not reconstruct it
in this file.

## One current question

Does replacing only the stale persistent v8 UFS core module with the proven
V49 high-speed module eliminate the p23 write/flush stall while preserving
charging, NCM, strict SSH, exact storage scope, and fallback?

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
- NetworkManager shared mode proved routed IP, DNS, and HTTPS over NCM. The
  separate profile remains available but normal boot restored the accepted
  manual `/30` profile.
- `/persist` recovered successfully after one UFS write stall. The Tailscale
  archive is staged there but must not be started or trusted as installed until
  the corrected module passes a bounded storage test.

## Just-completed checkpoint

The observer-only liveness cycle passed 7,200 target samples and 670 host
checks through 7,831 seconds target uptime. It did not reproduce the earlier
47-minute NCM timeout. Exact evidence is in
`test-results/2026-08-29-persistent-ncm-two-hour-pass.md`.

Conclusion: accept v8 for MVP development. Do not make a speculative USB
kernel or DT change. Keep the observer available for any future first failure.

## Cheapest next action

1. Make persistent initramfs assembly reject stale low-speed UFS modules.
2. Reuse the clean-twin V49 four-module closure; only `ufshcd-core.ko` differs.
3. Rebuild only the target initramfs and signed target bundle.
4. Run focused ABI/vermagic/BTF/closure tests plus the active tier.
5. Temporarily boot once and perform one bounded p23 write/flush test with
   adjacent NCM, charging, thermal, strict-SSH, relock, and fallback evidence.

Changed layer is kernel module plus target initramfs composition. Reuse the
existing Image, DTB, stable recovery, wrapper cache, power modules, and root.
No broad kernel build, DT change, wrapper rebuild, GPT change, or flash is
needed for the discriminating cycle.

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
