# Arch successor v2 protected export — offline result

Date: 2026-07-27

Result: **PASS OFFLINE. The exact successor-v2 archive now has a separate,
root-owned, read-only Btrfs export with a byte-exact recursive seal. The full
verifier passes and rejects four independent copy-on-write mutations. The
accepted successor-v1 export is unchanged.**

No phone command, boot, kexec, flash, module load, NFS export, host firewall,
interface, listener, or service change occurred. PolicyKit created the v2
subvolume without a sudo password. The root is not present in any server
allowlist and remains `UNBOOTED_HOLD`.

## Exact protected root

| Property | Value |
|---|---|
| path | `/var/lib/rog5-network-root-arch-successor-v2` |
| filesystem object | Btrfs subvolume |
| ownership and mode | `0:0:0555` |
| Btrfs property | `ro=true` |
| archive | `artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor-v2.tar.gz` |
| archive size | `2,007,001,876` bytes |
| archive SHA-256 | `0da5f1dbc05588fcda444b6ba6d8a66db8fa9749691b1f7e37132de9e8a88078` |
| seal | `/etc/rog5/arch-successor-v2-export` |
| seal mode | `0:0:0444` |
| seal SHA-256 | `f7c39890f2777d9d95f963bf802a09fe3cbfdb863ac9f80392a61d01867796c4` |
| recursively sealed entries | `181,239` |
| recursive tree SHA-256 | `476fba2af8ec064e6f4d8b11abe6c76b2430a6bcd865070b27bcddd6f833564b` |
| package count | `655` |
| kernel release | `7.1.4-g7a5cef0db479` |
| promotion state | `UNBOOTED_HOLD` |

The recursive identity covers path, type, mode, owner, group, size, mtime,
symlink target, every regular-file SHA-256, ACLs, and xattrs on one
filesystem. Only the seal file itself is excluded so it can carry the
resulting tree identity.

## Identity and credential policy

The protected root contains one dedicated Ed25519 SSH host key generated
during export creation. The private half is root-owned mode `0600`; the public
half is mode `0644`, and `ssh-keygen -y` reproduces it. The seal records only
the public-key SHA-256:

```text
a019add68b0ee84dd9af87ee24c77421c61e4a12da583fe0fc056b268bd1589c
```

The archive's approved public login key remains identical for `root` and
`rog5`. It contains one valid public-key line and no private-key material.
The verifier also requires the absence of a WireGuard profile,
NetworkManager connection, machine ID, KRDP setting, KWallet, and transient
pacman socket.

The seal pins:

- archive size and SHA-256;
- embedded project commit and kernel release;
- package count and requested-package-list hash;
- isolated Chromium service hash;
- successor-v2 hotspot script and service hashes;
- offline rootfs report hash;
- complete successor-v2 staged-root verifier hash;
- dedicated SSH host public-key hash;
- complete recursive tree identity; and
- `UNBOOTED_HOLD`.

## Full verification

The verifier independently requires:

- one exact manifest archive identity and unchanged source/report hashes;
- Btrfs subvolume, `ro=true`, root ownership, and mode `0555`;
- byte-exact seal reconstruction;
- 655 pacman entries and one matching Linux 7.1.4 module tree;
- AArch64 systemd, pinned A660 firmware, and preserved xattrs;
- locked `root`, `rog5`, and isolated `rog5-agent` accounts;
- key-only SSH and a dedicated matching host-key pair;
- exact Chromium and fail-closed hotspot files;
- NetworkManager/headless service enablement and disabled optional services;
- empty first-boot mount points and machine identity;
- no block-device `fstab` entry; and
- no VPN, desktop, or first-boot network credentials.

The direct root invocation returned:

```text
PASS Arch successor v2 export package=655 agent=isolated hotspot=fail-closed-v2 services=exact secrets=absent root-owned read-only Btrfs mode 0555 promotion=UNBOOTED_HOLD
```

## Mutation rejection

The test harness created four disposable writable Btrfs snapshots. It changed
one target in each snapshot, set the snapshot read-only, and required the full
verifier to reject it:

1. export seal;
2. `/usr/local/sbin/rog5-vpn-hotspot.sh`;
3. `/etc/systemd/system/rog5-vpn-hotspot.service`; and
4. `/etc/passwd`.

All four were rejected. Each snapshot was made writable only for deletion,
then removed. No mutation directory remains. The final harness result was:

```text
PASS Arch successor v2 export is manifest-pinned, recursively sealed, read-only Btrfs, mutation-tested, v1-independent, unbooted, and non-flashing
```

## V1 and host isolation

Before and after v2 creation and mutation tests, the accepted v1 root remained
root-owned mode `0555`, Btrfs `ro=true`, with unchanged seal SHA-256:

```text
6b5fa1b8e93b7e9f1ad41788ca524d5be6b4195c28ce85f70a28143360109eb4
```

Post-check state was:

```text
nfs-server=inactive
rpcbind=inactive
nfs_mounts=0
nfs_listeners_111_or_2049=0
mutation_leftovers=0
```

The v2 prepare and verifier contain no accepted-v1 path and cannot clean up
outside an exact
`/var/lib/rog5-network-root-arch-successor-v2.partial.*` target.

## Control identities

| Control | SHA-256 |
|---|---|
| export preparer | `050bf7f8503b12c480a7d8edb2b08a261af5e73ab3d84288757daa9708d974dd` |
| export verifier | `d58ff1486ae3828633fea04d1d0ed96171716e332677a8d165cfba9f5d069185` |
| export contract/mutation test | `df60154f9f5d657a802b2b4586bb7bf95045f46a881fb8f1bcbcd2e5e1ca4004` |
| archive contract | `a255aa92e50dcb145e0521d72f09bd80d7e9770753b5db4032a0bbfe343166ae` |
| aggregate Linux rootfs test | `f31c662abfe4a8a64e78aa545557597e6ea7a610884542ac8a97947ef423e52e` |

## Promotion boundary

Protected-export acceptance grants no NFS or boot authority. Before any live
cycle:

1. create separately versioned v2 target and one-shot host-runner controls;
2. add one exact v2 root to a verifier-first, explicit-token, bounded NFS
   case;
3. prove an unarmed invocation changes no host state;
4. repeat persistent-Alpine identity, fallback-health, and root verification;
5. conduct a fresh HOLD/GO review; and
6. require explicit user `GO` before opening NFS or booting.

The current live choices remain separate: the v10 RAM-only GPU diagnostic or
a future successor-v2 headless userspace trial. Neither is authorized by this
report.
