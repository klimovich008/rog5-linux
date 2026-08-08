# QEMU network-root NFSv4.2 gate

Date: 2026-08-08

Starting repository SHA:
`8eb493dd68a2e3fc0e32cf2bca52f47d8a8681bd`.

## Defect

The board-neutral full-system kernel gate proved initramfs and real-systemd
handoff, but its minimal Linux 7.1.4 configuration lacked the built-in IP
autoconfiguration, NFSv4.2 client, SUNRPC, root-NFS, and virtio-net features
needed to exercise the active network-root mount boundary. A regression could
therefore reach phone stage 70 without any preceding real Linux NFS client
test.

## Correction

- The QEMU kernel profile now requires the missing built-in networking and
  NFS client options through the existing exact-state build contract.
- A static AArch64 PID 1 mounts `169.254.77.1:/` with the option string
  extracted and compared against `initramfs/network-root-init`.
- QEMU assigns the exact `169.254.77.2/30` client identity. User networking
  remains restricted and exposes only one explicit guest TCP/2049 forward.
- NFS-Ganesha 4.3 uses its rootless in-memory FSAL, NFSv4.2, TCP, and a
  read-only export. The guest verifies NFS mount metadata and that create is
  rejected with `EROFS`.
- Five hostile mutations prove fail-closed classification for option drift,
  writable export drift, a privilege-dependent VFS backend, missing network
  isolation, and a removed read-only enforcement check.

The direct `mount(2)` fixture appends only `addr=169.254.77.1`, which is the
numeric-source resolution field normally supplied by `mount.nfs`; the
operator-visible production option string remains exact and is checked
directly against the initramfs source.

## Focused evidence

- Static contract: PASS, 248 ms.
- Five hostile mutations: PASS, 1,276 ms.
- Exact-state incremental QEMU kernel build: PASS, 20,669 ms.
- Linux 7.1.4 Image SHA-256:
  `d26eeb311aa7b12e1e6c98ee3ce4c1648dc1949d9e400aa22cdcbfa0490b2c19`.
- Kernel configuration SHA-256:
  `658cc1693fe797cb9f25f3b3fb4a36cd0402c9d8ad5af30d41971df732cfc219`.
- Existing initramfs and real-systemd/OpenSSH QEMU gates: PASS, 32,371 ms
  including ephemeral dependency installation.
- New rootless NFSv4.2 gate: PASS, 11,720 ms including ephemeral dependency
  installation.

No phone, fastboot/ADB operation, credential, signing key, GitHub mutation,
or phone storage was used. The active stage-75 v2 candidate remains unissued,
offline-only, and without boot authority. Generation 12 remains consumed and
must never be retried.
