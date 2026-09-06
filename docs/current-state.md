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

`headless-selector-rescue-v2` is now **consumed**, not unissued. Its sole RAM
execution on published source `23e8fe430dff4fb1dcc7c6634d660bf390458bb3`
selected the unchanged signed `persistent-native-root-v11` fallback, kernel
`7.1.4-g359318de534f`, boot `6aa96219-c542-441c-9500-dd540e89b249`.
Never execute this candidate again. No flash, GPT or selector change occurred.

Pinned USB SSH and a separately scoped fallback/P2 component passed. The
original smoke remains **FAIL**: its host predicate required `attested_boot_id`,
which the exact old V11 producer never emits (R2/R3/R7). Do not weaken current
server attestation or relabel this as H02/R01. The integrated
`check-deployed-server --readiness-only` preserves that distinction and passed
on this same boot in 0.251 s. Captured-marker tests run in normal/optimized
Python; future supervisors must reuse this checker instead of the copied grep.
Capture completed in 1380.804 s; owned route/firewall/profile/address cleanup
passed. At uptime 1398 s the same boot remained reachable, Full/Good 100%,
29.7°C, 8.621 V, zero battery current and USB online. This is not H03 regulation
qualification. Pstore was empty and remains inconclusive.

The only failed systemd unit is the known V11 uninitialized package-keyring
refresh (`fpr_email[1]: unbound variable`). Its fix was validated on the primary
below but is not in this immutable fallback. No failure was hidden/reset.
The fallback uses a tmpfs root upper, not the primary's 16 GiB persistent upper;
do not transfer primary userspace, Wi-Fi or Tailscale evidence to this boot.
Current selector hash and its previous healthy-primary trial remain unchanged.

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

Prepared **unissued/unbooted** `headless-acceptance-rescue-v6` refreshes V5's
headless init and adds its missing package-keyring helper/unit. Both kernels,
DTB and all 20 hardware payload members are unchanged. Target twins match
(`7703f398…`); signed recovery twins and sealed verifier pass (`32704e44…`
boot image). Only the canonical claim registry records its execution identity.
Root/archive composition PASS 35.642 s; nine QEMU watchdog cases PASS.
Registration active tier PASS 16.776 s. No selector or phone storage change.
Read-only source inspection confirms V11's actual shutdown is `ec3c7fd2…`, not
current source `1cd007ea…`; prepare its exact RAM transition instead of copying
a newer-primary adapter assumption. At uptime 3162 s this fallback remained
Full/Good 100%, 29.7°C, 8.620 V and USB online, with unchanged selector/trial.
The original observer fix's source
`4205a261…` passed all four GitHub jobs in run 34007323724.
All four registration CI jobs passed run 34007871579 at `2d5a0994…`.
Exact legacy exitrd action-delta syntax passed with its sealed BusyBox/filesystem;
pinned read-only inspection passed in the combined 0.516 s check at uptime
3871 s, with unchanged installed boot B, selector/trial and safe battery state.
No transition was installed or requested. Next: use the integrated readiness checker
in the exact private supervisor, verify the running V11 exitrd before a normal
storage-quiescent fastboot transition, then pass connected admission before
one execution. New physical evidence is needed for coherent headless startup
with the fixed keyring and Wi-Fi inactive, not to rediscover a marker parser bug.

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
