# Dedicated-layout Stage-2 offline checkpoint

Date: 2026-08-15

Status: **PASS offline. Stage 2 is separately gated, unissued, unbooted, and
ineligible until Stage 1 succeeds and exact Alpine fallback is reproven. No
phone storage mutation ran.**

Starting repository SHA:
`fab451eb009eefac89d6b4cc10c729e8410c5d21`.

## Implemented boundary

The sealed RAM-only executor accepts only the exact post-Stage-1 LUN and GPT
geometry. It requires clean `rog5-linux` userdata, an unsigned/empty
`arch_root_a` partition, the exact refreshed 16-GiB source image, the exact
source ext4 identity, and the refreshed 37,738-entry tree. It then:

1. performs the complete source hash and tree verification while userdata and
   the source loop remain read-only;
2. checks battery and thermal limits after that scan;
3. proves and disarms the exact recovery timer before the first target write;
4. opens a write window containing only the parent disk and partition 24;
5. clones exactly 17,179,869,184 bytes and hashes exactly that target prefix;
6. changes only the cloned filesystem UUID, requires correction-free fsck,
   grows ext4 to 8,388,603 blocks, and requires another correction-free fsck;
7. verifies the cloned tree, atomically replaces only the excluded persistent
   seal, restores the exact sealed root-directory mtime, and verifies again;
8. relocks every physical node, mounts the native root `ro,noload`, verifies
   its on-disk seal/tree, and proves the GPT and userdata identities unchanged.

Failure records distinguish untouched, partial clone, complete clone,
native-filesystem mutation, and final states. Signal cleanup is non-reentrant;
every failure attempts unmount/detach followed by physical relock. The
executor contains no GPT mutation, mkfs, fastboot, flashing, or erase path.

## Defects found before publication

The first runtime fixture showed that atomic seal replacement changes the root
directory mtime, which participates in the tree hash. The production path now
restores the exact staging epoch before verifying the new seal.

A credential-free Claude Opus review found two independent fail-before-write
bugs, both reproduced and fixed:

- a missing shell continuation made every UUID comparison in `verify_ext4()`
  fail; and
- the helper initially required the `ROG5_ARCH_A` label even when checking
  userdata, whose retained exact label is `rog5-linux`.

The regression now executes the real production helper against an ext4
fixture and rejects wrong UUID, label, and block count. A final corrected-file
Opus review reported `NO BLOCKER`; its useful minor observations were also
applied by requiring correction-free fsck, rejecting a target/userdata UUID
collision, and disabling signal traps before failure cleanup.

The first GitHub run exposed one publication-only test defect: Git records
only the executable bit, so a fresh checkout materialized the tracked seal as
`0644` even though the local source copy was `0444`. The corrected regression
accepts a non-executable tracked source and separately requires the builder's
exact `install -m 0444` boundary. Inspection of the final archive confirms the
packaged seal is `0444`.

## Offline evidence

- focused source/collector tests: 12 unit tests plus the executable ext4
  fixture passed in 7.339 seconds;
- the complete repository Linux CI tier passed in 444.978 seconds;
- after the checkout-mode regression correction, the coherent focused set
  passed in 7.358 seconds and the complete repository Linux CI tier passed in
  429.811 seconds;
- final initramfs twins: 6,075,358 bytes each, byte-identical SHA-256
  `36202033676f8d5217e3426ba05a5818e9b8787b3bae4145e050eb78a3ad0ba2`;
- twin build elapsed time: 3.47 seconds;
- AArch64 runtime closure passed the static tree verifier, exact clone-prefix
  hash, UUID change, correction-free e2fsck, and ext4 grow sequence;
- the existing AArch64 storage-tool closure also passed against the final
  archive; and
- the sealed current-tree record is 430 bytes at SHA-256
  `8dbc66163adde6919d9e48974a035e1a3d27c8d0304befbc806cd284d167be68`.

The private config binds the retained disk/partition identities and target
UUID but is neither tracked nor disclosed. No wrapper, candidate, signature,
claim, or boot authority was created.

## Next boundary

Stage 1 still requires the operator's exact final confirmation. After its
single RAM-only execution, the unchanged Alpine fallback must prove strict
SSH, the new GPT, clean shrunken userdata, and empty partition 24. Only then
may Stage 2 be considered for a separate issuance and physical decision.
