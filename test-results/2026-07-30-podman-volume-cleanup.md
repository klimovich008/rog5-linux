# Guarded Podman volume cleanup — 2026-07-30

Result: **complete; 87 approved volumes removed; retained closure verified**

This cleanup reclaimed host build storage only. It did not contact the phone,
use credentials, change Git history, remove tracked files, or use a broad
Podman/filesystem prune.

## Approved identity

Immediately before deletion, a fresh private
`rog5-host-storage-cleanup-plan-v1` inventory was generated against clean
repository commit `f6a4cb6fd788f5b8d134541aed2609ab4a562d0a`.
The guarded executor completed its full read-only preflight with:

| Property | Value |
|---|---:|
| Plan SHA-256 | `4a5ab6264d6fafec0f126c85750822d0afbda249c5c557c0b74ecf53a846e1ef` |
| Candidate count | 87 |
| Candidate-set SHA-256 | `9319e3a34558914b6c641b8f08542e45b1b8ed9359d4f8fd4c91da53694b4981` |
| Candidate allocated size | 373,321,981,952 bytes |
| Podman containers | 0 |
| Candidate mount counts | 0 |

The candidate-set identity exactly reproduced the previously reviewed and
approved set. The executor then re-ran the complete preflight and removed each
named volume individually with `podman volume rm` and without `--force`.
It reported `action=delete` and `status=complete`; no partial-cleanup stop was
reported.

## Retained closure

The post-delete Podman inventory contains exactly these 11 volumes:

```text
rog5-arch-pacman-cache
rog5-asus-v12a-source
rog5-asus-v13a-build
rog5-asus-v13a-source
rog5-asus-v13b-build
rog5-asus-v13b-source
rog5-asus-v14a-build
rog5-asus-v14a-source
rog5-asus-v14b-build
rog5-asus-v14b-source
rog5-mainline-v19-source
```

Every retained volume is local, has mount count zero, and remains below the
rootless Podman volume store. In particular, the accepted Linux 7.1.4 source
oracle `rog5-mainline-v19-source` remains available.

A fresh post-cleanup inventory records zero Podman prune candidates, 11
retained Podman volumes, and 29,136,179,200 allocated bytes in the Podman
volume scope. Its plan SHA-256 is
`69e3db76b22808e14309b3dee6b0b394713ee6ae15e8b9d7c3cae57fb22a595d`.

## Filesystem result

| Measurement | Before | After |
|---|---:|---:|
| `df -h` used | 664 GiB | 507 GiB |
| `df -h` available | 324 GiB | 474 GiB |
| Podman volume-tree apparent size | 375 GiB | 28 GiB |

The approximately 150 GiB increase in filesystem availability is smaller than
the candidate allocated-size sum because Btrfs extents are reflinked and
shared. The post-cleanup Btrfs estimate reports 508,466,638,848 bytes free.

## Recovery boundary

The removed volumes were detached, unreferenced generated state. Recovery is
by rebuilding from the retained source commits, tracked patches, manifests,
and container recipes. This operation is not recoverable as a filesystem
undelete.

The separate external development/cache candidates and in-repository artifact
candidates were not part of this approved tier and remain untouched.
