# Generation 48 QMP-UFS OF PHY-provider offline checkpoint

Status: **unbooted RAM-only candidate; no phone-storage access; never flash**.

Generation 47 proved QMP-UFS PHY creation with stable NCM. Generation 48
changes only the next probe boundary: it executes `phy_set_drvdata()`,
publishes the provider with `devm_of_phy_provider_register()`, and returns
before any UFS consumer probes. UFS core, platform, and host modules remain
outside the target load path, so the candidate cannot enumerate or access
storage.

Exact clean-twin result:

- source commit: `ae717d919f87b47ea9ed2173ea96660186b62a66`
- source tree: `939729426dcfa3bd72c75d81c0a675c6f0a193da`
- release: `7.1.4-gae717d919f87`
- config SHA-256: `b959774825e2bca7c634e55cd00e838121fde8d95fd214ffeead732ce92e35e6`
- Image SHA-256: `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`
- QMP-UFS module SHA-256: `73fef6fa7620bd4f9ac6df658521904ffeff2e19b02bc0258b77c410b7051ddb`
- target initramfs SHA-256: `b0c04138fba18c0105bcc0e9db487ef9691fdb2568a5947845e9994a90aae731`
- DTB SHA-256: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`
- signed manifest SHA-256: `734bd5af4c2f7db1af87e08d0a6c1de0e6d0b013be4901110b892fd065e7656c`
- manifest signature SHA-256: `c9be68d2ca3a5c827747ccba092e678602536b7612026313fc68c43005351e39`
- Generation 48 AVB SHA-256: `2e0f347a48ac9cd11c3e73ed795b4a42a5f920ebe98a7177bfedba6491be52b8`
- AVB salt: `8f47880b469d9bfbdfadaecd3451b6aa91eeee6e6a3cbf201556153041efbc5b`
- AVB digest: `bd72ee6a57a57eed2120541a3cd4c9e38a33a8b89745f0415c7c29ae4e653029`

Clean twin A took 109.914 seconds and clean twin B took approximately 76.9
seconds with the retained compiler cache. Initramfs twins took 2.207 seconds
combined, bundle twins took 0.293 seconds combined, and AVB generation took
1.862 seconds. All released twins are byte-identical. One preliminary build
failed after about 5.1 seconds because the container working directory was
read-only; its incomplete output is preserved separately and was not used.
A later timing-wrapper invocation failed immediately because `/usr/bin/time`
is absent; it did not start a build or modify an output.

The provider-boundary test, clean-twin kernel and initramfs checks, generic
one-use consumer, lifecycle runner, stable live gate, admission verifier, and
exact current artifact profile pass offline. This checkpoint does not
authorize any persistent-storage operation; publication and one exact RAM-only
hardware cycle remain separate gates.
