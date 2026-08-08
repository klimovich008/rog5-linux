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

## Production-shell follow-up

Starting repository SHA:
`36e2d42fff34bbce30168baa48ac149635a199ef`.

The original QEMU gate called `mount(2)` from a dedicated C PID 1. It proved
the kernel and server contract, but did not execute BusyBox `mount` or the
production diagnostic function. A shell-only regression could therefore pass
host mocks while remaining absent from full-system coverage.

The same boot now retains the direct probe, then invokes the pinned,
credential-free network-root BusyBox/musl runtime. The host extracts
`mount_network_root()` and its dependencies verbatim from the current
`initramfs/network-root-init`; the QEMU harness contains no copied NFS option
string. It renames the sole device-backed QEMU interface to `usb0`, supplies a
fixture-only exact UDC identity, and lets the production function perform the
real second mount and transport classification. The gate requires exactly one
stage 70 and one each of stages 75, 80, and 90, read-only NFS mount metadata,
and rejected writes. Stage 100 must remain absent because the intentionally
minimal mount-only kernel has no OverlayFS.

Hostile mutations now additionally reject removal of the C-to-shell handoff,
removal of the exact production-function invocation, and a copied NFS mount
implementation in the harness.

Focused evidence:

- production init unit/hostile suite: PASS;
- QEMU contract plus eight hostile mutations: PASS;
- prior direct-only QEMU gate: 1,288 ms;
- direct plus production-shell QEMU gate: 3,669 ms;
- added full-system coverage cost: 2,381 ms;
- Linux Image SHA-256:
  `d26eeb311aa7b12e1e6c98ee3ce4c1648dc1949d9e400aa22cdcbfa0490b2c19`.

No phone, fastboot/ADB operation, credential, signing key, GitHub mutation,
or phone storage was used. This remains board-neutral evidence and does not
prove USB/NCM continuity or the current successor on the phone.
