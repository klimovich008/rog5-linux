# Generation 28 UFS-enabled DTB control

Status: **offline pass, one RAM-only use, never flash**.

Generation 27 proved stable target NCM with the exact Generation 20 Image and
DTB. Generation 28 changes only the DTB half of that target pair: it uses the
Generation 25 UFS-enabled DTB with the same live-proven Generation 20 Image
and the same persistent initramfs.

The initramfs expects release `7.1.4-gcfd385a1c754`, while the target Image
reports `7.1.4-g7a5cef0db479`. USB setup therefore remains observable before a
deliberate release-identity rollback, and userspace cannot reach UFS. Target
NCM success exonerates the persistent DTB and isolates the UFS Image/config
lineage; failure before NCM implicates the DTB or its enabled hardware nodes.

Exact identities:

- target Image: `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf`;
- target DTB: `72c0db7cb2f54055240c420bbcd4fece6f497e1e648ce7081141781bc78f48c2`;
- target initramfs: `908f18f752962fae798249060aa8ee4c45673d8795571fbb8883ac4ed8d9e19e`;
- signed manifest: `c4cef9e256708d219c7c77f792dbff43336c5d446d0721048ff471b7c05969ee`;
- signature: `e6ef8730d60090ed44c596cdf9e7b7c3ba0c778284cbcda0784cbc0751bfd564`;
- unchanged raw recovery wrapper: `90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6`;
- Generation 28 AVB wrapper: `5047cfae9fbbeb0b76b59175792fc7e671e5ac94625bb81304d5422dd85024ee`;
- AVB generation record: `efd2a3b079e69e9af44cb47750e852088c2e07cb4a3790d573de09887248f76f`.

Both signed bundle builds are byte-identical. AVB issuance completed in
2.110 seconds with salt
`fd3be4f55b1fd7910206ab73f999ca3c273992147e2ad2a819d805b198724ece`
and digest
`f2147c99989c453b0f7c09b4b6f18531536908773bf7532aef2573a78234c32c`.
No phone was contacted during construction.
