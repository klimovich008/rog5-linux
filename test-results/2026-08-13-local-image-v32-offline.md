# Local-image v32 offline checkpoint

Date: 2026-08-13

Status: **offline PASS; no phone contact, candidate issuance, or boot occurred.**

This checkpoint prepares the first bounded local-root experiment: one new
16 GiB ext4 image inside fallback `userdata`, containing the existing
deployment-key-bound headless Arch root. The kernel, recovery, and target boot
remain RAM-only. The outer `userdata` filesystem and the inner image are both
mounted `ro,noload` by the target, with a tmpfs OverlayFS upper.

## Deterministic ext4 root

Two independent 16 GiB images were created sequentially on the host with the
exact signed Alpine 3.24 AArch64 `bsdtar 3.8.7` and a fixed ext4 UUID and hash
seed. Both passed full-tree verification and read-only `e2fsck`, and produced
identical release identities:

- tree entries: `37736`;
- regular files: `27604`;
- directories: `1902`;
- symbolic links: `8230`;
- bytes: `1625282905`;
- xattrs: `3`;
- tree SHA-256:
  `4701c23b93624bf894bb76331c165b650c9a2aecb99273a4e6d37c20ac3ef167`;
- seal SHA-256:
  `02231e86746fbc656090f52c96d7e0c968c7ca86ba7449c306f611ea20c6a876`;
- filesystem UUID: `598a876b-a8db-4859-a01a-1b864b0a87f4`;
- filesystem label: `ROG5_ARCH_A`.

Run 1 extracted in 25.408 seconds and sealed in 2.063 seconds. Run 2
extracted in 25.420 seconds and sealed in 2.217 seconds. The earlier failed
parallel rehearsal was a host tmpfs capacity failure, not a differing root
identity; its mounts and loop devices were absent and its disposable fixtures
were removed before these sequential runs.

The staging extractor is carried as a self-contained, volatile AArch64 runtime
rather than assuming its dynamic dependencies exist in Alpine fallback. Its
deterministic tar bundle is 7,526,400 bytes with SHA-256
`02cab6f4df503fbf279853535af09e57f472cfd463aeecb3f4d5c4c356115864`.
The stager pins the loader, `bsdtar`, every shared library, every relative
symlink, and the complete 20-entry runtime inventory before use.
A root-owned `/run` rehearsal on the PC passed every archive, verifier,
extractor, loader, shared-library, symlink, and runtime-directory check before
stopping at the expected non-phone boundary: `exact writable fallback userdata
root is absent`. The retained fallback's AArch64 `mkfs.ext4`, BusyBox `blkid`,
and read-only `e2fsck` dialects also passed under QEMU. This caught and fixed a
directory link-count assumption, one mistyped verifier digest, and unsupported
util-linux-only `losetup`/`blkid` options before phone staging.

## Boot-path corrections

Generation 52 reached `switch-root ENTER` but did not prove a completed mount
handoff. The successor now checks all seven moves (`userdata`, image root,
state, `dev`, `sys`, `proc`, and `run`), rolls back completed moves after any
failure, and treats a returned `switch_root` as terminal failure.

Offline review then caught a second fail-before-boot defect: publishing
`switch-root PASS` after moving `/proc`, `/dev`, and `/run` still referenced
their old paths. The corrected implementation caches the target boot ID,
writes the final record through `/newroot/run`, sends that record once, and
restores the old record path before any rollback report.

Focused results after both corrections:

- local-image stager contract: PASS in 57 ms;
- seven-mount handoff/rollback contract: PASS in 57 ms;
- image-backed initramfs contract: PASS in 2.789 seconds;
- 12 live-runner unit tests: PASS in 5 ms.

The final clean twin built in 1.138 and 1.134 seconds. Both initramfs artifacts
are byte-identical with SHA-256
`39f1d9a700d8c37cf434ef5d9608d0723571de807a7df0a3957d80be258066e4`.

The phone-side image has not been created. The exact unexpected `/root/usr`
cleanup boundary remains documented separately and no phone write is resumed
until that exact subtree is resolved.
