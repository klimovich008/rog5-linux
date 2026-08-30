# Active ROG Phone 5 Linux context

Updated: 2026-08-30

Read `docs/current-state.md` for the baseline and the latest V11 live result.
Historical generations remain in Git; do not reconstruct them here.

## One current question

Which PCIe controller/clock/reset/PHY step resets the phone before MHI or ath11k
loads? Wi-Fi remains the active server-MVP requirement. The native RAM handoff,
USB rescue and automatic V11 return now work; do not rebuild them for this fault.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V11 boot
  `3b71f143-439d-44db-ac09-991624e68c79`; slot A remains rescue.
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

The native RAM trial `native-wifi-ram-v1` is permanently consumed. Source
`abf3db6` passed full local CI (453s), exact-head, merge and QEMU CI. It reached
Arch/systemd/SSH; root handoff completed 28.310s after dispatch. Loading the PCIe
PHY triggered deferred controller probing and a reset before MHI/ath11k. V11
returned automatically with SSH, healthy power, correct storage scope and
Tailscale online. Temporary host alias/firewall/listeners were cleaned up.
See `test-results/2026-08-30-native-wifi-ram-handoff.md`.

## Cheapest next action

1. Investigate the saved PCIe-reset fixture before issuing a successor. Exact
   V11 supports KPROBE_EVENTS and exposes the relevant built-in PCIe, clock and
   reset symbols; function tracing is disabled. Prefer bounded runtime probes
   over another kernel build. No reason to change Wi-Fi firmware or rail values
   has been proven. Keep V11/slot A and lock all UFS nodes before activation.
   Pstore was empty; ramoops is built in but the native DT has no ramoops node
   and mem_size=0, so this attempt had no working ramoops backend.
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
