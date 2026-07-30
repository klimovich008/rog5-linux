# Corrected successor live-gate admission

Date: 2026-07-30

Result: **PASS**

The retained corrected-headless successor passes the exact production
stable-recovery artifact boundary without contacting a phone. This check used
no fastboot or ADB device, SSH credential, PolicyKit/root privilege, private
signing key, phone storage, or external service.

## Admitted identities

| Component | SHA-256 |
| --- | --- |
| AVB recovery image | `416d62e4f0d89e9184d8a362c8c9e5091bd265f4c48504916920706f08611430` |
| raw boot-v3 image | `157da94bf50635099c571ce97d3e3c797c22eb66e3b9730b4ea332d952a9261c` |
| ASUS wrapper Image | `bc42d9ffc78ed88c5e8f597905844e472a5681c57caab020ce88c1eae1b706da` |
| stable recovery initramfs | `ac5fd5169be86a44b01e8e2d5d5343feddf9ffdc34ea3581a430c5cbc2962c04` |
| public trust root | `ce9f89c9c1859a3239615932da36617f3436f9a0355c8db9c852a1b764f2dfeb` |
| bundle manifest | `d7a02a2403caf885a015060a8361019936e86efafde44f3bb7e6bdd48d2ee32d` |
| corrected DTB | `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46` |
| native host verifier | `9099f5f615144cf95655e6e169ac49b0cbe6f0a6d759441c59bc3130407ab78b` |
| recovery responder | `c1e1b7b58f36b9ff091bed3b5de463d6239031729a49e12c07064c410de43fd0` |
| recovery fetcher | `becc3fc1442823118fa75e79a9b756395df9f1b5b7df37440d4e2c8c5b4ef89c` |
| AArch64 verifier | `374900be5769eee074820007ab2e335d4c033c500da7a480cc88f9a70137029b` |
| wrapper config | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| AOSP `avbtool` | `6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff` |
| AOSP unpacker | `7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef` |
| qualified `cpio` wrapper | `7520899a405e1fc698875e047d8671c9415116e944831135a8e8eb6a93a21580` |
| qualified `cpio` shim | `a0a0a1d5b134d18470cc2fc55b0220fa464057e95ba05145e3dde6338ed59b58` |

## Boundary exercised

`scripts/host/test-corrected-successor-live-gate-offline.sh` selected
`ROG5_STABLE_RECOVERY_PROFILE=corrected-headless-successor-2026-07-30` and
ran the production gate's `artifact-preflight` action against:

- the ignored, nonsymlinked structured candidate roots;
- the byte-identical A/B products;
- every exact component identity above;
- the stable initramfs verifier through the qualified `cpio` path;
- the signed bundle and native signature verifier;
- the AVB footer, `NONE` algorithm, boot descriptor, raw prefix, boot-v3
  structure, and exact command line; and
- the no-storage and legacy-network rejection policies.

The test statically and dynamically proves that this action exits before the
gate's first fastboot device query. A clean checkout without the ignored
retained candidate skips this retained-artifact integration test; the static
production-gate contract still runs in CI.

The local result ended with:

```text
PASS stable recovery artifact preflight profile=corrected-headless-successor-2026-07-30
PASS retained corrected successor satisfies the exact phone-free live-gate boundary
```

The one-shot lifecycle now requires the same successor profile and rejects the
consumed `historical-2026-07-29` profile before inspecting SSH or evidence
paths.

## Independent review closure

A tool-free, nonpersistent Claude advisory review found two actionable
hardening gaps:

1. prepending the qualified `cpio` directory could allow another executable in
   that directory to shadow a verifier dependency; and
2. the standalone gate implicitly selected the historical profile when the
   profile variable was absent.

The gate now requires an explicit profile before host inspection and proves
that the qualified path contains exactly the one pinned `cpio` file before
using it. Focused contract and retained-candidate tests pass with both fixes.

## Remaining authority boundaries

The root-owned host controllers and production bundle root below `/var/lib`
still require a separate approved host mutation. A connected read-only
preflight and any attended temporary boot require fresh explicit
authorization. This result grants neither credential use nor live authority.
