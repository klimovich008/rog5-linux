# Persistent native Wi-Fi V2 live result

Result: **functional PASS; long-lived FAIL; superseded by V3**.

Primary question: can the qualified native Wi-Fi stack become a repeatable,
rollback-safe persistent primary without weakening V11 fallback or storage and
power boundaries?

## Defects and fixes

- The first selector-V2 attempt failed before target execution because raw
  RESTART2 cycles left p23 with `orphan_present`; ASUS 5.4 has no orphan-file
  implementation and failed its read-write trial-state mount. A clean systemd
  shutdown cleared the transient state and preserved the same unused trial.
- Wi-Fi V1 then proved radio, DHCP, route, NCM, SSH, Tailscale, charging and UFS,
  but its health unit could not find the helper after `switch_root`, shared its
  executable pathname with the success record, and canceled SSH while stopping
  the required rollback timer. The radio unit also retained an unrendered
  timeout token. These are R2/R3/R4/R8 infrastructure defects, not kernel or
  Wi-Fi failures.
- Commit `cba674002836f3cca80939f2ddcd4ffc317143c7` packages the helper under the
  preserved runtime root, uses `healthy.record`, disarms the timer with
  dependency propagation suppressed, and renders the radio timeout.

## Offline and artifact evidence

- Focused tests: 18 passed in 1.989 seconds.
- Active tier: PASS in 102.574 seconds; its 32-second sparse-staging test remains
  the largest fast-loop cost.
- Twin target initramfs build: 7.108 seconds, SHA-256 `628eaa72…`; kernel and DTB
  were reused unchanged. Signed manifest: `f54d3807…`; selector: `043d263d…`.
- The signed bundle independently verified against the exact recovery public
  key. GitHub run `33565385673` passed exact-head, merge, QEMU and publication.

## Physical evidence

- P24 staging preserved V11 and Wi-Fi V1 selectors/bundles and archived the
  accepted V1 trial instead of deleting it. The busy active OverlayFS lower
  cannot be remounted read-only in place, so the transaction block-locked p24
  and immediately used a clean reboot; the next boot mounted p24 read-only.
- First V2 boot `f7eac86d-b239-4f87-bb0d-a516c9a4f20c` committed healthy and
  disarmed rollback. Host-observed root-to-health time was 54 seconds.
- Repeat boot `8ac74ae5-f7b2-46ac-9ff3-bb6d201b4a8f` committed the same healthy
  trial and disarmed rollback again. Root-to-health time was 57 seconds.
- The repeat had systemd `running`; Wi-Fi radio/WPA/DHCP, persistent state,
  early SSH, Tailscale and health units were active. Strict key-only SSH passed
  directly over Wi-Fi at `192.168.1.151` as well as over NCM.
- Battery was Full/Good, 8.583 V and 30.0 C; USB was online with a 500 mA input
  limit. Maximum thermal-zone temperature was 37.1 C.
- P24 was read-only, exactly 117 block nodes were visible, only `sda` and
  `sda23` were writable, and no fatal storage, UFS, panic or oops signature was
  present.

The signed V11 fallback remains unchanged and was exercised during the initial
pre-execution trial-state failure. No slot-A, GPT, firmware, identity,
calibration, modem or protected partition data changed.

Subsequent liveness testing found a separate transient
`rog5-wifi-probe-rollback.timer` still armed for 600 seconds. It rebooted the
otherwise healthy V2 target at the exact boundary. V3 keeps the same kernel,
DTB and Wi-Fi composition but the health gate now disarms both rollback timers.
