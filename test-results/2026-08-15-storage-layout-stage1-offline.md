# Dedicated-layout Stage-1 offline checkpoint

Date: 2026-08-15

Status: **PASS offline and read-only live refresh. The Stage-1 storage writer
is unissued and unbooted. No phone partition or filesystem mutation ran.**

Starting repository SHA:
`1cefd0842d39f0bdda59be4807439bc7b96d5e74`.

## Defects closed

- Diagnostic code existed only for read-only storage preflight; there was no
  fail-closed executor for the first dedicated-layout boundary. The new
  executor resolves one exact UFS LUN without a fixed `sdX` name, validates
  GPT/ext4 identity, backs up GPT, shrinks ext4 before changing GPT, verifies
  partitions 1–22, and relocks all physical nodes.
- A successful target backup could previously not be made a durable host
  prerequisite for mutation. The new raw ACM protocol binds operation ID,
  nonce, file order, length, per-file SHA-256, and set SHA-256. The host writes
  each object with no-follow/exclusive creation, fsyncs files and directories,
  revalidates USB identity, and only then sends the exact ACK.
- The normal recovery rollback timer was still armed during a potentially
  long ext4 shrink. Its 900-second expiry could intentionally reboot inside a
  destructive filesystem operation. Stage 1 now requires that exact initial
  window, then freezes, revalidates, and terminates the exact leased watchdog
  plus its one `sleep` child after the durable ACK and before the first write.
- Independent Claude Opus review found a signal race between `SIGSTOP` and
  setting the helper's resumable state. The state is now set first, so every
  interruption path can safely issue `SIGCONT`.

## Hostile and runtime checks

- Source/policy contract: four tests pass.
- Backup/ACK collector: seven tests pass, including wrong operation, wrong
  order, payload corruption, invalid GPT signatures, and existing output.
- Watchdog disarm executes against real harmless processes and passes the
  exact case while rejecting a stale start time and two timer children. The
  rejected multi-child process is confirmed resumed.
- Retained phone GPT input under a 4-KiB-sector loop produced a 5,632-byte
  `sgdisk` backup, 24,576-byte primary capture, and 20,480-byte secondary
  capture; `sgdisk -v` and host raw-signature validation pass.
- Exact-size disposable-disk timings: setup 110 ms; synthetic ext4 create and
  forced check 182 ms; shrink 452 ms; GPT split/reread/post-check 1,313 ms;
  fresh-GPT restore/reread/filesystem check 1,143 ms. The first direct
  `BLKRRPART` returned the expected loop-device `EBUSY`; the production
  `partprobe` fallback completed successfully.
- Final sealed initramfs twins were byte-identical in 3,489 ms at SHA-256
  `74f4ecc24de5686eea059d83d9a455cd83e8cca6ecd5bd406bd2d07c2a781bd4`
  and size 5,934,933 bytes. The AArch64 `sgdisk`, e2fsprogs, `partprobe`, and
  serial closure executes under QEMU.

## Read-only phone refresh

The connected device had already booted exact Alpine rather than remaining in
fastboot. Strict pinned SSH verified the accepted 5.4 kernel and an unattached
17,179,869,184-byte local image. `e2fsck -fn` passed, the filesystem was clean,
and a read-only loop mount reported `norecovery`.

- image SHA-256:
  `a51ee69000bcdf56b87ef0045d517fa60cffe92a21fba728e80fc37c4380b3ce`;
- current tree: 37,738 entries, SHA-256
  `c804445418eea694667f6529086d7eeaa8e4a82293c86c692e0ebc379fd28e38`;
- controlled marker SHA-256:
  `9581532937a6791a74d55f61fb23b324769a8f0baff576066dae21d6dd5abac3`;
- mount/loop residue: none; elapsed time: 34 seconds.

The old Generation-53 persistent seal remains exact provenance for the
original materialization, but the controlled marker means it is not a current
whole-tree claim. Stage 2 must bind the refreshed image and tree identities.

The guarded fallback preflight and `RESTART2("bootloader")` path then returned
one exact `lahaina` fastboot device on slot B. No candidate was signed, issued,
claimed, or booted.

## Next boundary

Run focused and full repository CI, publish the unissued checkpoint, and
present the exact private Stage-1 operation for final confirmation. Only after
that confirmation may a one-use RAM-only candidate shrink `userdata` and
create empty partition 24. Partition-24 cloning remains a separate Stage-2
decision after exact Alpine fallback proof.
