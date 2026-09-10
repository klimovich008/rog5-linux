# Generation 38 QMP-UFS fixed-rate-symbol-clocks discriminator

Status: **offline checkpoint subsequently consumed; target NCM disappeared;
never retry or flash**.

Generation 37 localized target NCM loss to `qmp_ufs_register_clocks()`. The
Generation 38 diagnostic branch executes the function through allocation and
all three `devm_clk_hw_register_fixed_rate()` calls, then returns before
`of_clk_add_hw_provider()`, `devm_add_action_or_reset()`, PHY creation, or OF
PHY-provider registration. UFS core, platform, and host modules remain absent,
so the candidate cannot enumerate or access phone storage.

The patch applies to retained Generation 37 source commit
`a2947ed3ea474b61d2f4affd6488d149acfb1fa3`. The new clean source checkpoint is
commit `e81c21141c8752b9722fc3ebf2ae09f7f55dd856`, tree
`75aea2a02701f2a306cc93dfaf9bbeff837bd0ae`, and is clean. Both isolated module
compilations produced object SHA-256
`76fd6e6f26835d3f32b98f7b65f46be1453dd2038374eafea796e1ab2869f906`;
the deterministic final links produced byte-identical 474,768-byte modules
with SHA-256
`2390bccdd0c371675003ae085b7ec2763d28733c5b90929a55bbb6a8d03a99d8`.
All 37 undefined symbols exist in the retained accepted `Module.symvers`, and
the module has exact release `7.1.4-gcfd385a1c754`, name
`phy_qcom_qmp_ufs`, and no dependencies.

| Artifact | SHA-256 |
|---|---|
| reused kernel Image | `53d42da77b65a37149bd269c5d71d7855a7edb51748cb2da478bff5cb5f95203` |
| UFS-enabled DTB | `72c0db7cb2f54055240c420bbcd4fece6f497e1e648ce7081141781bc78f48c2` |
| diagnostic QMP-UFS module | `2390bccdd0c371675003ae085b7ec2763d28733c5b90929a55bbb6a8d03a99d8` |
| initramfs | `d90cfa9118cc553d2798833a588efd5291f5179187a6820a092920fae541e2de` |
| signed manifest | `abd615f73576c798505464c07a3816da470eee5eeb9c26bc2f8f201f85b44ba4` |
| manifest signature | `82bd71546984d4bfe3aff5040a3f06ea7aec661abafc6bf43da72ec389dfa790` |
| Generation 38 AVB wrapper | `e5fe136dc95e7380b144d2f6bd64480e35464ae4523b17712aa695807e1b7f18` |
| AVB generation record | `a769006b38c7234f9f6a55129e8523a0396261dffb9c70b388852a1018b6990d` |

The isolated module builds took 25.871 and 25.857 seconds after complete Kbuild
dependency synchronization; deterministic final links took 0.183 and 0.149
seconds. Initramfs twins each took 0.989 seconds, signed bundle twins took
0.111 and 0.150 seconds, and AVB issuance took 1.715 seconds. All released
twins are byte-identical. The raw recovery payload remains exact SHA-256
`90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6`.
Generation 37 remains consumed and revoked; the known-good Alpine fallback is
unchanged.

The final repository `ci` checkpoint passed in approximately 355 seconds.

The sole live cycle subsequently lost target NCM 11.276 seconds after product
enumeration, then returned to exact Alpine. Because this branch never reached
OF clock-provider publication, the result narrows the failure to allocation or
one of the three fixed-rate symbol-clock registrations. See the
[live result](2026-08-12-generation-38-qmp-fixed-clocks-stage-live.md).
