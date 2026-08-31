# Active ROG Phone 5 Linux context

Updated: 2026-08-31

Read `docs/current-state.md` for the baseline and the latest V11 live result.
Historical generations remain in Git; do not reconstruct them here.

## One current question

Validate loaded Wi-Fi/reconnect with USB data removed, then USB-data-absent boot.
V18 automatically initialized radio, loaded private p23 configuration, obtained
DHCP and passed strict WLAN SSH without host activation. V18 is consumed.
Preserve its kernel/firmware and V11 rescue; see
`test-results/2026-08-31-wifi-automatic-boot.md`.
V19 is narrowly admitted and unconsumed for the runtime-only isolation test;
it proves ordinary LAN SSH before cutting USB and does not use managed Tailscale
SSH. Booting with USB absent and Tailscale account verification remain required.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V11 boot
  `ac39a52f-dd50-4bc9-9d20-449a67aace83`; slot A remains rescue.
- V11 passes initial systemd running, V49 high-speed UFS, zero UFS errors,
  NCM, stable key-only SSH, p23 state and exact two-node write scope.
- Latest battery read: Full/Good, 8.599 V, 30.0°C; state/Tailscale active.
- Temporary source ACM disappeared on reboot; V11 currently exposes NCM only.
- Standalone shared mode is `10.77.0.1/30` → `10.77.0.2/30`. Fixed recovery
  management remains a separate `169.254.77.1/30` profile.
- Tailscale 1.102.3 starts automatically from p23 state. It is enrolled and
  online, with no health warnings; its identity survived normal systemd reboot.
- The empty runtime package keyring causes a separate background WKD parser
  failure. Initial systemd checks are not a long-soak zero-failure claim.

## Just-completed checkpoint

V18 passed automatic startup and exact WLAN SSH, with matched S12 traces.
Radio was qualified before p23 state opened; normal service used only the two
approved writable nodes. V11 fallback/services and host cleanup passed.
The private Wi-Fi file now persists in p23; the default V11 kernel still lacks
Wi-Fi. Full local/exact-head/merge/QEMU CI passed for the implementation.

## Cheapest next action

1. Reuse source1eea8970e87f and its qualified archived kit; do not rebuild it.
   Clean twins and cached Image match; base19/Wi-Fi37 module packages and
   initramfs twins match. V14 now qualifies the staged DT/power path physically.
   V18 automatic startup is physically qualified. Reuse its artifacts; do not
   rebuild kernel/modules. The bounded host USB-data-isolation helper is tested;
   see `test-results/2026-08-31-wifi-usb-isolation.md`. Prove the independent
   observation path before consuming the next trial. Distinguish USB data
   isolation from actual charger-only cold boot. P2 still needs the configured
   rescue address; boot rollback starts before P2/early SSH. State and private
   Wi-Fi configuration already persist at `/persist` through the p23 image.
   Preserve diagnostic/write-path observation and the independent fallback.
   Do not infer explicitly valid QMI fields from default-capable values.
   Keep the low hold, all117-RO/power/identity gates and matched write ACKs.
   Never rerun V18 or earlier. Restore shared networking after future fallback;
   reuse the fixed missing-interface helper and parameterized stage parser.
   Preserve archives/source; disk headroom remains low. Use
   ROG5_TEST_TMP_PARENT for project RAM scratch; never repurpose HOME.
2. The userspace validation client is online; finish its SSH sign-in check and test
   peer-to-phone Tailscale SSH. Do not re-enroll the phone or treat self-ping as
   peer evidence. Log out/remove the temporary client after successful testing.
3. Package-keyring work is preserved at `b9ceb26`: helper/unit and focused test
   pass, but it is not deployed or integrated into boot. Resume it when needed
   for signed Wi-Fi userspace packages; preserve package-signature enforcement.
4. Validate repeated host-free boot, Wi-Fi reconnect, loaded power/thermal
   behavior and rescue before switching the persistent Linux bundle selector.

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
