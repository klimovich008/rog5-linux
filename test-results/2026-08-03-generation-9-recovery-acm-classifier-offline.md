# Pre-Generation-9 recovery ACM classifier — offline result

Date: 2026-08-03

Result: **PASS for the host-only bounded classifier and focused integration;
no Generation-9 artifact has been issued or admitted.**

## Purpose

The sole Generation-8 RAM boot transferred its complete signed bundle but
stopped before `PREPARED` because the recovery ACM identity did not remain
stable. The old timeout preserved safety but collapsed every enumeration
failure into one generic message. This correction makes the next one-shot
failure actionable without collecting private USB identities.

## Implemented contract

`scripts/host/stable-recovery-control.py` now samples recovery ACM inventory
into exactly eight states:

- `absent`;
- `inspect-error`;
- `product-mismatch`;
- `node-mismatch`;
- `duplicate`;
- `unreadable`;
- `read-only`; and
- `exact`.

An uninspectable ACM node fails closed even when another node appears exact.
Only one readable and writable character device with the fixed recovery USB
identity can enter the stability dwell. The candidate must retain the same
path, device number, `DEVPATH`, `ID_PATH`, and `ID_SERIAL` for two seconds and
then pass one final observation, matching the prior admission behavior.

On timeout the controller emits only:

- fixed state names and sample counts saturated at 999;
- at most 16 state transitions plus an explicit truncation flag; and
- fixed labels for identity fields that changed.

It never emits the observed path, serial, udev value, raw USB event, or caught
inspection error. This is diagnostic output only; it does not add a retry,
relax selection, or authorize a candidate.

## Verification

- `python3 -m py_compile scripts/host/stable-recovery-control.py scripts/host/test-stable-recovery-control.py` — PASS.
- `python3 scripts/host/test-stable-recovery-control.py` — PASS, 29 tests.
- `python3 scripts/host/test-run-minimal-headless-live-cycle.py` — PASS, 62 tests.
- constrained, tool-free Claude Opus review identified test/classification
  gaps; opaque-node, node-type, invariant, saturation, and formatting findings
  were applied. Its fail-fast claim was rejected against the old source because
  the old wait loop also caught selection `RuntimeError`s until deadline.
- `scripts/host/test-repository-linux.sh ci` — PASS, complete local tier.
- GitHub Actions `Offline smoke` run `30838804593` at exact commit
  `77543ee2c7fadad19c3e247cebe448e8dfe0a9d2` — PASS: QEMU in 34 seconds and
  recovery-core in 3 minutes 35 seconds.

The lifecycle executes `stable-recovery-control.py` directly from the exact
synchronized repository checkout. It is not one of the fixed root-installed
broker files, so no privileged host reinstall is required or appropriate for
this correction. A cautious installer invocation rejected at its initial
PolicyKit-caller check before any mutation; no installed component changed.

No phone command, boot, reboot, fastboot/ADB/SSH connection, signing key,
credential, generation artifact, NFS service, or private evidence was used.
Generation 8 remains consumed and absent from temporary-boot policy.
