# Active ROG Phone 5 Linux context

Updated: 2026-08-31

Read `docs/current-state.md` for the baseline and the latest V11 live result.
Historical generations remain in Git; do not reconstruct them here.

## One current question

Prove association, DHCP and SSH over Wi-Fi using the V15-qualified composition.
V15 passed firmware/PHY startup and scanned33 access points. It is consumed;
V16 is consumed: radio passed, but WPA startup used an unsupported logging flag.
The foreground/systemd fix is tested; V17 is admitted once, not yet executed.
Preserve the kernel and firmware.
See `test-results/2026-08-31-wifi-late-activation.md`.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, anchored at host USB `1-1.2`.
- Active slot: B, running V11 boot
  `f352bcba-f393-4b1a-ad9f-93e7abf395a7`; slot A remains rescue.
- V11 passes initial systemd running, V49 high-speed UFS, zero UFS errors,
  NCM, stable key-only SSH, p23 state and exact two-node write scope.
- Latest battery read: Full/Good, 8.604 V, 30.2°C; state/Tailscale active.
- Temporary source ACM disappeared on reboot; V11 currently exposes NCM only.
- Standalone shared mode is `10.77.0.1/30` → `10.77.0.2/30`. Fixed recovery
  management remains a separate `169.254.77.1/30` profile.
- Tailscale 1.102.3 starts automatically from p23 state. It is enrolled and
  online, with no health warnings; its identity survived normal systemd reboot.
- The empty runtime package keyring causes a separate background WKD parser
  failure. Initial systemd checks are not a long-soak zero-failure claim.

## Just-completed checkpoint

V15 reached SSH39.566s after entry, then firmware/PHY readiness at uptime64.48s.
The exact-keyed board data worked and `wlp1s0` scanned33 access points.
V16 repeated radio/scan success, then stopped on WPA's unsupported `-f` flag.
Its parent PID check caught the misleading zero exit after usage output.
No association/DHCP/SSH occurred. Normal V11 fallback and services were restored.

## Cheapest next action

1. Reuse source1eea8970e87f and its qualified archived kit; do not rebuild it.
   Clean twins and cached Image match; base19/Wi-Fi37 module packages and
   initramfs twins match. V14 now qualifies the staged DT/power path physically.
   The V15 hw1.1 firmware/PHY/scan path is now physically qualified. Add only
   the WPA client and bounded connection test; the private WPA2 runtime has
   signature-verified Alpine packages and passes exact AArch64 version checks.
   Use `start-native-wifi-wpa.sh`: foreground systemd supervision, not `-B/-f`.
   The exact WPA/config and DHCP argv now pass on Arch in an isolated netns;
   journal capture is proven. Native dhcpcd's lease directory is volatile overlay.
   Do not infer explicitly valid QMI fields from default-capable values.
   Keep the low hold, all117-RO/power/identity gates and matched write ACKs.
   Never rerun V16 or earlier. Restore shared networking after future fallback;
   reuse the fixed missing-interface helper and parameterized stage parser.
   Preserve archives/source; disk headroom remains low. Use
   ROG5_TEST_TMP_PARENT for project RAM scratch; never repurpose HOME.
2. The userspace validation client is online; finish its SSH sign-in check and test
   peer-to-phone Tailscale SSH. Do not re-enroll the phone or treat self-ping as
   peer evidence. Log out/remove the temporary client after successful testing.
3. Package-keyring work is preserved at `b9ceb26`: helper/unit and focused test
   pass, but it is not deployed or integrated into boot. Resume it when needed
   for signed Wi-Fi userspace packages; preserve package-signature enforcement.
4. After association, remove the sealed initramfs's USB-carrier UFS rendezvous
   from the production read-only boot path while retaining diagnostic/write
   guards, then validate host-free boot, persistent Wi-Fi and loaded power.

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
