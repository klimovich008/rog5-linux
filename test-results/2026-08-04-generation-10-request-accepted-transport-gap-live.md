# Generation-10 request-accepted transport gap — live result

Date: 2026-08-04

Result: **REJECTED safely; consumed; never retry or flash.** The sole admitted
Generation-10 RAM-only recovery boot reached exact recovery ACM/NCM, emitted
the first correlated PREPARE progress frame, and caused the host to send the
complete signed diagnostic bundle. The ACM response transport then closed
before any later progress or `PREPARED` response reached the host; the exact
device-side boundary remains unknown. No COMMIT intent existed, no target ran,
exact Alpine fallback returned, and final host cleanup passed.

## Admission and connected preflight

The connected-preflight evidence was published at exact commit
`f4b9e1ce62ea4825516842642f35ba32c182eada`. Complete local CI and constrained
tool-free Opus review passed. GitHub Actions run `30872608193` then passed
`recovery-core` in 3m47s and QEMU in 43s at that exact head.

The fresh connected preflight passed the non-fixture deployment-key chain,
exact Generation-10 recovery and signed bundle, installed host surfaces,
rollback prerequisites, isolated USB profile, and one `lahaina` fastboot
device without booting. The lifecycle then atomically wrote the permanent
private `BOOT_CLAIMED` record immediately before its one boot gate.

## Sole RAM-only lifecycle

The lifecycle used the 100,663,296-byte AVB image
`b983e89b0279eecc8d936ef6d2d0c96222c09bd2af1de530619ef6988d468b51`.
The private bounded evidence records this sequence:

1. The exact AVB footer, `NONE` vbmeta structure, and 58,101,760-byte boot
   descriptor passed; fastboot accepted one sealed RAM-only snapshot.
2. Stable recovery exposed exact ACM/NCM on the anchored physical USB port
   with rollback armed.
3. Recovery accepted the correlated PREPARE request and emitted exactly the
   first new progress phase, `REQUEST_ACCEPTED`.
4. The one-transfer host sent all 46,163,787 bytes: manifest, signature,
   Image, board DTB, and diagnostic initramfs.
5. The restricted NFSv4.2 export reached its pre-COMMIT ready state while
   recovery control remained outstanding.
6. The initial ACM transport closed before a response containing
   `FETCH_COMPLETE`, `VERIFY_COMPLETE`, `KEXEC_LOADED`, or `PREPARED` reached
   the host.
7. Bounded replay discovery was explicitly labeled `phase=prepare-replay` and
   observed only `product-mismatch` for all 216 samples, with no identity
   changes or truncation. Its progress prefix was empty; the first attempt's
   retained prefix remained `REQUEST_ACCEPTED`.
8. The receive-only diagnostic collector independently reached its fixed
   120-second ACM-stability deadline with zero target frames and zero dropped
   USB events.
9. No durable COMMIT intent, target kexec, target USB personality, target SSH,
   mount, flash, partition write, or phone-storage access occurred.

The complete host transfer proves that recovery continued far enough to read
the entire wire payload after accepting PREPARE. The missing later progress
frames do **not** prove whether device-side fetch publication, signature
verification, kexec load, or PREPARED-state publication completed: loss of the
same ACM response channel can hide all later advisory progress. Generation 10
therefore narrows the failure to the interval after request acceptance and
host transfer, but it does not justify guessing the device-side boundary.

## Rollback and cleanup

The lifecycle made no retry. It terminated the pre-COMMIT NFS window, removed
the runtime firewall/export state, restored the exact fallback NetworkManager
profile, and verified the signed Alpine identity over strict SSH on the
anchored port. A separate post-lifecycle strict-SSH preflight also passed.

The private durable consumption record is `BOOT_CLAIMED` for
`headless-diagnostic-generation10-live-v1`. Central policy removes Generation
10, artifact inventory records it as consumed/offline-only, and hostile
readmission coverage requires even the former exact policy basis to fail on
the consumed inventory role.

Private serials, credentials, boot/session/request identifiers, and evidence
paths remain outside Git. The retained files are:

| Private evidence | Bytes | SHA-256 |
|---|---:|---|
| `bundle-server.log` | 885 | `9bdc6eb5732ad074b8aef5facbfe4c6c8baef8e48b59a09561213f2f1910edb7` |
| `early-target-diagnostics.json` | 598 | `320c58cd5c402464baa857979ce2c701f031b2c8d44079adf36d90fe7c895966` |
| `early-target-diagnostics.log` | 111 | `970a479aed1fdd0484a0dfb540f567c36766918c294ddd37cddb2b598a1a3429` |
| `fallback-identity.record` | 507 | `552a3a5fbe14b0b7520827018f1db0d78bf3c9daa990260be1f8afdb4898cbe6` |
| `fallback-preflight.log` | 84 | `c6432c9b31f985030290e137d4f9b3be42e32cb2636c4ef8960aa7f06e9bbe15` |
| `fallback-profile-restore.log` | 60 | `8608f0478541424f17bca20c9ab7adb85ba3cbe7da7fb986457fb4c358a99658` |
| `network-root-server.log` | 649 | `30f9de74861f934e0493207173e8ef384b4bcd5711441b87b23bf30fae79473f` |
| `recovery-control.log` | 321 | `2e77346449d3930591885fd37d6f1ef60cd4bd860534625aecfce3580ef70ce7` |
| `recovery-usb-anchor.log` | 110 | `017ec9cd2b1ebb5e62d411e0035375d1fd67ec453b28f1a72e987b106c70bfb4` |
| `recovery-usb.anchor` | 259 | `1427b7b42dded6cd164957bc25bb3d9dc335d37ba5ea598ff4a51b0031d5cb5b` |
| `stable-recovery-boot.log` | 799 | `3dd14cdc0f5296ea05db9bc4ed75041dd3917edac02d85dad98e99e6567e52e8` |

## Consumption-transition verification

- `scripts/host/test-recovery-linux.sh` passes with zero `allow` rows and the
  exact retained revoked-v18 policy row.
- `scripts/host/test-run-stable-recovery-live-gate.sh` passes its retained
  wrapper gate plus hostile missing-file, missing-row, malformed-policy-header,
  malformed-artifact-header, duplicate, wrong-basis, and former-exact-basis
  Generation-10 policy cases. The exact-basis case is rejected by the
  inventory role's machine-enforced leading `consumed` token before host
  inspection.
- `scripts/host/test-repository-linux.sh ci` passes after the final correction,
  including Markdown targets, compatibility/source/DTB oracles, lifecycle,
  native responder, fetcher/verifier, host controller, and recovery policy
  suites.
- The first constrained, tool-free Opus review returned actionable policy,
  evidence, and documentation findings. They were corrected. Final constrained
  re-review returned exactly `NO FINDINGS`.
- Shell syntax validation and `git diff --check` pass. No phone interface was
  used during this transition.

## Compatibility chain and next correction

The consumed inventory advances the compatibility chain to:

- artifact manifest:
  `ab4f3690c9312f0b190e3ea4e445f2a0d9f28389413093b338ec110b96f0d3d0`;
- minimal-headless profile:
  `577137fb5577a07f3fee560d4bfa3e004717bce909d64f49fd77d434cf813398`;
  and
- source/DT contract checkpoint identity (informational outer digest):
  `16ba1cc19a191f9b1b1ae0d3a784467247be689b4223abcea7582a8c429c204b`.

Do not issue Generation 11 yet. First reproduce this exact shape
hardware-free: first-attempt `REQUEST_ACCEPTED`, complete host transfer, loss
of the response channel, and fallback-only replay. Then add an independent
device-to-host progress path or retained postmortem source that survives ACM
loss and can prove the fetch/verify/load/PREPARED boundary. Extending timeouts
or changing only the AVB salt would not locate the failure.
