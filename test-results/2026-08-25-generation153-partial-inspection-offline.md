# Generation 153 read-only partial inspection

Result: **OFFLINE PASS; UNBOOTED; ADMITTED ONCE.** Never flash or retry after
claim entry.

After Generations 151 and 152 reproduced the same generic partial-identity
failure, the explicit-only systematic-debugging workflow requires evidence
instead of another guessed acceptance change. Generation 153 mounts userdata
`ro,noload`, leaves every block node read-only, reports exact partial and
directory metadata, and performs no file or block mutation.

Target initramfs twins built in 6.530 seconds and match at SHA-256
`952e2f8d39bb9e691e622456a233531d286c948852434bac76e8dfddf5ec458e`,
size 23,804,046 bytes. The sync-independent restart2-plus-SysRq fallback is
retained.

Signed bundle manifest SHA-256:
`f5d6229a85f2842cb3c0242f01b7788fc99f6443ade34d330ccd251433856dde`.
Generation-153 RAM-only AVB SHA-256:
`d05d4730a65bc6b2c1018b436996bb9aea56fead90a08f23e50516594845152b`.
