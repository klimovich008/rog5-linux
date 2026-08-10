# Haven-aware retention/observer refreeze — offline

Date: 2026-08-10

Starting repository SHA:
`72b90e587d6ddd7aa61d4d545f7fdd7c2cafc9f7`

Recommendation: **HOLD**

No phone, fastboot, ADB, ACM/NCM device, phone storage, SSH credential,
production signing key, candidate claim, policy allow row, flash, wipe, slot
operation, persistent installation, or phone boot was used. The two build
roots below are ignored local evidence. Their execution and observer claims
remain undefined, the central temporary-boot policy remains empty, and neither
artifact has boot authority.

## Concrete defect fixed

The previous joint retention profile pinned complete execution and observer
wrapper artifacts, but did not prove that either embedded recovery responder
was built from the current repository-owned C source by the reviewed builder.
Two wrappers could therefore remain internally reproducible while carrying a
stale or substituted responder.

The verifier now binds all of the following as one fail-closed chain:

1. the fixed repository path, exact size, mode, and SHA-256 of
   `initramfs/recovery-init`;
2. the fixed repository path, exact size, mode, and SHA-256 of a build record;
3. the build record's exact responder source and builder-script bytes;
4. a hard-pinned local AArch64 image ID and digest, architecture, compiler
   version, and source-date epoch;
5. the expected production responder size, mode, and SHA-256; and
6. the exact `/init` and responder payload embedded in both the execution and
   observation-only initramfs twins.

The build record is
`configs/recovery-control/aarch64-build-v1.json` with identity
`ff3eb511d1f58bdb0c40d6301ba17be3f74e25439e479577e4982e6131b00e48`.
Its reviewed inputs and output are:

- source: size 118,545, mode `0644`, SHA-256
  `04f84497c0b735ca72b32098f73df53b3d7c8ec0777476a1d4bac002f0013fd8`;
- builder: size 2,998, mode `0755`, SHA-256
  `818384e2b974b9e6f517bf71f9cc1877cd22158de70e8af8deb4dba888e2e745`;
- build image ID
  `a085070738e277a354bc22bb033f84c7c1568ae45a35ebf951ff27510fd7fd0e`
  and digest
  `sha256:ab143fea42bd7780c2b69512397f9a33251ef9218c3258e5dd2995a905abddaa`;
- compiler `15.2.0`, epoch `1681862400`; and
- production responder: size 132,896, mode `0755`, SHA-256
  `68142abd8daafed2f1d017bd0ae07407be9dcac17e57d2294a162d2b58bf2840`.

The first hostile test failed before the correction in 0.074 seconds because
the old verifier accepted a same-length mutated responder pair in both
archives. A read-only Opus review then rejected an intermediate profile-only
binary pin as tautological: it did not prove source-to-output derivation. The
repository build record and clean AArch64 output proof close that gap.

## Fresh exact twins

The Haven-aware execution evidence root is
`build/host-rendezvous-v3-haven-offline-20260810-r1`. A clean build completed
in approximately 45 minutes 13 seconds with a disposable public key; its
private half was destroyed. Exact identities include:

- candidate config:
  `41c23330fd95d7c7426434ae3c19f948208f221ddc4f502859137f22b7eab9cf`;
- runtime manifest:
  `54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc`;
- recovery initramfs:
  `11c40b76cff9918e2e38a7e86ed70ddea4ed05104e3b84aec2f52886c650cab6`;
- wrapper config:
  `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f`;
- wrapper Image:
  `e4172f5211e1fb935ceb4ff3e91012a34e90bfa9f8d724a439bbf02aa590e2b7`;
- raw boot image:
  `7512c97b424473be7c5271901414591f29436cad40c58c43bfa31db18da5a84f`;
- unsigned AVB image:
  `139071a197768a00b01c8b46ce1233ad953e5bd0372a3d66f104bcd20d5fe9f5`.

The fresh observation-only evidence root is
`build/observation-recovery-haven-offline-20260810-r1`. Its clean twin build
completed in approximately 32 minutes 46 seconds. Exact identities include:

- observer initramfs:
  `b2440d8ccc2f22b9c9072a2404569d2a5843f7dab186a2ccac307a929a4941ad`;
- wrapper config:
  `df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f`;
- wrapper Image:
  `eedb7deb64aa42de582245b121f4ea581d0b1e21e9eb49f3591e98df8f63ef59`;
- raw boot image:
  `5daf0919d38c9f7b1ffde85a8c5e9aabdbba526bcafa1a528bd8c31e27dda171`;
- unsigned AVB image:
  `3c9b282090691b169cf96b6e6b8c458d8b592d1d1420138ef0d327cb2b9ae73b`;
- wrapper evidence:
  `116d21a57514b25fa7c43137b925bce94d9d83e9bbb7287bcceb2a0a50fd8b11`.

Both wrappers use `Algorithm: NONE`. These are reproducibility artifacts, not
production-signed or issued candidates.

The joint verifier passed in 3.141 seconds and repeated after review in 2.871
seconds. It
reported both exact AVB hashes,
the exact recovery init/source/binary hashes, zero policy allow rows, undefined
claims, `authority=none`, `boot_authority=none`, `retention=unproven`,
`missing_pstore=inconclusive`, and `recommendation=HOLD`.

## Hostile and build tests

The 19-case admission suite passed in 3.708 seconds and repeated after review
in 2.604 seconds. It covers same-length source, init, and responder mutations;
dual-archive repacks; fixed-path aliases; schema and digest format; source and
builder modes; the exact builder script; the pinned image ID; duplicate JSON
keys; malformed scalar types; and exact report output. The source/builder-only
build-record check passed in 0.057 seconds, and the private-binfmt contract
passed in 0.181 seconds.

The build-record helper uses the verifier's duplicate-key-rejecting,
no-follow JSON reader. Exact-head CI can prove repository source and builder
bytes without pretending to reproduce an AArch64 output it did not build;
local clean AArch64 builds additionally prove the output identity.

The final local AArch64 run built two byte-identical production responders,
matched the recorded SHA-256, and passed 88/88 QEMU PTY tests in 95.221
seconds; the native x86 version of the same 88-test suite passed in 28.473
seconds. The first AArch64 rerun exposed a separate harness defect: the privileged
nested network-namespace case propagated the AArch64 binary but replaced its
QEMU prefix, producing an attempted native ARM execution after 87 otherwise
passing tests. The namespace prefix now composes with the sealed execution
runner; the formerly failing physical-path simulation passes. The global host
binfmt handler was restored after each run.

The final spec review also found that the clean-build script had parsed the
record with plain `json.loads`, newline-delimited field transport, and a
literal output mode. It now delegates to the admission verifier's exact,
no-follow, duplicate-key-rejecting parser, emits only a validated 17-field
NUL-framed record, and uses the validated output mode. A proposed archive-mode
gap was disproved: the earlier recovery-role verifier already requires the
control responder to be a root-owned/root-group regular file, mode `0755`,
with one link before the embedded byte-identity check.

The complete `scripts/host/test-repository-linux.sh ci` checkpoint passed in
314.279 seconds and repeated after parser review in 299.845 seconds. It
includes the new build-record check, all 19 admission tests, the 88-case native
responder suite, lifecycle/rollback contracts, and the existing repository
tiers. The final ending-commit local run and exact-head GitHub CI are recorded
in the checkpoint handoff so this committed report does not self-modify after
describing its own test.

## Pstore observer assessment

The retained ASUS recovery source agrees with upstream persistent-RAM
semantics relevant here: initialization saves a previous persistent buffer to
the old-log view before the current kernel reuses the physical zone, and
ramoops enumerates that saved record. Enabling `PSTORE_CONSOLE` therefore does
not by itself prove that observation recovery overwrites the prior
`console-ramoops` before userspace can read it.

Physical retention across target → fallback → bootloader → observer remains
unproven. Firmware clearing, stale lineage, observer failure, and a watchdog
reset with no Linux crash dump remain possible. An empty pstore result is
still explicitly inconclusive.

## Remaining uncertainty and minimal next action

- The Haven-watchdog explanation for Generation-12 target/USB loss remains a
  strong hypothesis, not a captured reset reason.
- The NFS failure remains separately explained by host lifecycle cancellation;
  this refreeze does not combine the two causes.
- No physical transition has tested retention, USB behavior, or the corrected
  handoff.
- The exact execution and observer claims required for a future retention
  experiment are intentionally absent.

Minimal safe next action: obtain independent standards/spec review, commit
this isolated checkpoint, and require successful GitHub exact-head CI for that
exact commit. Even after those offline checks, candidate admission and
hardware execution remain separate decisions. Recommendation remains
**HOLD**.
