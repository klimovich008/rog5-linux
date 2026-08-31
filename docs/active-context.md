# Active ROG Phone 5 Linux context

Updated: 2026-08-31

Read `docs/current-state.md` for the baseline and the latest V11 live result.
Historical generations remain in Git; do not reconstruct them here.

## One current question

Validate USB-data-absent boot, then charger-only and longer power behavior.
V19 passed automatic startup,180s USB-data isolation, one reassociation and64MiB
of strict WLAN SSH traffic. V19 is consumed. Preserve its kernel/firmware and
V11 rescue; see `test-results/2026-08-31-wifi-usb-isolation.md`.
Authenticated Tailscale UDP discovery found the same SSH-verified LAN endpoint
while USB was off. Use that for next-boot discovery, then require the project
SSH key and new boot ID. This does not satisfy or bypass managed Tailscale SSH.
V20 is admitted and unconsumed for the early-cut test; its target bytes are
unchanged. See `test-results/2026-08-31-wifi-early-cut.md`.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V11 boot
  `7750f962-9b70-4c28-b786-5b2309b03788`; slot A remains rescue.
- V11 passes initial systemd running, V49 high-speed UFS, zero UFS errors,
  NCM, stable key-only SSH, p23 state and exact two-node write scope.
- Latest battery read: Full/Good, 8.595 V, 30.2°C; state/Tailscale active.
- Temporary source ACM disappeared on reboot; V11 currently exposes NCM only.
- Standalone shared mode is `10.77.0.1/30` → `10.77.0.2/30`. Fixed recovery
  management remains a separate `169.254.77.1/30` profile.
- Tailscale 1.102.3 starts automatically from p23 state. It is enrolled and
  online, with no health warnings; its identity survived normal systemd reboot.
- The empty runtime package keyring causes a separate background WKD parser
  failure. Initial systemd checks are not a long-soak zero-failure claim.

## Just-completed checkpoint

V19 passed automatic startup and runtime isolation/reassociation/traffic.
Radio preceded writable p23 state; only the two approved nodes were writable.
V11 fallback/services and same-instance USB/host cleanup passed.
The private Wi-Fi file now persists in p23; the default V11 kernel still lacks
Wi-Fi. Full local/exact-head/merge/QEMU CI passed for the implementation.

## Cheapest next action

1. Reuse source1eea8970e87f and its qualified archived kit; do not rebuild it.
   Clean twins and cached Image match; base19/Wi-Fi37 module packages and
   initramfs twins match. V14 now qualifies the staged DT/power path physically.
   V19 startup and runtime are physically qualified. Reuse its artifacts; do not
   rebuild kernel/modules. The bounded host USB-data-isolation helper is tested;
   see `test-results/2026-08-31-wifi-usb-isolation.md`. Prove the independent
   observation path before consuming the next trial. Distinguish USB data
   isolation from actual charger-only cold boot. P2 still needs the configured
   rescue address; boot rollback starts before P2/early SSH. State and private
   Wi-Fi configuration already persist at `/persist` through the p23 image.
   Preserve diagnostic/write-path observation and the independent fallback.
   Do not infer explicitly valid QMI fields from default-capable values.
   Keep the low hold, all117-RO/power/identity gates and matched write ACKs.
   Never rerun V19 or earlier. Restore shared networking after future fallback;
   reuse the fixed missing-interface helper and parameterized stage parser.
   Preserve archives/source; disk headroom remains low. Use
   ROG5_TEST_TMP_PARENT for project RAM scratch; never repurpose HOME.
2. The userspace validation client is online; finish its SSH sign-in check and test
   peer-to-phone Tailscale SSH. Do not re-enroll the phone or treat self-ping as
   peer evidence. Log out/remove the temporary client after successful testing.
3. Package-keyring work is preserved at `b9ceb26`: helper/unit and focused test
   pass, but it is not deployed or integrated into boot. Resume it when needed
   for signed Wi-Fi userspace packages; preserve package-signature enforcement.
4. First integrate bounded fresh UDP endpoint discovery with strict LAN SSH
   for the early-cut boot test. A later optional capture raced V19's planned
   reboot; treat missing USB as unavailable, never as a new kernel failure.
   The discovery parser is implemented/tested; see
   `test-results/2026-08-31-wifi-early-cut.md`. Native root mounts at
   userdata-mount, so use that earlier marker for cutoff timing proof.
   Keep existing timers for trials; review healthy-startup policy before a
   persistent selector update. PC input stayed capped500mA and sampled battery
   current averaged−22mA; actual charger-only/longer power proof remains.

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
