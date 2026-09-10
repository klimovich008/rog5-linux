# Generation 32 deferred QMP-UFS PHY discriminator

Status: **offline checkpoint passed; subsequently consumed; never retry or flash**.

Generation 31 deferred UFS core, platform glue, and the Qualcomm host driver,
but still produced no target USB before exact Alpine returned. Its kernel left
`CONFIG_PHY_QCOM_QMP_UFS=y`. The retained DTB enables exactly
`/soc@0/phy@1d87000` as `qcom,sm8350-qmp-ufs-phy`, and Linux registers that
driver with `module_platform_driver()`, so built-in mode can probe before
`/init` establishes USB.

Generation 32 changes only `CONFIG_PHY_QCOM_QMP_UFS=y` to `m`. The initramfs
first establishes NCM and its bounded host-observation rendezvous, then loads
the exact sealed chain in dependency order: `phy-qcom-qmp-ufs.ko`,
`ufshcd-core.ko`, `ufshcd-pltfrm.ko`, and `ufs-qcom.ko`. No storage lookup,
mount, or filesystem operation precedes successful module insertion.

## Fail-first and focused checks

The pre-change storage-resolution test failed because the QMP-UFS module was
absent from the fixed loader. The pre-change build verifier also failed on a
deferred build because it delegated to the built-in-UFS metadata contract.
The correction adds independent config, source/tree, compressed-image,
four-module inventory, module name/dependency/release, compiled read-only guard,
and metadata-hash checks. Extra files and symlinks fail closed.

Focused results:

- eight storage/UDC/rendezvous/load-order tests: 0.82 seconds;
- deterministic real-module initramfs and hostile inventory test: 5.82 seconds;
- generic exact-claim consumer: 14 tests in 0.041 seconds;
- live runner: eight tests in 0.003 seconds;
- current exact artifact/profile preflight: pass;
- stable recovery gate: pass;
- retention admission: 27 tests in 3.151 seconds;
- core compatibility and source/DT contracts: 39 plus 77 tests passed.

## Clean twins

Two empty-output builds ran in parallel in the pinned historical Clang 18.1.3
container. Both completed in exactly 2,438 seconds. Their source commit is
`cfd385a1c754684dd28b63a4559e04baa5e902b1` and source tree is
`d2f03d2055227b8b72ab41be949847a066924c5a`.

| Artifact | SHA-256 |
|---|---|
| config | `b959774825e2bca7c634e55cd00e838121fde8d95fd214ffeead732ce92e35e6` |
| Image | `53d42da77b65a37149bd269c5d71d7855a7edb51748cb2da478bff5cb5f95203` |
| Image.gz | `56eafd21c8331c2168156b0d25307bb58ea30e8ab66827a06b41d4c0bca51c9f` |
| phy-qcom-qmp-ufs.ko | `5c397174c33a54187b6edabbed028b651eb974b0894e9dadf263e69257263bb1` |
| ufshcd-core.ko | `9adae539182c97f0afb571493eb365013062a388ccc535953db6907920898122` |
| ufshcd-pltfrm.ko | `45bda5a43a29b94e7a66665ab5ec7e47d9855abb3fcb8bb9c04ddaba5b3bd796` |
| ufs-qcom.ko | `7a5bb9d2d72be91a8a8c3caf7c1f534f1990a1efa7531252b55f264cbd8e019d` |

The complete config differs from Generation 31 by exactly the one intended
QMP-UFS symbol transition. Clean-twin verification completed in two seconds.
The clean initramfs twins completed in two seconds and are byte-identical at
`e2b21f3b674dad5c8e1d0d236fad043362918b33acbf4e341d4a9414301c6a3f`.

## Candidate identities

| Artifact | SHA-256 |
|---|---|
| UFS-enabled DTB | `72c0db7cb2f54055240c420bbcd4fece6f497e1e648ce7081141781bc78f48c2` |
| signed manifest | `e40da74acb705843b0f29c485ca922209e44073f7baab144cbac17c5b285500e` |
| manifest signature | `79435e7bde820c95725fc7dec92b73a13811a5328f722ff4b653b53666b0b6a7` |
| Generation 32 AVB wrapper | `e527793af5fa25024519fee864a5174a373079441501f1d58b671b7251e5457f` |
| unchanged raw recovery payload | `90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6` |
| AVB generation record | `8404821af49fd49a4e6ded7227f3917582694ba45e9298d5b12ecdae7ceee4ee` |

The bundle and AVB twins are byte-identical. The first AVB issuance attempt
correctly failed closed when given an already generation-tagged predecessor;
the accepted output was derived from the exact canonical generation-zero
wrapper. No phone was contacted, no claim was entered, and no target storage
was read or written during this checkpoint. The later sole cycle is recorded
in the
[Generation 32 live result](2026-08-12-generation-32-deferred-qmp-ufs-phy-live.md).

## Final local checkpoint

`scripts/host/test-repository-linux.sh ci` passed from the complete working
tree in 352 seconds, equal to the preceding coherent-checkpoint baseline.
