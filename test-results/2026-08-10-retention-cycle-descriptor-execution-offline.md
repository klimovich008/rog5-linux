# Retention-cycle held-descriptor execution fixture (offline)

Date: 2026-08-10

Recommendation: **HOLD**

## Concrete defect fixed

The preceding runtime closure held the exact program and interpreter but forked
a fixed writer that emitted caller-supplied test bytes. It proved durable
intent, fresh pipes, bounded process supervision, and exact result decoding,
but it did not prove that an interpreter and program reached `exec` through
the descriptors that had been inspected. Production descriptor execution was
therefore correctly recorded as unproven.

The fail-first suite took 0.096 seconds and stopped because
`scripts/host/retention-cycle-descriptor-execution.py` did not exist.

## Offline correction

Two mode-`0644` sources define a disconnected successor fixture:

- runner: 30,039 bytes, SHA-256
  `7e82e52ed44343f665f5f03f26b8540c7743415d74145c58db0eb3b935dd1d8a`;
- harmless probe: 5,288 bytes, SHA-256
  `afba8ae9c2bff325eadcae781895aafd7934897b238edcdc72bf73f7f38e20f5`.

For one kernel-generated 256-bit nonce the runner:

1. opens and holds the repository directory, exact probe, and pinned
   `/usr/bin/python3.13` interpreter with no-follow/CLOEXEC descriptors;
2. verifies owner, mode, link count, size, digest, device/inode identity, and
   the `/usr/bin/python3 -> python3.13` symlink before and after execution;
3. creates distinct empty nonblocking CLOEXEC stdout/stderr pipes;
4. creates a new session/process group, changes cwd with `fchdir()` on the held
   repository descriptor, applies umask `0077`, and installs devnull stdin;
5. duplicates only the held probe to descriptor 198 and interpreter to 199,
   closes every unrelated descriptor, then executes the interpreter by file
   descriptor; the exact argv names `/proc/self/fd/198` as the program;
6. passes one closed, parent-independent environment and no credential,
   authority, device, or user-selected path;
7. bounds both output streams, deadline, TERM/KILL process-group cleanup, and
   one attempt/one decode; and
8. accepts only one canonical evidence record that independently reports the
   program/interpreter digests and identities, full kernel-visible exec argv,
   Python argv/environment digests, cwd, umask, devnull/FIFO state,
   session/process-group leadership, and exact open descriptor inventory
   `0,1,2,198`.

The probe has five fixed modes: success, timeout, descendant, overflow, and
nonzero exit. There is no caller-supplied stdout/stderr or arbitrary argv,
environment, cwd, deadline, path, or command seam.

## Hostile evidence

`scripts/host/test-retention-cycle-descriptor-execution.py` passes 11 test
groups in 0.507 seconds:

- exact held interpreter/program execution and canonical context evidence;
- mutation refusal for argv, environment, cwd, umask, stdio, limits,
  deadlines, and fixed execution descriptors;
- program, interpreter, and repository pathname identity changes before fork;
- program pathname identity changes during execution and before decode;
- inherited parent-descriptor closure across exec, including a descriptor
  above a deliberately lowered soft `RLIMIT_NOFILE`;
- status-aware process-group signaling that never falls back to a possibly
  reused direct PID after the child has been reaped;
- bounded timeout, hostile descendant PID/pipe-EOF cleanup, overflow, and
  nonzero-exit handling;
- cross-preparation, reopened, duplicate-attempt, and duplicate-decode refusal;
- malformed output and aliased pipe-identity refusal; and
- source/profile proof of no CLI, output injection, live entry point, adapter
  wiring, production execution, connected admission, credential use, claim,
  policy allow row, result authority, or phone action.

The expanded exact admission suite passes 27 tests in 4.077 seconds and pins
both fixture sources plus every execution invariant.

## Independent review

The focused specification review found four concrete gaps. The correction now:

- inventories `/proc/self/fd` instead of assuming the soft descriptor limit is
  an upper bound;
- distinguishes `ECHILD` from a still-running child and permits direct-child
  signal fallback only while the child is known unreaped;
- makes decode terminal as soon as the internally issued proof object is
  presented, even when its output is malformed; and
- hashes the complete kernel-visible exec argv, including `argv[0]` and `-B`.

The standards review found no repository-standard violation. It did note that
process supervision now exists in both this fixture and the frozen runtime
closure. Extracting a shared supervisor at this checkpoint would broaden the
reviewed change and disturb the already green runtime-closure identity, so that
refactor is intentionally deferred until production-helper integration; the
two implementations must not be allowed to diverge silently.

## Scope boundary

This result proves the held-descriptor execution mechanism using a harmless
repository-owned probe. It does **not** execute the six production helper
descriptors. In particular, the two Bash helpers currently derive the
repository from `BASH_SOURCE[0]`; switching their script argv directly to a
`/proc/self/fd` pathname would change that behavior and requires a separate
inert-harness review. The profile therefore records:

- `fixture_descriptor_execution=proven`;
- `production_descriptor_execution=unproven`;
- `adapter_wiring=none`;
- `production_execution=none`;
- `authority=none` and `boot_authority=none`.

The next offline step is to make all six exact production `ProcessSpec`
descriptors compatible with descriptor-relative invocation and prove them in
an inert harness that cannot reach a phone, credentials, claims, recovery
gates, or privileged host services. Only a later separate review may consider
adapter eligibility.

No phone, USB device, credential, signer, claim, policy allow row, privileged
host operation, build artifact, VCNL36866 file, or storage deletion was used.
