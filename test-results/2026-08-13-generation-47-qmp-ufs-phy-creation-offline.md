# Generation 47 QMP-UFS PHY-creation offline checkpoint

Status: **unbooted RAM-only candidate; no phone-storage access; never flash**.

Generation 46 proved OF clock-provider publication and paired cleanup with
stable NCM. Generation 47 changes only the next probe boundary: it executes
`devm_phy_create()` and returns before `phy_set_drvdata()` or
`devm_of_phy_provider_register()`. UFS core, platform, and host modules remain
outside the target load path, so the candidate cannot enumerate or access
storage.

Exact clean-twin result:

- source commit: `3a0a28dcbbc377a4160eaf0bbe80122931c34b05`
- source tree: `db4db5e93e75671552046d1e3cdbc20402a729fc`
- release: `7.1.4-g3a0a28dcbbc3`
- config SHA-256: `b959774825e2bca7c634e55cd00e838121fde8d95fd214ffeead732ce92e35e6`
- Image SHA-256: `fcb89adff915556a188db7b6965fcd474c5a09bb242a5c831b5e07b2179cc809`
- QMP-UFS module SHA-256: `1a4bc0f657caba8f344c5592c721fd9c803f32af5f3cca8466d3cc5f3e494e36`
- target initramfs SHA-256: `e5d9bc6440b48508fa9639a6e84b5bf1e22a8bde5c25bd8736b4a20a47f2713a`
- DTB SHA-256: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`
- signed manifest SHA-256: `7f05c55c553e057b418f2adc23f284a907dd9ca693d532228372ad9dfe3e57c4`
- manifest signature SHA-256: `0038f0db0c224e689e75ff65b499b97393cabc05bf369c6e4f18e1f1761db57f`
- Generation 47 AVB SHA-256: `3443002bbb82c1880d347d891c469c138b1ef10f3c2f26470da53bf89128aeaf`
- AVB salt: `36d070b134f6a9dddebadda90ee1029a8ead52dfec3378b3e4142175db616b0e`
- AVB digest: `fcae27ac814be6f998ebf20c5c4c512071b81f33a0ce38f221bfd14c04df7455`

Clean twin A took 106.338 seconds and clean twin B took 90.549 seconds with
the retained compiler cache. Initramfs twins took 1.130 and 1.142 seconds,
bundle twins took 0.226 and 0.296 seconds, and AVB generation took 1.794
seconds. All released twins are byte-identical. One preliminary invocation
failed after 5.166 seconds because its Kconfig temporary directory was
read-only; that incomplete tree is preserved separately and is not a release
input.

The PHY-boundary test, predecessor-provider test, generic one-use consumer,
lifecycle runner, stable live gate, admission verifier, and exact current
artifact profile pass offline. The coherent repository CI tier passed in
442.804 seconds. This checkpoint does not authorize any persistent-storage
operation; publication and one exact RAM-only hardware cycle remain separate
gates.
