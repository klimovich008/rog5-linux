# Arch Plasma/server successor v2 — pre-live HOLD

Date: 2026-07-27

Decision: **HOLD. The separate successor-v2 NFS server, first-boot target
gate, strict-SSH host runner, watchdog handoff, normal-reboot requirement,
and fail-closed unarmed invocation pass. No NFS window or RAM-only boot is
authorized by this checkpoint.**

No NFS, RPC, firewall, interface, listener, mount, boot, kexec, reboot,
fastboot, flash, phone-storage, or external-service action ran. PolicyKit was
used for read-only root verification and one deliberately unarmed server
invocation. Existing pinned fallback SSH was used only for read-only health
checks. No credential was created, changed, exposed, or copied into Git.

This checkpoint builds on the
[successor-v2 protected-export acceptance](2026-07-27-arch-successor-v2-protected-export-offline.md).
The protected root remains:

```text
path=/var/lib/rog5-network-root-arch-successor-v2
owner_mode=0:0:0555
btrfs_ro=true
seal_sha256=f7c39890f2777d9d95f963bf802a09fe3cbfdb863ac9f80392a61d01867796c4
archive_sha256=0da5f1dbc05588fcda444b6ba6d8a66db8fa9749691b1f7e37132de9e8a88078
kernel=7.1.4-g7a5cef0db479
packages=655
promotion=UNBOOTED_HOLD
```

The accepted successor-v1 root, seal, server, target gate, and host runner
remain byte-exact. The sealed v10 GPU diagnostic root was neither an input
nor modified.

## Fail-first sequence

Commit `3533d78` added all three contracts before their implementations.
They stopped independently on:

```text
FAIL missing successor v2 NFS control: .../serve-arch-successor-v2.sh
FAIL missing Arch successor v2 target gate
FAIL missing Arch successor v2 live-gate control: .../run-arch-successor-v2-live-gate.sh
```

Commit `9ffc341` adds the dedicated server, target gate, and one-shot host
runner. It does not add an NFS start, boot, kexec, fastboot, flash, or
phone-storage command to the host runner.

## Exact-root NFS boundary

`serve-arch-successor-v2.sh` accepts only:

```text
/var/lib/rog5-network-root-arch-successor-v2
```

It requires:

```text
ALLOW_ARCH_SUCCESSOR_V2_NFS=1
```

The token check and complete
`verify-arch-successor-v2-export.sh` invocation both precede `etab=` and
every mutable host-state line. From `etab=` onward, the NFS/firewall runtime
is byte-identical to the accepted shared server; both suffixes have SHA-256:

```text
e6e0f8907ed86dbdd8be0ed58009ce34d6b157defbd8836706f1d1e2beef1a6a
```

The inherited runtime remains:

- NFSv4.2/TCP only;
- bound to `169.254.77.1:2049`;
- exported read-only only to `169.254.77.2`;
- isolated by the runtime drop-by-default firewall boundary;
- limited to 60–86,400 seconds; and
- fully cleaned up on exit.

The v2 server contains no accepted-v1 root, boot, ADB, fastboot, flash, or
phone-storage command.

## Actual unarmed refusal

A PolicyKit invocation against the exact v2 root with
`ALLOW_ARCH_SUCCESSOR_V2_NFS` absent returned:

```text
FAIL set ALLOW_ARCH_SUCCESSOR_V2_NFS=1 for the attended Arch successor v2 window
```

It exited with status 1 before the verifier or any host-state line.
Normalized before/after host state was byte-identical with SHA-256:

```text
a34f81c21eea49b27fa4ba36dcad14dfe5328ea70476430c06ef979773da405b
```

Normalization covered NFS/rpcbind/firewalld unit state, exports, listeners
on ports 111/2049/32767, the temporary mount, mountd, NFS threads,
`ip_nonlocal_bind`, all runtime firewalld zone state, IPv4 interface/prefix
identity, both protected roots' Btrfs read-only properties, and both seal
hashes.

Final state remained:

```text
nfs-server=inactive
rpcbind=inactive
exports=0
listeners=0
temporary_mount=absent
```

## First-boot target gate

`run-network-root-arch-successor-v2-gate.sh` requires separate exact gate and
reboot variables:

```text
ALLOW_ARCH_SUCCESSOR_V2_GATE=1
ALLOW_ARCH_SUCCESSOR_V2_REBOOT=1
```

Before watchdog handoff it requires:

- exact Linux 7.1.4, systemd PID 1, and `running` system state;
- headless `multi-user.target`, NetworkManager, key-only SSH, and the sleep
  inhibitor;
- successful udev coldplug, module loading, sysusers, and tmpfiles units;
- inactive graphical login, Chromium, ttyd, and VPN-hotspot services;
- OverlayFS `/`, exact read-only NFS lower, and `nodev,nosuid` tmpfs upper;
- zero physical block devices and zero block-backed mounts;
- exact USB `169.254.77.2/30` carrier and address;
- the exact v2 seal, package count, and isolated `rog5-agent`;
- a volatile machine ID and persistent root-only SSH host key;
- exact server-inhibitor, Chromium-isolation, and fail-closed v2 hotspot
  controls;
- every present backlight at brightness zero, or no backlight in the
  headless DTB;
- zero failed units and zero fatal kernel signatures; and
- the exact redacted metrics collector and watchdog-disarm helper.

The gate additionally pins the installed v2 hotspot controls:

```text
hotspot_script_sha256=5e2b4af39227f3afd37a494474faf982f1a87f3e8807406e47196d92b3bb079d
hotspot_service_sha256=8ea3d2509bb220d200816571f379c2992c5281771be22d1b84d49d4a716cd814
```

It emits the redacted runtime baseline, arms a separate 240-second transition
watchdog, atomically disarms the initial network-root watchdog, requests
exactly one normal `systemctl reboot --no-block`, and waits for disconnect.
It never writes phone storage.

## Strict-SSH host runner

`run-arch-successor-v2-live-gate.sh` does not start NFS or boot the phone. It
requires:

- separate live-gate and reboot variables;
- clean Git on `agent/linux-recovery-host`, synchronized with its remote;
- caller-owned mode-`0600` SSH key and known-hosts files outside Git;
- a caller-owned mode-`0700` private evidence directory;
- exact protected-root verifier, target-gate, and disarm-helper hashes;
- complete PolicyKit root verification before target contact;
- strict host-key checking under alias `rog5-arch-successor-v2`;
- exactly two root-owned mode-`0500` files staged in target tmpfs at
  `/run/rog5-arch-successor-v2-control`;
- an exact lower-root seal check before invocation;
- one target invocation and no retry;
- exact redacted headless/first-boot/reboot evidence; and
- an expected SSH disconnect followed by separate fallback and host cleanup
  verification.

The evidence log is created once at mode `0600`. No key body, fingerprint,
serial, address inventory, SSID, credential, or provider data enters Git or
this report.

## Offline revalidation

The dedicated v2 checks pass:

```text
PASS Arch successor v2 NFS window is exact-root, one-token, verifier-first, bounded, v1-independent, and non-flashing
PASS Arch successor v2 target gate is first-boot, screen-off, storage-free, fail-closed-hotspot-pinned, watchdog-handed-off, and one-reboot
PASS host Arch successor v2 gate stages two exact tmpfs inputs, invokes once, logs privately, and never retries
PASS Arch successor v2 export package=655 agent=isolated hotspot=fail-closed-v2 services=exact secrets=absent root-owned read-only Btrfs mode 0555 promotion=UNBOOTED_HOLD
PASS Linux rootfs tools pin signed input, preserve metadata, and avoid phone writes
```

All three accepted v1 control tests also pass. Bash/POSIX syntax,
ShellCheck at warning severity, mock call counts, one-reboot ordering,
`git diff --check`, protected-root verification, and v1 identity checks pass.

| Control | SHA-256 |
|---|---|
| dedicated v2 NFS server | `5101b94b472cce99b55414516003b08c306e758b27dbdf6efd3bff0ad96f93ac` |
| v2 NFS-window test | `537e43d89c3e27acdc637944c2b5a694c0d48f795c5c8262fecf8478664919e8` |
| v2 target first-boot gate | `bfacfeb83bf14468ea1fd349a3bc71ff443fb5c303a47fa2d761fa5291455c1f` |
| v2 target-gate test | `c99d6a4246dbf024fb8e470b7d7f5f51f251b9eb27b2388b3e6802aab3221974` |
| v2 strict-SSH host runner | `7151690f219d0d6e8a5df4a84d615e792e2c65d44e98e77211aa7ded80cc42a1` |
| v2 host-runner test | `8ddb6dab55e597cc54ef3a4d974d5f63380037fb336f1ef0359d3191ab3866f5` |
| v2 protected-root verifier | `d58ff1486ae3828633fea04d1d0ed96171716e332677a8d165cfba9f5d069185` |
| aggregate Linux-rootfs test | `1073c16a636753111fb84166e976695c8d6bda42f5741553d30ded46ae1fb98a` |

Accepted v1 identity remained:

```text
server_sha256=e3961cc441ae6cb75f1a3dcbbd5e4ccc99b31c67018159ac10f61c11f1548769
target_gate_sha256=50803d4c42619a0118d1458c694296d7151031befcf52110c23de80034bcd3c6
host_runner_sha256=6e76bde4ac491ff4d1185d9f50c5892b4e3bfd8ce9040135aeb174bfa81b673a
seal_sha256=6b5fa1b8e93b7e9f1ad41788ca524d5be6b4195c28ce85f70a28143360109eb4
```

## Connected fallback health

After the unarmed host test, strict read-only SSH to `rog5-fallback` returned:

```text
kernel=5.4.134-qgki-perf-00001-g6c308144c23e
id=alpine
version_id=3.24.0
brightness=0
```

No phone mutation occurred.

## Requirement for a future live decision

This control-plane acceptance is not a GO. A future attended cycle must first
choose between:

1. the v10 GPU diagnostic, which advances accelerated Plasma; or
2. this successor-v2 normal headless userspace root, which tests modern
   server userspace but does not prove GPU, Wi-Fi, VPN/hotspot, Plasma, KRDP,
   or battery behavior.

Either choice requires a fresh strict fallback preflight, clean synchronized
Git, exact protected-root and package checks, private SSH/evidence setup,
host-state cleanliness, and a new explicit user GO. One RAM-only cycle must
have no retry and no flash, return immediately to fallback, and prove complete
fallback and host cleanup.
