# Generation-8 host export proof — install verification

Date: 2026-08-03

Result: **PASS; host-only correction installed; no phone boot**.

## Reviewed checkpoint

Commit `dc2313f4db8905d7c8b1bc1a6d65d82df390f31b` records the consumed
Generation-8 lifecycle and replaces unprivileged export-table access with an
argument-free read-only operation in the fixed root broker. Complete local
`scripts/host/test-repository-linux.sh ci` passed. GitHub Actions run
`30836080889` passed `qemu-system` in 31 seconds and `recovery-core` in
3 minutes 29 seconds at that exact head.

The rejected alternative would have changed `/var/lib/nfs/etab` from mode
`0600` to `0644` after normal cleanup. Review identified that as a persistent
host-wide information and abnormal-exit defect. That approach was removed
before publication. The installed operation instead:

- accepts no caller argument or path;
- opens only `/var/lib/nfs/etab` read-only with `O_NOFOLLOW`;
- requires a root-owned regular mode-`0600` or mode-`0644` inode with one link
  and at most 1 MiB;
- completes the bounded descriptor read and revalidates the opened and named
  inode identity;
- accepts only an exact zero-byte table; and
- emits one canonical line without revealing table contents.

Hostile offline tests reject nonempty, mode-`0666`, hard-linked, symlinked,
missing, malformed-request, and noncanonical-response cases. A client/socket
test proves status framing is removed before the lifecycle compares the exact
proof line. The production-path test proves an unreadable unprivileged fixture
is not opened directly.

## Installation and real-host proof

The root installer completed and enabled the fixed operator socket. Installed
identities match the reviewed repository bytes:

- broker SHA-256
  `86b8cc62eaa3c08cbc512e596c8876b2871b83d603abd62f1913d34e06e656b1`;
- client SHA-256
  `ac0d8e8a498ae382a20a263eb7f610b80d5db9c18f1091c1fc4c055adc51a29c`;
- NFS server SHA-256
  `f316b1c706584c2d0ccfd311d56866dfcff0c1ba3d574658b261a1bc5b2c7e65`.

Two consecutive production `inspect` requests returned exactly
`PASS host NFS export table is empty`. Before and after inspection, the table
remained the same root-owned mode-`0600`, zero-byte, single-link inode. The
proof did not chmod, replace, truncate, export, or start NFS.

Independent post-install checks found:

- the root broker socket active and enabled as operator-owned mode `0600`;
- NFS server, rpcbind, and ModemManager inactive;
- no listener on the bounded NFS or mountd ports;
- no NFS-ready, server-state, or export-mount lifecycle marker;
- no active kernel NFS thread file; and
- the phone still in exact Alpine USB/NCM fallback at `169.254.77.1/30`.

No fastboot, recovery, ADB, SSH, credential, signing-key, payload-transfer,
phone-storage, or phone reboot action occurred during this correction or its
installation.

## Next boundary

Generation 8 remains consumed, absent from temporary-boot policy, and never
reusable. Before any Generation-9 issuance, add and hardware-free-test bounded
non-sensitive classification for the recovery ACM stability failure. The
classifier must report only exact product/interface/driver/location counts and
transition classes; it must not expose serials or raw USB text.
