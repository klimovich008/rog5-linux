# Generation 223 native SSH repair partial result

- Primary question: can the exact two mismatched p24 binaries be repaired and relocked in one bounded cycle?
- Passed: exact old hashes, power/thermal gate, softdog arm, p24-only write window, both writes, and both new hashes while mounted.
- Earliest failure: post-unmount `filesystem-clean` assertion.
- Outcome: exact slot-A fastboot and host cleanup passed; intent resolved `FALLBACK_RETURNED`.
- Candidate: consumed and permanently non-retryable.
- Storage disposition: unknown after transport loss; do not infer that either hash persisted or that ext4 is clean.
- Next action: Generation 224 performs only read-only ext4-state and seven-item boot-critical verification.
