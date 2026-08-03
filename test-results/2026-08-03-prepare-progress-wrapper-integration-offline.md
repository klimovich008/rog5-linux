# PREPARE progress recovery-wrapper integration — offline

Date: 2026-08-03

Result: **PASS hardware-free; reproducible; `authority=none`; no Generation 10
issued or booted**.

## Outcome

The PREPARE-progress responder from commit
`6ab0bd3f509fcd2fbfab9c63c5820923c4c634fd` was cross-compiled twice,
embedded into two independently assembled stable-recovery initramfses, and
carried through two clean ASUS 5.4 wrapper builds. The responder,
initramfses, wrapper Images, raw header-v3 boot images, and unsigned AVB test
images matched byte-for-byte.

This proves the exact responder that emits `REQUEST_ACCEPTED`,
`FETCH_COMPLETE`, `VERIFY_COMPLETE`, `KEXEC_LOAD_COMPLETE`, and
`PREPARED_PERSISTED` is present in a reproducible recovery wrapper. It does
not create production signing authority or authorize a phone boot.

## Reproduction command

```sh
scripts/host/build-corrected-headless-candidate-offline.sh \
  build/prepare-progress-observability-recovery-offline-20260803 \
  --candidate headless-netroot-early-diag-v1 \
  --expected-target headless-netroot-early-diag \
  --wrapper-jobs 8
```

The entry point rejected deployment credentials, used a disposable Ed25519
key below a private temporary directory, ran the build with network-disabled
containers, and deleted the private key before reporting success.
The directory name identifies this wrapper-integration run even though it
retains the preceding feature name. The entry point's mandatory empty-output
guard passed before it created the directory contents; it would have refused
to reuse a nonempty prior tree.

## Embedded identity gate

The integration gate is stronger than a version string or marker check:

1. the production AArch64 responder, fetcher, and verifier are compiled twice
   and each twin is compared byte-for-byte;
2. the two initramfses are assembled under differing locale/timezone inputs
   and compared byte-for-byte;
3. each archive is extracted and its responder, fetcher, verifier, and public
   trust root are compared byte-for-byte with the independently built inputs;
4. the two vendor wrapper Images are built from clean output trees and
   compared; and
5. both raw and unsigned AVB test repacks are compared and inspected.

No additional marker-only identity check is needed.

After the complete build, the retained A/B initramfses were compared again.
Each retained archive was then passed independently to
`verify-stable-recovery-initramfs.sh`, which extracted it and compared the
embedded init, responder, fetcher, verifier, and public key byte-for-byte with
the retained inputs. Both verifications returned the stable-recovery PASS
marker, followed by `PASS retained A/B initramfs byte identity and extracted
component identity`.

## Reproduced identities

| Product | Size | SHA-256 |
|---|---:|---|
| framed recovery responder | 132896 | `67b4f012aab21e7b29934d3d6e41949aca5e46fdf90e9578ad5f6c87a3f2c167` |
| fixed-host fetcher | 132824 | `77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800` |
| signed-bundle verifier | 4467272 | `5f3a47bb7cc9294fedfda8b9a81d6f57bb06fd7bc2a202475a1c5cc21144a6e0` |
| disposable public trust root | 32 | `d47ee6a6014803d4ee3baee9423505563651aaee3f173fe8913d787cbbd7675b` |
| stable-recovery initramfs | 7595068 | `dd0c7729898cd6e669c7962220422a1d46b95dc821dfad976607acb5c6351642` |
| runtime manifest | 831 | `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76` |
| accepted target DTB | 102870 | `86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46` |
| ASUS 5.4 wrapper Image | 50498048 | `30ce237f127a7062cb863dbae1b746c6c82484e93b5115b4b0669d479a1fb50c` |
| raw header-v3 wrapper | 58101760 | `a2f0f10d02aa046f959956177c90dee5cccb141aafb93516e2b60e6b6a72f876` |
| unsigned AVB test wrapper | 100663296 | `cb23bc4f4c06cdcf565585b392c90638070c14698ca64f6c238fa65b6355a448` |

The wrapper used source seal
`3bfe58a00bfdd3839f9b626c2d34f0cc6778945458f1eef93cbfdea90bf2e5a8`,
configuration profile `accepted-wrapper-v18-v1`, configuration SHA-256
`df28224e6e8d2dfc825ac49dc9f6bdeb12bbcdae2dff92cbbf14a8a94177578f`,
and Ubuntu clang 18.1.3. Existing vendor compiler/linker warnings remained
nonfatal and identical in character to the accepted baseline.

## Verification and boundary

- two clean ASUS wrapper builds passed byte-identity checks;
- both raw and unsigned AVB test repacks passed byte-identity and inspection;
- `test-prepare-recovery-candidate.py`: 12 tests pass;
- `test-recovery-candidate-integration.py`: 2 tests pass;
- `scripts/host/test-repository-linux.sh ci`: the complete hardware-free
  repository tier passes, including 41-file Markdown link validation, recovery
  protocol/native/host suites, retained live-gate verification, and the
  board-neutral full-system QEMU smoke contract;
- both candidate records are identical and state `status=offline` and
  `authority=none`;
- the disposable private key is absent after cleanup; and
- the tracked worktree and Generation 0–9 policy/history were unchanged.

The run used no production signing credential, `fastboot`, ADB, recovery ACM,
SSH, phone interface, boot, reboot, flash, wipe, slot change, or phone-storage
access. No Generation 10 artifact, profile, admission, or lifecycle record was
created.

A constrained, tool-free, nonpersistent Claude Opus review found four
documentation-evidence issues: make the retained initramfs/component checks
explicit, explain the output-directory name and empty-root guard, keep review
and CI visibly open until run, and state that instrumentation does not itself
locate the live gap. After those corrections and the explicit retained archive
verification, its targeted re-review returned `NO FINDINGS`.

## Next gate

The post-transfer gap is not located by this offline checkpoint; this result
only proves that the instrumentation needed to locate it is reproducibly
embedded. First publish this checkpoint with green review and CI. Then create
a distinct production-signed recovery successor from this exact
responder/initramfs/wrapper identity, bind it to an immutable lifecycle
profile, and pass artifact, credential, rollback, fallback, and successor
review/CI gates before any temporary boot. Any Generation-10 lifecycle is
diagnostic-only: use the new progress prefixes to locate the PREPARE boundary,
not to promote the normal Arch target prematurely.
