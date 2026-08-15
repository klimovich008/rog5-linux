# Dedicated Linux exact-command rehearsal

Date: 2026-08-15

Repository checkpoint: `47e595a28c2a2d628b7f7c24a12fbdde8eecd516`

Phone contact or storage mutation: none

## Result

The private Phase-1 backup was re-hashed and restored into seven disposable
sparse GPT images. All 14 GPT ranges, 107 protected partition images,
4,601,434,112 bytes, and seven GPT restorations passed in 5.612 seconds.

The first command-level rehearsal intentionally used the proposed `sgdisk`
transaction without an explicit alignment override. It failed the exact-start
postcondition: the requested existing `userdata` start at LBA 2,352,680 was
silently moved to LBA 2,351,104.

The corrected transaction added `--set-alignment=1` before deleting and
recreating partition 23. It then passed all exact postconditions:

```text
EXACT_GPT_COMMAND_REHEARSAL=PASS
userdata_first_lba=2352680
userdata_last_lba=53477375
arch_root_first_lba=53477376
arch_root_last_lba=61865978
attributes=0000000000000000
```

The disk GUID, existing partition type and unique GUID, and newly generated
partition/filesystem UUIDs were used during the rehearsal but remain only in
the private confirmation record. The command test used a user-owned sparse GPT
file with compensated 512-byte host geometry because this session had no
cached `sudo` elevation. The earlier disposable-loop rehearsal remains the
proof for the phone's exact 4,096-byte logical-sector geometry.

## Checkpoint tests

- focused Generation 20 profile: passed in 0.160 seconds;
- focused Generation 21 profile: passed in 0.137 seconds;
- full local `scripts/host/test-repository-linux.sh ci`: passed at exact
  `47e595a28c2a2d628b7f7c24a12fbdde8eecd516` in 431.457 seconds; and
- GitHub exact-head, merge-compat, QEMU-system, and candidate-publication jobs:
  passed in [run 31860137026](https://github.com/klimovich008/rog5-linux/actions/runs/31860137026).

The operation remains unexecuted on the phone and still requires the final
operator confirmation.
