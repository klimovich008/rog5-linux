# Generation 37 QMP-UFS clock-provider-stage discriminator

Status: **offline checkpoint; unbooted; one RAM-only use only; never flash**.

Generation 37 uses the exact Generation 36 kernel Image and UFS-enabled DTB.
Its patched QMP-UFS module binds only the exact SM8350 compatible, performs the
already-cleared clock/regulator and DT/MMIO setup, registers the PHY clock
provider with `qmp_ufs_register_clocks`, emits one marker, and returns before
`devm_phy_create`, PHY private-data setup, or OF PHY provider registration. UFS
core, platform, and host modules remain absent, so the candidate cannot
enumerate or access storage.

The patch applies cleanly to retained Generation 36 source commit
`08aa45cd0e4d230ce2f320daf9a6796a01746d8d`. The retained patched source is
commit `a2947ed3ea474b61d2f4affd6488d149acfb1fa3`, tree
`562b367ebcf8ddcb32a89930f549609d8241daf7`, and is clean. Two independent
module compilations and final links are byte-identical. Every undefined symbol
is present in the exact retained Generation 32 `Module.symvers`, and the
unchanged Kbuild module metadata and module-common objects remain byte-identical
to that accepted build.

| Artifact | SHA-256 |
|---|---|
| reused kernel Image | `53d42da77b65a37149bd269c5d71d7855a7edb51748cb2da478bff5cb5f95203` |
| UFS-enabled DTB | `72c0db7cb2f54055240c420bbcd4fece6f497e1e648ce7081141781bc78f48c2` |
| diagnostic QMP-UFS module | `763d3f944744967811bf4e8b259cd16ead1f08b73754913f693eb5ff247b2460` |
| initramfs | `59604ecb521d008b5fbec41bd375dfdd7b4965868bdf24f9925433524c68f78b` |
| signed manifest | `dd832a7655e4a1130b69f07188907f80853004f5e05c150e827a0aee4e1c6447` |
| manifest signature | `ca1a9b486661521c47ca693b8b7e97b54f807636a37c3d2ea81679af6789a7e4` |
| Generation 37 AVB wrapper | `bf223a9de39e0822493fa6769fcc4db94eada697eb1b12ae1a1a5197e88e0f8b` |
| AVB generation record | `731240f0e7c8da3b0c45fb84d4645de87166b92ab65158030011077b09ccce5b` |

Module twins built in 1.512 and 1.513 seconds; initramfs twins built in 1.120
and 1.133 seconds; signed bundle twins built in 0.244 and 0.190 seconds. All
twins are byte-identical. The AVB issuance took 1.847 seconds and retained raw
recovery payload
`90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6`
exactly. Success clears clock-provider registration; failure at the Generation
33 timing isolates that newly added boundary. The known-good Alpine fallback is
unchanged.
