# Repository audit — 2026-07-28

Status: **inventory and machine-readable plan complete; human review pending**

This audit was started because the project had begun to encode each hardware
experiment as another full script/report generation. That preserved evidence,
but it also obscured the current path and made unsafe historical artifacts
look runnable.

The audit used Git metadata, manifest joins, exact file/hash counts, and
repository-wide reference searches. A CodeGraph tool was not present on the
host, so no new indexing dependency was installed; `git`, `rg`, and small
read-only inventory scripts were sufficient. Claude Opus independently
reviewed the same repository and then corrected its recommendations against
the recorded live facts.

## Snapshot

These counts describe the pre-reduction checkpoint
`8e34d149d7346744588a48e848fe0fa33839d962`, not the smaller tree produced by
this audit.

| Area | Tracked files | Approximate lines |
|---|---:|---:|
| `scripts/device/` | 394 | 47,651 |
| `scripts/host/` | 119 | 18,480 |
| `test-results/` | 140 | 20,025 |
| `docs/` | 16 | 5,511 |
| `patches/` | 33 | 4,864 |
| whole repository | 763 | 93,515 |

Tracked content is only about 4.3 MB. The large footprint is ignored local
state:

| Local area | Size |
|---|---:|
| `artifacts/` | about 112 GB |
| `build/` | about 2.8 GB |
| entire working directory outside Git metadata | about 115 GB |

`artifacts/` contains 335,092 files in 22,038 directories. The artifact
manifest has 335 data rows, 38 duplicate-hash groups, 150 duplicate copies,
and about 2.98 GB of byte-identical duplication. Approximately 81.6 GB appears
to be reproducible or failed build/wrapper/repack trees, but that estimate is
not deletion authority.

The prose also had a clear duplication signal: `README.md`,
`ROADMAP.md`, `docs/current-state.md`, `docs/network-root.md`, and
`docs/test-plan.md` together exceeded 4,900 lines, with the first three
repeating much of the same chronology.

A 2026-07-29 recheck found approximately 113 GB under `artifacts/` and
53 GB under `build/`, or 166 GB total. The increase is ignored build state,
not tracked source, and reinforces the requirement for a referenced prune
plan before deletion.

The final read-only planner snapshot later that day measured 234,216,853,504
allocated bytes and 234,452,626,574 apparent bytes across 99 top-level units;
six nested recovery temporary units were classified separately. The difference
from the earlier estimate reflects a complete allocated/apparent measurement,
not tracked growth or cleanup.

## Archive checkpoint

Every tracked file before reduction is preserved by the pushed annotated tag:

```text
archive/pre-stable-recovery-2026-07-28
commit 8e34d149d7346744588a48e848fe0fa33839d962
```

This makes tracked-file reduction recoverable. It does **not** preserve
ignored binaries, build trees, private evidence, or credentials. Those local
files must not be deleted merely because the Git tag exists.

See [archive index](archive-index.md) for recovery commands and the category
boundary.

## Classification

### Active and required

These paths remain part of the current implementation or the closure proof
for its next replacement:

- `initramfs/recovery-init`, the v18 wrapper build/verifier path, and the
  twice-live-accepted v18 staging image identity;
- `scripts/host/recovery-linux.sh` and
  `scripts/host/reboot-fallback-to-fastboot.sh`;
- `initramfs/network-root-init`, `initramfs/network-root-shutdown`, and their
  build/verify/host paths, because accepted network-root v3 and successor
  roots still depend on them;
- `initramfs/persistent-root-init`, because it records the current P2 target
  contract even though no P2 live gate is authorized;
- the frozen staging archive with SHA-256
  `fcf147c4dc91323caaed4be8767545441f9df31323e4513e62c99ac20ac789e9`
  and every source/verifier pin that proves its identity;
- successor-v3 Arch packaging, screen/power controls, remote GUI services,
  VPN-hotspot v2 policy, and WCN6855 v1 offline/HOLD controls;
- the Linux 7.1.4 source/config/DTB/patch chain, accepted GPU evidence through
  the v10 GMU/CX runtime-PM boundary, and the v11 source-only next candidate;
- all `manifests/`, `patches/`, `dts/`, and `configs/`;
- the three machine acceptance records in `manifests/acceptance/` and every
  report or artifact hash that a still-active verifier reads directly.

`scripts/host/network-root-acm.py` is active only as a legacy dependency. It
must remain until the framed responder replaces it, but its execute actions
are not current live authority.

### Evidence that must remain easy to find

- v18 offline and twice-live staging/rollback reports;
- accepted network-root and successor-root closure reports;
- the current fallback identity, screen-off/remote-GUI, power, thermal, and
  storage-isolation reports;
- accepted WCN6855, VPN-hotspot, and A660 boundary reports;
- the rejected P2 and entry-v1 final reports that explain why no active gate
  exists;
- any report whose filename or hash is consumed by an active verifier.

Other intermediate reports remain recoverable from the archive tag. They can
be replaced on the active branch by a compact evidence index after reference
closure is machine-checked.

### Archive-only

These are historical and must never be treated as runnable:

- persistent-root entry-v1 and its sole consumed live attempt;
- every consumed P2 image/gate generation;
- superseded recovery wrapper generations before v18, including the local
  keyed v17 diagnostic;
- consumed GPUCC, Adreno SMMU, A660 registration/firmware/allocation/resume
  gate generations after their accepted evidence has been inherited by the
  next tier;
- duplicate version-per-step host runners and reports whose only surviving
  value is chronology;
- old Windows-only orchestration once its remaining package pin is ported to
  the Linux path and tested.

The files may still be visible on the active branch while a current verifier
references them. “Archive-only” means no execution authority; removal follows
only after replacement closure.

### Local deletion candidates, not yet deleted

The following ignored data is likely disposable:

- `.a`/`.b` duplicate outputs after byte identity and surviving inputs are
  recorded;
- failed or superseded wrapper/repack/build directories;
- consumed persistent-root bundles;
- six leaked recovery temporary trees under `artifacts/recovery-stage-v12/`
  containing roughly 259 files in total;
- caches that can be regenerated from pinned, signed inputs.

Historical network-root bundles, accepted recovery inputs, the frozen staging
archive, current Arch roots, firmware inputs, and anything named by an active
script remain retained.

No ignored artifact was deleted in this audit. A future cleanup must first
produce a machine-readable plan with, for every proposed path:

1. size and SHA-256 where applicable;
2. manifest status;
3. all tracked textual references;
4. whether the data is an input, accepted output, consumed output, duplicate,
   cache, or failed build;
5. a reproducibility command or an explicit reason it is irreplaceable.

The [retention report](../test-results/2026-07-29-artifact-retention-plan.md)
and
[machine-readable plan](../test-results/2026-07-29-artifact-prune-plan.json)
now satisfy the inventory step. They conservatively classify 51 units for
retention, 46 for review, and eight as prune candidates. All eight candidates
have zero tracked references and zero canonical-manifest rows, but still
require inspection for unique logs before any exact-path approval.

The plan must be reviewed before deletion. Hard-linking mutable artifact trees
is not an acceptable deduplication method; filesystem-native reflinks or
read-only content-addressed storage are safer future options. No ignored
artifact was deleted or deduplicated while generating the plan.

## Concrete problems found

### Artifact inventory was also boot authority

`scripts/host/recovery-linux.sh` previously accepted any unique
name/size/hash row from `manifests/artifacts.tsv`. That inventory includes
consumed, rejected, unsafe, and “never boot” images.

The fix separates knowledge from authority:

- `manifests/artifacts.tsv` continues to identify artifacts;
- `manifests/temporary-boot-images.tsv` is a deny-by-default allowlist;
- only the twice-live-accepted v18 AVB staging image is currently allowed;
- the wrapper now also requires exact fastboot product `lahaina`.

### Recovery control is an interactive shell

The device starts `sh -i` on `/dev/ttyGS0`, while host helpers send commands
and search terminal output for markers. Echo and connection loss can make
success ambiguous. A noninteractive shell with echo disabled would not solve
arbitrary execution, stale replies, or at-most-once behavior.

The required replacement is specified in
[stable recovery control plane](recovery-control-plane.md). It includes a
device-minted session, framed requests, a replay ledger, atomic execute claim,
host write-ahead intent, signed runtime manifests, and out-of-band outcome
classification.

### Retained ramoops needed a recovery reader

The fallback reserves ramoops memory but has no bound pstore/ramoops driver,
no `/dev/mem`, no `devmem`, `CONFIG_DEVMEM` unset, and no matching module
build environment. Relaxing its pstore-empty safety gate would not recover
evidence.

The stable recovery wrapper already has built-in `PSTORE_RAM` and the exact
reservation. Recovery source now snapshots pstore into RAM and exports
bounded outcome metadata through framed status; its offline tests pass.
Retention across target → bootloader → recovery remains unproven until a
controlled live cycle.

### Tests were fragmented

`scripts/host/Test-Repository.ps1` is a policy/secret scan, not a complete test
runner. `scripts/host/test-linux-rootfs-tools.sh` covers a useful but narrow
userspace subset. Hundreds of versioned tests are not collected by CI.

The stable recovery work therefore starts with a protocol/state/fault test
suite and one canonical offline runner before another image is built.

## Decisions

- Keep `fastboot boot` only; do not add flash paths.
- Keep the fallback slot and the guarded Qualcomm
  `RESTART2("bootloader")` helper unchanged.
- Permit v18 staging boot only; do not authorize any payload execution.
- Re-freeze recovery once after the responder and offline suite are complete.
- Deliver payload, DTB, and structured command-line policy at runtime under a
  signature verified by an in-image public key.
- Do not create a signing credential without separate user confirmation.
- Treat USB-C debug UART as an offline hardware investigation, not a promised
  capability.
- Do not start a 6.x/7.x rewrite “from scratch.” Continue the existing
  upstream Linux 7.1.4 board-enablement path, with each subsystem promoted by
  tests and rollback gates.

## Immediate next work

1. Review the eight prune candidates for unique diagnostic material; do not
   delete or deduplicate anything without separate exact-path approval.
2. Add and validate optional compiler caching plus reusable incremental kernel
   output trees without changing reproducible release outputs.
3. Pin the complete source and toolchain bootstrap for a fresh Linux host.
4. Rebuild the corrected-DTB candidate twice under a disposable trust root and
   repeat the hardware-free gate.
5. Ask separately before creating or using a production signing credential or
   temporarily booting the corrected candidate.
