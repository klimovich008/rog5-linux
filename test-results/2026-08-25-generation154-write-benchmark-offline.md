# Generation 154 proven-empty-partial UFS benchmark

Result: **OFFLINE PASS; LIVE CONSUMED; FALLBACK_RETURNED.** Never flash or
retry.

Generation 153 proved the crash partial is exactly a regular root-owned
mode-0644 one-link file with zero size and zero allocated blocks. A fail-first
fixture now accepts that state while retaining every pathname, type, owner,
mode, link, final-absence, and logical-size guard. The benchmark remains one
32 MiB aligned direct write followed by one 32 MiB buffered write, with
disposable cleanup and sync-independent fallback.

Target initramfs twins built in 6.445 seconds and match at SHA-256
`d017b3d1bbf6b7c9974d7aba1083c3332a7aeec5611eaf00c0445e8d06f82259`,
size 23,805,026 bytes. Kernel, DTB, modules, and recovery raw bytes are
unchanged.

Signed bundle manifest SHA-256:
`14741fb36498f039e1711719ad542fa88e5b3b990a147d0877dbd8b400b8f25e`.
Generation-154 RAM-only AVB SHA-256:
`49fbe0fa5f243a522d29f8fcab34dc4618ad797d3ca9e36124c3db568324b839`.

## Live result

Failure class: **NEW — target UFS buffered writeback/fsync stall**.

- exact mainline NCM, UFS, storage lock, key-only SSH, and runtime passed;
- direct 32 MiB write completed in 50.25 seconds at the exact size;
- buffered 32 MiB `conv=fsync` did not return inside 180 seconds;
- the independent 420-second sync-free rollback returned directly to exact
  slot-A fastboot at USB path `1-1.2`;
- intent resolved `FALLBACK_RETURNED`; battery remained 8.702 V with SOC gate
  yes.

This cycle answered its single question: use aligned direct writes and skip
sparse holes; do not use buffered writeback for full-image staging.
