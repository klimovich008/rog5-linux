# Generation 26 RMTFS-reserved UFS discriminator

Date: 2026-08-12

Generation 25 completed its sole RAM-only COMMIT but exposed no target USB;
exact Alpine returned after 25.038 seconds. Generation 20 is a decisive
counterexample to treating disabled RMTFS plus ramoops as a sufficient general
cause: that network-root target reached Arch and SSH with the same memory
model. Generation 26 therefore tests a coherent UFS-specific memory-ownership
hypothesis without claiming it as root cause.

The target Image and persistent initramfs remain byte-identical to Generation
25. A fail-closed DT transformer changes exactly the disabled
`qcom,rmtfs-mem` node at `0x9b800000 + 0x400000` to `status = "okay"`. The
verified persistent-root command line omits ramoops; diagnostic and network-
root profiles retain it. Phone storage remains read-only and no flash or
partition operation exists in the live runner.

Exact identities:

- target Image: `33366ffb30e453e191538799850ac38857c445c7f34f74d1a1c655f584c07cfb`
- target DTB: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`
- target initramfs: `908f18f752962fae798249060aa8ee4c45673d8795571fbb8883ac4ed8d9e19e`
- signed manifest: `1d64161dd213ced57b6761086629351ba116b30f894aa36afba9480873b4e3ab`
- stable-recovery verifier: `e5e59a5647a9c283c125e3362a714e3a2657411fb3e5c478ebaef9379a90c98e`
- stable-recovery initramfs: `3495070782746936065a314337732028d41bed29f85e888cfaf730828557bb5d`
- wrapper config: `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f`
- wrapper Image: `71b48a03e6e12e1ae2c21470ea80e1308ca5deba371dd810c00c6a936d309455`
- raw wrapper: `90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6`
- Generation-26 AVB: `1a0c13d5af49820932666a3801a577de92d579ede265ef83f4b1e8f17c56d07e`
- AVB generation record: `be2ee72b733ad00447c884c5308dd1c06e4bbf35cea93cca513932a7d1b50d6c`

Two clean recovery-wrapper builds ran from 11:23:57 to 11:59:15 CEST
(approximately 35 minutes 18 seconds) and reproduced byte-identical config,
Image, initramfs, raw boot, and generation-zero AVB artifacts. Issuance then
created a byte-distinct, twin-reproducible Generation-26 AVB while retaining
the exact raw wrapper.

Focused verification passed the native verifier profile/hostile matrix (26
tests), signed bundle packager (8), exact DT transform, generic claim consumer
(14), persistent lifecycle (8), stable-recovery live gate, current exact
artifact preflight, and the retryable NetworkManager classification-gap
regression. The final local repository CI checkpoint passed in 5 minutes
50.226 seconds; exact-head CI remains the publication gate before the sole
RAM-only physical cycle.

Generation 26 is one-use and never flashable. Passing offline checks does not
establish UFS success; only the live read-only inventory can do that.
