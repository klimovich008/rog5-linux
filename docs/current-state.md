# Current-state evidence ledger — 2026-08-01

This long-form file preserves verified chronology and exact identities. For
day-to-day orientation, start with [active-context.md](active-context.md).
The ordered plan is in [ROADMAP.md](../ROADMAP.md), and the detailed recovery
design is in [recovery-control-plane.md](recovery-control-plane.md).

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

Recovery v18 remains the reusable staging image admitted by
`manifests/temporary-boot-images.tsv`. The policy now also admits the exact
single-use diagnostic production wrapper only after its connected preflight.
Recovery v18 has:

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
The current Linux host also revalidated the optional positive source/DTB leg,
matching configuration and retained module archive, buttons/indicator source
contract, and corrected-successor artifact gate in one
[accepted-baseline checkpoint](../test-results/2026-07-31-accepted-core-baseline-revalidation.md).
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
six active headless capability contracts, eight future capability states,
exact CI entries, and the kernel-build verifier invocation. A committed
golden config, the retained accepted 7.1 config, and 39 mutation/CLI tests
pass. The complete hardware-free repository CI tier passes.

This is an ancestry and regression result, not a new hardware result.
`phase=active` means current roadmap scope; only `candidate_status` describes
acceptance. Buttons and battery remain baseline diagnostics, display-off is
evidence-only, and suspend, sensors, and audio remain pending. The corrected
root is still `live-pending` with `authority=none`. See the
[offline result](../test-results/2026-07-29-core-compatibility-oracle-offline.md).

The future `battery-charging` capability now has a hardware-free sustained
observation gate. A read-only target collector emits one canonical
candidate/boot/source-bound phase record with 21 samples at 30-second
intervals. It requires the exact three SM8350 power supplies, mode-`0444`
telemetry and input-current-limit files, no charge-control thresholds, and no
Type-C control device. The host verifier rejects malformed or replaced
evidence and compares same-boot unplugged and USB records only when status and
median current distinguish the phases; it derives either driver sign
convention rather than assuming one. Eleven hostile test groups pass and
Claude's complete-source review returned `NO_BLOCKERS`. This is an offline
test contract, not a new phone result or charging-safety acceptance. See the
[contract](battery-telemetry-series.md) and
[offline result](../test-results/2026-07-31-headless-battery-series-offline.md).

The corrected target's next live observation is now specified independently
of the boot controller. One read-only target probe emits exactly 88 canonical
fields for the six active capabilities. A host verifier binds the record to
the current probe hash, a separately observed boot ID, the full compatibility
oracle, the corrected candidate's root identities, exact CPUs `0-7`, the
three EPSS CPUfreq policy groups and schedutil governor, accepted RAM/thermal
envelopes, exact OverlayFS/NFSv4.2/tmpfs mount IDs and backing paths, zero
block/SCSI/RPMB/UFS exposure, the exact ConfigFS NCM gadget and primary
high-speed UDC, an isolated no-default-route `/30`, one current USB-peer SSH
session, matching Ed25519 authorized/host-key identities, strict key-only SSH,
and the live 600-second rollback lease. Target, host, and mocked strict-SSH
runner tests pass offline.
The runner executes the probe once and cannot boot, sign, retry kexec, disarm,
or reboot. No credential was used and no phone was contacted. See the
[runtime contract](minimal-headless-runtime-acceptance.md) and
[CPU/RAM result](../test-results/2026-07-29-cpu-ram-topology-offline.md), plus
the
[storage-isolation result](../test-results/2026-07-29-storage-isolation-offline.md)
and
[USB/NCM/SSH result](../test-results/2026-07-30-usb-ncm-ssh-offline.md).

The compatibility gate now also checks the kernel source and generated board
DTB rather than stopping at Kconfig and artifact ancestry. The retained exact
Linux 7.1.4 tree passes 43 Kconfig, Makefile, OF-table, binding, and source
entry-point checks; the accepted corrected DTB passes 23 RAM-bank, CPU/EPSS,
UFS-isolation, USB2/NCM, PSCI, and TSENS topology checks. The expanded source
gate and cross-node thermal policy additionally pin both
TSENS critical IRQ routes through PDC/GIC, 12 CPU thermal zones with exact
trips and cooling maps, five PMIC alarms/zones, and the kernel default
critical-shutdown path. Disabled zones, rewired interrupts, duplicate or
out-of-range sensors, changed trips, and altered cooling targets fail.
A future source or
DTB can run in candidate mode, but a pass reports
`compatible-not-accepted` and cannot promote hardware state. See the
[source/DT contract](core-source-dtb-contract.md), the
[static thermal result](../test-results/2026-07-31-thermal-policy-static-oracle-offline.md),
and the
[CPU/RAM result](../test-results/2026-07-29-cpu-ram-topology-offline.md).

The accepted config still builds the PMIC alarm driver as a module and sets
the emergency-poweroff delay to zero. The oracle therefore keeps PMIC
critical enforcement and a bounded 10–30 second forced fallback as separate
future capabilities. No IRQ delivery, cooling response, PMIC registration,
or shutdown behavior is accepted by this offline result.

The first H4 input/indicator delta is now packaged without widening any other
hardware boundary. It pins the accepted source, config, LPG module archive,
and corrected DTB; adds power, volume-down, PM8350 GPIO6 volume-up, and only
PM8350C green LPG channel 2; and keeps the LED default-off. Exact semantic and
source/config/module hostile suites pass in both repository tiers. This is
offline readiness only: no physical key or LED behavior has been accepted.
See the [buttons/indicator contract](buttons-indicator.md) and
[offline result](../test-results/2026-07-30-buttons-indicator-offline.md).

The matching userspace path is now native and bounded. A reproducible
67,520-byte static AArch64 daemon validates the exact PMIC power input and
green LPG class/driver/DT identity before accepting events. Only a value-1
`KEY_POWER` produces brightness 31 for 180 ms; signals and failures restore
zero. Host and AArch64/QEMU hostile suites pass, and a successor headless-root
staging profile adds only this binary, its confined service, and one module
line. The existing SSH-only root is unchanged, and no successor live
behavior is accepted yet. The successor archive is now sealed at
535,163,814 bytes with SHA-256
`f52bd75f023ab6209a04f842881356e5a224e1e1845f1d5732ab71da7d36e66b`;
both staged and clean-extraction verification pass with the repository's
public test key. The archive stays outside Git, is unsigned and unbooted, and
does not grant live authority. See the
[native runtime contract](headless-key-indicator.md) and
[offline result](../test-results/2026-07-30-headless-key-indicator-offline.md).

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

Those independent gates now have one hardware-free-tested lifecycle
controller. It performs complete preflight before mutation, waits for the
one-transfer recovery bundle server to exit and clean its firewall state
before starting NFS, commits exactly once, pins the volatile target key,
captures one strict-SSH runtime record through a single connection (rather
than five independent SSH/SCP handshakes), keeps rollback armed, verifies exact
fallback and host cleanup, and only then resolves the durable intent. An
ambiguous COMMIT is looked up in the ledger and is never replayed. The NFS
exporter is also staged for a fixed root-owned installation rather than
privileged execution of a mutable repository script. This checkpoint has not
installed the changed host components, booted the phone, or used a
credential. See the
[one-shot lifecycle runbook](minimal-headless-live-cycle.md).

The protocol reference model and host write-ahead ledger pass 48 offline
fault, replay, parser, crash-consistency, and concurrency tests. A static
native responder now passes 56 pseudo-terminal, postmortem, and
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
responder invokes the helper first under a 190-second outer deadline and maps
permanent bundle-ID conflict or an exact bounded fetch-stage failure without
invoking verifier or kexec. The helper's 180-second deadline is nested below a
190-second responder fetch wait, one 260-second same-session host PREPARE
deadline that also covers verification and kexec load, and a 320-second
lifecycle wait that includes initial ACM stabilization. At that checkpoint
the three binaries passed offline initramfs integration, but no production
signing key had been created. The accepted v18 recovery still contained the
old interactive control shell. None of those offline checkpoints granted live
authority.

The fixed NFS host server also has an authenticated cancellation boundary.
It publishes a root-owned PID/start-time/caller/token record before lengthy
setup, validates and freezes the exact isolated process leader through a
pidfd, signals only that process group, and accepts a terminal zombie only
after the server removed its own state record. A real-host serve/cancel test
passed and left no listener, export, NFS worker, mount daemon, marker, mount,
temporary PolicyKit rule, or writable SteamOS root state.
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
That checkpoint created no production key, live bundle, allowlist change,
host-network mutation, or phone action.

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

Status correction, 2026-07-30: the old identities below remain historical
evidence. The replacement `headless-ssh-v2` recipe is now offline,
credential-clean, and key-bound. Two fresh roots from commit `9739abe` are
byte-identical at 536,750,378 bytes with SHA-256
`2abe8c533179da598c37939ff8ebb4667a243bd8140c2d497237e41fbea72e6a`.
The fixed v3 package is 536,747,283 bytes, seals 37,735 entries, and binds the
canonical Ed25519 fingerprint across the build record, authorized key, whole
tree, and package. It uses only the public fixture, is unbooted, and is not
deployment authority. The distinct `headless-ssh-network-root-v3` fixture
candidate now binds that exact tree and seal to the accepted corrected DTB.
Its twin signed bundles, shell-free recovery initramfses, clean ASUS wrapper
kernels, boot-v3 images, and test-only AVB images reproduce and pass the
native verifier; the disposable signing key was destroyed and authority
remains `none`. See the
[hardening report](../test-results/2026-07-30-headless-root-credential-reproducibility-hardening.md)
and
[key-bound package report](../test-results/2026-07-30-headless-ssh-v2-key-bound-package.md),
plus the
[candidate report](../test-results/2026-07-30-headless-ssh-v2-candidate-offline.md).

The lifecycle now has a separate deployment-key admission boundary. After
exact guards and a clean, synchronized repository checkpoint, but before
privilege or phone discovery, it derives the public half from the caller's
canonical private key through fixed `/usr/bin/ssh-keygen`. It requires one
non-fixture `headless-ssh-v2` package, corrected candidate, and runtime
manifest chain; binds their root identities and exact Image/DTB/initramfs
tuple; and emits only hashes, the public fingerprint, and `authority=none`.
Fourteen hostile verifier tests and seventeen lifecycle tests use disposable
keys only. No deployment credential or phone was used. See the
[admission report](../test-results/2026-07-31-headless-ssh-v2-key-admission-offline.md).

The admitted identities now continue through the host-only execution path.
The lifecycle passes the exact package hash to a fixed
`headless-ssh-deployment-v3` NFS profile, recovery COMMIT waits for a
root-owned canonical v2 handoff marker containing that profile, fixed export
root, fresh token, listener, and package hash, and runtime acceptance receives
the exact admitted candidate path and hash. The target probe accepts only the
historical or deployment candidate identifier. The host verifier requires an
external canonical read-only non-fixture candidate for deployment and never
falls back to the tracked historical record. Historical no-argument NFS,
marker, recovery-control, target-probe, and runtime-verifier paths remain
intact. See the
[profile-threading report](../test-results/2026-07-31-headless-ssh-v3-profile-threading-offline.md).

Status update, 2026-07-31: the authorized non-fixture deployment chain is now
built. The sealed root archive is 536,746,495 bytes with SHA-256
`4d120a4b3a10be098cea47ba8536969bbaa931b47b31cc37fc3474fea045b324`;
its manifest, candidate, signed runtime manifest, raw recovery trust root,
recovery initramfs, wrapper kernel, raw boot image, and AVB wrapper are bound
by the new `headless-ssh-deployment-v3` live-gate profile. Two clean complete
builds are byte-identical, AVB verification passes, and the real artifact
preflight succeeds without phone access. See the
[deployment-chain report](../test-results/2026-07-31-headless-ssh-deployment-chain-offline.md).

The consumed v3 manifest is now superseded by signed bundle
`headless-ssh-network-root-v3-r2`. Its guarded twin build from clean pushed
checkpoint `81d2736` is byte-identical, retains only the public trust key, and
passes the production artifact gate before fastboot discovery. The exact r2
manifest is `9ea27452…d630` and the recovery AVB image is `11feb00b…13c`.
Candidate and bundle identities are now distinct throughout key admission,
recovery control, lifecycle intent, and runtime verification. See the
[signed-r2 report](../test-results/2026-07-31-headless-ssh-successor-r2-signed-build.md).

The host publication boundary was first implemented and accepted offline.
Its unprivileged launcher requires a clean branch synchronized with its exact
`origin` peer, verifies root-owned installed components byte-for-byte, and
reruns deployment-key admission. Only the canonical archive path, package
path, and admitted package SHA-256 enter the fixed PolicyKit command; the
private key, candidate, and runtime manifest do not. The root-owned installer
copies the caller-owned archive into an anonymous root-owned snapshot, binds
those exact bytes to the package, rejects unsafe archive members and tracked
fixture identities, extracts into a private deterministic stage, verifies the
complete root, syncs files and directories bottom-up, and publishes only with
`renameat2(RENAME_NOREPLACE)`. Eleven hostile installer tests and eight
launcher tests pass, including in-place rewrite, pathname replacement, unsafe
links/devices/credentials, stale installed bytes, and publication races. That
original acceptance used no PolicyKit action, host installation, deployment
credential, or phone. The later real-host deployment is recorded below. See
the
[export-installer report](../test-results/2026-07-31-headless-ssh-v3-export-installer-offline.md).

The first minimal mainline userspace profile was built and verified offline.
It used an official signed Arch Linux ARM base plus the exact
`7.1.4-g7a5cef0db479` modules and only three requested additions: `attr`,
`diffutils`, and `openssh`.

The historical stage removed the generic Arch kernel, twelve
`linux-firmware*` packages
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
measurement. Package versions are recorded in the historical root. The
corrected stage does not contact an Arch repository or generate a Pacman
trust database; it requires every requested package to be present in the
exact manifest-pinned base archive and empties Pacman signing state before
verification.

The recovery side also has a strict offline manifest adapter for the consumed
persistent-root P2 artifacts. It verifies their tracked sizes and hashes,
delegates canonical signing/publication to the stable runtime-bundle
packager, and requires either a consumed parity fixture or an offline
network-root candidate plus `authority=none`.

The historical root was packaged as a separately transported, sealed
`network-root-v1` lower. Two complete rootless builds produced the same
535,094,061-byte pax-restricted archive with SHA-256
`ee310c82ef925c9a801c310ab36f56f94b124ceb089d8db745c0959493c52b24`.
Its 37,669-entry tree, persistent seal, and explicit `workload=none` command
manifest are bound into the tracked `headless-network-root-v1` candidate.
The new 5,978,369-byte target initramfs includes the exact static AArch64
whole-tree verifier and also reproduces byte-for-byte.

The five frozen Linux 7.1.4 `network-root-v1` kernel artifacts are now
recoverable from a fresh exact source checkout and the reconstructed
historical builder. The missing input was Git ref state: retaining a local
`refs/tags/v7.1.4` changes `scripts/setlocalversion` from
`7.1.4-g7a5cef0db479` to `7.1.4`, despite an identical commit, tree, and
config. Two independently fetched, network-disabled builds from the
deliberate no-local-tag checkout are byte-identical and match every frozen
size and SHA-256 identity. This is host-only reproducibility evidence, not a
hardware or boot result.

The pruned recovery dependency chain is also closed. Two retained P2
lineages reconstruct the successor-only v18r base; exact historical source
transitions then recover the accepted network-root v3 archive and the
5,978,369-byte headless target initramfs byte-for-byte. Recovery component
builders run through pinned private rootless ARM64 emulation, and immutable
AOSP Git blobs recover the accepted Android boot tools. A reproducible 12 KiB
boot-v3 metadata template replaces the missing 96 MiB historical template
for successor builds. The historical wrapper builder remains frozen, while a
separate successor starts from the accepted v18 output config. See the
[dependency-closure proof](../test-results/2026-07-30-headless-recovery-dependency-closure.md).

The first signed live target exposed exact network-root NCM, then returned to
fallback before SSH because the candidate carried historical DTB v1. The
candidate now pins the accepted v3 GPU/RMTFS-isolated DTB
`86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`.
The corrected target, signed bundle, shell-free recovery, vendor wrapper, raw
boot image, and unsigned AVB test wrapper now reproduce in two clean offline
builds. The disposable test private key was destroyed. This correction
remains `authority=none` and grants no repeat authority.

The reconstructed successor path independently repeats that complete gate
with the qualified post-migration builders, compact canonical template, and
accepted v18 output config. Its two ASUS wrapper Images, raw boot-v3 images,
and AVB images are byte-identical; the exact source seal is unchanged, AVB
verification passes, and no private key remains. See the
[successor offline report](../test-results/2026-07-30-corrected-headless-successor-offline.md).

The retained historical recovery successor still passes its exact production
stable-recovery artifact boundary without a connected phone, but the new
lifecycle deliberately accepts only `headless-ssh-deployment-v3`. That
deployment profile now pins the complete non-fixture wrapper, trust root,
manifest, and verifier chain. The root-owned NFS controller understands only
that exact profile and package identity at its fixed v3 path. The first real
export publication stopped safely before extraction because SteamOS's 230 MiB
`/var` could not hold the 1.53 GiB lower. The reviewed remediation is now
pushed and installed. The fixed
`/home/rog5-linux/exports/headless-ssh-network-root-v3` store contains the
atomically published 37,735-entry root; every ancestor below `/home` is
root-owned mode `0700`. Export ancestry, complete-tree identity, fixed NFS
host state, exact recovery artifacts, and one connected `lahaina` fastboot
device pass.

A normal reboot into installed Alpine did not consume the experimental boot.
The new deployment key is not among its two older authorized keys. The USB
serial health payload nevertheless proved the exact fallback kernel, BusyBox
init, `qcom,lahaina-mtp`, ext4 root, zero project modules, empty pstore and
fatal-signature result, 70 thermal zones with a 38,800 m°C maximum, and Python
availability. A later Alpine/BusyBox source audit showed that invoking that
payload through the legacy interactive shell may also have updated its
history file; the historical inspection is therefore not retained as a
zero-write proof. The phone remains on the healthy fallback. At that
checkpoint, strict fallback SSH was the sole pre-lifecycle blocker: the untouched tier
would have required one of the existing authorized private keys, while
appending the deployment public key would have required an explicit
safety-tier revision and separate bounded phone-write approval.
See the
[real-host deployment result](../test-results/2026-07-31-steamos-deployment-preflight-live.md).

Current implementation supersedes the client-key blocker without changing
fallback configuration or `authorized_keys`. A fixed USB ACM controller sends
one nonce-bound read-only Python health payload through the exact Alpine
serial interface. The fallback signs the canonical
kernel/init/compatible/root, module, pstore, dmesg, thermal, Python, and boot
identity record with its existing Ed25519 SSH host key; the host verifies it
against the private pin captured during the deployment preflight.
The controller binds the same physical USB port, uses exclusive raw serial
ownership and bounded output, and requires a second guard plus verified ACK
and same-boot recheck before its only mutating action,
`RESTART2("bootloader")`. It then requires one same-port `lahaina` fastboot
device. Alpine 3.24 enables BusyBox per-command history, and reads from its
writable `relatime` ext4 root may update inode access times. Every action
therefore requires a separate action-scoped storage-write guard. It has no
fallback client key, host-network, mount, explicit storage-write, flash,
erase, or retry path. The isolated/no-site Python loader is bounded below
Alpine's 2,048-byte BusyBox line-editor limit. The host now drains and bounds
echoed bytes during writes, labels every write stage and byte count, and sends
one atomic Ctrl-C/newline plus split-literal nonce marker before the larger
launcher. It sends bounded, hash-checked source chunks only after one
nonce-bound ready marker, and the phone rejects missing or partial delivery
under a fixed deadline.
Non-reboot actions return to the supervised interactive shell. The
lifecycle permits at most one fallback contact even if final host cleanup
later fails. Before boot, its host-only preflight validates the exact
allowed-signers pin, fixed tools, ModemManager state, wait and loader bounds,
and the recovery-anchor time budget without opening ACM. The anchor consumer
is directly bound to the real capture producer and rechecks wall-clock
freshness after ACM discovery. Nonce-bound phone errors retain their failure
class through the last serial read. The clean-host gate reads the root-owned
canonical NFS export table directly, avoiding the successful-but-diagnostic
unprivileged `exportfs -v` lock path while still rejecting any real entry.
The emergency ACM protocol remains covered, while the active fallback path
now uses strict SSH over exact USB-NCM. Forty-six transport tests and all
twenty-six lifecycle methods pass hardware-free. The host has a persistent
no-gateway `rog5-fallback-usb-ssh` profile at `169.254.77.1/30`, and the
dedicated client key has passed a live strict-SSH fallback health preflight.
The first complete cycle through this path fetched, prepared, and committed
the target, then safely rejected a stale target route-parser assumption. The
watchdog returned the same port to Alpine, NetworkManager restored the
profile automatically, strict SSH verified the signed fallback at 44.1
degrees C without opening ACM, and the durable intent resolved
`FALLBACK_RETURNED`. See the
[strict-SSH fallback result](../test-results/2026-07-31-minimal-headless-live-cycle-ssh-fallback.md).

The distinct r2 successor subsequently completed framed recovery transfer,
PREPARE, and one durable COMMIT. Linux 7.1 exposed the expected USB-NCM gadget
on the exact port but physically disconnected 23 seconds later, before target
SSH host-key acceptance. The watchdog returned Alpine on that port and one
fresh signed strict-SSH fallback proof resolved the intent
`FALLBACK_RETURNED`. The controller now bounds the observed final
NetworkManager/udev identity race with a continuously clean dwell and one
shared deadline; all other residue still fails immediately. r2 is consumed.
See the
[r2 target USB-loss result](../test-results/2026-08-01-minimal-headless-r2-target-usb-loss.md).

The first authorized live ACM preflight was rejected because the existing
device-side reader had wedged; exact USB reset and host rebind could not
restore it. A physical reboot returned the exact fallback through fastboot and
restored its supervised ACM reader. The next signed exchange isolated a stale
exact-70-zone thermal predicate: the fallback now exposes 96 contiguous zones
with unavailable auxiliary modem/board channels but healthy core telemetry.
The collector now requires 70 through 128 contiguous zones, at least 29
stable positive readings, six named CPU/GPU/system sensor classes, and the
unchanged temperature ceilings. It ignores unreadable values only for the
exact observed auxiliary-type allowlist, plus zero and Qualcomm-inactive
values. Thirty-nine protocol tests pass, and a
fresh signed live preflight now passes with its no-replace mode-`0600` proof
retained outside Git. No experimental boot, flash, mount, fallback
configuration change, or client-key admission occurred. See the
[live acceptance](../test-results/2026-07-31-fallback-acm-preflight-live-accepted.md)
and preceding
[reader rejection](../test-results/2026-07-31-fallback-acm-preflight-live-rejected.md).
The private lifecycle record retains the verified nonce, physical USB
location, thermal maximum, and SHA-256 identities of the signed record,
signature, and inspected host-key pin, without retaining any private key.
The
`corrected-headless-successor-2026-07-30` profile binds its wrapper, raw image,
initramfs, signed bundle, accepted DTB, public trust root, verifiers, responder,
fetcher, wrapper configuration, AVB tool, unpacker, and qualified `cpio`.
`artifact-preflight` exits before fastboot discovery, and the one-shot
lifecycle rejects the consumed historical profile before credential paths.
See the
[live-gate admission report](../test-results/2026-07-30-corrected-successor-live-gate-admission.md).

The accepted stable-recovery wrapper now also has a fail-closed,
content-addressed cache path. A portable seal binds all 79,030 ASUS source
entries by path, type, mode, file content, and symlink target while excluding
host ownership and timestamps. Publication still requires the complete twin
kernel/raw/AVB gate and equal pre/post source seals. Materialization requires
the exact input key and caller-supplied entry ID, rehashes every cached file,
and never compiles or contacts the phone. The first 208 MiB entry reconstructs
the accepted corrected-headless wrapper in 3.10 seconds. It contains only the
historical public trust root; the disposable private key was destroyed, so
the cache is neither signing authority nor live authority. See the
[cache contract](recovery-wrapper-cache.md) and
[offline proof](../test-results/2026-07-30-stable-recovery-wrapper-cache.md).

The cached broad wrapper now has a separate configuration-slimming
experiment. A fail-closed policy, seven hostile mutations, and one positive
test preserve the
boot/CPU/RAM, UFS, gadget-only USB ACM/NCM, kexec, pstore, thermal, charging,
reboot, and PMIC power-key boundary while removing 601 built-ins and 655
active options. Two source-sealed clean builds produced the same
34,787,840-byte Image, 31.11% smaller than the accepted cached Image. Two
boot-header-v3/unsigned-AVB repacks also match and recover the exact kernel
and stable-recovery initramfs. Vendor HID and minimal V4L2 cores remain only
because ASUS Makefiles compile dependent accessory/video objects
unconditionally. The result is unbooted, `status=experiment`, and
`authority=none`; it neither changes the accepted cache nor grants live
authority. See the
[slimming contract](stable-wrapper-config-slimming.md) and
[offline proof](../test-results/2026-07-30-stable-wrapper-config-slimming-offline.md).

The historical native-indicator successor has a separate, non-sparse source
encoding and a v2 host package contract. Its 534,347,412-byte sealed archive
binds `build_profile=headless-core-v2`, 37,675 entries, the exact no-workload
command manifest, and the persistent seal while continuing to use the
accepted `network-root-v1` boot protocol. Normalization preserves the exact
source member set, hard-link topology, and inode flags before any verifier
mountpoints are created. The tracked
`headless-core-network-root-v2` candidate selects the 103,554-byte
buttons/default-off status-LED DTB. A full hardware-free gate reproduced two
signed bundles, stable-recovery initramfses, ASUS wrapper kernels, raw images,
and test-only AVB images under one disposable trust root; the private key was
destroyed and authority remains `none`. See the
[headless-core candidate result](../test-results/2026-07-30-headless-core-candidate-offline.md).

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

1. The external `headless-netroot-early-diag-v1` successor is production
   signed and twin-built. Its exact diagnostic wrapper, public trust root,
   manifest, verifier, and configuration tuple passes the artifact gate while
   every historical r2 pin remains unchanged. Independent review and local CI
   pass; publication, GitHub CI, and host-side installation still precede
   phone contact.
2. After installation and the connected preflight gate pass, use the
   same standing authorization for the successor's sole temporary boot,
   collect its receive-only early-target diagnostic stream, and prove normal
   fallback and cleanup. Consume the successor regardless of result.
3. Use that evidence to repair or promote a distinct normal minimal-headless
   candidate; then determine whether ramoops survives the target/fallback path
   and collect the exact 88-field core record over strict SSH.
4. Bring up the headless core in order: boot/storage/USB/SSH, power/charging/
   thermal/suspend, input/sensors, then audio and wireless.

GPU, display, desktop, hotspot, and automation work is frozen until the
headless reliability gate. Phone actions use the central standing
authorization and still must pass the lifecycle runbook's exact technical
gates; this status section does not relax them.

## Operational constraints

- Credentials and private identifiers stay outside Git.
- `artifacts/`, `build/`, and `dist/` are ignored and are not covered by the
  Git archive tag.
- The accepted pre-reduction tracked state is recoverable at
  `archive/pre-stable-recovery-2026-07-28`.
- Linux v7.1.4 now has an exact tag-object/commit/tree/source-ref contract and
  a twice-reproduced rootless x86_64 builder with pinned base images, Ubuntu
  snapshot, complete package closure, and offline verification. The frozen
  network-root build specifically requires the shallow `rog5-build`
  `FETCH_HEAD` state with no local `refs/tags/v7.1.4`.
- Android packaging dependencies now have an immutable AOSP Git-blob
  bootstrap with exact accepted byte identities, including the historical
  CRLF normalization. The compact canonical boot-v3 metadata template is
  independently reproducible and replaces the missing 96 MiB historical
  template for successor builds.
- The corrected headless stage is network-disabled, consumes only the exact
  manifest-pinned Arch base and modules, rejects embedded Pacman secret or
  revocation state, normalizes timestamps, and emits a sorted archive.
  The `headless-ssh-v2` source and v3 fixture package/candidate are
  byte-reproducible; the non-fixture deployment package and live-candidate
  identities remain pending.
- Fastboot remains boot-only. The fallback slot and guarded
  `RESTART2("bootloader")` helper remain unchanged.
