# Generation 36 QMP-UFS DT/MMIO-stage discriminator

Status: **PASS; consumed; never retry or flash**.

Generation 36 uses the exact Generation 35 kernel Image and UFS-enabled DTB.
Its patched QMP-UFS module binds only the exact SM8350 compatible, performs the
already-cleared clock/regulator setup, selects the driver's reviewed DT binding,
maps the PHY MMIO resources with `qmp_ufs_parse_dt`, emits one marker, and
returns before clock-provider registration, PHY creation, or provider
registration. UFS core, platform, and host modules remain absent, so the
candidate cannot enumerate or access storage.

The retained patched source is commit
`08aa45cd0e4d230ce2f320daf9a6796a01746d8d`, tree
`ae9e3ab0f8d30a1714e20cad6e527ee20325bae8`, and is clean. Two independent
module compilations and final links are byte-identical. Every undefined symbol
is present in the exact retained Generation 32 `Module.symvers`, and the
unchanged Kbuild module metadata and module-common objects remain byte-identical
to that accepted build.

| Artifact | SHA-256 |
|---|---|
| reused kernel Image | `53d42da77b65a37149bd269c5d71d7855a7edb51748cb2da478bff5cb5f95203` |
| UFS-enabled DTB | `72c0db7cb2f54055240c420bbcd4fece6f497e1e648ce7081141781bc78f48c2` |
| diagnostic QMP-UFS module | `bc518210994f03972f13042f2ccbbc5cc568166805a9e259ada6c71b984ca5ca` |
| initramfs | `1ae0d15b0675db51b32f620f6f7b69af01d4a27a8071bdd9c246b6e3acca0b6c` |
| signed manifest | `d81ff27520337a91e556018109173d4d14d9c38d0846639f2d056150fa39886d` |
| manifest signature | `1393633670517f1849c8ece82432dc2fc8841a85e19f8523aa61feb0339fcb22` |
| Generation 36 AVB wrapper | `d5d5cdeb343b573527db94bc8d5fa909a267c0f87eec690f7b821d16438c483a` |
| AVB generation record | `af33af01fa0c1429b49ab05925bf9fffa7e71acc723d922b26c67ce34ba097f6` |

Module twins built in 35.367 and 3.377 seconds; initramfs twins built in 1.114
and 1.123 seconds; signed bundle twins built in 0.231 and 0.235 seconds. All
twins are byte-identical. The AVB issuance took 1.774 seconds and retained raw
recovery payload
`90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6`
exactly. Success clears DT binding selection and MMIO resource mapping; failure
at the Generation 33 timing isolates that newly added boundary. The known-good
Alpine fallback is unchanged.

The sole live cycle reached stable target NCM in 58.860 seconds, preserved the
same anchored interface for the full 12.294-second post-module control window,
and returned to exact Alpine. See the
[live result](2026-08-12-generation-36-qmp-mmio-stage-live.md).
