# Generation-5 NFS-readiness lifecycle — live

Date: 2026-08-03

Result: **REJECTED safely and consumed**. The sole admitted Generation-5
RAM-only recovery boot reached verified ACM/NCM, returned `PREPARED`, and
transferred the complete 46,163,787-byte signed bundle. The exact NFSv4.2
listener was not ready before the pre-COMMIT gate, so `COMMIT_EXEC` was never
sent, `execution_started` remained `NO`, and no target ran.

## Exact candidate

- profile: `headless-diagnostic-generation5-live-v1`
- AVB image SHA-256:
  `abe4501f9a5fb2892d30d425c9498556cab84ab8c9557c18aba5ae4caf5beb1a`
- unchanged raw recovery SHA-256:
  `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce`
- signed diagnostic manifest SHA-256:
  `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`
- recovery trust-root SHA-256:
  `f10ca0762e51a3d606a9a11422c55e8447e6bad2021cb9f3aca5ba69ef17c57b`
- host verifier SHA-256:
  `0a5708053725c2eea2637b3df2432c22dcda02313280abd17cc3d0b61855b621`
- fastboot serial and private evidence paths: retained outside Git

The exact connected preflight checkpoint was commit `3e7ff47`. GitHub Actions
run `30799181863` passed `qemu-system` in 1 minute 13 seconds and
`recovery-core` in 3 minutes 38 seconds before the live action.

## Live sequence

The guarded lifecycle executed exactly once, with no image retry:

1. The AVB footer, `NONE` vbmeta structure, and exact 58,101,760-byte boot
   descriptor passed verification.
2. Fastboot accepted the 100,663,296-byte RAM-only image. Recovery exposed
   ACM and NCM at the pinned physical USB location with rollback armed.
3. Recovery returned one authenticated `PREPARED` record. Its postmortem was
   empty, its watchdog was armed, and `execution_started=NO`.
4. The one-transfer host server sent the exact manifest, signature, Image,
   DTB, and initramfs: 46,163,787 bytes in total.
5. Recovery control failed with `exact network-root NFSv4.2 listener was not
   ready before COMMIT`. The host had no NFS listener and therefore did not
   send COMMIT or execute the target.

The bundle log proves byte progress, not the server's independent completion
receipt or successful cleanup. The root controller remained active until its
fixed 205-second watchdog. This preserves the important boundary: all bundle
bytes reached the transport, but the handoff from one-transfer completion to
NFS startup still did not complete in time.

## Rollback and cleanup

The lifecycle's first fallback-profile restoration failed closed because the
bundle controller still held its exclusive lock. Its first cleanup observation
also rejected the shared `169.254.77.1/30` address while it remained outside
the exact managed fallback profile. A non-root `kill -0` probe was briefly
misclassified as process exit because it could not signal the root process;
subsequent checks used process-table presence and observed the controller exit
after its watchdog.

After that exit, one fixed restoration request used the captured physical USB
anchor and restored `rog5-fallback-usb-ssh`. The exact Alpine fallback then
passed strict SSH with the dedicated client key and pinned host key. Final
checks proved:

- the 37,735-entry installed network root and diagnostic bundle still pass
  their root-owned preflights;
- no project listener remains on the bundle, NFS, or rpcbind ports;
- no lifecycle marker, export, mount, or kernel NFS thread remains; and
- the exact fallback NCM interface is NetworkManager-managed, carries only
  `169.254.77.1/30`, and is not in the lifecycle drop zone.

No image was flashed; no partition was erased, formatted, mounted, or written;
no slot changed; and no target-side action ran.

## Disposition

Generation 5 is single-use and consumed. Its central-policy `allow` row is
removed, its inventory role is consumed/offline-only/never-retry-or-flash,
and policy tests require its absence. The exact image must not be retried or
flashed.

Before issuing a distinct successor, the next host-side test and correction
must explain why a complete byte transfer did not produce the independent
completion receipt and NFS listener while preserving the fixed deadline
lattice. Increasing a timeout alone is not an adequate correction.

## Published verification

Complete local repository CI passed after the consumption transition. The
exact consumed-state commit `be80019` then passed GitHub Actions run
[`30800728102`](https://github.com/klimovich008/rog5-linux/actions/runs/30800728102):
`qemu-system` completed in 1 minute 14 seconds and `recovery-core` completed in
3 minutes 10 seconds.
