# Retention-cycle executor contract — offline

Date: 2026-08-10

Repository SHA before and after implementation:
`a7fa97d0b76c3e474e45ee327f4d71a776077e32`

Recommendation: **HOLD**

## Defects fixed

The callback adapter proved durable intent ordering but left the future
process boundary unspecified. A launcher could otherwise inherit credentials,
select different helper bytes or interpreters, leave streams unbounded, or
wait indefinitely after an irreversible intent.

The adapter also named `reboot-fallback-to-fastboot.sh reboot`, the legacy
SSH-key route, for fallback transition. The accepted lifecycle uses
`fallback-acm-control.py reboot KNOWN_HOSTS`, which performs a bounded,
nonce-framed ACM `RESTART2` request and then verifies same-port fastboot. The
adapter now names that helper and carries only an unopened host-pin pathname.
No private SSH-key argument exists.

The regression test was created first and failed because
`scripts/host/retention-cycle-executor-contract.py` did not exist. The final
module is pure data construction: it has no subprocess, socket, CLI, inherited
environment, credential access, or live entry point.

## Exact identity

| Input | Value |
|---|---|
| contract path | `scripts/host/retention-cycle-executor-contract.py` |
| contract size | 14,560 bytes |
| contract mode | `0644` |
| contract SHA-256 | `8705c7fdfa9213a876128614057438565a4889087f77df7c2f41bdd9fe96be3e` |
| hostile test path | `scripts/host/test-retention-cycle-executor-contract.py` |
| hostile test size | 13,704 bytes |
| hostile test mode | `0755` |
| hostile test SHA-256 | `dae939ae6c008253b504813ff7e47dad3ba384e699dfa1b08e523f0561e489bd` |
| adapter size/SHA-256 | 10,260 bytes / `c36b4bfa407b4c5d0df6e32f2b69ebbbf411eaad75649465f89161aa84bf6976` |
| live entry point | none |
| built-in executor | none |
| credential use | none |
| claim registration | none |
| policy allow rows | zero |

The HOLD profile and joint verifier pin the contract and adapter identities,
their relationship, all process-policy fields, undefined claims, and zero
policy admissions.

## Exact six-process boundary

| Action | Program | Timeout | Per-stream bound | Success protocol |
|---|---|---:|---:|---|
| execution claim | `consume-exact-boot-claim.py` | 15 s | 4,096 B | `exact-claim-pass-v1` |
| execution boot | `run-stable-recovery-live-gate.sh` | 300 s | 131,072 B | `retention-boot-result-v1` |
| fallback reboot | `fallback-acm-control.py` | 240 s | 131,072 B | `retention-boot-result-v1` |
| observer claim | `consume-exact-boot-claim.py` | 15 s | 4,096 B | `exact-claim-pass-v1` |
| observer boot | `run-observation-recovery-live-gate.sh` | 300 s | 131,072 B | `retention-boot-result-v1` |
| postmortem read | `stable-recovery-control.py` | 90 s | 16,384 B | `postmortem-lineage-json-v1` |

Each helper's repository path, size, mode, and SHA-256 are exact. Python
helpers use `/usr/bin/python3 -B`; shell helpers use `/usr/bin/bash
--noprofile --norc`. The working directory is the repository. Stdin is
`devnull`; stdout and stderr are distinct bounded pipes. Each process starts a
new session, closes inherited file descriptors, uses umask `0077`, accepts
only exit 0, and requires process-group termination on timeout.

The base environment is exactly `HOME=/nonexistent`, `LANG=C`, `LC_ALL=C`,
`PATH=/usr/sbin:/usr/bin:/sbin:/bin`, `PYTHONDONTWRITEBYTECODE=1`,
`PYTHONNOUSERSITE=1`, and `TZ=UTC`. Each action receives only its reviewed
additional variables. Parent `PATH`, credential-agent/token variables,
Python injection variables, and unrelated authority guards are not inherited.

Dynamic inputs require distinct canonical target/fallback boot UUIDs, one
canonical repository journal USB location, one bounded fastboot serial, and
one absolute canonical host-pin path outside the repository. The contract
does not open or validate the target of that pathname; this is deliberately
left for a separately reviewed descriptor-relative executor boundary.

## Regression evidence

Focused hardware-free results on the final contract bytes before documentation:

- executor contract: 8/8 hostile groups in 0.080 seconds;
- callback adapter: 7/7 in 0.425 seconds;
- transaction journal: 9/9 in 0.891 seconds;
- sequence reference: 8/8 in 0.137 seconds;
- joint retention admission: 24/24 in 3.544 seconds;
- fallback ACM control: 72/72 in 3.324 seconds;
- repository-runner contract: PASS in 5.948 seconds;
- artifact-gated production HOLD profile: PASS in 10.380 seconds;
- artifact-gated observation HOLD profile: PASS in 3.962 seconds; and
- Python bytecode compilation and profile JSON parsing: PASS.

The required artifact-gated command was:

```text
REQUIRE_CURRENT_PRODUCTION_ARTIFACT=1 \
REQUIRE_CURRENT_OBSERVATION_ARTIFACT=1 \
scripts/host/test-repository-linux.sh ci
```

It passed the complete repository Linux `ci` tier in 317.093 seconds before
this timing paragraph was added. The immediately preceding exact staged
checkpoint took 316.610 seconds, so the contract checkpoint was 0.483 seconds
(0.15%) slower; that difference is operationally unchanged. Inside the full
run, the new executor-contract suite took 0.090 seconds, the corrected adapter
0.423 seconds, and joint admission 3.473 seconds. The command is rerun after
staging this paragraph so the handed-off tree, including this evidence, is
verified byte-for-byte; that final duration is reported in the handoff rather
than causing a self-referential post-verification edit.

## Remaining boundary

This contract is not a launcher. It does not consume a claim, export an
environment, open the known-hosts path, inspect USB, execute a helper, or kill
a process. The follow-on [pure executor boundary](2026-08-10-retention-cycle-executor-boundary-offline.md)
now models interpreter/program/host-pin descriptor revalidation and exact
output decoding without performing I/O. The follow-on
[boot-output checkpoint](2026-08-10-retention-cycle-boot-output-contract-offline.md)
defines and hostile-tests the canonical result for all three transitions.
Fallback now has a grounded guarded producer; execution and observer remain
blocked by their current HOLD gates. Runtime descriptor collection and bounded
process control remain offline work before any launcher, claim, or connected
admission review.

No phone, credential, signing, claim consumption, policy admission,
privileged-host change, build deletion, candidate operation, flash, wipe,
slot, or phone-storage action occurred. Recommendation remains **HOLD**.
