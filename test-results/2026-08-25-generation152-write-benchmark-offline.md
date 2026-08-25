# Generation 152 logical-size-bounded UFS benchmark

Result: **CONSUMED; PARTIAL METADATA STILL UNCLASSIFIED.** Never flash or retry.

Generation 151 disproved the transient snapshot as a stable partial-size
identity. Generation 152 accepts only absence or one root-owned regular
mode-0600/0644 partial no larger than the original fixed 16 GiB logical image,
then runs the unchanged 32 MiB direct-first and 32 MiB buffered benchmark.

Target initramfs twins built in 6.444 seconds and match at SHA-256
`a85ee290d37326bf900d20c0d813240bc78ac258c7c1e1e937953fbc9dbe63c0`,
size 23,805,025 bytes. Kernel, DTB, modules, benchmark scope, cleanup, and
sync-independent fallback are unchanged.

Signed bundle manifest SHA-256:
`65203683173ceacfa412d5dad54662bf46a7aa823016e2129c9aea869f3cf0c6`.
Generation-152 RAM-only AVB SHA-256:
`c51667b372cc5a731adae10917f69ea33faa0bf4d76f0aa05db89cb248ca5489`.

The sole cycle again returned exact `partial-identity` before benchmark
creation or writes, even with the full logical-size ceiling. Size is therefore
not the remaining discriminator. Per the systematic-debugging rule, benchmark
successors stop until a read-only probe reports exact type, owner, mode, link
count, size, allocated blocks, final state, and parent-directory metadata.
