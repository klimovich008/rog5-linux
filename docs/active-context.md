# Active ROG Phone 5 Linux context

Updated: 2026-08-29

Read `docs/current-state.md` for the authoritative baseline. Historical
generation detail is in Git and dated `test-results/`; do not reconstruct it
in this file.

## One current question

Can the already verified signed v9 bundle be installed into the existing p24
slot-B loader store with one bounded write and then boot repeatedly without
regressing charging, NCM, strict SSH, storage scope, or slot-A rescue?

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: A in exact fastboot after the Generation-234 fallback proof.
- Slot B retains the accepted persistent v8 Linux loader and bundle.
- Host profile `rog5-fallback-usb-ssh` autoconnects only for standalone mode
  and assigns `169.254.77.1/30`; attended recovery keeps its deferred mode.
- Generation 234 reached native p24, systemd running with zero failed units,
  high-speed NCM, bootstrap key-only SSH, and the retained stable SSH identity.
- Battery remained safe and `battery-soc-ok=yes` throughout the cycle.
- NetworkManager shared mode proved routed IP, DNS, and HTTPS over NCM. The
  separate profile remains available but normal boot restored the accepted
  manual `/30` profile.
- `/persist` recovered successfully after the old v8 UFS stall. The Tailscale
  archive remains staged but inactive.

## Just-completed checkpoint

Generation 234 is consumed. Its V49 UFS probe completed 64 MiB plus both sync
boundaries in 402 ms with zero UFS errors and exact p23 cleanup. A separate R7
cross-record parser collision rejected the valid combined log; the stable
persistent SSH key was independently matched to retained evidence before the
reviewed reboot helper returned exact slot-A fastboot. The intent resolved
`FALLBACK_RETURNED`. No p24 write occurred.

## Cheapest next action

1. Publish the consumed-policy, record-scoped parser, and compact evidence
   checkpoint.
2. Prepare one exact p24 bundle-store transaction that stages the already signed
   v9 bundle, verifies every byte and selector, syncs, and relocks p24.
3. Boot slot B, prove the V49 module is deployed, repeat systemd/NCM/SSH/power
   checks, then resume the staged Tailscale installation.

The live kernel result is complete. Reuse the existing signed v9 bundle and
stable slot-B loader; no kernel, DT, wrapper, GPT, or boot-partition rebuild is
needed.

## Stop conditions

Stop on wrong device/topology, unsafe power or temperature, a write outside
p23 service-state scope, loss of pinned SSH, ambiguous transport during a
write, or loss of slot-A rescue. Never expose credentials or private evidence.

## Git checkpoint

- Worktree: `/home/deck/.local/state/rog5-haven-clean-ci-20260810`.
- Branch: `agent/linux-recovery-host`.
- Last pushed checkpoint: `0403d2bf6253b58730793b21dd1ceebbc39eb6c3`.
- Standing GitHub authorization permits normal pushes to this branch; never
  force-push.
