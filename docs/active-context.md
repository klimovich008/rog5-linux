# Active ROG Phone 5 Linux context

Updated: 2026-08-31

Read `docs/current-state.md` for the baseline and the latest V11 live result.
Historical generations remain in Git; do not reconstruct them here.

## One current question

Complete the cache-coherent1350mV kernel/module path, then resume Wi-Fi radio
bring-up. V13 proved the exact OEM request on hardware and is consumed.
The new kernel and base module kit pass clean comparison/QEMU; no successor
is admitted. Physical cache-coherent power and radio qualification remain.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V11 boot
  `bdd1dd29-1def-4864-9d86-109ec9876137`; slot A remains rescue.
- V11 passes initial systemd running, V49 high-speed UFS, zero UFS errors,
  NCM, stable key-only SSH, p23 state and exact two-node write scope.
- Latest battery read: Full/Good, 8.613 V, 30.1°C; state/Tailscale restored.
- Temporary source ACM disappeared on reboot; V11 currently exposes NCM only.
- Standalone shared mode is `10.77.0.1/30` → `10.77.0.2/30`. Fixed recovery
  management remains a separate `169.254.77.1/30` profile.
- Tailscale 1.102.3 starts automatically from p23 state. It is enrolled and
  online, with no health warnings; its identity survived normal systemd reboot.
- The empty runtime package keyring causes a separate background WKD parser
  failure. Initial systemd checks are not a long-soak zero-failure claim.

## Just-completed checkpoint

V13 passed low hold, exact1350mV write, raw1350 readback, three direct UFS reads
and NCM. Normal reboot restored V11. No PCIe/radio was activated; all trials
through V13 are consumed. See `test-results/2026-08-31-s12-oem.md`.

## Cheapest next action

1. Reuse source1eea8970e87f and its qualified archived kit; do not rebuild it.
   Clean twins and cached Image match; base19/Wi-Fi37 module packages and
   initramfs twins match; exact-Image QEMU loads all required roots. Add the
   existing diagnostic module patches before passing observation parameters.
   Update active target release checks from the signed plan, not stale literals.
   The S12 module uses the regulator API and requires point support plus
   readback/cache consistency. Qualify that before conditional radio activation.
   Keep the low hold, all117-RO/power/identity gates and matched write ACKs.
   No new-kernel boot is admitted. OF dynamic/overlay APIs are available for
   evaluating controlled radio-node activation. Check one-syscall module-load
   behavior: the BusyBox wrong-board fixture retried its initializer.
   Restore shared host networking after fallback;
   reuse the fixed missing-interface helper and two-release stage parser.
   Preserve archives/source; disk headroom remains low. Add an explicit test
   temporary-parent option for RAM scratch; do not repurpose HOME.
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
