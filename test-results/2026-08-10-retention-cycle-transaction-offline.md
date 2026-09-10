# Retention-cycle transaction journal — offline

Date: 2026-08-10

Repository SHA before and after implementation:
`a7fa97d0b76c3e474e45ee327f4d71a776077e32`

Recommendation: **HOLD**

## Defect fixed

The pure two-claim sequence established the required order, but no durable
record carried its dynamic identity across process boundaries. In particular,
the fallback helper's same-port fastboot proof ended with that process, the
later image-boot boundary accepted only a serial, and no durable intent was
entered before the one allowed `postmortem-status` read. A host crash could
therefore leave the observer with an unprovable port handoff, unknown claim
dispositions, or an ambiguous read budget.

`scripts/host/retention-cycle-transaction.py` adds an offline-only fixture for
that missing contract. It does not call a lifecycle helper, claim consumer,
credential reader, USB API, fastboot, SSH, or another process, and it has no
command-line entry point. The current connected gates remain closed.

## Exact identity

| Input | Value |
|---|---|
| source path | `scripts/host/retention-cycle-transaction.py` |
| source size | 39,553 bytes |
| source mode | `0644` |
| source SHA-256 | `a7018537e2ad8aace316efc03cf4557c3871f0c777f0dc63ea1d787f242fe5ce` |
| cycle SHA-256 | `d8a3a085d2dfb474728d16cdf568547e529f026239a37a40881183c04ed8a078` |
| event format | `rog5-retention-cycle-event-v1` |
| live entry point | none |
| claim registration | none |
| policy allow rows | zero |

The authority-free retention profile and verifier pin every field above. A
source mutation, metadata mutation, profile mutation, live-entry declaration,
claim registration, or policy admission fails the joint review.

## Durable semantics

One caller-owned mode-`0700` root contains one cycle-digest-named mode-`0700`
directory. Every event is a new mode-`0600`, single-link, no-follow regular
file with canonical one-line JSON, an exact event index, the cycle digest, and
the previous event's SHA-256. Event publication uses exclusive creation,
file `fsync`, directory `fsync`, descriptor/path revalidation, and exact
inventory revalidation. The open cycle directory itself is non-blocking
locked, so a second writer is refused.

The journal binds the host boot ID and physical USB location before any
claim. It then records distinct intent and observed boundaries for both claims
and both temporary boots, target and fallback boot IDs, exact fallback
identity, ramoops preflight, the same USB location, exact `0b05:4daf` product,
one fastboot serial, and observer recovery. Target and fallback boot IDs must
be distinct.

Before the observer request, the journal irreversibly records a one-read
`postmortem-status` intent. A process reopening at that or any other ambiguous
action-intent boundary may only append a terminal `INCONCLUSIVE` result; it
cannot retry the action. Missing or lost postmortem output therefore cannot
silently create a second read. `MATCH` and `MATCH_REPEATED` still mean only
`LINEAGE_RETAINED`, never proof that no crash occurred.

## Regression evidence

The fail-first test failed in 0.062 seconds because the transaction source did
not exist. After implementation:

- transaction journal: 9/9 hostile groups pass in 0.847 seconds;
- joint retention admission: 22/22 pass in 3.008 seconds;
- sequence reference: 8/8 pass; and
- repository-runner contract: PASS.

Hostile coverage includes every crash prefix, claim-disposition
reconstruction, ambiguous-intent reopen, single-read loss, wrong port, wrong
serial, duplicate boot ID, wrong product and recovery, rollback removal,
tampered and noncanonical JSON, event gaps, unknown entries, hard links, weak
modes, concurrent writers, and root pathname replacement.

## Remaining gap

This is a durable offline fixture, not a live orchestration runner. The
follow-on [callback adapter](2026-08-10-retention-cycle-adapter-offline.md)
now proves six fixed fake helper descriptors occur only after their matching
durable intents, but it deliberately has no executor. Existing helpers do not
write these events, `verified-fastboot-boot.py` does not yet consume the
journal's USB-location anchor, and neither draft claim is defined, registered,
or issued. Real connected paths remain rejected pending separate claim,
profile, executor, and exact-head review.

No phone, credential, signing, claim-consumption, policy-admission,
privileged-host, retained-build, flash, wipe, slot, or storage operation
occurred.

## Final checkpoint

The exact final command was:

```sh
REQUIRE_CURRENT_PRODUCTION_ARTIFACT=1 \
REQUIRE_CURRENT_OBSERVATION_ARTIFACT=1 \
scripts/host/test-repository-linux.sh ci
```

Result: PASS in 335.797 seconds. The preceding complete-CI checkpoint was
332.609 seconds, so this run was 3.188 seconds slower (0.96%). In that run the
registered transaction suite passed 9/9 in 0.897 seconds, the sequence suite
passed 8/8 in 0.119 seconds, and the joint admission suite passed 22/22 in
3.066 seconds. The preceding focused checkpoint passed all transaction,
sequence, admission, runner, current-profile, and current-status tests in
25.317 seconds.

`git diff --check` and `git diff --cached --check` passed before CI. Starting
and ending repository SHA remain
`a7fa97d0b76c3e474e45ee327f4d71a776077e32`; the checkpoint is staged and
does not create a commit. Recommendation remains **HOLD**.
