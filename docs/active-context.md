# Active ROG Phone 5 Linux context

Updated: 2026-08-31

Read `docs/current-state.md` for the baseline and the latest V11 live result.
Historical generations remain in Git; do not reconstruct them here.

## One current question

Make the V17-qualified Wi-Fi composition persistent and USB-independent.
WPA2/CCMP, DHCP and strict SSH over the host WLAN route passed on hardware.
V17 is consumed; preserve its kernel/firmware and the V11 rescue baseline.
See `test-results/2026-08-31-wifi-connectivity-pass.md`.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V11 boot
  `1bc4a53b-ab56-40f2-a4ec-ead762590d01`; slot A remains rescue.
- V11 passes initial systemd running, V49 high-speed UFS, zero UFS errors,
  NCM, stable key-only SSH, p23 state and exact two-node write scope.
- Latest battery read: Full/Good, 8.602 V, 30.1°C; state/Tailscale active.
- Temporary source ACM disappeared on reboot; V11 currently exposes NCM only.
- Standalone shared mode is `10.77.0.1/30` → `10.77.0.2/30`. Fixed recovery
  management remains a separate `169.254.77.1/30` profile.
- Tailscale 1.102.3 starts automatically from p23 state. It is enrolled and
  online, with no health warnings; its identity survived normal systemd reboot.
- The empty runtime package keyring causes a separate background WKD parser
  failure. Initial systemd checks are not a long-soak zero-failure claim.

## Just-completed checkpoint

V17 used the corrected foreground WPA service, associated, acquired DHCP and
passed exact-key/boot-ID SSH over Wi-Fi. NCM and117-RO storage stayed healthy.
Normal V11 fallback and services were restored; Wi-Fi is not yet persistent.
Automatic initramfs/service integration passed full local and exact-head CI.
V18 is now narrowly admitted and unconsumed for one RAM-only automatic-startup
cycle; see `test-results/2026-08-31-wifi-automatic-boot.md`.

## Cheapest next action

1. Reuse source1eea8970e87f and its qualified archived kit; do not rebuild it.
   Clean twins and cached Image match; base19/Wi-Fi37 module packages and
   initramfs twins match. V14 now qualifies the staged DT/power path physically.
   The V17 radio/WPA/DHCP/SSH path is physically qualified. Integrate the same
   verified artifacts into automatic boot; do not rebuild kernel/modules.
   Validate the sealed automatic mode that removes only the USB-carrier
   dependency from read-only native startup. P2 still needs the configured
   address/SSH policy. The boot rollback timer starts before P2/early SSH.
   State mounting follows P2 at `/persist`; reuse it for private Wi-Fi config.
   Preserve diagnostic/write-path observation and the independent fallback.
   Do not infer explicitly valid QMI fields from default-capable values.
   Keep the low hold, all117-RO/power/identity gates and matched write ACKs.
   Never rerun V17 or earlier. Restore shared networking after future fallback;
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
