# Arch Plasma/server successor protected export — offline result

Date: 2026-07-27

Result: **PASS OFFLINE / HOLD LIVE. The exact successor archive is now
manifest-pinned and extracted into a new root-owned, read-only Btrfs
subvolume. Its recursive verifier passes, and three copy-on-write mutations
are rejected. The root is deliberately absent from the NFS server allowlist
and has not been booted.**

No sealed diagnostic root was read as an input or modified. No NFS, RPC,
firewall, network-interface, container, boot, kexec, reboot, fastboot, flash,
or phone-storage action ran. PolicyKit elevated only the bounded host
preparation and mutation-test commands; no password or private-key material
was printed or copied into the repository.

## Exact protected state

| Property | Value |
|---|---|
| protected root | `/var/lib/rog5-network-root-arch-successor-v1` |
| filesystem state | Btrfs subvolume, `ro=true` |
| root metadata | `root:root`, mode `0555` |
| seal | `/etc/rog5/arch-successor-v1-export`, `root:root`, mode `0444` |
| seal SHA-256 | `6b5fa1b8e93b7e9f1ad41788ca524d5be6b4195c28ce85f70a28143360109eb4` |
| recursive entries | `181239` |
| recursive tree SHA-256 | `167d139e76f2b164e9aaa72c480f547a5e3d7948ed5e82f8aadbe5367095079f` |
| promotion state | `UNBOOTED_HOLD` |

The source archive remains:

```text
artifacts/arch/rog5-arch-plasma-network-root-7.1.4-successor.tar.gz
size=2006999039
sha256=88c2d671a26f577aef963212cda17bc61baa888d77d0c1aaf1ca25c6fb3ad62a
```

That identity now has exactly one row in `manifests/artifacts.tsv`. The
archive remains ignored locally because GitHub cannot store this ordinary
2 GB Git object; the public repository contains its reproducer, exact
identity, and verification evidence.

## Preparation gate

`prepare-arch-successor-export.sh`:

1. requires PolicyKit root and the exact final path;
2. accepts only the repository-local manifest-pinned archive;
3. rechecks its byte size and SHA-256 before extraction;
4. requires at least 12 GiB free and Btrfs under `/var/lib`;
5. refuses an existing final or partial root;
6. creates a root-inaccessible staging subvolume;
7. extracts ACLs, xattrs, file flags, numeric ownership, and modes;
8. installs the exact key-only SSH policy;
9. proves the archive contains no SSH host key;
10. generates one dedicated persistent Ed25519 host identity in the protected
    root without exposing it;
11. seals the archive, package, service, report, host-identity policy, entry
    count, and recursive tree identities;
12. changes the root to mode `0555` and the subvolume to `ro=true`;
13. runs the complete protected-root verifier; and
14. atomically renames the verified subvolume to the final path.

Failure cleanup is restricted to the exact PID-suffixed staging path and uses
Btrfs subvolume deletion. It cannot replace or remove the sealed v10 root.

## Recursive verifier

The recursive digest covers every entry except the self-referential seal. It
includes:

- sorted path, type, mode, numeric UID/GID, size, mtime, and symlink target;
- SHA-256 for every regular file;
- every non-trivial numeric ACL; and
- every extended attribute without following symlinks.

The verifier separately requires:

- the exact manifest row and local archive identity;
- Btrfs `ro=true`, root mode `0555`, and seal mode `0444`;
- byte-exact build provenance, kernel release, requested packages, and 655
  installed package records;
- AArch64 systemd, one exact module tree, module dependency metadata, and all
  pinned A660 firmware;
- locked `root`, `rog5`, and isolated `rog5-agent` accounts;
- one approved public client key and no private client key material;
- one internally consistent, root-only persistent SSH host-key pair;
- current SSH, Chromium-isolation, VPN-hotspot, screen-off, and USB-network
  policy;
- headless default with Chromium, ttyd, and hotspot disabled;
- empty machine identity and no VPN, NetworkManager, KRDP, or KWallet secret;
  and
- empty pseudo-filesystem directories and no block-device `fstab` entry.

The clean protected root passed twice: once during preparation and once before
the mutation suite.

## Fail-closed mutation evidence

The privileged contract created three writable Btrfs snapshots from the
read-only source. It independently altered:

1. the protected-export seal;
2. the production VPN-hotspot unit; and
3. the account database containing the isolated agent identity.

Each snapshot was returned to `ro=true`; each verifier invocation rejected
the mutation; and each snapshot was then deleted. No mutation touched the
protected source and no mutation directory remains.

Current control hashes are:

| Control | SHA-256 |
|---|---|
| preparer | `8821d67cf35ed62569c35a022ea06ae5df3b73158aff5b2f06941d28e6cbf9d4` |
| recursive verifier | `6176b4172c7ad3a0338686eb4c3fd30a6cbcb32c6237c190317da4a4b197a983` |
| fail-first/mutation contract | `ad5f7d9ebd0b59b1e91e97c0b192c59303beb355cf25503b03f173b2c580fbbc` |
| aggregate Linux-rootfs test | `176b621740a4d6f159ba0994a986c10ba40ce7529f65dcbce3b1d7fd2aa3cdb2` |

The fail-first commit preceded the implementation and initially stopped on
the absent preparer.

## Inactive live boundary

After all tests:

- `nfs-server.service` and `rpcbind.service` were inactive;
- there were zero exports and zero running Podman containers;
- `serve-network-root.sh` still had no successor-root case;
- the phone remained on the known Alpine fallback kernel;
- fallback SSH remained reachable; and
- panel brightness remained `0`.

The protected root therefore has no live authority. Before any successor NFS
window or boot:

1. resolve the separate v10 GPU diagnostic HOLD or explicitly choose a
   headless-only userspace trial;
2. add a fail-first, one-token, exact-root NFS allowlist and runner;
3. repeat strict fallback identity and host-cleanliness preflight;
4. obtain a fresh explicit GO for one RAM-only attended cycle; and
5. require first-boot tmpfiles/sysusers, coldplug, SSH persistence,
   screen-off, resource, thermal, and clean-reboot evidence.

GPU acceleration, Plasma/KRDP, Wi-Fi AP operation, and real external VPN
configuration remain unaccepted live features.
