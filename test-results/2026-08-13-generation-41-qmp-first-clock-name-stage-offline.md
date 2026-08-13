# Generation 41 QMP-UFS first-symbol-clock-name discriminator

Status: **offline checkpoint; unbooted; one RAM-only use only; never flash**.

Generation 40 proved that clock-data allocation and metadata initialization
preserve target NCM. Generation 41 repeats that work, constructs the first
dynamic `rx_symbol_0` name using `dev_name()` and `snprintf()`, then returns
before `devm_clk_hw_register_fixed_rate()`, the remaining clocks, OF
clock-provider publication, PHY creation, or OF PHY-provider registration.
UFS core, platform, and host modules remain absent, so this candidate cannot
enumerate or access phone storage.

Independent review exposed that the inherited DTB marked the exact
`0x9b800000 + 0x400000` RMTFS range disabled while the target command line gave
the same valid RAM to ramoops. Linux skips disabled reserved-memory children,
so ramoops could alias allocator-owned pages. The existing fail-closed DTB
transform changes only that node's status to `okay`. `CONFIG_QCOM_RMTFS_MEM=m`
and the module is absent from the initramfs, so this reserves the range without
activating RMTFS. The initial signed v20 bundle is superseded offline; only the
r2 bundle with the reserved range is admitted.

The patch applies to retained Generation 40 source commit
`858db0ad4f9a3b9b6532443e3f8f9509203a920c`. The new clean source checkpoint
is commit `d327b6f0251129e0c80f32fe9309f8278e800db7`, tree
`00a7ab806aed07ea869757e7eefa7a6e26ac67fd`. Both isolated module compilations
produced object SHA-256
`7650c45063dfc3dbf572ac3e8274db266e10d0444bb8958534b0673ac3b57f12`;
deterministic final links produced byte-identical 473,040-byte modules with
SHA-256
`a1ff62cf31315648931b4412212e1eb3bf89e270ca3ae01d4efa0a265ad35f13`.
All 37 undefined symbols exist in the retained accepted `Module.symvers`; the
module release is `7.1.4-gcfd385a1c754`.

| Artifact | SHA-256 |
|---|---|
| reused kernel Image | `53d42da77b65a37149bd269c5d71d7855a7edb51748cb2da478bff5cb5f95203` |
| UFS-enabled, RMTFS-reserved DTB | `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2` |
| diagnostic QMP-UFS module | `a1ff62cf31315648931b4412212e1eb3bf89e270ca3ae01d4efa0a265ad35f13` |
| initramfs | `ce6c3839e6a2a885549dfe6f52207f6aa6b136e2ad655e0f85d775ad1cf2d934` |
| signed manifest | `86c8262c080b0b7254a9175bc8487f464db7a4304ba7879b450a74504a23f713` |
| manifest signature | `ce306594f02fd08bddb834e0ff293abe270e29f157ee98c606f49dc186465f3f` |
| Generation 41 AVB wrapper | `6f2a17b3d282a96fb491fc371b29f2fefc4ab274ffefa7904d97bd6dcacc98d4` |
| AVB generation record | `e3ec64ce3a7df591fb9629dcc16e5250e5fa91ab00533a07d883b10cf1cd2444` |

The normalized module twins each compiled in 7.012 seconds. Initramfs twins
took 1.122 and 1.119 seconds, the corrected DTB twins took 0.103 seconds
combined, signed r2 bundle twins took 2.872 and 2.105 seconds, and AVB issuance
took 1.958 seconds. All released twins are byte-identical.
The complete repository Linux CI tier passed in 361.259 seconds.
The raw recovery payload remains exact SHA-256
`90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6`.
Generation 40 is consumed and revoked; the known-good Alpine fallback is
unchanged.
