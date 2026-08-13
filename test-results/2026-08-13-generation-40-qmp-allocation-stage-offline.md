# Generation 40 QMP-UFS allocation-stage discriminator

Status: **offline checkpoint subsequently consumed; allocation stage passed;
never retry or flash**.

Generation 39 localized target NCM loss to clock-data allocation/metadata
setup or the first fixed-rate symbol-clock registration. Generation 40
allocates and initializes the three-entry clock-data table, then returns before
naming or registering `rx_symbol_0`, the remaining clocks, OF clock-provider
publication, PHY creation, or OF PHY-provider registration. UFS core, platform,
and host modules remain absent, so this candidate cannot enumerate or access
phone storage.

The patch applies to retained Generation 39 source commit
`e09bdc38dccd64c04a9143accb4b220b5c06fd3b`. The new clean source checkpoint
is commit `858db0ad4f9a3b9b6532443e3f8f9509203a920c`, tree
`2af45fcef2b902db592001cc2203ef42d6210147`, and is clean. Both isolated
module compilations produced object SHA-256
`b55b755daf512ec4ef11c54a3654703b751f69ad65eb032462caa3dd250a3672`;
deterministic final links produced byte-identical modules with SHA-256
`14d0be7cfe9ae1a66e70833ad352d92091da9852a415bc90ed055ad617a3b34f`.
All 37 undefined symbols exist in the retained accepted `Module.symvers`; the
module release is `7.1.4-gcfd385a1c754`, its name is `phy_qcom_qmp_ufs`, and it
has no dependencies.

| Artifact | SHA-256 |
|---|---|
| reused kernel Image | `53d42da77b65a37149bd269c5d71d7855a7edb51748cb2da478bff5cb5f95203` |
| UFS-enabled DTB | `72c0db7cb2f54055240c420bbcd4fece6f497e1e648ce7081141781bc78f48c2` |
| diagnostic QMP-UFS module | `14d0be7cfe9ae1a66e70833ad352d92091da9852a415bc90ed055ad617a3b34f` |
| initramfs | `857e91dd8ae55c9aa0ed8999754c832f85e36615699dbe7faaee87afa34d1265` |
| signed manifest | `82f38e524cc9f8c65bd5ae225bbb4d0acf4a7ef20021d61af313880c98731835` |
| manifest signature | `e0761a599ff58f2835976d0e41873ce95829502d875a1e80ceffa0cbb59358e7` |
| Generation 40 AVB wrapper | `39051935dda192ac24983a91b0508eaa6f74788a77ce14a12f570ea2cad40280` |
| AVB generation record | `40000ccf9ad9e84736c3516eaff8cb2056da9568012fa355cb9256674cd0b382` |

The isolated module builds took 25.143 and 24.865 seconds; deterministic final
links took 0.366 and 0.404 seconds. Initramfs twins took 1.111 and 1.155
seconds, signed bundle twins took 0.213 and 0.219 seconds, and AVB issuance
took 1.857 seconds. All released twins are byte-identical. The raw recovery
payload remains exact SHA-256
`90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6`.
Generation 39 is consumed and revoked; the known-good Alpine fallback is
unchanged.

Focused tests passed for the allocation-stage patch, exact claim consumer,
executor identity contract, retention admission, live-cycle runner, current
profile, stable-recovery gate, compatibility oracle, and source/DT contract.
The complete local `scripts/host/test-repository-linux.sh ci` checkpoint passed
in 398.091 seconds.

The sole live cycle subsequently reached stable target NCM in 59.680 seconds,
preserved it for the complete 12.173-second control window, and returned to
exact Alpine. This clears allocation/metadata setup and leaves dynamic first
clock-name construction or the first fixed-rate clock registration as the
remaining boundary. See the
[live result](2026-08-13-generation-40-qmp-allocation-stage-live.md).
