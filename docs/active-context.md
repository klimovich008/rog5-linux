# Active ROG Phone 5 Linux context

Updated: 2026-08-31

Read `docs/current-state.md` for the baseline and the latest V11 live result.
Historical generations remain in Git; do not reconstruct them here.

## One current question

Does an independently held S12 enable vote, after proven AUTO, allow safe
radio power-up while UFS remains stable? V9 passed query/AUTO without voltage writes.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V11 boot
  `76daa970-fd40-4f93-9dad-ab5b821bc6e0`; slot A remains rescue.
- V11 passes initial systemd running, V49 high-speed UFS, zero UFS errors,
  NCM, stable key-only SSH, p23 state and exact two-node write scope.
- Latest battery read: Good, 8.625 V, 30.0°C; state/Tailscale restored.
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

All nine native Wi-Fi trials through s12-ready-v9 are permanently consumed.
Six reached target SSH then reset during PCIe power; v6/v8 failed before the probe.
V9 passed its query/AUTO-only probe and deliberately returned to V11.
Trace-v2 proved controller/PHY success; observe-v3 proved creation
return 0 and power-on-enter. Isolated MHI load/unload passed on V11 with PCI
empty and 117 nodes RO. No rail or GPIO fault is proven. Exact-kernel QEMU
passes client creation and dummy power. Full local CI passed in 453s for the
handoff code; retained timing and physical evidence are in
`test-results/2026-08-30-native-wifi-ram-handoff.md`.

## Cheapest next action

1. S12-held-v10 is signed but unissued; it reuses V9's Image/DTB/initramfs/modules.
   Validate publication and connected gates, then run its protected-enable/radio plan.
   V9 passed full local CI450.562s and every GitHub33354938967 job at220ba05b.
   Query returned0 with no S12 request; enabled=-22 was correctly advisory.
   AUTO sent0x40108/data6, received ACK and returned0; cache8→2. No voltage
   or enable request occurred. Ten buffered1MiB reads and NCM checks passed.
   Use direct I/O for stronger hardware-read evidence in the next gated probe.
   USB was online at the first value sample; V8's settling hypothesis is not proven.
   V11 recovered normally; temporary host address/firewall/ACM setup is removed.
   All60 authenticated WW33 DTB/DTBO compositions agree: S12 always-on,
   UFS VCCQ parent, active UFS load210mA selects AUTO at the200mA threshold.
   Mainline AUTO=2, vendor AUTO=3; the latter means mainline HPM. An offline
   reviewer caught the wrong permission literal before deployment; fixed/tests.
   New module twins and permission-only DTB twins match; exact-Image QEMU
   proves module ABI/BTF load and generic-board rejection. V8/V9 cannot be retried.
   Query/AUTO gates are proven; retain ACK capture and all117-RO UFS/NCM checks.
   Held-enable is a separate voltage-capable action, never an automatic retry.
   Do not add always-on or reparent L9 before the shared dependency is proven.
   Keep V11/slot A; source firmware, bootloader and persistent selector unchanged.
   V7 source gates and target SSH passed without a PMIC reset across kexec.
   Its radio event added PS_HOLD warm reset count6→7; trace0x40100/data0x548
   submitted but no completion was recorded. Preserve the real regression
   fixture `s12-voltage-submit-reset.json`; absent tail/pstore is inconclusive.
   The installed B loader cannot export its pstore snapshot before second kexec;
   native V11 has no working ramoops backend. Preserve the stable loader.
   Conditional hw1.1 modules remain offline and separate from this power test.
   See `test-results/2026-08-31-native-wifi-s12-shared-rail.md`.
2. The userspace validation client is online; finish its SSH sign-in check and test
   peer-to-phone Tailscale SSH. Do not re-enroll the phone or treat self-ping as
   peer evidence. Log out/remove the temporary client after successful testing.
3. Package-keyring work is preserved at `b9ceb26`: helper/unit and focused test
   pass, but it is not deployed or integrated into boot. Resume it when needed
   for signed Wi-Fi userspace packages; preserve package-signature enforcement.
4. Continue loaded Wi-Fi/power checks and the remaining standalone server MVP.

Opus remains OAuth-expired; bounded built-in review covered the handoff. Retain V11/V10, the stable loader,
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
