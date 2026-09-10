# Reviewed deployment-checkpoint isolation

Result: **PASS; host-only, authority-free, and credential-free.**

The review started at
`e4303e27c90666ae4a1eb21b7d276c1c423e6dd6`. No phone command, phone
storage access, credential access, signing, deployment, or boot occurred.

## Concrete defect fixed

The guarded deployment launchers fetched and verified the exact origin head
and sealed the top-level implementation, but the sealed implementation then
ran the remaining scripts and read repository data from the mutable branch
checkout. A concurrent checkout or reset after launcher verification could
therefore change credentialed build inputs without changing the already-sealed
top-level script.

Both launchers now create a private detached Git worktree at the exact reviewed
commit and pass that immutable checkpoint to the sealed implementation. All
build scripts and tracked data are read from that worktree. The original
checkout is used only to refresh and revalidate the exact expected commit
before credential read and as the final ignored-output destination. Output is
built inside the checkpoint and published with no-clobber rename semantics
only after the private-key snapshot is destroyed. The checkpoint worktree is
removed on preflight, success, failure, signal, and launcher `execve(2)`
failure.

The signing-input stager now accepts the launcher-pinned commit, compares the
fresh origin-verified checkpoint with it, and revalidates after candidate
validation but before reserving outputs or reading the signing key.

## Regression proof

- The hostile launcher fixture proves the detached worktree and sealed memfd
  remain byte-exact after the mutable checkout implementation is replaced.
- The preflight integration proves the reviewed worktree is removed and no
  build output is published.
- A signing-input race advances the repository after candidate validation and
  proves refusal occurs before signing-key read or output creation.
- A mismatched launcher checkpoint likewise fails before any private input is
  read.

The new checkpoint-race regression failed before the fix in 198 ms because the
stager had no pinned-checkpoint interface. It passed after the first fix in
249 ms. Final focused timings were:

- signing-input suite: 2,781 ms, 15 tests;
- deployment launcher contract: 1,175 ms.

The implementation checkpoint `scripts/host/test-repository-linux.sh ci`
passed in 612,108 ms. The preceding baseline was 608,871 ms, a 3,237 ms
(about 0.5%) increase. The exact final-checkpoint timing and ending commit are
reported in the handoff for the commit containing this record.
