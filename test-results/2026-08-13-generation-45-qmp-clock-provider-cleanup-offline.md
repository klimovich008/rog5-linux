# Generation 45 QMP-UFS clock-provider/cleanup offline checkpoint

Status: **consumed before mainline execution; no phone-storage access; never retry or flash**.

Generation 44 proved all three fixed-rate symbol-clock registrations with an
exact target-originated post-`insmod` record and stable NCM. Generation 45
changes only the next QMP-UFS boundary: it publishes the OF clock provider,
requires successful registration of the paired devm cleanup action, and then
returns before `devm_phy_create()`, `phy_set_drvdata()`, or OF PHY-provider
registration. UFS core, platform, and host modules remain outside the load
path, so this candidate cannot enumerate or access storage.

Exact clean-twin result:

- source commit: `07858678c59cc4acdb4e2949100225b2320997b9`
- source tree: `5c09c9adb9b6e7f8875e8be887901bbdf9452fdf`
- release: `7.1.4-g07858678c59c`
- config SHA-256: `b959774825e2bca7c634e55cd00e838121fde8d95fd214ffeead732ce92e35e6`
- Image SHA-256: `719f5ab2ec89ee01df9d3cd8a29a4e56b6e5cc0239a4266ba1b271fb66dd108d`
- Image.gz SHA-256: `5eaf286ba7e0b5e4b4114a7919f5c6d9572378aad1016e4f341275fe59d0b3d5`
- QMP-UFS module SHA-256: `3b51e861acb1fc3e555c4c0af1c48ee635aeb7f6ebd91d76e6f0a0b3c6d1367e`
- UFS core module SHA-256: `fded65c7434d5ee7070e5b4b7d2e9d6b681a91b86bce95a02fb4b65db7f52675`
- UFS platform module SHA-256: `615d4c3f5f558a24e45804546192acbc138afed39ca802479f9c9bc140d1c686`
- UFS Qualcomm module SHA-256: `36c0ce6cc37447c101f221ee67461444177cadf96ec92eadf42c6aa8a7fb6c14`
- initramfs SHA-256: `6c06511dbfa69c634a4ce7fa7589176bc8ee8d9c89e2256e8ef2a92341f6d1a9`
- signed manifest SHA-256: `1bc07a9e0b0acf874f542a84f1d7d8c12505504790bc4da433eb22989b76839b`
- manifest signature SHA-256: `489422dad416dcced829b081127647671dbe3a993f194ce580d436134557a51a`
- Generation 45 recovery SHA-256: `06fdc98669a72d02795c4fdeabb73875832a673b6d7d8190502ef5841682425f`
- AVB salt: `52c215cb5e8a379cccf6a4ce04245302bb40edcb791efc768d84f624fd4e502b`
- AVB digest: `5108fb7ddaa3162facaf071f13776c2a2f2b60aeaa0b66bc08b7d7f360e74a87`

Clean twin A took 99.846 seconds and clean twin B took 92.331 seconds with
the retained compiler cache; exact verification took 1.003 seconds. The cache
reported 86.10% hits. Initramfs twins took 1.134 and 1.130 seconds. Bundle
twins took 0.191 and 0.177 seconds. AVB issuance took 1.793 seconds. All
released twins are byte-identical, and the raw recovery wrapper remains exact
SHA-256 `90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6`.

Focused tests, full local CI, and exact-head GitHub CI passed before the sole
temporary boot; those offline results did not establish target execution.

The sole live cycle later failed recovery PREPARE with `FETCH_CONNECT` before
bundle transfer or COMMIT. The target kernel did not execute, and this
checkpoint therefore contains no evidence about clock-provider publication.
Generation 45 remains consumed and non-retryable; Generation 46 carries the
same target payload behind the corrected bounded recovery transport.
