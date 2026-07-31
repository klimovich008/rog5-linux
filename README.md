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
| Core compatibility | ASUS 5.4 and accepted 7.1 ancestry now form a fail-closed profile/config/evidence oracle; the active-core source/DT gate has 37 source and 23 corrected-DTB checks, while an 88-field runtime probe covers all six active capabilities, including exact RAM/CPUfreq topology, mount-bound NFSv4.2 storage isolation, and target-side USB/NCM/SSH identity; the corrected candidate remains live-pending |
| Buttons/indicator | Exact Linux 7.1.4 source/config/module and DTB contracts pass offline; a reproducible 67,520-byte native AArch64 service validates the exact power-key/LPG identities and emits one bounded default-off green pulse per physical press; the historical headless-core-v2 root is pruned and must not be relabeled as its successor |
| Mainline userspace | SSH-only Arch lower exposed target NCM but reset before SSH with historical DTB v1. The credential-clean `headless-ssh-v2` replacement twin-builds to one 536,750,378-byte source identity and seals as a verified 536,747,283-byte v3 package whose canonical Ed25519 fingerprint is bound across root record, tree seal, and package; a distinct fixture-only corrected-DTB candidate passes the complete twin-bundle/recovery/wrapper gate. A hostile-tested local admission gate now derives the public half from an exact private key and rejects all fixture identities before privilege or phone discovery; a non-fixture rebuild and v3 stable-recovery/NFS profile remain pending |
| Persistent Arch root | Staged and sealed offline; P2 and entry-v1 live attempts were rejected and consumed |
| GPU | Accepted A660 ancestry is frozen while headless core mechanics are completed |
| Wi-Fi | WCN6855/PCIe package passes offline tests; hardware cycle remains on HOLD |
| VPN hotspot | IPv4/IPv6 and real WireGuard fail-closed tests pass offline; radio/provider live gate remains |
| New phone action | None authorized by repository state; production trust-root approval and staging promotion remain |

Nothing in this table grants permission to flash or repeat a consumed live
gate.

## Start here

- [Current state](docs/current-state.md) — concise facts and blockers.
- [Steam Deck host setup](docs/steam-deck-host.md) — pinned rootless builder,
  complete ASUS source verification, and fail-closed source-volume import.
- [Steam Deck ASUS 5.4 builder qualification](test-results/2026-07-30-steam-deck-asus-builder-qualified.md)
  — independent rootfs reproduction and twin byte-identical kernel builds.
- [Steam Deck ARM64 recovery-builder qualification](test-results/2026-07-30-steam-deck-recovery-builders-qualified.md)
  — reboot-safe rootless ARM64 emulation and exact responder/verifier
  filesystem, package, and binary identities.
- [Linux 7.1.4 network-root reconstruction](test-results/2026-07-30-network-root-kernel-ref-state-reconstruction.md)
  — exact Git ref-state root cause, reconstructed historical builder, and
  twin byte-identical recovery of all five frozen kernel artifacts.
- [Headless recovery dependency closure](test-results/2026-07-30-headless-recovery-dependency-closure.md)
  — exact v18r/network-root/headless reconstruction, immutable AOSP boot
  tools, compact boot-v3 template, and accepted-config wrapper successor.
- [Key-bound headless SSH v2 package](test-results/2026-07-30-headless-ssh-v2-key-bound-package.md)
  — hostile key/parser tests, byte-identical source roots, v3 fingerprint
  binding, deterministic sealed packaging, and zero phone/credential use.
- [Key-bound headless SSH v2 candidate](test-results/2026-07-30-headless-ssh-v2-candidate-offline.md)
  — exact package/candidate binding, twin signed bundles, shell-free recovery,
  byte-identical ASUS wrappers, and destroyed disposable signing key.
- [Deployment SSH-key admission gate](test-results/2026-07-31-headless-ssh-v2-key-admission-offline.md)
  — exact private-to-public derivation, non-fixture package/candidate/manifest
  binding, hostile metadata and identity tests, and lifecycle ordering before
  privilege or phone discovery.
- [Corrected headless successor offline candidate](test-results/2026-07-30-corrected-headless-successor-offline.md)
  — twin accepted-config ASUS wrappers, boot-v3/AVB verification, signed
  bundle integration, and destroyed disposable key.
- [Corrected successor live-gate admission](test-results/2026-07-30-corrected-successor-live-gate-admission.md)
  — exact production artifact-profile verification with a proven exit before
  phone discovery or credential inspection.
- [Headless stable-recovery live result](test-results/2026-07-29-headless-stable-recovery-live.md)
  — exact signed transaction, rejection, rollback, root cause, and corrected
  offline candidate.
- [Corrected headless candidate twin build](test-results/2026-07-29-corrected-headless-candidate-offline.md)
  — exact corrected DTB, bundle, recovery, wrapper, trust boundary, and
  byte-identical offline products.
- [Corrected DTB semantic oracle](test-results/2026-07-29-corrected-dtb-semantic-oracle-offline.md)
  — exact rejected-to-accepted property delta, malicious fixtures, and
  fail-closed builder integration.
- [Core compatibility oracle](docs/core-compatibility-oracle.md) and
  [offline result](test-results/2026-07-29-core-compatibility-oracle-offline.md)
  — exact ASUS 5.4/accepted 7.1 ancestry, active Kconfig contract, mutation
  coverage, and the boundary before evaluating another kernel.
- [Minimal-headless runtime acceptance](docs/minimal-headless-runtime-acceptance.md)
  and
  [offline result](test-results/2026-07-29-minimal-headless-runtime-acceptance-offline.md)
  — canonical target evidence, candidate/runtime thresholds, strict-SSH
  capture, and the still-armed rollback boundary.
- [Storage-isolation result](test-results/2026-07-29-storage-isolation-offline.md)
  — mount-attested NFSv4.2 plus zero block/SCSI/RPMB/UFS exposure.
- [Buttons and status indicator](docs/buttons-indicator.md) and
  [offline result](test-results/2026-07-30-buttons-indicator-offline.md) —
  stock-evidenced key/LED mapping, exact additive DTB delta, accepted
  source/config/module gate, hostile tests, and the remaining physical gate.
- [Native key-indicator runtime](docs/headless-key-indicator.md) and
  [offline result](test-results/2026-07-30-headless-key-indicator-offline.md)
  — sealed static AArch64 helper, exact runtime identity gate, bounded
  press-only policy, QEMU fixtures, and the successor headless-root boundary.
- [Volatile target host-key bootstrap](docs/minimal-headless-host-key-bootstrap.md)
  and
  [offline result](test-results/2026-07-29-minimal-headless-host-key-bootstrap-offline.md)
  — recovery-to-target physical USB continuity, credential-free Ed25519
  discovery, and the strict-SSH handoff for temporary development boots.
- [Minimal-headless one-shot lifecycle](docs/minimal-headless-live-cycle.md)
  — fail-closed recovery, bundle/NFS sequencing, strict-SSH observation,
  watchdog rollback, fallback proof, cleanup, and durable outcome rules.
  The
  [offline result](test-results/2026-07-29-minimal-headless-live-cycle-offline.md)
  records the original fourteen failure-path scenarios; the current controller
  adds the separately reported deployment-key admission boundary.
- [Roadmap](ROADMAP.md) — ordered work and acceptance gates.
- [Stable-wrapper configuration slimming](docs/stable-wrapper-config-slimming.md)
  and
  [offline result](test-results/2026-07-30-stable-wrapper-config-slimming-offline.md)
  — source-sealed config reduction, hostile tests, clean twin builds, and
  boot-v3/AVB structural evidence with no live authority.
- [Stable recovery control plane](docs/recovery-control-plane.md) — the next
  implementation and its test-first protocol.
- [Recovery re-freeze integration](docs/recovery-refreeze-integration.md) —
  exact initramfs/wrapper inputs, ordering, offline evidence, and remaining
  signing boundary.
- [Repository audit](docs/repository-audit-2026-07-28.md) — what is active,
  evidence, archived, or a local cleanup candidate.
- [Host storage cleanup](docs/host-storage-cleanup.md) — read-only inventory,
  preservation rules, reclaim order, and the explicit approval boundary.
- [Host storage audit](test-results/2026-07-29-host-storage-audit.md) — current
  candidate sizes, dirty-worktree closure, and zero-delete evidence.
- [Archive index](docs/archive-index.md) — how to inspect the pre-reduction
  checkpoint.
- [Test plan](docs/test-plan.md) and
  [network-root guide](docs/network-root.md) — detailed historical operating
  procedures; do not interpret old live commands as current authority.
- [Remote GUI](docs/remote-gui.md) — loopback-only SSH tunnel and screen-off
  administration.
- [Hardware contract](docs/hardware-contract.md),
  [persistent storage](docs/persistent-storage.md), and
  [kernel port](docs/kernel-port.md) — detailed subsystem evidence.
- [A660 acceptance](docs/a660-acceptance.md) — bounded staging and promoted
  soak gates for Turnip, KWin, screen cycling, thermal, memory, and battery.
- [Automation security](docs/security-automation.md) — credential and agent
  isolation boundaries.

## Safety model

- Never flash an experimental boot, vendor boot, recovery, DTB, or rootfs.
- Keep the installed fallback slot untouched.
- Use only an attended `fastboot boot` of an explicitly allowed image.
- Require exact artifact size and SHA-256, one fastboot device, and product
  `lahaina`.
- Keep physical storage read-only in staging and target diagnostics.
- Keep an independent rollback watchdog armed.
- Treat every live diagnostic payload as single-use.
- Do not retry an execute action after an ambiguous disconnect.
- Keep credentials and private evidence outside the repository.

`manifests/artifacts.tsv` is an inventory, not boot authority.
`manifests/temporary-boot-images.tsv` is the deny-by-default boot policy.
Only the twice-live-accepted v18 staging image is currently admitted.

## Recovery host workflow

Run the hardware-free host/control suite first:

```sh
scripts/host/test-repository-linux.sh ci
```

The `ci` tier needs no phone, Vulkan stack, desktop, or delegated cgroup. It is
the default pull-request gate for the recovery protocol and host safety path.
The workflow also has a separate full-system ARM64 job. It builds a minimal
`tinyconfig` kernel from the exact pinned upstream Linux v7.1.4 commit and
boots a syscall-only initramfs under QEMU. Its content-keyed kernel cache is
invalidated when the build recipe changes. This proves the generic
kernel-to-PID-1 handoff without pretending to emulate ROG Phone hardware.
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

If the exact persistent fallback is reachable, the guarded helper can request
bootloader mode through Linux `RESTART2("bootloader")`. It verifies the pinned
fallback before acting and never writes a partition:

```sh
SSH_KEY=/secure/path/rog5-client-key \
KNOWN_HOSTS=/secure/path/rog5-known-hosts \
  scripts/host/reboot-fallback-to-fastboot.sh preflight
```

The mutating `reboot` action still requires its own explicit environment
guard. See the script before use.

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
discovery. Its tests use disposable keys only. The next boundary is rebuilding
that chain around a separately authorized deployment key, adding the v3
stable-recovery/NFS profile, and passing host-only artifact preflight.
See the
[corrected twin-build result](test-results/2026-07-29-corrected-headless-candidate-offline.md),
[root hardening result](test-results/2026-07-30-headless-root-credential-reproducibility-hardening.md),
[key-bound package result](test-results/2026-07-30-headless-ssh-v2-key-bound-package.md),
[key-bound candidate result](test-results/2026-07-30-headless-ssh-v2-candidate-offline.md),
[deployment-key admission result](test-results/2026-07-31-headless-ssh-v2-key-admission-offline.md),
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
remain offline-only pending fresh live authorization.

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
