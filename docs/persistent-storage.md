# Persistent native-Linux storage and rollback design

## Current decision

Use no repartitioning during the current read-only discovery and bounded-image
phases. This is no longer a permanent “never repartition” decision. The phone
is becoming a dedicated Linux server, and a reviewed native Linux layout may
replace Android payload in Phase 3 after exact backups, restoration rehearsal,
and final operator confirmation of the destructive commands. See the
[current storage migration checkpoint](storage-migration-phase1.md).

The installed Alpine fallback already occupies the large `userdata`
partition and provides a proven USB/SSH recovery path. Arch will be staged as
versioned roots inside that existing ext4 filesystem. Initial Linux 7.x boots
will enter through kexec from Alpine, mount `userdata` read-only, and use a
tmpfs OverlayFS upper. This reaches a native Linux kernel and normal Arch PID
1; it is not Linux inside Android or a container.

No boot, vendor-boot, vbmeta, super, metadata, calibration, or modem partition
is part of the Phase-2 bounded-image write experiment. `super` and Android
`metadata` are future reclaim candidates; firmware, identity, calibration,
both GPT copies, and the verified recovery route remain protected.

## Measured storage contract

The read-only live inspector passes on the installed fallback:

```text
PASS persistent layout mode=live slot=_b protected_slot=_b root=/dev/sda23 filesystem=ext4 userdata_bytes=243766472704 free_kib=197263136 plan=no-repartition
```

The following table is historical evidence from one boot, not a reusable
device-node mapping. A later Phase-1 inventory proved that UFS `sd*` letters
change across boots. New code must use freshly matched disk/partition GUID,
label, offset, and size. The relevant historical topology was:

| Node | GPT name | Start sector | Sectors | Role |
|---|---|---:|---:|---|
| `sda19` | `super` | 4,108,352 | 14,680,064 | Android dynamic partitions; preserve in Phase 2, Phase-3 reclaim candidate |
| `sda22` | `metadata` | 18,788,672 | 32,768 | Android metadata; preserve in Phase 2, Phase-3 reclaim candidate |
| `sda23` | `userdata` | 18,821,440 | 476,106,392 | current Alpine ext4 root and future `/rog5` store |
| `sde11` | `boot_a` | 688,176 | 196,608 | boot-critical; never use during kexec development |
| `sde14` | `vbmeta_a` | 885,200 | 128 | boot-critical; never use during kexec development |
| `sde23` | `vendor_boot_a` | 1,482,168 | 196,608 | boot-critical; never use during kexec development |
| `sde35` | `boot_b` | 2,367,416 | 196,608 | active Alpine fallback slot; preserve |
| `sde38` | `vbmeta_b` | 2,564,440 | 128 | active-slot verification data; preserve |
| `sde47` | `vendor_boot_b` | 3,161,408 | 196,608 | active Alpine fallback slot; preserve |

Sysfs sector counts use 512-byte units even though the UFS logical block size
is 4096 bytes. `userdata` is 243,766,472,704 bytes (about 228 GiB). Its ext4
filesystem reports about 223 GiB usable and 189 GiB currently available.

The current boot slot is `_b`. “Inactive slot A” is not synonymous with
“disposable”; it remains unopened until a separate read-only backup and
identity review.

## On-filesystem layout

All new persistent project data stays below one top-level directory so the
existing Alpine root remains bootable and removal remains straightforward:

```text
/rog5/
  boot/
    candidates/
      <generation>/
        Image
        board.dtb
        initramfs.cpio.gz
        SHA256SUMS
        seal
  roots/
    arch-a/
    arch-b/
  shared/
    home/
    srv/
  state/
    good
    next
    attempts/
  evidence/
```

Rules:

- A candidate or root is first created with a `.partial` suffix, verified,
  recursively sealed, and atomically renamed on the same filesystem.
- `arch-a` and `arch-b` are deployment generations, not Android boot slots.
- The selected generation is an exact record in `state/good`; the initramfs
  never follows an unverified selector symlink.
- `state/next` permits one trial. It is consumed before kexec so a failed
  target cannot create an automatic reboot loop.
- Root images contain no SSH private key, VPN profile, email, CV, browser
  state, API token, or remote-desktop credential.
- Mutable user/server data belongs under `shared`, with separate ownership
  and backup policy. Credential integration remains a later explicit step.
- Evidence is mode `0700` and stores only redacted runtime reports.

The first staged root should be the already verified successor-v3 Arch
archive. A deployment-local SSH host key is generated on the phone, outside
the archive, after the persistent-write gate is explicitly authorized.

## Boot architecture

```text
active slot B
  -> proven Alpine 5.4 recovery shim
  -> USB NCM + strict SSH + fallback watchdog
  -> hash-pinned one-shot kexec payload
  -> Linux 7.x initramfs
  -> exact userdata discovery
  -> selected /rog5/roots/arch-* lower tree
  -> native Arch systemd / Plasma / server
```

The steady-state system is Linux 7.x with Arch PID 1. Alpine is a short
recovery shim and rollback target, not an Android host and not a container.
This avoids boot-partition writes while GPU, display, Wi-Fi, charging, and
normal UFS operation are still being accepted.

Direct boot from an inactive Android slot is optional future optimization,
not a prerequisite for a native system. It remains prohibited until the
kexec release passes repeated boot, rollback, storage, thermal, power, and
hardware gates and all affected partitions have verified backups.

## Migration gates

### Gate P0 — measured-layout preflight (passed)

`scripts/device/inspect-persistent-layout.sh` reads only procfs, sysfs, the
fallback marker, and filesystem free-space metadata. It requires:

- exact primary and boot LUN sizes;
- exact `super`, `metadata`, `userdata`, boot A/B, vendor-boot A/B, and vbmeta
  A/B numbers, starts, sizes, and GPT names;
- `/dev/sda23` as the unique writable ext4 `/`;
- slot suffix `_a` or `_b`, with the current slot reported as protected;
- no boot-critical partition mounted;
- the existing `.rog5-linux-root` marker; and
- at least 16 GiB free.

Its fixture suite rejects changed size, label, root device, slot, mounted
boot media, insufficient space, missing fallback marker, and changed active
boot label. The implementation contains no mount, partition, format, block
read, flash, reboot, or kexec action.

### Gate P1 — host-side root staging package (passed offline)

`scripts/device/stage-persistent-arch-root.sh` and
`scripts/device/persistent-root-tool.py` now implement the first-generation
stager for `/rog5/roots/arch-a.partial`. The production path accepts only the
manifest-pinned 2,007,033,670-byte successor-v3 archive with SHA-256
`a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7`.
Before creating `/rog5`, it requires the live P0 map and a separate
`ALLOW_ROG5_PERSISTENT_STAGE=1` arm.

The archive inspection rejects absolute/parent paths, duplicate entries,
device nodes, FIFOs, unsupported members, escaping relative links, and known
deployment-credential paths. Extraction uses libarchive with ACL, xattr,
file-flag, ownership, mode, and timestamp preservation. A canonical
whole-tree seal covers every directory, regular file, symlink, file-content
hash, mode, owner, group, size, mtime, link count, link target, ACL,
capability, and other xattr. The root remains `UNBOOTED`; staging never writes
`state/good` or `state/next`.

The fail-first fixture suite proves that an interrupted extraction leaves
only `arch-a.partial`, a stale partial or existing final root is never
overwritten, and the verified tree becomes visible only through one
same-filesystem atomic rename. It also detects post-publication content
changes. The real 181,242-entry archive passes the independent archive
contract. Alpine's signed aarch64 `libarchive-tools 3.8.7-r0` package is
size/hash pinned, signature-verified offline, and its `bsdtar` payload executes
against the current fallback libraries without installing the package.

See the
[offline P1 result](../test-results/2026-07-27-persistent-arch-staging-offline.md).
The later
[live P1 result](../test-results/2026-07-27-persistent-arch-staging-live.md)
passed the exact production preflight, phone-side archive hash, atomic
publication, and an independent post-publication whole-tree verification.
`/rog5/roots/arch-a` now exists with promotion state `UNBOOTED`; neither
`state/good` nor `state/next` exists. The redundant phone-side transfer
archive was removed after verification. Alpine remained online and no root
was selected or booted.

### Gate P2 — UFS read-only Arch boot

The 2026-08-12 Generation-22 cycle completed signed recovery transfer and
COMMIT, but the target never exposed its `ROG5 persistent root` USB identity.
Exact Alpine returned after a 25.255-second USB blackout. This proves neither
that UFS failed nor that the target kernel panicked; a temporary pstore mount
was empty and therefore inconclusive. Generation 22 is consumed and absent
from boot policy.

Generation 23 kept the same Linux 7.1.4 Image, UFS DTB, read-only storage
contract, 600-second rollback, and sealed Arch root. Its sole cycle again
produced no target USB and returned exact Alpine after 25.330 seconds. The
initramfs still validated its command line and running release before USB, so
the result did not distinguish those gates. A forced-Alpine reboot baseline
was 18.162 seconds; the roughly 7.168-second delta strongly fits the
five-second invalid-command-line branch plus startup, without proving it.
Generation 23 is consumed and absent from boot policy.

Generation 24 moved rollback arming and NCM setup before target command-line/
release validation and every userspace UFS operation. Its sole cycle still
showed no target USB before exact Alpine returned after 25.567 seconds, so the
earlier command-line-ordering explanation is disproven. Generation 24 is
consumed and absent from boot policy.

Generation 25 substituted the reconstructed historically accepted UFS Image
while retaining Generation 24's DTB, initramfs, USB identity, and read-only
storage behavior. Its sole cycle still produced no target USB and exact Alpine
returned after 25.038 seconds. It obtained no UFS inventory and performed no
authorized storage write. Generation 25 is consumed and absent from active
boot policy. See the [offline](../test-results/2026-08-12-generation-25-ufs-image-control-offline.md)
and [live](../test-results/2026-08-12-generation-25-ufs-image-control-live.md)
results.

Generation 26 tested one coherent UFS-specific memory-ownership difference.
The retained historically live-passing UFS DTB reserves the 4 MiB
`qcom,rmtfs-mem` range at `0x9b800000`; the failing persistent DTB disables
that node while its command line assigns the same range to ramoops. A one-
property DT transform restores the reservation, and the persistent-only
verified command line omits ramoops. Network-root profiles retain ramoops.
Generation 20's successful boot used the disabled node plus ramoops, so the
overlap is not a proven general root cause. Its sole cycle still exposed no
target USB before exact Alpine returned after 25.333 seconds, so Generation 26
is consumed and absent from active policy.

Generation 27 is a smaller pre-UFS discriminator. It combines the exact
Generation 20 Image and DTB that reached NCM carrier on this phone with the
byte-identical Generation 26 persistent initramfs. The initramfs deliberately
expects the UFS kernel's different release: after USB succeeds it must stop at
the release-identity gate, 25 seconds before any UFS discovery. A target NCM
appearance therefore proves the persistent USB path and points to a
Generation 22–26 kernel/DTB regression; another no-target-USB result points
instead to initramfs/configfs or residual kexec state. Neither outcome accesses
phone storage.

Its sole live cycle passed: the target product appeared on the exact USB port,
NCM stabilized at 65.057 seconds from lifecycle start, and the deliberate
release mismatch returned exact Alpine. This disproves the persistent
initramfs/configfs path and payload-independent residual kexec state as the
cause of Generations 22–26 failing before target USB. Generation 27 is
consumed and absent from active policy.

Generation 28 cross-pairs the same live-proven Generation 20 Image with the
UFS-enabled Generation 25 DTB, while retaining the byte-identical initramfs
and pre-UFS release mismatch. If NCM appears, the failure is in the UFS target
Image/config lineage rather than the persistent DTB. If NCM does not appear,
the UFS-enabled DTB or one of its enabled hardware nodes is the discriminated
boundary. Neither outcome permits userspace UFS access.

Its sole live cycle reached stable target NCM in 59.723 seconds from lifecycle
start, then the deliberate release mismatch returned exact Alpine. Generation
28 is consumed and absent from active policy. The result exonerates the DTB
and enabled-node description when paired with a kernel that has no UFS driver;
it does not prove that active UFS probing is safe.

Generation 29 completed the missing no-storage matrix cell. The rebuilt UFS
Image from Generations 25/26, Generation 20's exact UFS-disabled DTB, and the
identical persistent initramfs reached stable target NCM in 58.780 seconds.
The expected no-UFS rollback then returned exact Alpine. No UFS inventory,
filesystem operation, or phone-storage access occurred. The result localizes
the remaining early regression to interaction between the rebuilt Image and
active UFS binding or probing. Generation 29 is consumed and must never be
retried.

The exact original persistent-root clean-twin Image remains recoverable from
the retained P2 stage as `832757fc…c76469f`. Reconstructed builds with the
same source tree and config do not reproduce that Image: the previous
persistent-root twins are `854397a7…b4a13`, while a fresh historical-recipe
UFS-discovery build produced `805a68b3…e923b` instead of the accepted
`bdc72155…9ac8c`. Generation 30 therefore used the retained accepted
persistent-root Image directly with the current UFS-enabled DTB and USB-first
initramfs. Its sole cycle never exposed target USB before exact Alpine
returned, reproducing the active-UFS early failure with the accepted Image.
Generation 30 is consumed and must never be retried.

Generation 31 deferred the host probe without changing the accepted UFS source
or DTB. USB remained built in; UFS core, platform glue, and the Qualcomm host
were sealed as an explicit three-module chain outside `/lib/modules`. Its sole
cycle still exposed no target USB before exact Alpine returned, so Generation
31 is consumed and must never be retried. No target-side storage access was
observed.

Generation 32 moves the one remaining UFS-specific built-in layer,
`CONFIG_PHY_QCOM_QMP_UFS`, to a fourth sealed module. Initramfs establishes NCM
and the bounded host-observation window before loading the exact QMP-UFS PHY,
UFS core, platform glue, and Qualcomm host chain. Its sole cycle reached stable
target NCM in 60.616 seconds, proving that the built-in QMP-UFS PHY path was
inside the previous pre-init boundary. Target USB disappeared 11.276 seconds
after enumeration, before the retained evidence could classify a specific
module transition. Generation 32 is consumed and must never be retried.

Generation 33 reused the exact Generation 32 kernel, DTB, and modules. It
loaded only `phy-qcom-qmp-ufs.ko`; target NCM disappeared 11.419 seconds after
enumeration, before the 15-second control window completed. UFS core,
platform, and host modules remained absent, and no UFS enumeration or storage
access occurred. The result narrows the failure boundary to QMP-UFS module
load/driver registration, platform bind/probe, or a shared fixed-time reset.
Generation 33 is consumed and must never be retried.

Generation 34 kept the exact Generation 33 Image, module, and initramfs but
disabled only `&ufs_mem_phy` through a tested one-property overlay. Inserting
the module preserved target NCM for the full 12.008-second control window and
exact Alpine returned. The module therefore relocated and registered safely;
the Generation 33 failure boundary is active platform binding or probe.
Generation 34 is consumed and must never be retried.

Generation 35 advanced through clock and regulator acquisition, including the
existing 91,600 and 19,000 microamp regulator loads. It preserved target NCM
for the full 12.002-second control window and exact Alpine returned. This
clears the probe path through the reviewed regulator loads. Generation 35 is
consumed and must never be retried.

Generation 36 reuses the exact Generation 35 Image and UFS-enabled DTB. Its
diagnostic-only SM8350 branch advances through the legacy-binding decision and
`qmp_ufs_parse_dt`, which maps the PHY MMIO resources, then returns before
clock-provider registration, PHY creation, or provider registration. UFS core,
platform, and host modules remained absent. Its sole cycle preserved NCM for
the full 12.294-second control window and returned to exact Alpine, clearing DT
binding selection and MMIO resource mapping. Generation 36 is consumed and
must never be retried.

Generation 37 advances the same diagnostic-only SM8350 branch through
`qmp_ufs_register_clocks`, then returns before `devm_phy_create`, PHY private
data setup, or OF PHY provider registration. UFS core, platform, and host
modules remain absent, so the cycle cannot enumerate or access storage. A
passing control window clears QMP-UFS clock-provider registration; an early
loss isolates that newly added boundary.

Use the accepted UFS discovery kernel boundary with ext4 built in. The target
must:

1. force every physical block node read-only;
2. locate exactly one `userdata` partition by the measured contract;
3. mount it `ro,noload`;
4. verify the selected Arch tree and boot-candidate seals;
5. use that tree only as an OverlayFS lower with tmpfs upper/work;
6. boot systemd and strict SSH with screen off;
7. report zero blocked UFS command, error-handler, journal-replay, physical
   write, or block-backed writable mount evidence; and
8. return automatically to Alpine through the independent watchdog.

This gate proves mainline UFS and ext4 reads. It does not authorize a writable
mainline root.

The
[offline P2 acceptance](../test-results/2026-07-28-persistent-root-p2-offline.md)
now supplies the exact implementation. A hardened AArch64 verifier reproduces
the complete P1 seal; the target forces all 116 physical nodes read-only,
mounts only exact `/dev/sda23` as `ro,noload`, uses the sealed root below a
2 GiB tmpfs OverlayFS, boots systemd with strict SSH and backlights off, and
retains an independent 600-second reset. Target initramfs, Linux 7.1.4,
nested stage, ASUS wrapper, and header-v3/AVB products all reproduce across
two builds.

The first attended live gate temporarily booted the wrapper, loaded the exact
target once, and then returned automatically to exact Alpine. The target
never exposed its USB or SSH identity, so it was rejected. The run also
revealed an echoed-command marker false positive and rejected peer-key
retention. A first correction also misread missing custom UFS counters as a
missing wrapper flag. Its live run rolled back before staging because the
ASUS wrapper does not implement the target-only read-only UFS mode. The
[first target rejection](../test-results/2026-07-28-persistent-root-p2-live-rejected.md)
and
[wrapper-contract rejection](../test-results/2026-07-28-persistent-root-p2-wrapper-contract-live-rejected.md)
record both safe fallbacks.

Fail-first regressions now require an output-only marker, removal of rejected
volatile SSH keys between probes, zero target-only UFS tokens on the ASUS
wrapper, and exactly one such token in the Linux 7.1.4 kexec command line.
The staging preflight freshly proves all 116 physical nodes read-only and
zero block-backed mounts. The corrected wrapper then reached recovery,
executed the target exactly once, and returned to exact Alpine after
37 seconds. The
[timing result](../test-results/2026-07-28-persistent-root-p2-config-timing-live-rejected.md)
selected the old broad kernel-config branch. Offline extraction proves the
embedded target config equals the pinned config exactly. The next fail-first
correction decoded it once to RAM, verified its full SHA-256 identity, and
separated config-file, decode, and identity failures. Its sole
[config-identity run](../test-results/2026-07-28-persistent-root-p2-config-identity-live-rejected.md)
also executed the target exactly once and returned to exact Alpine after
37 seconds without target USB. That package is consumed.

The next successor removed the live proc-config dependency and required exact
running release `7.1.4-gcfd385a1c754` through `uname -r`. Its sole
[kernel-release run](../test-results/2026-07-28-persistent-root-p2-kernel-release-live-rejected.md)
passed recovery, executed the target exactly once, and returned to exact
fallback after 36 seconds without target USB. The sealed root remained
unchanged and `UNBOOTED`. The fallback panel was initially on and required
one transient screen-off action, so automatic display restoration remains a
separate defect. That package is consumed.

The latest successor reads `/proc/sys/kernel/osrelease` directly and
separates unavailable/read failure from release mismatch. Recovery still pins
the exact target Image hash, and the offline boot contract extracts that
Image's IKCONFIG stream and requires byte identity with the pinned config and
all critical settings. Two corrected raw/AVB repacks are byte-identical. Nine
unique bounded timing markers identify any target pre-USB failure from the
automatic-fallback interval without opening an early shell or mounting
storage. Its sole
[direct-procfs run](../test-results/2026-07-28-persistent-root-p2-osrelease-live-rejected.md)
passed recovery, executed the target exactly once, and returned to exact
fallback after 37 seconds without target USB. Root and host state remained
exact; the fallback display again required a transient screen-off correction.
That package is consumed.

P2 remains HOLD. The common 36-37 second interval across several different
early checks is no longer treated as proof of branch selection. The required
[early-entry v1 package](../test-results/2026-07-28-persistent-root-entry-v1-offline.md)
now passes offline with a credential-free receive-only ACM marker emitted
before userland storage access and an independently armed 120-second reset.
The fallback also has a live-tested OpenRC screen lifecycle, but its
post-cycle boot persistence is now accepted by the
[sole entry-v1 live cycle](../test-results/2026-07-28-persistent-root-entry-v1-live-rejected.md).
That cycle executed target kexec once but never exposed a stable oracle ACM,
so target entry remains unproved. Exact fallback, unchanged `UNBOOTED` root,
absent selectors, and automatic screen-off service restoration passed after
the fixed thermal gate cooled. The target reset path remains unclassified.
Entry-v1 is consumed. P3 remains blocked until a separate offline-reproduced
marker channel can classify target entry even when USB enumeration fails.

### Historical Gate P3 — bounded directory write probe (superseded)

The current plan replaces this older loose-directory probe with the bounded
filesystem-image experiment in
[storage-migration-phase1.md](storage-migration-phase1.md). The text below is
retained as historical design evidence, not the active write target.

Only after P2 passes, build a normal-UFS kernel and a separate one-cycle
write oracle. Stop Alpine services, sync, and make its root clean before
kexec. Limit writes to one new disposable directory under
`/rog5/evidence/write-probe`. Require create, data and directory fsync, atomic
rename, readback after fallback, deletion, clean ext4 state, zero UFS errors,
and automatic rollback. Do not alter a partition table or boot partition.

### Gate P4 — persistent Arch A/B roots (pending)

After P3, stage the inactive Arch generation, boot it once, require a health
record, then promote it to `state/good`. Package upgrades always target the
inactive generation first. A missing health record, fatal log, failed
service, storage error, or fallback mismatch leaves the previous generation
selected and disables automatic retry.

### Gate P5 — release boot (pending)

Require repeated cold boots and reboots, recovery without the Arch root,
screen-off remote access, charging and thermal stability, accelerated GPU,
Wi-Fi client, fail-closed VPN hotspot, and update/rollback drills. Only then
decide whether to retain the safer Alpine-to-mainline kexec shim or separately
review direct inactive-slot boot.

## Recovery

At every pre-release gate:

- slot B and the existing Alpine root remain the recovery baseline;
- USB NCM, ACM where available, and strict SSH are established before handoff;
- kexec is one-shot and guarded by an independent wall-clock fallback;
- a failed target is never retried automatically;
- host artifacts remain sufficient for `fastboot boot` recovery without
  flashing; and
- the reviewed bounded Phase-2 image write uses standing authorization; any
  raw partition change still requires final confirmation of the exact action.
