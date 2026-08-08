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

## Server-read-only and OverlayFS follow-up

Starting repository SHA:
`a3cb1995d1b74c9b48f2cbd8841ed39692c435bc`.

The production-shell gate stopped at stage 90 because the minimal QEMU kernel
omitted OverlayFS and the in-memory export contained no executable init. It
therefore could not catch regressions between a verified read-only NFS lower
and the stage-100 merged root. The previous direct probe also requested a
read-only client mount, so its rejected write did not independently prove that
the NFS server enforced the export policy.

The minimal profile now includes built-in OverlayFS and tmpfs xattrs. A first
guest uses the same static PID 1 to seed an executable sentinel into the
volatile MEM export while it is writable. The host verifies ownership of the
sole TCP/2049 listener, reloads that exact Ganesha process with the static
read-only configuration, and starts the test guest. The test guest first
proves that its server-policy probe is mounted read-write yet receives exact
`EROFS` on create. It then retains the direct read-only mount and executes the
production function through stages 70, 75, 80, 90, and 100. The final checks
require an NFSv4.2 read-only lower, executable merged init, writable OverlayFS
root, a corresponding upper-file write, and no lower-root mutation.

The regression contract was added first and failed with:

`FAIL missing QEMU smoke source: tools/qemu-network-root-nfs/seed-init.sh`

Focused evidence:

- static contract: PASS, 290 ms;
- hostile mutation suite: PASS, 5,502 ms;
- clean Linux 7.1.4 kernel build: PASS, 395,827 ms;
- exact-state incremental rebuild: PASS, 18,625 ms;
- unchanged Linux Image SHA-256:
  `fe5c693ab264f4c8ac69b48c727851026d703c08e49cd277dfb4fbb8a879d0b6`;
- unchanged kernel configuration SHA-256:
  `87f73146614d64de55f8d7f07d2ada1aba63918e176b5d48e4cf3ca327e200d5`;
- prior stage-90 production-shell gate: PASS, 3,669 ms;
- server-read-only plus stage-100 gate: PASS, 6,529 ms.

Hostile mutations remove or corrupt each new invariant: exclusive listener
preflight and exact listener ownership, configuration reload, writable fixture
seed, seed-mode entry, server-read-only probe, client-RW proof, static-init
reuse, single QEMU invocation, stage 100, OverlayFS, and tmpfs xattrs.

No phone, fastboot/ADB operation, credential, signing key, GitHub mutation, or
phone storage was used. Generation 12 remains consumed and must never be
retried; the active successor remains unissued and has no boot authority.

## Production systemd and OpenSSH handoff follow-up

Date: 2026-08-09

Starting repository SHA:
`dafebf77592077133b14676d447d7974751199e2`.

The stage-100 gate still stopped at a sentinel merged init. It did not run the
production shutdown-root handoff, execute `switch_root`, reach systemd as PID
1, or prove OpenSSH over the assembled root. Several fixture incompatibilities
were exposed while closing that gap:

1. Ganesha's MEM backend returned `EIO` while reading the 198,968-byte systemd
   binary; its VFS backend requires real file handles and therefore a bounded
   privileged test container.
2. Linux NFSv4.2 `READ_PLUS` requests failed against Ganesha 4.3. The
   QEMU-only kernel profile now disables `CONFIG_NFS_V4_2_READ_PLUS`; this is
   not a broad target-kernel config cleanup.
3. Ganesha rejected optional `GET_DIR_DELEGATION`. The fixture pins
   `nfsv4.directory_delegations=0` and verifies the live module parameter.
4. String owner mapping made the NFS files appear non-root and caused sshd to
   reject `/usr/share/empty.sshd`. The server now requires numeric NFSv4
   owners, the client pins `nfs.nfs4_disable_idmapping=1`, and the guest
   verifies that policy before mounting.

The single test guest now validates the direct server read-only contract,
executes the production NFS/OverlayFS path through stage 100, verifies exact
systemd/loader/libc hashes, and calls the production
`prepare_shutdown_root()` and `handoff_network_root()` functions before
`switch_root`. Real ARM64 systemd becomes PID 1, real OpenSSH accepts one
disposable key-only command, and the terminal helper revalidates the exact
OverlayFS root, read-only NFS lower, tmpfs state, storage-isolation records,
upper write, and unchanged lower before powering QEMU off. The obsolete seed
guest is removed.

Regression evidence:

- red contract before integration: expected failure, 319 ms;
- sealed runtime archive SHA-256:
  `990689a5ebc0a3cdc16f9c6198bab3a9cc4531ead17ffe4ee0ad14c81c1aebde`;
- clean Linux 7.1.4 QEMU kernel build: PASS, 320,815 ms;
- kernel configuration SHA-256:
  `f4aa4a887ee3e42bb601988529cf2be82f0dcf0c85f1ffcd0659d9cc67a6b008`;
- Linux Image SHA-256:
  `ce35c6732a553a3931d67a2af4b74dfd9a61396620d0b15e00290ff20253ebcc`;
- focused static contract: PASS, 318 ms;
- 39 hostile mutations, including owner mapping, runtime hashes, live
  zero-block topology, terminal QEMU status, password-only rejection, and
  post-handoff topology: PASS, 11,149 ms with the static contract;
- prior server-read-only plus stage-100 QEMU gate: PASS, 6,529 ms;
- production systemd plus key-only OpenSSH QEMU gate after independent review:
  PASS, 12,309 ms;
- added end-to-end coverage cost: 5,780 ms;
- prior complete repository Linux `ci` checkpoint: PASS, 441,010 ms;
- pre-review complete repository Linux `ci`: PASS, 480,632 ms;
- final post-review complete repository Linux `ci`: PASS, 441,490 ms, an
  increase of 480 ms (0.1%) from the starting checkpoint.

Independent standards/spec review found and closed four missing assertions:
the runner now rejects a nonzero QEMU status even after terminal markers, the
terminal helper measures live block topology instead of trusting only the
handoff record, the hostile contract pins the semantic mount checks rather
than only their caller, and a disposable non-root account performs a real
password-only authentication attempt that must fail. The minimal kernel has
no `/sys/class/block` class; exact `ENOENT` is accepted as zero topology while
all other inspection failures and every listed device fail closed. The same
review corrected stale README wording that still described SSH as a stub.

No phone, fastboot/ADB operation, credential, signing key, GitHub mutation, or
phone storage was used. Generation 12 remains consumed and must never be
retried. The active stage-75/current-cycle-postmortem successor remains
unissued and has no boot authority.
