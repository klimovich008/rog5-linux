# Legacy interactive ACM retirement — offline

Date: 2026-08-08

Result: **PASS — superseded interactive ACM and P2 live entry points fail
closed before authority, credential, host, USB, or phone inspection.**

## Defect

The framed stable-recovery lifecycle had replaced interactive ACM execution,
but three historical Python controls and two old P2 live-gate runners were
still directly executable. Their environment guards reduced accidental use;
they did not retire the obsolete execution path.

## Correction

- The public `main()` of `network-root-acm.py`, `persistent-root-acm.py`, and
  `persistent-root-entry-acm.py` now returns one exact retirement failure.
- Both historical P2 live-gate runners return the same failure immediately
  after defining their local `fail()` helper.
- Historical parser, transport, action, and runner bodies remain tracked for
  forensic review and fixture tests. They were not copied into a new path.
- The framed stable-recovery lifecycle remains unchanged and is the only
  active target-execution path.

## Regression evidence

The new three-case hostile suite initially failed against all five executable
surfaces in 0.107 seconds. After the correction it passed in 0.111 seconds and
proved that Python entry points do not call `uname`, command lookup,
`subprocess.run`, or USB discovery. It executes both shell entry points and
requires the exact retirement result before their first authority check.

The complete focused set passed in 2.206 seconds:

- the new retirement contract;
- all 24 retained ACM transport/parser fixture cases;
- the recovery wrapper authority test;
- all nine recovery-init policy tests; and
- the repository-runner contract.

The retirement contract is part of the shared repository test list and runs
in every tier.

## Safety boundary

No credential, external service, signing key, USB device, phone, or boot path
was accessed. No generation was issued, admitted, or consumed. Historical
artifacts and evidence remain unchanged.
