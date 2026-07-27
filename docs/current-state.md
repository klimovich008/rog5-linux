# Current state — 2026-07-27

## Hardware and boot

- Device: ASUS ROG Phone 5, codename `anakin`, SM8350 / Snapdragon 888, Adreno 660.
- Bootloader: unlocked; verified boot reports orange.
- Active Android slot during the recorded tests: slot B.
- Stable 5.4 baseline userspace: Alpine 3.24 on the userdata-backed root filesystem.
- Target userspace: Arch Linux ARM with systemd and minimal Plasma. The locked
  archive contains the exact accepted network-root modules, pinned firmware,
  and key-only SSH; its Linux-native stage and clean archive round trip pass.
  A newer offline-verified development archive adds a locked automation
  account without replacing the live-tested root.
- Stable experimental kernel: `5.4.210-qgki-perf #20`.
- Current persistent fallback boot: `5.4.134-qgki-perf-00001-g6c308144c23e`;
  this is older than the separately proven temporary 5.4.210 artifact.
- Boot method: temporary `fastboot boot`; the experimental kernel has not been flashed.

## Passing baseline

The 5.4.210 #20 smoke test currently passes:

- UFS root and initramfs startup
- USB NCM and SSH at the private debug address
- DSI DRM connector and panel backlight
- FocalTech touch input
- ADSP startup and the real Qualcomm battery charger driver
- native UPower battery reporting
- Plasma Mobile on the physical panel using software rendering
- power-button screen toggle and default OLED blanking
- Wi-Fi client and AP/hotspot after delayed radio startup
- modem stability with supervised `rmtfs` and patched `tqftpserv`

At the last baseline capture the battery was full, the panel backlight was zero, zram was 3 GiB and unused, and the server remained reachable with the physical screen off. The screen toggle now applies Wayland DPMS as well as backlight zero, and restores DPMS plus the saved brightness on wake.

The mainline userspace VPN-hotspot policy also has packet-level offline
evidence. A network-disabled privileged container permits only the simulated
VPN path, blocks one-way IPv4/IPv6 ordinary-uplink leakage, blocks unsolicited
VPN-side client ingress, stays closed when the VPN interface disappears, and
restores nftables/sysctls on cleanup. The real ath11k AP, WireGuard handshake,
DHCP/DNS, coexistence, throughput, thermal, and battery gates remain pending.

## Display modes

The vendor DRM connector publishes these mode names:

```text
1080x2448x144x150024cmd
1080x2448x120x150003cmd
1080x2448x90x150007cmd
1080x2448x60x138333cmd
```

The mode names encode the intended 144/120/90/60 Hz panel profiles. Generic `modetest` calculates misleading refresh values because the vendor command-mode timings are not conventional desktop timings. The connector capability blob explicitly reports no qsync, dynamic FPS, or dynamic bit-clock support, so the safe UI is a fixed-mode selector. The low-power default should be 60 Hz; 90 Hz is the balanced interactive profile; 120/144 Hz should be opt-in.

The live KScreen mapping is verified as 144 -> ID 1, 120 -> ID 2, 90 -> ID 3, and 60 -> ID 4. The current default is the 60 Hz server profile with DPMS off.

## GPU blocker

The extracted A660 firmware loads and Mesa 26.1.1 Turnip can identify `Turnip Adreno (TM) 660` on a fresh boot. It is not stable.

Reproducer:

1. First raw `O_RDWR` open of `/dev/kgsl-3d0` succeeds.
2. Close it.
3. A second raw open fails with `ETIMEDOUT`.
4. Kernel log reports GMU HFI error `115 902 PwrLimitsExitIdl` and a CP read-translation page fault at a varying low address.

The same failure occurs on 5.4.134 and 5.4.210 #20. It remains with ACD, BCL, and IFPC disabled and with rail/clock/bus/no-nap debug forces enabled. This proves the current blocker is the vendor KGSL/GMU open/idle transition, not KDE, Zink, Xvnc, or a Turnip command submission.

GPU tests are intentionally a separate opt-in tier because the failure poisons KGSL until reboot.

## Desktop and RAM

- Plasma Mobile, Plasma Desktop, Plasma NetworkManager, Discover, and the Alpine APK backend are installed.
- The physical session currently forces Qt Quick and OpenGL software rendering.
- noVNC/Xvnc is also a software path and should remain an emergency/admin interface, not the GPU validation target.
- Repaired localhost-only remote-session launchers are installed. On the
  persistent Alpine 3.24 fallback, nested KWin Wayland, Plasma, Chromium CDP,
  ttyd, and noVNC passed a live visual and endpoint check while the physical
  panel state remained off with backlight zero. See the
  [live report](../test-results/2026-07-27-alpine-remote-gui-linux-tunnel-live.md).
- The Nobara host now runs an enabled reconnecting user service with four
  loopback-only SSH forwards. An induced main-process exit incremented the
  restart counter, recreated the tunnel, reran the idempotent desktop
  launcher, and restored all tested endpoints.
- The live desktop checkpoint retained about 10.2 GiB available memory and
  used zero swap. An earlier same-boot before/after observation put the
  incremental nested desktop/browser cost at roughly 264 MiB; full idle-power
  and per-process PSS measurement remains pending.
- Recorded memory usage was about 0.85 GiB without the full physical UI and about 1.4 GiB with Plasma Mobile, radio services, and caches active. The device has roughly 11 GiB usable RAM, so reliability and idle power matter more than aggressive memory trimming.

## Known operational constraints

- Radio startup is delayed to avoid a low-battery boot power spike.
- The current vendor kernel has BPF and uprobes but no `/sys/kernel/btf/vmlinux`; GodShell cannot run its CO-RE eBPF programs on this baseline.
- The boot image is not persistent. Any normal reboot returns to the installed fallback kernel.
- PC cross-compilation is active on Nobara Linux under rootless Podman. Linux
  7.1.4 and the ASUS-source 5.4.210 kexec staging kernel both compile
  reproducibly with container networking disabled.
- The connected fallback system enumerates as USB gadget `1d6b:0104` and
  `/dev/ttyACM0`. Android platform tools 35.0.2 are installed and the user is
  configured in `dialout`; the current desktop login includes the
  supplementary group.
- An autoconnecting, never-default host-only USB profile at
  `169.254.77.1/16` reaches the
  fallback server at `169.254.77.2`; the network-root target uses an isolated
  `169.254.77.1/30` link. After explicit approval, the dedicated public key
  was added to the persistent fallback authorization file while preserving a
  backup. Key-only fallback login passed across a full reboot. Its private
  half remains mode 0600 outside the repository.
- Credentials and private identifiers are deliberately excluded from this repository.

## Mainline recovery status

The historical header-v3 v2 image temporarily booted and produced staging and
target logs. Those logs include Linux 7.1.4 entering `/init`, mounting
configfs, configuring NCM and ACM, binding the `a600000` UDC, creating `usb0`,
and later returning through rollback. Ramoops from that run also supported the
TLMM GPIO 52-59 reservation and built-in Qualcomm SNPS FEMTO USB2 PHY changes.
These remain useful historical observations, not a passing recovery gate.

A later live and artifact audit found that the v2 staging `/` was a writable
physical UFS filesystem. Its target DTB also enabled the UFS controller, UFS
PHY, and QMP/SuperSpeed PHY. The earlier “zero storage mounts” and USB2-only
claims were therefore false. Nothing was flashed, but every v2 boot artifact
is superseded and must not be booted again.

The later v6 candidate embedded the staging initramfs in the ASUS 5.4 kernel
and carried a USB2-only target DTB with UFS, QMP/SuperSpeed, and the secondary
USB controller disabled. It passed its then-current offline suite, but live
ACM data and automatic rollback failed. Later source fixes supervise ACM and
use repeated forced-reboot fallback.

Recovery v12 was rebuilt reproducibly but remained unbooted after a final
safety audit found that it did not lock block devices before USB exposure.
Recovery v13 added an all-block-device `BLKROSET` gate and passed duplicate
offline builds. Its first `fastboot boot` transfer succeeded, but the exact
recovery USB identity never appeared; the known fallback gadget returned 21
seconds after fastboot disconnected. No intervening recovery USB product was
recorded, no image was flashed, and kexec was not attempted. V13 is rejected.

Recovery v14 retains the pre-USB rejection of any block-backed mount but locks
only physical disks and their partitions. This covers seven fallback-visible
UFS LUNs and 109 partitions while excluding 33 volatile loop, RAM, and zram
objects. Both initramfs layers, two fresh ASUS wrapper builds, and two
header-v3/AVB repacks are byte-identical. The expanded `acm-only` verifier
passes, and the host now requires exact product `ROG5_recovery` rather than
accepting the shared vendor/product ID. Its live attempt still returned to
fallback after the same 21-second interval, so v14 is rejected and no live
recovery gate is accepted.

Recovery v15 is a reproducible diagnostic-only image. It keeps USB closed on
failure and adds 10/30/50-second rollback delays for PM wake-lock failure,
block-backed mount detection, and physical-device lock failure respectively.
Its live temporary boot returned to fallback in exactly 31 seconds, proving
that `/init` ran and the wake-lock branch failed before storage isolation.
Kexec was not loaded or executed.

Recovery v16 removes the wake-lock gate and timing-only delays. The wrapper
configuration has `CONFIG_PM_AUTOSLEEP` disabled, and the initramfs has no
userspace power manager, so no automatic suspend path needs that lock. The
forced-reboot watchdog, block-backed-mount rejection, physical-device
`BLKROSET` verification, USB-closed failure paths, and exact host identity
check remain. V16 reached exact recovery USB, working NCM, and automatic
rollback to a changed fallback boot, but ACM returned no bytes.

The separately authorized local v17 SSH diagnostic proved a RAM-backed
`rootfs`, zero block-backed mounts, 116 physical disks/partitions read-only,
and live watchdog/ACM supervisor processes. Its configfs ACM function exposed
`/sys/class/tty/ttyGS0`, but `/dev/ttyGS0` was absent. A live RAM-only
`mdev -s` created the node and the supervised ACM shell worked immediately.
The diagnostic then rolled back automatically; it was never published and
kexec was not attempted.

Recovery v18 adds that explicit rescan, requires the character node, and
repeats storage isolation before ACM or UDC binding. Both initramfs layers,
two independent ASUS wrapper builds, and two boot-image repacks are
byte-identical; the strengthened network-isolated verifier passes. Two live
credential-free staging/rollback cycles also pass: both reported RAM root,
zero block mounts, 116 read-only physical nodes with zero failures, live
watchdog/ACM, no authorization or SSH, configured NCM, and automatic return to
a changed fallback boot identity. A subsequent attended kexec loaded the
hash-verified payload and booted `7.1.4-g7a5cef0db479`. The target again passed
RAM root, zero block mounts, zero physical block devices, watchdog/ACM/NCM,
no-credential/no-SSH, and zero fatal-log-signature checks before automatically
returning to a changed fallback boot identity. The next gate is read-only UFS
discovery.

The read-only UFS discovery v1 bundle passed its complete offline gate and
then safely reached Linux `7.1.4-g44fd886a77b8` through temporary boot and
kexec. It enumerated 7 UFS disks and 109 partitions with all 116 physical
nodes independently read-only, a RAM root, zero block-backed mounts, the
Qualcomm host bound, and recovery USB/watchdog services live. The live gate
was rejected because runtime PM attempted three auto-BKOPS `SET_FLAG`
queries. The compile-time command gate blocked every query, but the resulting
UFS fatal-recovery state also stalled orderly reboot. An authorized SysRq
reset returned the phone to the exact fallback kernel; no storage was mounted,
written, or flashed.

The three-patch replacement source at commit `cfd385a1c754` / tree
`d2f03d205522` retains the UFS runtime reference, forbids host and WLUN
runtime PM, disables auto-hibern8, and returns before discovery suspend or
shutdown transitions. The target also requires the active-link markers and
zero blocked query/SCSI commands twice before USB binding. Rollback now arms
an independent five-second emergency SysRq reset before starting orderly
forced reboot in the background, fixing the v1 watchdog wait deadlock. Two
clean mainline builds, both initramfs layers, the reviewed DTB, two clean ASUS
wrapper builds, and two header-v3/AVB repacks are byte-identical. The exact v2
thirteen-file manifest passes the complete network-isolated verifier.

The attended v2 temporary boot now passes. Exact
`7.1.4-gcfd385a1c754` exposed 7 UFS disks and 109 partitions; all 116 nodes
were independently read-only with zero block-backed mounts and a complete
117-line sysfs inventory. Auto-hibern8 was zero, the host remained active with
runtime PM forbidden, blocked query/SCSI counts were zero, and no BKOPS,
error-handler, or fatal signature appeared. The untouched watchdog chain
automatically returned the phone to the exact fallback kernel with a changed
boot identity. Nothing was flashed. Read-only UFS discovery is accepted; the
next gate is a minimal Arch/Debian root served over USB NCM while UFS remains
unmounted.

The network-root gate now passes its offline and live headless boundaries.
Two clean Linux 7.1.4 builds are byte-identical with NFSv4.2/OverlayFS built
in and SCSI/UFS plus the related QMP storage/SuperSpeed paths compiled out.
Two target initramfs builds, two nested credential-free staging archives, two
clean ASUS wrappers, and two header-v3/AVB repacks are also byte-identical.
The fourteen-file manifest passes nested hash, config, no-credential,
boot-header, and AVB verification. The signed Arch Linux ARM base was
reverified under the pinned signing key, and its metadata-preserving Linux
staging path executes as AArch64. The final 2,007,186,653-byte Plasma/server
archive passes a clean round trip with the exact modules and pinned firmware.

The newer 2,007,027,068-byte resource-bounded, agent-isolated development
archive has SHA-256
`5863cacf23a9c0cb972b37e3c71f801df77ccb708a277c0f2787d3afd9ac51e4`.
Its full verifier passes both before archival and after extraction into a
clean volume. The locked `rog5-agent` system account has no login, SSH access,
supplementary group, credential, or desktop-user data; its on-demand Chromium
service is loopback-only, systemd-hardened, capped at two CPUs/2 GiB
RAM/512 MiB swap/256 tasks, and restart-limited. A staged redacted collector
can capture the later headless/desktop/browser/screen-off comparison without
network or device identifiers. This artifact remains outside Git and has not
been promoted to the NFS export or booted.

The runtime-only host export implementation now passes its static safety test
and the final archive passes a second disposable extraction through the
independent export-root verifier. It binds the future server to the USB
address, isolates the exact gadget in the verified-unused built-in `drop`
zone, blocks the same ports in the host's broad workstation zone, and cleans
up on exit.

After explicit approval, `nfs-utils` was installed through PolicyKit and the
archive was prepared at `/var/lib/rog5-network-root-v1`. The privileged host
gate then passed with one `169.254.77.1:2049` TCP listener, NFSv4.2 only, one
read-only export to `169.254.77.2`, inactive system NFS/rpcbind services, no
permanent firewall rule, and a successful isolated `/30` client mount of the
exact Arch root. Attended shutdown removed the export, listener, mounts,
kernel NFS filesystem, temporary sysctl, firewall rules, and test namespace;
the fallback USB link was restored.

Four initial normal Arch boots mounted NFS, created OverlayFS, completed
`switch_root`, and entered systemd, then reset at the same 16-second target
uptime. Diagnostic boots and the attended coldplug probe isolated two recovery
DT hazards: `gpucc_sm8350` stalls during live clock-controller probe, and the
enabled `rmtfs_mem` reserved-memory node overlaps the recovery ramoops span.

Network-root v2 disables RMTFS, GPUCC, GPU, GMU, and the Adreno SMMU. Its DTB,
nested initramfs, ASUS wrapper, and header-v3/AVB image reproduce
byte-for-byte and pass the expanded semantic verifier. Two normal boots with
no systemd masks now pass exact Linux `7.1.4-g7a5cef0db479`, running systemd,
successful udev-trigger/modules-load, active `multi-user.target` and SSH,
OverlayFS `/`, read-only NFSv4.2 lower, 2 GiB tmpfs state, zero physical block
devices, zero block-backed mounts, stable USB/NFS reads, 33 sane thermal
zones, zero failed units, and zero fatal signatures. Each rollback watchdog
was disarmed only after all gates. Nothing was flashed.

The dedicated client key remains outside the repository at mode 0600. Its
public half is authorized for root and `rog5`, and the persistent fallback
also passes strict key-only login after reset. Root preparation now creates a
deployment-local Ed25519 server host key outside Git and pins `sshd` to that
single identity. The same client authorization and server identity passed on
two separate native-Linux boots.

The v2 normal `systemctl reboot` test removed the gadget but did not return to
fallback, Fastboot, or ADB within 120 seconds. A forced double reboot returned
in about 21 seconds, isolating the defect to userspace teardown rather than the
kernel restart path. V3 fixes that boundary by preparing `/run/initramfs`
before `switch_root` and retaining BusyBox, its AArch64 musl loader, and a
reviewed shutdown script. The exitrd moves the NFS lower and tmpfs state out
of the old root, unmounts OverlayFS first, then its backing filesystems.

The complete v3 bundle was reproduced twice and passed its fourteen-file
offline verifier. Its attended normal, unmasked Arch boot passed the prior
kernel, systemd, coldplug, storage, NFS, SSH, thermal, and fatal-log gates plus
the executable retained-exitrd contract. `systemctl reboot --no-block` then
removed the target gadget after about six seconds and returned the persistent
fallback after about 25 seconds. Strict fallback SSH passed, and the NFS
listener, export, bind mount, kernel threads, runtime firewall rules,
temporary sysctl, and `/30` interface state were all absent afterward.

The next isolated PMIC experiment was also reproduced twice. Network-root v4
enabled only the PMK8350 RTC and power key. Its normal live boot was stable,
but the raw RTC was near the Unix epoch and set Linux about 56 years behind
the host. V4 is rejected as a server-time source; no clock or RTC write was
attempted.

Network-root v5 retains only the power-key enablement and keeps RTC disabled.
Its true diagnostic boot proved that `qcom_pon` is the reviewed modular parent
for the built-in PM8941 input driver. The guarded probe registered exactly one
`pmic_pwrkey` event device with `KEY_POWER`, wakeup enabled, and the expected
PMK8350 compatible. Normal systemd reboot with the module loaded returned to
fallback and complete host cleanup passed. A physical short press was not
observed during the bounded attended windows, so switch/IRQ operation remains
pending rather than passed. A subsequent normal, unmasked v5 repeat passed
ordinary coldplug, a complete module-tree read, zero-storage/NFS/USB gates,
33 thermal zones at a 37 C maximum, the repository watchdog-disarm helper,
normal systemd reboot, strict fallback SSH, and complete cleanup. The protected
120-second low-level monitor received no confirmed press/release event. The
[PMIC input report](../test-results/2026-07-24-network-root-pmic-input-live.md)
records the reproducible artifacts and live evidence.

The phone is currently in persistent Alpine fallback. The attended NFS
listener, export, bind mount, runtime firewall changes, and temporary target
interface state are absent. The v3-v5 images remain attended RAM-only
development transports and must never be flashed. The same applies to every
v6-v8 ADSP/telemetry candidate. Display, charging, Wi-Fi,
and GPU hardware remain unaccepted separate tiers; one read-only mainline
battery snapshot now passes. Trusted time must currently be bootstrapped from
the host or network rather than the PMIC RTC.
The new `sync-network-root-time.sh` host tool now passes that live role. It
required host NTP synchronization, strict SSH, normal zero-storage
network-root, RTC disabled, and an armed rollback watchdog. It corrected a
measured 2,378,466-second drift through only the volatile Linux system clock,
passed an independent bounded comparison, then repeated the safety gates and
returned through normal reboot and complete cleanup. The
[time-bootstrap report](../test-results/2026-07-25-network-root-time-bootstrap-live.md)
records the evidence.

The mainline ADSP prerequisite now passes in network-root v7. Stock runtime
FDT and `/proc/iomem` evidence identified three missing ASUS-owned RAM spans:
`0xcbc00000+68 MiB`, `0xd8000000+8 MiB` (`no-map`), and
`0xedc00000+288 MiB`. Before that correction, PAS metadata landed at
`0xfe400000` inside the high stock-owned span and secure firmware returned
`-EINVAL`. With the exact reservations present, metadata moved to
`0xec000000`; both PAS layers returned zero and ADSP reached `running`.

The first corrected boot was deliberately rolled back after the strict module
allowlist omitted the expected `qrtr` IPC core. After requiring `qrtr` absent
before startup and present afterward, a same-tier repeat passed its settle,
module, USB/NFS, zero-storage, zero-power-supply, systemd, and log gates.
Normal reboot restored exact Alpine fallback and complete host cleanup. The
[ADSP live report](../test-results/2026-07-25-network-root-adsp-live.md)
records the reproducible bundle, memory diagnosis, both guarded runs, and
remaining boundary.

Network-root v8 now passes the separate read-only battery gate. The first run
registered the exact supplies but remained `EAGAIN`; source review proved
that Linux 7.1 already contains QRTR name service and that the missing pieces
were the `IPCRTR` transport plus the local SM8350 PD mapper. Both modules were
source-audited and hash-pinned. A second guarded run safely rejected an
incorrect unprefixed auxiliary-driver sysfs assertion before PMIC GLINK
loaded. After the live-informed correction and a 31-test pass, the final run
kept ADSP running and read 84%, 8.255 V, 81 mA, 30.3 C, `Discharging`, USB
online, and wireless offline from exactly three read-only supplies. It
exposed zero Type-C devices or charging thresholds, retained zero storage and
clean logs, disarmed its watchdog only after every gate, and returned through
normal reboot with complete cleanup. The
[battery telemetry report](../test-results/2026-07-25-network-root-battery-telemetry-live.md)
records the reproducible inputs and all three guarded outcomes. Charging
behavior/control, dual-cell interpretation, and sustained current-direction
validation remain untested and disabled.

Network-root v9 retested GPUCC with only its clock-controller DT node enabled.
V10 added a read-only, default-off common-clock phase trace and rebuilt the
matching kernel/module set. Duplicate clean Linux builds, ASUS wrappers, and
Android repacks were byte-identical. GPU, GMU, Adreno SMMU, display, UFS, RTC,
input, and every remote processor remained disabled. The guarded v10 probe
completed MMIO mapping, both Lucid PLL configurations, reset registration,
both GDSC steps, and protected-clock handling, then stopped during regmap clock
index 0 registration. Sources map that index to non-critical
`gpu_cc_ahb_clk`, whose parent has not yet registered; ordinary CCF should
orphan it and should not invoke its branch enable operation. The evidence does
not prove a read or write at `0x1078`. The independent SysRq watchdog restored
the exact fallback, pstore retained no record, and complete
NFS/firewall/service cleanup passed. The
[GPUCC diagnostic report](../test-results/2026-07-25-network-root-gpucc-diagnostic-live.md)
records the v9 boundary. The
[GPUCC common-clock report](../test-results/2026-07-25-network-root-gpucc-common-diagnostic-live.md)
defines the required generic CCF instrumentation and ACM load-recovery gate.
Network-root v11 passed that offline gate and one attended RAM-only probe.
After a bounded replay of one lost idempotent staging-load marker, the one-shot
execute reached Linux 7.1 with zero storage. For index-0
`gpu_cc_ahb_clk`, CCF completed allocation, prepare-lock/runtime-PM, parent
lookup, orphan insertion, phase/duty/rate, and the non-critical branch. The
last marker was `orphan-reparent-begin`; its completion never arrived.
`topology-insert-complete ret=1` confirms orphan state rather than an error.
The generic scan can inspect and invoke callbacks for other orphan clocks, so
this does not prove GPUCC MMIO. The independent watchdog restored the exact
fallback and complete host cleanup passed. The
[v11 offline report](../test-results/2026-07-25-network-root-gpucc-ccf-diagnostic-offline.md)
records the exact build inputs and contracts; the
[v11 live report](../test-results/2026-07-25-network-root-gpucc-ccf-diagnostic-live.md)
records the exact phase boundary, rollback, cleanup, and required per-orphan
v12 trace.

Network-root v12 passed that complete offline prerequisite. Its
exact-device/default-off extension traces at most four orphan entries, with
fourteen boundaries per entry around parent lookup, before/after reparent
callbacks, accuracy/rate recalculation, and requested-rate assignment. The
maximum added marker delay is 5.6 seconds and the complete collection/reset
budget remains inside the independent 75-second watchdog. Source-order and
mutation contracts pass, two clean Linux builds match including BTF and the
modified CCF object, and two staging initramfs, ASUS wrapper, header-v3, and
AVB paths are byte-identical. The exported symbol table, GPUCC-only DTB, and
RAM-only target initramfs remain unchanged.

Its one attended probe completed parent lookup and scan completion for
`gpu_cc_ahb_clk`, then advanced to the second orphan,
`disp_cc_mdss_pclk0_clk_src`. The final marker brackets
`__clk_init_parent()` for that display clock. On SM8350 it is a three-parent
RCG using `clk_pixel_ops`; source order calls `clk_rcg2_get_parent()` before
the cached-parent lookup. V12 has no markers inside that function, so it does
not prove the callback, its regmap read, or the later lookup as the exact
non-returning operation. The independent watchdog restored the exact
fallback, zero pstore records remained, and complete NFS/firewall/service
cleanup passed.

The
[v12 offline report](../test-results/2026-07-25-network-root-gpucc-orphan-diagnostic-offline.md)
records the exact hashes and gates; the
[v12 live report](../test-results/2026-07-25-network-root-gpucc-orphan-diagnostic-live.md)
records the ordered orphan trace, source-bounded interpretation, rollback, and
cleanup.

Network-root v13 passed the complete offline successor gate. Its
default-off extension adds six exact-trigger markers for parent shape,
read-only provider runtime state, the existing display RCG `get_parent()`
callback, and CCF's parent-cache lookup. Contracts preserve one call to each
original operation and reject broad tracing, duplicate calls, runtime-PM
control, and hardware control. The four-orphan maximum adds at most 8 seconds;
the full 73-second fixture retains the 15-second forced-reset margin inside
the independent 75-second watchdog. Two network-isolated Linux builds match
through BTF, CCF objects, symbols, modules, and metadata. Two credential-free
staging archives, independently prepared ASUS wrappers, and corrected
header-v3/AVB packages also match byte-for-byte.

The
[v13 offline report](../test-results/2026-07-25-network-root-gpucc-parent-diagnostic-offline.md)
records exact hashes and every acceptance gate. Its one attended probe
completed the GPUCC orphan, recorded the three-parent DISPCC pixel-clock
provider runtime-suspended, and entered its `get_parent()` callback without
reaching the callback-complete or later parent-cache markers. The independent
watchdog restored exact fallback and complete cleanup passed.

The
[v13 live report](../test-results/2026-07-25-network-root-gpucc-parent-diagnostic-live.md)
records the ordered markers, runtime-state interpretation, source boundary,
rollback, and host audit. Source maps the callback to
`clk_rcg2_get_parent()`, but v13 does not prove that its regmap read began.
GPUCC remains rejected, and directly resuming DISPCC while the global CCF
prepare lock is held is not an acceptable shortcut.

Network-root v14 passed that complete offline prerequisite. Its
exact-clock, default-off, mode-`0400` core parameter adds only
`parent-read-begin` and `parent-read-complete` around the existing
`clk_rcg2_get_parent()` regmap read. Source, mutation, integration, and timing
tests preserve exactly one read and reject broad tracing, runtime-PM control,
and hardware control. Reducing the inherited orphan limit to the two already
localized entries caps marker delay at 4.2 seconds, retains the 15-second
forced-reset margin, and leaves 5.8 seconds spare inside the 75-second
watchdog.

Two network-isolated Linux builds match through BTF, CCF/RCG2 objects, symbols,
modules, and metadata. Two credential-free staging archives, independently
prepared ASUS wrappers, and header-v3/AVB packages also match byte-for-byte.
The exact bundle verifier passes with all GPU/display consumers disabled and
no trace parameter enabled by default. The
[v14 offline report](../test-results/2026-07-25-network-root-gpucc-rcg2-diagnostic-offline.md)
records its hashes and gates.

Its one attended probe reached `parent-read-begin` after recording the DISPCC
provider runtime-suspended, but never reached `parent-read-complete`, the
outer callback completion, or the later CCF parent-cache lookup. This
localizes the non-returning boundary to the existing `regmap_read()` call
without distinguishing MMIO, interconnect, regmap-lock, or provider-state
causes. The independent watchdog restored the exact fallback; zero retained
pstore/fatal records and complete NFS, firewall, service, address, inhibitor,
and profile cleanup passed. The
[v14 live report](../test-results/2026-07-25-network-root-gpucc-rcg2-diagnostic-live.md)
records the ordered trace and rollback evidence. V14 must not be rerun. The
next gate could not add a provider runtime resume under `prepare_lock`.

Network-root v15 now passes that complete offline behavioral gate. An
exhaustive finite-state model makes the old order and get-beneath-lock
mutations reach ABBA deadlock, while the candidate core and both OF-provider
paths reach neither deadlock nor reference leak. Red/green source,
integration, mutation, and exact-patch tests pass, as do 118 clock KUnit tests
with zero failures. The candidate is an experimental partial backport of the
unmerged March 2025 CCF runtime-PM RFC: acquire all registered provider
runtime-PM references before `prepare_lock`, run the unchanged orphan scan,
unlock, then release the references.

Two clean mainline builds match through BTF, CCF/QCOM objects, symbols,
modules, and metadata. Two credential-free staging archives, independently
prepared ASUS wrappers, and header-v3/AVB packages also match byte-for-byte.
The exported ABI, complete module archive, GPUCC module, and RCG2 object are
unchanged from v14. The
[v15 offline report](../test-results/2026-07-25-network-root-gpucc-runtime-pm-candidate-offline.md)
records the exact identities and residual risk.

Its single attended RAM-only probe made the DISPCC provider active (`ret=11`
instead of v14's suspended `ret=7`), completed 7/7 observed RCG reads, and
advanced common-clock registration through completed index 6 and into index
7. The probe delivered 552 CCF markers over 73.901 seconds, with no gap over
0.116 seconds, until the 75-second watchdog reset at
`consumer-allocation-complete`. This strongly supports trace-budget
exhaustion rather than a new localized stall, but GPUCC registration and
post-load stability did not return. Exact fallback, zero retained
pstore/fatal evidence, and complete host cleanup passed. The
[v15 live report](../test-results/2026-07-25-network-root-gpucc-runtime-pm-candidate-live.md)
records the trace and inference. V15 must not be rerun; the next gate is an
offline-verified trace-free v16 confirmation using unchanged behavior and
disabled consumers.

Network-root v16 now passes that complete offline gate without rebuilding or
changing any accepted artifact. Its explicit fixed ACM action omits all three
core trace flags. The guarded probe requires confirmation mode, exact
command-line count zero, and mode-`0400` state `N` for every core parameter
before arming the 75-second watchdog. A hash-pinned read-only target baseline
also requires the initial 900-second watchdog to remain armed while it checks
zero storage, consumer isolation, thermals, the module tree, and a quiet
kernel log. Only the read-only outer GPUCC trace remains; source proves its
eight successful-return notices add no deliberate delay. Red/green, semantic,
mutation, baseline, existing probe, nine pseudoterminal transport, and exact
nested-bundle tests pass. The
[v16 offline report](../test-results/2026-07-25-network-root-gpucc-confirmation-offline.md)
records the pinned procedure and one-shot acceptance gate.

The attended v16 cycle stopped safely before target entry. One temporary boot
and the trace-free load passed, but a 284-second operator gap exceeded the
staging recovery's 180-second watchdog. The missing-guard and later
stability-check failures both occurred before serial execute, the target NFS
link never appeared, and exact fallback and host cleanup passed. V16 is
consumed. V17 now offline-accepts a compound `confirm-gpucc` mode that requires
both guards before discovery and runs trace-free load followed immediately by
non-retryable execute in one process. Its 12 ACM tests, semantic/mutation
suite, and complete exact nested bundle verifier pass. See the
[v16 staging-only report](../test-results/2026-07-26-network-root-gpucc-confirmation-live.md)
and
[v17 offline report](../test-results/2026-07-26-network-root-gpucc-atomic-confirmation-offline.md).
The one permitted live v17 cycle then passed the complete gate. Its atomic
transport performed one execute, Linux 7.1.4 passed the trace-free baseline,
and the guarded module reached all eight outer markers through
`registration-complete ret=0`. GPUCC bound exactly one device and stayed
stable for 30 seconds with GPU, GMU, Adreno SMMU, render nodes, and storage
still absent. A normal reboot restored a changed exact fallback boot with zero
pstore/fatal evidence, 73 readable thermal zones at a 38.5 C maximum, and
complete host cleanup. The
[v17 live report](../test-results/2026-07-26-network-root-gpucc-atomic-confirmation-live.md)
accepts only the isolated GPUCC/CCF foundation. Acceleration remains pending
an offline-tested and reproducible power-domain, regulator, interconnect,
Adreno SMMU, GMU, firmware, and DRM consumer sequence.

V18 offline-accepted the smallest next slice: GPUCC plus the built-in Adreno
SMMU only. The pinned Linux 7.1.4 source contract proves seven clocks, one CX
GDSC, twelve IRQs, runtime PM with 20 ms autosuspend, and no SMMU firmware
path. The two-status overlay leaves GPU, GMU, A660 firmware, render nodes,
storage, and every unrelated consumer disabled. Two clean ASUS wrapper builds
and two independent repacks match byte-for-byte; source, DT, stage, baseline,
probe, mutation, historical, and exact-bundle tests pass. See the
[v18 offline report](../test-results/2026-07-26-network-root-adreno-smmu-offline.md).

The one attended v18 cycle reached Linux 7.1 and invoked its compound gate
once, but the read-only baseline safely rejected the normal line `iommu:
Default domain type: Translated`: the case-insensitive detector matched
`fault` inside `Default`. The original watchdog remained armed, no watchdog
was disarmed, GPUCC was never loaded, the SMMU remained unbound, and GPU/GMU,
firmware, render nodes, storage, and failed units remained absent. Normal
reboot restored exact fallback and complete NFS/firewall/USB host cleanup.
V18 is consumed and must not be retried. See the
[safe-rejection report](../test-results/2026-07-26-network-root-adreno-smmu-v18-live-rejected.md).

V19 is the corrected external control plane around the unchanged reproduced
v18 binary. Test-first fault detection now rejects `Default` while accepting
real token-delimited IOMMU, arm-smmu, context, and global faults; fallback
fatal detection likewise rejects benign `dynamic_debug` and `panic:1` config
text. The full exact binary verifier and all affected contracts pass. A new
copy-on-write v19 root preserves all 1,008 matching module files and
credentials, removes only the three exact A660 firmware files, and leaves the
accepted base unchanged. At that checkpoint, the runtime NFS allowlist
accepted v1 and v19, not historical v18. The strict five-file launcher retains
the original watchdog, overlapping 120-second transition watchdog, one
75-second probe, one invocation, private evidence, and immediate fallback.

The one attended v19 gate passed that baseline, armed both handoff/probe
watchdogs, and completed the same trace-free GPUCC registration with
`ret=0`. After the full 30-second settle, however, the exact SMMU platform
device still had no driver link. Systemd remained running with zero failed
units, the maximum observed target temperature was 37.1 C, and no warning,
fault, firmware request, GPU/GMU bind, render, or storage message appeared.
The armed watchdogs automatically removed the gadget; exact fallback and
complete host cleanup then passed. V19 is consumed and must not be retried.
See the
[v19 no-bind report](../test-results/2026-07-26-network-root-adreno-smmu-v19-live-rejected.md).

Pinned source shows a late-provider/deferred-probe boundary: the SMMU needs
GPUCC clocks, the kernel's deferred-probe timeout is ten seconds, GPUCC was
loaded at target uptime 193 seconds, and the built-in `arm-smmu` driver
suppresses its force-bind attribute. V19 did not capture enough supplier and
deferred-list state to assign a single cause.

V20 passed that offline boundary without changing the v18 binary. A
hash-pinned Linux 7.1.4 driver-core verifier proves that platform
`drivers_probe` resolves one exact name with `sysfs_streq()` and calls
`device_attach()` only for that unbound device. The target baseline and probe
validate the exact `3da0000.iommu` identity, an assumed-empty
`driver_override`, enabled
autoprobe, mode-0200 exact-device control, and absent ARM SMMU force-bind
files. They record `waiting_for_supplier`, the already-mounted
`devices_deferred` view, supplier links, driver state, and direct
storage/mount/render/firmware/system counters. After five seconds of normal
autoprobe, the 90-second guarded probe may issue exactly one device-name
request inside a 150-second transition watchdog. Global timeout extension,
broad rescan, force-bind, unload, retry, firmware, render, and storage paths
are rejected.

The full binary verifier passed, and PolicyKit created and independently
verified `/var/lib/rog5-network-root-adreno-smmu-v20`: all 1,008 modules and
credentials are preserved, all three A660 firmware files are absent, and the
accepted base is unchanged. Its one permitted live cycle reached the exact
network root, then stopped before handoff because the fresh platform device
exposed its unset override pointer as `(null)`, not an empty line. The
original watchdog remained armed; the transition/probe watchdogs were not
armed, GPUCC stayed absent, `drivers_probe` was not written, and the SMMU
remained unbound. Read-only diagnosis found two supplier links and zero
waiting, deferred, storage, mount, render, firmware, or failed-unit evidence.
Normal fallback and complete host cleanup passed. V20 is consumed and must not
be served or retried. See the
[v20 offline report](../test-results/2026-07-26-network-root-adreno-smmu-v20-offline.md)
and
[v20 safe baseline-rejection report](../test-results/2026-07-26-network-root-adreno-smmu-v20-live-rejected.md).

Pinned source explains the value: `of_device_alloc()` uses
`platform_device_alloc()`, which zero-initializes the device;
`driver_override_show()` formats the NULL name pointer with `%s`; the kernel
formatter emits `(null)`; and platform matching falls through to OF when no
override exists.

V21 locks those semantics. Its pure read-only checker requires exactly
`(null)\n` and rejects empty, malformed, nonempty, and linked inputs. Static
tests forbid any `driver_override` write. The baseline, probe, and compound
gate retain the exact-device-only request and nested 90/150-second watchdogs.
The full unchanged-binary verifier passes. PolicyKit created and a separate
invocation independently verified
`/var/lib/rog5-network-root-adreno-smmu-v21`: all 1,008 modules and
credentials are preserved, A660 firmware is absent, and the accepted base is
unchanged.

The sole v21 live cycle passed. Its read-only baseline saw an unbound SMMU,
the exact unset-null override representation, two supplier links, zero
waiting/deferred entries, and zero firmware/render/storage activity. The
accepted GPUCC module loaded once; ordinary autoprobe still left the SMMU
unbound, then exactly one `3da0000.iommu` request to `drivers_probe` bound
`arm-smmu`. It remained bound through the 30-second settle with runtime status
`suspended`. Target temperature peaked at 37.1 C before action and 36.2 C at
acceptance, systemd stayed running, and no new warning, fault, or fatal
signature appeared. Normal reboot restored the exact persistent Alpine
fallback, whose final health check reported 39.1 C maximum, zero pstore
records, and zero project modules; complete NFS/firewall/network cleanup
passed. Nothing was flashed.

This accepts only idle GPUCC plus Adreno SMMU registration/runtime suspend.
A660 registration, firmware, DRM open, rendering, display, suspend, and an
accelerated desktop remain unaccepted. V21 is consumed, must never be retried,
and is now absent from the runnable NFS allowlist. See the
[v21 offline report](../test-results/2026-07-26-network-root-adreno-smmu-v21-offline.md)
and
[v21 live acceptance report](../test-results/2026-07-26-network-root-adreno-smmu-v21-live-accepted.md).

The complete pinned A660 graph now also passes source audit. Its guarded
Linux `7.1.4-rog5-a660reg1` build makes DRM/MSM and GPUCC manual modules,
disables MSM display KMS and UFS, and propagates a GMU power-level probe
failure before later initialization. Two rootless, network-isolated builds
produced byte-identical configs, Images, module archives, symbols, three
critical modules, and metadata. No A660 firmware is embedded and the phone was
not contacted. The exact v18-derived four-node DT now also passes mutation
tests and duplicate byte-identical builds while preserving storage, display,
remote-processor, RTC, and USB containment. Its baseline and manually ordered
seven-module registration probe pass offline. The
[registration build report](../test-results/2026-07-26-a660-registration-build.md)
now also records the verified isolated seven-module NFS export, duplicate
nested stages, clean ASUS wrappers, header-v3/AVB repacks, and exact
fourteen-file source-locked bundle.

Registration v2 now removes the `NOT_ACCEPTED` lock without changing any
kernel, config, DT, module, initramfs, wrapper, or AVB bit. A mutation-tested
nonsecret marker pins the exact v21 live report, candidate/evidence commits,
one SMMU bind at runtime suspend, zero firmware/render/storage activity,
passed fallback/cleanup, forbidden v21 reuse, and no flash. The probe reads
that marker only from the immutable NFS lower. PolicyKit created and a
separate invocation verified the new root-owned mode-`0555`
`/var/lib/rog5-network-root-a660-registration-v2`: seven exact modules, zero
A660 firmware, preserved credentials, unchanged base, and root-owned
mode-`0444` marker/seal. The old A660 root and consumed SMMU roots are not
server-allowlisted; NFS stayed inactive. The complete exact binary verifier
passed again and the phone was not contacted. See the
[registration v2 report](../test-results/2026-07-26-a660-registration-v2-offline.md).

A follow-up offline review found that v2 assumed automatic SMMU bind after
GPUCC even though accepted v21 required an exact reprobe. Registration v3 now
checks the immutable-lower NULL-override helper, exact device name, autoprobe,
root-owned mode-`0200` control, and absent force-bind files; after five seconds
of ordinary autoprobe it may write only `3da0000.iommu` once, before any DRM
dependency load. PolicyKit created and independently verified the new
root-owned v3 export; v2 is preserved but no longer allowlisted.

V3 also passes the missing live-control suite: A660-release-specific original
watchdog disarm, independent 90/180-second probe/transition watchdogs, one
target invocation, immediate normal reboot, strict SSH identity, clean
synchronized Git, exact AVB/export hashes, mode-`0600` private evidence, and
no retry. The complete binary verifier passes again. The phone was not
contacted and NFS stayed inactive. See the
[registration v3 report](../test-results/2026-07-26-a660-registration-v3-offline.md).

The sole v3 RAM-only cycle then passed. After the accepted exact SMMU reprobe,
all seven reviewed modules loaded in order; A660 bound, GPU and GMU joined two
IOMMU groups, one headless render node appeared, no process opened DRM, and
firmware, connectors, storage, mounts, failed units, warnings, and faults
stayed zero through the 30-second settle. Maximum target temperature was
38.1 C. Normal reboot restored exact persistent fallback with zero pstore and
project modules; privileged host cleanup removed all NFS/firewall/sysctl
state and restored NetworkManager and ModemManager. V3 is consumed and no
longer server-allowlisted. A mutation-tested nonsecret acceptance marker pins
the exact report hash and evidence checkpoint for every later GPU tier. See the
[registration v3 live acceptance](../test-results/2026-07-26-a660-registration-v3-live-accepted.md).

The next source audit proved that copying firmware without a DRM open causes
no request, while the ordinary first-open path continues immediately into
ucode, runtime power, hardware initialization, HFI, and ZAP/SCM. The accepted
next design is a custom, read-only-armed one-shot open that requests only the
exact SQE and GMU files and then fails before file-context creation or every
later hardware step. Its default-off patch and two isolated clean builds now
pass byte-for-byte: the Image, config, ABI, and every non-MSM module remain
accepted. A new root-owned v4 export now contains only exact SQE/GMU firmware,
the changed MSM module, and a reproducible 896-byte one-open helper; ZAP is
absent. Its mutation-tested target/host watchdog gate and the unchanged full
AVB package pass offline. The sole live cycle then loaded SQE and GMU exactly
once and returned `EUCLEAN` before ucode, runtime power, HFI, or ZAP/SCM.
No DRM descriptor survived; storage, display, warnings, and faults stayed
zero. Maximum target temperature was 38.5 C. Normal reboot restored exact
fallback with zero pstore/project modules and complete host cleanup. V4 is
consumed and removed from the runnable allowlist. A mutation-tested nonsecret
acceptance marker pins the exact report and evidence checkpoint. See the
[firmware-only boundary report](../test-results/2026-07-26-a660-firmware-only-boundary.md)
and
[request-only build report](../test-results/2026-07-26-a660-firmware-request-only-build.md),
then the
[request-only v4 offline report](../test-results/2026-07-26-a660-firmware-request-only-v4-offline.md)
and
[request-only v4 live acceptance](../test-results/2026-07-26-a660-firmware-request-only-v4-live-accepted.md).

The next GPU source boundary now passes offline: exact A660.1 ucode allocation
creates SQE, privileged shadow, and privileged power-up reglist objects
through three SMMU mappings before GPU/GMU runtime power or register access.
The audit also proves that normal A6xx teardown is insufficient for an early
return, so the next patch must be atomic-one-shot and explicitly roll back all
three objects on every path. See the
[ucode-allocation boundary report](../test-results/2026-07-26-a660-ucode-allocation-boundary.md).
That default-off patch now passes its exact stacked-source verifier, strict
checkpatch, and eight source mutations; it also replaces normal A6xx teardown
with the balanced helper. See the
[ucode-allocation patch report](../test-results/2026-07-26-a660-ucode-allocation-patch.md).
Two isolated builds now pass with byte-identical outputs, unchanged
Image/config/ABI and non-MSM modules, an exact MSM-only delta, BTF, and zero
embedded firmware; see the
[ucode-allocation build report](../test-results/2026-07-26-a660-ucode-allocation-build.md).
The fresh root/gate now passes offline with a root-owned SQE/GMU-only export,
PID-filtered exact map/unmap/close and GEM-free contracts, balanced CPU-vmap
and firmware-reference evidence, equal pre/post GEM snapshots, nine
power/HFI/ZAP/SCM zero-event probes, nested watchdogs, and the unchanged full
temporary-boot package. See the
[ucode-allocation v5 offline report](../test-results/2026-07-26-a660-ucode-allocation-v5-offline.md).
A fail-first-tested host runner now pins the exact root, package, target
scripts, SSH identity, one invocation, expected reboot disconnect, and
mode-`0600` private evidence. The
[pre-live control acceptance](../test-results/2026-07-26-a660-ucode-allocation-v5-prelive-hold.md)
records **HOLD**: NFS remains inactive, the root is absent from its allowlist,
the phone was not contacted, and no live cycle is authorized. The later
[pre-live GO review](../test-results/2026-07-26-a660-ucode-allocation-v5-prelive-go.md)
passed exact fallback, host, credential, root, package, runner, and unarmed
refusal checks. A verifier-first opt-in permitted only v5 for one attended
RAM-only cycle; NFS remained inactive until that bounded transition.
That sole cycle is now complete and
[safely rejected](../test-results/2026-07-26-a660-ucode-allocation-v5-live-rejected.md).
The kernel reported successful three-object rollback with balanced map,
unmap, close, unpin, free, and firmware-reference traces. The gate then
stopped at public-wrapper `get=1`, expected `4`, before its settle and GEM
snapshot comparison. The accepted Clang module inlines the other three
logical acquisitions inside `msm_gem_kernel_new()` and two releases inside
`msm_gem_kernel_put()`; an exact hash/symbol/relocation verifier now pins
logical balance `4/4` and live wrapper counts `get=1, put=2`. V5 is consumed,
non-runnable, and cannot be retried. A fresh v6 offline contract must trace
the convenience helpers directly and still require equal post-settle GEM
snapshots before another GO review.

That
[v6 offline contract](../test-results/2026-07-26-a660-ucode-allocation-v6-offline.md)
now passes without rebuilding the kernel. Zero-fuzz patches reproducibly
derive new runtime scripts from hash-pinned v5 sources, while an exact
relocation verifier binds the oracle to the accepted MSM module. The new
probe requires three successful `kernel_new` results, two `kernel_put`
operations, public wrappers `get=1, put=2`, logical `4/4`, exact object-set
relationships, and the original equal post-settle GEM snapshot. Its
root-owned reflink export passed whole-tree verification and a changed-seal
mutation. At that checkpoint v6 had no live host runner. The subsequent
[pre-live control acceptance](../test-results/2026-07-26-a660-ucode-allocation-v6-prelive-hold.md)
adds a fail-first-tested, exact one-invocation runner with strict SSH identity,
private evidence, protected root verification, and no NFS/boot/retry control.
NFS remains inactive, v6 is absent from the server allowlist, and the decision
remains **HOLD**. The phone was not contacted.

The subsequent
[pre-live GO review](../test-results/2026-07-26-a660-ucode-allocation-v6-prelive-go.md)
adds one explicit-opt-in v6 NFS case guarded by the complete root verifier
before any host mutation. Its fail-first/static tests and actual unarmed
privileged refusal pass. Clean synchronized Git, exact fallback, distinct
pinned SSH identities, credential/root/package/runner inputs, and inactive
NFS/RPC pass. This lifts HOLD for at most one attended RAM-only v6 cycle; it
does not accept any GPU result and does not permit a retry.

That sole cycle is now complete and
[safely rejected](../test-results/2026-07-26-a660-ucode-allocation-v6-live-rejected.md).
The exact kernel diagnostic requested both firmware files, completed three
allocations and rollback, and emitted its success marker. The userspace entry
probe correctly observed raw request sizes `43288`, `4`, and `4096`, but v6
incorrectly expected page-rounded object sizes `45056`, `4096`, and `4096`.
It stopped before settle and GEM snapshot comparison. The transition watchdog
restored exact fallback, privileged host cleanup passed, and v6 is consumed
and absent from the runnable server. A separately reviewed v7 must fix the
raw-size oracle while retaining every pointer, forbidden-event, storage,
watchdog, and equal-snapshot constraint.

That
[v7 offline contract](../test-results/2026-07-26-a660-ucode-allocation-v7-offline.md)
now passes without rebuilding the kernel. It derives exact controls and a
root-owned mode-`0555` export from immutable consumed v6, expects the raw
entry set `4/4096/43288`, separately source-pins page-rounded objects
`4096/4096/45056`, and retains three successful kernel-new returns, two
kernel puts, wrapper `1/2`, logical `4/4`, exact rollback object sets, and an
equal post-settle GEM snapshot. Whole-tree comparison preserves credentials
and every undeclared payload; changed-predecessor and rounded-as-raw roots
are rejected. NFS/RPC stayed inactive, v7 has no server case or live runner,
and the phone was not contacted at that checkpoint. The subsequent
[v7 pre-live control acceptance](../test-results/2026-07-26-a660-ucode-allocation-v7-prelive-hold.md)
adds a fail-first-tested exact one-invocation runner. Its strict SSH identity,
immutable input, private logging, expected disconnect, one-call, and no-retry
mock contracts pass; local credential fingerprints match the protected root,
and an actual unarmed invocation refused before any state change. The runner
cannot start NFS or boot the phone. NFS/RPC remains inactive, the v7 root
had no server case at that checkpoint, and no phone contact occurred. The
separate
[v7 pre-live GO review](../test-results/2026-07-26-a660-ucode-allocation-v7-prelive-go.md)
now adds one exact-root, verifier-before-state NFS case behind a dedicated
opt-in. Clean synchronized Git, immutable root/package/runner hashes,
credentials, distinct SSH identities, strict read-only fallback health,
inactive services, and actual unarmed runner/server refusals pass with zero
residue. At most one attended RAM-only v7 cycle is authorized, with no retry
and no flash.
That
[sole v7 live cycle](../test-results/2026-07-26-a660-ucode-allocation-v7-live-accepted.md)
now passes. The raw `4/4096/43288` entry set, three successful allocations,
exact map/unmap/close/unpin/free sets, compiler-aware logical `4/4`, and
equal pre/post GEM snapshots after settle all matched. The intentional open
returned `EUCLEAN`; power, HFI, ZAP/SCM, hardware initialization, storage,
faults, and retained DRM descriptors remained zero. The normal reboot
restored exact fallback and complete host cleanup. V7 is consumed,
non-runnable, and must not be retried.

The next source-only boundary and kernel build now pass offline. The
[GMU resume-entry audit](../test-results/2026-07-26-a660-gmu-resume-entry-boundary.md)
pins the normal first-open call graph through outer GPU runtime PM into
`a6xx_gmu_resume()`, then places an exact-A660.1 one-shot stop after the GMU
initialized guard and before `gmu->hung`. Its patch is default-off,
mode-`0400`, independently consumes the open and entry hit, deliberately
returns `EUCLEAN`, rejects mixed/repeated/missed paths, balances outer runtime
PM, and reuses the v7-proven ucode/firmware rollback.

The
[v8 offline build acceptance](../test-results/2026-07-26-a660-gmu-resume-entry-v8-offline.md)
records two complete network-disabled clean builds with byte-identical config,
Images, symbols, modules, archive, and metadata. Relative to accepted v7,
only the BTF-bearing `msm.ko` changes; KMS, UFS, embedded A660 firmware, GMU
inner power/clock/MMIO/IRQ/firmware/HFI, hardware initialization, ZAP/SCM,
submit, and rendering remain outside the accepted boundary.

The
[v8 runtime acceptance](../test-results/2026-07-26-a660-gmu-resume-entry-v8-runtime-offline.md)
now reproducibly derives both target controls from immutable consumed v7 with
two zero-fuzz patches. The compiler-relocation gate preserves the accepted
three-object/logical-`4/4` cleanup and proves the atomic entry hit is compiled
before inner PM, clocks, IRQ, and HFI. Semantic and mutation tests require one
outer and zero inner runtime-PM operations, exact `EUCLEAN`, successful
rollback, equal settled GEM snapshots, and zero clock/IRQ/HFI/devfreq/LLC/
hardware/ZAP/SCM work. The
[v8 protected-root acceptance](../test-results/2026-07-26-a660-gmu-resume-entry-v8-root-offline.md)
now also passes. A PolicyKit-only builder derives a root-owned mode-`0555`
copy-on-write root from permanently consumed v7, replaces only the versioned
controls and exact v8 MSM module, and preserves all other bytes, metadata,
credentials, host keys, modules, and firmware. The complete verifier passed
during construction and twice against the final root; predecessor, parameter
mode, build-evidence, trace-policy, and old-MSM mutations were rejected. The
compound target gate passes offline with the initial watchdog retained
through baseline, an overlapping 240-second transition watchdog, exactly one
probe, and mandatory normal reboot. NFS/RPC stayed inactive at that
checkpoint. The
[v8 pre-live control acceptance](../test-results/2026-07-26-a660-gmu-resume-entry-v8-prelive-hold.md)
now also passes. Its one-invocation runner pins clean synchronized Git,
caller-owned credentials and private evidence, the unchanged RAM-only
package, complete protected-root verifier, target gate, and watchdog helper.
The mock proves one prepare/copy/remote-verify/gate sequence, expected reboot
disconnect, and no retry. Local-only fingerprint checks agree across the
client key, both protected authorized-key files, and pinned server identity;
the real root verifier and an actual unarmed runner refusal pass with
NFS/RPC inactive. The
[v8 pre-live GO review](../test-results/2026-07-26-a660-gmu-resume-entry-v8-prelive-go.md)
then adds only a fail-first verifier-before-state exact-root server case and
revalidates the complete package, protected root and five mutations,
credentials, distinct host identities, strict read-only fallback health, and
both actual unarmed refusals. The temporary USB profile was deactivated and
final host state is residue-free. The
[sole v8 live cycle](../test-results/2026-07-26-a660-gmu-resume-entry-v8-live-rejected.md)
then reached the exact GMU entry and accepted rollback. All three deliberate
`-EUCLEAN` returns appeared as zero-extended `4294967179` in the `s64`
kretprobe oracle, which failed closed. Complete trace review also found 21
process-scoped generic `__pm_runtime_resume()` calls across mapping, the GPU
callback, and rollback, invalidating the global count-of-one oracle. Direct
inner GPU/GMU PM, clock, IRQ, HFI, devfreq, LLC, hardware, ZAP, and SCM
probes remained zero. The runner was not retried; exact fallback and complete
host cleanup passed. V8 is permanently consumed and absent from the bounded
server. A separately versioned v9 must correct signed-`int` handling and
scope runtime PM by GPU device while retaining every later settle, snapshot,
rollback, zero-resource, and watchdog gate. The
[v9 offline runtime acceptance](../test-results/2026-07-26-a660-gmu-resume-entry-v9-runtime-offline.md)
now passes that control-only correction. It reuses the exact v8 kernel/module,
accepts signed and zero-extended `EUCLEAN` plus the observed 21 generic PM
events with one GPU-device match, reproduces byte-identical controls, and
rejects twelve semantic mutations. The
[v9 protected-root acceptance](../test-results/2026-07-26-a660-gmu-resume-entry-v9-root-offline.md)
now adds a consumed-v8-derived mode-`0555` root, exact unchanged
kernel/seven-module/two-firmware payload, signed/device-scoped oracle,
whole-tree and credential verification, and overlapping-watchdog target gate.
Construction and an independent final-path audit pass with NFS/RPC inactive
and no phone contact. The
[v9 pre-live HOLD review](../test-results/2026-07-26-a660-gmu-resume-entry-v9-prelive-hold.md)
now adds a strict one-invocation/no-retry runner, exact mocked transport,
private evidence contract, local Ed25519 client/server agreement, real
unarmed refusal, clean synchronized Git, and another full root audit. NFS/RPC
remains inactive and the bounded server has no v9 token at that checkpoint. A
later
[attended GO review stopped at HOLD](../test-results/2026-07-26-a660-gmu-resume-entry-v9-prelive-go-hold.md):
one fail-first-tested verifier-before-state exact-root NFS case now exists,
and all local package/root/runner/server/credential/host gates plus an actual
unarmed zero-state refusal pass. The phone is physically absent, however, so
the mandatory identity-pinned persistent-fallback preflight cannot run. No
NFS window opened at that checkpoint.

The
[sole v9 live acceptance](../test-results/2026-07-27-a660-gmu-resume-entry-v9-live-accepted.md)
now closes that HOLD. Current exact fallback and every transition-time gate
passed; one manifest-pinned image was booted in RAM and the corrected oracle
accepted one GPU-device outer runtime-PM event, signed `-EUCLEAN`, exact
two-firmware/three-allocation rollback, logical `4/4`, and an equal settled
GEM snapshot. All specific inner power, clock, IRQ, HFI, devfreq, LLC,
hardware, ZAP, and SCM probes stayed zero; storage and retained DRM
descriptors stayed zero. Exact fallback and complete host cleanup passed.
V9 is permanently consumed and absent from the bounded server. The separate
[v10 GMU/CX runtime-PM offline acceptance](../test-results/2026-07-27-a660-gmu-cx-runtime-pm-v10-offline.md)
now passes a source-pinned pre-GX boundary, twelve patch mutations, strict
patch checks, and two byte-identical isolated Linux 7.1.4 builds. It changes
only `msm.ko` from accepted v8 while preserving Image, ABI, config, all other
installed modules, and storage/firmware containment. V10 remains HOLD: no
runtime oracle, protected root, target gate, bounded server case, boot
authority, retry, or flash exists.

The raw ramoops reader and bootloader restart-reason helper remain under
`tools/diagnostics/`.
