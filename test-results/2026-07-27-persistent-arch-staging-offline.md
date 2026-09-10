# Persistent Arch P1 staging acceptance

Date: 2026-07-27

Result: **PASS OFFLINE. The exact successor-v3 Arch root now has a guarded,
metadata-preserving, interruption-safe path to an atomically published but
unbooted `/rog5/roots/arch-a`. No persistent phone write was performed.**

## Fail-first sequence

The new fixture test was added before its implementation and initially
stopped on:

```text
FAIL missing executable persistent staging tool: .../stage-persistent-arch-root.sh
```

After implementing the stager and canonical tree tool:

```text
PASS persistent Arch staging is identity-pinned, path-safe, metadata-preserving, credential-clean, interruption-safe, sealed, and atomic
```

The suite requires the exact measured-layout inspector and rejects:

- an absent `ALLOW_ROG5_PERSISTENT_STAGE=1` arm;
- a wrong archive SHA-256 before any store directory is created;
- a parent-traversal member;
- a character-device member;
- an embedded SSH host-key path;
- a forged reserved seal path;
- an existing final generation;
- a stale interrupted `.partial` generation; and
- any seal-mode, file-content, or metadata change after publication.

It confirms preservation of mode `0640`, a `user.rog5` xattr, and a symlink.
An injected post-extraction interruption leaves only
`roots/arch-a.partial`; no final root or boot selector appears. A passing
tree receives a mode-`0444` seal and becomes `roots/arch-a` through one
same-filesystem `mv -T`.

## Exact production input

| Input | Size | SHA-256 |
|---|---:|---|
| `rog5-arch-plasma-network-root-7.1.4-successor-v3.tar.gz` | 2,007,033,670 | `a7c286491d2fde97e17024b36f514d595196975da1988c986f70819c964eb8d7` |
| `libarchive-tools-3.8.7-r0.apk` | 674,658 | `033049f6d53ff0d267341087adfe142d3e4abe8d3fcec6853e2ed7c95ce2d41e` |

The real archive passes:

```text
archive_entries=181242
archive_regular_files=130575
archive_directories=10150
archive_symlinks=38670
archive_hardlinks=1847
PASS successor v3 archive is manifest-pinned, path-safe, credential-clean, v2-preserving, and power-button-enabled
```

GNU tar is deliberately not used: it reports the archive's libarchive
capability and project xattr headers as unknown. The signed Alpine aarch64
APK passes `apk verify` in the pinned, network-disabled Alpine 3.24 image.
Its extracted `bsdtar 3.8.7` payload also executes from `/run` on the current
phone and resolves every required shared library, without installing a
package or changing Alpine's package database.

## Seal contract

`persistent-root-tool.py` hashes a canonical record for the root directory
and every descendant except the seal itself. Records include raw relative
path, entry type, mode, UID, GID, size, nanosecond mtime, link count,
regular-file SHA-256, symlink target, and every xattr name/value. This covers
POSIX ACL and file-capability xattrs without requiring a phone-side
`getfattr` binary.

The seal additionally records the generation, exact source archive identity,
entry/type/byte/xattr counts, and `promotion_state=UNBOOTED`. Staging does not
create `state/good` or `state/next`.

## Live boundary

Read-only SSH revalidation found the persistent Alpine fallback healthy on
`/dev/sda23`, with about 189 GiB free. `/rog5` was absent. The only phone-side
runtime test copied the signed `bsdtar` payload into tmpfs `/run`, executed
`--version` plus dynamic-link inspection, and removed that temporary file.

No archive was transferred to persistent storage, no package was installed,
no root was extracted, no selector was written, no kexec/reboot occurred,
and no block or boot partition was opened for writing. A fresh explicit
persistent-write instruction remains mandatory before live P1 deployment.
