# Host storage cleanup

The ROG5 project currently has enough reproducible host state to reclaim
hundreds of GiB without touching the phone, the Git history, proprietary input
archives, or the accepted corrected headless candidate. Cleanup remains
guarded by an exact generated plan for each tier. The central standing
authorization covers deletion only for the reproducible project-only cache or
disposable-artifact set admitted by that plan; no separate consent prompt is
needed.

## Completed tier-1 execution

The first guarded Podman-only cleanup completed on 2026-07-30. It removed the
exact approved set of 87 detached ROG5 volumes, retained all 11 referenced
volumes, and increased filesystem availability from about 324 GiB to 474 GiB.
The exact plan identity, candidate-set identity, retained closure, and
before/after measurements are recorded in the
[cleanup result](../test-results/2026-07-30-podman-volume-cleanup.md).

External development/cache units and the separate in-repository artifact
candidates were not part of that execution and remain subject to a fresh
reviewed plan under the central standing authorization.

## Completed cache-backed wrapper cleanup

The stable-recovery cache checkpoint completed a second narrow repository
cleanup on 2026-07-30. Immediately before deletion, every retained wrapper
config, Image, build-metadata, initramfs, raw image, and AVB image was compared
byte-for-byte with content-addressed entry
`05865d1cdbc7de08606d064316a7bd3e64d0ba6f9ba7218e17c73932f9e48333`.
The exact two corrected-headless A/B kernel object trees and the disposable
cache materialization/inspection copies were then removed.

The four generated directories represented 9,665,237,171 apparent bytes.
Btrfs filesystem availability increased by 3,695,415,296 bytes because
reflinks and compression made apparent and exclusive allocation differ. The
208 MiB verified cache entry and 662 MiB compact corrected-headless candidate
remain. The removed files are not directly recoverable, but the wrapper
outputs remain in the cache and the broad object trees are reproducible from
the pinned source, builder, config, initramfs, and scripts. See the
[cache proof](../test-results/2026-07-30-stable-recovery-wrapper-cache.md).

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

## Tier-1 Podman preflight

Generate a fresh private plan file, record its exact hash, and run the
non-destructive preflight:

```sh
plan=test-results/private/host-storage-plan.json
scripts/host/generate-host-storage-cleanup-plan.py --output "$plan"
plan_sha256=$(sha256sum "$plan" | cut -d ' ' -f 1)
scripts/host/cleanup-podman-volumes.py preflight \
  --plan "$plan" \
  --plan-sha256 "$plan_sha256" \
  --expected-candidate-count 87
```

The preflight requires an owned, bounded ordinary plan file that is not
group/other-writable, the exact clean repository commit, zero containers,
zero candidate mount counts, an exact current volume-name closure, a second
`podman volume inspect` of every candidate, the `rog5-*` project prefix, the
local volume driver/scope, empty volume options, mountpoints contained below
the exact hash-bound local store, unchanged volume creation timestamps,
unchanged allocated/apparent sizes, a plan age below 15 minutes, and the
expected candidate count. Inherited remote Podman connection selectors are
rejected. Non-ROG5 and non-local volumes are always retained. The preflight
prints the SHA-256 of the sorted candidate-name set and does not remove
anything.

The separate `delete` action is intentionally not shown as a copy-paste
command. It uses only `podman volume rm` without `--force`; it never deletes a
filesystem path. It requires the same complete preflight, the exact plan hash
and count, an independently supplied expected candidate-set SHA-256, and
`ALLOW_ROG5_PODMAN_VOLUME_DELETE` equal to the exact current plan SHA-256.
The environment guard is not authority by itself. The central standing
authorization supplies operator authority only after the candidate-set
identity is reviewed; regenerate and re-preflight immediately before setting
the guard.

If deletion ever stops after removing only part of the approved set, do not
reuse the stale plan. Preserve its output, regenerate inventory for the new
state, and review the remaining exact candidate set under the standing
authorization before continuing.

## Preservation rules

Retain these categories regardless of apparent size:

- every tracked file, Git tag, manifest, patch, redacted test report, and
  accepted artifact identity;
- the corrected headless target, signed-bundle inputs, stable recovery inputs,
  and the pinned container images used to verify them;
- the current accepted Linux 7.1.4 source oracle in rootless volume
  `rog5-mainline-v19-source`, until a replacement retained source is recorded;
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
   plan through the guarded tier-1 executor. Never use `podman system prune`.
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
