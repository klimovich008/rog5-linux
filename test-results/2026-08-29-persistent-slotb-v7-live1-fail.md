# Persistent slot-B release v7 live 1 — FAIL (identity loaded)

- Primary question: does the integrated service automatically load the seeded
  persistent Ed25519 identity and preserve strict pinned SSH?
- V7 reached target USB in 29.957 seconds. Strict SSH against the previously
  pinned `WSn4Lik…` fingerprint passed automatically in 179.266 seconds,
  proving persistent key load and sshd HUP succeeded.
- Classification: R1 runtime-name collision. The helper executable and its
  publication record both used `/run/rog5-persistent-ssh-identity`; record
  publication therefore failed after the successful key switch and left the
  service failed/systemd degraded.
- State service, exact two-node write scope, p24 read-only, persistent marker,
  runtime/persistent key equality and strict SSH all remained valid.
- Regression: the record is now
  `/run/rog5-persistent-ssh-identity.record`, the test rejects the executable
  pathname as a record, and the helper explicitly refuses self-aliasing.
- The corrected helper passed live from tmpfs, publishing a root-owned 0444
  112-byte record while preserving the executable and stable fingerprint.
- V7 must not be reused as an acceptance candidate. V8 changes only the target
  initramfs; kernel, DTB, wrapper, loader, state image and persistent key stay
  unchanged.
