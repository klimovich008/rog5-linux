# Persistent native-Linux storage and rollback design

## Decision

Do not repartition the phone.

The installed Alpine fallback already occupies the large `userdata`
partition and provides a proven USB/SSH recovery path. Arch will be staged as
versioned roots inside that existing ext4 filesystem. Initial Linux 7.x boots
will enter through kexec from Alpine, mount `userdata` read-only, and use a
tmpfs OverlayFS upper. This reaches a native Linux kernel and normal Arch PID
1; it is not Linux inside Android or a container.

No boot, vendor-boot, vbmeta, super, metadata, calibration, or modem
partition is part of this design.

## Measured storage contract

The read-only live inspector passes on the installed fallback:

```text
PASS persistent layout mode=live slot=_b protected_slot=_b root=/dev/sda23 filesystem=ext4 userdata_bytes=243766472704 free_kib=197263136 plan=no-repartition
```

The relevant measured topology is:

| Node | GPT name | Start sector | Sectors | Role |
|---|---|---:|---:|---|
| `sda19` | `super` | 4,108,352 | 14,680,064 | Android dynamic partitions; never use |
| `sda22` | `metadata` | 18,788,672 | 32,768 | Android metadata; never use |
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

### Gate P2 — UFS read-only Arch boot (pending)

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

### Gate P3 — bounded UFS write probe (pending)

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
- persistent writes, credential deployment, and any partition change require
  separate explicit authorization.
