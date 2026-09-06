# Generation 221 native-root tree failure

- Primary question: did the completed stock-fastboot transfer produce the exact grown Arch filesystem on p24?
- Earliest failed stage: boot-critical tree verification after exact grown ext4 geometry, UUID, label and clean state passed.
- Evidence: target runtime reached key-only SSH at 6.90 seconds; UFS exposed the expected 117 read-only block nodes; the verifier emitted `status=FAIL reason=target-tree`; exact slot-A fastboot fallback and host cleanup passed.
- Root cause: unproven. The host-finalized image satisfies all seven predicates under the exact sealed AArch64 BusyBox, so either an on-device inode differs or a target-only read condition remains unobserved.
- Failure class: R2 pending exact deployed-byte classification.
- Candidate: consumed and permanently non-retryable.
- Phone storage modified: no; all UFS nodes remained read-only.
- Existing test gap: the verifier collapsed seven predicates into one `target-tree` reason.
- Regression: Generation 222 emits bounded per-item metadata/hash records and rejects missing, reordered, contradictory or unbounded records.
- Successor prerequisite: focused target/parser tests, frozen exact artifact checks, exact-head CI and non-consuming connected preflight.
