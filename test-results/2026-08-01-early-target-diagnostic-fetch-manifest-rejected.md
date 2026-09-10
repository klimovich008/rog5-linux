# Early-target diagnostic manifest rejection

Date: 2026-08-01

Result: **rejected deterministically during manifest validation before full
bundle transfer, `PREPARE`, intent creation, NFS, `COMMIT_EXEC`, or target
execution; watchdog rollback and exact same-port Alpine proof passed.**

## Live boundary

The branch was clean and synchronized. Local and GitHub recovery CI, installed
controller/server hashes, the sole-bundle unchanged-atime preflight, the
37,735-entry NFS preflight, deployment-key admission, exact `lahaina` fastboot
gate, and complete diagnostic lifecycle preflight passed. A fresh private
evidence directory was used.

The one-shot lifecycle temporarily booted production recovery SHA-256
`9c060a27f21f6f99ca0c00cd1ff2ed9532220d585cd726b194f8b6d04e6204ef`.
Recovery NCM/ACM anchored to the expected USB port and the receive-only
diagnostic collector became ready. The server accepted the exact request and
sent the response header plus manifest, after which recovery closed the
connection and returned:

```text
FAIL recovery refused PREPARE result=FETCH_FAILED state=IDLE last_error=FETCH_MANIFEST
```

The host server consequently reported `response send failed`. No signature,
kernel, DTB, or initramfs transfer completed. Recovery control never accepted
`PREPARE`; no durable intent, NFS server, `COMMIT_EXEC`, target kexec, or target
diagnostic frame existed. The failed execution request was not retried.

## Cause

The signed 831-byte diagnostic manifest has SHA-256
`4eacb90f08a80af1bdfed704c4a5e0d8eff600e94191c18c066b23b1228f7e76`.
It correctly binds `diagnostic-initramfs-v1` to the admitted Arch tuple:
nonzero command-manifest/tree/seal hashes, generation `arch-a`, 37,735 entries,
and subtree `/`.

The repository contract, packager, host server, native bundle verifier, and
generated target cmdline all require that tuple for both
`network-root-v1` and `diagnostic-initramfs-v1`. Only
`rog5-bundle-fetch.c` classified the diagnostic profile with
`persistent-root-ro-v1` and required zero hashes, generation `none`, zero
entries, and subtree `none`. Its sandboxed worker therefore exited 50,
reported as `FETCH_MANIFEST`.

A new native integration test uses the live profile/trust shape. It fails with
exit 50 before the correction, passes after the fetcher places diagnostic and
network-root in the same branch, and rejects each partial zero/`none` mutation.
A separate persistent-root regression accepts the canonical unset tuple at 300
seconds and rejects both carried root trust and a 299-second rollback. The
complete 30-test native fetch suite, the same 30 tests under root-isolated
credential-drop/chroot/seccomp/parent-death conditions, 25 executable
AArch64/QEMU cases with five expected native-only skips, candidate integration,
and repository Linux CI tier pass.

## Host cleanup observation

The fixed 75-second host watchdog removed the server, listener, firewall
rules, and controller process. During cleanup, the controller explicitly
reactivated `rog5-fallback-usb-ssh` while the device still identified as
`ROG5_recovery`; the lifecycle correctly rejected that escaped shared `/30`.
An attempted in-controller deferral was rejected during review because the
short-lived controller could not guarantee a later completer and udev query
failure would reopen the race. That speculative change is not retained. The
secondary cleanup race remains a separate HOLD for a bounded lifecycle-level
design; it does not change the deterministic fetcher cause or rollback result.

## Rollback and evidence

The recovery watchdog disconnected the recovery gadget and Alpine returned on
the same physical USB location. Strict SSH accepted kernel
`5.4.134-qgki-perf-00001-g6c308144c23e`, new boot ID
`5f2c72dc-9206-4c3f-bc8a-d66ca9769f32`, maximum observed temperature 43.5 C,
and signed result `PASS`. No project process, TCP 111/2049/8080 listener, NFS
marker/mount/state, or fastboot device remained. The normal fallback profile
was active, the operator socket was active, and SteamOS read-only mode was
enabled.

Private evidence remains outside Git. Its public SHA-256 inventory is:

| Evidence | SHA-256 |
|---|---|
| `stable-recovery-boot.log` | `59c21f1a1677a5bc3410976b99a9a3fa667a0c35e7ce7074853200fcc03ed310` |
| `recovery-usb.anchor` | `28fbd6aff384cd3a5a25bbac1bef331c4afa25db612af43783459b599c6253c3` |
| `recovery-usb-anchor.log` | `017ec9cd2b1ebb5e62d411e0035375d1fd67ec453b28f1a72e987b106c70bfb4` |
| `bundle-server.log` | `73a455d189ea90c432ca518cc9d689b59ad6bfe2345082fe2f3c203ffeb8385a` |
| `recovery-control.log` | `5a5eb566e9e4bb09967d4916310eec5acb499d8235ab9a46e176fc44a8d19e99` |
| `early-target-diagnostics.log` | `860714e24102606aee7dc40637e7bbd620d1d7f3743f018657cb9db56178f088` |
| `fallback-identity.record` | `d14f334c337d8c541e43d7b800db2e7cb0b88b788cc02b21b185612d3707c827` |

The used recovery wrapper is consumed and removed from
`manifests/temporary-boot-images.tsv`; it must never be retried or flashed.
Because no `COMMIT_EXEC` existed, the diagnostic target bundle remains
unexecuted. A later lifecycle requires a fresh corrected twin-built and
production-signed recovery wrapper, complete review/CI, installation, exact
connected preflight, and a new evidence directory.
