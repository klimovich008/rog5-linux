# Test plan

Tests are ordered so a failure never hides whether the phone can be recovered. A tier is attempted only after every mandatory test in the previous tier passes.

## Tier 0 — static build checks

- Kernel source revision is pinned and recorded.
- Board DTS compiles with `dtbs_check` warnings reviewed.
- Configuration fragment contains only real symbols.
- `Image`, DTB, modules, initramfs, and boot image hashes are recorded.
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
- `test-screen-toggle.sh` exercises idempotent display state.
  `test-vpn-hotspot.sh` checks service/rule contracts and sends IPv4/IPv6
  packets through isolated AP, VPN, and ordinary-uplink namespaces; it
  requires VPN-only forwarding, unsolicited-client isolation, fail-close
  after VPN loss, and exact cleanup without phone hardware.
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
  absence of broad container privilege or phone-write commands.
- `recovery-linux.sh preflight` requires an explicit manifest-pinned image and
  exactly one fastboot target; no candidate is selected by default and `boot`
  remains inert unless `ALLOW_TEMPORARY_BOOT=1` is explicit. Recovery ACM
  detection requires exact normalized product `ROG5_recovery`; the fallback
  gadget sharing `1d6b:0104` is a hard failure.
- `reboot-fallback-to-fastboot.sh` requires the separately pinned fallback
  host identity, exact stock kernel/init/compatible/ext4 state, empty pstore,
  zero project modules, safe thermals, and a separate reboot guard. Its only
  reboot primitive is the standard AArch64 `RESTART2("bootloader")` syscall;
  the host then requires exactly one fastboot target. The mocked test rejects
  NVMEM, sysfs, partition, flash, and identity-bypass paths.
- `network-root-acm.py` replaces terminal attachment with three fixed staging
  actions, `O_NOCTTY`, exact recovery-gadget discovery, a separate attended
  kexec guard, and sanitized console output. Its pseudoterminal regression
  proves cursor-position queries are never returned as shell input.
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
  **Pending.**
- Before enabling an Adreno rendering consumer, source-test the remaining
  GPU/GX, regulator, interconnect, GMU, reserved-memory, firmware, and complete
  consumer dependency graph. **Passed. The audit separates probe-time
  IOMMU/RSCC/PDC work from first-open firmware/power/SCM work.**
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
- Treat charging behavior/control, display, radio, physical input actuation,
  sustained battery-current direction, and GPU as untested despite accepted
  read-only battery values and the normal headless coldplug/input gates.

## Tier 2 — core hardware

- USB NCM remains stable during sustained traffic.
- Battery capacity, voltage, current, temperature, and status are real.
  **One read-only aggregate snapshot passed; charging-state comparison and
  sustained validation remain pending.**
- Thermal zones and CPU frequency policies are present.
- DRM connector, backlight, and touch work; a physically observed short
  power-button press traverses the switch/IRQ/input path. Driver registration
  alone does not satisfy this gate.
- Screen-off state does not stop SSH, networking, or scheduled work.
- At least 30 minutes of idle and load operation produce no fatal kernel warnings.

## Tier 3 — networking and services

- Wi-Fi client associates and routes to the internet.
- Hotspot DHCP, DNS, NAT, and source-policy routing pass.
- Radio startup produces no modem watchdog, fatal interrupt, or WLAN RDDM.
- SSH is key-only and remote access is not exposed directly to the public internet.

## Tier 4 — display and desktop

- Plasma Desktop Wayland starts on physical DRM and KRDP shares that session.
- Screen wakes on power-button press and returns to the configured blank timeout.
- Fixed 60/90/120/144 mode selection is verified visually and from the active DRM/KScreen state.
- 60 Hz idle is the default; mode changes do not blank permanently or reset the panel.
- Remote admin UI remains available independently of the physical compositor.

## Tier 5 — GPU (opt-in, run last)

- Raw KGSL or DRM render-node open/close/open cycle succeeds repeatedly.
- `vulkaninfo --summary` succeeds at least ten consecutive times.
- A headless Vulkan submit and a rendered Wayland workload pass.
- KWin runs with hardware acceleration and without llvmpipe.
- Suspend/idle/wake cycles do not produce GMU HFI errors or IOMMU faults.
- Power use with GPU idle remains acceptable.

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
