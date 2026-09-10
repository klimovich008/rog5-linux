# Generation 27 exact Generation 20 USB control

Status: **offline pass, one RAM-only use, never flash**.

Generation 27 is the minimum discriminator after five approximately
25-second persistent-root fallbacks without target USB. It reuses:

- Generation 20 Image `349c41d660a7eaa695098ce3734d8fea584447fd34849503f9a855269b425daf`;
- Generation 20 DTB `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`;
- Generation 26 persistent initramfs `908f18f752962fae798249060aa8ee4c45673d8795571fbb8883ac4ed8d9e19e`.

Generation 20 reached target reporter at 2.680 seconds and NCM carrier at
3.680 seconds on this phone. The reused persistent initramfs expects release
`7.1.4-gcfd385a1c754`, while this exact kernel reports
`7.1.4-g7a5cef0db479`. USB setup runs first, so the expected live sequence is
target NCM enumeration followed by the fixed 25-second release-identity
rollback. UFS discovery and all userspace phone-storage access remain after
that unreachable gate.

Twin signed bundles are byte-identical. The signed manifest is
`33715e0c566a5fc7e771f6b89ca81fd1fe0bb6325b926995a0ba5c5f81a44a5b`.
The Generation 27 AVB wrapper is
`765e45af3d4ced2c87e15adf5ba6141ce5824d75334afc2ddedb4a28db18d88f`;
its raw recovery payload is unchanged from Generation 26.
