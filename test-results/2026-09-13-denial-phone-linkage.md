# Denial userspace linkage and phone-input boundary — 2026-09-13

The current Denial/engine/AOT bytes pass twelve actual ARM64 dynamic-loader
checks in a confined QEMU user-mode environment. This is **linkage only**:
no EGL context, Adreno initialization, framebuffer, scanout, touch event or
phone operation was attempted. Previous VirGL VM results remain separate.
The Pro framebuffer review does not become phone GPU evidence through this audit.

## Source and executed checks

Starting commit `dc92882cec77a065b14bd9d9f262a8baf718efd6`, tree
`6acc7af6ca5197517bd8f878fca612ac92733d9e`.
Probe build and ARM64 audit source: `8b6928778963ac5bdf8264f7b61f68268cfa8262`,
tree `b97e7b0538dfab605fe900b970e096468d0ba8f4`.
Final test-registration source: `1e1dac85021ddbc2bb3025eaa0859df829347dd9`,
tree `76b2b56a04424104a836fe2b549956a0fe9ce466`.
Only selector/manifest registration changed between those source commits;
probe and checker bytes are unchanged. This evidence commit adds metadata only.

- Thirteen focused host regressions PASS, 0.776s. The real Rust probe loads
  small C shared-library fixtures; tests cover missing libraries/symbols,
  unresolved immediate relocations, dependency closure, cleanup ordering,
  runtime-root symlinks, file tampering and strict result parsing.
- Removing explicit `dlclose` before success fails the cleanup-order regression
  as expected, 0.743s. A destructor at process exit is insufficient proof.
- ARM64 Rust probe build PASS, 1.106s, immutable retained builder image,
  512MiB/one CPU/no network. SHA256
  `00fd1f7eca8629eb8c69d6a5b2b434321da0f6527afb8806c8a8d2aca0f7fa49`.
- Twelve ARM64 loader checks PASS, total 3.398s; 117 package files verified
  against authenticated runtime tree SHA256
  `a8bc7e9fedbf5d8d8c145c5c60fad328bb4ad96b261fa075544d42c3d16418b0`.
  The three executable checks use the target loader's `--list`; nine libraries
  use `RTLD_NOW|RTLD_LOCAL`, required-symbol lookup and explicit close.
- Final active tier: **93 PASS, 0 FAIL, 0 BLOCKED, 0 SKIPPED,
  255 NOT_SELECTED**, 134.418s; peak memory 285.7MiB, no swap.
- Retained three-member GPU firmware byte audit PASS, 0.542s. Corrected
  Image/DT/metadata/panel/touch identity checks PASS, 0.063s; MSM hash and
  vermagic verified separately. No kernel build or module loading this turn.

The machine-readable [qualification](2026-09-13-denial-phone-linkage-qualification.json)
contains exact build/audit commands, each loader duration, input/output hashes,
final integrated JSON/JUnit counts and private evidence identities. It preserves
the initial 92-suite active run, followed by the final run with the new mandatory
linkage suite. No existing CI run is claimed as personally executed.

Initial setup failures are retained: bare `rustc` was unavailable, so the tests
used the retained bounded compiler wrapper; the first private archive checker
compared access time and rejected a legitimate read. The corrected stable-stat
comparison excludes access time while retaining inode/owner/mode/link/size/
mtime/ctime checks, and the complete archive hash was reverified.

## Actual checked userspace

Native Denial SHA256 `40b1fc631643d602b57db2b988eb2caf8839e1e044890f7c9aa4ad0555bb8af0`;
engine `a75c88d8f12d9ec7a24bb107ff9dc0349b6bb2d5b0f18cb4d40b9e54227e9418`;
AOT `e6434b805636598a937cfa69736012c213bd3e5b6c99f3607d495f7e4e292ba5`.
Denial upstream `85b2303e2f09ae7b7b993641f90061a200f03d53`, Smithay
`812bd33259ff58810dadef6086d8385eeac1ca55`; local patches and exact built bytes
are retained in their existing artifact records.

Checks include Denial, Foot, Mousepad, engine extension and Dart AOT symbols,
EGL/GLES, Mesa EGL, GBM and DRI backend, MSM DRI and Freedreno Vulkan.
Driver descriptor JSON names are checked against the selected libraries.
MSM DRI is a shim; successful loading does not prove later dynamically loaded
components or device initialization. The Vulkan loader itself was not exercised.
Constructors, IFUNC resolvers and destructors may execute during loading; the
probe does not call the requested symbols. Each probe has its own read-only,
network/device-isolated, bounded process environment and strict output receipt.

## Kernel, firmware and trial separation

The verified corrected module cohort targets `7.1.4-rog5-production`.
The frozen prepared phone trial targets `7.1.4-g136f75ae869a`; the historical
observed installed runtime reported `7.1.4-g05941d04803f`. Full installed-byte
verification remains BLOCKED as previously recorded. These are distinct
identities: the corrected panel/touch modules cannot substitute into the frozen
trial. No claim or admission lock was edited to make them appear compatible.

The corrected DT requests `qcom/sm8350/a660_zap.mbn`; the exact A660 catalog
requests `a660_sqe.fw` and `a660_gmu.bin`. The retained old trial CPIO contains
all three matching firmware members, whose bytes/metadata were streamed and
verified. Empty `modinfo` firmware output does not mean no firmware is needed.
The userspace fixture has no Qualcomm firmware directory; that alone does not
prove firmware missing from the phone boot payload. No new current production
composition was made. The corrected composed DT's touch I2C parent and
`touchscreen@38` both remain `disabled`.

## Changed files and remaining boundary

Implementation: `tools/denial-runtime-linkage/probe.rs`,
`configs/denial/mobile-runtime-linkage.json`,
`scripts/host/check-denial-runtime-linkage.py`,
`scripts/host/test-denial-runtime-linkage.py`, `configs/repository-tests.json`,
`scripts/host/test-repository-linux.sh`, `docs/development.md`, and
`docs/development-lessons.md`.
Publication: this report, its qualification JSON, `manifests/artifact-sets.json`,
`manifests/current-artifact.json`, `configs/project-status.json`, and the generated
header of `docs/current-state.md`. All prior artifact records and historical
current-state paragraphs remain unchanged.

The immediate next offline task is to check the existing GPU-query capability
contract against the corrected production cohort. The next useful physical
question, only under separate hardware authorization and an exact reviewed
input set, is whether A660 initialization and the bounded render/readback path
succeed with that cohort. A new Denial VM polish run cannot answer it.

Physical rows remain **NOT RUN**; historical S06/R01 remain **FAIL**. No phone,
USB, root-device access, signing, admission, claim, candidate, protected-storage
mutation or installed-image change occurred. The long-term phone goal remains
incomplete.

Publication validation: five metadata regression cases and eight mobile-status
cases PASS; inventory and generated-status checks PASS. Prior509 artifact sets,
all old current-artifact entries, both acceptance contracts and historical
current-state body were compared unchanged. Final evidence contains510 sets.
