# Archive index

The pre-reduction tracked repository is preserved by the pushed annotated
tag:

```text
archive/pre-stable-recovery-2026-07-28
8e34d149d7346744588a48e848fe0fa33839d962
```

This is the canonical archive for consumed diagnostic tiers, superseded
scripts, intermediate reports, and the long-form documentation that existed
before the stable-recovery cleanup.

## Read without changing the working tree

List archived files:

```sh
git ls-tree -r --name-only archive/pre-stable-recovery-2026-07-28
```

Read one archived file:

```sh
git show archive/pre-stable-recovery-2026-07-28:path/to/file
```

Create an isolated read-only review worktree outside the current checkout:

```sh
git worktree add --detach /tmp/rog5-pre-stable-recovery \
  archive/pre-stable-recovery-2026-07-28
```

Remove that worktree through Git when review is complete:

```sh
git worktree remove /tmp/rog5-pre-stable-recovery
```

## Archived categories

- recovery wrapper generations before accepted v18;
- local keyed recovery diagnostics;
- consumed persistent-root P2 and entry-v1 tiers;
- consumed GPU and SMMU diagnostic generations;
- superseded live-gate runners and their intermediate reports;
- duplicate chronological material removed from `README.md`, `ROADMAP.md`,
  or `docs/current-state.md`;
- any tracked file later removed under the reduction plan in
  [repository audit](repository-audit-2026-07-28.md).

An archived control has no execution authority. Restoring source for study
does not restore permission to run its live action or boot its image.

## Not covered by the Git archive

The tag does not contain:

- ignored `artifacts/`, `build/`, `dist/`, or firmware files;
- private test evidence;
- SSH private keys, known-host records, API tokens, or personal data;
- external source/build trees.

Those files need a separate, reviewed retention plan. In particular, do not
delete a local artifact solely because its tracked builder or report is
available from this tag.
