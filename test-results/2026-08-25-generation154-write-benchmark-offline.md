# Generation 154 proven-empty-partial UFS benchmark

Result: **OFFLINE PASS; UNBOOTED; ADMITTED ONCE.** Never flash or retry after
claim entry.

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
