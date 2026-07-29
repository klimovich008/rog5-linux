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
| Mainline kernel | Reproducible Linux 7.1.4 board port with pinned source tag/commit/tree and rootless x86_64 builder; subsystem bring-up remains incremental |
| Mainline userspace | SSH-only Arch lower exposed target NCM but reset before SSH with historical DTB v1; the corrected v3-isolated target, bundle, shell-free recovery, and wrapper now reproduce in a complete offline twin build |
| Persistent Arch root | Staged and sealed offline; P2 and entry-v1 live attempts were rejected and consumed |
| GPU | Accepted A660 ancestry is frozen while headless core mechanics are completed |
| Wi-Fi | WCN6855/PCIe package passes offline tests; hardware cycle remains on HOLD |
| VPN hotspot | IPv4/IPv6 and real WireGuard fail-closed tests pass offline; radio/provider live gate remains |
| New phone action | None authorized by repository state; production trust-root approval and staging promotion remain |

Nothing in this table grants permission to flash or repeat a consumed live
gate.

## Start here

- [Current state](docs/current-state.md) — concise facts and blockers.
- [Headless stable-recovery live result](test-results/2026-07-29-headless-stable-recovery-live.md)
  — exact signed transaction, rejection, rollback, root cause, and corrected
  offline candidate.
- [Corrected headless candidate twin build](test-results/2026-07-29-corrected-headless-candidate-offline.md)
  — exact corrected DTB, bundle, recovery, wrapper, trust boundary, and
  byte-identical offline products.
- [Roadmap](ROADMAP.md) — ordered work and acceptance gates.
- [Stable recovery control plane](docs/recovery-control-plane.md) — the next
  implementation and its test-first protocol.
- [Recovery re-freeze integration](docs/recovery-refreeze-integration.md) —
  exact initramfs/wrapper inputs, ordering, offline evidence, and remaining
  signing boundary.
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

The first concrete userspace profile now packages only the signed Arch base,
the exact Linux 7.1.4 modules, `attr`, `diffutils`, and OpenSSH additions. It
removes the generic kernel, all `linux-firmware*` bundles, published accounts,
desktop/browser/GPU/Wi-Fi/VPN/agent packages, reusable machine identity, and
reusable SSH host keys. Its 535,093,875-byte source becomes a
byte-reproducible 535,094,061-byte sealed read-only network lower with an
explicit hash-bound no-workload manifest and 37,669-entry whole-tree seal. A
dedicated initramfs embeds the exact static AArch64 verifier; an
ephemeral-key signed v2 bundle and the actual consumed-P2
prepare/serve/verify/execute composition pass offline. Its first signed live
transaction exposed target NCM but returned before SSH because the candidate
selected historical DTB v1. The tracked candidate now pins the accepted
GPU/RMTFS-isolated v3 DTB. The complete target, bundle, shell-free recovery,
and wrapper now reproduce twice under one destroyed disposable key, remain
`authority=none`, and are not phone boot authority. See the
[corrected twin-build result](test-results/2026-07-29-corrected-headless-candidate-offline.md),
[Arch Linux ARM userspace](docs/arch-linux.md) and the
[runtime integration result](test-results/2026-07-29-headless-runtime-integration-offline.md),
plus the
[live rejection](test-results/2026-07-29-headless-stable-recovery-live.md).

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
