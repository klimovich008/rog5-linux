# Retention-cycle exact-claim registry checkpoint — offline

Date: 2026-08-10

Starting exact repository HEAD:
`34d7af9948ccb0d345ea6365d6929cefe653ad86`

Recommendation: **HOLD**

No phone, USB device, fastboot, ADB, ACM/NCM session, phone storage,
credential, signing key, production signature, candidate issuance, boot claim,
temporary-boot policy row, privileged host action, flash, wipe, slot operation,
persistent installation, or phone boot was used. Generation 12 remains
consumed and non-retryable. The isolated VCNL36866 working tree was not
touched.

## Concrete defect

The generic exact-record consumer still regenerated every repository-owned
record from one Generation-11/12-specific candidate and manifest template.
Changing only the profile name therefore could not represent the two distinct
execution and observation-recovery claims required by the retention cycle.
The HOLD profile promised `distinct-exact-records`, but the consumer's lookup
could not encode distinct exact records without changing its template or
copying another generation-specific consumer.

The consumer now contains one literal repository-owned mapping from each
historical profile to its complete exact record bytes. Generation 11 and 12
records are byte-for-byte unchanged. The caller still supplies only a reviewed
identifier; it cannot supply a path, candidate, manifest, image identity, or
record content. Descriptor-relative no-follow access, owner/mode/content
validation, global and local no-replace entry, fsync, pathname revalidation,
concurrency refusal, source unlink, and irreversible at-most-once behavior are
unchanged.

No future record was added. In particular, neither the execution nor observer
role of `host-rendezvous-v3-observer-v1` is consumable.

## Fail-first and hostile tests

The new literal-registry regression failed against the previous
dict-comprehension implementation in 0.209 seconds while the other 12
consumer cases passed. After the correction:

- generic exact-claim consumer: 13/13 PASS in 0.210 seconds;
- retention admission hostile suite: 19/19 PASS in 2.637 seconds initially
  and 2.611 seconds after rebinding the profile;
- recovery-control build-record check: PASS in 0.068 seconds;
- real retained execution/observer joint verifier: PASS in 2.837 seconds.
- complete `scripts/host/test-repository-linux.sh ci`: PASS in 314.388
  seconds.

The retention verifier now requires one literal `CLAIMS` dictionary with the
exact historical key/value bytes. It rejects comprehensions, duplicate keys,
non-string keys, non-byte values, aliases, rebinding, late mutation,
preissuance of the active HOLD profile, and any unreviewed entry. The profile
pins consumer size 14,600 and SHA-256
`b6a3cc42db948dec706352d4cac1f8304c28550e678d607318986405b26a4c4e`.

Claude Code 2.1.220 was available and authenticated, but Anthropic refused the
requested read-only Opus review because its session quota was exhausted until
08:00 Europe/Paris. This was a quota limit, not a repository or security
failure. No Claude result is claimed.

## Critical-path ordering

There is no existing entry point that enforces the complete
target → exact Alpine fallback → bootloader → observation recovery →
postmortem-status sequence:

- `run-minimal-headless-live-cycle.py` keeps the production diagnostic path
  closed because Generation 12 is consumed;
- `recovery-linux.sh` handles one policy-admitted image and does not establish
  a two-claim retention transaction;
- `reboot-fallback-to-fastboot.sh` proves one fallback transition but does not
  bind either recovery claim;
- `stable-recovery-control.py postmortem-status` correlates an already-running
  observer and does not establish the preceding boot sequence.

The safe order for the remaining work is:

1. create and independently verify the final production execution and
   observer artifact identities without granting boot authority;
2. define two distinct literal one-use records bound to those final identities;
3. add an offline hostile lifecycle contract that consumes the execution
   claim before its boot, proves exact fallback and retention preflight,
   reaches the same-port bootloader, consumes the observer claim before its
   boot, and performs one lineage-bound postmortem read;
4. only after exact-head review, make candidate admission and a physical cycle
   separate decisions.

Production signing cannot safely follow claim issuance because signing or
repacking changes the exact boot identities the claims must bind. Building an
orchestrator before the two final claim identities exist would likewise leave
its most important inputs unspecified.

The minimal next action is exact-diff review, commit, and exact-head GitHub CI
for this authority-free registry correction. Candidate creation, signing,
claim issuance, policy admission, and hardware execution remain separate.
Recommendation remains **HOLD**.
