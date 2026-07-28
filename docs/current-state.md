# Current state — 2026-07-28

This file records facts, not planned work or live authority. The ordered plan
is in [ROADMAP.md](../ROADMAP.md), and the detailed recovery redesign is in
[recovery-control-plane.md](recovery-control-plane.md).

## Hardware and boot

- Device: ASUS ROG Phone 5, codename `anakin`, Snapdragon 888 / SM8350,
  Adreno 660, roughly 11 GiB usable RAM.
- Bootloader: unlocked; verified boot reports orange.
- Recorded active Android slot: B.
- Experimental boot method: attended `fastboot boot` only.
- No experimental kernel, recovery, DTB, or Linux root has been flashed.
- Installed fallback: userdata-backed Alpine 3.24 on
  `5.4.134-qgki-perf-00001-g6c308144c23e`.
- Proven temporary baseline: vendor-derived
  `5.4.210-qgki-perf #20`.
- Mainline development kernel: reproducible Linux 7.1.4 ARM64.

The installed fallback is intentionally left available after every temporary
cycle.

## What works on the vendor-derived baseline

The 5.4.210 temporary baseline has passed:

- UFS root and initramfs startup;
- USB NCM and key-only SSH;
- DSI DRM/panel and FocalTech touch;
- real Qualcomm charger path and UPower battery reporting;
- Plasma Mobile with software rendering;
- power-button screen toggle, DPMS, and OLED-off server operation;
- Wi-Fi client and AP/hotspot after delayed radio startup;
- supervised modem support processes.

The persistent 5.4.134 fallback remains useful for SSH, screen-off operation,
and remote GUI, but it does not have matching ADSP/battery modules.
Incompatible 5.4.210 modules must not be force-loaded into it.

The fallback screen service was restored after the latest rejected P2
entry cycle. The panel can remain off while the server is reachable.

## Recovery

Recovery v18 is the only temporary boot image admitted by
`manifests/temporary-boot-images.tsv`. It has:

- exact fastboot product `lahaina`, observed by both accepted v18 preflights;
- two completed credential-free RAM-only staging/rollback cycles;
- exact recovery USB identity, ACM, and NCM;
- zero block-backed mounts;
- all observed physical disks/partitions forced read-only;
- an armed automatic rollback watchdog;
- a separate accepted Linux 7.1.4 load/target/rollback cycle.

Evidence:

- [v18 offline](../test-results/2026-07-24-recovery-v18-offline.md)
- [v18 staging live](../test-results/2026-07-24-recovery-v18-live.md)
- [v18 mainline live](../test-results/2026-07-24-recovery-v18-mainline-live.md)

The transport is accepted; the control protocol is not. Recovery still starts
an interactive BusyBox shell on `/dev/ttyGS0`. Host tools send shell text and
search output for markers. Echo, stale text, serial-open races, and the
expected disconnect during `kexec -e` prevent reliable request correlation
and safe retry.

There is therefore no active payload-execution gate. The next recovery must
implement the framed, device-session-bound, at-most-once protocol in
[recovery control plane](recovery-control-plane.md).

The current source has now removed that shell from recovery, network-root,
and persistent-root. A deterministic builder replaces the accepted v18
userspace init, scrubs SSH/getty/credentials, and integrates the static
responder, fetcher, verifier, pinned kexec runtime, and a caller-supplied raw
public key. With an ephemeral key, two complete image builds are
byte-identical and pass extraction verification. This is an offline
re-freeze test, not a boot candidate: v18 itself remains unchanged and
interactive, no production trust root exists, and no wrapper or AVB image was
created. See [re-freeze integration](recovery-refreeze-integration.md).

The protocol reference model and host write-ahead ledger pass 47 offline
fault, replay, parser, crash-consistency, and concurrency tests. A static
native responder now passes 53 pseudo-terminal and PREPARE-boundary tests as
both a host build and a real AArch64 static binary under QEMU. A separate
static native signed-bundle verifier enforces the canonical manifest, raw
Ed25519 trust root, artifact identity, arm64 Image/FDT policy, bounded
gzip/newc initramfs, and generated command line. The verifier now transfers
immutable write-sealed snapshots of the exact three verified files to the
responder over `SCM_RIGHTS`; the responder parses the canonical plan, performs
bounded watchdog-supervised `kexec -c -l` through `/proc/self/fd`, and
persists `PREPARED` only after load success. Host and AArch64/QEMU tests
replace and overwrite every bundle pathname and cover malformed handoff
without descriptor leaks, bounded child failure/timeout cleanup, watchdog
death, ledger-boundary replay, and crash-after-load retry.
An uncommitted image is now removed with fixed `kexec -c -u` after a rejected
or timed-out load, after a returned executor, and during every non-prepared
startup. The fixed execution child also uses bounded kill/reap under watchdog
death. These unload and executor paths pass through the same fake-kexec seam
on host and AArch64/QEMU; real kernel-side unload remains a staging-only live
gate.

The fixed-host acquisition helper now passes 28 native tests,
28 tests as root through a network-disabled container, and 23 executable
AArch64/QEMU cases, with five expected QEMU-only skips. It binds a fixed NCM
source/interface/peer, isolates
network parsing in a UID/GID-65534 chroot/seccomp worker, independently
revalidates the root-owned, non-writable staged files in the privileged
parent, and publishes with `RENAME_NOREPLACE`. QEMU user mode cannot safely
emulate a guest seccomp filter, so native and root suites own that gate. The
responder invokes the helper first under a 65-second outer deadline and maps
fetch failure or permanent bundle-ID conflict without invoking verifier or
kexec. The three binaries now pass offline initramfs integration, but no
production signing key exists. The accepted v18 recovery still contains the
old interactive control shell. None of these offline checkpoints grants live
authority.
See the
[reference result](../test-results/2026-07-28-recovery-control-reference-offline.md)
and
[native result](../test-results/2026-07-28-recovery-control-native-offline.md),
plus the
[runtime bundle contract](recovery-bundle-contract.md) and
[verifier result](../test-results/2026-07-28-recovery-bundle-verifier-offline.md).
The combined descriptor/load checkpoint is recorded in the
[sealed PREPARE result](../test-results/2026-07-28-recovery-sealed-prepare-offline.md).
The fixed transport is specified in
[recovery fetch contract](recovery-fetch-contract.md), with evidence in the
[fixed fetch offline result](../test-results/2026-07-28-recovery-fixed-fetch-offline.md).
The matching one-shot host server and root-owned runtime firewall controller
now pass nine protocol/descriptor tests and nine mocked controller-lifecycle
tests. The server opens only the fixed caller-owned bundle root, serves
already-verified descriptors as an unprivileged capability-free process, and
the controller restores every address, rule, zone assignment, and
NetworkManager override it creates. The reviewed helpers have not been
installed and no live host network state was changed. See the
[host server result](../test-results/2026-07-28-recovery-host-server-offline.md).

The fallback reserves ramoops memory but cannot currently read it: no driver
is bound, `/dev/mem` and `devmem` are absent, `CONFIG_DEVMEM` is unset, and a
matching module environment is unavailable. The fallback pstore-empty gate
remains unchanged.

## Persistent Arch root

The successor-v3 Arch root is built, verified, and recursively sealed offline.
It contains:

- systemd and minimal Plasma/server packages;
- exact Linux 7.1.4 modules and pinned firmware;
- key-only SSH;
- screen-off-first behavior and confined power-button handling;
- a locked, resource-limited automation account;
- fail-closed hotspot packaging.

The persistent-root P2 package also passed its offline construction and
storage-isolation contract. Its live target did not reach the required
acceptance marker and returned to the exact fallback. Follow-up wrapper,
timing, identity, release, and procfs diagnostics narrowed the failure but did
not produce a promotable target.

Entry-v1 then moved the oracle earlier. Its sole allowed live cycle executed
kexec once, never produced a stable entry marker, and returned to the exact
fallback with the root still `UNBOOTED` and selectors absent.

Evidence:

- [P2 offline](../test-results/2026-07-28-persistent-root-p2-offline.md)
- [P2 live rejected](../test-results/2026-07-28-persistent-root-p2-live-rejected.md)
- [entry-v1 offline](../test-results/2026-07-28-persistent-root-entry-v1-offline.md)
- [entry-v1 live rejected](../test-results/2026-07-28-persistent-root-entry-v1-live-rejected.md)

P2 and entry-v1 are consumed evidence. They must not be retried. Persistent
root work resumes only after stable recovery can classify one execute
transaction without relying on terminal markers.

## Mainline GPU

The vendor KGSL path can identify A660 with Mesa Turnip on a fresh boot, but a
second raw `/dev/kgsl-3d0` open times out after GMU HFI and translation-fault
errors. That failure occurs on both tested vendor kernels and poisons KGSL
until reboot. It is not caused by KDE or noVNC.

The Linux 7.1.4 path has isolated, rollback-guarded evidence for:

- Adreno SMMU;
- A660 registration;
- firmware request;
- microcode allocation;
- GMU resume entry;
- GMU/linked-CX runtime power management offline.

V9 GMU resume entry is the last live-accepted GPU ancestry. The v10 GMU/CX
runtime-PM package is offline-accepted and remains on HOLD; it has not run on
the phone. The v11 clock-preparation change is source/offline work only and is
not a runnable candidate. Stable DRM render-node operation, repeated
open/close, KWin/Wayland, Chromium, suspend/resume, and thermal acceptance
remain pending.

Machine acceptance records remain under `manifests/acceptance/`.

## Wi-Fi and VPN hotspot

Read-only fallback evidence identifies Qualcomm PCIe endpoint `17cb:1103`
with ASUS subsystem `17cb:0108`. The WCN6855 package supplies the reviewed
PCIe/QMP/power graph, matching ath11k modules, firmware layout, regulatory
data, enumeration-only oracle, root overlay, watchdog handoff, and
verifier-first host controls.

Two clean builds/packages are reproducible. The protected successor-v3 root
and one-cycle runner pass offline readiness. The package remains
`UNBOOTED_HOLD`; no mainline radio activation has occurred.

The hotspot v2 policy passes offline:

- kill-switch-first setup and partial-failure rollback;
- IPv4 and IPv6 ordinary-uplink leak rejection;
- unsolicited VPN-side ingress rejection;
- real WireGuard packet, handshake, and encrypted-transfer checks;
- UDP and TCP DNS through the tunnel;
- endpoint/interface loss remains fail-closed;
- exact cleanup and restart recovery.

Still pending on real hardware are ath11k client/AP operation, provider
WireGuard, DHCP/provider DNS, coexistence, throughput, thermal behavior, and
battery drain.

## Desktop, remote access, and memory

The fallback has a loopback-only remote administration stack reached through
a reconnecting host user service:

- ttyd terminal;
- noVNC/Xvnc emergency desktop;
- nested KWin/Plasma;
- Chromium CDP;
- singleton phone-side supervisor.

An induced tunnel failure restarted correctly, and a Chromium termination was
recovered without creating duplicate supervisors. The physical panel remained
off.

The recorded screen-off baseline retained about 10.1 GiB available memory and
zero swap. Approximate proportional memory was 390 MiB for KDE, 345 MiB for
Chromium, and 67 MiB for remote transport; a short low-overhead sample was
below 1% aggregate CPU. Wall-power and battery measurements are still needed.

A minimal Plasma/KWin installation is preferred over a full default Plasma or
GNOME environment. The device has enough RAM; idle power, GPU reliability,
service count, and thermal stability are the stronger constraints.

See [remote GUI](remote-gui.md).

## Automation-agent boundary

The development Arch image has a separate locked agent account with native
systemd limits:

- two CPUs;
- 2 GiB RAM;
- 512 MiB swap;
- 256 tasks;
- reduced CPU and I/O weight;
- private writable state only.

No email account, CV, browser profile, provider token, or API key is embedded.
Future Codex/Claude/OpenRouter-style automation should use narrow connectors,
revocable credentials, audit logs, and explicit confirmation for external
submissions. A general desktop login with access to all personal data is not
the intended security model.

## Refresh rate and screen-off policy

The vendor panel exposes fixed 60, 90, 120, and 144 Hz profiles. Dynamic FPS,
qsync, and dynamic bit clock are not advertised by the observed connector
capabilities.

- 60 Hz is the server/battery default.
- 90 Hz is the balanced interactive profile.
- 120/144 Hz remain explicit performance choices.
- DPMS off plus backlight zero is the default remote-server state.

Mainline refresh-rate acceptance waits for stable DRM/KWin acceleration.

## Current blockers

1. Replace interactive ACM control with a framed fixed responder and
   at-most-once execute state.
2. Re-freeze and promote one stable recovery image through staging-only tests.
3. Re-enter persistent Arch boot with unambiguous outcome classification.
4. Complete A660 clock/power/GMU bring-up to a stable render node.
5. Run separately authorized WCN6855 and VPN-hotspot hardware gates.
6. Measure screen-off wall power, charging, thermal behavior, and refresh-rate
   cost on the promoted kernel/userspace.

No new phone action is needed while blocker 1 is being implemented offline.

## Operational constraints

- Credentials and private identifiers stay outside Git.
- `artifacts/`, `build/`, and `dist/` are ignored and are not covered by the
  Git archive tag.
- The accepted pre-reduction tracked state is recoverable at
  `archive/pre-stable-recovery-2026-07-28`.
- External build dependencies such as `mkbootimg` and `avbtool.py` still need
  an explicit pinned bootstrap path for fresh-clone reproducibility.
- Fastboot remains boot-only. The fallback slot and guarded
  `RESTART2("bootloader")` helper remain unchanged.
