# Denial upstream and Mobile Linux reuse audit — 2026-09-19

Source review only. No build, VM, phone operation, source import, candidate,
signing, admission or claim consumption occurred in this audit. Physical
qualification remains NOT RUN. The earlier VM device-wait failure remains open.

## Exact Denial comparison

Local project source: `745640319f88aa450415af6b0c905329b9f97afe`, tree
`04d6835c50fbfe5f66b580535ee9640b28baa1c2`.
Our Denial base is `85b2303e2f09ae7b7b993641f90061a200f03d53` (v0.3.1).
Live Git refs identify main/v0.4.3 as
`93eb3261ff4c86b84b80e05d642c753c5ece3159`, 23 commits ahead;
dev is `1395c0f5e70ecc3158fcdd9b03d02850d7ec17d2`, two further commits.
The initial cached web history was stale; live Git and GitHub API supplied the
current identities. [Exact comparison](https://github.com/denialwm/denial/compare/85b2303e2f09ae7b7b993641f90061a200f03d53...93eb3261ff4c86b84b80e05d642c753c5ece3159).

| Local issue | Current upstream source disposition |
| --- | --- |
| Close/focus commands starved before background yield; delayed flush (0009/0012) | Addressed by [e40d5988](https://github.com/denialwm/denial/commit/e40d598813a3462e537cb4d24c8e158be52a1d5c). Upstream drains all commands; retain a review of our bounded-work policy. Does not prove Mousepad teardown succeeds. |
| Mobile content-origin coordinates (0019) | Same commit restores origin and divides presentation scale, covering more than the local 1:1 correction. |
| Render/resource EGL clear-current dispatch (0005, Denial half) | Addressed by [3284c6c](https://github.com/denialwm/denial/commit/3284c6c09b09e7462cd946fb9b0664909ad85951). Matched engine teardown needs separate qualification. |
| Backing-store refusal diagnostics (0002) | Reason-specific categories in [4217e8c](https://github.com/denialwm/denial/commit/4217e8c1944ac3d09818e6d97b248956a32fd756) largely cover their purpose. |
| Implicit/explicit modifier contract (0001) | Still unresolved: fabricated Linear support, Invalid-only pool rejection, no requested/BO/export modifier agreement check. |
| Work-ID reservation lifetime (0006) | Still unresolved: view-only grants and unconditional expiry remain. |
| Callback-registration lifetime owner (0007) | Still unresolved: fallible registrations precede construction of the owner. |
| Keyboard geometry/caret publication (0013–0017) | Not replaced wholesale. Shared animation geometry and caret transport/visibility are absent; observer changes partly overlap. |

Additional fixes include [delayed software-keyboard activation](https://github.com/denialwm/denial/commit/81356a790db52341699ea2389aba380ad3ecd91d),
prepared-renderer retention, focus handoff, and SVG raster reuse. Icon performance
changes do not prove our startup stall resolved. Main/dev retain the same
examined graphics defects; dev's extra packaging/scrolling work does not fix them.

The matched Flutter engine changes from
`d728e61e7d835e02c453c70ae9523a40f6c03215` to
`c8894357b3a91902c358e8ad5cf0ebc85d45e83e` (46 commits, 77 files).
The [engine comparison](https://github.com/denialwm/flutter/compare/d728e61e7d835e02c453c70ae9523a40f6c03215...c8894357b3a91902c358e8ad5cf0ebc85d45e83e)
includes resource-context shutdown and image-upload draining, but does not modify
`gpu_surface_gl_impeller.cc` or the rasterizer files. Do not assume local engine
surface-clear, work-ID or pending-scene fixes are obsolete. New Denial also loads
a texture-presentation callback symbol: compositor, engine and shell must match.
[v0.4.3 release](https://github.com/denialwm/denial/releases/tag/v0.4.3) publishes
x86-64 packages, not a drop-in ARM64 runtime for this project.

Before another expensive build, port only still-needed contracts with their
semantic regressions and retire overlapping patches only after those checks.
The current device-wait failure occurs before PAM/Denial; upstream compositor
changes are not evidence that this independent startup boundary is repaired.

## Community reuse, prioritized for ROG5

The [community porting discussion](https://www.reddit.com/r/mobilelinux/comments/1tzhxhb/how_do_you_guys_even_port_linux_to_android_phone/)
leads to postmarketOS and Linux MSM work. No independently verified ready-made
ROG5/anakin port emerged in this bounded search.

1. **Same-SoC references:** [SM8350 mainline fork](https://gitlab.com/sm8350-mainline/linux)
   and [upstream Sony Sagami DTSI](https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/qcom/sm8350-sony-xperia-sagami.dtsi).
   Compare power domains, firmware integration and device-tree wiring against
   our exact 7.1.4 source. Sagami is BSD-3-Clause; Sony board values are not ASUS
   values. The accessible postmarketOS package is older 6.7-r2/GPL-2.0-only;
   the fork's current patch contents were not accessible and are NOT AUDITED.
   Pin mutable upstream references before any import.
2. **Display, charger and suspend investigations:** the [OnePlus 7T Pro post](https://www.reddit.com/r/mobilelinux/comments/1vjzdxr/ive_been_bringing_mainline_linux_postmarketos_to/)
   links [Hotdog Linux bring-up](https://github.com/Sr-0w/hotdog-linux-bringup).
   Its GPLv2 repository has DSI/DSC, SMB5 and remoteproc power-domain investigations,
   plus a sensor integration lead using libssc/iio-sensor-proxy. It targets
   SM8150/A640 and different touch hardware. Child investigations are leads,
   not yet audited patches; do not copy panel commands or charger limits.
3. **Independent keyboard test client:** the [native-mobile Linux post](https://www.reddit.com/r/mobilelinux/comments/1utdymr/i_finally_have_two_mobile_linux/)
   uses [wvkbd](https://github.com/jjsullivan5196/wvkbd), GPLv3. Current Denial source
   creates layer-shell, virtual-keyboard-v1 and input-method-v2 globals, so it is
   a concrete protocol-testing candidate. This source inventory does not prove
   client interoperability, automatic activation, lock-screen policy or ARM64
   runtime behavior. Preserve Denial's intended integrated shell.
4. **Packaging reference:** that post also links [Phoneputer](https://github.com/mwlaboratories/phoneputer),
   MIT, for OnePlus 6/Mobile NixOS. Pinned package closure and separate bootstrap
   versus session configuration may be reusable ideas, subject to comparison
   with our existing work. Retain Arch; its partition/flashing guide does not
   apply to our rescue layout.
5. **Practical mobile applications:** the community's
   [Pocketblue post](https://www.reddit.com/r/mobilelinux/comments/1vwe4bb/fedora_atomic_by_pocketblue/)
   leads to its [mobile Firefox configuration](https://pocketblue.github.io/tips-and-tricks/flatpaks/).
   This is a concrete app-usability reference for our eventual Arch session;
   it is not a kernel port or evidence that our browser, portal or keyboard works.
   Inspect the actual configuration and its license before importing anything.

The follow-up source read also confirms a useful sensor integration distinction
in [Hotdog's support description](https://github.com/Sr-0w/hotdog-linux-bringup):
its `iio-sensor-proxy` uses `libssc` to communicate with Qualcomm SEE over QMI,
without an IIO/input device, and applies a measured `ACCEL_MOUNT_MATRIX`.
This is a lead for the non-cellular rotation milestone, not permission to copy
its sensor firmware, calibration or axis matrix. Its suspend report explicitly
retains Bluetooth and other resume limitations. These are that project's
reported results, not independently reproduced results or ROG5 qualification.

Live Denial refs were checked again during this follow-up: main remains
`93eb3261ff4c86b84b80e05d642c753c5ece3159`, dev remains
`1395c0f5e70ecc3158fcdd9b03d02850d7ec17d2`. The v0.4.3 annotated tag object
is `d65db9bc1c2758c26c75eedd47581ff6d653607a`; do not confuse the tag-object
identity with its target commit. No newer compositor build is justified by
these unchanged refs alone.

The OnePlus 12R Denial demonstration uses Snapdragon 8 Gen 2/Adreno 740,
not our SM8350/A660. Its success is neither ROG5 GPU nor panel qualification.
The smallest kernel follow-up is one same-SoC source comparison tied to an
unresolved ROG5 path, followed by a host regression if a real defect is found.

## Retained evidence and limits

Private audit directory: `rog5-denial-upstream-check-20260919-r1` under the local
state root. It retains the bare Git comparison, GitHub release/engine responses,
graphics/mobile reports and machine-readable source identities, relevant diff,
and detailed community links/licenses/access limitations. No credentials or raw
phone evidence were copied into Git. Source-review findings are not test PASS.
postmarketOS wiki/current GitLab source access was limited; support matrices were
not inferred from old search snippets. New upstream tests/build/VM: NOT RUN.
