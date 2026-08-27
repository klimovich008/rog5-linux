# Generation 225 p24 fsck pass

- Precheck: exact `clean with errors` state and both repaired SSH binary hashes passed read-only.
- Operation: p24-only `e2fsck -p` under a 600-second softdog; exit status 1 (errors corrected).
- Postcheck: ext4 state clean, all seven boot-critical objects exact, all UFS nodes relocked.
- Runtime: one authenticated SSH attempt; completed and returned exact slot-A fastboot in 151.211 seconds.
- Intent: `TARGET_ACCEPTED`.
- Candidate: consumed and permanently non-retryable.
- Next gate: fresh RAM-only native-root boot to systemd and key-only SSH; no persistent slot-B flash yet.
