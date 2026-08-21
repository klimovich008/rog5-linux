# V21 wrapper-cache snapshot-root miss

Primary question: can the corrected signed V21 build reuse the already
twin-proven ASUS recovery wrapper?

Earliest failed stage: wrapper cache lookup after signed bundle verification.

Observed evidence: the credentialed builder entered a temporary reviewed
worktree and started `make` for ASUS 5.4 even though the exact recovery input
key was already published in the main worktree cache.

Root cause: proven R6 host-path defect. The wrapper helper derived its default
cache from the temporary snapshot repository, so it could not see the
authoritative cache under the synchronized main worktree.

Disposition: the unnecessary compile was interrupted. No candidate output,
policy row, phone claim, COMMIT, or phone contact occurred.

Regression and correction:

- the sealed deployment builder passes the fixed synchronized checkpoint
  repository and its ignored cache root;
- the wrapper helper canonicalizes that repository and accepts only its
  `build/` subtree;
- static deployment contracts pin both environment assignments;
- a real cache-hit integration materialized the exact wrapper in 19.795
  seconds and printed `no ASUS kernel build ran`.

The interrupted build is evidence only and is never relabeled as a valid V21
candidate.
