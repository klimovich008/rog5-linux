# Generation 29 UFS Image with UFS-disabled DTB control

Status: **offline pass; unbooted; one RAM-only use; never flash**.

Generation 29 completes the missing no-storage kernel/DTB matrix cell. It
combines the rebuilt UFS Image that failed before target USB in Generations 25
and 26 with Generation 20's live-proven UFS-disabled DTB and the unchanged
persistent initramfs. The controller and UFS PHY are disabled in DT, so the
kernel cannot probe UFS and no phone storage can be exposed.

This is a clean Image-only contrast with Generation 27 under the same recovery
wrapper, DTB, and initramfs. Stable target NCM proves the failure requires the
UFS Image to interact with active UFS nodes. Failure before NCM proves the
rebuilt Image/config/source lineage is broken independently of hardware UFS
activation.

Exact signed bundle identities:

- Image: `33366ffb30e453e191538799850ac38857c445c7f34f74d1a1c655f584c07cfb`;
- DTB: `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46`;
- initramfs: `908f18f752962fae798249060aa8ee4c45673d8795571fbb8883ac4ed8d9e19e`;
- manifest: `c3cab07c75012941b103a9100e69298ef69de7aa4d73893d6d02ea4602f66f56`;
- signature: `75dfa6046df15214366879ea31c5cae67deb080efa103265aca61ccb297154b9`.

Both signed bundle builds are byte-identical and completed in 0.486 seconds.
The unchanged raw recovery wrapper is
`90c61adbbe9792efd71c19e12ea8f3caa1a9e1469b1fba44e5ef2a687b85daa6`.
Generation-29 AVB issuance completed in 1.938 seconds with wrapper
`0fa7d7511b0acce2427dccbc1c02dfdda6ee95b48040c6e66acb6ff77396f2ec`
and record
`5d3cc8063b69b7de16633ab025208cf1b34bdee8a4533f0ddf344edcee5c4a46`.
No phone was contacted during construction.
