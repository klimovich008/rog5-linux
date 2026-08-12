# Generation 30 accepted persistent-root Image

Status: **offline pass; unbooted; one RAM-only use; never flash**.

Generation 29 proved that the rebuilt UFS Image reaches stable target NCM
when UFS is disabled, localizing the remaining loss to active UFS binding or
probing. A fresh build in the reconstructed historical container produced
Image `805a68b3…e923b`, not the live-accepted UFS-discovery Image
`bdc72155…9ac8c`. The source commit, source tree, config, compiler version,
and deterministic build fields matched, so the reconstruction is not an
exact substitute for the original build environment.

Generation 30 avoids that ambiguity. Its target is assembled from:

- retained clean-twin persistent-root Image: 38,607,360 bytes,
  `832757fc6b97554813a14049123667bc6f5b225e6204ca048d73c3a36c76469f`;
- current UFS-enabled DTB:
  `72c0db7cb2f54055240c420bbcd4fece6f497e1e648ce7081141781bc78f48c2`;
- current USB-first read-only initramfs:
  `908f18f752962fae798249060aa8ee4c45673d8795571fbb8883ac4ed8d9e19e`.

The exact Image is recovered from the retained P2 outer stage and independently
hash-verified before packaging. Its original acceptance record pins clean
twin builds, source commit `cfd385a1c754…`, source tree `d2f03d205522…`,
config `8a7fabffa076…`, built-in ext4/OverlayFS, and the read-only UFS guards.

Signed bundle twins are byte-identical:

- bundle: `persistent-root-accepted-image-v9`;
- manifest:
  `90c3cd03ab749003d46f039b31d6bffd51b98d2ea18e858eaddf59cb64c0efbd`;
- signature:
  `fd9903ddcac5696158afa2796ce46751819dd5b6add816d7ff469d6b67ea7713`;
- trust key:
  `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b`.

The recovery raw payload remains unchanged at
`90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6`.
Generation-30 AVB issuance produced wrapper
`7e6185bc40778c74d4528d54c22ae249997132ff0c57f64eb47ce7ba854a9ec4`
and record
`611cd93a6d6abaf7fc0a358ecf9957806423dacc912b35eabb19bb11358604d4`.

The live path can force all 116 physical nodes read-only, identify exact
userdata, mount it only as `ext4 ro,noload`, verify the sealed Arch tree, use
it as an OverlayFS lower with tmpfs upper/work, start systemd and key-only SSH,
collect UFS and mount evidence, and return to Alpine. It has no phone-storage
write operation and cannot create the later bounded local filesystem image.
