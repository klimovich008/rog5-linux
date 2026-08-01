# Early-target diagnostic production-signing readiness

Date: 2026-08-01

Result: **PASS offline — the production path now has an exact diagnostic
candidate, guarded signer entry point, distinct recovery artifact profile,
independently closed review, and one complete disposable-key
wrapper/twin-build/native-verification/artifact-preflight execution. Complete
repository CI passes.**

No production credential was opened, no external service or privileged host
action was used, and no phone interface was contacted. This result grants no
signing, installation, or boot authority.

## Fixed candidate before credential access

`prepare-early-target-diagnostic-deployment-candidate.py` parses the existing
non-fixture v3 Arch package, rejects tracked fixture identities, and requires
all six root fields to equal the accepted diagnostic template. It publishes
one new mode-`0444` candidate outside Git without replacement. Its canonical
record is:

- candidate and bundle: `headless-netroot-early-diag-v1`;
- record SHA-256:
  `7081a0c77158ed695e62751e152baff101b18a9b364640c0cbffd6ef8ba1c6e8`;
- profile: `diagnostic-initramfs-v1`;
- target: `headless-netroot-early-diag`; and
- manifest SHA-256:
  `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`.

The neutral recovery signing-input stager now resolves only the fixed normal
or diagnostic candidate ID; the former SSH-named path remains only as a
compatibility entry point. It reads and validates the candidate, then
atomically reserves the staged key, candidate, and public-key destinations
before reading the signing key. Reservation identity is captured immediately
after exclusive creation, so even an injected permission-setting failure
removes only the exact inode just created. The diagnostic policy additionally
requires the exact candidate-record hash above, so a root, formatting, or
occupied-output mutation is rejected while an absent key path remains
untouched.

## Guarded build and artifact profile

`build-early-target-diagnostic-deployment-candidate.sh` starts through an
environment-clearing isolated-Python shebang, accepts the two one-shot
authorization flags and credential paths only as explicit arguments, sets only
the fixed diagnostic candidate/target tuple, and executes the existing twin
builder with a fixed environment. The shared builder still requires both
explicit credential guards, privately
snapshots the externally held candidate and signing key, creates two complete
bundles and stable-recovery wrappers, compares every twin output, and destroys
the private-key snapshot. Diagnostic builds additionally require the exact
manifest hash above. None of these guards was enabled against a production key
in this result.

Both guarded wrappers start through an `env -i`/isolated-Python shebang and
accept authorization plus candidate/key paths only as explicit arguments.
They `execve` the internal Bash builder with an exact environment, so caller
`BASH_ENV`, `SHELLOPTS`, exported functions, `PATH`, `PYTHONPATH`, and OpenSSL
provider settings cannot execute while a source key path or snapshot is live.
Before that handoff, each launcher verifies the clean synchronized checkpoint,
compares the implementation to its exact `HEAD` blob, and executes a sealed
memfd snapshot so pathname replacement cannot change the Bash bytes.
The builder invokes the stager through `/usr/bin/python3 -I -S`; the stager's
direct shebang is isolated too, and both OpenSSL key-validation processes use
an explicit configuration-free environment. After staging, the builder
removes the remaining build/credential guards and proves a later child cannot
observe them. A guarded input-preflight mode executes the actual diagnostic
wrapper, shared builder, and stager in a clean synchronized temporary
repository with a disposable Ed25519 key. Hostile startup hooks, provider
configuration, imported functions, and helper shims remain unused; the test
also verifies the caller's key is unchanged, the private snapshot is
destroyed, and no signing/build output is created.

This result trusts the existing local-owner process, root-managed dynamic
loader, and absolute `/usr/bin` runtime binaries. It does not claim protection
from pre-existing same-user `LD_PRELOAD`/`LD_AUDIT` injection before
`/usr/bin/env` clears the environment; production signing must begin from a
trusted shell without loader injection. That attacker class already has the
same-user authority required to read the external 0600 key.

`run-stable-recovery-live-gate.sh` now has a distinct
`headless-diagnostic-deployment-v1` profile. It reuses the already pinned
production recovery wrapper, trust root, control, fetcher, verifier,
configuration, and host-verifier identities, but requires the diagnostic
bundle, manifest, bundle profile, and target. Both the historical consumed
manifest and consumed r2 manifest are refused before direct boot admission.
The one-shot lifecycle selects this profile only for diagnostic actions while
retaining the established NFS package profile and normal runtime path.
The credential-free `policy-preflight` is limited to the fully pinned
diagnostic profile and emits one exact canonical record binding the recovery
profile, bundle, manifest, bundle profile, target, recovery image, trust key,
and host verifier. Executed hostile cases reject an unpinned historical
profile, a normal manifest, normal bundle, and wrong recovery image under the
diagnostic profile; the success test compares the complete output bytes so
extra, duplicate, missing, or reordered lines fail.

## Complete disposable-key deployment-path execution

The canonical full-path test ran from clean synchronized checkpoint
`0375e97a05b1d2485fe6c351e83e461331d2d7c1`. It created one external
disposable Ed25519 key and executed the real diagnostic wrapper, shared
builder, signing-input stager, two complete signed bundles, two stable-recovery
initramfses, two clean ASUS 5.4 wrapper kernel builds, header-v3 raw-image
packing, test-only AVB wrapping, twin byte comparison, and native artifact
verification. It then destroyed the private-key snapshot and retained no
deployment authority (`authority=none`).

The retained full-path identities are:

- test-only AVB image SHA-256:
  `24b9b8c410b42b5c7c62e4b682fab6bead32264771991b2641345f7ccb2dd441`;
- raw wrapper image SHA-256:
  `e10a63209c8af5aac249f81fa2b185c8f12232fb20e8127e53f7d2a94dd6bb65`;
- ASUS 5.4 wrapper `Image` SHA-256:
  `b96f7e8a816da18e67c7b02dbe639b0b48ca07c245c1cb64a2793b6790100bea`;
- accepted wrapper config SHA-256:
  `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f`;
- stable-recovery initramfs SHA-256:
  `cdf11bcd7285a45107f778cbf61ac0f7b95416e027036a4d9b5a61272dc940ba`;
- disposable recovery trust-key SHA-256:
  `36026bd2eb0ae47d7e6b5feebc02b2ef9c354acc3197c327143bd42501918c4b`;
- host verifier SHA-256:
  `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621`;
- recovery control SHA-256:
  `f564fb848eb58724c09f3b4dabeebcc95f95fb35cdc259045d3c29c226dd1e77`;
- bundle fetcher SHA-256:
  `677fa731b1bd9fd11efc46aabeb32e7a725725483c86a2f58d417f482c27f392`;
- target verifier SHA-256:
  `5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0`;
  and
- diagnostic manifest SHA-256:
  `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`.

The final artifact-preflight did not weaken or replace the production pins.
The test copied the real gate to an explicitly Git-ignored temporary path and
replaced ten exact SHA-256 constants with the observed disposable-build
identities: AVB image, raw image, wrapper kernel, accepted config,
stable-recovery initramfs, trust key, host verifier, recovery control, bundle
fetcher, and target verifier. The complete gate logic then verified that
identity-parameterized disposable chain and emitted its exact pass record.
This proves that the wrapper and artifact gate compose against all generated
artifacts at the recorded checkpoint; it does not prove the production pins,
claim that production-signed artifacts exist, or authorize their creation or
use.

## Focused verification

- 3 diagnostic candidate-preparer tests pass: exact non-fixture binding, all
  six root mismatches, fixture rejection, and no-replace output.
- 12 signing-input tests pass: normal and diagnostic snapshots, exact
  diagnostic hash, candidate-before-key rejection, fixed two-ID CLI policy,
  key type/encryption, metadata, repository checkpoint, internal path, and
  no-replace output cases, including injected permission-setting failure
  cleanup.
- The deployment-build shell contract passes for both guarded wrappers and
  runs the complete diagnostic wrapper-to-builder-to-stager input preflight
  with a disposable key, including post-stage environment scrub and snapshot
  destruction without signing.
- All 34 lifecycle methods pass with the distinct diagnostic recovery profile.
- The stable-recovery live-gate contract passes, executes exact diagnostic
  policy association and hostile substitutions, and exercises refusal of both
  consumed normal manifests.
- Python compilation, shell syntax checks, and `git diff --check` pass.

The complete local repository `ci` tier passes with one expected optional
retained-source skip. Independent standards/spec review reports no remaining
actionable findings. GitHub CI must pass before any separately authorized
production signing, host installation, connected preflight, or temporary
phone boot.
