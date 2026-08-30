# Active ROG Phone 5 Linux context

Updated: 2026-08-31

Read `docs/current-state.md` for the baseline and the latest V11 live result.
Historical generations remain in Git; do not reconstruct them here.

## One current question

Which S12 RPMh request or kernel/firmware fault triggers the radio reset?
The stock retention vote applied successfully in v5 but did not prevent reset.
Distinguish voltage/enable failure with independent evidence before successors.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V11 boot
  `1b24ebf0-e4a1-466c-8197-13904886f5cf`; slot A remains rescue.
- V11 passes initial systemd running, V49 high-speed UFS, zero UFS errors,
  NCM, stable key-only SSH, p23 state and exact two-node write scope.
- Latest battery read: Good, 8.633 V, 30.1°C; same V11 boot and active state services.
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

All five native Wi-Fi trials through s12-ret-v5 are permanently consumed.
Arch/systemd/SSH and automatic V11 recovery passed; PCIe activation reset the
target. Trace-v2 proved controller/PHY success; observe-v3 proved creation
return 0 and power-on-enter. Isolated MHI load/unload passed on V11 with PCI
empty and 117 nodes RO. No rail or GPIO fault is proven. Exact-kernel QEMU
passes client creation and dummy power. Full local CI passed in 453s for the
handoff code; retained timing and physical evidence are in
`test-results/2026-08-30-native-wifi-ram-handoff.md`.

## Cheapest next action

1. Run the prepared observation-only successor after CI and connected gates.
   V5 passed full local CI (466s) and every GitHub job, then ran once. Its
   cached mode8 proves the RET vote applied, but the reset remains. Both v4
   and v5 stop delivering rail evidence at vddpmu entry after two successes.
   Paired PON adds one PS_HOLD warm reset per cycle (counts3→4→5). V11 recovers.
   Fixtures: `tests/fixtures/native-wifi/s12{,-ret}-entry-reset.json`.
   Missing trace records still prevent proof of the exact voltage/enable call.
   Do not issue a guessed voltage, HPM or ordering change as another fix.
   New lead: Qualcomm's SM8350/WCN6851 series uses S11 for VDDPMU, whereas
   our SM8450-derived mapping uses S12. Conditional hw1.1 modules now build,
   reproduce and load with accepted BTF in exact-Image QEMU. See the offline
   Wi-Fi result; ASUS chip/mapping and hw1.1 firmware/BDF still need validation.
   Image, DTB, initramfs, power wiring and firmware were not changed for this backport.
   Keep V11/slot A and lock all UFS nodes before activation.
   Pstore was empty; ramoops is built in but the native DT has no ramoops node
   and mem_size=0, so this attempt had no working ramoops backend.
   The fixed-bank read-only PMIC reader changes no PMIC or SDAM state. Paired
   snapshots now correlate the new warm reset to v4, but do not identify its
   software cause. No OCP/UVLO entry was added; absence is not crash-free proof.
   RPMh call/send/ack probes pass passive V11 setup/read/cleanup and exact-head CI.
   Fresh signed twins are prepared but unconsumed. S12 maps to0x40100; buffering is not a
   proven loss cause. The exact B loader snapshots pstore but does not export
   it before its second kexec. Preserve that loader; resolve capture separately.
   See `test-results/2026-08-31-native-wifi-rpmh-observer.md`.
   Keep future reader/probe sequences contiguous and retain the ready guard.
2. Finish the existing userspace validation client's account login and test
   peer-to-phone Tailscale SSH. Do not re-enroll the phone or treat self-ping as
   peer evidence. Log out/remove the temporary client after successful testing.
3. Package-keyring work is preserved at `b9ceb26`: helper/unit and focused test
   pass, but it is not deployed or integrated into boot. Resume it when needed
   for signed Wi-Fi userspace packages; preserve package-signature enforcement.
4. Continue loaded Wi-Fi/power checks and the remaining standalone server MVP.

The bounded Opus retry still failed with expired OAuth; no review ran. Retain V11/V10, the stable loader,
module kit and compressed V11 image: no GPT or experimental boot-partition flash.
Do not repeat the completed p24 transfer or successful builds.

## Boundaries and Git

Stop on wrong device/topology, unsafe power/temperature, writes outside the
reviewed scope, ambiguous transport during a write or loss of slot-A rescue.
Never expose credentials or private evidence, or retry ambiguous execution.

- Worktree: `/home/deck/.local/state/rog5-haven-clean-ci-20260810`.
- Branch: `agent/linux-recovery-host`; normal pushes authorized, never force-push.
- V11 executable source: `7f7621ce0a11a624d703200e5a65c03127802736`.
- Resolve publication from Git and exact-head CI, not copied last-pushed fields.
