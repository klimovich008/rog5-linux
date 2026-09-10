# Corrected DTB semantic oracle

Date: 2026-07-29

Result: **PASS hardware-free; authority=none; no phone action**

## Outcome

The corrected recovery DTB is now guarded by an exact semantic-delta
verifier, not only by source-pattern checks and a final artifact hash. A
candidate must preserve the complete ASUS board node set and every
non-allowlisted property byte-for-byte.

The verifier is part of the DTB builder and the hardware-free repository CI
tier. It cannot sign, package, boot, flash, or access the phone.

## Enforced delta

`verify-recovery-dtb-delta.py` parses the flattened device tree directly. It
requires:

- one ordinary, non-symlink DTB below the 2 MiB bound;
- exact FDT v17/v16 header identity and file size;
- terminated, aligned, in-bounds, non-overlapping reservation, structure,
  and strings blocks;
- a complete token stream with one root, no duplicate nodes or properties,
  bounded property data, and bounded ASCII property names;
- exact `asus,rog-phone5`, `qcom,sm8350` board identity;
- identical base and candidate node sets;
- byte-identical values and presence for every unapproved property;
- the five isolated RMTFS/GPU/GMU/GPUCC/Adreno-SMMU states;
- the reviewed USB1/USB2-PHY high-speed-only state; and
- one exact USB2 PHY phandle, frozen against the base DTB.

The candidate must make at least one semantic change. This rejects a silently
unapplied overlay.

The builder creates its candidate in a same-filesystem staging directory,
completes the semantic and existing hardware checks before publication, then
renames the verified DTB into place. `SIGINT` and `SIGTERM` exit instead of
resuming after cleanup.

## Retained real-artifact oracle

The historical rejected v1 object and accepted v3 object were compared
directly:

| Object | Size | SHA-256 |
|---|---:|---|
| rejected network-root v1 | 102,774 | `255c5ac199b0412c499aae39bb596507b934e71c003396040d4952f0c5ffabe6` |
| accepted network-root v3 | 102,870 | `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46` |

The verifier reported `changed_properties=4`. Those exact changes add
`status = "disabled"` to:

- `/reserved-memory/memory@9b800000`;
- `/soc@0/clock-controller@3d90000`;
- `/soc@0/gmu@3d6a000`; and
- `/soc@0/iommu@3da0000`.

The GPU node was already disabled in v1. No node or other property changed.
This matches the documented root cause of the rejected signed transaction.

The current retained ASUS base was also exercised:

| Object | Size | SHA-256 |
|---|---:|---|
| current ASUS base | 102,887 | `49be8b691a057e541d4dd32c8272b05eab9a4fef93ea58b8c4c78f59b92bcfbe` |
| generated recovery candidate | 103,038 | `ebcad2f865b7383c832a9bc3205891ceb7d6c8d7cc93bffdbb35017f7b54ae57` |

That comparison reported `changed_properties=10`, all inside the fixed
isolation/USB allowlist. The base already had the GPU disabled, so that
allowlisted property was a no-op.

## Regression coverage

The CI fixture compiles a symbol-bearing ROG Phone 5 base and the real
recovery overlay. It rejects:

- removal of each required isolation state, with the exact source-policy
  diagnostic;
- an unrelated root property;
- an unrelated GPU property added through the overlay;
- an extra DT node;
- re-enabled GPUCC;
- a USB `phys` property redirected to the QMP PHY;
- a truncated DTB;
- leaked publication staging directories; and
- a TERM-interrupted build that resumes or publishes output.

Each negative test requires the intended `FAIL` diagnostic; an unrelated
crash or command failure cannot satisfy the test. The complete
`scripts/host/test-repository-linux.sh ci` tier passed after integration.

## Claude advisory review

The Claude wrapper health probe returned `CLAUDE_OK`, proving that
authorization and the safe wrapper were functioning. Separate self-contained
Opus reviews returned `NO_BLOCKERS` for the strict parser and semantic
comparison.

The shell review found two blockers: signal traps could resume execution, and
negative tests accepted arbitrary failures. Both were corrected and covered
by exact regressions. A final self-contained closure review returned
`NO_BLOCKERS`.

One intermediate review attempted to print a disabled Bash-tool invocation
and fabricated file contents. The empty-tool wrapper did not execute it, and
that output was discarded rather than treated as evidence. The earlier
combined review also timed out; the wrapper correctly reported timeout rather
than misclassifying it as authentication or security failure.

## Boundary

This checkpoint creates no live signing credential or boot authority. The
corrected candidate remains offline. A new signed temporary boot still
requires fresh, separate user authorization.
