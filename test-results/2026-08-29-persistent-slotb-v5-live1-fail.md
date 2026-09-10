# Persistent slot-B release v5 live 1 — FAIL (clean)

- Primary question: can the staged p23 service-state image mount read-write
  after P2 while p24 and every unrelated partition remain read-only?
- V5 p24 transfer completed once in 216.316 seconds; all four sparse chunks
  passed. Slot A remained active during transfer and no other partition was
  modified.
- V5 reached target USB in 34.660 seconds and exposed its exact Ed25519 SSH
  key in 138.284 seconds. NCM, direct `/30` routing, ping and key-only SSH
  passed.
- Classification: R3 exact BusyBox/POSIX shell incompatibility. Four
  predicates split the right-hand operand of `[` after `=`, so the first one
  emitted `[: missing ']'` and attempted to execute `4096`.
- The state service failed before opening its write window. P23, p24, the
  parent UFS disk and all 117 physical nodes remained read-only; no loop or
  residual mount existed.
- Regression: the helper contract now rejects every line ending in a bare
  `=`, and the corrected helper's read-only preflight passes on the exact live
  target.
- V5 must not be reused as the persistent-state candidate. The successor may
  change only the target initramfs; kernel, DTB, wrapper and slot-B loader stay
  byte-identical.
