# ROG5 current state

Updated: 2026-09-06. This is the authoritative handoff, not continuous monitoring.

## Objective and boundaries

Qualify one reliable standalone headless Arch Linux server using the
[acceptance contract](release-acceptance.md) and
[test manifest](../configs/release-acceptance.json).
Run `scripts/host/rog5-dev accept` for the matrix. Display is optional.
Do not combine incompatible releases or count missing/skipped evidence as PASS.
Keep Arch: the reproduced failures were project composition/service defects.

Exact phone: ROG Phone 5 ZS673KS, `lahaina`, `M5AIKN00F0353YH`,
anchored side USB `1-1.2`. Preserve stock slot A, official WW33
`33.0210.0210.200`, as the verified charging/rescue route.
[Charging restoration](asus-charging-recovery.md) is complete.

Preserve exact device/slot/topology/boot-chain, signatures, power/thermal gates,
bounded storage/backup scope, independent rollback and permanent non-retry after
COMMIT or ambiguity. No experimental flash or protected-data/GPT change.
Destructive storage requires separately reviewed exact scope and explicit approval.
Private credentials, raw evidence and artifacts stay outside Git; do not delete them.

## Running rescue versus installed system

- Running **consumed** RAM rescue: `headless-acceptance-rescue-v5`;
  kernel `7.1.4-g359318de534f`;
  boot `c2149c4a-6ce4-47c6-9c3b-e3ca55ea43fb`. Never execute v1–v5 again.
- Installed slot B remains recovery `340f6392…`, selector-v2 primary
  `persistent-native-root-wifi-overlay-v10` and signed
  `persistent-native-root-v11` fallback. Installed demotion/verification
  corrections are still pending; this is not the running RAM rescue.
- P24 `arch_root_a` is the immutable native RO/norecovery lower and bundle store.
  RAM rescue uses a tmpfs upper. Existing P23 service-state image is /persist.
  Only sda/sda23 were writable among 117 checked nodes. Installed primary also
  uses the bounded 16 GiB root-overlay image. Accepted state/journal writes are
  not a zero-storage-write boot.
- Pinned SSH: `10.77.0.2`, host alias `169.254.77.2`,
  fingerprint `SHA256:WSn4LikLHGYMmnIhkgP/D3Q42/40SW99Mh1CuOHYkhQ`.
  Wi-Fi intentionally inactive. Tailscale service active; this host lacks a mesh
  route/client, so remote Tailscale reachability is not yet qualified.

## Latest physical evidence

V5 sole RAM boot: fastboot 12.820 s, authenticated SSH 59.298 s.
Late SSH restart passed in 2.547 s with unchanged boot/core identities.
Watchdog acknowledged current-boot P2+identity at uptime 902.576 s.
Capture completed in 1380.711 s, all four owned cleanup steps passed.
Passive transport evidence is not authenticated acceptance.

256 MiB RAM-only USB transfers passed both ways in 7.429/6.659 s with matching
hashes and no new interface errors/drops. This is not combined USB/Wi-Fi S02 PASS.
A 600.615 s observation has 61 Full/Good 100%, 30°C samples, 8.632–8.635 V,
0 µA, unchanged charge counter and USB online. H03 remains BLOCKED until
full-battery regulation/noise criteria are declared before another run.

Latest read-only continuity: same V5 boot at uptime 14053 s, core services active,
100% Full/Good, 29.9°C, 8.627 V, 0 µA, USB online. Only
`archlinux-keyring-wkd-sync.service` is failed: its bootstrap wiring fix is not
deployed. Do not mask this failure or call it a kernel defect. No formal
combined soak, ordinary-reboot sequence or physical rollback qualification yet.

## Published fixes and current checkpoint

Previous fully published checkpoint `0150d853fcb4930ac6057f6016ebc0af0c8d7b99`:
all four GitHub jobs passed run 33994287705. Full local CI 485.305 s.
This includes strict Python/-O composer validation, safe pre-activation radio
refusal (8.4 V gate unchanged), keyring startup wiring, late-SSH rollback guards,
and exact-kernel interrupted OverlayFS recovery. Detailed regressions and
historical failed runs are in the [acceptance incident](../test-results/2026-09-05-headless-acceptance.md).
These source fixes are not deployed-release qualification.

This checkpoint fixes the standalone builder's missing keyring inputs
and adds explicit `--successor --refresh-userspace` to the existing persistent
Wi-Fi composer. It refreshes repository scripts/units and the canonical trial
helper together; normal identity-only behavior still refuses helper mismatch.
Source/firmware/module/identity/integrity guards remain; packaging grants no authority.

Unsigned **offline-only** server twins built identically in 18.519 s.
Archive SHA-256:
`e57bf7d447dac8489a5aaf99952928aa8cef627b03da7a9b7464913cacadfc91`.
They retain persistent-overlay mode and 33 hardware payload members unchanged.
No signed candidate or claim was issued, and no phone was contacted this iteration.
With the retained Wi-Fi kernel, all nine watchdog/root-handover cases pass;
disposable OverlayFS journal/interruption/corruption tests pass in 85.349 s.
Actual Arch runtime preparation then exposed another R2 defect: the common
dormant `load-pwrkey` helper was mistaken for incomplete display opt-in. Fixed
the runtime presence check; full display still requires all components and
exact metadata. Corrected unsigned twins took 8.095 s, changing only runtime
and its checksum list:
`6934f7323a1aec6711045b11a7ff7e7d370636e357aa01fb64da545d16552fda`.
Explicit server-runtime composition passes in 33.808 s against the retained Arch
lower, using sealed BusyBox, real systemd/sshd and core/radio unit validation.
All writes were disposable; input hashes/source stayed unchanged; cleanup passed.
The default rescue checker still rejects radio-bearing archives. Radio module
load/closure is explicitly NOT RUN in this runtime-only result, not a release PASS.
Published as `d6def104ecd57e410e5f330ed621ba302a39953f`: active tier 18.178 s;
full local CI 485.604 s PASS. All four GitHub jobs, including exact-head,
merge and QEMU, passed run 33996636085.
Prior QEMU results bind
the preceding archive, not an automatically green final release.

## Next action

1. Finish the selector-validation checkpoint: normal/optimized Python now reject
   malformed manifests, changed fallback hashes and unsafe input/output files.
   Acceptance A02/D02 include the new behavior tests without duplicating them.
   Frozen full local CI PASS 491.554 s; publication/exact-head CI next.
2. Use the normal selector-backed recovery path for persistent trial qualification.
   The embedded-RAM rescue path deliberately bypasses trial preparation; it cannot
   acknowledge a fresh persistent trial. Read-only inspection found the installed
   V10 selector and matching old healthy record unchanged. Preserve/archive that
   state through the reviewed staging transaction, not a fabricated health ACK.
   Complete final wrapper/timing/transport qualification using the unchanged
   hardware set; do not retry consumed execution or repeat passed unchanged suites.
3. Use fresh reviewed execution identity for physical server qualification:
   Wi-Fi/USB transfer and restart, durable scratch, three ordinary boots,
   powered-off start, 60-minute combined soak and isolated failed-boot recovery.

Retained Wi-Fi-soak kernel `7.1.4-g1eea8970e87f`, DTB and V3 archive hashes
match the historical record. Its 22 direct and 37 nested radio/dependency modules
have matching release metadata. Keep that set together; never mix g359 modules
into it. Metadata agreement is not new BTF/symbol/load proof. Reuse accepted
kernel bytes for userspace fixes, not consumed execution authority.

The original installed-boot failure and prior PMIC IRQ/UFS emergency-RO incident
remain unproven. Empty pstore is inconclusive. Earlier accepted
[boot/start](../test-results/2026-09-03-unattended-reboot-v10.md),
[overlay](../test-results/2026-09-02-persistent-root-overlay-v8-live.md),
[Wi-Fi soak](../test-results/2026-09-02-persistent-wifi-v3-soak.md),
[NCM](../test-results/2026-08-29-persistent-ncm-two-hour-pass.md) and
[Tailscale](../test-results/2026-08-30-persistent-tailscale-v11-live.md) evidence
is not silently reused for another release. Use [development](development.md)
and applicable [lessons](development-lessons.md); keep one device coordinator.
