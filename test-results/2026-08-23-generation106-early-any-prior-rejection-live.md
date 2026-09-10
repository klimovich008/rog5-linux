# Generation 106 early any-prior rejection

Date: 2026-08-23

Result: **CONSUMED; EXACT EARLY POLICY BUG PROVEN.** Generation 106 must never
be retried or flashed.

The repository continuous lifecycle passed claim, recovery, signed transfer,
PREPARE, COMMIT, and target-network activation. Target NCM appeared at
09:58:31. The host address, stage listener, and target host-key process were
ready at 09:58:33. Target USB departed at 09:58:51 with zero stage and host-key
bytes. Stock slot A returned, though its unauthorized descriptor proof was not
accepted; the durable intent resolved `FALLBACK_RETURNED`.

This rules out the previous manual attachment race. Source review found the
exact pre-reporter failure: `persistent-root-init` validates
`expected_ufs_storage_mode:expected_probe_boot_id` before stage reporter start.
The marker verifier and attestation accepted `any-prior`, but this earlier case
still sent it through the literal-UUID branch and `fail_stage` with the
`kernel-release-file` 20-second delay. That exactly matches zero stages and the
20-second target lifetime.

The regression requires the explicit `read-only:any-prior) ;;` early policy
case. The successor changes only that target initramfs source, retains the
current charging/UFS/NCM Image and DTB, and runs through the same continuous
lifecycle. No target storage write occurred in Generation 106.
