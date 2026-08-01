# Test plan

> Historical detailed plan. It preserves accepted and rejected tier
> contracts, but it grants no current live authority. Do not run its legacy
> ACM/kexec steps. Current work is the offline
> [framed recovery control plane](recovery-control-plane.md).

Tests are ordered so a failure never hides whether the phone can be recovered. A tier is attempted only after every mandatory test in the previous tier passes.

The canonical Linux `quick` tier is a provisioned security/integration tier.
It requires GCC, `dtc`, OpenSSL development files, `pkg-config` Vulkan
headers/loader metadata, and a writable delegated non-root cgroup v2 exposing
`cgroup.kill`. These are mandatory because the tier compiles the real C
helpers, executes the Vulkan fault matrix, and proves descendant cleanup.

## Tier 0 — static build checks

- Kernel source revision is pinned and recorded.
- Board DTS compiles with `dtbs_check` warnings reviewed.
- Configuration fragment contains only real symbols.
- `Image`, DTB, modules, initramfs, and boot image hashes are recorded.
- The stable-wrapper slim-config path binds the accepted config, reviewed
  fragment/profile, complete portable ASUS source seal, builder image, and
  stable-recovery initramfs. Seven hostile mutations plus one positive
  auditor test and separate host and device contracts reject identity,
  authority, requirement, reduction, module-promotion, canonical-input,
  symlink, transport, and reproducibility regressions. Each negative test
  asserts the exact policy error. A
  release proof requires two clean byte-identical configs/Images/metadata and
  independent Android boot-v3/unsigned-AVB repacks whose unpacked kernel and
  ramdisk match exactly. This compile-only gate grants no phone authority.
- The first recovery candidate is `acm-only` and contains no
  `authorized_keys`, credentials, or host-specific SSH private keys.
- Build logs contain no errors and are retained outside Git if large.
- `verify-mainline-build.sh` validates the pinned Python hash seed, raw and
  compressed Images, artifact hashes, final boot/BTF config, and parseability
  of every comparison DTB.
- `compare-mainline-builds.sh` rejects the same directory through aliases and
  requires byte-identical configuration, raw and compressed kernels, module
  archive, metadata, and all reviewed DTBs from two fresh output directories.
- `verify-kexec-recovery-stage.sh` requires an explicit `acm-only` or `ssh`
  access mode and a separately recorded artifact SHA-256 manifest, then
  validates the staging kernel config, recovery DTB allowlist, both initramfs
  layers, nested payload hashes, boot header, AVB footer, and access material.
- The base board-DTB check requires the TLMM 52-59 reservation and all eight translated ASUS HS-PHY tuning properties.
- The recovery DTB check requires USB2 high-speed operation, a built-in FEMTO PHY, exactly one USB PHY reference, and disabled UFS, QMP/SuperSpeed, and secondary USB.
- The core source/DTB contract requires a clean Git source root, 43
  Kconfig/Makefile/OF/binding/source checks, and 23 corrected-DTB topology
  checks across all six active minimal-headless capabilities. OF tables must
  be attached to registered drivers; enabled DT paths must have enabled
  ancestors, mandatory PHY cells, and exact phandle relationships. A global
  compatible scan rejects alternate enabled UFS/QMP USB3 nodes. Candidate
  mode is compatibility evidence only and must never report hardware
  acceptance.
- Its static thermal policy separately pins both TSENS critical IRQs through
  the PDC/GIC chain, exact source critical-shutdown calls, 12 CPU zones with
  trips and cooling maps, and five PMIC alarm/zone pairs. All required source
  literals and hostile DT rewires are mutation-tested. The accepted
  `qcom-spmi-temp-alarm` module and zero emergency delay do not satisfy the
  future built-in PMIC and bounded forced-fallback gates.
- `build-gpu-recovery-initramfs.sh` preserves the recovery init, adds exactly the three hash-pinned A660 payloads, and reproduces the same archive byte-for-byte.
- `verify-staged-arch-rootfs.sh` checks the requested packages, modules,
  firmware, locked accounts, key-only SSH, NetworkManager ownership,
  headless/no-autologin default, on-demand ttyd/Chromium, Plasma/KRDP tools,
  and absence of baked network or remote-desktop credentials. It also requires
  the separate locked `rog5-agent` identity, exact mode-`0700` empty state
  directories, no SSH or supplementary groups, a loopback-only service that
  does not reuse `rog5`, exact CPU/memory/swap/task/I/O/restart controls, and a
  successful in-rootfs `systemd-analyze verify`.
- `test-collect-baseline.sh` runs the staged runtime collector against a
  synthetic proc/sys/systemd fixture; requires memory, CPU, Plasma PSS,
  automation cgroup, battery, thermal, display, target, inhibitor, DRM, and
  interface-counter fields; and rejects address, MAC, SSID, serial, or kernel
  command-line sources.
- `test-collect-component-pss.sh` fixture-tests the separate read-only
  component collector for desktop, browser, remote-transport, and total
  process counts/PSS. It fails closed to `unavailable` when a selected
  process lacks readable PSS, rejects relative fixture roots, and forbids
  process arguments, environments, descriptors, network identities, and
  credentials. The full Linux-rootfs tool aggregate delegates this test.
- `test-capture-vendor-kernel-log.sh` requires the fallback capture to use
  strict pinned SSH, mode-`0600` ignored storage, atomic no-overwrite
  publication, complete framing, the exact vendor identity, and a real
  time-zero boot origin. It rejects SSH failure, malformed or late rings,
  outside paths, partial artifacts, and remote mutation commands. The
  [live HOLD](../test-results/2026-07-27-alpine-vendor-kernel-boot-log-hold.md)
  records why the current ring cannot close the boot-log gate.
- `test-inspect-persistent-layout.sh` fixture-tests the read-only,
  no-repartition storage preflight. It pins the measured primary/boot LUN,
  `super`, `metadata`, `userdata`, boot A/B, vendor-boot A/B, and vbmeta A/B
  identities; requires the marked ext4 `userdata` fallback root, a valid
  protected slot, unmounted boot-critical partitions, and at least 16 GiB
  free; and rejects eight map/state mutations. The
  [live result](../test-results/2026-07-27-persistent-layout-preflight-live.md)
  authorizes design work only and no phone write.
- `test-stage-persistent-arch-root.sh` fail-first tests the P1 root stager and
  canonical tree sealer. It rejects an absent arm, wrong archive identity,
  parent traversal, device nodes, embedded deployment credentials, Pacman
  private-key directories and revocation state, a forged reserved seal,
  existing final roots, and stale partial roots; preserves
  mode and xattrs; detects a changed seal mode or published file; and proves
  interrupted extraction exposes no final root before atomic rename. The
  separate real-archive check accepts 181,242 path-safe entries. The
  [offline result](../test-results/2026-07-27-persistent-arch-staging-offline.md)
  changes no persistent phone state.
- `test-arch-headless-rootfs-contract.sh` requires the minimal root stage to
  use only the manifest-pinned base packages, disable networking, avoid
  Pacman sync/update/key initialization and mutable caches, empty Pacman
  signing state, normalize output mtimes, sort archive members, and disable
  sparse-file reads. Release admission additionally requires two fresh
  byte-identical full builds; source-contract tests alone are insufficient.
- `test-collect-vendor-wifi-contract.py` fixture-tests the read-only vendor
  CNSS/PCIe collector. It requires one unambiguous QCA6490 node and matching
  root complex, exact supplies/GPIOs/pinctrl and PCI endpoint identity,
  deterministic output, and `HOLD` status for unresolved providers. It
  rejects relative roots, duplicate CNSS nodes, malformed properties, and
  mutation-capable implementation surfaces. The
  [live contract report](../test-results/2026-07-27-arch-wifi-vendor-contract-hold.md)
  records the exact endpoint and remaining stale regulator phandle without
  activating the radio.
- `test-wifi-candidate-dtb.sh` requires the isolated WCN6855 PMU host/output
  rail graph, PCI `17cb:1103` endpoint, PCIe0/QMP PHY and GPIO contract,
  immutable accepted network-root v8 base, deterministic merge, and rejection
  of incomplete rails or invented calibration/link-speed properties.
- `test-validate-wifi-candidate-dtb.sh` pins dtschema `2026.6`, clean Linux
  commit `7a5cef0db479`, a network-disabled validator, two identical merged
  DTBs, and the WCN6855, ath11k PCI, PCIe0, QMP PHY, RPMh-regulator, and TLMM
  schemas.
- `test-mainline-wifi-build-contract.sh` requires the QMP PCIe PHY, PCI power
  control, WCN sequencing, MHI, and ath11k symbols/modules and aliases. With
  two distinct build directories supplied, it verifies both and requires
  byte-identical `.config`, `Image`, `Image.gz`, module archive, and metadata.
  The
  [offline acceptance](../test-results/2026-07-27-wcn6855-pcie-offline.md)
  records the accepted hashes; no boot or radio action is implied.
- `test-wifi-root-overlay-contract.sh` and
  `verify-wifi-root-overlay.sh` require the exact successor-v3 root and Wi-Fi
  module tree, inherited pinned WCN6855 firmware, default module blacklist,
  unmanaged `wlan0`, no connection/provider credentials, deterministic
  output, and rejection of module, seal, mode, and credential-path mutations.
- `test-wifi-network-root-bundle-contract.sh`,
  `verify-network-root-wifi-bundle.sh`, and
  `compare-network-root-wifi-bundles.sh` pin every predecessor and tool,
  require UFS-disabled storage-free packaging, reconstruct the nested stage,
  verify header-v3/AVB structure, and require two complete packages to match
  byte-for-byte.
- `test-network-root-wifi-bundle.sh` accepts the exact pristine package, then
  refreshes the candidate manifest after separate DTB, root-overlay, and raw
  boot-image mutations and requires every case to fail.
- `test-probe-network-root-wifi.sh` and
  `test-run-network-root-wifi-gate.sh` statically require explicit guards,
  exact storage/NFS/kernel identity, a one-attempt enumeration-only probe,
  independent watchdog handoff, one immediate reboot, no retry, no scan,
  association, AP, Bluetooth, credentials, unload, phone, or host-network
  action. The
  [offline package result](../test-results/2026-07-27-wcn6855-runtime-package-offline.md)
  passes all gates and remains `UNBOOTED_HOLD`.
- `test-screen-toggle.sh` exercises idempotent display state.
  `test-vpn-hotspot.sh` checks service/rule contracts and sends IPv4/IPv6
  packets through isolated AP, VPN, and ordinary-uplink namespaces; it
  defaults to successor v2 and requires VPN-only UDP/TCP DNS, one-way
  ordinary-uplink leak detection, unsolicited-client isolation, fail-close
  after VPN-interface loss, recovery after recreation, and exact cleanup.
- `test-vpn-hotspot-wireguard-contract.sh` pins the separate
  `test-vpn-hotspot-wireguard.sh` to a network-disabled TEST-NET underlay,
  mode-`0600` disposable keys, the v2 production kill switch, valid UDP/TCP
  DNS framing, a real kernel WireGuard handshake, endpoint loss/recovery,
  increasing encrypted transfer counters, and exact teardown. Run both only
  in privileged network-disabled builder containers. The
  [offline result](../test-results/2026-07-27-vpn-hotspot-v2-dns-recovery-offline.md)
  records the current hashes and mutation evidence.
- `test-vpn-hotspot-systemd-order.sh` rejects the Arch
  dnsmasq/network-online ordering cycle and requires the complete staged-root
  verifier to run `systemd-analyze verify` on the hotspot unit.
- `test-load-mainline-recovery.sh` rejects non-Haven watchdog controls and rollback timeouts outside 30-900 seconds before loading kexec.
- `verify-ufs-discovery-patch.sh` applies the three-patch discovery series to
  the pinned tree, enforces exact query/SCSI whitelists, rejects
  data-to-device and bidirectional payloads, proves discovery returns before
  runtime-PM/BKOPS and shutdown transitions, and compiles the guarded
  SCSI/UFS objects.
- `verify-ufs-discovery-bundle.sh` requires exactly thirteen manifest-pinned
  products, rebuilds the reviewed UFS/USB2 DTB, verifies both nested
  credential-free initramfs layers, and checks the wrapper, boot header,
  command line, and AVB footer.
- `verify-network-root-bundle.sh` requires exactly fourteen manifest-pinned
  products, delegates the dedicated kernel and target-initramfs checks,
  rejects an enabled UFS path or UFS module, verifies both credential-free
  initramfs layers and nested hashes, and checks the wrapper, boot header,
  command line, and AVB footer.
- `test-linux-rootfs-tools.sh` checks the pinned signed-Arch input path,
  metadata-preserving rootfs stage path, exact network-root module input, and
  absence of broad container privilege or phone-write commands. It also
  delegates the exact persistent-layout fixture so a rootfs release cannot
  silently assume a disposable Android partition. It also
  delegates the static v2 real-WireGuard hotspot contract so the aggregate
  rootfs gate cannot silently fall back to the superseded v1 control. It
  delegates
  `test-arch-successor-export.sh`, which requires one exact successor
  manifest identity, read-only Btrfs preparation, a recursive
  content/metadata/ACL/xattr seal, isolated agent and service identities,
  no v10 dependency, an explicit-token verifier-first NFS case, and optional
  COW mutation rejection. It also delegates the successor target and host
  runner tests, which require first-boot/coldplug/sysusers/tmpfiles checks,
  headless screen-off state, exact two-file tmpfs staging, strict SSH, one
  reboot, a private log, and no retry or boot command.
  The
  [offline protected-export result](../test-results/2026-07-27-arch-successor-protected-export-offline.md)
  records the exact accepted root and three rejected mutation cases; the
  [pre-live HOLD](../test-results/2026-07-27-arch-successor-v1-prelive-hold.md)
  records the fail-first controls and actual unarmed refusal.
- `test-arch-successor-v2-archive-contract.sh` pins the newer archive, rejects
  unsafe paths and embedded runtime credentials, and compares both installed
  hotspot files byte-for-byte with the reviewed v2 sources.
  `test-arch-successor-v2-export.sh` then requires an exact, v1-independent,
  root-owned read-only Btrfs export and optionally rejects COW mutations to
  the seal, hotspot control, hotspot service, and account database. The
  [v2 rootfs result](../test-results/2026-07-27-arch-successor-v2-rootfs-offline.md)
  and
  [v2 protected-export result](../test-results/2026-07-27-arch-successor-v2-protected-export-offline.md)
  remain offline HOLD and add no NFS or boot authority.
- `test-serve-arch-successor-v2-live-window.sh`,
  `test-run-network-root-arch-successor-v2-gate.sh`, and
  `test-run-arch-successor-v2-live-gate.sh` require a separate exact-root
  token and verifier-first server, headless screen-off/storage-free target,
  exact two-file tmpfs staging, strict SSH, private logging, one reboot, and
  no retry. The
  [v2 pre-live HOLD](../test-results/2026-07-27-arch-successor-v2-prelive-hold.md)
  records their fail-first commits and the actual unarmed zero-state check.
- `test-power-buttond.sh` feeds native AArch64 input records to the
  standard-library handler and requires press-only toggling, truncated-record
  and failed-toggle rejection, and a parsed device-confined systemd unit.
  `test-arch-successor-v3-power-button-contract.sh` layers it over the
  byte-exact v2 verifier, while
  `test-arch-successor-v3-archive-contract.sh` pins the clean archive and
  rejects unsafe paths or embedded host, VPN, desktop, and agent credentials.
  `test-arch-successor-v3-export.sh` then requires a separate recursively
  sealed read-only Btrfs root and rejects seal, power-handler, power-service,
  and account mutations. The v3 NFS, target, and runner tests require a
  verifier-first exact-root token, exact seal/archive identities, one real
  `pmic_pwrkey` character device, active zero-restart handler service, strict
  SSH, one reboot, and no retry. See the
  [v3 offline result](../test-results/2026-07-27-arch-successor-v3-power-button-offline.md)
  and
  [protected pre-live HOLD](../test-results/2026-07-27-arch-successor-v3-protected-prelive-hold.md).
- `test-arch-headless-rootfs-contract.sh` pins the three-package SSH-only
  profile, public-key validation, firmware-free host path, strict SSH,
  volatile identities, multi-user/sleep-inhibitor services, disabled network
  managers, and the absence of desktop/browser/GPU/radio/agent and phone-write
  surfaces. The real ARM64 stage runs the same complete verifier before
  archival and after clean extraction.
- `test-collect-minimal-headless-runtime.sh`,
  `test-verify-minimal-headless-runtime.py`, and
  `test-run-minimal-headless-runtime-acceptance.sh` define the next corrected
  target result without granting live authority. They require one canonical
  88-field observation covering the six active compatibility capabilities,
  bind it to the exact probe/boot/candidate/root/watchdog identities and
  device-specific CPU/RAM/thermal envelopes, exact attested storage mount
  identities and OverlayFS backing paths, NFSv4.2/TCP, and zero
  block/SCSI/RPMB/UFS exposure. They also require the exact ConfigFS
  descriptor/function/UDC, high-speed `usb0`, isolated connected route with no
  default, one current USB-peer SSH session, and matching Ed25519 key
  identities; reject target and record mutations; and prove one strict-SSH
  connection streams, verifies, and executes the exact probe before one
  private capture, with no established-session replay, boot, signing, disarm,
  or reboot action. The
  historical no-argument path remains fixed, while deployment requires an
  external canonical read-only non-fixture v3 candidate plus its exact
  admitted hash and cannot fall back to the historical candidate. See
  the
  [runtime result](../test-results/2026-07-29-minimal-headless-runtime-acceptance-offline.md)
  and
  [storage-isolation result](../test-results/2026-07-29-storage-isolation-offline.md),
  plus the
  [USB/NCM/SSH result](../test-results/2026-07-30-usb-ncm-ssh-offline.md).
- `test-pin-minimal-headless-host-key.py` covers the credential-free bridge
  between signed recovery and strict target SSH. It fixture-tests canonical
  private anchors, host-boot and 600-second freshness binding, exact
  recovery/target products, same-port USB continuity, `cdc_ncm`, one direct
  `/30` route, one nonzero Ed25519 wire key, atomic mode-`0600` publication,
  and pre-inspection authorization. It rejects duplicate gadgets, another
  port, wrong driver, stale or malformed anchors, routed peers, absent,
  multiple, RSA, zero, or extended keys, repository/symlink/loose-parent
  outputs, and an enumerated set of client-credential and TOFU command
  surfaces. See the
  [bootstrap result](../test-results/2026-07-29-minimal-headless-host-key-bootstrap-offline.md).
- `test-run-minimal-headless-live-cycle.py` composes the corrected boot-only
  recovery, fixed one-transfer bundle server, fixed read-only NFS exporter,
  durable intent ledger, USB-continuity host-key pin, one strict-SSH runtime
  observation, watchdog rollback, exact signed strict-SSH fallback proof, and
  host cleanup.
  Twenty-six process test methods now also prove exact key guards fail first,
  `key-preflight` stops before phone/privilege actions, and deployment-key
  admission precedes connected preflight. The same admission record now binds
  the fixed NFS profile/package marker, recovery-control rendezvous, target
  candidate identity, and runtime-verifier candidate path/hash. They prove
  bundle cleanup precedes
  NFS startup, COMMIT is never retried, transport loss is recovered only
  through the durable ledger, runtime rejection resolves as
  `FALLBACK_RETURNED`, accepted runtime resolves only after exact fallback and
  cleanup, and missing fallback proof leaves the intent `UNKNOWN`. Injected
  protected-zone, temporary-address, NetworkManager-ownership, final-cleanup,
  and silent-post-ledger-arm failures cover the cleanup/oracle boundaries.
  They also cover transient and persistent udev gaps, an address-view race,
  clean/dirty flapping, immediate failure for non-identity residue, one shared
  cleanup deadline across subprocesses, and the invariant that stabilization
  cannot add a fallback contact or COMMIT attempt. The tests perform no phone,
  personal-credential, PolicyKit, firewall, or NFS action.
  See the
  [one-shot runbook](minimal-headless-live-cycle.md).
- `test-fallback-acm-control.py` covers the configuration-unchanged Alpine
  fallback control
  plane without a client SSH key or host networking. Thirty-eight
  hardware-free cases require one exact nonce-correlated frame, canonical
  health fields, real disposable Ed25519 signing and verification, the exact
  private host pin, exclusive/raw bounded ACM transport, exact USB
  product/interface and physical location, ACK-before-reboot, disconnect, and
  same-port `lahaina` fastboot. Echoes, truncation, duplicate
  frames/products/interfaces, key or payload mutations, loose guard ordering,
  missing/additional/unreadable thermal or pstore entries, unsafe 60 C
  preflight or 80 C return temperatures, occupied/malformed fastboot
  inventories, bounded serial read/write/ACK failures, echoed-write
  backpressure, unbounded drained output, malformed write stages, a too-short
  post-ACK COMMIT deadline, delayed post-ACK health collection, missing
  credential or action-scoped storage authority, and explicit
  write/flash/mount surfaces fail closed. Admitted fallback-storage
  effects are limited to separately authorized BusyBox history before the
  fixed launcher starts its child and possible read-induced ext4 atime
  updates. Non-reboot actions return to the existing supervised shell. The
  exact recovery-anchor fields and literal USB product are bound to the real
  capture producer; host-only fallback prerequisites and the 3,600-second
  contact-start/7,200-second anchor-age relationship are checked before boot.
  Wall-clock freshness is rechecked after ACM discovery to cover host suspend.
  Canonical nonce-bound remote error frames retain their failure class even on
  the final bounded read. The
  suite also executes the bounded two-phase loader, proves its
  shell line remains below Alpine's 2,048-byte editor limit, requires
  isolated/no-site Python startup, and prevents payload delivery before a
  nonce-bound ready marker. Missing and partial chunks expire without payload
  execution. The lifecycle suite also recovers a durable intent after
  zero-exit malformed control output and reserves a bounded post-discovery
  control margin.
- `test-verify-headless-ssh-v2-key-admission.py` has fourteen hostile,
  deployment-credential-free host scenarios around the boundary. It derives
  public halves only from disposable Ed25519 keys, accepts one exact
  non-fixture v3 package/candidate/runtime-manifest chain, and rejects the
  tracked fixture fingerprint, every tracked fixture root identity,
  key/package mismatch, package/candidate/manifest/artifact mutations,
  encrypted and RSA keys, unsafe parents, symlinks, hard links, replacement,
  record metadata changes, and non-fixed key derivation or live-transport
  surfaces. Canonical output contains only public fingerprints and hashes.
  See the
  [admission result](../test-results/2026-07-31-headless-ssh-v2-key-admission-offline.md).
- `test-install-headless-ssh-deployment-export.py` has thirteen offline
  root-installer fixtures. They cover exact package/archive binding, fixture
  and historical-package refusal, unsafe input metadata, escaping and
  credential paths, symlink ancestors, devices/FIFOs, caller pathname and
  in-place replacement after admission, bottom-up durability ordering, and a
  racing final destination. They also require fixed root-owned destination
  ancestry and a stable Python 3.13 caller-lookup refusal. Inspection and
  extraction consume only one anonymous private snapshot, and publication
  uses no-replace rename.
- `test-run-headless-ssh-deployment-export-install.py` has eight launcher
  fixtures. They prove guards and fixed installed bytes fail before private
  key admission, require a clean exact `origin` checkpoint, bind admission to
  the package and archive, and pass only the archive, package, and admitted
  package hash to PolicyKit. The private key, candidate, and manifest never
  enter the privileged command. See the
  [export-installer result](../test-results/2026-07-31-headless-ssh-v3-export-installer-offline.md).
- `test-prepare-recovery-candidate.py` exercises the offline candidate
  adapter with a disposable Ed25519 key, rejects live authority, unknown
  status, fields, and mutated artifacts, checks the tracked consumed-P2 and
  headless network-root identities, and statically excludes
  transport/server/phone actions.
- `test-headless-network-root.py` binds the explicit no-workload manifest,
  complete persistent seal, tree count/hash, source archive, and final sealed
  archive for the historical SSH-only package, `headless-core-v2`, and
  key-bound `headless-ssh-v2`/package-v3. It rejects tree, archive,
  command-manifest, profile, malformed or cross-version records, package/
  build/key fingerprint mismatches, options/comments, noncanonical Base64,
  SSH blob algorithm confusion, unsafe parent/`.ssh`/file metadata, hard
  links, v3-to-v2 downgrade attempts, and post-publication export-ancestry
  permission/symlink drift. The shell contract also requires the public
  fixture to satisfy its Ed25519 gate, pins the v2-only
  `AuthorizedKeysFile`, and requires ancestry re-attestation before bind plus
  package verification against the already bound tree.
- `test-compare-root-archives.py` rejects added paths, unsafe paths, hard-link
  topology changes, and inode-flag loss across a dense source re-encoding.
- `test-normalize-headless-core-archive-contract.sh` pins a hardware-free,
  twin-built dense re-encoding that rejects sparse archive members and proves
  exact source paths, hard links, inode flags, and extracted whole-tree
  identity are unchanged after canonicalizing only the extraction-volume root
  mtime. Compression and archive validation run inside the digest-pinned
  builder.
- `test-recovery-candidate-integration.py` composes the real packager,
  descriptor-oriented server, sandboxed fetcher, native verifier, and framed
  responder. Local artifact stores exercise the exact consumed P2 payload;
  clean clones use a tiny policy-valid fixture. Only kexec is replaced, and
  the fake verifies exact descriptor hashes plus load/execute/unload order.
- `test-corrected-headless-candidate-offline-contract.sh` pins the PC-only
  twin-build entry point, accepted v3-isolated DTB, snapshot builder, shared
  disposable public key, native verifier, and `authority=none`; it rejects
  phone, privilege, storage, and live-promotion transports. The full entry
  point rebuilds both target bundles, shell-free initramfs files, vendor
  wrapper kernels, raw images, and unsigned AVB test wrappers, then destroys
  the disposable private key.
- `test-corrected-successor-live-gate-offline.sh` submits the retained
  corrected successor to the exact production stable-recovery artifact
  profile. It pins the signed bundle, corrected DTB, trust root, initramfs
  components, boot-v3 image, ASUS wrapper, AVB descriptors, and qualified
  tools, then proves the artifact-only action exits before any fastboot device
  query. The lifecycle also rejects the consumed historical profile before
  inspecting credential paths.
- The optional accepted-input leg uses the clean retained Linux 7.1.4 source,
  exact accepted DTB, tracked v3 configuration, and an explicitly selected
  byte-identical retained module archive. The host keeps the existing v1
  archive instead of duplicating 300 MB into v3. See the
  [accepted-baseline revalidation](../test-results/2026-07-31-accepted-core-baseline-revalidation.md).
- `test-kernel-source-seal.py`,
  `test-stable-recovery-wrapper-cache.py`, and
  `test-stable-recovery-wrapper-cache-contract.sh` require a
  host-metadata-independent ASUS source identity, exact profile/tool/config/
  initramfs/builder inputs, equal pre/post source seals, byte-identical twin
  wrapper/raw/AVB outputs, immutable private cache entries, one output identity
  per input key, caller-pinned materialization, and atomic no-replace
  publication. They reject content, mode, symlink, source, profile, dependency,
  twin, manifest, inventory, cache-permission, input-binding, and destination
  mutations. The cache contains no phone, privilege, storage, process, or
  network transport.
- `test-headless-core-candidate-offline-contract.sh` layers the successor
  candidate ID, v2 package contract, buttons/default-off status-LED DTB, and
  distinct target ID over the same authority-free twin-build gate while
  excluding phone, privilege, and storage transports from both the wrapper
  and shared builder and rejecting malformed or co-varied candidate tuples.
- `test-core-compatibility-oracle.py` runs 33 positive, mutation, parser, and
  CLI cases over the ASUS 5.4/accepted 7.1 ancestry profile. It requires the
  committed golden Kconfig, checks the retained accepted config when locally
  available, and rejects evidence, manifest, candidate, capability, config,
  integration, JSON, path, and process-exit weakening. The kernel build
  verifier runs the same oracle against each completed `.config`.
- `recovery-linux.sh preflight` requires an explicit manifest-pinned image and
  exactly one fastboot target; no candidate is selected by default and `boot`
  remains inert unless `ALLOW_TEMPORARY_BOOT=1` is explicit. Recovery ACM
  detection requires exact normalized product `ROG5_recovery`; the fallback
  gadget sharing `1d6b:0104` is a hard failure.
- `test-recovery-fetch-native.py`, `test-recovery-fetch-root.sh`, and
  `test-recovery-fetch-aarch64.sh` exercise the fixed binary NCM acquisition
  helper as an ordinary host process, as root in a network-disabled
  container, and as a reproducible static AArch64 binary. They require the
  UID/GID-65534 chroot/seccomp worker, exact descriptor set, fixed peer
  contract, bounded canonical stream, independent parent revalidation,
  no-replace publication, conflict/quota policy, crash/ENOSPC containment,
  and parent-death cleanup. The responder reference/native/AArch64 suites
  additionally require exact fetch-before-verifier-before-loader ordering,
  immutable `FETCH_FAILED` and `BUNDLE_ID_CONFLICT` decisions, no verifier or
  kexec call after acquisition failure, nested helper-tree timeout cleanup,
  abrupt responder-death propagation, new-request-ID refetch refusal, and
  rollback-watchdog death during fetch. The
  [offline result](../test-results/2026-07-28-recovery-fixed-fetch-offline.md)
  grants no image or live authority.
- `reboot-fallback-to-fastboot.sh` requires the separately pinned fallback
  host identity, exact stock kernel/init/compatible/ext4 state, empty pstore,
  zero project modules, safe thermals, and a separate reboot guard. Its only
  reboot primitive is the standard AArch64 `RESTART2("bootloader")` syscall;
  the host then requires the exact serial and `lahaina` product. An SSH
  disconnect before the remote marker is accepted only when that exact
  fastboot identity independently proves the reboot. The mocked test rejects
  NVMEM, sysfs, partition, flash, and identity-bypass paths.
- The active lifecycle uses `fallback-acm-control.py wait-ssh-preflight` over
  the exact fallback USB-NCM product. It requires the dedicated client key,
  pinned Ed25519 host key, direct `169.254.77.1/30` route, exact active
  NetworkManager profile UUID and restoration, recovery USB
  continuity, one signed nonce-bound health frame, and post-reply USB
  revalidation. The interactive ACM actions remain emergency-only.
- `prepare-headless-ssh-deployment-candidate.py` can retain the proven v3
  target while assigning only the fixed r2 signed-bundle identity. Its test
  packages base and r2 with identical target inputs, requires every manifest
  field except `bundle` to remain byte-equivalent, and requires distinct
  manifest hashes. The lifecycle rejects the consumed live v3 manifest before
  private-key inspection. See the
  [r2 offline result](../test-results/2026-07-31-headless-ssh-successor-r2-offline.md).
- `preflight-headless-ssh-successor-candidate.py` moves the real r2
  package/candidate/artifact/manifest check before signing-key access. Twenty-two
  offline tests require a clean pushed checkpoint first, secure external-input
  metadata, exact package reconstruction of both caller-owned records,
  bundle-only succession, descriptor-bound artifact snapshots, production
  identity rederivation from the tracked contract, canonical public output,
  and sanitized failure. Credential derivation, bundle signing, privilege,
  external network, and phone/transport surfaces must remain unreachable;
  only local read-only Git checkpoint commands are allowed.
- `network-root-acm.py` replaces terminal attachment with three fixed staging
  actions, `O_NOCTTY`, exact recovery-gadget discovery, a separate attended
  kexec guard, and sanitized console output. Its pseudoterminal regression
  proves cursor-position queries are never returned as shell input.
- `run-persistent-root-p2-live-gate.sh` composes the manifest-pinned temporary
  boot, fixed P2 ACM actions, volatile target-host-key capture, immutable
  target readiness record, untouched 600-second watchdog, exact fallback
  identity/root state, private evidence, and ModemManager restoration. Its
  mocked positive path proves exact ordering and one execute; a target
  rejection cannot reach fallback acceptance. The volatile key is retained
  only after the peer reports the exact target kernel; failed probes truncate
  their temporary known-hosts file. The ACM preflight success marker must not
  occur literally in its echoed command, and the P2 boot-contract test
  forbids target-only `rog5.ufs_discovery` in the ASUS boot-v3 wrapper while
  the separate kexec-loader test requires exactly one such token for the
  Linux 7.1.4 target. The ACM preflight independently counts 116 physical
  nodes, requires every node read-only, and permits zero block-backed mounts.
  If strict SSH sees the exact pinned Alpine fallback before target
  acceptance, the runner records elapsed time privately, restores host state,
  and exits rejected immediately. The rejected one-pass package decoded
  `/proc/config.gz` once but returned to exact fallback after 37 seconds and
  is consumed. Its successor required exact running release
  `7.1.4-gcfd385a1c754` through `uname -r`, then returned to exact fallback
  after 36 seconds without target USB; it is also consumed. The latest target
  reads `/proc/sys/kernel/osrelease` directly, invokes no `uname`, separates
  file/read failure from identity mismatch, and has no proc-config
  dependency. The boot-contract regression extracts the recovery-hashed
  target Image's IKCONFIG stream, requires byte identity with the pinned
  config, and checks IKCONFIG, read-only UFS, ext4, and OverlayFS. Nine
  pre-USB stages have distinct bounded timing markers. Its sole live cycle
  returned to exact fallback after 37 seconds without target USB and is
  consumed. Six different live packages have now rejected safely, while
  repeated 36-37 second returns make timing insufficient to prove a specific
  init branch. The next diagnostic must expose a fixed credential-free
  RAM-only ACM marker before any userland storage access and retain an
  independent distinguishable reset if USB setup fails. The latest live
  report also keeps automatic fallback screen-off unresolved because the
  panel returned on before one transient corrective action.
- `persistent-root-entry-init` replaces timing inference with a fixed
  RAM-only pre-storage marker. It arms a 120-second reset first, mounts only
  virtual filesystems, reads the exact kernel release with a shell builtin,
  validates one each of the three P2 command-line tokens, requires zero
  block-backed mounts, and exposes a fixed 15-line marker over receive-only
  ACM. `persistent-root-entry-acm.py` opens only the exact
  `ROG5_P2_entry_oracle` character device with `O_RDONLY`; its pseudoterminal
  suite proves it transmits zero bytes and rejects complete mismatched
  markers.
- `run-persistent-root-entry-live-gate.sh` requires a clean synchronized
  branch, exactly one fastboot device, three explicit guards, private
  caller-owned credentials/evidence, and the manifest-pinned entry-v1 image.
  Its positive and rejected-marker mocks both execute target kexec exactly
  once, wait for fixed rollback, reverify the exact `UNBOOTED` root and absent
  selectors, attest the exact OpenRC screen-service files/processes plus
  screen-off state, and restore ModemManager. A failed marker is reported only
  after fallback acceptance; there is no flash, retry, promotion, mount, or
  target shell path.
- The Alpine fallback screen lifecycle has a separate fixture and live
  start/stop/start acceptance. The idempotent toggle avoids a redundant zero
  write rejected by the real panel, the daemon traps termination and reaps its
  `evtest` child/FIFO, and the phone-start wrapper initializes volatile OpenRC
  state before executing the preserved original launcher. Automatic
  post-cycle persistence was part of the entry-v1 live gate.
- The sole entry-v1 live cycle passed exact recovery/staging and transmitted
  one target execute, but the exact oracle ACM identity never remained stable.
  Automatic rollback restored Alpine without proving which reset path fired.
  Immediate fallback acceptance stopped on the unchanged 60 C thermal
  ceiling; after passive cooling, the exact preflight and full root/screen
  attestation passed. The root remained `UNBOOTED`, and OpenRC returned
  automatically with one dynamic `qpnp_pon` reader and all backlights off.
  This accepts the fallback screen correction but rejects target entry.
  Entry-v1 is consumed and must not be retried; see the
  [live rejection](../test-results/2026-07-28-persistent-root-entry-v1-live-rejected.md).
- Build diagnostic modules under `tools/diagnostics/` only against the exact fallback kernel, and record their local hashes before use.

## Tier 1 — boot and recovery

- `fastboot boot` reaches the 5.4 kexec staging initramfs without flashing or mounting storage.
- The first candidate exposes supervised USB ACM without credentials or SSH;
  USB networking may remain unaddressed in this sub-tier.
- The staging rollback timer returns to the installed fallback kernel.
- The v15 diagnostic maps approximately 21/31/51/71-second fallback intervals
  to pre-`/init`, wake-lock, block-backed-mount, and physical-lock paths; it
  stopped after the 31-second wake-lock result and never ran kexec.
- V16 exposed exact `ROG5_recovery`, NCM, and automatic rollback but lacked an
  ACM device node. V17 proved the RAM/storage gates and live rescan fix.
- V18 exposed credential-free ACM, proved a RAM-backed root and read-only
  physical storage, and returned through its 180-second watchdog twice. The
  separate attended kexec then passed Linux 7.1 RAM-root, zero-storage,
  ACM/NCM, watchdog, fatal-log, and automatic rollback checks.
- Before exposing USB, both stages reject any block-backed mount and use
  `BLKROSET` through `blockdev --setro`; every physical disk and partition
  must report read-only. Volatile loop, RAM, and zram devices are excluded.
- After creating the ACM function, both stages must rescan device nodes,
  require `/dev/ttyGS0`, and repeat the storage gate before ACM or UDC binding.
- The mainline payload loads, then starts only after a separate attended `kexec -e`.
- Before kexec, exactly one Haven hypervisor watchdog control is disabled and verified; a secure-watchdog deactivation failure aborts the test.
- The Linux 7.1 target reports the expected release, starts `/init`, mounts configfs, configures NCM/ACM, binds the expected UDC, creates `usb0`, and runs its independent rollback timer.
- The host enumerates the target NCM or ACM function and target SSH becomes reachable.
- If host enumeration fails, record UDC state and `usb0` carrier, allow the rollback timer to recover the phone, then capture the reserved region with `tools/diagnostics/ramoops-raw` before changing hardware enablement.
- UFS remains disabled and the target has zero block-device mounts.
- Watchdog/reset counters do not increase unexpectedly.
- A normal reboot still reaches the fallback slot.

## Tier 1.5 — read-only UFS discovery

Status: **passed by discovery v2**. Exact `7.1.4-gcfd385a1c754` exposed all
116 physical nodes read-only with zero blocked commands and no UFS
error-handler signature, then the untouched watchdog chain automatically
restored the exact fallback kernel.

- Use only the dedicated compile-time discovery kernel and its exact
  UFS/USB2 DTB; no normal mainline image is interchangeable.
- Arm rollback before enumeration and attest
  `CONFIG_SCSI_UFS_DISCOVERY_READ_ONLY=y` from `/proc/config.gz`.
- Require at least one physical UFS disk while retaining zero block-backed
  mounts.
- Require every disk and partition to report read-only through sysfs and the
  block ioctl before ACM/NCM is exposed.
- Collect only the sysfs topology inventory; do not run `blkid`, mount, fsck,
  partitioning tools, raw-device reads, or write tests.
- Require the Qualcomm UFS driver, forbidden host/WLUN runtime PM,
  auto-hibern8 disabled, zero blocked commands, exact compiled guard markers,
  working ACM/NCM, no UFS error handler or fatal log signature, and orderly
  automatic return to the exact fallback kernel.
- Require rollback to arm an independent delayed SysRq reset before starting
  `reboot -f` in the background, so shutdown cannot block the fallback path.
- Treat the resulting topology as design input only. Persistent rootfs or
  partition changes require a later explicit authorization.

## Tier 1.75 — UFS-disabled network root

Status: **offline, privileged host, normal-coldplug, and retained-exitrd reboot
gates passed**. Persistent storage and hardware bring-up remain isolated.

- Use only the fourteen-file manifest-pinned network-root bundle.
- Require built-in NFSv4.2, TCP, OverlayFS, tmpfs xattrs, USB ACM/NCM, and
  `/proc/config.gz`.
- Require SCSI/UFS, SCSI disk/BSG/RPMB, and UFS/combo/PCIe/SuperSpeed QMP PHY
  paths to be absent from the final kernel config and module archive.
- Keep the accepted USB2 recovery DTB with UFS and its PHY disabled.
- Restrict the host NFSv4 export to `169.254.77.2` on the dedicated USB
  interface, export it read-only, and remove the runtime export/firewall rule
  after the attended test.
- Run `test-network-root-host.sh` before privilege; require a fixed
  NFSv4.2-only listener address, exact gadget identity, read-only bind mount,
  dedicated drop-by-default zone, pre-zone drops for broad host zones, and
  cleanup traps.
- Require read-only NFS lower, 2 GiB `nodev,nosuid` tmpfs upper, OverlayFS
  `/`, zero physical block devices, and zero block-backed mounts before
  accepting userspace.
- Boot `multi-user.target`, leave `usb0` unmanaged, and require key-only SSH.
- Verify exact kernel release, systemd state, nested mounts, watchdog, stable
  USB traffic, no fatal log signature, and automatic return to fallback.
- Require the default loader path to carry no systemd mask. Diagnostic mode
  may mask only the two named coldplug/module units and must fail before kexec
  for any other value.
- The diagnostic target must reach running systemd, active
  `multi-user.target`, key-only root and unprivileged SSH, zero failed units,
  and a controlled watchdog disarm. **Passed twice.**
- Replay coldplug candidates only through the explicit allowlisted probe with
  an independent process-group watchdog. **Passed; `gpucc_sm8350` isolated as
  the live stall, and overlapping `rmtfs_mem` rejected by DT review.**
- Before any further GPUCC attempt, require a GPUCC-only DT with every
  consumer disabled, an external hash-pinned module, default-off read-only
  tracing, two byte-identical builds, and the same zero-storage/watchdog gate.
  **V9 passed those offline and baseline gates. V10 then passed duplicate
  kernel/module, wrapper/package, mutation, and bundle gates; live tracing
  completed power-domain, reset, GDSC, and protected-clock phases, then stopped
  during CCF registration of index-0 `gpu_cc_ahb_clk` and rolled back safely.
  V11 passed the required offline gate with exact-compatible traces over
  regmap lookup, devres, prepare-lock/runtime PM, parent/orphan/hash,
  phase/duty/rate, orphan reparenting, debug registration, and return. Two
  clean kernel, wrapper, and package paths match. A missing marker may retry
  only the identical idempotent load action once; kexec execution is never
  retried. Its one live probe passed the full zero-storage baseline and
  stopped inside `clk_core_reparent_orphans_nolock()` after index-0 orphan
  insertion and all earlier traced phases. Independent rollback, exact
  fallback, and cleanup passed. V12 passed the required source-order,
  mutation, 5.6-second trace-budget, duplicate kernel/wrapper/package, and
  exact-bundle gates, then ran once. It completed the new GPUCC orphan's
  no-parent scan and stopped inside `__clk_init_parent()` for the next,
  DISPCC-owned orphan. Independent rollback, exact fallback, and complete
  cleanup passed. V13 passed its source-order, mutation, strict-style,
  8-second trace-budget, duplicate kernel/wrapper/package, and exact-bundle
  gates. It separately brackets the display clock's existing `get_parent()`
  callback and cached-parent lookup, records read-only runtime state, and adds
  no runtime-PM or hardware control. Its one attended probe recorded the
  display provider runtime-suspended, entered that callback, and did not reach
  the callback-complete or later parent-cache markers. Independent rollback,
  exact fallback, and cleanup passed. V14 passes the next offline gate with a
  default-off exact-clock boundary around the existing display-RCG regmap
  read. Source/mutation/integration tests preserve one read, reject PM or
  hardware control, and cap its two-orphan trace at 4.2 seconds. Two clean
  kernel, wrapper, and package paths match byte-for-byte, and the exact bundle
  verifier passes. Its one attended zero-storage probe reached
  `parent-read-begin` and never reached `parent-read-complete`; independent
  rollback, exact fallback, and complete cleanup passed. V14 must not be
  rerun. V15 passes the successor offline gate: an exhaustive lock model,
  red/green source/integration/mutation contracts, and 118 clock KUnit tests
  validate an experimental CCF ordering candidate that acquires generic
  all-provider runtime-PM references before the global prepare lock and
  releases them after unlocking. Two clean kernel, wrapper, and package paths
  match byte-for-byte; exported symbols, modules, and RCG2 remain v14-exact.
  V15's one probe made DISPCC active, completed 7/7 observed RCG reads, and
  completed common-clock indexes 0 through 6 before entering index 7. Its 552
  CCF markers arrived continuously for 73.901 seconds with no gap over 0.116
  seconds until the 75-second watchdog reset. Exact fallback and cleanup pass,
  but registration did not return. V15 must not be rerun. Require a v16
  trace-free confirmation to reject all three core trace flags, retain only
  the bounded outer GPUCC trace, bind exactly one GPUCC device, remain stable,
  keep every consumer/storage path disabled, and pass exact rollback.**
- Require v16 to reuse the exact v15 artifact manifest while its explicit
  confirmation action omits all three core trace flags. Before its independent
  watchdog arms, require a hash-pinned read-only baseline to prove the initial
  watchdog remains armed, command-line count zero plus mode-`0400` state `N`
  for each built-in parameter, zero storage, and consumer isolation. Retain
  only the read-only, delay-free outer GPUCC trace. **Passed offline through
  red/green semantic and mutation tests, baseline source checks, existing
  guarded-probe checks, nine ACM pseudoterminal tests, and the exact
  nested-bundle verifier. The attended cycle stopped before target entry when
  a 284-second operator gap exceeded the staging watchdog; no execute was
  transmitted, exact fallback/cleanup passed, and v16 is consumed.**
- Require v17 to preserve the exact v15 artifacts and v16 target gates while
  one guard-first host process performs trace-free load then execute. Permit
  only the existing one-time identical-load replay; make execute unreachable
  after load failure and non-retryable after serial transmission. **Passed
  offline through 12 ACM tests, semantic and mutation rejection, and the
  complete exact nested-bundle verifier. Its one live cycle sent exactly one
  execute, completed all eight GPUCC markers, bound one device for 30 seconds,
  kept every consumer/render/storage path absent, rebooted normally, and
  restored exact fallback with complete cleanup. V17 must not be rerun.**
- Before enabling GPU or GMU, source-test and reproduce the smallest
  consumer-disabled Adreno SMMU slice. Require exactly seven clocks, one CX
  domain, twelve IRQs, runtime PM, no firmware path, a two-status DT change,
  unchanged Linux Image/modules/target initramfs, clean duplicate wrapper and
  package builds, zero storage, and fail-closed baseline/probe contracts.
  **Passed offline; the phone was not contacted.**
- Permit one attended RAM-only SMMU probe only after the read-only baseline
  passes with the original watchdog armed. Arm a separate 120-second
  transition watchdog before disarming the original, then run the existing
  independent 75-second probe exactly once and request fallback reboot in the
  same target process. Require one GPUCC bind, one exact SMMU bind, runtime
  suspend, no GPU/GMU client, firmware, render node, warning, IOMMU fault,
  storage, thermal, reboot, or cleanup failure. The isolated firmware-free
  export, exact server allowlist, five-file strict-SSH launcher, negative
  tests, watchdog ordering, and complete bundle re-verification pass offline.
  **V18 was consumed by a safe baseline rejection: `fault` matched inside the
  normal word `Default`, before any watchdog disarm, module load, or SMMU bind.
  Exact fallback and cleanup passed; v18 must not be retried. V19 keeps the
  unchanged reproduced binary, corrects the token-delimited fault detector,
  passes regressions and full offline re-verification, and has a new isolated
  exact-allowlist export. V19 passed baseline and GPUCC registration but
  rejected because the SMMU remained unbound after 30 seconds. No warning,
  fault, firmware, render, storage, failed-unit, or thermal message appeared;
  direct post-bind checks were not reached. Watchdog fallback and complete
  cleanup passed. V19 must not be retried.**
- Before another SMMU cycle, source-pin the platform `drivers_probe` path and
  capture the exact device's `waiting_for_supplier`, deferred-list, driver,
  identity, and device-link state before and after GPUCC registration. Permit
  only one exact-device reprobe after both watchdogs are armed. Reject any
  global deferred-timeout extension, broad bus rescan, force-bind, unload,
  retry, firmware, render, or storage path. **Passed offline. The source lock
  proves exact-name `device_attach()` semantics and suppressed SMMU bind
  attributes; baseline/probe evidence covers deferred/supplier and direct
  safety state; the 90-second probe permits one `3da0000.iommu` request inside
  a 150-second transition watchdog. The isolated v20 root verifies with 1,008
  modules, zero A660 firmware, preserved credentials, and unchanged base.
  V18/v19 are no longer server-allowlisted. The single v20 cycle stopped
  safely at baseline because the fresh unset override reads `(null)`, not an
  empty line. No handoff, GPUCC load, reprobe write, or SMMU bind occurred;
  fallback and cleanup passed. V20 is consumed.**
- Before another exact-device SMMU cycle, source-pin platform zero-allocation,
  override display/match behavior, and NULL `%s` formatting. Accept only exact
  `(null)` as the reviewed unset state, reject every other nonempty value,
  forbid any `driver_override` write, and preserve the v20 one-device and
  watchdog boundaries. **Passed offline as v21. The source verifier pins OF
  allocation, zero initialization, `%s` NULL formatting, override matching,
  and OF fallthrough. The seven-byte checker passes positive and mutation
  tests. The unchanged binary and a new isolated root verify with 1,008
  modules, zero A660 firmware, preserved credentials, and unchanged base.
  The sole v21 live cycle passed: GPUCC registered, one exact-device reprobe
  bound `arm-smmu`, runtime status reached `suspended`, firmware/render/storage
  counters stayed zero, and exact fallback plus complete cleanup passed. V21
  is consumed, must not be retried, and is absent from the runnable
  allowlist.**
- Before any A660 registration-only cycle, hash-pin the exact v21 live
  acceptance into the compile-time source lock, rebuild or reseal every
  dependent export/stage/wrapper/package artifact, reject consumed diagnostic
  roots, and rerun the full offline verifier. **Passed as registration v2.
  The mutation-tested marker is read only from the immutable NFS lower; the
  new root-owned export verifies seven modules, zero firmware, preserved
  credentials, and an unchanged base. Old/consumed roots are rejected and the
  unchanged fourteen-file package passes its full exact verifier.**
- Before running registration v3, carry the accepted exact-device reprobe into
  the probe, accept only exact unset override state, wait five seconds for
  ordinary autoprobe, and permit at most one `3da0000.iommu` write before DRM
  dependencies. **Passed offline; v3 replaces v2 in the runnable allowlist.**
- Before running registration v3, fail-first test one atomic host/target
  launcher with exact Git/artifact/export/SSH identity, nested watchdogs, one
  invocation, private evidence, immediate normal reboot, persistent-fallback
  health, and complete privileged host cleanup. **Passed offline. Dedicated
  A660 disarm, compound gate, and host-runner suites pass; the full exact
  bundle and actual root-owned v3 export reverify with NFS inactive.**
- Run registration v3 at most once, require one exact SMMU reprobe, seven
  loaded modules, GPU/GMU attachment to two IOMMU groups, one unopened
  headless render node, zero firmware/connectors/storage/faults, normal
  fallback, and complete host cleanup. **Passed live. Maximum target
  temperature was 38.1 C; persistent fallback returned with zero pstore and
  project modules; v3 is consumed and absent from the runnable allowlist. The
  exact report/marker pair is hash-pinned and mutation-tested.**
- Prove whether exact A660 firmware requests can be separated from the normal
  first-open ucode, runtime-power, hardware-init, HFI, and ZAP/SCM path.
  **Passed offline. The pinned source has one seam after SQE/GMU requests; a
  no-open provisioning gate would test nothing.**
- Before any firmware live cycle, fail-first test a default-off, read-only
  module parameter and one-shot failed-open helper; include only exact
  mode-`0644` SQE/GMU files, exclude ZAP, reproduce every build/export/package
  twice, and require independent rollback. **Passed offline. The exact patch,
  two clean kernel builds, two static-helper builds, root-owned SQE/GMU-only
  export, mutation-tested target/host watchdog gate, and unchanged AVB package
  pass their complete contracts; see the
  [request-only v4 offline report](../test-results/2026-07-26-a660-firmware-request-only-v4-offline.md).**
- Run request-only v4 at most once; require exact `EUCLEAN`, two firmware
  requests, one success marker, no surviving DRM descriptor, zero
  ucode/power/HFI/ZAP/SCM/storage/display/fault evidence, exact fallback, and
  complete cleanup. **Passed live. Maximum target temperature was 38.5 C;
  persistent fallback returned with zero pstore/project modules; v4 is
  consumed and absent from the runnable allowlist. The exact report/marker
  pair is hash-pinned and mutation-tested; see the
  [request-only v4 live acceptance](../test-results/2026-07-26-a660-firmware-request-only-v4-live-accepted.md).**
- Source-audit exact A660.1 ucode allocation, then require a default-off,
  read-only, atomic one-shot patch with balanced SQE, shadow, power-up
  reglist, IOVA, CPU-vmap, and firmware rollback on every path. **Passed
  offline. The exact patch passes eight mutations and strict checkpatch.**
- Build the exact `0012` → `0013` → `0014` stack twice in network-disabled
  isolated containers. Require byte-identical outputs, unchanged
  Image/config/ABI and non-MSM modules, exact MSM-only delta, BTF, both
  diagnostic modes, and zero embedded firmware. **Passed offline; see the
  [ucode-allocation build report](../test-results/2026-07-26-a660-ucode-allocation-build.md).**
- Before any ucode-allocation live cycle, fail-first test a fresh versioned
  root/export and watchdog gate with exact map/unmap counts, zero surviving
  GEM/DRM state, no runtime power/HFI/ZAP/SCM/storage path, immutable fallback,
  and complete host cleanup. **Passed offline. The root-owned candidate,
  PID-filtered exact pointer/count contract, equal pre/post GEM snapshots,
  nine forbidden-event probes, nested watchdogs, and unchanged full boot
  package pass; NFS remains inactive and the root is deliberately not
  runnable. See the
  [ucode-allocation v5 offline report](../test-results/2026-07-26-a660-ucode-allocation-v5-offline.md).**
- Fail-first test the host-side live controller independently. Require a
  clean synchronized checkpoint, exact immutable root/package/gate inputs,
  strict SSH identity, one invocation, no retry or NFS/boot/flash control,
  and private evidence. **Passed offline in a mock transport suite. The
  separate
  [pre-live control acceptance](../test-results/2026-07-26-a660-ucode-allocation-v5-prelive-hold.md)
  records HOLD; it does not authorize contacting the phone.**
- Lift HOLD only after exact fallback, SSH identity, root, package, runner,
  service, and clean-Git checks pass. Add only one explicit-opt-in v5 server
  case and require its complete verifier before any host mutation. **Passed;
  the
  [pre-live GO review](../test-results/2026-07-26-a660-ucode-allocation-v5-prelive-go.md)
  authorized at most one attended RAM-only cycle.**
- Run the one authorized v5 cycle exactly once, never flash, and consume the
  tier whether it passes or rejects. **Completed with safe rejection. The
  kernel completed balanced three-object rollback, but the gate stopped at
  public wrapper `get=1`, expected `4`, before settle/snapshot comparison.
  Exact fallback and host cleanup passed; v5 is consumed. See the
  [v5 live rejection](../test-results/2026-07-26-a660-ucode-allocation-v5-live-rejected.md).**
- Before designing v6, hash-pin the accepted MSM module and test its symbols
  and `.rela.text` call layout. Require three logical gets inlined through
  `msm_gem_kernel_new()`, two logical puts inlined through
  `msm_gem_kernel_put()`, public wrapper counts `get=1, put=2`, and logical
  balance `4/4`. **Passed offline.**
- Build a fresh default-off v6 root and gate that traces three successful
  `kernel_new` and two `kernel_put` operations, retains every v5 pointer,
  firmware, forbidden-event, storage, and watchdog constraint, and reaches
  an equal post-settle GEM snapshot. Require independent mock tests and a new
  HOLD/GO review; never reuse v5 authorization. **Passed offline and remains
  HOLD. Generated-runtime reproducibility, semantic mutations, compound-gate
  ordering, exact compiler relocations, protected whole-tree export checks,
  a changed-seal mutation, and the unchanged boot package pass. NFS is
  inactive and no live runner existed at this checkpoint; see the
  [v6 offline report](../test-results/2026-07-26-a660-ucode-allocation-v6-offline.md).**
- Fail-first test a v6 host runner with exact immutable inputs, strict SSH
  identity, private evidence, one invocation, no retry, and no NFS/boot/flash
  control. **Passed offline. The mock proves one prepare, copy, verify, and
  gate call; local credential/root/service checks pass, NFS remains inactive,
  and the separate
  [v6 pre-live control acceptance](../test-results/2026-07-26-a660-ucode-allocation-v6-prelive-hold.md)
  records HOLD without contacting the phone.**
- Lift v6 HOLD only through a verifier-before-state, explicit-opt-in NFS case
  plus clean Git, exact fallback, distinct SSH identity, root/package/runner,
  credential, and inactive-service checks. **Passed. The actual unarmed
  privileged launcher refused with zero residue, and the
  [v6 pre-live GO review](../test-results/2026-07-26-a660-ucode-allocation-v6-prelive-go.md)
  authorizes at most one attended RAM-only cycle with no retry.**
- Run that v6 cycle exactly once and consume it regardless of result.
  **Completed with safe rejection. The kernel allocation-and-rollback marker
  passed, but the entry probe saw raw sizes `43288`, `4`, and `4096` while
  the oracle expected page-rounded `45056`, `4096`, and `4096`. The settled
  GEM snapshot was not reached. Watchdog fallback and complete host cleanup
  passed; v6 is consumed and non-runnable. See the
  [v6 live rejection](../test-results/2026-07-26-a660-ucode-allocation-v6-live-rejected.md).**
- Build a fresh v7 userspace gate from the unchanged accepted module. Pin the
  source-derived raw-size set, retain every v6 logical-vmap, pointer-union,
  firmware, forbidden-event, storage, thermal, systemd, and watchdog
  constraint, and require an equal post-settle GEM snapshot. Require a new
  protected root, runner, HOLD, and GO review; never reuse v6 authorization.
  **Runtime, target gate, and protected root pass offline; runner and GO
  remain pending. The accepted contract separately pins raw
  `4/4096/43288` and page-rounded `4096/4096/45056`, inherits the exact
  accepted module from consumed v6, preserves logical `4/4` and settled
  snapshot checks, and rejects predecessor and size-layer mutations. V7 has
  no server case or runner, NFS stayed inactive, and the phone was not
  contacted. See the
  [v7 offline report](../test-results/2026-07-26-a660-ucode-allocation-v7-offline.md).**
- Fail-first test an exact one-invocation v7 host runner with strict SSH
  identity, immutable inputs, private evidence, no retry, and no
  NFS/boot/flash control. Reverify the protected root and record a separate
  non-runnable HOLD. **Passed offline. The mock proves one prepare, copy,
  verify, and gate call with expected reboot disconnect; local
  credential/root checks and an actual unarmed refusal pass, NFS remains
  inactive, and the
  [v7 pre-live control acceptance](../test-results/2026-07-26-a660-ucode-allocation-v7-prelive-hold.md)
  records HOLD without contacting the phone.**
- Lift v7 HOLD only through a later verifier-before-state,
  explicit-opt-in server case plus clean Git, exact fallback, credentials,
  root/package/runner hashes, inactive host services, and actual unarmed
  refusal. **Passed. The fail-first exact-root case verifies immutable v7
  before any host mutation; strict fallback and distinct SSH identities,
  credentials, package/root/runner hashes, clean synchronized Git, inactive
  services, and actual unarmed runner/server refusals pass with zero residue.
  The
  [v7 pre-live GO review](../test-results/2026-07-26-a660-ucode-allocation-v7-prelive-go.md)
  authorizes at most one attended RAM-only cycle with no retry and no
  flash.**
- Run at most one RAM-only v7 cycle under nested watchdogs, require the full
  raw-size, pointer-union, logical `4/4`, complete rollback, and equal settled
  snapshot contract, then consume v7 regardless of result. **Passed live.
  Three successful allocations matched raw `4/4096/43288`, every pointer set
  and logical `4/4` rollback check passed, the 20-second settled GEM snapshot
  was equal, and power/HFI/ZAP/SCM/storage/fault evidence stayed zero. Normal
  reboot restored exact fallback and complete host cleanup; v7 is consumed
  and non-runnable. See the
  [v7 live acceptance](../test-results/2026-07-26-a660-ucode-allocation-v7-live-accepted.md).**
- Before enabling an Adreno rendering consumer, source-test the remaining
  GPU/GX, regulator, interconnect, GMU, reserved-memory, firmware, and complete
  consumer dependency graph. **Passed. The audit separates probe-time
  IOMMU/RSCC/PDC work from first-open firmware/power/SCM work.**
- Source-test the first normal GMU resume entry after the initialized guard
  and before software mutation, inner runtime-PM, clocks, MMIO, IRQ, firmware,
  HFI, hardware initialization, or ZAP/SCM. Require an exact-A660.1,
  read-only, atomic-one-shot failed-open path and complete accepted-v7
  rollback. **Passed source and mutation tests; see the
  [boundary report](../test-results/2026-07-26-a660-gmu-resume-entry-boundary.md).**
- Build that v8 diagnostic twice from clean pinned source in isolated,
  network-disabled containers. Require byte-identical config, Images,
  symbols, module archive, metadata, and critical modules; relative to
  accepted v7, permit only `msm.ko` to change. **Passed offline; the
  [v8 build report](../test-results/2026-07-26-a660-gmu-resume-entry-v8-offline.md)
  records exact hashes and HOLD.**
- Before any v8 live decision, build and mutation-test a fresh protected
  storage-free root, target gate, strict no-retry runner, exact-root NFS case,
  unchanged package verifier, fallback preflight, and separate HOLD/GO
  reports. **The reproducible target runtime and compiler-relocation gate now
  pass, including predecessor, mode, resume, rollback, inner-PM, clock, IRQ,
  HFI, snapshot, errno, and writable-parameter mutations. The
  consumed-v7-derived protected root and compound target gate also pass:
  whole-tree exact delta, credentials, seven modules, two firmware files,
  generated controls, five negative mutations, watchdog overlap, inactive
  NFS, and non-runnable HOLD are verified. The strict host runner and
  separate pre-live HOLD now also pass: one mocked
  prepare/copy/remote-verify/gate sequence, private evidence, expected reboot
  disconnect, no retry, local credential agreement, complete root
  reverification, actual unarmed refusal, and inactive NFS/RPC. The separate
  attended GO review now passes too: one fail-first, verifier-before-state,
  exact-root NFS case; complete fourteen-file package and protected-root
  verification; all five hostile mutations; distinct SSH identities; strict
  read-only fallback health; real unarmed server/runner refusals; and final
  residue-free host state. Exactly one RAM-only v8 cycle was authorized, with
  no retry and no flash. See the
  [v8 runtime report](../test-results/2026-07-26-a660-gmu-resume-entry-v8-runtime-offline.md)
  and
  [v8 protected-root report](../test-results/2026-07-26-a660-gmu-resume-entry-v8-root-offline.md)
  and
  [v8 pre-live HOLD report](../test-results/2026-07-26-a660-gmu-resume-entry-v8-prelive-hold.md)
  and
  [v8 pre-live GO report](../test-results/2026-07-26-a660-gmu-resume-entry-v8-prelive-go.md).**
- Run the authorized v8 cycle exactly once and consume it regardless of
  result. **Completed with safe rejection. The kernel reached exact GMU
  resume entry, propagated deliberate `EUCLEAN`, and completed accepted
  rollback. Arm64 zero-extension made the three `int` returns appear as
  `4294967179` to the `s64` oracle; complete trace review also found 21
  process-scoped generic runtime-PM calls instead of the assumed one. Direct
  inner PM/resource/HFI/hardware/ZAP/SCM probes stayed zero. The runner was
  not retried, exact fallback and cleanup passed, and v8 is permanently
  consumed. See the
  [v8 live rejection](../test-results/2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md).**
- Before any GMU power-preparation tier, build a separately versioned v9
  userspace oracle around the unchanged v8 module. Require fail-first signed
  32-bit return tests, GPU-device-scoped runtime-PM matching, all existing
  zero-resource and rollback constraints, full settle and equal snapshot,
  fresh protected-root/runner controls, and a separate HOLD/GO review.
  **The runtime-only portion passes offline. Signed and zero-extended
  `EUCLEAN`, the observed 21-call fixture with one GPU-device match, duplicate
  generation, unchanged v8 module, all retained safety constraints, and
  twelve mutations pass; see the
  [v9 offline runtime report](../test-results/2026-07-26-a660-gmu-resume-entry-v9-runtime-offline.md).
  The consumed-v8-derived protected root and compound target gate now also
  pass: the exact unchanged kernel/seven-module/two-firmware payload,
  versioned signed/device oracle, credentials, whole-tree delta, overlapping
  watchdogs, construction cleanup, and independent final-path audit are
  verified; see the
  [v9 protected-root report](../test-results/2026-07-26-a660-gmu-resume-entry-v9-root-offline.md).
  The strict one-invocation/no-retry runner and separate pre-live review also
  pass: exact mock call counts, dynamic classified generic-PM evidence,
  private logging, local client/server SSH agreement, real unarmed refusal,
  clean synchronized Git, full root revalidation, inactive NFS/RPC, and zero
  server tokens are verified; see the
  [v9 pre-live HOLD report](../test-results/2026-07-26-a660-gmu-resume-entry-v9-prelive-hold.md).
  A fail-first verifier-before-state exact-root server case and every local
  GO gate now also pass, including the unchanged fourteen-file package and an
  actual unarmed zero-state refusal. The
  [v9 attended GO review stopped at HOLD](../test-results/2026-07-26-a660-gmu-resume-entry-v9-prelive-go-hold.md)
  because the phone is physically absent, so the identity-pinned current
  fallback health preflight cannot run. NFS never started at that checkpoint.
  The later
  [sole v9 live cycle](../test-results/2026-07-27-a660-gmu-resume-entry-v9-live-accepted.md)
  passes one GPU-device outer PM event, signed `EUCLEAN`, exact rollback,
  logical `4/4`, equal settled snapshots, zero specific inner resources,
  exact fallback, and complete cleanup. V9 is permanently consumed and
  server-non-runnable.**
- Before any later GMU work, source-test and reproduce a fresh GMU/CX
  runtime-PM-only tier. Isolate the first
  `pm_runtime_get_sync(gmu->dev)`, balance a failed get, synchronously return
  the GMU consumer and linked CX supplier to suspended state, and stop before
  GX or later resources. **Passed offline: the
  [v10 acceptance](../test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-offline.md)
  pins the source and patch, rejects twelve mutations, and accepts two
  byte-identical builds whose only changed installed module is `msm.ko`.**
- Before any v10 live review, build a source-pinned runtime oracle and
  require exact GMU/CX-domain classification with zero GX, clock-rate/
  enable, secure-init, MMIO, IRQ, firmware-start, HFI, hardware-init,
  ZAP/SCM, storage, or retained DRM-descriptor activity. Require a fresh
  protected root, runtime mutation suite, target gate, watchdog,
  one-shot/no-retry runner, verifier-before-state server case, and separate
  HOLD/GO review. **The runtime/root/control requirements and separate
  [pre-live HOLD](../test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-prelive-hold.md)
  now pass, including fourteen rejected oracle mutations, complete recursive
  root verification, actual unarmed zero-state refusal, and connected
  fallback health. The later
  [attended-GO HOLD](../test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-prelive-go-hold.md)
  repeats every technical prerequisite after successor-v3 publication and
  stops only on the absent exact user instruction; there is no v10 live
  authority.**
- Before extending v10, prove whether a GX-only stage crosses a hardware
  boundary, then source-test the smallest meaningful next operation. **The
  [v11 offline acceptance](../test-results/2026-07-27-a660-gmu-clock-preparation-v11-offline.md)
  proves SM8350 GX power-on is a no-op, so v11 balances GX bookkeeping and
  isolates both GMU rates plus all seven clocks. Strict style, eighteen
  hostile mutations, two byte-identical isolated builds, and exact-v10
  comparison pass; only `msm.ko` changes.**
- Before any v11 runtime use, require accepted-and-consumed v10, a
  source-pinned clock/runtime oracle, fresh protected root, target/watchdog
  gate, one-shot/no-retry runner, verifier-before-state bounded-server case,
  and separate HOLD/GO reviews. **Pending; v11 is not packaged, exported,
  allowlisted, or authorized.**
- Require the first registration kernel to keep DRM/MSM, GPUCC, and MDT
  loading modular; disable display KMS and UFS; propagate GMU power-level
  failures; embed no A660 firmware; and reproduce its config, Images, module
  archive, symbols, critical modules, and metadata twice. **Passed offline;
  nine outputs are byte-identical and the phone was not contacted.**
- Reproduce the exact v18-derived four-node DT and reject missing nodes,
  disabled dependencies, wrong firmware, hardware-property overrides, extra
  consumers, modified bases, and input/output aliasing. **Passed; duplicate
  DTBs are byte-identical and storage/display containment is unchanged.**
- Require a read-only pre-disarm baseline and an independent SysRq-watchdog
  probe that manually loads the exact seven-module chain, never opens DRM,
  detects any firmware request, and disarms only after stable registration.
  Keep a source lock until a passing SMMU live marker is hash-pinned. **Passed
  offline against the exact build; deliberately locked for live use.**
- Reproduce the initramfs/module stage carrying the accepted baseline and
  probe, then the nested wrapper and temporary-boot package before permitting
  registration. **Passed offline: the isolated seven-module export, duplicate
  stages, clean wrappers, header-v3/AVB repacks, and exact fourteen-file
  bundle all verify; the source lock remains.**
- Require the recovery DT contract to disable RMTFS, GPUCC, GPU, GMU, and the
  Adreno SMMU. **Passed reproducibly and in two normal-coldplug boots.**
- Require persistent client authorization plus one pinned server host
  identity to pass strict verification across two boots. **Passed.**
- Require `/run/initramfs/shutdown` to match the reviewed source and execute
  with its retained AArch64 BusyBox/musl runtime. Unmount OverlayFS before its
  tmpfs and NFS backing filesystems, then prove normal `systemctl reboot`
  returns to the exact fallback and removes all host runtime state.
  **Passed once with v3; repeated clean cycles remain a Phase 4 gate.**
- Keep v4 as rejected RTC evidence only: the raw PMK8350 clock was near the
  Unix epoch and set Linux about 56 years behind the host. Require no RTC,
  system-clock, offset-storage, or phone-storage write in this tier.
- For v5 diagnostic input isolation, require RTC disabled, `qcom_pon` absent
  and zero power-key events before the guarded probe, then require the
  watchdog safely disarmed, `qcom_pon` loaded, exactly one
  `pmic_pwrkey`/`pm8941-pwrkey` event, `KEY_POWER`, wakeup enabled, unchanged
  NFS/USB/storage boundaries, and a clean systemd reboot to fallback.
  **Dependency plus diagnostic and normal registration/reboot passed. The
  fail-resumable disarm helper passed live; physical press remains pending
  after a protected 120-second window received no confirmed event.**
- Run `monitor-network-root-pwrkey.sh` only after the full normal-mode gate and
  watchdog disarm. Require its explicit guard, exact storage/NFS/RTC/input
  state, low-level logind inhibitor, and both `KEY_POWER` press and release
  records before accepting the physical switch/IRQ path.
- Before TLS, package, or automation tests, run
  `sync-network-root-time.sh` while the rollback watchdog is still armed.
  Require an NTP-synchronized host, strict dedicated SSH identity, normal
  unmasked Linux, read-only NFS/OverlayFS, zero storage, RTC disabled and
  absent, exact USB state, and no failed/fatal state before and after changing
  only the volatile Linux system clock. **Offline fake-SSH contract and live
  `changed=1` correction of a 2,378,466-second drift passed; independent host
  interval, normal reboot, and cleanup passed.**
- Require the board DTS to reserve the exact three stock-owned RAM spans
  before enabling any remote processor. For the ADSP-only gate, keep every
  other remote processor and PMIC GLINK disabled, stage exact stock firmware
  only in tmpfs, arm an independent SysRq watchdog, and require PAS/SCM
  success, ADSP `running`, only the reviewed PAS/GLINK plus `qrtr` module set,
  zero power supplies/storage, stable USB/NFS, clean logs, and fallback
  restoration. **Passed twice at the hardware boundary; the second run
  passed the complete corrected harness.**
- For the separate telemetry tier, require hash-pinned `qrtr_smd` and
  `qcom_pd_mapper` before PDR and battery-only PMIC GLINK, exact read-only
  SM8350 battery/USB/wireless supplies, zero UCSI/alt-mode/Type-C devices,
  zero charger-control thresholds, clean logs, and the unchanged
  storage/NFS/watchdog boundary. **Passed once with v8; a normal reboot and
  complete cleanup also passed.**
- Before any new H3 hardware run, require
  `test-headless-battery-series.py` to pass. Its eleven hardware-free groups
  cover an executable read-only sysfs fixture, exact collector identity and
  schedule, all canonical header fields, sample ordering/ranges/status,
  phase-to-online-state binding, evidence metadata/replacement, both possible
  current-sign conventions, ambiguous-current refusal, same-boot comparison,
  and capacity-window refusal. The future `battery-charging` capability names
  this test in the compatibility profile and the test is an exact core-CI
  entry. See the
  [battery-series contract](battery-telemetry-series.md).
- Treat charging behavior/control, display, radio, physical input actuation,
  sustained battery-current direction, and GPU as untested despite accepted
  read-only battery values and the normal headless coldplug/input gates.

## Tier 2 — core hardware

- USB NCM remains stable during sustained traffic.
- Battery capacity, voltage, current, temperature, and status are real.
  **One read-only aggregate snapshot passed. A fixed 10-minute sustained
  record and unplugged/USB comparison now pass hostile tests offline;
  collecting those records on the corrected candidate remains pending.**
- Thermal zones and CPU frequency policies are present.
- DRM connector, backlight, and touch work; a physically observed short
  power-button press traverses the switch/IRQ/input path. Driver registration
  alone does not satisfy this gate.
- Screen-off state does not stop SSH, networking, or scheduled work.
- At least 30 minutes of idle and load operation produce no fatal kernel warnings.

## Tier 3 — networking and services

- Wi-Fi client associates and routes to the internet.
- Hotspot DHCP, DNS, NAT, and source-policy routing pass.
- A real hotspot client reaches DNS and the internet only through the
  on-phone VPN; endpoint loss and reconnect never expose the ordinary uplink.
- Radio startup produces no modem watchdog, fatal interrupt, or WLAN RDDM.
- SSH is key-only and remote access is not exposed directly to the public internet.

## Tier 4 — display and desktop

- Plasma Desktop Wayland starts on physical DRM and KRDP shares that session.
- Screen wakes on power-button press and returns to the configured blank timeout.
- Fixed 60/90/120/144 mode selection is verified visually and from the active DRM/KScreen state.
- 60 Hz idle is the default; mode changes do not blank permanently or reset the panel.
- Remote admin UI remains available independently of the physical compositor.

## Tier 5 — GPU (opt-in, run last)

- The fixed
  [A660 accelerated-desktop acceptance](a660-acceptance.md) staging mode runs
  under the still-armed rollback watchdog and its 540-second internal
  deadline. The signed command line must independently attest
  `network-root-v1`, `target_timeout=600`, `rollback_timeout=900`, and the
  exact command-manifest plus `arch-a` tree/seal/count/subtree identity. The
  real persistent-root C verifier must match that identity both before and
  after the workload. A separate mode-`0400` initramfs attestation must bind
  the active OverlayFS, authenticated lower, and bounded tmpfs state by
  stable kernel mount ID across `mount --move`. The mode-`0400` lease must
  bind the
  watchdog and live timer child, both start times, the 900-second boottime
  deadline, and write-capable reset/log descriptors.
- The sole mainline DRM render node survives 100 open/close cycles; vendor
  KGSL is absent.
- `vulkaninfo --summary` succeeds ten consecutive times with Turnip, and the
  minimal helper completes ten real queue submissions.
- `vkcube --wsi wayland --c 120` completes the fixed frame count within its
  bounded window; a hung process cannot pass.
- KWin, EGL, and Vulkan all report A660 hardware with no software renderer.
- Five screen off/on cycles preserve the same KWin process and accept Vulkan
  work with the panel off. A lightweight concurrent monitor samples the state
  marker and zero backlight every 100 ms without spawning processes;
  synchronous checkpoints separately require KScreen DPMS off.
- Every fixed command runs in a fresh delegated cgroup v2; timeout and output
  overflow tests require `cgroup.kill`, `populated 0`, no residual child
  cgroup, and no surviving descendant even after `setsid`.
- No boot-time or new GMU/HFI error, SMMU/IOMMU fault, GPU hang, DRM error,
  external abort, watchdog bite, BUG, Oops, call trace, or panic appears.
- After persistent promotion, the separate 30-minute soak mode requires exact
  bundle/kernel/ext4-subtree/tree/seal provenance plus v2 mount-ID linkage
  from active OverlayFS to the sealed lower and tmpfs state. It recomputes the
  tree through an exact read-only mount and records memory, independently
  matched Plasma process/PSS totals, thermal, battery-current, and capacity
  evidence with the panel off.

The script `scripts/device/kgsl-open-cycle.sh` requires `ALLOW_GPU_FAULT_TEST=1` because the current vendor driver is known to fail this tier.

## Tier 6 — observability and automation

- BPF syscall/JIT, BTF, tracepoints, kprobes, and uprobes are enabled.
- GodShell can load its ARM64 programs without verifier errors.
- The observability daemon runs as a restricted systemd service on the Arch target.
- AI/email/CV automation runs as an unprivileged account with scoped tokens and an approval queue for external actions.

## Release gates

Before any persistent flash:

- three cold boots
- three warm reboots
- one four-hour idle run with screen off
- one sustained CPU/network load run
- charging from low battery through a meaningful interval
- complete redacted report with all mandatory tiers
- verified recovery/fallback procedure
