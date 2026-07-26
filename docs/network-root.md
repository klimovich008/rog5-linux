# Native Arch/Debian network-root gate

This is the first full-distribution boot after accepted read-only UFS
discovery. It runs a normal ARM64 distribution as PID 1 directly on Linux,
not inside Android, while keeping phone storage absent from the kernel.

Status: **headless Arch boot, normal systemd reboot, ADSP startup, and one
read-only battery-telemetry snapshot pass**. Linux 7.1.4, systemd, OverlayFS,
read-only NFS, persistent key-only SSH, the zero-storage boundary,
retained-exitrd power cycles, guarded ADSP startup, and the audited
QRTR/PDR-to-PMIC GLINK telemetry path are accepted. Charging, Type-C control,
sustained current-direction validation, display, radio, and GPU remain
separate test tiers.

## Chosen design

The development PC exports one prepared rootfs over NFSv4.2 on the dedicated
USB NCM link. The phone mounts that export read-only, places a size-limited
tmpfs above it with OverlayFS, and executes `switch_root` into the merged tree.

```text
PC rootfs directory -- NFSv4.2 read-only --> phone lower layer
                                             + 2 GiB tmpfs upper
                                             = writable overlay root
                                             -> systemd multi-user.target
```

This gives systemd, SSH, package files, and ordinary Arch/Debian userspace
without writing UFS or mutating the host copy of the rootfs. A reboot discards
the tmpfs upper layer.

NFS is preferred over NBD for this gate because the phone receives no remote
block device. The only new mount is the exact read-only network export.

## Independent safety boundaries

- The Android wrapper remains temporary `fastboot boot`; no image is flashed.
- Kexec load and execution remain separate attended actions.
- The target uses the v2 USB2 recovery DTB, where UFS, its PHY, SuperSpeed
  QMP, the secondary USB controller, RMTFS, GPUCC, GPU, GMU, and the Adreno
  SMMU are disabled.
- The dedicated kernel also compiles out SCSI, UFS host drivers, UFS/QMP PHY
  drivers, BSG, RPMB, and SCSI disk support.
- Initramfs rejects any physical block device or block-backed mount before USB
  exposure and checks again immediately before `switch_root`.
- Device and host addresses are fixed at `169.254.77.2/30` and
  `169.254.77.1`; no command-line network/export parser is present.
- The NFS lower mount is fixed to NFSv4.2 over TCP, port 2049, read-only.
- The tmpfs upper is capped at 2 GiB and mounted `nodev,nosuid`.
- A 60-900 second watchdog opens `/proc/sysrq-trigger` before `switch_root`,
  so it can reset the phone even if the network root or new userspace stalls.
- No private key, SSH host key, machine identity, VPN secret, email data, CV,
  API token, or browser profile enters the kernel/initramfs bundle.

## Kernel and initramfs contract

`configs/kernel/rog5-network-root.fragment` is layered after the normal
mainline requirements. NFSv4.2, its dependencies, OverlayFS, tmpfs xattrs,
USB ACM/NCM, and `/proc/config.gz` are built in. Every UFS/SCSI path is
disabled in the final configuration, not merely left unused by the DTB.

`initramfs/network-root-init`:

1. mounts only proc, sysfs, devtmpfs, devpts, and tmpfs;
2. requires exactly one `rog5.netroot=1`;
3. proves zero physical storage and zero block-backed mounts;
4. arms the independent reset watchdog;
5. creates credential-free ACM diagnostics plus USB NCM;
6. configures the fixed point-to-point address;
7. mounts the exact NFS export read-only;
8. creates the tmpfs/OverlayFS merged root;
9. repeats the no-phone-storage check;
10. prepares `/run/initramfs` with the reviewed shutdown script, BusyBox, and
    its AArch64 musl loader;
11. moves `/dev`, `/proc`, `/sys`, and `/run`; and
12. executes the distribution's `/sbin/init`.

The target watchdog PID remains in `/run/rog5-network-root-watchdog.pid`.
During the first attended test it is disarmed only after the host verifies the
kernel, mounts, zero-storage state, network path, systemd target, and SSH.

## Live result

Four initial normal attempts crossed the NFS mount, OverlayFS, `switch_root`,
and systemd boundary, then reset at the same 16-second target uptime.
Diagnostic-mode boots and the rollback-guarded coldplug probe then established:

- `qcomtee` and the reviewed NVMEM, pinctrl, PON, regulator, RNG, ADC/thermal,
  stats, crypto, and SoC-info modules remain stable;
- `gpucc_sm8350` stalls during live probe and the watchdog resets the phone;
  and
- the enabled `rmtfs_mem` node overlaps the 4 MiB recovery ramoops reservation.

Network-root v2 disables RMTFS, GPUCC, GPU, GMU, and the Adreno SMMU in the
recovery DTB. Two boots with `ROG5_SYSTEMD_DIAGNOSTIC=0` then passed:

- exact kernel `7.1.4-g7a5cef0db479` with systemd as PID 1 and no
  `systemd.mask=` argument;
- running systemd, active `multi-user.target`, SSH and udev, successful
  unmasked udev-trigger/modules-load, zero failed units, and no fatal kernel
  signature;
- OverlayFS `/`, exact NFSv4.2 lower at `169.254.77.1:/` read-only, and a
  2 GiB `nodev,nosuid` tmpfs state layer;
- zero physical block devices and zero block-backed mounts;
- exact USB NCM address/carrier and a sustained full module-tree NFS read;
- five disabled live DT nodes, with `gpucc_sm8350` and `rmtfs_mem` absent;
- 33 sane thermal zones and about 10.4 GiB available memory; and
- successful watchdog disarm only after every acceptance gate.

ICMP to the host is expected to fail because the USB interface is in the
drop-by-default zone and only NFS is allowed to the host. SSH and sustained
NFS traffic passed. The full evidence and exact artifact identities are in
the [v2 live report](../test-results/2026-07-24-network-root-v2-live.md).

Network-root v3 retains the minimal shutdown environment that v2 lacked. Its
normal live boot repeated the accepted coldplug, storage, NFS, SSH, thermal,
and fatal-log gates. The retained exitrd matched the reviewed source,
executed in an AArch64 chroot, and remained executable at
`/run/initramfs/shutdown`. After watchdog disarm,
`systemctl reboot --no-block` returned to persistent fallback in about
25 seconds. Strict fallback SSH and complete NFS/firewall/interface cleanup
passed. The [v3 report](../test-results/2026-07-24-network-root-v3-live.md)
records the reproducible artifact identities and live result.

Network-root v4 then isolated the PMK8350 RTC and power key. The target stayed
stable, but the raw RTC was near the Unix epoch and set Linux about 56 years
behind the host. V4 is rejected as a server-time source; no clock or RTC write
was attempted. V5 keeps RTC disabled and enables only the power key. Its true
diagnostic boot identified `qcom_pon` as the missing modular parent, passed the
independently watched module probe, and registered exactly one
`pmic_pwrkey`/`pm8941-pwrkey` input with `KEY_POWER` and wakeup enabled.
Systemd reboot with the module loaded returned to fallback with complete host
cleanup. A physical short press still needs an attended observation, so the
switch/IRQ path is pending. A later normal, unmasked v5 repeat passed ordinary
coldplug, a complete module-tree read, 37 C maximum temperature, the
repository watchdog-disarm helper, normal reboot, and complete cleanup. Its
protected 120-second event window received no confirmed press/release. See the
[PMIC input report](../test-results/2026-07-24-network-root-pmic-input-live.md).

## Trusted volatile time

V4 proved that the raw PMK8350 RTC cannot be trusted. V5 therefore keeps that
node disabled and never loads or writes an RTC device.
`sync-network-root-time.sh` provides the minimal temporary bootstrap for the
USB network-root tier:

```bash
ALLOW_NETWORK_ROOT_TIME_SYNC=1 \
SSH_KEY=/secure/path/network-root-client-key \
KNOWN_HOSTS=/secure/path/network-root-known-hosts \
scripts/host/sync-network-root-time.sh
```

The host tool refuses to run unless the host reports NTP synchronization, the
private key is not group/world-accessible, known-host checking is strict, and
the target passes exact normal-kernel, systemd, read-only NFS/OverlayFS,
zero-storage, USB, fatal-log, disabled-RTC, and armed-watchdog gates. It steps
only Linux `CLOCK_REALTIME` through GNU `date` when drift exceeds two seconds,
then requires convergence within three seconds and repeats the RTC, storage,
watchdog, USB, systemd, and fatal-log checks. It never invokes `hwclock`,
`timedatectl set-time`, a storage command, or a PMIC offset mechanism.

The live gate now passes. After a controlled ten-second volatile skew, the
tool measured a much larger 2,378,466-second boot-chain drift, reported
`changed=1`, converged inside the bounded host sampling interval, kept RTC and
storage absent, and left rollback armed. Normal reboot returned to exact
fallback with complete cleanup. Run it after the full target safety gate and
before watchdog disarm. Once Wi-Fi is accepted, normal authenticated NTP
should take over; the SSH bootstrap remains the recovery/network-root fallback.
See the
[live time-bootstrap report](../test-results/2026-07-25-network-root-time-bootstrap-live.md).

## Offline result

The v3 bundle passes its fourteen-file verifier:

- two fresh Linux 7.1.4 output volumes produced byte-identical config, raw and
  compressed Images, modules, and metadata;
- NFSv4.2, OverlayFS, tmpfs xattrs, ACM, and NCM are built in;
- SCSI, UFS, SCSI disk/BSG/RPMB, and the UFS/combo/PCIe/SuperSpeed QMP PHY
  paths are absent from the final config, with no UFS module in the archive;
- target and nested staging initramfs builds are byte-identical, contain the
  reviewed executable exitrd, and contain no authorization key, host key,
  machine identity, or private key;
- two clean ASUS wrapper builds and two header-v3/AVB repacks are
  byte-identical; and
- nested hashes, wrapper metadata, boot command line, recovery-DTB node
  semantics, and unsigned AVB footer all pass.

The signed 818,293,654-byte Arch Linux ARM input also re-verifies under the
pinned Arch Linux ARM key, and the Linux-native rootfs path preserves metadata
and executes the extracted userspace as `aarch64`. The final
2,007,186,653-byte archive was staged from a fresh volume with the exact
`7.1.4-g7a5cef0db479` modules, pinned A660 firmware, key-only SSH, and the
headless-first Plasma/server package set. Its SHA-256 is
`8711b34cf454a3f3eef04f12650ef0622ee575d80942e418e1c61f45679aa717`.
Re-extraction into a second clean volume passed the complete architecture,
ownership/mode/xattr, module, firmware, identity, networking, SSH, and desktop
contract. The archive contains only client authorization. Preparing an export
creates one deployment-local Ed25519 server host key outside the repository,
checks its private/public pair and modes, and pins `sshd` to that identity.

## Rootfs policy

Arch Linux ARM remains the primary target because the existing signed staging
workflow already covers the server, VPN/hotspot, and Plasma package set.
Debian is the fallback if an Arch-specific userspace blocker appears; the
kernel and initramfs transport are distribution-independent.

The first boot is deliberately headless:

- `multi-user.target`;
- key-only SSH;
- no Wi-Fi, hotspot, VPN, browser, KDE, GNOME, or GPU test;
- NetworkManager must leave `usb0` unmanaged so it cannot remove the address
  carrying its own NFS root;
- no `/etc/fstab` entry may name a block device, UUID, or PARTUUID;
- client authorization is persistent but contains no private client key; and
- the prepared root supplies one persistent server host identity, while
  machine identity remains volatile.

KDE Plasma is preferred over GNOME for the eventual GUI because the repository
already has a minimal Plasma/KRDP path and measured baseline. It is enabled
only after the headless boot, display, input, and GPU gates pass.

## Host boundary

The host export must be:

- read-only;
- restricted to the exact phone address;
- reachable only through the dedicated USB interface/firewall zone;
- absent from `/etc/exports`;
- enabled only for an attended test; and
- removed when the phone returns to fallback.

Installing `nfs-utils`, starting `nfs-server`, or changing the runtime firewall
is an external service setup and requires user confirmation. Offline kernel,
initramfs, rootfs, and preflight work does not.

The offline host implementation now passes
`scripts/host/test-network-root-host.sh`. After confirmation,
`prepare-network-root-export.sh` authenticates the exact archive, extracts it
with ACL/xattr support into `/var/lib/rog5-network-root-v1`, seals its artifact
identity, and runs the independent path-based verifier.
`serve-network-root.sh` then:

1. refuses an existing NFS service, export, kernel server, unexpected root,
   or an in-use/non-drop firewall boundary;
2. creates only runtime firewalld rules and blocks the NFS and fixed mountd
   ports in every previously active zone;
3. binds NFSv4.2/TCP only to `169.254.77.1`;
4. exports a read-only bind mount only to `169.254.77.2`, using
   `no_root_squash` because PID 1 and root-owned key files must remain
   readable;
5. recognizes only the `ROG5_network_root` CDC-NCM gadget and gives it the
   `/30` host address in the verified-unused built-in `drop` zone; and
6. unexports, stops its private server processes, unmounts, restores the
   temporary sysctl, and removes all runtime firewall state on exit, including
   the interface assignment when the USB gadget has already disappeared.

The server accepts exactly two source directories: the accepted general
`/var/lib/rog5-network-root-v1` export and the independently verified
`/var/lib/rog5-network-root-adreno-smmu-v19` diagnostic sibling. The latter is
a copy-on-write derivative with the same 1,008-file Linux
`7.1.4-g7a5cef0db479` module tree and credentials, but with all three
hash-pinned A660 firmware files absent. The source-locked A660 registration
export, the consumed v18 sibling, and every other path are rejected before NFS
or firewall setup.
`prepare-adreno-smmu-export.sh` creates the sibling only when absent, and
`verify-adreno-smmu-export.sh` independently compares it with the accepted
base before `serve-network-root.sh` may expose it.

The default attended window remains 900 seconds. An explicitly requested
long-running diagnostic may set `ROG5_NFS_TIMEOUT` up to 86400 seconds. The
phone must return to fallback with the validated attended procedure before
that deadline: removing NFS while it is the live lower root would strand
userspace. V3 has one passing normal mainline reboot through its retained
exitrd. This PC-backed root remains an attended bring-up transport, not the
final independent storage design.

After explicit approval, the Nobara host installed `nfs-utils`, prepared and
reverified the fixed export root, and passed the privileged runtime gate. The
server exposed one TCP listener at `169.254.77.1:2049`; the system
`nfs-server`, rpcbind, and gssproxy units remained inactive; the export was
NFSv4.2-only, read-only, and restricted to `169.254.77.2`; and no permanent
firewall rule was created. The private server uses the minimum supported
10-second NFSv4 grace/lease and reports ready only after the kernel ends grace,
so protected-file opens cannot race startup. An isolated namespace using the
exact `/30` peer mounted the export read-only, matched `/etc/os-release`, and
found the exact `7.1.4-g7a5cef0db479` module tree. Cleanup removed every
runtime export, listener, mount, sysctl, rule, interface, and namespace.

## Acceptance gate

Before any live attempt:

1. two clean kernel builds must be byte-identical — **passed**;
2. two initramfs builds must be byte-identical and credential-free — **passed**;
3. the final kernel config must prove built-in NFS/OverlayFS and absent UFS —
   **passed**;
4. the reused recovery DTB hash and disabled-node contract must pass —
   **passed**;
5. the staged rootfs must pass architecture, systemd, module, SSH, network,
   fstab, identity, secret, and archive round-trip checks — **passed**; and
6. host NFS/firewall preflight must pass without broad network exposure —
   **offline contract and privileged runtime mount passed**.

Live acceptance requires exact kernel release, OverlayFS `/`, read-only NFS
lower, tmpfs upper, zero physical block devices, zero block-backed mounts,
`multi-user.target`, key-only SSH, stable USB traffic, no fatal kernel log,
and a validated return to the exact fallback kernel. These gates pass twice
with normal coldplug. V3 also passes the executable retained-exitrd contract
and one normal systemd reboot to the exact fallback with complete host
cleanup. V4 records a safely rejected RTC result, while v5 passes the isolated
power-key dependency, diagnostic and normal registration, repeated reboot, and
cleanup gates; physical press observation remains pending. Failure leaves the
watchdog armed until all acceptance gates pass.

Network-root v7 adds only the three stock-owned ASUS RAM reservations and the
ADSP status change. Two clean builds and repacks are reproducible. Live PAS
metadata moved from the rejected stock-owned address `0xfe400000` to
`0xec000000`; both SCM layers returned zero and ADSP reached `running`.
After correcting the strict allowlist for the expected `qrtr` IPC core, the
same-tier repeat passed with zero power supplies, zero storage, stable
USB/NFS, clean logs, normal reboot, and complete cleanup.

Network-root v8 adds only the root PMIC GLINK compatible and uses the
battery-only diagnostic module. Source and live evidence proved that
`qrtr_smd` must bind the ADSP `IPCRTR` endpoint and `qcom_pd_mapper` must
provide the local SM8350 service-location metadata before PMIC GLINK can
become ready. Both modules are source-audited and hash-pinned. The corrected
guarded run exposed exactly three read-only SM8350 supplies, reported one
real aggregate battery snapshot, kept UCSI/alt-mode/Type-C and charging
thresholds absent, passed clean-log and zero-storage gates, then returned
through a normal systemd reboot with complete cleanup. Charging behavior and
control remain separate and unaccepted.

Network-root v9 enables only GPUCC while keeping GPU, GMU, the Adreno SMMU,
display, every remote processor, RTC, input, and storage disabled. Duplicate
kernel/module, DTB, initramfs, wrapper, and Android package builds matched.
The live trace completed MMIO mapping plus both existing PLL configuration
calls, then lost USB/SSH before clock/reset/GDSC registration returned. The
independent SysRq watchdog restored exact fallback and full host cleanup
passed. GPUCC remains rejected; disabled consumers do not remove the stall.
The next gate must instrument the built-in Qualcomm common-clock registration
sub-phases before another attended probe.

Network-root v10 adds that default-off common-clock trace, gated to the exact
SM8350 GPUCC compatible. Duplicate clean Linux builds, matching module
archives, ASUS wrappers, and Android packages were byte-identical. The live
trace completed power-domain attachment, reset registration, both GDSC steps,
and protected-clock handling. It stopped after
`clock-regmap-register-begin index=0`, before the matching completion marker.
Binding and driver sources map index 0 to non-critical `gpu_cc_ahb_clk`; its
single parent is index 17 and has not registered yet, so CCF should initially
place the clock on the orphan list. This does not prove that its `0x1078`
branch register was accessed. The watchdog restored exact fallback, pstore
contained no record, and full cleanup passed. A narrower trace inside generic
CCF registration, plus stronger recovery from a lost idempotent ACM load
marker, is required before another attempt.

Network-root v11 passed that offline prerequisite. Its read-only,
default-off, exact-compatible trace brackets 63 generic CCF boundaries and 9
Qualcomm regmap-wrapper boundaries. Source contracts preserve the exact
single-call counts of the original registration, lock, runtime-PM, topology,
orphan, and debug operations. The 100 ms marker settles deliberately perturb
timing, including while the prepare lock is held, so this is diagnostic-only.
State-valued `ret` markers are not all errors, and the orphan-reparent bracket
does not prove direct GPUCC MMIO.

The fixed ACM load action may rediscover the endpoint and retry the identical
idempotent action once after a missing PASS marker; a second miss fails and
`execute` is never retried. Two clean Linux builds, module archives, ASUS
wrappers, staging initramfs files, and Android packages match byte-for-byte.
The target initramfs and DTB remain identical to v10, every GPU consumer stays
disabled, and the external BTF module and all 14 manifest artifacts are
hash-pinned.

The attended v11 probe completed 46 generic CCF markers through index-0
allocation, prepare-lock/runtime-PM, parent lookup, orphan insertion,
phase/duty/rate, and the non-critical branch. It stopped after
`orphan-reparent-begin` and before its matching completion. The source call
scans every CCF orphan while holding the prepare lock and can invoke callbacks
for clocks outside GPUCC, so the result does not prove GPUCC MMIO. The
independent watchdog restored exact fallback and full host cleanup passed.
V11 remains rejected for normal coldplug.

Network-root v12 added the required bounded trace without changing the original
orphan operations. Only the exact GPUCC-triggered registration scan emits
markers; provider-wide scans remain silent. The first four orphan entries
receive at most fourteen boundaries each around parent lookup,
before/after-parent callbacks, accuracy/rate recalculation, and requested-rate
assignment. At 100 ms per marker, the maximum added delay is 5.6 seconds and
the complete offline fixture leaves a 15-second forced-reset margin inside the
75-second watchdog. Source-order and mutation tests pass. Two clean Linux
builds, matching split-BTF modules, credential-free staging initramfs files,
ASUS wrappers, and Android packages are byte-identical. The GPUCC module
remains external, the target initramfs remains unchanged, and every consumer
remains disabled exactly as before.

The one attended v12 probe completed the `gpu_cc_ahb_clk` no-parent lookup and
scan, then entered `__clk_init_parent()` for the next orphan,
`disp_cc_mdss_pclk0_clk_src`, without reaching its completion marker. Source
maps that SM8350 clock to the display clock-controller's three-parent
`clk_pixel_ops` RCG. Its `get_parent()` callback precedes the generic cached
parent lookup, but v12 does not separate those operations and therefore does
not prove a specific register access. The independent watchdog restored exact
fallback and complete cleanup passed. V12 remains diagnostic-only. That live
result established the v13 requirement: a default-off inner-call trace with
duplicate offline builds before one further attended probe.

Network-root v13 passed that offline prerequisite. Six new markers record
parent shape and read-only provider runtime state, then separately bracket the
existing `get_parent()` callback and generic parent-cache lookup. Source and
mutation tests preserve exactly one callback and one cache lookup and reject
runtime-PM or hardware control. Together with v12, the four-entry trace has an
8-second maximum delay and leaves the required 15-second reset margin inside
the independent 75-second watchdog. Two network-isolated Linux builds,
credential-free staging initramfs files, independently prepared ASUS wrappers,
and corrected header-v3/AVB packages are byte-identical.

Its one attended probe completed the GPUCC orphan, recorded the existing
`disp_cc_mdss_pclk0_clk_src` provider as runtime-PM-enabled and suspended, and
entered its three-parent `get_parent()` callback. The callback-complete and
later CCF parent-cache markers never appeared. Source resolves the callback to
`clk_rcg2_get_parent()`, whose first substantive operation is a regmap read,
but v13 has no marker inside that function and does not prove the read began.
The independent watchdog restored exact fallback and complete host cleanup
passed.

GPUCC normal coldplug remains rejected. Network-root v14 passed the required
offline successor gate. Its mode-`0400`, default-off trace matches
only `disp_cc_mdss_pclk0_clk_src` and emits `parent-read-begin` and
`parent-read-complete` immediately around the one existing RCG regmap read.
Source and mutation tests preserve exactly one read and all original return
behavior while rejecting broad tracing, extra register accesses, runtime-PM
control, and hardware changes. The inherited orphan trace is reduced to the
two entries already localized by v13. Its 4.2-second maximum marker delay
preserves the 15-second forced-reset margin and leaves 5.8 seconds spare inside
the independent 75-second watchdog.

Two network-isolated Linux builds match through BTF, CCF/RCG2 objects, exported
symbols, modules, and metadata. Two credential-free staging initramfs files,
independently prepared ASUS wrappers, and header-v3/AVB packages are
byte-identical. The exact bundle verifier passes with the module and firmware
external, every GPU/display consumer disabled, and all three trace parameters
absent from the default boot command line.

Its one attended zero-storage probe emitted `parent-read-begin` after entering
the runtime-suspended DISPCC orphan's callback, but never emitted
`parent-read-complete`. The independent watchdog restored exact fallback and
complete host cleanup passed. This places the non-returning boundary inside
the existing regmap call, but does not prove that the fault is an MMIO
transaction rather than an interconnect, regmap-lock, or provider-state
interaction. V14 must not be rerun. A provider runtime resume cannot simply
be inserted in the global orphan scan because it runs under CCF's
`prepare_lock` and a provider resume callback may need that lock.

Network-root v15 passes the complete offline gate for an experimental partial
backport of the unmerged March 2025 CCF runtime-PM RFC. Its exhaustive lock
model makes the old and get-beneath-lock orders deadlock, while the candidate
core and both OF-provider paths have no modeled deadlock or reference leak.
Red/green source, integration, mutation, exact-patch, and clock KUnit tests
pass. The candidate acquires generic all-provider runtime-PM references before
`prepare_lock`, preserves each orphan scan, unlocks, and then releases the
references. It adds no device-specific resume, RCG/regmap change, forced
parent, skipped orphan, DT change, or consumer.

Two clean mainline builds match through BTF, symbols, CCF/QCOM objects,
modules, and metadata. Two credential-free staging archives, independently
prepared ASUS wrappers, and header-v3/AVB packages also match byte-for-byte.
The exported ABI, full module archive, GPUCC module, and RCG2 object are
unchanged from v14.

V15's one attended RAM-only probe made the display provider active, completed
7/7 observed RCG reads, and completed common-clock registration indexes 0
through 6 before entering index 7. Its 552 CCF markers arrived continuously
for 73.901 seconds with no gap over 0.116 seconds; the 75-second watchdog then
reset at `consumer-allocation-complete`. This supports trace-budget exhaustion
rather than a new source stall, but does not accept full GPUCC registration.
Exact fallback, zero retained pstore/fatal evidence, and complete host cleanup
passed. V15 must not be rerun; an offline-verified trace-free v16 confirmation
is next.

V16 now passes that complete offline gate while reusing the exact v15
kernel/module/DTB/initramfs/wrapper/package manifest. The fixed confirmation
load action omits all three high-volume trace flags. Before the independent
watchdog is armed, a hash-pinned read-only baseline requires the initial
watchdog to remain armed and proves each built-in parameter has command-line
count zero, mode `0400`, and value `N`, with zero storage and every consumer
isolated. Only the delay-free outer GPUCC trace remains. Red/green semantic
and mutation tests, baseline source checks, existing probe safeguards, nine
ACM transport tests, and the complete nested exact-bundle verifier pass.

The attended v16 cycle never reached this target. The trace-free load passed,
but a 284-second operator gap exceeded the independent 180-second staging
watchdog. A missing kexec guard and a later recovery-identity stability check
both failed before serial execute. The exact target link never appeared;
fallback and complete host cleanup passed. V16 is consumed.

V17 keeps the same image and target checks but adds one compound
`confirm-gpucc` ACM mode. Both safety guards are checked before discovery;
the same process then performs trace-free load and immediately calls the
existing non-retryable execute path. A missing load marker may still replay
only the identical load once, and any load failure makes execute unreachable.
Twelve ACM tests, semantic/mutation rejection, and the complete exact v17
bundle verifier pass. See the
[v16 staging-only report](../test-results/2026-07-26-network-root-gpucc-confirmation-live.md)
and
[v17 offline report](../test-results/2026-07-26-network-root-gpucc-atomic-confirmation-offline.md).
The one-shot live v17 gate also passes. Exactly one execute entered the
trace-free Linux 7.1 target; all eight outer GPUCC markers returned through
`registration-complete ret=0`, one platform device remained bound for the
required 30 seconds, and the independent watchdog was safely disarmed. GPU,
GMU, Adreno SMMU, render nodes, and storage stayed absent, and no new warning
or fault appeared. Normal systemd reboot restored exact fallback and complete
host cleanup. The result accepts only the GPUCC/CCF foundation; see the
[v17 live report](../test-results/2026-07-26-network-root-gpucc-atomic-confirmation-live.md).

V18 keeps that accepted GPUCC module and enables only its smallest reviewed
consumer, the built-in Adreno SMMU. Its pinned source audit, two-status DT
overlay, credential-free nested stage, clean duplicate builds, baseline,
guarded probe, mutation suite, and exact bundle verifier pass offline. Its one
attended compound gate stopped safely in the read-only baseline because
`fault` matched inside the normal word `Default`. No watchdog was disarmed,
GPUCC was not loaded, the SMMU remained unbound, and exact fallback plus host
cleanup passed. V18 is consumed and cannot be served or retried.

V19 preserves the byte-identical v18 binary and corrects only the external
detectors, source locks, export seal, and allowlist. Regression tests reject
the benign `Default`, `dynamic_debug`, and `panic:1` inputs while accepting
real token-delimited IOMMU and fatal signatures. Its independently verified
v19 export preserves the complete module tree and credentials, contains zero
A660 firmware, and leaves the accepted base unchanged. The target launcher
still runs the baseline under the original watchdog, overlaps a 120-second
transition watchdog across disarm and one 75-second probe, and requests
immediate fallback. The inert host entry point is
`run-adreno-smmu-live-gate.sh`; it requires both explicit guards and new
private evidence. See the
[v18 offline report](../test-results/2026-07-26-network-root-adreno-smmu-offline.md)
and
[v18 safe-rejection/v19 correction report](../test-results/2026-07-26-network-root-adreno-smmu-v18-live-rejected.md).

See the [redacted v3 live report](../test-results/2026-07-24-network-root-v3-live.md)
for the exact artifact identities, retained-exitrd proof, normal-reboot
timeline, SSH persistence, and cleanup result. See the
[PMIC input report](../test-results/2026-07-24-network-root-pmic-input-live.md)
for the v4 RTC rejection and v5 power-key evidence, and the
[ADSP report](../test-results/2026-07-25-network-root-adsp-live.md) for the v7
memory-contract diagnosis and live prerequisite. The
[battery telemetry report](../test-results/2026-07-25-network-root-battery-telemetry-live.md)
records the v8 dependency diagnosis, live values, watchdog handling, and
rollback. The
[GPUCC diagnostic report](../test-results/2026-07-25-network-root-gpucc-diagnostic-live.md)
records the reproducible v9 candidate, live phase boundary, watchdog rollback,
and first common-clock instrumentation gate. The
[GPUCC common-clock report](../test-results/2026-07-25-network-root-gpucc-common-diagnostic-live.md)
records the reproducible v10 candidate, exact index-0 localization,
source-bounded interpretation, rollback, cleanup, and next CCF trace gate.
The
[GPUCC generic-CCF offline report](../test-results/2026-07-25-network-root-gpucc-ccf-diagnostic-offline.md)
records the reproducible v11 implementation. The
[GPUCC generic-CCF live report](../test-results/2026-07-25-network-root-gpucc-ccf-diagnostic-live.md)
records its exact orphan-scan boundary, rollback, cleanup, and v12 gate. The
[GPUCC per-orphan offline report](../test-results/2026-07-25-network-root-gpucc-orphan-diagnostic-offline.md)
records the accepted v12 source, timing, reproducibility, and bundle gates.
The
[GPUCC per-orphan live report](../test-results/2026-07-25-network-root-gpucc-orphan-diagnostic-live.md)
records the ordered two-orphan boundary, source interpretation, rollback,
cleanup, and v13 gate. The
[GPUCC inner-parent offline report](../test-results/2026-07-25-network-root-gpucc-parent-diagnostic-offline.md)
records the accepted v13 source, timing, reproducibility, and bundle gates.
The
[GPUCC inner-parent live report](../test-results/2026-07-25-network-root-gpucc-parent-diagnostic-live.md)
records the callback boundary, runtime-state interpretation, source and
lock-order limits, rollback, and cleanup. The
[GPUCC RCG parent-read offline report](../test-results/2026-07-25-network-root-gpucc-rcg2-diagnostic-offline.md)
records the accepted v14 source boundary, 4.2-second timing cap, duplicate
build/package paths, exact hashes, and complete offline acceptance. The
[GPUCC RCG parent-read live report](../test-results/2026-07-25-network-root-gpucc-rcg2-diagnostic-live.md)
records the regmap-call boundary, watchdog rollback, exact fallback, and
complete host cleanup. The
[GPUCC runtime-PM candidate offline report](../test-results/2026-07-25-network-root-gpucc-runtime-pm-candidate-offline.md)
records its model, tests, reproducibility, exact identities, residual risk,
and one-shot live gate. The
[GPUCC runtime-PM candidate live report](../test-results/2026-07-25-network-root-gpucc-runtime-pm-candidate-live.md)
records the completed DISPCC reads, later GPUCC progress, continuous
trace-budget exhaustion, rollback, cleanup, and v16 gate. The
[GPUCC trace-free confirmation offline report](../test-results/2026-07-25-network-root-gpucc-confirmation-offline.md)
records its unchanged artifacts, fail-closed transport/probe, tests, and
one-shot acceptance criteria. The
[v16 staging-only report](../test-results/2026-07-26-network-root-gpucc-confirmation-live.md)
records the no-execute rollback and cleanup. The
[v17 atomic confirmation offline report](../test-results/2026-07-26-network-root-gpucc-atomic-confirmation-offline.md)
records the guard-first transport and unchanged target gates. The
[v17 atomic confirmation live report](../test-results/2026-07-26-network-root-gpucc-atomic-confirmation-live.md)
records complete trace-free GPUCC registration, one-device stability, normal
reboot, exact fallback, cleanup, and the next isolated Adreno dependency gate.
The
[v18 Adreno SMMU offline report](../test-results/2026-07-26-network-root-adreno-smmu-offline.md)
records the pinned source graph, consumer-disabled DT and probe contracts,
duplicate wrapper/repack evidence, exact identities, and one-shot live gate.
