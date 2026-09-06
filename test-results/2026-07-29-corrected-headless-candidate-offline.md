# Corrected headless candidate twin build

Date: 2026-07-29

Result: **PASS offline; reproducible; authority=none; no phone action**

## Outcome

The corrected `headless-network-root-v1` target, signed runtime bundle,
shell-free stable-recovery initramfs, vendor-compatible recovery wrapper, raw
Android boot image, and unsigned AVB test wrapper were built twice and matched
byte-for-byte. The candidate carries the accepted GPU/RMTFS-isolated v3 DTB:

```text
size:   102870
sha256: 86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46
```

This checkpoint used no `fastboot`, ADB, SSH, privileged host setup, phone
storage, or live allowlist. It does not authorize a temporary boot.

## Reproduction command

```sh
scripts/host/build-corrected-headless-candidate-offline.sh \
  build/corrected-headless-candidate-20260729-a
```

The entry point accepts only an empty, ignored directory below `build/`, pins
the accepted rootless Podman builder identity, and has a static contract test
that rejects phone, privilege, storage, and live-promotion transports.

## Trust boundary

One test-only Ed25519 private key was created with mode `0600` below a
`mktemp -d` directory. Its raw 32-byte public key was bound into both recovery
initramfs builds and used to verify both bundles:

```text
public-key sha256:
fb3f74deabaec1abd5d65dcf9de952a22739cce4e3d8af54c9c6e88229f5a879
```

The private key was deleted before the build reported success. A post-build
audit found only the public key and 64-byte detached signatures in retained
outputs. Both candidate records say:

```text
status=offline
authority=none
```

No production or live signing credential was created.

## Reproduced identities

The production AArch64 recovery components were independently built twice
before composition:

| Component | Size | SHA-256 |
|---|---:|---|
| framed responder | 132896 | `c1e1b7b58f36b9ff091bed3b5de463d6239031729a49e12c07064c410de43fd0` |
| fixed-host fetcher | 132824 | `becc3fc1442823118fa75e79a9b756395df9f1b5b7df37440d4e2c8c5b4ef89c` |
| signed-bundle verifier | 4467272 | `374900be5769eee074820007ab2e335d4c033c500da7a480cc88f9a70137029b` |

The retained twin products matched:

| Product | Size | SHA-256 |
|---|---:|---|
| shell-free stable-recovery initramfs | 7593276 | `6927d91d5c590ada1f6cae44cfa126c15470008f79949ca3256a45ee3edc4fff` |
| target Linux 7.1.4 Image | 40049152 | `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf` |
| target initramfs | 5978369 | `819bdf88c920057a5d8b511cb13e3adc0f7d8d9cf1a92a7fac087697889bb9b5` |
| canonical manifest | 811 | `d7a02a2403caf885a015060a8361019936e86efafde44f3bb7e6bdd48d2ee32d` |
| vendor 5.4 wrapper config | — | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| vendor 5.4 wrapper Image | 50498048 | `cf8c2aced08010a193b60f3dbc6099f6a24cebbe7473fb13be0e18a7015fd4ad` |
| raw header-v3 wrapper | 58097664 | `0489b6522a8bae12138e20630cc8d7a4005e82b687a9dd52fa4a874ded480e9f` |
| unsigned AVB test wrapper | 100663296 | `fe0046e342b9aad0ecbfda3d4e8851a2ab261dfd70db8773d817a55f73030531` |

The wrapper used Ubuntu clang 18.1.3 in the accepted builder:

```text
builder_id:
c5b80647ddd7fb29464b4735abbe27012ee4dc89be559b44b25c9b1ff59c9cec

builder_digest:
sha256:8513960144bb1ca77878a1364c03fb100c8b87fffb8440fd37a6cc4fc0043b41
```

Legacy vendor-source compiler and linker warnings remained nonfatal. Both
clean builds produced the same final identities.

## Verification

The run completed:

- two independent production AArch64 responder/fetcher/verifier builds;
- two malicious-fixture and policy checks of the shell-free initramfs;
- two signed corrected runtime bundles with one public trust root;
- native verification of both immutable execution plans;
- two clean vendor 5.4 wrapper kernel builds;
- two header-v3 raw and unsigned AVB test repacks;
- `test-prepare-recovery-candidate.py` (7 tests);
- `test-recovery-candidate-integration.py` (2 tests); and
- stable-recovery composition with the consumed-P2 fixture.

The retained output also passed an independent `cmp` audit across the A/B
initramfs, all five runtime-bundle files, raw wrapper, and AVB wrapper.

## Claude advisory review

A constrained Claude Opus review used safe mode, no tools, no session
persistence, no permission prompts, a fixed timeout, and only the
self-contained implementation patch. It returned `NO_BLOCKERS` after checking
path containment, traps, private-key deletion, A/B independence, and
live-authority exclusion.

Its one actionable non-blocking suggestion was to expose whether the
initramfs integration generated its own test public key or consumed the
caller's explicitly supplied offline key. The final script reports
`trust_root=generated` or `trust_root=supplied`, and the contract test requires
that provenance marker. Claude had no repository write authority.

## Next gate

The hardware-free corrected-candidate gate is complete. The next step needs a
fresh and separate user authorization before either:

1. creating or using a live signing credential; or
2. temporarily booting a newly allowlisted corrected recovery wrapper.

Any live gate must remain attended, boot-only, storage-safe, single-use, and
rollback-guarded. The first target acceptance criterion is minimal key-only
SSH with a clean fallback; power, charging, thermal, input, and sensors follow
before GPU or desktop work.
