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

All three native Wi-Fi trials through observe-v3 are permanently consumed.
Arch/systemd/SSH and automatic V11 recovery passed; PCIe activation reset the
target. Trace-v2 proved controller/PHY success; observe-v3 proved creation
return 0 and power-on-enter. Isolated MHI load/unload passed on V11 with PCI
empty and 117 nodes RO. No rail or GPIO fault is proven. Exact-kernel QEMU
passes client creation and dummy power. Full local CI passed in 453s for the
handoff code; retained timing and physical evidence are in
`test-results/2026-08-30-native-wifi-ram-handoff.md`.

## Cheapest next action

1. Complete the prepared rails-v4 per-supply diagnostic. It serializes the
   existing WCN supply list and logs each enable plus clock/GPIO boundaries,
   with no voltage/mode setters added. It is default-off, bounded and not a
   production fix. Rollback injection tests, matching module/archive twins,
   and exact-kernel QEMU 0/250/1001 cases pass. The probe now loads software
   before PCIe and verifies the exact endpoint before binding ath11k, avoiding
   the observed MHI-init overlap. No v4 claim is issued or target executed.
   ASUS CNSS enables supplies serially; mainline uses bulk enable. Vendor and
   mainline regulator mode constants differ. Composed modes are not proven;
   do not copy raw mode numbers or retune voltages (see the result record).
   The Image, DTB, initramfs and firmware remain unchanged.
   Keep V11/slot A and lock all UFS nodes before activation.
   Pstore was empty; ramoops is built in but the native DT has no ramoops node
   and mem_size=0, so this attempt had no working ramoops backend.
   A fixed-bank read-only PMIC FIFO reader now works without reboot. Its
   retained window contains three PS_HOLD warm resets, not OCP/UVLO records;
   that is history, not yet exact per-cycle attribution. A before-v4 snapshot
   is preserved for comparison. The reader changes no PMIC or SDAM state.
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
