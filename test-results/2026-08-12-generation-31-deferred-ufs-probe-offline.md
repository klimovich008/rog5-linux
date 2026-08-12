# Generation 31 deferred Qualcomm UFS-probe discriminator

Status: **offline ready; unbooted; one RAM-only use; never flash**.

Generation 30 reproduced the early target loss with the accepted UFS-capable
Image and enabled UFS DTB: no target USB identity appeared before exact Alpine
returned. Generation 31 changes only the probe timing. USB remains built in;
UFS core, platform glue, and the Qualcomm host driver are sealed as three
modules outside `/lib/modules`. Initramfs establishes NCM, requires ten stable
100 ms carrier samples, leaves a fixed three-second host observation window,
then loads the exact module chain in dependency order.

## Clean twins

Two empty-output builds ran in parallel in the pinned historical Clang 18.1.3
container. They completed in 2,442 and 2,444 seconds. Their source commit is
`cfd385a1c754684dd28b63a4559e04baa5e902b1` and source tree is
`d2f03d2055227b8b72ab41be949847a066924c5a`.

| Artifact | SHA-256 |
|---|---|
| config | `042b652a6d349e7d6f2eb2e41f95fb177ac2a6b062542a5f2ebd7d1b8e60ed16` |
| Image | `247d179de5d3c1955086bece25d086f689ef729f36b7e59c1a830f8024eb91bb` |
| Image.gz | `1af24e6dea96e1471c01c6c9d0fbc5397973890cc43bbf0607d6647ed163b8e9` |
| ufshcd-core.ko | `317e973fea0fb673ea737daf1a2558ca39d43fa8a7ff2ee37e5f27820753ddf5` |
| ufshcd-pltfrm.ko | `61559c8d4c50bb0874fef26172d64bca1a89c80ca1c53327adbf49a20de27215` |
| ufs-qcom.ko | `e0f86f0e16d9322dff366d828f6aa4503c5f52d1123dbe2148b6ca7cedf08faf` |

The complete config differs from the accepted persistent-root config only by
`CONFIG_SCSI_UFSHCD`, `CONFIG_SCSI_UFSHCD_PLATFORM`, and
`CONFIG_SCSI_UFS_QCOM` changing from built-in to modules. The clean initramfs
twins completed in two seconds and are byte-identical at
`36900b357674f66e6808eaf48e97e9c0b9858a807030786265be0582f9fcd9c6`.

## Candidate identities

| Artifact | SHA-256 |
|---|---|
| UFS-enabled DTB | `72c0db7cb2f54055240c420bbcd4fece6f497e1e648ce7081141781bc78f48c2` |
| signed manifest | `dc22fde250d88f75859d544737d3703f9a3cf09ca2987eaf213dd744204cd8f7` |
| manifest signature | `2ac44cda112fb077d34839c6ad39e8c96ae17f83434915fa29d974070b5ee7cf` |
| Generation 31 AVB wrapper | `218bd8f60e4b88f91981334fa40431dd7a7a47886f68d9bd93e4b9614783fce1` |
| unchanged raw recovery payload | `90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6` |
| AVB generation record | `861df55c9119b3134acdeec8f43aa1eee00fec658655312eddd6425e68bfa56b` |

The signed bundle twins and AVB wrapper twins are byte-identical. The exact
claim remains unentered. No phone was contacted, no target storage was read or
written, and no boot occurred during this checkpoint.

Focused tests passed: eight storage/UDC/rendezvous tests in 0.84 seconds,
real-module deterministic initramfs plus hostile inventory tests in 4.42
seconds, 14 generic claim tests in 0.043 seconds, eight live-runner tests in
0.002 seconds, exact artifact/profile preflight in 12.25 seconds, stable-gate
contracts in 4.25 seconds, and 27 admission tests in 3.16 seconds.

The final complete local checkpoint,
`scripts/host/test-repository-linux.sh ci`, passed in 352 seconds.
