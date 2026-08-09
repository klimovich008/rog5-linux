# Observation-only stable recovery — offline

Date: 2026-08-09
Starting repository SHA: `a4f53711b9f70201932d0634e181b689727e01be`
Recommendation: **HOLD**

## Outcome

Stable recovery now has a distinct observation-only initramfs composition for
a future ramoops-retention experiment. The concrete gap was that the only
current recovery identity retained the complete bundle fetch, verification,
prepare, commit, and kexec surface. Using that identity for a postmortem boot
would make an intended read-only observation depend on operator discipline
rather than a machine-enforced role.

The fix binds the role at both PID 1 and protocol layers:

- `/etc/rog5/recovery-mode` must be a root-owned, regular, non-symlink,
  single-link, mode-`0444`, one-line file with the exact selected-mode byte
  count before USB setup;
- `full-v1` alone creates the volatile bundle root;
- `observation-only-v1` requires that root to be absent;
- the production responder requires one exact explicit mode;
- observation mode permits `HELLO` and `STATUS`, returns
  `OBSERVATION_ONLY` for `PREPARE` and `COMMIT_EXEC` before ledger, state,
  helper, or kexec mutation, and refuses non-IDLE, non-`NONE`, or nonempty
  ledger state at startup; and
- the observation archive contains no bundle fetcher, verifier, public trust
  key, kexec binary, or bundle root.

The exact UDC selection, read-only storage isolation, pstore snapshot,
watchdog, fixed NCM address, and rollback behavior are unchanged. The
observation binary still contains the reviewed full implementation, but its
validated packaged mode, protocol refusal, missing execution tools, and
absent bundle root form independent fail-closed layers; it does not infer its
role from a missing helper.

No phone, credential, signing key, candidate, manifest policy row, wrapper,
flash, wipe, slot, phone storage, or boot action was used.

## Patch and hostile regression boundary

- `initramfs/recovery-init` validates the immutable role before any bundle
  root or responder startup and passes it explicitly to the responder.
- `tools/recovery_control/rog5-recovery-control.c` and its reference model
  implement the exact observation-only result and pristine-start contract.
- `scripts/device/build-observation-recovery-initramfs.sh` first verifies a
  current full archive, pins the BusyBox identity, removes all execution
  components, changes only the sealed mode, repacks deterministically, and
  verifies the derived archive before publication.
- `scripts/device/verify-stable-recovery-initramfs.sh` separates current full,
  current observation, and hash-pinned historical contracts.
- `packaging/host/rog5-recovery-bundle-controller` pins the resulting exact
  protocol-reference digest, preserving installed-module refusal on any
  unreviewed byte change.
- host tests prove that observation-mode prepare/commit attempts invoke no
  fetcher, verifier, loader, ledger, claim, or execution path; nonpristine
  last-error and ledger state refuse startup; and an observation-only PREPARE
  response cannot arm the host COMMIT ledger.
- cross-locale/time-zone archive tests reject a full archive presented as an
  observer, a wrong mode marker, and an injected kexec binary.

The fail-first native run against the old responder produced two failures in
2.33 seconds: no mode argument was accepted and the observation-only protocol
identity was absent. During integration, four hostile fixture/verifier issues
were corrected without weakening the contracts: invalid reliance on
unprivileged extracted UID (85.17 seconds), private-copy mode mutation
(87.22 seconds), the earlier historical failure boundary (89.86 seconds), and
hostile-fixture mode mutation (90.69 seconds).

The final manual audit then found that line count plus one `read` did not by
itself exclude unterminated trailing bytes after a valid first line. PID 1 now
requires the exact 8-byte `full-v1` or 20-byte `observation-only-v1` record as
well as one newline. The policy regression fails without those size checks;
the corrected r2 twins passed the complete integration gate in 98.15 seconds.

Focused fixed results:

| Check | Result | Time |
|---|---|---:|
| recovery-init policy | 12 tests passed (0.133 s suite) | 0.25 s |
| host recovery-control | 42 tests passed (0.171 s suite) | 0.34 s |
| native observation mutation/startup subset | passed | 2.25 s |
| AArch64 native responder through private binfmt | 72 tests passed; reproducible production binary | 93.18 s |
| full + observation cross-locale integration | passed | 98.15 s |
| complete `scripts/host/test-repository-linux.sh ci` | passed on the exact r2 composite working tree | 457.84 s |

The first complete repository run stopped after 432.13 seconds because the
host controller still pinned the pre-change protocol-reference digest. The
controller therefore would have refused the newly reviewed module set. After
updating that one pin from the measured source digest, its focused 38-test
suite passed in 29.71 seconds and the then-current complete tier passed in
458.60 seconds. After the final exact-size hardening and r2 rebuild, the exact
final complete tier passed in 457.84 seconds (`user 144.10`, `sys 146.83`). It
also exercised the preserved uncommitted VCNL sensor work; that makes it a
composite-tree validation, not an ownership or completion claim for those
files.

## Reproducible composition

The final full and observation initramfs twins compare byte-for-byte:

| Component | Size | SHA-256 |
|---|---:|---|
| recovery init source | — | `c989f8dddb8097f6f8a16370cf3b0f565085a6b2cf1acac063dc54742a088309` |
| recovery responder source | — | `3f25a0f2d528dcaf963804d03be32371127542f4a2f555c623f03ce15375e96c` |
| native AArch64 recovery responder | 132,896 | `87c47583a9aad6597e9e9ab8e7d3f0859bc68aa09502019d9172c0a9ae0e41cf` |
| fixed bundle fetcher, full archive only | 132,824 | `77eff28d60d6997a1f3ebfd641cfa458f6fdedbcc05feb49d003d6d4f7afe800` |
| native verifier, full archive only | 4,467,272 | `33aa65c6438c11a577854dcf95482759c8a3e703bd2cd2ed14d8c22775e442ef` |
| disposable trust input, full archive only | 32 | `b279a61121aa108b53e51720ed3d6f3b274343f564b8173aa4e6d87911ad3075` |
| current full initramfs A/B | 7,603,762 | `550f851d3ff8b2c85ceccc0c9ea5b348195fa46c2f3db52303aa9a4e2aaa812b` |
| observation-only initramfs A/B | 5,371,780 | `613d6e3e61d7818693c0d26b0b7c252479941cc25c98e897ef6aa30469e770db` |

The ignored evidence occupies approximately 30 MiB below
`build/recovery-observation-only-offline-20260809-r2/`. The retained prior
exact-UDC archive was also measured directly at 7,602,307 bytes; earlier
documentation said 7,602,301 while recording its correct unchanged
`afc55f96…d790` digest. Only that metadata typo was corrected.
The superseded r1 observation evidence is retained for audit and was not
deleted.

## Remaining boundary

This checkpoint does not yet provide an outer ASUS 5.4 boot-v3/AVB wrapper
for the observation identity and does not test physical ramoops retention.
The next safe increment is an unsigned, clean-twin outer-wrapper composition
using the retained source-sealed kernel `4b30cfff…9495`, followed by offline
inspection of the exact 4 MiB ramoops reservation. Candidate admission,
signing, and physical execution remain separate decisions. Missing pstore
evidence must never be interpreted as proof that no crash occurred.

The complete repository checkpoint passes. A separate wrapper/admission
review is still required, so the recommendation remains **HOLD**.
