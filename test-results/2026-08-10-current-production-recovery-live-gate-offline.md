# Current production recovery live-gate profile — offline

Date: 2026-08-10

Starting repository SHA:
`adef48557e63e1cfc2d6ba8aef65035c9b017faf`

Recommendation: **HOLD**

No phone, fastboot device, ADB, ACM/NCM interface, phone storage, SSH
credential, signing credential, claim, policy row, flash, wipe, slot operation,
persistent installation, or phone boot was used.

## Concrete defect fixed

The joint retention verifier accepted the final project-key execution artifact
and the separate observation-only artifact, but the stable-recovery live gate
recognized only historical recovery profiles. It therefore had no exact
artifact-only path for the current production bytes. The gate also always
passed `-` as the recovery-init argument to its archive verifier, so it could
not select the newer `exact-a600000-v1` contract that proves the
repository-owned init and exact `a600000.dwc3` UDC logic.

The gate now has one
`headless-diagnostic-host-rendezvous-v3-haven-production-hold-v1` profile. It
accepts only:

- `policy-preflight`, which validates caller-supplied exact identities and
  emits `authority=none` without reading or changing boot policy; and
- `artifact-preflight`, which verifies the ignored local twins and exits before
  any fastboot query.

Connected `preflight` and `boot` fail as the first operation in the profile
case. Adding every legacy allow environment variable does not change that
result. The profile has no boot-image path, claim record, policy row, or
lifecycle selector.

## Exact production identity

| Input | SHA-256 |
|---|---|
| unsigned AVB recovery | `cba4e6e858c46a431eaa96a72af65e72ba601fa3169a63aad07864cc5122370d` |
| raw boot-v3 wrapper | `ea9e90fdbf1bfdbe75816462ae79897e6cf7749d9e87607be2b033b7cfb06517` |
| wrapper Image | `8a600acfc6f7e01f9eb932e0a04174079d6ee68142c44fad819fe96bbd34325d` |
| full recovery initramfs | `ab0a3ee219684c994af386cb60e5280dcc4269457b196f96ca3928acce691f0b` |
| recovery responder | `68142abd8daafed2f1d017bd0ae07407be9dcac17e57d2294a162d2b58bf2840` |
| bundle fetcher | `77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800` |
| bundle verifier | `33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef` |
| host bundle verifier | `03dae9292cd486f1a4ab92be74621593479eee0baa66eef7521c46ff39000de0` |
| runtime manifest | `54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc` |
| raw public project key | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |

The AVB descriptor is still `Algorithm: NONE`. Its salt is the exact raw-image
digest and its recomputed digest is
`9647a92d83bc1d3a71a59742d8aacd8d05b9e5105ac729c792e6577ef9af52eb`.
This is composition verification, not boot admission.

## Fail-first and hostile evidence

The new test failed against the starting commit in under one second because
the current profile did not exist. After correction, the identity-only path:

- accepts exactly the five external identities above;
- rejects an independent mutation of recovery, trust key, runtime manifest,
  host verifier, or bundle name;
- requires `exact-a600000-v1`, the fixed repository-owned recovery init, and
  `initramfs_verifier_expected=-`;
- proves the independent initramfs SHA-256 check occurs before archive
  verification;
- preserves `initramfs_verifier_expected=$expected_initramfs` for every
  historical profile; and
- requires connected preflight and boot to emit exactly one rejection line and
  no stdout before host or policy inspection.

A 22-file, 377 MiB physical sparse-copy fixture materialized only the inputs
read by the gate from the retained production output. Exact artifact preflight
and its hostile case passed in 10.343 seconds. A hostile copy changed all four
initramfs copies together, preserving twin and wrapper/source comparisons; the
gate still failed at the independent source-initramfs identity before invoking
the exact archive verifier. The existing complete stable-recovery live-gate
suite passed in 3.585 seconds.

An independent read-only Opus review initially reported the archive identity
as missing because it considered only the new diff. The existing gate already
checks `source_initramfs` before the verifier. Its review usefully exposed that
the new regression did not assert this ordering; the strengthened test now
does so behaviorally and textually. It also now proves historical behavior and
exact single-line connected rejection.

The final local
`REQUIRE_CURRENT_PRODUCTION_ARTIFACT=1 scripts/host/test-repository-linux.sh ci`
checkpoint passed in 312.509 seconds. The retained-artifact profile occupied
10.291 seconds within that run, so the current production-byte path was not
silently skipped. Exact-head publication is a subsequent repository-state
check and is recorded in the checkpoint handoff.

## Remaining boundary

No hardware timing, USB retention, NFS mount, SSH target, reset cause, or
ramoops retention result changed. The execution and observer claims are still
undefined and central policy has zero `allow` rows. A future candidate claim,
policy admission, lifecycle selector, connected preflight, and phone boot are
separate reviewed decisions. Recommendation remains **HOLD**.
