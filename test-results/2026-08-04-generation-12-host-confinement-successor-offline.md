# Generation-12 host-confinement successor — offline issuance

Date: 2026-08-04

Result: **PASS — two authority-free Generation-12 AVB trees reproduce one
distinct wrapper over the byte-identical Generation-11 recovery payload. The
immutable offline profile passes both retained trees, while direct preflight,
boot, an unreviewed live profile, lifecycle selection, and central-policy
admission all remain absent or fail closed.**

## Purpose and lineage

Generation 11 is consumed and never reusable. Its phone lifecycle failed in
the host's post-start TCP-8081 confinement check before recovery control or a
bundle transfer began. The corrected host controller is installed, reviewed,
published, and exact-head green. Because that correction changed no recovery
payload byte, rebuilding the kernel or initramfs would create an unrelated
variable and weaken the comparison.

Generation 12 therefore uses the canonical generation-zero wrapper retained
at:

```text
build/generation11-ncm-progress-production-base-20260804/wrapper
```

That source has raw SHA-256
`44c43e27ba0cdb646eb3a6327c519011090f64b1e76ec67e2ff9db469e6612b2`
and canonical source-AVB SHA-256
`8c0916fec05c8636a10cbdec3e535f0f3bb705fd1115113a3344ca9fc20a61c1`.
An attempted issuance from the already generation-salted Generation-11 AVB
was rejected before publication with `source AVB wrapper is not the canonical
generation-zero encoding`; neither requested output path appeared. This
confirms that generations cannot be chained from prior final wrappers.

## Retained twins

The atomic issuer created:

- `build/stable-recovery-generation12-host-confinement-fix-20260804-a`; and
- `build/stable-recovery-generation12-host-confinement-fix-20260804-b`.

Every retained file in the two trees is byte-identical. Their exact generation
record is:

| Field | Value |
|---|---|
| generation | `12` |
| raw SHA-256 | `44c43e27ba0cdb646eb3a6327c519011090f64b1e76ec67e2ff9db469e6612b2` |
| source AVB SHA-256 | `8c0916fec05c8636a10cbdec3e535f0f3bb705fd1115113a3344ca9fc20a61c1` |
| AVB salt | `728dcc59f29e0fbf83165b6979bb5dc68571b0d0e0236993fc9b8f2dd98084c9` |
| AVB digest | `31d1ec59526d876de914330004d42752cfc7b24bd069b955d64687ef750b526d` |
| output AVB SHA-256 | `615d7498e85be499b80473aa0fd6c0cb341dbd13ef5006d6464b389fedd72cf6` |
| partition size | `100663296` |
| generation-record SHA-256 | `2b8a05d4655a4794ae4ee5ce9fe1279b194dec39d3a4bfcb93904cc665192c72` |
| authority | `none` |

The Generation-12 AVB wrapper differs from Generation 11, while the raw
wrapper, kernel Image
`895272e87d5a90ae6b9b8df71862b48d819479d5bbf2741fab002126e47d3eae`,
and NCM-capable initramfs
`3695ded23cc422f8363235884cb3cc402c0c90eeddee04d0603c09befd0f6a8c`
remain byte-identical. The AVB salt and digest were independently reproduced
from the format domain, raw digest, generation number, and raw bytes.

## Offline profile and refusal boundary

`headless-diagnostic-generation12-offline-v1` pins the exact AVB, raw,
kernel, initramfs, recovery control/fetcher/verifier, trust key, signed bundle,
manifest, target ID, generation record, salt, and digest. Policy preflight and
artifact preflight pass both trees.

The profile has no boot-image path or boot basis. `preflight` and `boot`
reject as offline-only before host inspection even when every historical
authorization guard is supplied. `headless-diagnostic-generation12-live-v1`
is unsupported. Neither lifecycle source contains a Generation-12 profile,
path, or identity. `manifests/temporary-boot-images.tsv` retains zero `allow`
rows and no Generation-12 row; `manifests/artifacts.tsv` records exactly one
unbooted, untracked, never-flash Generation-12 identity.

## Regression

- deterministic Generation-12 twin issuance, exact Generation-11 payload
  preservation, AVB non-reuse, independent salt/digest calculation, and
  `authority=none`: pass;
- exact offline profile and five-field policy mutation matrix: pass;
- retained-local twin artifact preflight and generation-record mutation
  rejection: pass;
- direct connected-action refusal, unsupported live-profile refusal,
  lifecycle non-selection, exact inventory row, and zero-policy-row checks:
  pass; and
- complete local stable-recovery live-gate oracle: pass. A clean checkout
  intentionally lacks the ignored production trees, so GitHub CI skips their
  byte-level preflight while still exercising the deterministic synthetic
  Generation-12 issuer, exact committed identities, and fail-closed policy.

Independent standards and spec review passed after strengthening AVB non-reuse
against every consumed generation, rejecting aliased inventory rows, guarding
the Generation-11 comparison dependency, and documenting the retained-tree CI
boundary. Tool-disabled Claude advisory review identified the same boundary
and confirmed that salt/digest checks are consumed by artifact preflight.
Complete repository Linux CI passes. Publication and exact-head GitHub CI
remain before any connected preflight profile is created. This result
authorizes no phone boot.

## Effects

Only ignored build outputs and repository source, tests, inventory, and
documentation changed. No credential, signing private key, ADB, fastboot, ACM,
NCM, SSH, phone reboot, phone boot, flash, erase, wipe, slot operation,
phone-storage mount, or phone write occurred.
