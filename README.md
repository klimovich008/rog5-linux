# ROG Phone 5 native Linux

This project is bringing native Linux to the ASUS ROG Phone 5 (`anakin`,
Snapdragon 888 / SM8350) as a low-power ARM server. Development is
headless-first: recovery, logging, boot, storage, USB/SSH, power, charging,
thermal behavior, input, sensors, audio, and wireless must be stable before
display, GPU, desktop, remote GUI, hotspot, or automation work resumes.

The project is experimental. It contains source, tests, configuration,
artifact identities, and redacted evidence. It deliberately excludes private
keys, personal data, Android partition dumps, proprietary firmware, and large
build outputs.

## Current status

| Area | State |
|---|---|
| Bootloader | Unlocked; temporary `fastboot boot` only |
| Persistent fallback | Alpine on vendor kernel 5.4.134; SSH/remote GUI and screen-off service available |
| Proven temporary baseline | Vendor-derived 5.4.210; display, touch, charging, USB, Wi-Fi, hotspot, and Plasma smoke tests passed |
| Recovery transport | v18 passed two RAM-only staging/rollback cycles and a separate mainline cycle |
| Recovery control | Shell-free framed recovery fetched and verified one signed bundle, claimed one correlated commit, started target NCM, and returned automatically to exact fallback |
| Mainline kernel | Reproducible Linux 7.1.4 board port with pinned source tag/commit/tree, exact no-local-tag ref state, and reconstructed historical rootless x86_64 builder; two independent builds recover every frozen `network-root-v1` identity; subsystem bring-up remains incremental |
| Core compatibility | ASUS 5.4 and accepted 7.1 ancestry now form a fail-closed profile/config/evidence oracle; the active-core source/DT gate has 43 source and 23 corrected-DTB checks plus an exact static thermal policy for TSENS critical IRQs, 12 CPU cooling zones, and five PMIC alarms; an 88-field runtime probe covers all six active capabilities, including exact RAM/CPUfreq topology, mount-bound NFSv4.2 storage isolation, and target-side USB/NCM/SSH identity; PMIC critical enforcement and forced thermal fallback remain future hardware gates, and the corrected candidate remains live-pending |
| Buttons/indicator | Exact Linux 7.1.4 source/config/module and DTB contracts pass offline; a reproducible 67,520-byte native AArch64 service validates the exact power-key/LPG identities and emits one bounded default-off green pulse per physical press; the historical headless-core-v2 root is pruned and must not be relabeled as its successor |
| Mainline userspace | Native Arch/systemd/NFS/OverlayFS/NCM/SSH passed twice on Linux 7.1.4, but the latest hardened r2 target lost USB 23 seconds after NCM enumeration and returned safely to fallback. The distinct `headless-netroot-early-diag-v1` successor now has a complete production-key twin build: signed bundles, recovery initramfses, ASUS wrapper kernels, raw images, and temporary-boot AVB wrappers reproduce byte-for-byte; its private build snapshot was destroyed and the exact diagnostic-only tuple passes the native artifact gate. A sealed 9.6 MB ARM64 runtime executes its exact stage 130/140 units under real Arch systemd in QEMU; the test SSH service proves ordering, not OpenSSH. The receive-only exact-port ACM collector is integrated into the one-shot lifecycle before the non-retryable commit boundary while the consumed r2 pins remain unchanged. Independent closure review and local CI pass; publication/GitHub CI, host installation, connected preflight, and one phone acceptance cycle remain pending. |
| Battery/charging | One historical Linux 7.1 battery-only PMIC GLINK snapshot remains accepted as read-only diagnostic evidence. A new candidate/boot/source-bound collector and host verifier define fixed 21-sample, 10-minute unplugged/USB/wireless observations and an unplugged-versus-USB comparison that derives either current-sign convention; 11 hostile hardware-free test groups pass. No new phone observation, charging-control surface, dual-cell interpretation, or charging-safety acceptance is claimed |
| Persistent Arch root | Staged and sealed offline; P2 and entry-v1 live attempts were rejected and consumed |
| GPU | Accepted A660 ancestry is frozen while headless core mechanics are completed |
| Wi-Fi | WCN6855/PCIe package passes offline tests; hardware cycle remains on HOLD |
| VPN hotspot | IPv4/IPv6 and real WireGuard fail-closed tests pass offline; radio/provider live gate remains |
| Operator authorization | [Standing project authorization](docs/operator-standing-authorization.md) covers in-scope credentials, host setup, connected preflights, reboots, and admitted temporary boots without repeated prompts; technical gates and the no-flash boundary remain mandatory |

Nothing in this table grants permission to flash or repeat a consumed live
gate.

## Start here

- [Active development context](docs/active-context.md) — the shortest
  authoritative resume point, current deployment boundary, and next hardware
  sequence.
- [Minimal-headless lifecycle runbook](docs/minimal-headless-live-cycle.md) —
  exact one-shot recovery, NFS, SSH, rollback, and cleanup procedure.
- [Operator standing authorization](docs/operator-standing-authorization.md) —
  actions that may proceed without another consent prompt and the hard
  boundaries that remain.
- [Roadmap](ROADMAP.md) — ordered subsystem gates and completion criteria.
- [Port status](docs/port-status.md) — compact per-subsystem evidence matrix.
- [Core compatibility](docs/core-compatibility-oracle.md),
  [source/DTB contract](docs/core-source-dtb-contract.md), and
  [runtime acceptance](docs/minimal-headless-runtime-acceptance.md) — active
  hardware-free and live core gates.
- [Current-state evidence ledger](docs/current-state.md) and
  [build/artifact ledger](docs/builds-and-artifacts.md) — detailed chronology
  and immutable identities; use these for investigation, not orientation.
- [Test plan](docs/test-plan.md) — complete regression and hardware tiers.
- [Archive index](docs/archive-index.md) — consumed and superseded material.

## Safety model

- Never flash an experimental boot, vendor boot, recovery, DTB, or rootfs.
- Keep the installed fallback configuration and authorization unchanged;
  separately guarded shell-history and read-induced atime effects are the only
  current exception.
- Use only an attended `fastboot boot` of an explicitly allowed image.
- Require exact artifact size and SHA-256, one fastboot device, and product
  `lahaina`.
- Keep physical storage read-only in staging and target diagnostics; only the
  bounded fallback ACM history/atime effects covered by the standing
  authorization are allowed.
- Keep an independent rollback watchdog armed.
- Treat every live diagnostic payload as single-use.
- Do not retry an execute action after an ambiguous disconnect.
- Keep credentials and private evidence outside the repository.

`manifests/artifacts.tsv` is an inventory, not boot authority.
`manifests/temporary-boot-images.tsv` is the deny-by-default boot policy.
It admits the twice-live-accepted v18 staging image and one exact single-use
diagnostic recovery, which remains gated by installation and connected
preflight. Neither image may be flashed.

## Recovery host workflow

Run the hardware-free host/control suite first:

```sh
scripts/host/test-repository-linux.sh ci
```

The `ci` tier needs no phone, Vulkan stack, desktop, or delegated cgroup. It is
the default pull-request gate for the recovery protocol and host safety path.
The workflow also has a separate full-system ARM64 job. It builds a minimal
kernel from the exact pinned upstream Linux v7.1.4 commit, proves the generic
kernel-to-initramfs handoff, then enters a sealed Arch runtime under real
`systemd 260.2-2-arch` and executes the production-generated stage 130/140
units. Its content-keyed kernel cache is invalidated when the build recipe
changes. The SSH dependency is a test stub, and QEMU does not emulate ROG
Phone hardware; see the
[systemd QEMU result](test-results/2026-08-01-arm64-systemd-qemu-gate.md).
For the wider provisioned local suite, run:

```sh
scripts/host/test-repository-linux.sh quick
```

The quick tier is intentionally provisioned, not a minimal POSIX smoke test.
It requires GCC, `dtc`, OpenSSL development files, `pkg-config` with Vulkan
headers/loader metadata, and a writable delegated non-root cgroup v2 with
`cgroup.kill`. This lets it compile and fault-test the real descriptor-only
launcher and Vulkan helper. Run it from a systemd scope with cgroup delegation
when a container does not expose those controls.

Use `rootfs` instead of `quick` to include the larger userspace packaging
suite.

Preflight the exact accepted staging image:

```sh
BOOT_IMAGE="$PWD/artifacts/recovery-stage-v18/boot-5.4.210-kexec-stage-builtin-recovery.avb.img" \
  scripts/host/recovery-linux.sh preflight
```

An attended staging-only boot has a second explicit guard:

```sh
ALLOW_TEMPORARY_BOOT=1 \
BOOT_IMAGE="$PWD/artifacts/recovery-stage-v18/boot-5.4.210-kexec-stage-builtin-recovery.avb.img" \
  scripts/host/recovery-linux.sh boot
```

The v18 rollback watchdog remains armed after ACM appears. Do not use the
legacy ACM helpers to load or execute another payload. The next permitted
control path is the framed responder in
[stable recovery control plane](docs/recovery-control-plane.md).

The fixed ACM controller verifies the exact persistent fallback without host
networking or a fallback client key. It sends one nonce-bound read-only health
payload over the exact USB serial interface and verifies the result with
Alpine's already-pinned Ed25519 SSH host key. The installed fallback exposes
only a legacy interactive BusyBox shell. Alpine enables per-command history
saving, so accepting the launcher can update the shell-selected history file
before it starts the child. Reading the interpreter, libraries, tools, and
host key from a writable `relatime` ext4 root can also update inode access
times. The launcher is bounded below Alpine's 2,048-byte BusyBox editing
limit. It starts Python with isolated/no-site/bytecode-disabled flags,
announces a nonce-bound ready marker, and only then accepts bounded,
hash-checked source chunks under a phone-side receive deadline. Missing or
partial delivery exits without executing the payload. The child returns to
the existing supervised shell after non-reboot actions. Every action therefore
requires a separate action-scoped storage-write guard:

```sh
ALLOW_FALLBACK_ACM_CONTROL=1 \
ALLOW_PHONE_CREDENTIAL_USE=1 \
ALLOW_FALLBACK_ACM_STORAGE_WRITE=1 \
  scripts/host/fallback-acm-control.py \
  preflight /secure/path/fallback-known-hosts \
  /secure/path/fallback-preflight.record
```

Its separate `reboot` action rechecks the same boot after a verified ACK,
requests bootloader mode only through Linux `RESTART2("bootloader")`, and
requires the same physical USB port and exact `lahaina` fastboot product.
It has a second explicit guard and must not be retried after an ambiguous
disconnect. It does not flash, mount, change `authorized_keys`, or explicitly
write a partition; BusyBox history and possible read-induced atime updates are
the bounded phone-storage exception.

```sh
ALLOW_FALLBACK_ACM_CONTROL=1 \
ALLOW_PHONE_CREDENTIAL_USE=1 \
ALLOW_FALLBACK_ACM_STORAGE_WRITE=1 \
ALLOW_FALLBACK_BOOTLOADER_REBOOT=1 \
  scripts/host/fallback-acm-control.py \
  reboot /secure/path/fallback-known-hosts
```

## Active server direction

The current active image is intentionally smaller than the proven fallback:

- kernel, initramfs, minimal init, USB networking, and key-only SSH;
- logging, watchdog, rollback, power, thermal, and hardware telemetry;
- only the tools required by the current hardware gate.

The active replacement recipe packages only the signed Arch base,
the exact Linux 7.1.4 modules, `attr`, `diffutils`, and OpenSSH additions. It
removes the generic kernel, all `linux-firmware*` bundles, published accounts,
desktop/browser/GPU/Wi-Fi/VPN/agent packages, reusable machine identity, and
reusable SSH host keys. The new `headless-ssh-v2` source twin-builds to
536,750,378 bytes and seals as a 536,747,283-byte, 37,735-entry read-only
network lower. Package format v3 binds one canonical Ed25519 public-key
fingerprint across `/etc/rog5/build`, `/root/.ssh/authorized_keys`, the full
tree seal, and the package manifest; effective `sshd` policy consults only
that bound path. The tracked result uses the public-only fixture whose private
half was destroyed, remains unbooted, and grants no credential or phone
authority. The separate `headless-ssh-network-root-v3` fixture candidate now
passes twin signed-bundle, native verifier, shell-free recovery, and
byte-identical ASUS wrapper gates; it remains unbooted with `authority=none`.
A deployment-key admission gate now derives the public half through the fixed
host `ssh-keygen`, rejects every tracked fixture identity, and requires one
exact v3 package/candidate/runtime-manifest chain before privilege or phone
discovery. A dedicated non-fixture key now binds the verified root, candidate,
signed bundle, recovery trust root, and wrapper. The admitted package and
candidate hashes continue through the fixed v3 NFS
marker/recovery rendezvous and strict runtime verifier without changing the
historical path or accepting a tracked fixture. The fixed v3 export installer
and its unprivileged launcher are implemented and hostile-tested.
They reject tracked fixtures and unsafe archive metadata, copy caller-owned
archive bytes into an unreachable anonymous snapshot before inspection,
verify and sync the extracted root, and publish only by no-replace rename.
The first export attempt stopped before publication because SteamOS provides
only a 230 MiB `/var` filesystem while the sealed lower expands to 1.53 GiB.
The reviewed remediation is now installed and the host deployment preflights
pass. Serial health inspection proved the exact healthy Alpine fallback,
but its two older authorized keys do not include the new deployment key.
The fixed ACM verifier removes that dependency without changing fallback
configuration or `authorized_keys`: Alpine signs one canonical nonce-bound
health record with its existing host key, and the host verifies it against
the private pin already retained outside Git. A source audit found that the
legacy interactive shell can persist the launcher in BusyBox history, while
ordinary reads may update inode access times. The standing operator
authorization now covers those bounded effects, but the same protocol,
preflight, one-shot, and cleanup gates remain mandatory. The hardware-free
protocol and lifecycle integration pass.
See the
[corrected twin-build result](test-results/2026-07-29-corrected-headless-candidate-offline.md),
[root hardening result](test-results/2026-07-30-headless-root-credential-reproducibility-hardening.md),
[key-bound package result](test-results/2026-07-30-headless-ssh-v2-key-bound-package.md),
[key-bound candidate result](test-results/2026-07-30-headless-ssh-v2-candidate-offline.md),
[deployment-key admission result](test-results/2026-07-31-headless-ssh-v2-key-admission-offline.md),
[v3 profile-threading result](test-results/2026-07-31-headless-ssh-v3-profile-threading-offline.md),
[v3 export-installer result](test-results/2026-07-31-headless-ssh-v3-export-installer-offline.md),
[SteamOS export-storage remediation](test-results/2026-07-31-steamos-export-storage-remediation.md),
[SteamOS deployment preflight](test-results/2026-07-31-steamos-deployment-preflight-live.md),
[authenticated fallback ACM result](test-results/2026-07-31-fallback-acm-control-offline.md),
[Arch Linux ARM userspace](docs/arch-linux.md) and the
[runtime integration result](test-results/2026-07-29-headless-runtime-integration-offline.md),
plus the
[live rejection](test-results/2026-07-29-headless-stable-recovery-live.md).

The next target observation is no longer an ad-hoc terminal transcript. One
read-only probe and fail-closed verifier now bind an 88-field private record to
the exact corrected candidate, boot ID, all six active core capabilities,
exact eight-CPU topology, three Qualcomm EPSS CPUfreq policies,
device-specific RAM/thermal thresholds, attested OverlayFS/NFSv4.2/tmpfs mount
IDs and backing paths, zero block/SCSI/RPMB/UFS exposure, and the still-armed
rollback watchdog. The same record now proves the exact ConfigFS NCM gadget,
primary high-speed UDC, isolated `/30` route with no default route, one current
USB-peer SSH session, and matching 256-bit Ed25519 client/server public-key
identities.
The strict-SSH capture runner cannot boot, sign, reboot, disarm, or retry
execution. Because this credential-free root creates a volatile server host
key in RAM, a separate bootstrap now pins only the public Ed25519 key after
proving that the exact target NCM gadget replaced signed recovery on the same
physical USB port. No client key is offered during that discovery. Both paths
may proceed under the standing authorization only after their exact artifact,
preflight, one-shot, rollback, and cleanup gates pass.

The Alpine fallback already proves that the OLED can remain off while server
and remote-GUI services continue. Its ttyd/noVNC/KWin/Plasma/Chromium setup is
preserved as an operator lifeline, not copied into the active mainline root.
Historical desktop and A660 work remains frozen until the headless 24-hour
reliability gate passes. See [roadmap](ROADMAP.md),
[remote GUI](docs/remote-gui.md), and [current state](docs/current-state.md).

Email, CVs, browser profiles, API credentials, and job-application data do
not belong in the image or repository. They should later be exposed to a
confined agent through narrow, revocable connectors with explicit
confirmation for external submissions.

## Repository layout

```text
configs/       kernel configuration fragments
containers/    reproducible cross-build environment
docs/          current state, architecture, audit, and operating guidance
dts/           reviewed device-tree source and overlays
initramfs/     recovery, network-root, and persistent-root init sources
manifests/     artifact identities, acceptance records, and boot policy
packaging/     Alpine, Arch, and host service files
patches/       versioned kernel changes
scripts/       host orchestration, device tools, verifiers, and tests
test-results/  redacted evidence reports
tools/         small diagnostics and future recovery components
```

Large outputs under `artifacts/`, `build/`, and `dist/` are ignored. They are
not preserved by Git and must not be manually pruned until the reviewed
artifact-retention plan exists.

## Development order

The project no longer advances by adding another shell-driven diagnostic
tier. Work proceeds in this order:

1. postmortem oracle, fixed recovery, CI, QEMU, and build-loop reduction;
2. minimal read-only Linux root with USB networking and SSH;
3. charging, battery, thermal, reboot, suspend, wake, and screen-off;
4. buttons, touch, sensors, audio, Wi-Fi, Bluetooth, GPS/modem where feasible;
5. persistent 24-hour headless reliability;
6. display, then headless GPU, then optional desktop/remote GUI;
7. hotspot, automation, and upstream-oriented kernel maintenance.

The full plan and completion criteria are in [ROADMAP.md](ROADMAP.md).
