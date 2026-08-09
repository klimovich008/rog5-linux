# Build retention inventory

Date: 2026-08-09

Result: **inventory only; no deletion performed.**

## Capacity and active-state check

- `build/`: 203,412,105,198 bytes (189.44 GiB), 90 top-level entries;
- `artifacts/`: 2,310,234,941 bytes (2.15 GiB);
- `/home`: 1,007,626,104,832 bytes total, 544,369,491,968 bytes used,
  463,239,835,648 bytes available (431.43 GiB, 55% used);
- active kernel/build/make/ninja processes: none;
- held locks below this repository's `build/`: none;
- idle containers: `rog5-dev` (15 hours) and `rog5-qemu-debug` (8 days);
- inert `.rog5-kbuild.lock` files exist in retained build directories, but no
  process holds them.

## Retention classes

| Class | Bytes | Disposition |
|---|---:|---|
| network-root deployment/lifecycle builds | 132,005,351,927 | Largest recovery target. Historical build trees are generally reproducible from tracked scripts, manifests, and reports, but exact directories must be matched to their evidence before quarantine. |
| thermal/suspend kernel builds | 42,042,321,519 | Includes clean twins and accepted compile-only evidence. Rebuildable, but retain until their tracked hashes/reports are mapped. |
| isolated VCNL partial build | 8,906,386,763 | Active uncommitted evidence: partial build A only. Preserve while the working-tree set is isolated. |
| retained source trees | 7,567,576,862 | Rebuildable from pinned source identities; some local CI paths discover the canonical accepted tree, so do not remove before proving reconstruction and CI fallback. |
| stable-recovery generation twins | 8,247,682,703 | Historical clean-twin evidence. Candidate bytes and identities are recorded elsewhere, but map every pair before quarantine. |
| QEMU builds/caches/runtime roots | 1,509,665,189 | Rebuildable test acceleration. Safe only after confirming no active container bind-mount depends on a selected path. |
| kernel ccache | 919,502,463 | Rebuildable cache; no release identity depends on preserving cache contents. |
| other build state | 2,213,617,772 | Mixed local tools, roots, reconstructions, logs, and small probes; classify individually. |

The 13 largest deployment/lifecycle directories are about 10.0 GB each and
account for most of the recoverable space. The retained VCNL directory is
incomplete, not authoritative, but remains current uncommitted work and is
therefore excluded from cleanup.

Authoritative identities and reproducibility records are primarily in the
tracked `manifests/`, `test-results/`, selected tracked `artifacts/`, and
artifact reconstruction/provenance files. Many byte artifacts are deliberately
ignored but hash-pinned by `manifests/artifacts.tsv`; ignored does not mean
disposable. `build/` itself is ignored and must be treated as rebuildable only
after its corresponding tracked identity and reconstruction path are proven.

## Safe recovery procedure

1. Recheck for active build processes, held locks, and container bind mounts.
2. Select explicit directories; never use a broad glob or recursive workspace
   target.
3. Map each selected directory to tracked source, config, manifest, artifact
   hash, clean-twin report, and reconstruction command. Abort on any missing
   mapping.
4. Record path, byte count, file count, and required hashes in a new tracked
   retention decision.
5. Move selected directories to a same-filesystem quarantine using explicit
   paths. Do not immediately delete them.
6. Run focused reconstruction tests and complete repository `ci` from the
   quarantined state.
7. Keep a cooling period. Restore by moving the exact quarantined directory
   back if any regression appears.
8. Permanently remove only the explicitly approved quarantine set after a
   separate operator review.

No cleanup command was run in this review.
