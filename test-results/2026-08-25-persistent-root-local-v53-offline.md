# Persistent-root local V53 / Generation 162 offline

- Generation 161 reached mounted local Arch and then failed `root-verify`.
- The exact image matches every required seal, UUID, mode, size, symlink, and
  boot-critical file hash. `verify_exact_local_image_probe()` rejected the
  `staged-seal` token in its UUID-only branch before the intended absence check.
- V53 routes exact `read-only:staged-seal` directly to the required absent-probe
  check. All other probe policies are unchanged.
- Kernel, DTB, modules, firmware, staged image, storage policy, and stable
  recovery raw bytes are unchanged.
- Target twins completed in 3.433 and 3.373 seconds and matched at SHA-256
  `9a2659ac403ee8c3cba6767b90c79d61bb601bddf61e408cce6953ca9086e0cb`.
- Signed bundle twins matched at manifest SHA-256
  `4a55d0f6010779abc0cc7ecc22367a1b75451b2fc3bfb26a4922d02557d316ca`.
- Generation 162 wrapper SHA-256 is
  `d642f0e0f9a42e1bc308ae62d310bb35403417c4f671442074ecc9aac2092df3`;
  raw recovery bytes are unchanged. Candidate remains offline with no authority.
- Focused initramfs, candidate, runner, and gate checks passed in 11.82 seconds.
  The active repository tier passed in 57.724 seconds.
- Exact-head, merge-compat, candidate-publication, and QEMU CI passed for
  `ff20d61af20dacd9f6274f43845eb9746cf126e1`. Generation 162 is admitted once.
