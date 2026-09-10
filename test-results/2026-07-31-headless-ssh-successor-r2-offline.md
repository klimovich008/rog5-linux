# Headless SSH deployment successor r2 — offline staging

Date: 2026-07-31

Result: **PASS OFFLINE; the consumed deployment is locked out and a distinct
signed-bundle successor can be produced without changing target artifacts.**

## Consumed boundary

The lifecycle now rejects manifest
`457273993a9ce3cb0a9c735ef29e96101c1303720cafefc774aed12972a6926e`
before inspecting the deployment private-key path. This is the exact manifest
used by the resolved `FALLBACK_RETURNED` cycle. It cannot reach key admission,
host mutation, fastboot, recovery, or SSH again.

## Successor shape

The non-fixture candidate generator accepts one new exact bundle identity:

```text
candidate=headless-ssh-network-root-v3
bundle=headless-ssh-network-root-v3-r2
```

The candidate, kernel, corrected DTB, initramfs, target identity, timeouts,
command-manifest identity, sealed root, package, and admitted SSH client key
remain unchanged. Only the signed bundle identity changes. With the retained
non-secret manifest tuple, the expected r2 manifest SHA-256 is:

```text
9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630
```

This value is predictive, not live authority. A fresh Ed25519 recovery trust
root and rebuilt wrapper will produce new trust and recovery-image hashes;
those must be generated under fresh credential authorization, reviewed, and
pinned before r2 can become runnable.

## Verification

Hardware-free tests use one disposable test signing key to package the base
and r2 records from identical artifacts and root identities. They require:

- different manifest hashes;
- exact bundle lines for each output;
- byte identity of every other manifest field;
- only the fixed base/r2 mapping, rejecting arbitrary bundle names;
- builder/verifier use of the record's bundle rather than assuming candidate
  and bundle names are equal; and
- consumed-manifest rejection before key admission.

No phone, fastboot, private deployment key, host privilege, installed export,
or live signing key was used. The disposable test key was confined to the
temporary test directory and removed with it.

## Superseded HOLD

The real external candidate and signed twin build now exist and reproduce the
predicted manifest. Continue from the
[signed r2 result](2026-07-31-headless-ssh-successor-r2-signed-build.md) for
the remaining review, installation, preflight, and temporary-boot sequence.
