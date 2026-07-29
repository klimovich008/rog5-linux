# Artifact retention plan — 2026-07-29

Status: **plan generated; human review pending; no deletion or deduplication**

The [machine-readable plan](2026-07-29-artifact-prune-plan.json) is a
read-only snapshot of ignored artifact and build state at repository commit
`c60bd458b710a40795e5381fcf8b54fb8accf5b3`.

| Property | Value |
|---|---:|
| Plan SHA-256 | `9772029f897174feeb65100018cc598059f992f166e878152291980f031221e4` |
| Plan size | 226,982 bytes |
| Top-level units | 99 |
| Separately scoped nested temporary units | 6 |
| Top-level allocated size | 234,216,853,504 bytes |
| Top-level apparent size | 234,452,626,574 bytes |
| Retain | 51 units |
| Review | 46 units |
| Prune candidate | 8 units |
| Candidate allocated size | 13,616,275,456 bytes |
| Candidate apparent size | 13,490,033,655 bytes |

All eight prune candidates are either failed build units or leaked temporary
units, and each has zero canonical-manifest rows and zero tracked textual
references. This is necessary evidence, but it is not deletion authority.
Directory contents were not content-hashed, canonical manifest hashes were
recorded but not reverified, and a failed or temporary unit may still contain
unique diagnostic logs.

The other decisions are deliberately conservative:

- `retain` means the unit is named by tracked source/evidence or the canonical
  artifact manifest;
- `review` means the planner could not prove either retention or safe
  reproduction;
- `prune_candidate` means only that the narrow automated eligibility rules
  passed.

No artifact or build path was deleted, modified, hard-linked, or deduplicated.
The generator has no deletion mode and refuses to overwrite an existing plan.

Generate a new snapshot at a new path with:

```sh
scripts/host/generate-artifact-prune-plan.py \
  --output test-results/YYYY-MM-DD-artifact-prune-plan.json
```

Before any cleanup, inspect all eight candidates for unique logs and secrets,
map each of the 46 review units to an exact reproducer or an explicit
irreplaceability reason, then request separate approval for the exact paths
and operation.
