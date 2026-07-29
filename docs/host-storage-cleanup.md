# Host storage cleanup

The ROG5 project currently has enough reproducible host state to reclaim
hundreds of GiB without touching the phone, the Git history, proprietary input
archives, or the accepted corrected headless candidate. Cleanup remains
disabled until the exact generated plan is reviewed and explicitly approved.

## Current finding

The 2026-07-29 audit measured 661 GiB used and 326 GiB free on the 991 GiB
host filesystem. The dominant ROG5 areas are:

| Scope | Logical size | Important physical-allocation fact |
|---|---:|---:|
| repository `artifacts/` and `build/` | about 228 GiB | 8 narrow candidates total about 12.7 GiB allocated |
| rootless Podman volumes | about 375 GiB | about 331 GiB is Btrfs-exclusive |
| external ROG5 development trees | about 219 GiB | about 174 GiB is Btrfs-exclusive for the containing data root |
| ROG5 cache | about 38 GiB | about 11 GiB is Btrfs-exclusive |
| Codex temporary state | about 17 GiB | out of scope while Codex is running |
| desktop trash | about 5.5 GiB | unrelated to the project and out of scope |

Logical sizes overlap because the filesystem uses Btrfs reflinks and
compression. Only a post-cleanup filesystem measurement can report the exact
physical reclaim.

## Generate the two read-only plans

Run both planners from the repository root:

```sh
scripts/host/generate-artifact-prune-plan.py
scripts/host/generate-host-storage-cleanup-plan.py
```

The artifact planner covers ignored `artifacts/` and `build/` units inside the
checkout. The host planner covers only:

- top-level units below the ROG5 external `dev` directory;
- top-level units below the ROG5 cache directory;
- rootless Podman volumes.

The host plan deliberately publishes stable identifiers such as
`rog5-dev:UNIT` and `podman-volume:NAME`, not absolute home-directory paths.
Both planners are read-only, have no deletion mode, refuse to overwrite an
existing output, reject sensitive-looking unit names, and state that a prune
candidate is not deletion authority.

## Preservation rules

Retain these categories regardless of apparent size:

- every tracked file, Git tag, manifest, patch, redacted test report, and
  accepted artifact identity;
- the corrected headless target, signed-bundle inputs, stable recovery inputs,
  and the pinned container images used to verify them;
- any external unit or volume named by tracked project source or evidence;
- any unit containing an uncommitted Git worktree unless a separate closure
  proof reconstructs it byte-for-byte;
- the Arch package cache and active ASUS source/build volumes that current
  scripts name;
- proprietary firmware and stock-image inputs;
- Codex desktop temporary state while the application is running;
- unrelated caches, virtual machines, downloads, and desktop trash.

The four modified external kernel worktrees in three inventory units are not
unique. Two cache worktrees are reconstructed exactly by patch `0004`, one
development worktree by patches `0013` and `0014`, and one development
worktree by patches `0012` through `0016`. Every modified file has the same
Git blob identity after applying those tracked patches to its recorded base
commit. This closure permits their large copies to be reviewed as reproducible
later; it does not itself delete them.

## Recommended reclaim order

1. Preserve a fresh plan, its SHA-256, the filesystem measurements, all compact
   logs, and the two external worktree closure records.
2. Remove only detached, unreferenced Podman volumes named in the approved
   plan. Never use `podman system prune`.
3. Remove only approved unreferenced generated units in the external ROG5
   development and cache scopes.
4. Remove the eight exact failed/temporary units admitted by the separate
   artifact plan.
5. Re-run both planners, repository CI, and Btrfs/filesystem measurements.
6. Resume the corrected headless live gate only after the build and verifier
   inputs still pass.

Do not use wildcards for cleanup. A nonzero Podman container count, nonzero
volume mount count, new tracked reference, dirty worktree, sensitive-looking
name, linked inventory root, or changed candidate set stops the operation and
requires a new review.

## Recovery and rollback

Deletion of generated host state is irreversible as a filesystem operation.
Recovery means rebuilding from the pinned source commits, patches, manifests,
and container recipes. That is why the first cleanup execution must use the
exact reviewed identifiers and capture before/after evidence. The phone,
fallback slot, phone storage, and boot state are not part of this runbook.
