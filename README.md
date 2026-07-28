# ROG Phone 5 native Linux

This project is bringing native Linux to the ASUS ROG Phone 5 (`anakin`,
Snapdragon 888 / SM8350) as a low-power ARM server and usable desktop. The
target is modern Arch Linux ARM with Plasma, remote administration while the
OLED is off, reliable charging and suspend policy, Wi-Fi, a fail-closed
VPN-backed hotspot, and upstream-style Adreno 660 acceleration.

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
| Recovery control | Reference, native protocol, signed verifier, and same-descriptor load pass offline; fixed-host fetch and image integration remain required |
| Mainline kernel | Reproducible Linux 7.1.4 board port; subsystem bring-up remains incremental |
| Mainline userspace | Arch server/Plasma roots build and verify offline; successor-v3 is not promoted |
| Persistent Arch root | Staged and sealed offline; P2 and entry-v1 live attempts were rejected and consumed |
| GPU | A660 registration/firmware/allocation boundaries progressed; stable accelerated desktop is not yet achieved |
| Wi-Fi | WCN6855/PCIe package passes offline tests; hardware cycle remains on HOLD |
| VPN hotspot | IPv4/IPv6 and real WireGuard fail-closed tests pass offline; radio/provider live gate remains |
| New phone action | None authorized by repository state; build the stable recovery control plane first |

Nothing in this table grants permission to flash or repeat a consumed live
gate.

## Start here

- [Current state](docs/current-state.md) — concise facts and blockers.
- [Roadmap](ROADMAP.md) — ordered work and acceptance gates.
- [Stable recovery control plane](docs/recovery-control-plane.md) — the next
  implementation and its test-first protocol.
- [Repository audit](docs/repository-audit-2026-07-28.md) — what is active,
  evidence, archived, or a local cleanup candidate.
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
scripts/host/test-repository-linux.sh quick
```

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

## Desktop/server direction

The persistent fallback already demonstrates the desired operating model:

- the OLED can remain off while SSH, ttyd, noVNC, and Chromium automation
  continue;
- host forwards are loopback-only and reconnect through a user service;
- the phone-side remote GUI supervisor is singleton and restartable;
- the development Arch root has a locked, resource-limited automation account
  separate from the desktop user.

The target desktop is minimal Plasma/KWin rather than a full default GNOME or
KDE installation. On this 12 GB device, reliability, idle CPU, GPU stability,
and battery drain matter more than saving the last few hundred MiB of RAM.
See [remote GUI](docs/remote-gui.md) and
[current state](docs/current-state.md).

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

1. protocol/state/fault tests;
2. fixed recovery responder and signed runtime manifest;
3. one reproducible recovery re-freeze and staging-only promotion;
4. persistent Arch boot closure;
5. GPU, Wi-Fi, VPN hotspot, desktop, and power acceptance;
6. upstream-oriented Linux 7.x maintenance.

The full plan and completion criteria are in [ROADMAP.md](ROADMAP.md).
