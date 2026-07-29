# Host storage audit — 2026-07-29

Result: **large reclaim is available; read-only plan complete; no deletion**

The host filesystem had 661 GiB used and 326 GiB free before cleanup. The
dominant footprint is reproducible ROG5 build state, especially detached
rootless Podman volumes. The phone was not contacted, booted, rebooted, or
modified during this audit.

## Normalized host plan

The new read-only planner was run against repository commit
`cc9aab504ba34fe1b3f76716d040aacb15e0b441` at
`2026-07-29T16:07:52+00:00`.

| Property | Value |
|---|---:|
| Plan format | `rog5-host-storage-cleanup-plan-v1` |
| Plan SHA-256 | `2b0b6b7146adec138b2791f78b123dc6b258a967a9d4f0a2fccf1fae30fc8339` |
| Podman containers | 0 |
| Inventoried units | 194 |
| Logical allocated size | 684,361,760,768 bytes / 637.36 GiB |
| Retain | 13 units / 44.59 GiB |
| Review | 29 units / 46.33 GiB |
| Prune candidate | 152 units / 546.43 GiB |

The plan was streamed through the summary checker and not stored as a tracked
machine snapshot. Re-run the planner for the exact current set immediately
before cleanup. Its timestamp and size measurements intentionally make each
snapshot unique.

| Scope | Units | Retain | Review | Prune candidate |
|---|---:|---:|---:|---:|
| Podman volumes | 98 | 10 / 25.16 GiB | 0 | 88 / 349.65 GiB |
| external ROG5 `dev` | 82 | 2 / 1.97 GiB | 29 / 46.33 GiB | 51 / 176.41 GiB |
| ROG5 cache | 14 | 1 / 17.46 GiB | 0 | 13 / 20.37 GiB |

These are logical allocated sizes reported by `du`, including shared Btrfs
extents. They cannot be added to predict exact filesystem free space. Earlier
Btrfs extent accounting measured approximately 331 GiB exclusive in the
volume scope, 174 GiB exclusive in the containing external-data scope, and
11 GiB exclusive in the cache scope. The guarded reclaim estimate remains
roughly 250–450 GiB; only after-delete filesystem accounting can make it
exact.

The ten retained volumes are the Arch package cache plus the currently named
ASUS v12a source and v13/v14 A/B source/build volumes. The planner derives
that set from tracked references rather than a hard-coded list.

## Dirty-worktree closure

The planner conservatively retained every dirty worktree. A separate temporary
Git-index reconstruction then proved that all four dirty worktrees reproduce
exactly from tracked patches:

| Inventory unit | Base commit | Tracked patch closure | Recorded `HEAD` diff SHA-256 | Result |
|---|---|---|---|---|
| cache PMIC GLINK build A | `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` | `0004` | `052a9f6c4cc7c0b094d28828ee8ebd6731323ea1f9e8e16a5641701a1ab40686` | exact |
| cache PMIC GLINK build B | `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` | `0004` | `052a9f6c4cc7c0b094d28828ee8ebd6731323ea1f9e8e16a5641701a1ab40686` | exact |
| A660 ucode patch tree | `43db8b9a01d2646dad45794956c90ea8f9dd3725` | `0013`, `0014` | `988fcaa69f3a01209ec4e34e523224c8826a2a083cc577e60a92eac89a979268` | exact |
| v10 GMU/CX patch tree | `d9ac316489f4258d389d6298659d5e9c22183400` | `0012`–`0016` | `adb308c5af7ba4fde8a2d8c3b26083e8659e3a60970076987b936eb528cb046e` | exact |

For every modified file, the blob produced in a temporary index by applying
the listed tracked patches matched the working-tree blob. This proves source
closure without modifying or staging the external worktrees. The planner
still retains them by policy; an approved cleanup may treat this report as the
additional closure evidence.

## In-repository candidate inspection

The separate artifact plan still admits only eight exact candidates totaling
13,616,275,456 allocated bytes (12.68 GiB): two failed A660 build trees and six
leaked recovery extraction/template trees.

The failed session-signal tree contains build products and no compact log,
JSON, Markdown, manifest, or root-level build metadata. The failed source-path
tree contains one 1,732-byte `build-meta.txt`; its SHA-256 is
`c467d3ae4e1059ef2dc0beb9be5dd72ca27bcc47a1371190c97096f3db20d5d7`.
Its important source, fragment, patch, config, image, module, and compiler
identities remain represented by tracked patches and verifier contracts.

One leaked recovery extraction has a 232-byte `SHA256SUMS` with SHA-256
`91a2ae046d4310bd4e2aa49debf6730c96e3fc8fe016193f4d550d889cc91ec5`;
the listed payload identities remain in the canonical v12 artifact manifest.
The other leaked units contain only extracted roots or kernel/ramdisk
templates. No candidate contained a unique diagnostic log.

## Safety outcome

- No file, volume, image, cache, trash item, or Btrfs extent was deleted,
  moved, deduplicated, or changed.
- No broad `podman system prune`, wildcard deletion, or recursive home-path
  command was prepared.
- Codex temporary state, unrelated project caches, libvirt images, desktop
  trash, proprietary inputs, and phone state remain outside scope.
- The current corrected headless candidate, its accepted inputs, pinned
  verifier images, and all tracked evidence remain retained.
- Cleanup requires a newly generated exact plan and fresh explicit approval.

See the [host cleanup runbook](../docs/host-storage-cleanup.md) for the reclaim
order, stop conditions, and recovery boundary.
