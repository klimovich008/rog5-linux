# Generation 25 UFS-only Image control

Status: **OFFLINE-READY; unbooted; RAM-only; never flash**.

Generation 24 reached the shell-free recovery COMMIT but never exposed the
target USB product before exact Alpine returned. Moving NCM ahead of target
identity and userspace UFS checks therefore disproved the prior command-line
ordering explanation. Generation 25 changes the target kernel config from
the persistent-root profile to the historically live-passing read-only UFS
profile. The only functional Kconfig delta is `CONFIG_OVERLAY_FS=y` to `m`.
The DTB and initramfs remain byte-identical to Generation 24; the mandatory
bundle and AVB generation identifiers rotate for one-use execution.

## Clean kernel control

Two network-disabled builds used the retained clean Linux source at commit
`cfd385a1c754684dd28b63a4559e04baa5e902b1`, tree
`d2f03d2055227b8b72ab41be949847a066924c5a`, the reconstructed historical
Clang-18 builder, and separate empty output trees. Both completed in about
39 minutes 46 seconds while running in parallel and produced byte-identical
outputs:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `.config` | 242,248 | `f36d92cadc1d9982157143a02631c25a2ea88a71e32034305a59ac26b693c1eb` |
| `Image` | 38,406,656 | `33366ffb30e453e191538799850ac38857c445c7f34f74d1a1c655f584c07cfb` |
| `Image.gz` | 14,316,856 | `f232ba75a1ec5a19d3d79319e33eb58aa0c63f4603a63e68df7a22041b5d3582` |

The source, config, release `7.1.4-gcfd385a1c754`, arm64 Image header, and
compiled read-only UFS guards all verify. The new Image does **not** reproduce
the pruned 2026-07-24 binary hash `bdc72155…`; the exact cause of that binary
identity difference is unresolved. It is therefore recorded as a new clean-
twin identity, not mislabeled as the historical artifact. This does not alter
the functional config discriminator.

## Candidate identities

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| target Image | 38,406,656 | `33366ffb30e453e191538799850ac38857c445c7f34f74d1a1c655f584c07cfb` |
| Generation-24 DTB reused exactly | 103,546 | `72c0db7cb2f54055240c420bbcd4fece6f497e1e648ce7081141781bc78f48c2` |
| Generation-24 initramfs reused exactly | 6,121,179 | `908f18f752962fae798249060aa8ee4c45673d8795571fbb8883ac4ed8d9e19e` |
| signed manifest | 831 | `5d835b0986587c7ce174e66ccf03f82bb8c9e581e83384ce93c0ed455d053baa` |
| manifest signature | 64 | `5ada74327b558f51c26c6b90b6707e294dfdd7748a6bda0203521f5188a99465` |
| Generation-25 AVB wrapper | 100,663,296 | `0947cde461c495cd889e6c4de9cbafe1fe9bc3ceb977844a7c8ec2a5590a3a8c` |
| unchanged raw recovery wrapper | 58,114,048 | `067329920cc479714cac10ce001112c9029a3b986ac44269b8e7185a396c4aff` |

The signed bundle twins are byte-identical. AVB generation 25 has salt
`d28bdb6d…c8235`, digest `a28ab175…106bd`, and generation-record SHA-256
`013aca00…20075`. The wrapper still has `authority=none`; repository policy,
an exact durable claim, exact-head CI, and the live lifecycle remain separate
requirements.

## Host correction and focused checks

Generation 24 also exposed a host-only classification defect: the lifecycle
queried NetworkManager ownership while Alpine was still re-enumerating, so a
valid fallback transition could be reported as an ownership failure. The
runner now classifies fallback through the already anchored exact USB identity
and leaves NetworkManager inspection to the later cleanup stage.

- live-runner unit tests: 8 passed in 0.003 seconds;
- generic exact-claim tests: 14 passed in 0.041 seconds;
- exact current-profile artifact preflight: passed in 11.616 seconds;
- stable live-gate contract plus admission tests: passed in 7.155 seconds,
  including 27 admission tests in 3.176 seconds.

No phone was contacted, no claim was entered, and no phone storage was read or
written during this offline checkpoint.
