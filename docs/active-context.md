# Active ROG Phone 5 Linux context

Updated: 2026-08-31

Read `docs/current-state.md` for the baseline and the latest V11 live result.
Historical generations remain in Git; do not reconstruct them here.

## One current question

Can the first S12 enable preserve its measured 1.224 V APPS vote before Wi-Fi requests a higher voltage? Readback-v11 passed and is consumed; no new power-setting trial is admitted.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V11 boot
  `19c698fe-513d-468b-ada3-485a5902fa5e`; slot A remains rescue.
- V11 passes initial systemd running, V49 high-speed UFS, zero UFS errors,
  NCM, stable key-only SSH, p23 state and exact two-node write scope.
- Latest battery read: Full/Good, 8.618 V, 30.0°C; state/Tailscale restored.
- Temporary source ACM disappeared on reboot; V11 currently exposes NCM only.
- Standalone shared mode is `10.77.0.1/30` → `10.77.0.2/30`. Fixed recovery
  management remains a separate `169.254.77.1/30` profile.
- Tailscale 1.102.3 starts automatically from p23 state. It is enrolled and
  online, with no health warnings; its identity survived normal systemd reboot.
- The empty runtime package keyring causes a separate background WKD parser
  failure. Initial systemd checks are not a long-soak zero-failure claim.

## Just-completed checkpoint

Readback-v11 booted the new kernel, Arch, NCM/UFS/SSH and read all six votes.
S12: 1224mV, enable1, retention3; these are APPS votes, not physical measurements.
No S12 writes appeared in the trace. Normal reboot restored V11 and Tailscale.
All trials through readback-v11 are permanently consumed. See
`test-results/2026-08-31-rpmh-readback-development.md`.

## Cheapest next action

1. Use the now-qualified readback kernel/module ABI for the next bounded
   S12 handoff experiment; do not recompile the ASUS wrapper. The current
   driver caches DT-min1352mV while enabled-state is unknown, then writes it
   on first enable. Captured APPS state was already enabled at1224mV/RET3.
   This mismatch is proven; its relationship to the earlier reset is not.
   Preserve the measured vote before considering another increase. Do not
   activate radio at an unqualified voltage or reparent shared rails.
   Stock CNSS requests1350mV; the mainline selector rounds to1352mV. Reconcile
   that contract separately. V9 AUTO-only passed; V10 AUTO+first-enable reset.
   Preserve fixtures and `test-results/2026-08-31-native-wifi-s12-shared-rail.md`.
   Future readers must accept the exact trial and V11 fallback releases;
   restore the existing shared host profile after fallback identity proof.
   Kernel/config/module twins and full A object cache are archived; RAM scratch
   was released. Disk headroom remains low. Preserve V11 and slot A.
2. The userspace validation client is online; finish its SSH sign-in check and test
   peer-to-phone Tailscale SSH. Do not re-enroll the phone or treat self-ping as
   peer evidence. Log out/remove the temporary client after successful testing.
3. Package-keyring work is preserved at `b9ceb26`: helper/unit and focused test
   pass, but it is not deployed or integrated into boot. Resume it when needed
   for signed Wi-Fi userspace packages; preserve package-signature enforcement.
4. Continue loaded Wi-Fi/power checks and the remaining standalone server MVP.

Opus retry confirmed expired OAuth; no review produced. Retain V11/V10, the stable loader, module kit and compressed V11 image: no GPT or experimental boot-partition flash.
Do not repeat the completed p24 transfer or successful builds.

## Boundaries and Git

Stop on wrong device/topology, unsafe power/temperature, writes outside the
reviewed scope, ambiguous transport during a write or loss of slot-A rescue.
Never expose credentials or private evidence, or retry ambiguous execution.

- Worktree: `/home/deck/.local/state/rog5-haven-clean-ci-20260810`.
- Branch: `agent/linux-recovery-host`; normal pushes authorized, never force-push.
- V11 executable source: `7f7621ce0a11a624d703200e5a65c03127802736`.
- Resolve publication from Git and exact-head CI, not copied last-pushed fields.
