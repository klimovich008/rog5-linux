# Retention-cycle runtime-closure fixture (offline)

Date: 2026-08-10

Recommendation: **HOLD**

## Defect addressed

The transaction, callback adapter, process contract, and output decoder were
individually strict, but no layer proved that a decoded result arrived through
new pipes created after the matching durable action intent. A caller could
supply a structurally valid `ProcessOutcome` and descriptor attestation without
proving one fresh child lifecycle. The prior checkpoint therefore left
cross-cycle stale-result exclusion explicitly unproven.

The fail-first hostile suite took 0.101 seconds and stopped because
`scripts/host/retention-cycle-runtime-closure.py` did not exist.

## Offline correction

The new mode-`0644` runtime fixture is pinned at:

- size: 38,531 bytes;
- SHA-256: `2cce1d450805d4a5f43352b221d35011e43ade5868817cce37b322912f3c765b`.

For one freshly appended action intent it:

1. rejects a reopened or concurrently prepared intent;
2. opens and holds the canonical fsynced intent event, exact repository
   program, pinned Python/Bash interpreter, and, for fallback only, the exact
   caller-owned public host-pin file and private parent directory;
3. hashes and revalidates every held regular descriptor and pathname;
4. creates two distinct empty `O_CLOEXEC|O_NONBLOCK` pipes only after that
   intent check and generates a 256-bit kernel nonce;
5. forks a fixed offline writer in a new session with devnull stdin, pipe-only
   stdout/stderr, and all unrelated descriptors closed;
6. bounds both streams to the reviewed action limit, enforces an absolute
   fixture deadline, and terminates the process group with TERM then KILL;
7. rejects journal, intent, descriptor, path, pipe, process, or output changes;
8. wraps the existing exact decoder result as `authority=none` and
   `adapter_eligible=false`; and
9. releases the in-process preparation marker only after the journal advances
   by exactly one validated result event whose canonical data equals the
   result decoded from those pipes, while holding and immediately
   revalidating the descriptor-relative event pathname.

The fixture never invokes `ProcessSpec.argv`. Its child is a fixed offline
writer using test-supplied bytes. This proves intent/pipe/process/result
plumbing, including all six action transitions, but it does **not** prove that
an outcome was produced by executing the held production program and
interpreter descriptors. The profile records
`production_descriptor_execution=unproven`; no launcher or adapter wiring is
claimed.

## Hostile evidence

`scripts/host/test-retention-cycle-runtime-closure.py` passes 13 groups:

- actual program/interpreter/intent descriptor holds;
- all six actions in one complete journal, with release only after each exact
  result event;
- cross-cycle proof substitution and reopened-intent refusal;
- duplicate preparation and intent-path replacement;
- journal advancement while the child is active;
- preloaded-pipe refusal before fork;
- timeout, descendant, and output-overflow bounds;
- actual public host-pin hold and symlink refusal;
- wrong process contract and unrelated host-pin digest refusal;
- one-use decode/attempt behavior; and
- valid-but-different durable result data refusal; and
- result-event pathname replacement before marker release; and
- source/profile proof of no live entry point, production execution, adapter
  wiring, credential use, connected admission, claim, policy row, or result
  authority.

The focused runtime suite passed 13 tests in 1.055 seconds. The expanded joint
admission suite passed 26 tests in 3.777 seconds and now pins the runtime
source and its explicit production-execution limitation.

## Independent review

The standards axis found no README safety violation and no hard standards
failure. Its opaque stat-tuple finding was corrected with a named immutable
`StatIdentity`. Splitting descriptor preparation from process supervision and
moving runtime ownership into the frozen journal were retained as possible
future refactors because either would expand this safety checkpoint without
improving its evidence.

The first specification review found that a successful first action retained
the in-process preparation marker and blocked the remaining five actions. The
new exact-result finalization step and complete six-action regression correct
that defect. It also correctly found that the fixed writer does not execute
the held production descriptors; the profile, verifier, and this report now
state that limitation instead of calling production runtime closure proven.
The follow-up specification review found that finalization initially checked
only the result phase and event count. Finalization now opens and validates
the exact next event and requires its canonical data to equal the stored
decoded result; a hostile valid-but-different postmortem event is refused.
The final recheck then found that the validated event pathname could be
replaced before marker release. Finalization now retains the event descriptor,
revalidates the descriptor-relative pathname immediately before release, and
the hostile rename/replacement regression fails closed. A pre-final staged CI
pass completed in 319.422 seconds; the final exact-state pass is recorded in
the checkpoint handoff.

## Safety state

- profile: `hold`;
- authority / boot authority: `none` / `none`;
- execution / observer claims: `not-defined` / `not-defined`;
- temporary-boot policy allow rows: zero;
- live entry point / adapter wiring / production execution: none;
- credential use, phone contact, signing, issuance, claim consumption,
  privileged host change, and storage deletion: none;
- VCNL36866 work: untouched.

## Remaining boundary

The next offline step is a descriptor-execution closure with no output
injection seam: the launched child must demonstrably be the held interpreter
and program with the exact reviewed argv, environment, cwd, umask, devnull,
stream bounds, deadline, and process-group behavior. It must be tested first
against a harmless exact descriptor fixture and remain disconnected from the
six live helpers, claims, credentials, recovery gates, and phone. Only a later
separately reviewed integration may decide whether that mechanism can become
adapter-eligible.

Clean twin issuance and hardware admission remain separate decisions.
