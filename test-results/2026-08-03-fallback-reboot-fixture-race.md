# Fallback reboot fixture race — offline correction

Date: 2026-08-03

Result: **PASS offline**. A timing-dependent test fixture, not the production
fallback reboot helper or the Generation-8 recovery artifacts, caused the
first Generation-8 live-profile GitHub run to fail. The fixture now drives its
deferred USB transition from an observed poll event and reports every negative
case by name. No phone, credential, privilege, network service, or signing key
was used.

## Failure classification

GitHub Actions run `30827808868` at commit `92c7099` passed the Generation-8
stable-recovery gate and every recovery fetch, host-controller, host-socket,
and init-policy suite. The final
`scripts/host/test-reboot-fallback-to-fastboot.sh` invocation then exited 1
without a diagnostic after approximately the test's normal runtime. The same
unchanged test passed locally and in replacement run `30828252815` at commit
`5b9b706`.

The final fixture shortened the production helper's 45-second timeout to
three seconds while the helper retained integer-second wall-clock deadlines.
Its `fallback-return` and `fallback-wrong-serial` cases removed the mock USB
identity and started an untracked background process that restored it after a
1.2-second sleep. On a loaded runner, the final useful poll could fall beyond
an effective deadline of only slightly more than two seconds. The helper then
returned a valid but different timeout classification. A bare expected-text
`grep` under `set -e` converted that mismatch into the observed silent exit.

## Correction

- The mock SSH transition now removes the USB identity and publishes a
  one-use restore marker containing the intended serial.
- The next mock `fastboot devices` poll consumes that marker and reconstructs
  the sysfs identity in safe order. The helper therefore observes one absent
  poll followed by one restored poll without depending on scheduler timing.
- The orphaned sleep/background writer is gone. Production helper code,
  timeout semantics, USB identity checks, restart2 syscall, and fastboot-only
  policy are unchanged.
- USB-mode, port/serial-boundary, fallback-count, and call-ledger assertions
  now emit the exact failing case, expected classification, observed output,
  and call counts.

## Verification

- shell syntax and ShellCheck: pass;
- twelve concurrent focused fixture runs: pass;
- complete `scripts/host/test-repository-linux.sh ci`: pass, including exact
  retained Generation-8 twin-artifact preflight;
- replacement GitHub run `30828252815`: recovery-core and QEMU jobs pass on
  the pre-correction documentation commit, independently proving the
  Generation-8 transition itself; and
- targeted Claude Opus race analysis identified the same deferred-writer and
  integer-deadline interaction and recommended the event-driven correction;
  and
- final Claude Opus review of the exact mock branches, loop selectors,
  environment propagation, and production poll order returned `PASS`.

The corrected commit still requires its own GitHub run before Generation-8
connected preflight or temporary boot admission.
