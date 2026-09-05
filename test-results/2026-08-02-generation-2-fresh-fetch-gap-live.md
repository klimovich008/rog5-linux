# Generation-2 fresh-fetch gap: safe live result

Date: 2026-08-02

## Outcome

The sole generation-2 RAM-only recovery boot reached the framed recovery
responder and returned a correlated `PREPARED` response, but the host's exact
one-transfer HTTP server never reported a completed transfer. The NFSv4.2
handoff therefore remained absent and host control failed before
`COMMIT_EXEC`.

No commit intent was armed, no target kexec was executed, no diagnostic target
frame arrived, and no phone storage was mounted or written. The recovery
watchdog rebooted to the untouched Alpine fallback. The host restored the
exact fallback NetworkManager profile and proved the pinned same-port Alpine
identity over strict SSH.

Generation-2 AVB `70fd77f7f0225d1fe9cce54111d378002b1c8c8a0d1d59c581b4d4ef9bfc72b1`
is consumed and removed from temporary-boot admission. It must never be
booted again or flashed.

## Exact evidence

- Fastboot verified and accepted exactly one temporary boot of the pinned
  96 MiB AVB wrapper.
- Recovery enumerated as the exact NCM/ACM product on the pinned physical USB
  path and kept rollback armed.
- The receive-only diagnostic collector reached `READY`.
- The host bundle server reached its unique
  `169.254.77.1:8080` ready state for
  `headless-netroot-early-diag-v1` and the exact manifest, but emitted no
  transfer-complete marker.
- Host control terminated with
  `exact network-root NFSv4.2 listener was not ready before COMMIT`.
- Alpine returned on the same physical USB path. Exact profile restoration
  and strict-SSH fallback proof passed.
- Post-run host inspection found no active NFS export, nfsd thread state,
  project listener, or project controller process.

Private logs and identity records remain outside Git under the operator-owned
generation-2 evidence directory.

## Offline classification

The exact booted ramdisk was re-extracted from the retained raw wrapper. Its
SHA-256 is `fec72c4dba62a24ced899af4d4fc3d0af3b7b691ea6f6c1bcf90c7aaf181c57a`,
matching the pinned source archive. The archive contains `/run` but no target
bundle, and the wrapper configuration has `CONFIG_TMPFS=y`.

At this revision, the fetcher had two success paths: complete one network
transfer, or accept an already-valid final bundle in `/run/rog5-bundles`.
Only the second code path could return success without completing the live
host transfer. The vanished RAM state prevents proving that it was actually
taken, so the precise live cause remains classified as an unevidenced
freshness gap rather than asserted as fact.

The lifecycle fixture also encoded the wrong dependency: mock control created
the bundle-consumed event directly, masking the requirement that a real
PREPARE must drive the host transfer.

## Required correction before generation 3

1. Make a successful tmpfs mount at `/run` mandatory before exposing USB.
2. Reject every pre-existing final bundle on the first fetch; responder state,
   not bundle-cache reuse, remains the same-request replay mechanism.
3. Model PREPARE as the cause of bundle transfer in the lifecycle fixture and
   prove that a cache-like PREPARED path cannot start NFS or COMMIT.
4. Stabilize host cleanup observations across transient USB identity races.
5. Pass focused tests, complete local CI, independent review, and GitHub CI
   before issuing a distinct generation-3 wrapper.

No generation-3 phone boot is authorized by this result.
