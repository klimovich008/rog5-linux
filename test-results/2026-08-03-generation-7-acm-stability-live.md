# Generation-7 ACM-stability rejection — live

Date: 2026-08-03

Result: **REJECTED safely and consumed before COMMIT**. The sole admitted
Generation-7 RAM-only recovery boot reached verified recovery ACM/NCM and the
one-transfer service sent the complete 46,163,787-byte signed diagnostic
bundle. Recovery control produced no output and no authenticated `PREPARED`
record. Independently, the diagnostic collector rejected after its fixed
120-second target-ACM stability deadline with zero frames. No durable commit
intent existed, `COMMIT_EXEC` was never sent, NFS never started, and no target
ran.

## Exact candidate

- profile: `headless-diagnostic-generation7-live-v1`
- AVB image SHA-256:
  `d3d4cdb99b3192ee68498b4cfa4ac7505c213e572b41a7aa35c2882e6a812901`
- unchanged raw recovery SHA-256:
  `f1a7c5ad6bf27d67d495b9149965f72abfa40359da69c6f4392cfa871356a4ce`
- signed diagnostic manifest SHA-256:
  `4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`
- connected checkpoint:
  `158a8ac39eb2f29c44983d66e916d4e823babdb5`, GitHub Actions run
  [`30815999859`](https://github.com/klimovich008/rog5-linux/actions/runs/30815999859)
- fastboot serial and private evidence directory: retained outside Git

## Live sequence

1. Local credential admission, exact fallback health, guarded bootloader
   entry, and the complete connected diagnostic preflight passed.
2. The AVB footer, `NONE` vbmeta structure, and exact 58,101,760-byte raw boot
   descriptor passed verification. Fastboot accepted the 100,663,296-byte
   image for one temporary RAM-only boot.
3. Recovery exposed the pinned ACM and NCM identities with rollback armed.
   The host anchored the physical USB location and started the receive-only
   diagnostic collector before any possible commit.
4. Recovery requested the signed bundle. The one-transfer server sent the
   831-byte manifest, 64-byte signature, Image, DTB, and initramfs, reporting
   exactly 46,163,787 bytes and successful network cleanup.
5. Recovery control returned no canonical output. The collector observed no
   target USB events or frames and rejected with `collector-preflight` because
   exact diagnostic ACM did not become stable before its deadline.
6. Because no `PREPARED` boundary was established, the lifecycle created no
   durable intent, did not start NFS, and did not execute the target.

## Rollback and host state

Anchored fallback-profile restoration passed, followed by strict-key SSH to
exact Alpine on the same USB port. The controller nevertheless returned a
cleanup failure. Its first pre-commit cleanup observation reported that the
deferred recovery interface retained an unexpected NetworkManager profile
association. After fallback was proved, the final cleanup loop observed clean
state but did not complete its required continuous dwell before the fixed
10-second deadline.

Independent read-only checks after controller exit found the canonical
`rog5-fallback-usb-ssh` profile active on the expected interface with only
`169.254.77.1/30`; no project process, NFS export, NFS/rpcbind listener,
lifecycle marker, or project TCP 8080 listener remained. The only TCP 8080
listener was the pre-existing Steam loopback process. The root broker socket
remained as its expected installed service endpoint. The phone stayed on exact
Alpine fallback.

No image was flashed; no partition was erased, formatted, mounted by the host,
or switched to another slot. No retry is permitted.

## Private evidence seals

| Record | SHA-256 |
| --- | --- |
| stable-recovery boot | `7e202f45a36c103ed9cf2b826ca6e3e69f5ed79b95adda36d2cd0a8817c89d08` |
| recovery USB anchor | `5d6aa43cfcb319524576ff1debe7ab1a1d5522214df1fdaf509e3432d2782d41` |
| bundle server | `9bdc6eb5732ad074b8aef5facbfe4c6c8baef8e48b59a09561213f2f1910edb7` |
| recovery control | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| diagnostic collector log | `970a479aed1fdd0484a0dfb540f567c36766918c294ddd37cddb2b598a1a3429` |
| diagnostic collector record | `98c747eae13f725be84d09f7e26c04a66bbc7725a99a29c052f48322634039cc` |
| fallback restoration | `8608f0478541424f17bca20c9ab7adb85ba3cbe7da7fb986457fb4c358a99658` |
| fallback strict-SSH proof | `c6432c9b31f985030290e137d4f9b3be42e32cb2636c4ef8960aa7f06e9bbe15` |
| fallback identity | `13266b1a1db1ccafc1c09f0446951b3359c75bbb52c61a3f24570730906c9287` |

## Disposition

Generation 7 is single-use and consumed. Its central-policy row is removed,
its inventory role is consumed/offline-only/never-retry-or-flash, and tests
require zero active temporary-boot rows and exact Generation-7 absence.

Before issuing a distinct successor, reproduce the cleanup deadline and
association behavior in hardware-free tests, preserve the strict physical-
port/profile/address/ownership checks, and obtain a passing complete local and
GitHub test suite. Increasing a timeout without explaining the observation
cost, weakening identity checks, or reusing Generation 7 is not acceptable.

The deadline failure was subsequently reproduced and corrected offline by
consolidating the firewalld snapshot while retaining the fixed timeout and all
identity/residue checks. See the
[cleanup snapshot correction](2026-08-03-generation-7-cleanup-snapshot-fix-offline.md).
This does not change the consumed live result or authorize a retry.
