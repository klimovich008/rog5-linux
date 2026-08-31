# Active ROG Phone 5 Linux context

Updated: 2026-08-31

Read `docs/current-state.md` for the baseline and the latest V11 live result.
Historical generations remain in Git; do not reconstruct them here.

## One current question

What S12 APPS votes are inherited before a voltage/enable request? The read-only transport, clean kernel twins and exact-Image QEMU gate pass; one readback-only RAM trial is prepared, not consumed.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V11 boot
  `3d760020-1bda-45b5-aedd-b30a3747f673`; slot A remains rescue.
- V11 passes initial systemd running, V49 high-speed UFS, zero UFS errors,
  NCM, stable key-only SSH, p23 state and exact two-node write scope.
- Latest battery read: Good, 8.624 V, 30.0°C; state/Tailscale restored.
- Temporary source ACM disappeared on reboot; V11 currently exposes NCM only.
- Standalone shared mode is `10.77.0.1/30` → `10.77.0.2/30`. Fixed recovery
  management remains a separate `169.254.77.1/30` profile.
- Tailscale 1.102.3 starts automatically from p23 state. It is enrolled and
  online, with no health warnings; its identity survived normal systemd reboot.
- The empty runtime package keyring causes a separate background WKD parser
  failure. Initial systemd checks are not a long-soak zero-failure claim.

## Just-completed checkpoint

V11's installed firewall and normal reboot pass; see its live result.
The complete set now contains 22 modules, including dynamic signature/cipher
dependencies. QEMU accepts valid regulatory data, rejects tampering and proves
the requested Wi-Fi crypto transforms. The native Wi-Fi DTB preserves unrelated
state and uses stock-derived, selector-valid voltage intervals. Its RAM trial
booted Arch/UFS/USB/SSH, but PCIe activation reset the phone before Wi-Fi worked.
Firmware matches the prior verified set. See
`test-results/2026-08-30-native-wifi-offline.md`.

All ten native Wi-Fi trials through s12-held-v10 are permanently consumed.
Six reached target SSH then reset during PCIe power; v6/v8 failed before the probe.
V9 passed query/AUTO; V10 reset at held-enable entry before radio activation.
Trace-v2 proved controller/PHY success; observe-v3 proved creation
return 0 and power-on-enter. Isolated MHI load/unload passed on V11 with PCI
empty and 117 nodes RO. No rail or GPIO fault is proven. Exact-kernel QEMU
passes client creation and dummy power. Full local CI passed in 453s for the
handoff code; retained timing and physical evidence are in
`test-results/2026-08-30-native-wifi-ram-handoff.md`.

## Cheapest next action

1. No successor: V10 disproved AUTO alone as the enable-boundary fix.
   It confirmed AUTO ACK/cache2, then lost reporting at held-enable entry.
   No new RSC/voltage/enable frame was captured; do not infer the faulting instruction.
   PON added PS_HOLD warm reset0→1; V11 recovered. Preserve the new real fixture.
   Stock CNSS audit confirms exact1350000/1350000 request, no zero override.
   Mainline's1352000 selector widens that consumer contract; electrical effect unknown.
   Fixed-offset PMIC reads did not identify S12. Patch0035 now adds read-only RPMh
   transport with timeout-safe references, nonblocking admission and no WAKE borrowing.
   V9's query/AUTO and buffered reads passed; V10 confirms that mode again.
   V10 did not reach its direct-read or radio gates. All temporary host/ACM
   setup is removed. V8's separate USB-settling hypothesis remains unproven.
   All60 authenticated WW33 DTB/DTBO compositions agree: S12 always-on,
   UFS VCCQ parent, active UFS load210mA selects AUTO at the200mA threshold.
   Mainline AUTO=2, vendor AUTO=3; the latter means mainline HPM. An offline
   reviewer caught the wrong permission literal before deployment; fixed/tests.
   New module twins and permission-only DTB twins match; exact-Image QEMU
   proves module ABI/BTF load and generic-board rejection. V8/V9 cannot be retried.
   Query/AUTO gates are proven; retain ACK capture and all117-RO UFS/NCM checks.
   Do not issue another voltage/HPM guess; establish the actual voltage/state contract.
   Do not add always-on or reparent L9 before the shared dependency is proven.
   Keep V11/slot A; source firmware, bootloader and persistent selector unchanged.
   V7 source gates and target SSH passed without a PMIC reset across kexec.
   Its radio event added PS_HOLD warm reset count6→7; trace0x40100/data0x548
   submitted but no completion was recorded. Preserve the real regression
   fixture `s12-voltage-submit-reset.json`; absent tail/pstore is inconclusive.
   The installed B loader cannot export its pstore snapshot before second kexec;
   native V11 has no working ramoops backend. Preserve the stable loader.
   Conditional hw1.1 modules remain offline. Readback twins match, preserving
   V11 config/HS UFS; 19 modules load in exact-Image QEMU. The fixed readers
   reject the wrong board. Baseline DT has PCIe disabled and no S12 node.
   No voltage/radio tools accompany this trial. Keep its execution one-use.
   See `test-results/2026-08-31-rpmh-readback-development.md`.
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
