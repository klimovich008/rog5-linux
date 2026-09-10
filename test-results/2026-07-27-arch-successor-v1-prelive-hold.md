# Arch Plasma/server successor v1 — pre-live HOLD

Date: 2026-07-27

Decision: **HOLD. The exact-root NFS case, first-boot target gate, strict-SSH
host runner, watchdog handoff, normal-reboot requirement, and fail-closed
unarmed invocation pass offline. No NFS window or RAM-only boot is authorized
by this checkpoint.**

No NFS, RPC, firewall, or interface state mutation and no boot, kexec,
reboot, fastboot, flash, phone-storage, or external-service action ran.
Existing pinned fallback SSH was used only for read-only health checks; no
credential was created, changed, exposed, or copied into the repository. The
phone remained on the persistent Alpine fallback with its panel brightness
at zero.

This checkpoint builds on the
[protected-export acceptance](2026-07-27-arch-successor-protected-export-offline.md).
The root remains the same root-owned Btrfs `ro=true` subvolume:

```text
/var/lib/rog5-network-root-arch-successor-v1
seal_sha256=6b5fa1b8e93b7e9f1ad41788ca524d5be6b4195c28ce85f70a28143360109eb4
archive_sha256=88c2d671a26f577aef963212cda17bc61baa888d77d0c1aaf1ca25c6fb3ad62a
kernel=7.1.4-g7a5cef0db479
packages=655
```

The sealed v10 diagnostic root was neither an input nor modified.

## Fail-first sequence

Commit `142198a` added all three contracts before their implementations. They
stopped independently on:

```text
FAIL successor NFS window omits: /var/lib/rog5-network-root-arch-successor-v1)
FAIL missing Arch successor v1 target gate
FAIL missing Arch successor live-gate control: .../run-arch-successor-v1-live-gate.sh
```

Commit `14b1da4` adds only the bounded server case and the two one-shot
controls. It does not add a boot command or start a service.

## Exact-root NFS boundary

`serve-network-root.sh` has one new path:

```text
/var/lib/rog5-network-root-arch-successor-v1
```

It requires:

```text
ALLOW_ARCH_SUCCESSOR_V1_NFS=1
```

The token check precedes `verify-arch-successor-export.sh`; the complete
recursive verifier precedes the first export-table, NFS, firewall, bind,
interface, or sysctl state line. The shared server remains:

- NFSv4.2/TCP only;
- bound to `169.254.77.1:2049`;
- exported read-only only to `169.254.77.2`;
- isolated by the runtime drop-by-default firewall boundary;
- limited to 60–86,400 seconds; and
- fully cleaned up on exit.

The server still contains no boot, ADB, fastboot, flash, or phone-storage
command.

## Actual unarmed refusal

A PolicyKit invocation against the exact protected root without the token
returned:

```text
FAIL set ALLOW_ARCH_SUCCESSOR_V1_NFS=1 for the attended Arch successor v1 window
```

The invocation exited nonzero before the verifier or any state line.
Normalized before/after host state had the same SHA-256:

```text
42bd2f77aa14e468ab6dbb910ade53b91eff578321895cca92706278743ad142
```

The normalization covered NFS/rpcbind unit states, exports, ports
111/2049/32767, the temporary mount, mountd, NFS threads,
`ip_nonlocal_bind`, runtime firewall state, and IPv4 interface/prefix
identity. Time-varying address lease lifetimes were deliberately omitted.

Final state remained:

```text
nfs-server=inactive
rpcbind-service=inactive
rpcbind-socket=inactive
exports=0
listeners=0
mount=absent
protected-root-ro=true
```

## First-boot target gate

`run-network-root-arch-successor-v1-gate.sh` requires separate one-shot gate
and reboot variables and root execution. Before any watchdog handoff it
requires:

- exact Linux 7.1.4 and systemd PID 1 in `running` state;
- `multi-user.target`, active NetworkManager, key-only SSH, and sleep
  inhibitor;
- successful udev coldplug, module loading, sysusers, and tmpfiles units;
- inactive greetd, Chromium, ttyd, and VPN-hotspot services;
- OverlayFS `/`, exact read-only NFS lower, and a 2 GiB
  `nodev,nosuid` tmpfs upper;
- zero physical block devices and zero block-backed mounts;
- exact USB `/30` carrier and address;
- the exact protected-root seal and 655 installed packages;
- locked desktop/agent identities and isolated mode-`0700` agent state;
- an empty lower machine ID and a generated volatile upper machine ID;
- the persistent root-only SSH host key;
- exact inhibitor, Chromium-isolation, and VPN-hotspot units;
- every present backlight at brightness zero, or no backlight in the
  headless DTB;
- zero failed units and zero fatal kernel signatures; and
- the exact redacted metrics collector and watchdog-disarm helper.

It emits the redacted runtime baseline, arms a separate 240-second reset
watchdog, atomically disarms the initial network-root watchdog, requests one
normal systemd reboot, and then waits for disconnect. It never writes phone
storage.

## Strict-SSH host runner

`run-arch-successor-v1-live-gate.sh` does not start NFS or boot the phone. It
requires:

- separate live-gate and reboot variables;
- clean Git on `agent/linux-recovery-host`, synchronized with its remote;
- caller-owned mode-`0600` SSH key and known-hosts files outside Git;
- a caller-owned mode-`0700` private evidence directory;
- the exact protected-root verifier, target gate, and disarm-helper hashes;
- complete PolicyKit root verification before target contact;
- strict host-key checking under alias `rog5-arch-successor-v1`;
- exactly two root-owned mode-`0500` files staged in target tmpfs;
- an exact lower-root seal check before invocation;
- one target invocation and no retry;
- exact redacted headless/first-boot/reboot evidence; and
- an expected SSH disconnect followed by separate fallback/host cleanup
  verification.

The evidence log is created once at mode `0600`. No key body, fingerprint,
serial, address inventory, SSID, credential, or provider data enters Git or
the report.

## Offline revalidation

All current checks pass:

```text
PASS Arch successor v1 NFS window is exact-root, one-token, verifier-first, bounded, and non-flashing
PASS Arch successor v1 target gate is first-boot, screen-off, storage-free, watchdog-handed-off, and one-reboot
PASS host Arch successor v1 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries
PASS Arch successor export is manifest-pinned, recursively sealed, read-only Btrfs, mutation-tested, v10-independent, unbooted, explicit-token NFS-gated, and non-flashing
PASS host gate is exact-peer, runtime-only, read-only, and fail-closed
PASS A660 GMU/CX runtime-PM v10 NFS window is exact-root, opt-in, verifier-first, bounded, and non-flashing
PASS network-root init keeps UFS absent, retains an exitrd, tears down overlay backing mounts, and preserves rollback
PASS exitrd move order cleanly unmounts overlay root before its backing filesystems
PASS watchdog disarm is explicit, storage-safe, race-safe, and fail-resumable
```

Shell syntax, ShellCheck, mock call counts, one-reboot ordering, and
`git diff --check` also pass.

| Control | SHA-256 |
|---|---|
| bounded NFS server | `e3961cc441ae6cb75f1a3dcbbd5e4ccc99b31c67018159ac10f61c11f1548769` |
| successor NFS-window test | `8f748f8a76d6dfbd2e93721e742bfe7465d47ce9395cd0b54d8a2354f4b93ef0` |
| target first-boot gate | `50803d4c42619a0118d1458c694296d7151031befcf52110c23de80034bcd3c6` |
| target-gate test | `5a782d0cbcd2ba0f451385e8a9f4d6c70c71ef3cfb235595c47134fa6fb8cf85` |
| strict-SSH host runner | `6e76bde4ac491ff4d1185d9f50c5892b4e3bfd8ce9040135aeb174bfa81b673a` |
| host-runner test | `27c7b47043dd10458a954d46ed9138bc2c7f68dcf29a9ae3a2a4a638b9d7299a` |
| protected-root verifier | `6176b4172c7ad3a0338686eb4c3fd30a6cbcb32c6237c190317da4a4b197a983` |
| aggregate Linux-rootfs test | `1bc09ac86776c4d9567c1c5ee300678bfd4955b80e4320ee8712cdd2c9dac530` |

## Requirement for a future live decision

This control-plane acceptance is not a GO. A future attended cycle must first
choose between:

1. the v10 GPU diagnostic, which advances accelerated Plasma; or
2. this normal successor root, which validates modern headless userspace but
   does not prove GPU acceleration.

Either choice requires a new strict fallback preflight, clean synchronized
Git, exact protected-root and package checks, private SSH/evidence setup,
host-state cleanliness, and a fresh explicit GO. One RAM-only cycle must have
no retry and no flash, reboot immediately to fallback, and prove complete
fallback and host cleanup.
