# Headless SSH successor r2 — real candidate checkpoint

Date: 2026-07-31

Result: **PASS CREDENTIAL-FREE; the real external r2 candidate is staged and
all non-secret inputs are ready for the signed twin build.**

## Candidate

The candidate generator consumed the retained non-fixture v3 root package and
created one caller-owned, read-only external record outside Git. On the current
development host it is retained at
`/home/deck/.local/state/rog5-deployment-20260731-live1/headless-ssh-network-root-v3-r2.json`.
The credentialed build must pass that exact absolute path as
`ROG5_DEPLOYMENT_CANDIDATE_RECORD` and bind the hash below:

```text
candidate=headless-ssh-network-root-v3
bundle=headless-ssh-network-root-v3-r2
candidate_sha256=b26bc73ec6cd0053900044776270ed2c3a7f7bf6424140a59bb74d513b5dd51e
authority=none
```

Its metadata is a regular mode-`0444` file owned by the caller. No existing
file was replaced.

## Verification

The credential-free check:

- parsed the external record through the production candidate validator;
- required exact equality between all six package and candidate root fields;
- separately required the historical candidate and r2 candidate to differ
  only in `bundle`, outside that six-field package/root comparison;
- opened and SHA-256 checked the exact retained Image, corrected DTB, and
  initramfs bytes named by the candidate;
- validated the production network-root bundle configuration; and
- generated the canonical unsigned manifest bytes through the production
  packager and reproduced the predicted r2 identity:

```text
manifest_sha256=9ea27452207962da1e4bc749ac305e3478fde557b93c2f307635527b0d11d630
credential_access=none
phone_access=none
```

The manifest value is byte-equal to the prediction pinned by the
[offline successor result](2026-07-31-headless-ssh-successor-r2-offline.md).

The check did not open the deployment SSH key or recovery signing key. It did
not invoke fastboot, modify host networking, contact the phone, sign a bundle,
or create boot authority.

## Remaining HOLD

1. Under fresh credential authorization, twin-sign and twin-build this exact
   r2 candidate.
2. Require the signed build to reproduce the predicted manifest, review its
   fresh trust, recovery-wrapper, verifier, and configuration hashes, and pin
   the resulting five-member tuple in one clean commit.
3. Install the reviewed no-replace artifacts and pass local, privileged, and
   connected preflights.
4. Obtain separate fresh temporary-boot authorization before one live r2
   lifecycle.
