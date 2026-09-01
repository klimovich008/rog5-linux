# Canonical selector-v2 recovery checkpoint

Result: **offline PASS; phone recovery still required**.

- The standalone selector-v2 loader passed two RAM boots but its boot_b-only
  installation (`f049dc19…`) produced no USB identity. Selector and p24 remained
  v1/V11; exact old-boot_b restoration is ready.
- The correction keeps canonical recovery responsible for USB, watchdog and
  fallback. Its tiny executor wrapper invokes the shared selector-v2 loader in
  `existing-recovery` mode; no selector implementation is duplicated.
- Shared logic retains exact p23-only trial state, mandatory relock, signed
  primary/fallback verification, Haven deactivation and kexec.
- Focused loader suites passed. Full local CI: 484.483 seconds.
- GitHub run `33557374234`: exact-head, merge compatibility, QEMU system and
  candidate publication all passed for `cba1ecf3`.
- Canonical recovery initramfs twins: `745925795d78c5edfb5a084ca4311f09471bde9785cbc71d4ce02a02fe1b48dc`.
- Exact installed wrapper kernel retained: `838425a8…`.
- Official AOSP avbtool 1.4 commit `c5066a96…` produced AVB twins
  `f2a73030aa792466ad6e779f7299b1357e3bd1ad1a969d6f31be48e44d794e50`.

The canonical artifact is unbooted and unflashed. Restore the proven old boot_b
first, verify V11, then RAM-test this candidate before any persistent update.
