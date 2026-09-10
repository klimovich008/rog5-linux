# Generation 153 read-only partial inspection

Result: **CONSUMED; READ-ONLY ROOT CAUSE PROVEN.** Never flash or retry.

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

The sole cycle reported: partial regular, uid/gid 0, mode 0644, one link,
size 0, allocated blocks 0; final absent; `rog5` metadata `0:0:700:3` and
`images` metadata `0:0:700:2`. No phone write occurred. The exact successful
record was followed by the known SSH disconnect-timeout line; the parser now
accepts only that one exact trailing transport artifact. Fastboot fallback and
host cleanup passed.

Root cause: emergency reboot plus ext4 recovery preserved the created inode
but rolled its data back to an empty regular file. Benchmark policy wrongly
required every present partial to be nonempty. A fail-first fixture now allows
that exact safe state while retaining path, type, owner, mode, links, and the
fixed logical-size ceiling.
