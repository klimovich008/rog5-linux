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
   temporary sysctl, and removes all runtime firewall state on exit.

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

See the [redacted v3 live report](../test-results/2026-07-24-network-root-v3-live.md)
for the exact artifact identities, retained-exitrd proof, normal-reboot
timeline, SSH persistence, and cleanup result. See the
[PMIC input report](../test-results/2026-07-24-network-root-pmic-input-live.md)
for the v4 RTC rejection and v5 power-key evidence, and the
[ADSP report](../test-results/2026-07-25-network-root-adsp-live.md) for the v7
memory-contract diagnosis and live prerequisite. The
[battery telemetry report](../test-results/2026-07-25-network-root-battery-telemetry-live.md)
records the v8 dependency diagnosis, live values, watchdog handling, and
rollback.
