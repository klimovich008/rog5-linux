# VCNL36866 source/port contract — offline

Date: 2026-08-09
Starting repository SHA: `84bd7ca9304864040230feffd86bf0bb306b758d`

## Result

The first H4 sensor now has an exact hardware-free port boundary. Sixteen
retained ASUS 5.4 files establish the inherited ZS673KS board wiring and
wire protocol, while the exact clean Linux 7.1.4 source is classified
`port-required`. Synthetic future source/DT/runtime fixtures fail closed on
partial support, wrong topology or protocol, writable/control surfaces,
storage access, and authority.

This result created no kernel driver or build artifact, contacted no phone,
used no credential, and grants no boot or hardware authority.

## Test-first timing

- fail-first run before the verifier existed: 64 ms, expected failure;
- first green 15-case hostile and retained-source suite: 581 ms, pass;
- reviewed 16-case suite, including forbidden candidate surfaces: 575 ms,
  pass.

The first complete `scripts/host/test-repository-linux.sh ci` checkpoint
passed in 451,603 ms. The final complete rerun after metadata-path hardening
passed in 453,287 ms.
The final 17-case focused rerun after metadata-path hardening passed in
623 ms.

The final repository `ci` timing and ending SHA are recorded when this
checkpoint is committed.
