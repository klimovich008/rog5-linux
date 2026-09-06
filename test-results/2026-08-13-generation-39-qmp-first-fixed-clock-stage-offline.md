# Generation 39 QMP-UFS first-fixed-clock discriminator

Status: **offline checkpoint subsequently consumed; target NCM disappeared;
never retry or flash**.

Generation 38 localized target NCM loss to allocation or one of three
fixed-rate symbol-clock registrations. Generation 39 performs the allocation
and registers only `rx_symbol_0`, then returns before `tx_symbol_0`,
`rx_symbol_1`, OF clock-provider publication, cleanup-action registration, PHY
creation, or OF PHY-provider registration. UFS core, platform, and host
modules remain absent, so this candidate cannot enumerate or access phone
storage.

The patch applies to retained Generation 38 source commit
`e81c21141c8752b9722fc3ebf2ae09f7f55dd856`. The new clean source checkpoint
is commit `e09bdc38dccd64c04a9143accb4b220b5c06fd3b`, tree
`df2d06bab7891fa94994ed2b6dc0b827a40f975e`, and is clean. Both isolated
module compilations produced object SHA-256
`55ae0d189860f92789e6c13004d2d0bb4f1db1d1ffbc4755ad3937b0a4d6b75a`;
deterministic final links produced byte-identical 474,768-byte modules with
SHA-256
`0d710255c85d6a0c25663933d0255c40b960b5050068323f0ea2171681218e7d`.
All 37 undefined symbols exist in the retained accepted `Module.symvers`; the
module release is `7.1.4-gcfd385a1c754`, its name is `phy_qcom_qmp_ufs`, and it
has no dependencies.

| Artifact | SHA-256 |
|---|---|
| reused kernel Image | `53d42da77b65a37149bd269c5d71d7855a7edb51748cb2da478bff5cb5f95203` |
| UFS-enabled DTB | `72c0db7cb2f54055240c420bbcd4fece6f497e1e648ce7081141781bc78f48c2` |
| diagnostic QMP-UFS module | `0d710255c85d6a0c25663933d0255c40b960b5050068323f0ea2171681218e7d` |
| initramfs | `8868b5f858ec8217eeb5c0383482ce6c058bd1dfbff523d04abdf27de34f5628` |
| signed manifest | `f047d1c0ca676afa62a8a4f30d7b68306622b2eee5fc8dfb8b94e9d71450d3c5` |
| manifest signature | `946f61ef32e993fe95a79db4b4a8d2cf5c71155692d25651824255560a895629` |
| Generation 39 AVB wrapper | `fbaee0cd105ba7d02e76ef5f1b13a4cb43bc0c4e03e14f0c9a0e9406c5513b7a` |
| AVB generation record | `eed09e1837725e26416ff38365bcc5260bdc3fa2c4016cbdbfcfc3decdd41018` |

The isolated module builds took 17.669 and 17.687 seconds; deterministic final
links took 0.277 and 0.268 seconds. Initramfs twins took 1.103 and 1.111
seconds, signed bundle twins took 0.186 and 0.222 seconds, and AVB issuance
took 1.873 seconds. All released twins are byte-identical. The raw recovery
payload remains exact SHA-256
`90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6`.
Generation 38 is consumed and revoked; the known-good Alpine fallback is
unchanged.

The final repository `ci` checkpoint passed in 360 seconds, including the
bounded successful-controller/late-bundle-cleanup regression and its stalled
cleanup refusal.

The sole live cycle subsequently lost target NCM 11.273 seconds after product
enumeration, then returned to exact Alpine. This narrows the failure to
clock-data allocation/metadata setup or the first fixed-rate clock
registration. See the
[live result](2026-08-13-generation-39-qmp-first-fixed-clock-stage-live.md).
