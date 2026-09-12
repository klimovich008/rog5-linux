# ROG5 RPMh and touch offline qualification, 2026-09-12

Starting source: `b2065813860ea0bc8d0e96fe165e91f11a76d087`, tree
`bee31454298d4a6ee7c8426c7c6ac7e66767da87`, branch
`agent/review-correctness-20260912`. The original dirty working checkout,
historical Q6 failure, signed candidate/fallback and phone were untouched.

## Result and scope

The new [board software receipt](2026-09-12-touch-board-qualification.json)
is PASS. All sixteen production patches applied in order to every affected
file from the pinned Linux archive. Only the RPMh binding differs from the
previous patched kernel source; all Image/module inputs are unchanged. The
retained Image, 1,031 modules and four overlays were rehashed. The changed base
DT was compiled with the actual kernel tool/flags, after reproducing the old
DTB byte-for-byte. Full-board validation against all bindings has zero
diagnostics. No cold Image/module rebuild was needed.

The new DTB SHA-256 is
`52978b7def2241ed8f8d8a0223eb5becf47976b0355c09120ecfc8e2a5b5ead7`.
Image remains
`0789c10855e74c2f54caee7437864235f5872118e9f697782cc8547b286d406a`.
The current source binding is `5b716c1d0a48dfe13e429d94ac07a460681e250f`,
tree `9492c29f1a71bb5e6164fb3da9d3ff803ec1c4b7`. Raw execution records retain
their dirty-checkout metadata separately from these verified committed inputs.

The dedicated touch prototype built twice in 2.854/2.855 seconds against the
read-only kernel kit. Both modules are 16,144 bytes, SHA-256
`a2560d4458e5cab00725912db3a7e7551eb70362af2747d261a8460a7ac23b15`,
vermagic `7.1.4-rog5-production SMP preempt mod_unload aarch64`, with no
module dependencies. W=1 and modpost emitted no warnings. Its required GENI
I2C provider is built in; GPI remains a separate module. This does not prove
physical bus operation. The touch driver and disabled overlay are unchanged.

The source-origin supplement matched all 698 consumed kernel source files
against the exact Linux archive plus production patches. Forty-two generated
or built inputs were recorded and verified unchanged; they were not regenerated.
This supplement took 15.387 seconds and retains its producer/cache identities.

## Regressions and review

- RPMh: the historical generic-compatible DT fails the required power-domain
  check. The ASUS-specific pair passes, an optional valid domain passes, and
  malformed compatible/domain fixtures fail. Generic nodes retain the original
  requirement. The decoded before/after DT differs only in that compatible.
  Five actual driver PM branches pass; kernel PM code/configuration is unchanged.
- Full RSC/schema run: 81.378 seconds. A later seven-case, 0.001-second guard
  test rejects enabled, duplicated or absent PSCI-domain assignments. The old
  substring guard accepted a conflicting enabled assignment. An AST/input
  supplement binds the stricter guard without repeating the unchanged schema run.
- Touch lifecycle: fifteen actual-driver cases, thirteen probe-failure stages
  and three mutation controls pass in 1.822 seconds. They cover IRQ draining,
  immediate IRQ delivery, stale contacts, transient regulator errors and
  suspend refusal. Exact 7.1.4 IRQ/MT functions are compiled and compared with
  the retained source. No driver defect was invented to justify changes.
- Touch builder: twelve tests pass in 0.506 seconds. An actual failed-make
  fixture exposed missing command/timing in failure receipts before the fix.
  Failures and interruption now retain stage command, duration and exit status.
  Successful build-command/launch ASTs are unchanged, preserving the twins.
- The explicit `board` test tier requires kernel/schema prerequisites, records
  JSON/JUnit results and fails on missing source. Ordinary host tests include
  the cheap guards, actual touch harness and namespace builder regressions.

Integrated tier: pending final frozen-source execution. Earlier 297-PASS host
results belong to the preceding repair and are not a new result for these changes.
Remote GitHub Actions and full-system QEMU were not run in this continuation.

## Remaining limits

Persistent regulator-disable failure during final devres cleanup can leave
power outstanding after the consumer is destroyed. Transient retry tests do
not prove rail restoration after unbind. The private draft supplies have no
declared parent/coupling or load adjustment; extending those features needs
separate error/ownership analysis. Suspend returns `-EBUSY`; physical touch,
normal firmware identification, coordinate calibration, IRQ delivery and wake
are NOT RUN. Mobile physical rows remain NOT RUN; headless S06/R01 remain FAIL.

The RPMh compatible documents the existing firmware integration and retains the
generic fallback; it does not qualify CPU idle or suspend. This follows the
board-specific binding structure used by the upstream
[SC7180/SDM845 firmware exception](https://lists.openwall.net/linux-kernel/2025/03/18/1540).
Firmware presence, hermetic toolchain closure and physical panel/GPU qualification
remain open. The old Q6 FAIL receipt has not been edited or relabelled.

The next touch question is whether the exact normal-mode controller responds
as `56/52` through the qualified provider/rail topology. A future authorized,
bounded identity/readback trial must establish cleanup and fallback before
asking for touches. No phone operation, candidate generation, signing,
admission, claim creation/consumption or protected-storage mutation occurred.

Exact commands, raw logs, timings, hashes and read-only input bindings are in
the private `rog5-touch-kernel-evidence-20260912-r1` evidence root. The
[current artifact pointer](../manifests/current-artifact.json) separates the
historical board failure, new software supplement, touch prototype and signed
candidate. None of these offline results authorizes installation.
