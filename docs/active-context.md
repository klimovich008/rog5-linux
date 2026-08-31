# Active ROG Phone 5 Linux context

Updated: 2026-09-01

Read `docs/current-state.md` for the persistent V11 baseline. Historical
generations remain in Git and dated `test-results/`; do not reconstruct them
here.

## One current question

Prove that the qualified Wi-Fi target remains power-safe on the original ASUS
charger, then prove charger-only startup. These physical gates precede any
persistent selector or slot-B loader change.

## Current live state

- Exact phone: `M5AIKN00F0353YH`, `lahaina`, host side port `1-1.2`.
- Active slot: B, running V11 boot
  `cec1225b-e998-4d97-8728-c56faddbee5c`; slot A remains ASUS rescue.
- V11 passes systemd, V49 UFS, NCM, key-only SSH, p23 state, Tailscale and the
  exact `sda` plus `sda23` write scope. P24 remains read-only.
- Latest read: battery Full/Good, 8.593 V, 30.1 C. Tailscale is online with no
  health warnings. Its separate managed-SSH check still needs fresh account
  approval and is not a charger-test prerequisite.
- The empty runtime package keyring causes a separate background WKD parser
  failure. Do not mask it or attribute it to Wi-Fi/kernel behavior.

## Qualified Wi-Fi evidence

- V21 removed PC USB data by target uptime 5.786s, before native-root mount at
  11.432s, then proved authenticated WLAN discovery and strict SSH. V11
  recovery took 64.532s.
- V19 passed 180 seconds of isolation, reassociation and 64 MiB traffic.
- V22 is signed, admitted and unconsumed for a coordinated PC → ASUS charger →
  PC runtime test. Its operator marker is absent; never run it unattended.
- Reuse the qualified Image, DT, modules, firmware and initramfs. Do not rebuild
  the kernel for the remaining physical power questions.

## Rollback-safe persistence checkpoint

Offline selector-v2 support now keeps V11 as a signed fallback. The dedicated
loader verifies both bundles, opens only the existing p23 write scope, and
atomically records a try-once trial. First entry selects Wi-Fi; a reboot while
still pending selects V11. The target can commit `healthy` only after WLAN,
SSH, Tailscale service, charging, thermal and exact storage checks pass.
Malformed/unavailable trial state selects V11 after clean relock; any cleanup
or relock failure stops the loader. P24 stays read-only.

Focused tests passed in 22.910s. Final full local CI passed in 454.453s. Exact
details are in `test-results/2026-09-01-persistent-wifi-rollback-offline.md`.
Nothing in this checkpoint was flashed, selected, admitted or run on the phone.

## Next actions

1. Keep the PC cable attached until the operator can perform both bounded V22
   cable moves; then run V22 once and restore V11.
2. Run a separate charger-only startup trial using the same qualified target.
3. Only after both pass, build/sign the persistent bundle, generate selector v2
   from its manifest, RAM-test the updated loader repeatedly, and review the
   exact slot-B loader/p24 deployment. Keep slot A and V11 intact.
4. Initialize the Arch package keyring and finish peer Tailscale SSH separately.

## Boundaries

Stop on wrong device/topology, unsafe power/temperature, unexpected writes,
ambiguous transport during a write, or loss of rescue. Never expose credentials
or private evidence, reuse a consumed trial, alter slot A, rebuild `super`, or
force-push. Permit no GPT or experimental boot-partition flash. Use `/dev/shm`
for test scratch because `/home` has minimal headroom.
