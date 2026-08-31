# Active ROG Phone 5 Linux context

Updated: 2026-08-31

Read `docs/current-state.md` for the baseline and the latest V11 live result.
Historical generations remain in Git; do not reconstruct them here.

## One current question

Can the exact OEM1350mV request be established after the proven1224mV hold,
without the mainline selector silently changing it to1352mV? Re-vote-v12
passed and is consumed. No higher-voltage/radio trial is admitted yet.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V11 boot
  `04128e6c-c09b-4ddc-83eb-cdaad89e87a5`; slot A remains rescue.
- V11 passes initial systemd running, V49 high-speed UFS, zero UFS errors,
  NCM, stable key-only SSH, p23 state and exact two-node write scope.
- Latest battery read: Full/Good, 8.614 V, 30.1°C; state/Tailscale restored.
- Temporary source ACM disappeared on reboot; V11 currently exposes NCM only.
- Standalone shared mode is `10.77.0.1/30` → `10.77.0.2/30`. Fixed recovery
  management remains a separate `169.254.77.1/30` profile.
- Tailscale 1.102.3 starts automatically from p23 state. It is enrolled and
  online, with no health warnings; its identity survived normal systemd reboot.
- The empty runtime package keyring causes a separate background WKD parser
  failure. Initial systemd checks are not a long-soak zero-failure claim.

## Just-completed checkpoint

Re-vote-v12 passed query, AUTO, voltage1224/enable1 writes, post-readback and
three direct1MiB UFS reads. NCM survived; normal reboot restored V11/Tailscale.
Voltage raw changed0x4c8→0x800004c8; do not call this a proved electrical no-op.
All trials through re-vote-v12 are consumed. No PCIe/radio was activated.
See `test-results/2026-08-31-s12-revote.md`.

## Cheapest next action

1. Reuse the qualified readback kernel/kit; no ASUS wrapper rebuild. The retained
   vendor VRM setter accepts millivolt-rounded requests, unlike the mainline
   8mV selector grid. Stock CNSS asks for1350mV. Qualify that exact request
   after the proven low-voltage hold before any radio operation. Do not infer
   a physical reset cause from V12: kernel/DT also differed from V10.
   Keep fresh raw gates, explicit write-origin ACKs, all117-RO checks and hold
   retention. Never seed global regulator caches or reparent shared rails.
   Restore the existing shared host profile after fallback. Reuse the fixed
   missing-interface-tolerant helper and two-release stage parser.
   The module kit is restored in RAM; full kernel cache and signed base are
   archived. Keep existing work; disk headroom is low. Preserve V11 and slot A.
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
