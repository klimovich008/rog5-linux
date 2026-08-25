# Generation 151 crash-bounded UFS write benchmark

Result: **OFFLINE PASS; UNBOOTED; ADMITTED ONCE.** Never flash or retry after
claim entry.

Generation 150 proved the write benchmark itself did not run because ext4
recovery changed the partial file's exact pre-crash tuple. Generation 151
keeps the same 64 MiB total benchmark and accepts only safe crash outcomes:
partial absent, or one root-owned regular file with one link, mode 0600/0644,
and size from 1 through 825,884,672 bytes. It reports exact observed size and
mode before the direct-first benchmark.

Target initramfs twins built in 6.477 seconds and match at SHA-256
`e8334a941c54efa4cb09718e34150a94c80022ad1dfcddb6026ea4c6f9dcdd41`,
size 23,805,018 bytes. Kernel, DTB, modules, benchmark sizes, storage scope,
and sync-independent fallback are unchanged.

Signed bundle manifest SHA-256:
`eda3bd6c644adb12254cf92d1c32dab1ace1982809227f0eb1917286c8cd36e9`.
Generation-151 RAM-only AVB SHA-256:
`a90a25e8270e85205f1898c02e7ce8b146a0e583770cba93cf1f7e23e99a2e35`.
