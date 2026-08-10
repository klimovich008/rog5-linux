# Retention-cycle callback adapter — offline

Date: 2026-08-10

Repository SHA before and after implementation:
`a7fa97d0b76c3e474e45ee327f4d71a776077e32`

Recommendation: **HOLD**

## Defect fixed

The durable transaction journal defined exact action intents, but nothing
proved how the existing fixed helper entry points map onto those intents. A
future orchestrator could therefore call a claim consumer, temporary-boot
gate, fallback reboot, or observer read before the corresponding event had
been durably published.

`scripts/host/retention-cycle-adapter.py` is a callback-only hardware-free
fixture for that mapping. It has no built-in executor, command-line entry
point, subprocess, credential, USB, SSH, fastboot, or device interface. Tests
inject callbacks and inspect the already-fsynced journal event before returning
synthetic exact results.

## Exact identity

| Input | Value |
|---|---|
| source path | `scripts/host/retention-cycle-adapter.py` |
| source size | 10,260 bytes |
| source mode | `0644` |
| source SHA-256 | `c36b4bfa407b4c5d0df6e32f2b69ebbbf411eaad75649465f89161aa84bf6976` |
| journal SHA-256 | `a7018537e2ad8aace316efc03cf4557c3871f0c777f0dc63ea1d787f242fe5ce` |
| cycle SHA-256 | `d8a3a085d2dfb474728d16cdf568547e529f026239a37a40881183c04ed8a078` |
| fixed invocation descriptors | 6 |
| live entry point | none |
| built-in executor | none |
| claim registration | none |
| policy allow rows | zero |

The HOLD profile and joint verifier pin all fields and both source identities.
The adapter source, journal binding, cycle binding, execution model, claim
registration, or policy count cannot be changed without failing admission.

## Exact invocation map

| Durable intent | Fixed helper descriptor |
|---|---|
| `execution-claim-intent` | `consume-exact-boot-claim.py retention-host-rendezvous-v3-execution-v1` |
| `execution-boot-intent` | `run-stable-recovery-live-gate.sh boot` |
| `bootloader-transition-intent` | `fallback-acm-control.py reboot FALLBACK_HOST_PIN` |
| `observer-claim-intent` | `consume-exact-boot-claim.py retention-host-rendezvous-v3-observer-v1` |
| `observer-boot-intent` | `run-observation-recovery-live-gate.sh boot` |
| `postmortem-read-intent` | `stable-recovery-control.py postmortem-status headless-netroot-early-diag-v2 TARGET_BOOT_ID` |

These are descriptors, not executable calls. The two claim identifiers remain
absent from the generic consumer. Both current boot gates reject `boot`, and
the temporary-boot policy has zero `allow` rows.

The original fixture descriptor named the legacy SSH-key reboot helper. The
accepted lifecycle uses the nonce-framed ACM helper, so the descriptor was a
real integration defect even though no process could be launched. The fixed
descriptor carries a placeholder for one canonical known-hosts pathname and
does not accept a private SSH key. The separate [executor-contract
checkpoint](2026-08-10-retention-cycle-executor-contract-offline.md) pins that
boundary without opening the path or adding execution.

Target/fallback boot IDs, USB location, fastboot serial, and postmortem
classification are validated before the first intent. Target and fallback IDs
must be distinct. Each callback result has exact fields, values, and Python
types; integer/boolean aliasing is rejected. The journal is rechecked after
every callback, so callback-side state mutation cannot satisfy the adapter.

## Regression evidence

The fail-first test failed in 0.059 seconds because the adapter source did not
exist. After implementation:

- callback adapter: 7/7 hostile groups pass in 0.405 seconds, with repeated
  focused passes in 0.421 and 0.416 seconds;
- transaction journal: 9/9 pass in 0.887 seconds;
- pure sequence reference: 8/8 pass in 0.126 seconds;
- joint retention admission: 24/24 pass in 3.440 seconds;
- repository-runner contract: PASS in 5.946 seconds;
- artifact-gated production recovery HOLD profile: PASS in 10.517 seconds;
- artifact-gated observation recovery HOLD profile: PASS in 4.043 seconds;
- current recovery status: PASS in 0.019 seconds; and
- the complete focused checkpoint passed in 25.213 seconds.

Coverage proves exact descriptor paths/arguments, fsynced-intent-before-call
ordering, all six callback failures, refusal to restart from an ambiguous
intent, hostile/malformed/type-aliased callback results, invalid evidence
before callback, exact final lineage, one postmortem call, source-level absence
of live interfaces, absent draft claims, and zero policy admissions.

The previous required full-tree command was:

```text
REQUIRE_CURRENT_PRODUCTION_ARTIFACT=1 \
REQUIRE_CURRENT_OBSERVATION_ARTIFACT=1 \
scripts/host/test-repository-linux.sh ci
```

It passed the earlier adapter-only exact staged checkpoint in 318.844 seconds,
then again after the evidence record was finalized in 316.610 seconds, versus
the 335.797-second pre-adapter baseline. The executor-contract checkpoint adds
its own final exact-tree CI result in the linked report. Repository HEAD
remained `a7fa97d0b76c3e474e45ee327f4d71a776077e32`; no commit or publication was
performed.

## Remaining gap

This fixture proves orchestration order but intentionally supplies no real
executor. The follow-on pure contract now binds fixed environment/input and
process descriptors. The later [pure executor boundary](2026-08-10-retention-cycle-executor-boundary-offline.md)
models descriptor revalidation and decodes the two claims plus postmortem JSON,
but proves the synthetic boot results cannot yet be derived from current helper
output. It adds no launcher, claim, or live profile capable of moving either
current gate out of HOLD. Those remain separate review and admission decisions.

No phone, credential, signing, claim-consumption, policy-admission,
privileged-host, retained-build, flash, wipe, slot, or storage operation
occurred. Complete artifact-gated repository CI passed at the final staged
checkpoint. Recommendation remains **HOLD**.
