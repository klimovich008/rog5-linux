# ROG5 current state

Updated: 2026-09-06. Authoritative handoff, not continuous monitoring.

## Goal and boundaries

Qualify one reliable standalone headless Arch Linux server using the
[acceptance contract](release-acceptance.md) and
[test manifest](../configs/release-acceptance.json).
`scripts/host/rog5-dev accept` shows the formal matrix. Display is optional.
Component passes below are not an all-green release or imported acceptance rows.
Keep Arch: demonstrated defects were project composition/service problems.

Exact phone: `M5AIKN00F0353YH`, product `lahaina`, anchored side USB `1-1.2`.
Preserve official WW33 slot A (`33.0210.0210.200`) for charging/rescue.
[Stock charging restoration](asus-charging-recovery.md) is complete.
Preserve exact identity/slot/topology/boot-chain, signatures, power/thermal gates,
bounded storage/backups, independent rollback and permanent non-retry after
COMMIT or ambiguity. No experimental flash, GPT or protected-data change.
New destructive storage needs separately reviewed exact scope and approval.
Keep private credentials, raw evidence and artifacts outside Git; do not delete them.

## Current running rescue

**Consumed** `headless-acceptance-rescue-v6` ran once from published source
`ae819406f4c4bbb37cc479ff6da8287ba6d393c2`; all four CI jobs passed run
34008374648. Never execute this RAM candidate again.
Kernel `7.1.4-g359318de534f`, boot
`64e209e2-0efe-40c6-8396-29f3e481f0ff`.
Signed manifest `8beb3ab7…`, boot image `32704e44…`; exact identities and
preparation evidence remain in the [incident](../test-results/2026-09-05-headless-acceptance.md).

| Same-boot component | Measured result |
|---|---|
| Exact V11-to-fastboot RAM exitrd transition | PASS 9.260 s; no flash or selector change |
| Sole V6 fastboot operation / authenticated readiness | 12.824 s / PASS 59.555 s |
| Package trust and keyring refresh | PASS; no failed systemd units |
| Eight deployed runtime files vs sealed archive | PASS 0.246 s, including shutdown/keyring/SSH helpers |
| Powered continuity | PASS 95 samples / 960.494 s; Full/Good 100%, 29.7–29.8°C, USB online |
| Deployed watchdog | Current-boot P2 + SSH identity ACK at uptime 902.520 s |
| Late SSH service restart / new pinned connection | PASS 0.230 s / 0.191 s; same boot |
| Capture / owned host cleanup | 1380.479 s; route/firewall/profile/address cleanup PASS |
| Pinned readiness after cleanup | PASS 0.193 s |

The kernel-log prefix was retained with no new matched warning/oops/UFS-error
lines. The initial SPMI warning remains visible; this is not proof that the
kernel is fault-free. Do not treat empty pstore as proof of no crash.
Wi-Fi is deliberately inactive. This rescue uses a tmpfs root upper over
RO/noload P24 plus the existing P23 service-state image; it is **not** the
primary's 16 GiB persistent upper. Selector `c15c7782…` and healthy primary
trial `bfc82fac…` are unchanged. Stock A and signed V11 are preserved.

These are component passes, not a green release or H03 full-state regulation
qualification. H02's complete executable acceptance integration remains pending.
The first supervisor preflight failed before capture/claim/boot because its
restricted PATH lacked `gh`; the fixed absolute path passed under actual
runuser. A later host Python text/bytes error prevented sending the first
service-restart script; its failure and corrected invocation are retained.
Neither was a kernel failure or a retry of target execution. All capture and
power-monitor processes are now terminal.

## Previous primary checkpoint and installed recovery

- Previous **consumed** RAM execution `headless-server-selector-v1`, kernel
  `7.1.4-g1eea8970e87f`, boot `dd9cd15a-d9a6-4128-9dfa-5d8ef8d91fbd`.
  Do not execute this RAM candidate again. Previous rescue v1–v5 remain consumed.
- Normal selector-backed recovery verified the staged signed primary and
  created its pending record; the actual target committed **healthy**.
  Trial `bfc82fac0199062bb7244e451299ed11c513c8895c8943ac3c5b86d4dbdb141b`.
- Installed selector now names this primary and unchanged signed
  `persistent-native-root-v11` fallback. Selector SHA
  `c15c77824e3cecf128288f2c273c6bd7f93825e837568c669d8288145541d904`.
  Old V10 selector/healthy record were preserved on device and hash-verified on host.
- **Installed boot B still contains old recovery `340f6392…`.** This successful
  RAM recovery is not proof that installed demotion/helper corrections exist.
  Do not substitute an ordinary reboot for a newly reviewed recovery test.
- P24 `arch_root_a` remains RO/norecovery lower and bundle store. The target uses
  the existing bounded 16 GiB persistent root-overlay image on P23 and the
  existing service-state image at `/persist`. Only sda/sda23 are writable among
  117 checked physical block nodes. Accepted journals/state are not zero writes.
- Pinned SSH: `10.77.0.2`, alias `169.254.77.2`, fingerprint
  `SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
  Wi-Fi associated and acquired DHCP. Tailscale is Running/online, Health `[]`;
  independent mesh-peer SSH is still unproven.

## Previous primary physical checkpoint

Source `918f3f6d48c6eed3c46a4b0b0858c121a4bc85fb` passed full local CI
in 500.609 s and all four GitHub jobs in run 33999018607 before execution.
Existing identical signed twins and sealed primary/fallback verification were
reused; neither kernel was rebuilt. No flash or GPT change occurred.

Bounded bundle/selector staging passed and relocked P24. A RAM-only exitrd
action change took the old rescue through normal storage teardown to exact
slot-B fastboot in 9.288 s. Its first syntax check failed before installation
or reboot because musl BusyBox was invoked outside its exitrd filesystem;
verified same-boot/original-file inspection allowed that pre-install step to
continue using the exact chroot. No target claim was reused.

The sole new RAM boot took 12.831 s in fastboot; authenticated target/P2/SSH
identity readiness was observed at 83.174 s. Persistent OverlayFS, Wi-Fi,
trial health and package-keyring initialization passed. Systemd has no failed
units. Watchdog acknowledged current-boot readiness at target uptime 902.559 s;
late SSH restart did not provoke rollback.

| Same-boot component | Measured result |
|---|---|
| 256 MiB USB upload/download | PASS 7.366 / 6.582 s; hashes match |
| 256 MiB Wi-Fi upload/download | PASS 171.180 / 104.777 s; hashes match |
| Interface error/drop counters | No new errors/drops during either transfer |
| SSH / WPA+DHCP / health restart | PASS 1.484 / 17.513 / 0.383 s; no radio reactivation |
| Powered continuity | 61 samples over 600.697 s; same boot/storage, Full/Good 100%, 29.9–30.0°C |
| Kernel-log continuity | Prefix preserved; no new oops/panic/UFS/IRQ/emergency-RO signature |
| Capture and cleanup | 1380.501 s; route/firewall/profile/address cleanup all PASS |

The overlay still contained old healthd `019418fa…` despite the repository fix.
A bounded idle-client test reproduced a 2.276 s timeout. Deployed the already
tested `6bed593e…` script to the bounded overlay, preserving its predecessor;
idle/trickle clients no longer blocked USB/Wi-Fi health requests. No reboot.
Final runtime/healthy/trial-helper/healthd/exitrd hashes match expected source.
This userspace deployment must be included in final release composition.

Wi-Fi upload is close to its 180 s limit. Later readout showed high-rate Wi-Fi 6
on the phone but 54 Mb/s on the host; host-path limitation is a hypothesis,
not a demonstrated phone-kernel defect. Do not relax the deadline.
Full battery, -13–0 mA and unchanged charge counter do not prove net-positive
charging. H03 still needs predeclared full-battery regulation/noise criteria.

## Next actions and remaining acceptance

The bounded [source-reuse assessment](kernel-port.md#bounded-source-reuse-assessment--2026-09-06)
found incompatible downstream charging controls, not a demonstrated mainline
defect. Keep the accepted kernel; Denial remains deferred and optional.

The coherent rescue checkpoint above is complete as a component. Reuse its
accepted kernel and artifact evidence; no further source-reuse or kernel
redesign is indicated. Next integrate H02's complete runner and plan the
separate R01 experiment. The exact sealed failure helper uses
`RESTART2("bootloader")`: expiry reaches fastboot, not automatically signed
fallback SSH. Any host-assisted R01 cycle must prebind a fresh rescue execution
and its evidence budget, preserve one-use behavior, and remain distinct from
autonomous standalone recovery qualification. Do not silently change the
failure helper or installed loader to make that test easier.

1. New `rog5-dev check-deployed-server` compares six live userspace/helper
   files with repository-derived hashes and strict metadata through pinned SSH;
   first live component PASS in 0.297 s, with the captured stale-healthd fixture
   rejected offline. A02 runs both Python modes. The composition checker now
   binds `/shutdown` and reproduces the exitrd-musl failure from the retained
   Arch root before proving the correct nested chroot (component PASS 37.465 s).
   Finish whole-release composition integration; no kernel change is indicated.
2. Qualify the updated recovery path separately from the old installed loader.
   Preserve stock A and signed V11; no consumed/ambiguous retry or implicit flash.
   **Consumed** `headless-selector-rescue-v2` used identical offline-verified
   twins to boot V11 without opening the recovery trial-write window. Its
   fallback-selection/transport component is **not R01 failed-target recovery**;
   reuse the integrated readiness checker in the next supervisor. The observer
   checkpoint passed active tests in 16.633 s and full local CI in 483.726 s.
   Installed helper v1 was replayed
   against the tested v2: v1 leaves a previously healthy primary healthy on its
   next selection; v2 rearms pending and selects fallback after an unacknowledged
   attempt. Do not qualify installed boot B from v2 source or RAM evidence.
3. Finish executable hardware acceptance integration, explicit durable scratch
   scope/readback after reboot, three ordinary boots, powered-off start,
   60-minute combined storage/network soak and isolated failed-boot recovery.
   Local-root RAM-trial success does not complete standalone boot qualification.
4. Finish H03 regulation criteria and independent Tailscale peer SSH. Keep
   display/GPU/audio/sensor expansion outside the headless completion criteria.
   Previous-primary read-only check at uptime 3744 s: Full/Good 100%, 29.8°C, 8.623 V,
   USB online at 5.021 V/366 mA with 500 mA input limit; device/sink role.
   Charge-start/end thresholds are absent and full/design-capacity reads return
   ENODATA. These are missing regulation evidence, not proof of bad charging.
   Project SSH/health/Tailscale services are active with no failed units;
   generic `sshd` is intentionally masked. Tailscale reports Running/online,
   but this host has no Tailscale service/client/mesh route for the peer test.

The [acceptance incident](../test-results/2026-09-05-headless-acceptance.md)
retains source fixes, failed runs, exact artifacts and timing evidence. Older
boot/soak passes are not silently transferred to this release. The earlier
PMIC IRQ/UFS fault remains unproven; empty pstore is inconclusive.
Use [development](development.md), relevant [lessons](development-lessons.md)
and one physical-device coordinator. The full goal remains active.
