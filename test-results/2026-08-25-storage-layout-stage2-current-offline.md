# Current dedicated-layout Stage 2 offline

- Stage 2 now binds current userdata UUID, exact 16-GiB image hash, exact
  37,736-entry source tree, and slot-A rescue.
- The obsolete marker-bearing 37,738-entry native seal was replaced by the
  current source tree seal. UUID change and ext4 growth do not alter file-tree
  contents; the verifier excludes the seal file itself.
- Private config uses a fresh operation ID, retained GPT identities, current
  source UUID/hash, and the still-unused proposed target UUID.
- Clean twins completed in 1.900 and 1.829 seconds and matched at SHA-256
  `ae67a6fdb6e8d9ccbdf04cf527186d8e04d60ed55d0460a4ab389099145abdc2`.
- The sealed AArch64 runtime passed clone-prefix hashing, UUID change,
  correction-free fsck, ext4 growth, and tree verification in a private mount
  namespace.
- Status is offline HOLD. Stage 2 remains ineligible until refreshed Stage 1
  succeeds and slot-A rescue is reproven. No candidate, claim, phone boot, GPT
  operation, or storage write exists.
