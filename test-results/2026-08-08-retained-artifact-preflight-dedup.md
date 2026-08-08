# Retained stable-recovery artifact-preflight deduplication

Result: **PASS; host-only, authority-free, and credential-free.**

This increment started at
`34c51d2e3e1880b1bc6d5634672e0646af65a46f`. No phone command, phone
storage access, credential access, signing, candidate issuance, or boot
occurred.

## Concrete defect fixed

The stable-recovery live-gate suite validated both offline and live policy
names correctly, but then reran the complete AVB and initramfs artifact
preflight for both names even though each pair enters one shared artifact
contract. Generations with byte-identical retained production twins were also
fully reverified for both build roots. This repeated nineteen approximately
ten-second checks without exercising a distinct artifact identity.

The hostile policy matrix still validates both names and every wrong identity.
The retained-artifact section now runs one canonical offline artifact preflight
per distinct byte tree. Existing explicit `cmp` checks establish equality for
production twin roots before one of them represents the pair. Generations
10--12 still preflight both suffixes because their bundle-a/b inputs are not
covered by the wrapper-tree comparison. Mutation preflights are unchanged.

## Regression and timing evidence

The new structural regression proves that every offline/live pair shares one
gate case, both policy names remain covered, and every generation has exactly
one canonical retained-artifact preflight site. Against the starting commit it
failed with:

```text
FAIL retained bytes are reverified once per offline/live policy profile
```

It passes on the corrected tree. The complete focused live-gate suite also
passes.

- prior untraced focused gate: 353,205 ms;
- diagnostic xtrace gate: 361,668 ms (85.687 s user, 112.744 s system);
- corrected untraced focused gate: 163,400 ms;
- focused reduction: 189,805 ms (53.7%).

The final `scripts/host/test-repository-linux.sh ci` timing and ending commit
are reported in the handoff for the commit containing this record.
