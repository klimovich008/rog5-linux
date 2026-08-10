# Retention-cycle executor boundary — offline

Date: 2026-08-10

Recommendation: **HOLD**

This file preserves the initial three-decodable/three-blocked boundary
checkpoint. The current source identities and six-action decoder are recorded
in the later
[boot-output checkpoint](2026-08-10-retention-cycle-boot-output-contract-offline.md).

Starting repository HEAD:
`a7fa97d0b76c3e474e45ee327f4d71a776077e32`

Ending repository HEAD before final CI:
`a7fa97d0b76c3e474e45ee327f4d71a776077e32`

The local `origin/agent/linux-recovery-host` tracking ref is
`91334dcb9ef26f21a66fe55a4ae843d8cc218d7c`. It is an ancestor of HEAD;
`git rev-list --left-right --count HEAD...origin/agent/linux-recovery-host`
reports `13 0`. The local branch is 13 commits ahead, not behind or remotely
diverged. No fetch, merge, rebase, commit, or publication occurred.

## Concrete defect fixed

The executor contract labeled six success protocols and the callback adapter
accepted six synthetic result dictionaries. Neither proved that current helper
stdout contains the fields needed to construct those dictionaries. Treating
the labels or fixtures as executable evidence could therefore admit a future
launcher with ungrounded USB, fastboot, or host-pin identity.

The new boundary is pure data and parsing logic. It verifies the exact
program/interpreter/host-pin descriptor evidence that a future executor must
supply, applies common process-result rejection, and decodes only output that
is exact today. It fails closed where the real helpers are incomplete.

| Action | Offline conclusion |
|---|---|
| execution claim | exact durable `BOOT_CLAIMED` record decodes |
| execution boot | blocked: success output has no physical USB location |
| fallback reboot | blocked: success output has no location, fastboot product, serial, or host-pin digest |
| observer claim | exact durable `BOOT_CLAIMED` record decodes |
| observer boot | blocked: current HOLD gate has no success output |
| postmortem read | exact canonical 12-field lineage JSON decodes |

The boot gaps are admission findings, not proof of a live failure and not an
invitation to infer values from host state after a helper exits.

## Exact identities and descriptor contract

| Item | Value |
|---|---|
| boundary source | `scripts/host/retention-cycle-executor-boundary.py` |
| source size/mode | 20,936 bytes / `0644` |
| source SHA-256 | `a3592ede57080dca93de86920becea3e83bc30f0c0bf2b2b4f9995cb0928fe83` |
| hostile test | `scripts/host/test-retention-cycle-executor-boundary.py` |
| test size/mode | 20,410 bytes / `0755` |
| test SHA-256 | `cf18a8cbcdf192a42f27b5b63cbec7ea9db8212aa08a35108163340830eae824` |
| executor contract SHA-256 | `d5fa9e2bf38eee016f3e3d16e7afb7a1d9df52bda691f66dfd0b81b8cfc370e2` |
| Python | `/usr/bin/python3` → `python3.13`, 14,352 bytes, `62cf34d8…b718` |
| Bash | `/usr/bin/bash`, 1,162,328 bytes, `66bb45cd…22d1` |
| live entry point / built-in executor | none / none |
| credential use / connected admission | none / none |
| host-pin SHA-256 / runtime closure | `not-defined` / `unproven` |

Program files require exact repository identity, regular type, root owner,
reviewed mode, one link, expected size/hash, and matching opened/path device
and inode under `O_CLOEXEC|O_NOFOLLOW|O_RDONLY`. Directories additionally use
`O_DIRECTORY`. Python's logical and resolved paths bind both the original and
revalidated symlink target. The public fallback pin requires one exact
`rog5-fallback ssh-ed25519 ...` record in a caller-owned mode-`0600`,
single-link regular file beneath a caller-owned mode-`0700` directory. This
module validates supplied evidence only; it never opens that path.

## Fail-first and hostile tests

The new test was run before the source existed and failed as intended with
`FileNotFoundError` in 0.059 seconds. Ten groups now cover exact six-action
descriptors, program mutations, Python/Bash identity, Python link-target
revalidation, hostile host-pin file/parent/content/digest state, exact claim
records, canonical postmortem JSON, duplicate/noncanonical output, process
exit/signal/timeout/overflow/stderr/stream failures, exact rejection of the
three current boot outputs, absence of an I/O/executor surface, and preserved
HOLD/claim/policy closure.

Focused final-byte results before documentation:

- executor boundary: 10/10 in 0.107 seconds;
- executor contract: 8/8 in 0.088 seconds;
- callback adapter: 7/7 in 0.413 seconds;
- transaction journal: 9/9 in 0.874 seconds;
- sequence reference: 8/8 in 0.118 seconds;
- joint retention admission: 25/25 in 3.682 seconds;
- fallback ACM control: 72/72 in 3.345 seconds;
- stable-recovery gate: PASS in 3.554 seconds;
- repository-runner contract: PASS in 5.954 seconds;
- artifact-gated production HOLD profile: PASS in 10.353 seconds;
- artifact-gated observation HOLD profile: PASS in 3.999 seconds; and
- Python bytecode compilation and profile JSON parsing: PASS.

The required artifact-gated command passed the complete repository Linux `ci`
tier in 319.630 seconds before this timing paragraph was added:

```text
REQUIRE_CURRENT_PRODUCTION_ARTIFACT=1 \
REQUIRE_CURRENT_OBSERVATION_ARTIFACT=1 \
scripts/host/test-repository-linux.sh ci
```

The preceding exact staged checkpoint, before this boundary, passed twice in
317.093 and 316.823 seconds; its baseline was 316.610 seconds. The new boundary
checkpoint is 2.807 seconds (0.89%) slower than the immediately preceding
316.823-second run. The command is rerun after staging this paragraph so the
handed-off tree is verified byte-for-byte; that final duration is reported in
the handoff rather than causing a self-referential post-verification edit.

## Remaining boundary

This report records the initial fail-closed boundary. Its three output gaps are
closed at the schema/decoder layer by the later
[boot-output checkpoint](2026-08-10-retention-cycle-boot-output-contract-offline.md):
all six actions now have an exact decoder and fallback has a grounded guarded
producer. Execution and observer remain blocked by their current HOLD gates.
Runtime descriptor collection and process control remain offline future work.
No launcher, host-pin open, claim registration, policy admission, credential
use, candidate creation, signing, or phone contact is justified.

No phone, USB inspection, credential, signing key, privileged host mutation,
claim consumption, policy admission, retained-build deletion, candidate,
flash, wipe, slot, or phone-storage action occurred. Recommendation remains
**HOLD**.
