# V21 early observer profile-composition rejection

Primary question: can the exact V21 early-initramfs target be signed and
verified without rebuilding the ASUS wrapper kernel?

Earliest failed stage: native signed-bundle verification, before wrapper cache
materialization, candidate publication, admission, COMMIT, or phone contact.

Observed evidence:

```text
rog5-bundle-verify: non-diagnostic initramfs carries early-target reporter
```

Root cause: proven R2 composition defect. The canonical V21 source selected
`network-root-v1`, while its early-initramfs target intentionally embeds the
typed ACM reporter. The native verifier correctly requires
`diagnostic-initramfs-v1` for that composition.

Failure class: R2.

Was the candidate consumed?: no. No published V21 output, policy row, target
claim, COMMIT, or phone execution existed.

Was phone storage modified?: no; the phone was not contacted.

Why existing host tests missed it: phase and capability generation were
validated, but the canonical phase was not required to select the matching
bundle profile before credentialed assembly.

New regression:

- canonical generation rejects `early-initramfs` with `network-root-v1`;
- the deployment builder derives `diagnostic-initramfs-v1` from the generated
  phase;
- the shared deployment-builder contract pins that mapping.

Successor prerequisite: publish the corrected exact head and rerun signing
input preflight before one new signed V21 build. Do not reinterpret or reuse
the failed temporary build.
