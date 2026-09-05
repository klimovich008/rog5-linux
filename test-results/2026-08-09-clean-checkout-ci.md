# Clean-checkout CI closure

Date: 2026-08-09

Status: **PASS offline; HOLD hardware admission**

This checkpoint closed clean-checkout defects found while validating the
critical NFS/USB work from a detached checkout. It did not contact the phone,
use credentials, sign or issue a candidate, or grant boot authority.

## Exact state

- Initial clean-checkout review base:
  `74e4d5dee4c890d4d22a63614f04e836e8a9acb1`.
- Fully passing implementation checkpoint:
  `28f78fe880fedde83c79468b1d95df2f4efc6273`.
- The detached checkout had no tracked or untracked Git changes before or
  after the full test run. Workflow-generated bootstrap files remained under
  ignored `artifacts/` paths.
- The existing uncommitted VCNL36866 work remained only in the primary working
  tree and was neither staged nor copied into the detached checkout.

## Defects closed

1. The dual-cell candidate contract assumed ignored `build/` already existed.
   It now creates that directory only when absent and removes only the
   directory it created. A fresh-checkout focused run passed in 0.111 seconds.
2. The observation-wrapper hostile suite read an ignored ASUS recovery config.
   The exact 185,763-byte config is now a tracked fixture with SHA-256
   `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f`;
   neighboring recovery artifacts remain ignored. Eight focused hostile tests
   passed in 8.365 seconds and the recovery policy test passed in 0.475 seconds.
3. Clean CI fetched the pinned Android boot tools but did not build their
   reproducible canonical boot-v3 template. Both exact-head and merge-compat
   jobs now build it before the repository runner, and the contract requires
   both setup steps. The generated 12,288-byte template has SHA-256
   `95be17d48ec61d00a4e8c92be754c8a8345f93685ce05d412a6d3a6aceba6e02`.
4. Tracking the config changed `manifests/artifacts.tsv`, but the compatibility
   oracle still pinned its previous identity. The manifest pin and its parent
   source/DTB profile pin are now chained to the new exact hashes. All 39 core
   oracle tests passed in 0.383 seconds and all 77 source/DTB hostile tests
   passed in 12.896 seconds in the retained-input development tree.

## Clean-checkout sequence and timing

- The first clean run exposed the missing `build/` assumption after 16.776
  seconds.
- The next run reached the ignored recovery-config dependency after 188.429
  seconds.
- The first run with the full bootstrap reached the stale manifest pin and
  failed after 34.375 seconds.
- The fresh detached checkout at the passing implementation checkpoint ran
  `scripts/host/test-repository-linux.sh ci` successfully in 300.793 seconds.
- For comparison, the earlier retained-input development-tree CI passed in
  476.059 seconds. These are end-to-end observations, not a controlled
  performance benchmark: the retained and clean checkouts exercise different
  optional artifact paths.

The passing run included the NFS hostile model, target rendezvous and timeout
tests, recovery lifecycle and one-use claim tests, watchdog and pstore policy
tests, exact-head workflow tests, observation-only wrapper tests, and the
generic retention-pair admission tests. Optional tests that require pruned
retained build trees reported explicit skips; no required suite failed.

## Decision

Keep **HOLD**. Clean reproducibility is now proven, but it does not establish
that the modeled host-readiness race caused Generation 12, prove ramoops
lineage across the physical target-to-fallback transition, or provide an
independent physical diagnostic channel. No candidate should be admitted,
signed, issued, or booted solely from this offline result.
