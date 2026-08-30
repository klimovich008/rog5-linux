# Active ROG Phone 5 Linux context

Updated: 2026-08-30

Read `docs/current-state.md` for the baseline and the latest V11 live result.
Historical generations remain in Git; do not reconstruct them here.

## One current question

Which board-specific power transition causes the reset after endpoint power-on
is entered? Observe-v3 proves the client probe and device creation complete.
MHI initialization alone passes on V11. Wi-Fi remains the active requirement.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V11 boot
  `22963cf0-b453-444d-89e3-3444a41d1d29`; slot A remains rescue.
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

V11's installed firewall and normal reboot pass; see its live result.
The first Wi-Fi builder pass completed in 71.47s without rebuilding V11.
The complete set now contains 22 modules, including dynamic signature/cipher
dependencies. QEMU accepts valid regulatory data, rejects tampering and proves
the requested Wi-Fi crypto transforms. The native Wi-Fi DTB preserves unrelated
state and uses stock-derived, selector-valid voltage intervals. Its RAM trial
booted Arch/UFS/USB/SSH, but PCIe activation reset the phone before Wi-Fi worked.
Firmware matches the prior verified set. See
`test-results/2026-08-30-native-wifi-offline.md`.

All three native Wi-Fi trials, through observe-v3, are permanently consumed. Source
`abf3db6` passed full local CI (453s), exact-head, merge and QEMU CI. It reached
Arch/systemd/SSH; root handoff completed 28.310s after dispatch. Loading the PCIe
PHY triggered deferred controller probing and a reset before MHI/ath11k. V11
returned automatically with SSH, healthy power, correct storage scope and
Tailscale online. Temporary host alias/firewall/listeners were cleaned up.
Trace-v2 additionally proved controller clocks/reset and PHY power-on returning
0. QEMU created/bound the exact WCN client and completed dummy power-on/off, so
a generic creation/ABI bug is not reproduced. No hardware setting was changed.
Observe-v3 then captured probe-ready, creation return 0 and power-on-enter before
reset. V11 recovered automatically. Isolated MHI load/unload passed in about
0.01s on the same V11 boot with PCI empty and 117 nodes RO, removing an unconditional
MHI-init failure from the leading explanations. No rail or GPIO fault is proven.
See `test-results/2026-08-30-native-wifi-ram-handoff.md`.

## Cheapest next action

1. Audit the stock power-sequence contract, then choose a per-rail/GPIO
   discriminator. Retained ASUS CNSS code enables its regulator list serially;
   mainline uses bulk enable. The WW33 base DT has vendor init-mode values 1
   on S12 and 4 on S2; vendor levels.h decodes these as RET/HPM, whereas mainline
   uses different numeric mode constants. Overlay applicability and live mode
   still need verification. Do not copy raw mode numbers or retune voltages.
   No successor is issued. The kernel, DTB, initramfs and firmware remain unchanged.
   Keep V11/slot A and lock all UFS nodes before activation.
   Pstore was empty; ramoops is built in but the native DT has no ramoops node
   and mem_size=0, so this attempt had no working ramoops backend.
   The new selective kprobe helper has passed setup/marker/cleanup on V11
   without activating PCIe; original global probe definitions were restored.
   Observe-v3 is consumed. Its host management lease expired during an operator
   gap before the radio probe; the ready guard prevented activation. The same
   still-running trial resumed through one bounded reader/probe script, without
   reboot or new claim. Keep that critical sequence contiguous in future cycles.
2. Finish the existing userspace validation client's account login and test
   peer-to-phone Tailscale SSH. Do not re-enroll the phone or treat self-ping as
   peer evidence. Log out/remove the temporary client after successful testing.
3. Package-keyring work is preserved at `b9ceb26`: helper/unit and focused test
   pass, but it is not deployed or integrated into boot. Resume it when needed
   for signed Wi-Fi userspace packages; preserve package-signature enforcement.
4. Continue loaded Wi-Fi/power checks and the remaining standalone server MVP.

Opus's saved OAuth session expired; the attempted review did not run. This is
not a hardware failure and is not a reason to redo the successful builds.

Retain V11/V10 and the stable slot-B loader. Wi-Fi may need a DTB and module
change, but no GPT or experimental boot-partition flash. Preserve the exact
rebuilt module kit and compressed V11 p24 image. Do not repeat the completed
p24 transfer.

## Boundaries and Git

Stop on wrong device/topology, unsafe power/temperature, writes outside the
reviewed scope, ambiguous transport during a write or loss of slot-A rescue.
Never expose credentials or private evidence, or retry ambiguous execution.

- Worktree: `/home/deck/.local/state/rog5-haven-clean-ci-20260810`.
- Branch: `agent/linux-recovery-host`; normal pushes authorized, never force-push.
- V11 executable source: `7f7621ce0a11a624d703200e5a65c03127802736`.
- Resolve publication from Git and exact-head CI, not copied last-pushed fields.
