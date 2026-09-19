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

### Later live-ref follow-up on September 19

Main is still `93eb3261ff4c86b84b80e05d642c753c5ece3159`, but dev has
advanced to `5ab4004a36df28799b5f0636ee0cf31d1eba8c31`. This supersedes only
the earlier statement that dev was unchanged. The GitHub
[comparison](https://github.com/denialwm/denial/compare/1395c0f5e70ecc3158fcdd9b03d02850d7ec17d2...5ab4004a36df28799b5f0636ee0cf31d1eba8c31)
contains four commits and 102 changed files: scrolling geometry/color fixes,
display/input/architecture integration, Flutter Nix lock refresh, and a
non-Flutter geometry compilation fix. The changed architecture helpers map
native ARM64 build outputs and engine targets; this is useful upstream work,
not an executed or qualified ARM64 package. The session target also gains
ordering against `graphical-session-pre.target`.

An exact-source read of
[kms_state.rs](https://github.com/denialwm/denial/blob/5ab4004a36df28799b5f0636ee0cf31d1eba8c31/compositor/src/bin/deniald/kms_state.rs)
confirms that the unsupported Linear substitution and Invalid-only pool
rejection remain. These four commits do not retire our modifier repair. The
full 102-file change was not behaviorally audited; no build or runtime result
is claimed. In particular, session ordering changes do not establish a fix
for the retained pre-Denial kernel stall.

The community and linked primary repositories were revisited. The priority
remains same-SoC SM8350/Sagami comparison first, then narrowly applicable
Hotdog display, SMB5 and sensor investigations. Hotdog's current README keeps
display instability, incomplete charging qualification and Bluetooth failures
explicit; its older Reddit demonstration is not a current support matrix.
No source was imported and no phone operation occurred in this follow-up.

Private audit directory: `rog5-denial-upstream-check-20260919-r1` under the local
state root. It retains the bare Git comparison, GitHub release/engine responses,
graphics/mobile reports and machine-readable source identities, relevant diff,
and detailed community links/licenses/access limitations. No credentials or raw
phone evidence were copied into Git. Source-review findings are not test PASS.
postmarketOS wiki/current GitLab source access was limited; support matrices were
not inferred from old search snippets. New upstream tests/build/VM: NOT RUN.

### Subsequent main merge and concrete reuse checks

Live Git now reports main at
[`cd84b8b72f21024edc3da33d5f3c8dbe9ce44985`](https://github.com/denialwm/denial/commit/cd84b8b72f21024edc3da33d5f3c8dbe9ce44985).
It merges the already examined dev revision `5ab4004a`; both have tree
`8fad31cf8d75d3c7f2032032537eb3b59d00854b`. A local
`git diff --exit-code 5ab4004a cd84b8b7` returned zero. Thus the new main
identity adds no source change beyond that dev review. Against the previous
main it contains six non-merge commits and the merge, changing 141 files.
The exact new main still substitutes Linear without render-set membership
and rejects Invalid-only pools in `kms_state.rs`. No patch retirement or
rebuild follows from the merge alone. New upstream builds/tests remain NOT RUN.

The community's same-SoC lead was checked against our actual pinned Linux
`7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`. Its Sony Sagami DTSI uses
a bootloader simple-framebuffer and Sony-specific SLPI firmware; it does not
provide a native ASUS panel or board GPU override to copy. The same source's
`sm8350-hdk.dts` enables `gpu` and names `qcom/sm8350/a660_zap.mbn`, already
present in our GPU overlay. This comparison found no missing change to import.
Keep the separately guarded GPUCC/GMU/SMMU registration overlay and ASUS
firmware/reservation evidence; identical SoCs do not imply identical boards.

Hotdog was pinned at `47087509c4289c2580c54f5433e55366b2e00445` for a
read of its [sensor gate](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/helpers/hotdog-sensor-proxy-gate.sh).
The useful idea is to establish DSP services and actual sensor enumeration
before the graphical client claims the accelerometer: owning a D-Bus name is
not sufficient readiness. The helper itself is unsuitable for direct reuse:
it unbinds a specific SM8150 SD controller to free GPIO96, invokes root-local
helpers/OpenRC, and can finish with a successful final echo after sensor
readiness expires. A future Arch implementation needs an explicit degraded
result, bounded service operations and ASUS-specific DSP/firmware validation.
This is a source finding about that helper, not a demonstrated ROG5 defect.
Its [display regression](https://github.com/Sr-0w/hotdog-linux-bringup/blob/47087509c4289c2580c54f5433e55366b2e00445/docs/evidence/2026-08-20-display-regression-01.md)
also retains DSI/DSC corruption despite recovery after lock/unlock; it supplies
diagnostic ideas, not a proven replacement panel sequence.

A further community lead is the author's [Fairphone 6 charging-mode report](https://catcrafts.net/posts/fairphone-6-postmarketos-offline-charging-mode):
a charger-origin boot enters a reduced-power session, with explicit display
and debug activation and shutdown on cable removal. This is a product-policy
idea only; its implementation and license were not audited here. Preserve
ASUS slot A for rescue/charging. Do not copy CPU/charger settings or infer
that this resolves S06/R01. The N900 suspend project addresses OMAP I2C noirq
behavior, so it is not a direct Qualcomm kernel fix.

The Reddit web listing was cached and a direct JSON request returned HTTP403;
linked primary sources and live Denial Git refs were checked separately.
This is a bounded relevance search, not a full
community inventory. No external code was imported, no runtime was upgraded,
and no phone operation or new VM execution occurred during this follow-up.

### September 20 recheck and additional keyboard lead

At local project HEAD `1ab6d7c64e5c431be80e48848e35e0d724bb5f5b`, live
`git ls-remote` and GitHub API still identify main as `cd84b8b7` and dev as
`5ab4004a`. Main is 30 commits ahead of our pinned `85b2303e`, including merges;
it has not advanced beyond the source tree examined above. A fresh exact-main
read of `compatible_xrgb8888_modifiers()` and `allocate_scanout_pool()` confirms
the fabricated Linear fallback and Invalid-only rejection remain. Existing
upstream corrections are useful, but no new build or local patch retirement
is justified by unchanged upstream bytes.

The r/mobilelinux feed also links the Rust
[linux-mobile-keyboard crate](https://crates.io/crates/linux-mobile-keyboard).
The registry identifies version 0.1.2, MIT OR Apache-2.0, with its repository
at [Codeberg](https://codeberg.org/maybeJosiah/linux-mobile-keyboard).
Codeberg/docs.rs web access failed; the published 0.1.2 archive was read directly
from crates.io, bounded to 1 MiB and without filesystem extraction or execution.
Its actual `src/lib.rs` supplies precise reasons not to adopt this version:

- `show()` and `hide()` discard D-Bus and signal errors, update tracked visibility,
  and return success. That state is not confirmation of a visible keyboard.
- `wait_for_readiness()` can accept any detected keyboard PID, not necessarily
  the child it launched; its fallback uses the child PID without protocol proof.
- `kill_if_spawned()` and `Drop` signal `self.pid` even when no owned child exists.
  Detection of another keyboard can therefore lead to termination of an unowned
  process. Clones also share the child handle while retaining copied PIDs.

These are source-level counterexamples, not executed signal tests or a claim
that our installed software has these defects. The useful idea is a small
backend adapter with lazy startup; direct dependency adoption is deferred.
[wvkbd](https://github.com/jjsullivan5196/wvkbd) remains the concrete independent
protocol-test candidate: upstream documents automatic text-field activation
through input-method-v2 and portrait/landscape layouts. Denial interoperability
and lock-screen behavior remain NOT RUN.

The Nothing Phone Spacewar demonstrations are useful interaction references,
but this bounded search did not establish the demonstrated shell's public
source and licensing. Do not substitute an unrelated Android/UEFI repository
with a similar name. SM8350 source comparisons, Hotdog's subsystem investigations,
and Pocketblue's mobile Firefox configuration retain their priorities above.
No phone access, package installation, runtime upgrade, build, or VM was performed
for this research recheck; it does not change any earlier runtime result.
