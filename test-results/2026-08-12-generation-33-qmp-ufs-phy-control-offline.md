# Generation 33 QMP-UFS PHY control discriminator

Status: **offline checkpoint passed; unbooted; one RAM-only use only; never flash**.

Generation 32 proved that deferring the QMP-UFS PHY registration clears the
pre-init USB failure boundary, but its four-module sequence did not identify
which transition preceded target loss. Generation 33 changes no kernel, DTB,
or module binary. It changes only the sealed initramfs control flow: after the
existing host rendezvous it inserts `phy-qcom-qmp-ufs.ko`, proves that exact
module is present while the UFS core, platform glue, and Qualcomm host remain
absent, and keeps the exact UDC, carrier, and NCM identity alive for 15 target
seconds before a deliberate five-second fallback.

The host independently requires one unchanged anchored USB identity, direct
route, exact `169.254.77.1/30` address, NetworkManager ownership, and a
non-drop firewall zone for 12 seconds. That window starts after host-side NCM
activation and overlaps the target's three-second pre-probe delay; it is a
control-window discriminator, not by itself proof that `insmod` returned. The
target-side 15-second post-return hold and resulting fallback timing provide
the complementary evidence. The cycle performs no UFS enumeration, block
read, mount, filesystem operation, or phone-storage write.

## Focused checks

- persistent-root storage/UDC/rendezvous/module control: 9 tests in 0.759
  seconds;
- deterministic real-module initramfs fixture and hostile inventory checks:
  pass;
- live-cycle runner, including exact-window and early-loss fixtures: 10 tests
  in 0.005 seconds;
- generic exact-claim consumer: 14 tests in 0.044 seconds;
- retention executor contract and descriptor boundary: 8 plus 11 tests in
  0.053 seconds;
- retention admission: 27 tests in 3.174 seconds;
- core compatibility oracle: 39 tests in 0.391 seconds;
- current exact profile and stable recovery gate: pass.

## Reused and rebuilt identities

The kernel and modules are the byte-identical Generation 32 clean-twin
outputs. Only the initramfs, signed bundle, and generation-tagged AVB wrapper
were rebuilt.

| Artifact | SHA-256 |
|---|---|
| reused kernel Image | `53d42da77b65a37149bd269c5d71d7855a7edb51748cb2da478bff5cb5f95203` |
| reused UFS-enabled DTB | `72c0db7cb2f54055240c420bbcd4fece6f497e1e648ce7081141781bc78f48c2` |
| initramfs clean twins | `e14253847f2acb7730a22e01cbad0f5f61147a9bc2b82365706fc5adf078f723` |
| signed manifest | `330f33a533f8f65e1d32b9e9c90bce10b4301983d7dced88fddfcd8f49e9f294` |
| manifest signature | `3ccf52761ff9322c51d50da5382a0d138c474e98742f2dd1cf9b80f865ab8624` |
| Generation 33 AVB wrapper | `56dc47f1ead79a66cfd6d66a293ced84a120f3b980cd5a12685a164938d8f3de` |
| unchanged raw recovery payload | `90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6` |
| AVB generation record | `57f7e45003571d8606114b15b5b9970d755d629b0b276327d3d90b0fdae8e671` |

Initramfs twins completed in one second, signed bundle twins in one second,
and the AVB generation twins in two seconds. No phone was contacted while
building or validating this checkpoint, and no claim has yet been entered.

The coherent repository baseline for this change is
`23a574611331d39a46c83b0df516da06314b96e3`. The final repository CI timing
was 351 seconds, one second faster than the preceding 352-second checkpoint.
The ending publication commit is reported after commit creation because a
commit cannot contain its own identity.
