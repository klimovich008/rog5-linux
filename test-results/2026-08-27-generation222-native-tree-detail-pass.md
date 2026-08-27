# Generation 222 native-tree detail pass

- Primary question: which boot-critical p24 objects differ from the finalized host image?
- Result: exact metadata passed for all seven objects; seal, init, systemd, authorized key and SSH policy content passed.
- Mismatches: `sshd` hash `cfcf0874...` and `ssh-keygen` hash `535ad8b0...`; both retained exact owner, mode, size and link count.
- Sparse correlation: both file extents cross zero-FILL chunks in the staged sparse image. This is the leading cause hypothesis, not yet a general ABL claim.
- Runtime: key-only SSH at 7.99 seconds; classification and exact fastboot return in 100.135 seconds.
- Intent: `TARGET_ACCEPTED`; candidate consumed and permanently non-retryable.
- Phone storage modified: none; all UFS nodes remained read-only.
- Successor: Generation 223 requires the two exact observed old hashes and writes only sealed `sshd`/`ssh-keygen` bytes under power, thermal, softdog, verification and relock gates.
