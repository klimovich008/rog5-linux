# Generation-6 signal-fix recovery — offline

Date: 2026-08-03

Result: **PASS offline issuance; unbooted**. A distinct
Generation-6 outer AVB wrapper was issued twice after installing the corrected
recovery-host broker. The accepted recovery kernel, raw boot image, initramfs,
control responder, fetcher, verifier, target, signed bundle, and embedded trust
root are unchanged.

## Exact identities

| Item | SHA-256 |
| --- | --- |
| Generation-6 AVB image | `6aa47517de806fea73b70f5b5b2e4c749ec39f9e3538a622b7a75f1a1cd9d398` |
| AVB-generation record | `bff8432e20e01f74132addda464120886c5090b079798054fe359845b1a552a2` |
| AVB salt | `66d5537af0ff592b94ab516306ad03643ee48b15e90e49cb3c990e786031fbe8` |
| AVB payload digest | `47c517b5c066671b32728076e3b4a5836e839efa9f2ba878659156cffdf0d461` |
| Unchanged raw recovery | `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce` |
| Unchanged recovery kernel | `8c3d6bb8271eb4bcf6bd31ff828aed2d62c49408e13d3db07caa469a72c27d0c` |
| Unchanged recovery initramfs | `144f1cfde88302278c487b763199f53f1a9448ac5ea8c594b9b7d2a0837ae4ec` |

Both independently issued output trees are byte-identical. Generation 6 is
distinct from generations one through five for both A and B wrappers. Its AVB
algorithm remains `NONE`; authenticity still comes from the pinned artifact
identity and embedded production Ed25519 trust root, not an AVB signature.

## Fail-closed policy

At issuance, `headless-diagnostic-generation6-offline-v1` was the only
Generation-6 profile. It permits only `policy-preflight` and
`artifact-preflight`. Supplying
all temporary-boot and lifecycle authorization flags still cannot make its
connected `preflight` or `boot` action pass; both reject before dependency,
host-state, credential, fastboot, or phone inspection.

At this issuance, the artifact inventory contains one exact candidate row with
`authority=none`, `unbooted`, and `never flash`. The temporary-boot policy has
no Generation-6 row and no `allow` row at all. No Generation-6 live profile,
lifecycle selection, or boot authority exists.

## Verification

The following focused gates pass:

- deterministic issuer regression, including both twins and every predecessor;
- stable-recovery policy mutation and retained-artifact preflight;
- recovery-wrapper inventory/boot-authority separation;
- 39 compatibility-oracle tests; and
- 74 source/DTB tests, with one optional retained-source test skipped.

The retained-artifact gate hashes both complete AVB twins, both unchanged raw
images, both kernel/config/initramfs trees, the generation record, signed bundle
manifest, trust root, control components, and host verifier. It then validates
the exact AVB descriptor salt and digest. This connects the generic deterministic
issuer regression to the production identities above without weakening the
static profile pins.

A constrained Claude Opus review confirmed that Generation 6 is offline-only
and the payload identities are preserved. Its proposed production-linkage gap
was already covered by the retained-artifact preflight. Its useful suggestion
to check predecessor non-reuse for both twins was applied. Claude output is
advisory; the executable gates above are the evidence.

No credential, signing key, privileged host action, fastboot command, phone
interface, or phone storage was used. The separate
[live-profile transition](2026-08-03-generation-6-live-profile-offline.md)
now wires the lifecycle to the same exact tuple without adding boot authority.
The subsequent [one-shot admission](2026-08-03-generation-6-live-admission-offline.md)
adds the separately reviewed central policy row. This issuance result itself
does not authorize or predict a phone boot.
