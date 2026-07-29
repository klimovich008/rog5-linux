# Current state — 2026-07-29

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

The legacy v18 artifact remains unchanged and interactive, but its successor
source removes the shell from recovery, network-root, and persistent-root.
A deterministic builder removes SSH/getty/login/DHCP entry points and
credentials, locks root, and integrates the static responder, fetcher,
verifier, pinned kexec runtime, and a caller-supplied raw public key. Eight
init-policy tests and malicious-archive/init fixtures enforce that boundary.
Builds under different locales and time zones are byte-identical.

That shell-free path has now completed one attended signed live transaction.
The exact guarded runner used only `fastboot boot`; recovery fetched and
verified one signed bundle, returned correlated `PREPARED` and `CLAIMED`
responses, started the target NCM gadget, and automatically returned to the
exact persistent fallback. The durable host intent was resolved as
`FALLBACK_RETURNED`; no commit was retried.

The target did not reach SSH. Its signed candidate selected historical
network-root v1 DTB hash `255c5ac1...`, which leaves RMTFS, GPUCC, GMU, and
the Adreno SMMU enabled and reproduces the documented roughly 16-second
coldplug reset. The tracked candidate now pins the accepted v3-isolated DTB
hash `86e5cb81...` and a regression test requires that complete identity.
The correction now passes a complete twin build of the target bundle,
shell-free recovery initramfs, vendor-compatible wrapper kernel, raw boot
image, and unsigned AVB test wrapper. One disposable test private key was
destroyed before success; retained products say `authority=none`. The
DTB builder now also enforces an exact property-level delta against its base.
The retained rejected v1 and accepted v3 objects differ in only the four
expected RMTFS/GPUCC/GMU/Adreno-SMMU isolation states; malicious node,
property, phandle, truncation, and signal-interruption fixtures fail in core
CI. See the
[semantic oracle](../test-results/2026-07-29-corrected-dtb-semantic-oracle-offline.md).
The correction has not been signed by a live trust root or booted. There is no
repeat live authority. See the
[live result](../test-results/2026-07-29-headless-stable-recovery-live.md)
and
[corrected offline twin build](../test-results/2026-07-29-corrected-headless-candidate-offline.md),
plus [re-freeze integration](recovery-refreeze-integration.md).

The ASUS 5.4 and accepted Linux 7.1 behavioral ancestry is now also encoded in
a strict [core compatibility oracle](core-compatibility-oracle.md). It binds
the historical evidence hashes and markers, artifact-manifest hash, accepted
Image/config identities, corrected candidate Image/DTB/initramfs ancestry,
six active headless capability contracts, six future capability states,
exact CI entries, and the kernel-build verifier invocation. A committed
golden config, the retained accepted 7.1 config, and 33 mutation/CLI tests
pass. The complete hardware-free repository CI tier passes.

This is an ancestry and regression result, not a new hardware result.
`phase=active` means current roadmap scope; only `candidate_status` describes
acceptance. Buttons and battery remain baseline diagnostics, display-off is
evidence-only, and suspend, sensors, and audio remain pending. The corrected
root is still `live-pending` with `authority=none`. See the
[offline result](../test-results/2026-07-29-core-compatibility-oracle-offline.md).

The corrected target's next live observation is now specified independently
of the boot controller. One read-only target probe emits exactly 48 canonical
fields for the six active capabilities. A host verifier binds the record to
the current probe hash, a separately observed boot ID, the full compatibility
oracle, the corrected candidate's root identities, accepted CPU/RAM/thermal
envelopes, strict key-only SSH, and the live 600-second rollback lease. Target,
host, and mocked strict-SSH runner tests pass offline. The runner executes the
probe once and cannot boot, sign, retry kexec, disarm, or reboot. No credential
was used and no phone was contacted. See the
[runtime contract](minimal-headless-runtime-acceptance.md) and
[offline result](../test-results/2026-07-29-minimal-headless-runtime-acceptance-offline.md).

The sealed lower deliberately has no reusable SSH host key, so the corrected
temporary target cannot have a static known-hosts entry before boot. The new
host-key bootstrap closes that development-only gap without `accept-new`: it
records the exact recovery USB device location, requires the
`ROG5_network_root` NCM gadget and `cdc_ncm` driver on the same port, verifies
the direct `169.254.77.1/30` route, scans exactly one nonzero Ed25519 public
key without offering a client credential, rechecks USB and route continuity,
and publishes a caller-owned mode-`0600` alias pin. Fifteen hardware-free test
groups reject stale/cross-boot anchors, duplicate or wrong gadgets, another
port, wrong driver, routed peers, malformed/multiple/RSA/zero keys, unsafe
paths, and missing authorization. This does not create a persistent server
identity or grant a live cycle. See the
[bootstrap contract](minimal-headless-host-key-bootstrap.md) and
[offline result](../test-results/2026-07-29-minimal-headless-host-key-bootstrap-offline.md).

The protocol reference model and host write-ahead ledger pass 48 offline
fault, replay, parser, crash-consistency, and concurrency tests. A static
native responder now passes 55 pseudo-terminal, postmortem, and
PREPARE-boundary tests as both a host build and a real AArch64 static binary
under QEMU. A separate
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

The host now also has one atomic runtime-bundle packager. With an explicitly
supplied ephemeral Ed25519 key, it snapshots the kernel, DTB, and initramfs
through already-open descriptors, creates the canonical signed manifest in a
private staging directory, enforces exact `0700/0500/0400` ownership and mode
policy, and publishes with one no-replace rename. Its refusal suite covers
unsafe identity, timeout, symlink, key, and root metadata; injected signing
failure leaves the bundle root unchanged, and a competing final directory is
preserved. All three fixed profiles pass the native verifier and host-server
opener, and two roots produce byte-identical output with the same inputs. The
persistent Arch payload maps to
`persistent-root-ro-v1`; accepted A660 ancestry maps to `network-root-v1`.
No production key, live bundle, allowlist change, host-network mutation, or
phone action was created by this checkpoint.

The installed fallback still cannot read the ramoops reservation: no driver
is bound, `/dev/mem` and `devmem` are absent, and `CONFIG_DEVMEM` is unset.
The stable recovery wrapper already has built-in `PSTORE_RAM` and the exact
4 MiB ramoops command line. Recovery source now arms rollback first, mounts
pstore read-only, takes an immutable RAM snapshot without deleting records,
and exports state, record count, byte count, SHA-256, and a 512-byte tail
through framed status. Its empty/present/unavailable and malformed-state
tests pass offline. Two clean final builds produced identical initramfs,
wrapper kernel, raw boot-v3, and test-only AVB images. The hashes and commands
are recorded in the
[headless speed-amplifier result](../test-results/2026-07-29-headless-speed-amplifiers-offline.md).
Whether the reserved DRAM survives target → bootloader → recovery remains a
live experiment; no retained log has yet been claimed.

## Active headless Arch root

The first minimal mainline userspace profile now builds and verifies offline.
It is an official signed Arch Linux ARM base plus the exact
`7.1.4-g7a5cef0db479` modules and only three requested additions: `attr`,
`diffutils`, and `openssh`.

The stage removes the generic Arch kernel, twelve `linux-firmware*` packages
(1,281.37 MiB installed), the published `alarm` account, all reusable SSH
host keys, and the reusable machine ID. It enables key-only root SSH and the
existing sleep inhibitor, sets `multi-user.target`, and leaves USB networking
to the initramfs rather than enabling NetworkManager or systemd-networkd.
Desktop, browser, Vulkan, GPU firmware, Wi-Fi, VPN/hotspot, Node, and agent
packages are absent.

The final archive was built from commit
`eb61a45938c851b1b02a2f3151db5265ab9213e7` and passed the complete verifier
inside the staged root and again after clean extraction:

```text
path: artifacts/arch/rog5-arch-headless-ssh-7.1.4.tar.gz
size: 535093875
sha256: 4e472f2fa3f21fd3a5cf6de9eaf96810104083758039e8cdeefc4e03ec4e6427
packages: 150
```

This is 73.3% smaller than the 2,007,033,670-byte successor-v3 Plasma
archive. The number is disk/archive evidence, not a RAM or battery
measurement. Package versions are recorded in the root, but byte-for-byte
reproducibility is not yet claimed because Arch package repositories are
rolling and the local pacman trust database is generated during staging.

The recovery side also has a strict offline manifest adapter for the consumed
persistent-root P2 artifacts. It verifies their tracked sizes and hashes,
delegates canonical signing/publication to the stable runtime-bundle
packager, and requires either a consumed parity fixture or an offline
network-root candidate plus `authority=none`.

The active root is now packaged as a separately transported, sealed
`network-root-v1` lower. Two complete rootless builds produced the same
535,094,061-byte pax-restricted archive with SHA-256
`ee310c82ef925c9a801c310ab36f56f94b124ceb089d8db745c0959493c52b24`.
Its 37,669-entry tree, persistent seal, and explicit `workload=none` command
manifest are bound into the tracked `headless-network-root-v1` candidate.
The new 5,978,369-byte target initramfs includes the exact static AArch64
whole-tree verifier and also reproduces byte-for-byte.

The first signed live target exposed exact network-root NCM, then returned to
fallback before SSH because the candidate carried historical DTB v1. The
candidate now pins the accepted v3 GPU/RMTFS-isolated DTB
`86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`.
The corrected target, signed bundle, shell-free recovery, vendor wrapper, raw
boot image, and unsigned AVB test wrapper now reproduce in two clean offline
builds. The disposable test private key was destroyed. This correction
remains `authority=none` and grants no repeat authority.

An ephemeral-key signed v2 bundle passes the real native verifier with
manifest SHA-256
`70136ad498fad21bce5279f60cbad36359c7d6df6eb42280591071c5e1389bf6`.
The real consumed P2 fixture also passes one complete offline
prepare/serve/fetch/verify/descriptor-load/execute composition through the
framed responder; a changed signature never reaches load. That earlier
offline checkpoint added no production key or live authority. See the
[root checkpoint](../test-results/2026-07-29-headless-root-candidate-offline.md)
and
[runtime integration result](../test-results/2026-07-29-headless-runtime-integration-offline.md),
plus the
[live rejection](../test-results/2026-07-29-headless-stable-recovery-live.md)
and
[corrected twin build](../test-results/2026-07-29-corrected-headless-candidate-offline.md).

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

Before any wider GPU candidate runs, the repository now has one unified A660
acceptance harness and a minimal Vulkan queue-submit helper. Offline fault
tests cover exact mainline-render identity, KGSL rejection, rollback-versus-
soak separation, software-renderer rejection, boot-time and new
fatal-kernel-signature detection, finite Wayland frame completion, lightweight
continuous physical-darkness sampling plus bounded DPMS checks, private
evidence metadata, independent full Plasma PSS inventory, malformed telemetry,
watchdog/KWin PID reuse, signed and
sealed command execution, delegated-cgroup cleanup of `setsid` descendants,
before/after full-root verification, and atomic helper publication. A
test-only Vulkan implementation covers success, missing or
duplicate A660, missing queue, submit failure, and fence timeout.

The bounded staging mode requires target-visible signed 600/900-second timing,
enforces its own 540-second deadline, and rechecks storage isolation. The
network-root init now atomically attests the watchdog, its live timer child,
deadline, and timeout; the harness pins those identities, executable and
write-capable reset/log descriptors. It also records stable mount IDs before
moving the OverlayFS, authenticated lower, and tmpfs state; the harness
rejects a pathname-correct decoy mount. The 30-minute soak requires an
independently promoted persistent root with an exact OverlayFS-to-sealed-ext4
mapping, bounded tmpfs state, exact bundle/kernel/subtree/tree/seal identities,
an exact read-only verification mount, and a successful tree recomputation
before workload.

The incompatible signed bundle v2 format now emits target timeout,
command-manifest identity, and the complete `arch-a` lower-tree identity;
v2 components reject the older unsigned-root v1 schema. A static AArch64
verifier is now required inside the signed network-root initramfs and
authenticates the lower before OverlayFS or distribution userspace starts.
The canonical command manifest, static cgroup executor, static root verifier,
Vulkan submit helper, and unified acceptance harness are now installed in two
offline, versioned, read-only roots. One derives from successor-v3 and one
preserves the accepted v10 GPU ancestry before adding the runtime surface.
Both identities bind the exact base verifier, base seal, pre-integration base
tree, runtime provenance, commands, tools, complete tree, and persistent seal.
Their builders require the external approved runtime-tools manifest hash,
compare every pre-existing entry against a private read-only base snapshot,
permit only the fixed runtime additions, independently verify the final tree
with a static AArch64 binary, and publish the root plus identity together
through one atomic no-replace directory rename.

This is a sealed-root milestone, not a signed-bundle or live-acceptance
milestone. Promoted-root device identity, signed bundle packaging, the host
server profile, and the versioned recovery rebuild remain pending. No
installed recovery, trust root, or phone state changed. Neither acceptance
mode has run on the phone. See the
[offline runtime-root evidence](../test-results/2026-07-28-a660-runtime-root-offline.md).
See [A660 accelerated-desktop acceptance](a660-acceptance.md).

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

1. Obtain explicit approval before creating or using a live recovery signing
   trust root or temporarily booting the corrected candidate.
2. Promote the stable recovery through staging-only tests and determine
   whether ramoops survives the target/fallback path.
3. Bring up the headless core in order: boot/storage/USB/SSH, power/charging/
   thermal/suspend, input/sensors, then audio and wireless.

GPU, display, desktop, hotspot, and automation work is frozen until the
headless reliability gate. No new phone action is authorized by this document.

## Operational constraints

- Credentials and private identifiers stay outside Git.
- `artifacts/`, `build/`, and `dist/` are ignored and are not covered by the
  Git archive tag.
- The accepted pre-reduction tracked state is recoverable at
  `archive/pre-stable-recovery-2026-07-28`.
- Linux v7.1.4 now has an exact tag-object/commit/tree source contract and a
  twice-reproduced rootless x86_64 builder with pinned base images, Ubuntu
  snapshot, complete package closure, and offline verification.
- Android packaging dependencies such as `mkbootimg` and `avbtool.py` still
  need an explicit pinned bootstrap path for fresh-clone reproducibility.
- The headless root records its exact package inventory, but its rolling Arch
  package snapshot and generated pacman trust database are not yet
  byte-reproducible inputs.
- Fastboot remains boot-only. The fallback slot and guarded
  `RESTART2("bootloader")` helper remain unchanged.
