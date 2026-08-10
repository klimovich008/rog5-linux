# Current observation recovery HOLD gate — offline

Date: 2026-08-10

Starting repository SHA:
`a7fa97d0b76c3e474e45ee327f4d71a776077e32`

Recommendation: **HOLD**

No phone, USB device, phone storage, credential, signature, boot claim,
temporary-boot policy row, candidate issuance, flash, wipe, slot operation,
persistent installation, or phone boot was used.

## Concrete defect fixed

The current project-key execution recovery already had an exact offline HOLD
profile, but its distinct observation-only recovery did not. The retained
observer twins and the joint retention verifier therefore established
composition independently without one fixed entry point that bound the
current observer identity, rejected connected actions, and re-ran the complete
artifact verifier.

`run-observation-recovery-live-gate.sh` now provides that missing offline-only
boundary. It accepts two actions:

- `policy-preflight` checks the exact profile and AVB identity and emits
  `authority=none` and `boot_authority=none` without reading artifact or host
  state.
- `artifact-preflight` verifies a private, owner-controlled root below the
  repository `build/` directory, pins all 22 files by size and SHA-256, runs
  the existing structural wrapper verifier, compares its output byte-for-byte
  with retained evidence, and revalidates every inode and identity afterward.

`preflight` and `boot` emit one fixed offline-only rejection before artifact,
host, policy, or device inspection. The gate contains no device command and no
claim-consumption path.

## Exact observer identity

| Product | Size | SHA-256 |
|---|---:|---|
| observation initramfs | 5,374,739 | `b2440d8ccc2f22b9c9072a2404569d2a5843f7dab186a2ccac307a929a4941ad` |
| wrapper config | 185,763 | `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f` |
| wrapper Image | 48,400,896 | `eedb7deb64aa42de582245b121f4ea581d0b1e21e9eb49f3591e98df8f63ef59` |
| raw boot-v3 image | 53,784,576 | `5daf0919d38c9f7b1ffde85a8c5e9aabdbba526bcafa1a528bd8c31e27dda171` |
| unsigned AVB image | 100,663,296 | `3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b` |
| retained verifier evidence | 823 | `116d21a57514b25fa7c43137b925bce94d9d83e9bbb7287bcceb2a0a50fd8b11` |

The AVB algorithm remains `NONE`. This is exact composition evidence, not a
signature, candidate, or boot admission.

## Fail-first and hostile evidence

The new regression failed against the starting checkpoint in 0.008 seconds:

```text
FAIL current observation-recovery HOLD gate is absent
```

After the correction, it proves:

- wrong external AVB identity is rejected;
- every legacy allow environment variable still cannot reach connected
  preflight or boot;
- the temporary-boot policy has zero `allow` rows and the observer profile has
  no consumable claim;
- all 22 retained products must be safe regular, owner-controlled, non-writable
  by group/other, single-link files with exact size and digest;
- a hard-linked input fails before content verification;
- changing both initramfs twins together still fails at the independent
  initramfs identity; and
- private test material is removed after each run.

The retained observer files currently have link count two because the clean-CI
and production-preflight checkouts share them. The verifier correctly rejects
that mutable-alias condition. The regression copies only the 22 required files
to an owner-mode-`0700` copy-on-write fixture, producing independent inodes;
it does not duplicate or traverse the approximately 9.2 GiB build tree. A
future offline artifact preflight must likewise use an independently
materialized, fixed-file root rather than the hard-linked retained directory.

Focused results:

| Test | Result | Time |
|---|---|---:|
| fail-first observer profile | expected failure | 0.008 s |
| corrected observer profile and hostile cases | PASS | 3.912 s |
| observation wrapper verifier, 8 tests | PASS | 7.834 s |
| joint retention admission, 20 tests | PASS | 2.738 s |
| repository-runner contract | PASS | 5.937 s |

The mandatory complete local CI timing and ending SHA are recorded at the
final checkpoint below.

## Remaining boundary

This correction supplies the observer-side equivalent of the current
execution-recovery HOLD gate. It does not define either future one-use claim,
does not add a sequence-enforcing target → fallback → bootloader → observer
runner, and does not prove ramoops retention or reset cause. Those are separate
review and admission steps. Recommendation remains **HOLD**.

## Final checkpoint

The exact mandatory command passed:

```text
REQUIRE_CURRENT_PRODUCTION_ARTIFACT=1 \
REQUIRE_CURRENT_OBSERVATION_ARTIFACT=1 \
scripts/host/test-repository-linux.sh ci
PASS repository Linux ci tier
FULL_CI_DURATION_MS=313848 status=0
```

The observer profile occupied 3.967 seconds and did not take its optional skip
path. The preceding clean full-CI checkpoint took 311.660 seconds, making the
complete-run change +2.188 seconds (+0.7%). Focused behavior improved from the
0.008-second expected absence failure to a 3.912-second complete exact-artifact
and hostile-path pass.

Ending repository SHA:
`a7fa97d0b76c3e474e45ee327f4d71a776077e32`

The SHA is unchanged because this reviewed tree remains staged and uncommitted.
No commit or publication is permitted until the separate exact-head CI step is
authorized and green. Recommendation remains **HOLD**.
