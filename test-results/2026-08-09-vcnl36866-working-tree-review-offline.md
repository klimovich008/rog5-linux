# VCNL36866 working-tree review — isolated

Date: 2026-08-09

Result: **HOLD and preserve.** The current uncommitted sensor set is not
candidate-ready and is intentionally excluded from the network-root
critical-path change. No file was stashed, discarded, or rewritten, and the
interrupted partial build was not resumed.

The retained build has only partial build A. It has no build B, candidate
manifest, clean-twin comparison, or release timing. The tracked repository
runner refers to untracked sensor tests, so the working tree is coherent only
as an all-or-nothing WIP island. The accepted-state documentation may continue
to say no integrated driver exists; this review is the explicit record of the
unaccepted implementation attempt.

## Standards review

- **P1:** `CONFIG_VCNL36866` does not depend on `PM`, although probe powers
  the sensor off and subsequent power-up relies on runtime-PM callbacks. A
  `CONFIG_PM=n` build can read an unpowered device and may unbalance cleanup.
- **P1:** the candidate builder removes its output lock on `HUP`, `INT`, or
  `TERM`, but those traps do not exit. An interrupted build can continue
  unlocked and admit a concurrent builder.
- **P2:** PM8350C L7 omits `regulator-initial-mode`; accepted SM8350 board
  definitions use `RPMH_REGULATOR_MODE_HPM`. The current exact-delta verifier
  forbids adding the property before this hardware/load decision is resolved.
- **P2:** the exact patch verifier merges all added lines before token checks.
  Required driver operations can be removed and copied into comments or
  another approved file without rejection.
- **P2:** DTB twins use ambient, unversioned host `dtc`/`fdtoverlay`, so equal
  same-host output does not bind release tool identity.
- **P2:** binding and driver are combined although upstream requires binding
  documentation as a separate preceding patch. The exact-four-file verifier
  forbids a possible `MAINTAINERS` addition, and Jonathan Cameron is assigned
  binding ownership without evidence of consent.
- **P3:** three `/bin/sh` scripts are syntax-checked with Bash, which can miss
  shell incompatibility.
- **Judgment:** the 248-line candidate builder substantially duplicates the
  dual-cell release lifecycle and spreads one integration across generic
  verifier, lifecycle, token-test, and runner changes.

## Specification review

- **P1:** the overlay requests exactly 3,300,000 µV, but PM8350C L7 uses the
  `1,504,000 + 8,000 * n` µV lattice. 3,300,000 µV is not representable, and
  the verifier currently freezes that exact invalid request.
- **P1:** only partial build A exists; the default static candidate test says
  PASS without materializing clean twins. There is no clean-twin evidence.
- **P1:** the tracked repository runner invokes three untracked files, so a
  tracked-only commit breaks a clean checkout.
- **P2:** the sensor specification still describes the driver as future work
  while the WIP contains driver, binding, overlay, and candidate pipeline.
  This is acceptable only while the WIP remains explicitly isolated.
- **P2:** binding maintainer attribution is unsupported.
- **P2:** the implementation freezes 14 mA proximity current and 55 ms timing
  without cited datasheet or behavioral-oracle evidence.

The specification review found no defect in inherited I2C default pinctrl,
cross-fragment phandle fixups, or the userspace-only interpretation of
read-only/minimal. The existing base I2C node already has its default QUP
pinctrl, and the current polled/raw-only scope does not use the IRQ.

## Local evidence

- source/port oracle: 17/17 PASS in 0.701 s;
- patch contract: 8/8 PASS in 0.973 s;
- DTB contract: 4/4 PASS in 1.036 s;
- static candidate contract: PASS in 0.314 s;
- Linux `checkpatch.pl`: zero errors, two warnings (new files/MAINTAINERS and
  binding-plus-driver patch split).

These passes prove current self-consistency, not hardware correctness or
release reproducibility. Sensor work stays frozen behind the stage-70
network-root blocker.
