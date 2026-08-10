# Deployment boot-tool dependency closure — offline

Date: 2026-08-10

Starting repository SHA:
`05c58459ba48bbd684e193d0737782e245d0b807`

Recommendation: **HOLD**

No phone, USB device, fastboot, ADB, ACM/NCM session, phone storage, claim,
policy row, flash, wipe, slot operation, persistent installation, or phone
boot was used. The authorized production signing key was admitted only to the
reviewed offline build. Its temporary snapshot and all unpublished staging
were removed after failure; no production output directory, candidate,
wrapper, claim, or boot authority was published.

## Concrete defect

The first production clean-twin build after fixing detached-checkpoint input
staging completed both sealed ASUS 5.4 wrapper compiles and proved them
byte-identical. Release repacking then failed after 2,253 seconds:

```text
PASS two clean ASUS kexec-wrapper builds are byte-identical
ModuleNotFoundError: No module named 'gki'
```

The fixed checkpoint allowlist copied `mkbootimg.py`, `unpack_bootimg.py`, and
`avbtool.py`, but omitted the exact runtime import
`gki/generate_gki_certificate.py`. The stable-wrapper preflight and cache
identity made the same incomplete assumption. This allowed an expensive clean
twin compile to begin even though release post-processing could not run.

The failed build nevertheless established the following unpublished
intermediate identities:

| Product | SHA-256 |
|---|---|
| production full recovery initramfs A/B | `ab0a3ee219684c994af386cb60e5280dcc4269457b196f96ca3928acce691f0b` |
| observation-only initramfs A/B | `b2440d8ccc2f22b9c9072a2404569d2a5843f7dab186a2ccac307a929a4941ad` |
| wrapper config A/B | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| wrapper Image A/B | `8a600acfc6f7e01f9eb932e0a04174079d6ee68142c44fad819fe96bbd34325d` |
| production trust root | `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b` |

These hashes are diagnostic build evidence, not admitted release identities.
Raw and AVB wrapper identities do not exist because repacking never started.

## Correction

Both deployment launchers now copy the helper only from the literal
repository-owned path with exact size 3,082, mode `0755`, and SHA-256
`367858be999c3013d44450a91bde0067f0530857b5a95fbf5858c62477bcaf36`.
The existing no-follow, no-replace, streaming hash, metadata revalidation,
fsync, and Git-state gates apply unchanged.

The stable-wrapper gate checks the same file before Podman or either compile.
The content-addressed cache profile, command interface, and input key now bind
the helper as a first-class dependency. Consequently the prior profile hash
`c6b06b44561506d3adfd7c3d49ef5d3476356d8aa0061fc3dec11bbf8496a4c7`
is superseded by
`98bfe97f2e3e094cd1ccc7ee998c6f553acfe33a3162b406fbab4e9631938b91`.
Historical cache evidence is preserved, but an old entry cannot satisfy the
current dependency-complete materialization contract.

## Fail-first and focused tests

The new fixed-profile regression failed against the starting commit in 163 ms
for both deployment launchers because the helper tuple was absent. After the
correction:

- checkpoint-input hostile suite: PASS, 6 cases, 0.190 s;
- guarded deployment contract: PASS, 1.684 s;
- wrapper-cache hostile suite: PASS, 11 cases, 2.039 s;
- wrapper-cache static contract: PASS, 0.443 s; and
- Android boot-tool bootstrap contract: PASS, 0.349 s.

The cache suite now mutates the GKI helper independently, proves that
publication is refused, and rejects the legacy profile that omitted its
identity. The static gate proves the helper is verified before Podman or the
first wrapper build. The launcher suite proves both fixed profiles carry its
exact path, size, mode, and digest. The complete
`scripts/host/test-repository-linux.sh ci` checkpoint passed in 300 seconds.
The exact ending commit and GitHub exact-head result are recorded after this
report is committed.

## Boundary and next action

The failed output root is absent, no reviewed-checkpoint worktree remains,
and the host's temporarily disabled AArch64 binfmt handler was restored. The
next safe action is full local CI, commit/push, and exact-head CI. Only after
that checkpoint may the authority-free production clean-twin build be retried.
Claim definition, candidate admission, signing/issuance, and physical
execution remain separate decisions. Recommendation remains **HOLD**.
