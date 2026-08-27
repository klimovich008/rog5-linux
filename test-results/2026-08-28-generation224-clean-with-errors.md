# Generation 224 post-repair verification

- Primary question: did Generation 223 leave a clean exact native root?
- Result: exact UUID, block count and label passed; ext4 state is `clean with errors`.
- Tree: skipped by the fail-closed verifier because filesystem state was not exactly clean.
- Prefix hash changed to `a00ae250...`, consistent with the completed filesystem mutation but not proof of file content.
- Phone storage modified: none in this cycle.
- Outcome: exact slot-A fastboot and host cleanup passed; `FALLBACK_RETURNED`.
- Candidate: consumed and permanently non-retryable.
- Successor: Generation 225 prechecks both repaired hashes read-only, then runs only bounded `e2fsck -p`, verifies clean state/tree and relocks p24.
