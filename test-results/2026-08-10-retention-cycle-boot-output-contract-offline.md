# Retention-cycle boot-output contract — offline

Date: 2026-08-10

Recommendation: **HOLD**

Repository HEAD remained
`a7fa97d0b76c3e474e45ee327f4d71a776077e32`. No commit, fetch, merge,
rebase, publication, phone contact, credential use, signing, claim, policy
admission, privileged host change, or retained-data deletion occurred.

## Concrete defects fixed

The pure boundary could previously decode only claims and postmortem output.
The three boot helpers did not expose one exact machine record containing all
journal-required identity, so a future launcher could only guess those values
from mutable host state after process exit.

The contract now requests exactly one terminal
`ROG5_RETENTION_BOOT_RESULT_V1` record for every boot action. The pure decoder
validates caller-supplied program, interpreter, and host-pin descriptor
evidence and compares every result field with the immutable process inputs and
journal lineage. Old human-readable markers, marker-like echoes or duplicates
on either output stream, nonterminal records, unknown or reordered fields,
hostile diagnostics, mismatched descriptor identity, and missing lineage fail
closed. A later runtime must still prove that the evidence came from the held
descriptors actually used for that child process.

Fallback had a separate identity gap: same-port discovery accepted any unique
fastboot serial. It now requires the expected serial before accepting the
exact `0b05:4daf` product and emits the actual verified physical location,
product, serial, and SHA-256 of the inspected public allowed-signers bytes.
The production recovery gate emits its result only after its existing success
and rollback evidence and revalidates that the ACM endpoint belongs to the
expected physical USB ancestry.

The selected execution and observation profiles remain HOLD and have no
current successful producer. The observation gate merely advertises the
protocol during offline policy inspection. Thus all six results are decodable,
only fallback has a guarded current producer, and no connected lifecycle is
possible.

The observation artifact gate now also pins its repository verifier before
invocation: exact owner/group, mode `0755`, one link, 19,876-byte size, and
SHA-256 `c3c75dd55167e898edd92a04e4afd2aae1c3d4cf826cd1011ac32c6e9f8214c2`.
Changed and symlinked verifier fixtures fail closed.

## Exact identities

| Item | Value |
|---|---|
| executor contract | 14,560 bytes, mode `0644`, `8705c7fdfa9213a876128614057438565a4889087f77df7c2f41bdd9fe96be3e` |
| executor boundary | 24,548 bytes, mode `0644`, `76cd7367e73e1ec8e38d545b2cf387c8700279dca6aba3f337a9a9123b8f1e43` |
| production recovery gate | 64,136 bytes, mode `0755`, `2ca017c152a2ad60e6dad3475bce4986c8853e7d5f8da8680f330d36c4e6498e` |
| fallback ACM helper | 109,852 bytes, mode `0755`, `685383b58e928df924fbb2472691338e99a90da5f78eb13775152437d90da83a` |
| observation recovery gate | 9,531 bytes, mode `0755`, `cd154ad0c75e49c222bc2ca64ebe7453d3e9486a8dda19a240e5d88dd868eb9d` |
| observation wrapper verifier | 19,876 bytes, mode `0755`, `c3c75dd55167e898edd92a04e4afd2aae1c3d4cf826cd1011ac32c6e9f8214c2` |
| live entry point / built-in executor | none / none |
| runtime closure / admitted host-pin digest | unproven / not defined |
| claims / policy allow rows / boot authority | none / zero / none |

## Fail-first and hostile evidence

The expanded boundary test failed first in 0.121 seconds because boot decoding
and descriptor attestation did not exist. The expanded fallback suite failed
first in 3.328 seconds because the helper neither bound the expected serial nor
emitted a grounded terminal record. The executor-contract test failed first in
0.079 seconds because the reviewed USB/serial inputs and boot-result protocol
were absent.

Focused final-byte tests passed:

- executor boundary: 11/11 in 0.185 seconds;
- executor contract: 8/8 in 0.099 seconds;
- fallback ACM control: 74/74 in 3.949 seconds;
- joint retention admission: 25/25 in 4.259 seconds;
- stable-recovery gate: PASS in 5.090 seconds;
- production recovery HOLD profile: PASS in 12.135 seconds;
- observation-recovery HOLD gate: PASS in 4.199 seconds; and
- Python compilation plus canonical profile JSON parsing: PASS.

The hostile cases cover exact one-record framing, duplicate/marker-like echoed
records on stdout or stderr, field order and count, descriptor mismatch,
serial/product/location drift, host-pin digest drift, wrong ACM ancestry,
changed/symlinked observer verifier, diagnostics bounds, process failure, and
preservation of HOLD, empty claims, and zero policy rows.

The complete artifact-gated repository `ci` tier passed these staged source
bytes in 318.130 seconds. The immediately preceding executor-boundary
checkpoint passed its final exact-byte run in 320.260 seconds, so this
checkpoint is 2.130 seconds (0.67%) faster; the difference is operationally
unchanged. A second run after staging this timing paragraph verifies the final
documentation bytes, with its duration reported in the handoff to avoid a
self-referential edit.

An independent two-axis review found no hard repository-standard violation or
scope creep. It identified marker-like stderr/echo duplication and an unpinned
observation verifier; both are corrected and hostile-tested here. Its concern
about cross-cycle stale output is retained as a runtime-closure requirement,
not overstated as solved by this pure decoder.

## Remaining boundary

The minimal next step is a pure offline runtime-closure fixture that collects
and revalidates the exact descriptors it would use, performs bounded process
control, binds each child outcome to one fresh fsynced action intent, and
passes those attestations to this decoder. Cross-cycle stale-result exclusion
belongs to that fresh-pipe/intent binding and is not claimed by this pure
caller-supplied evidence model. It must not be wired to claims, credentials,
either recovery gate, or a phone until separately reviewed. Clean twin
candidate issuance and any hardware admission remain separate decisions.

Recommendation remains **HOLD**.
