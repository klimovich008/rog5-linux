# Generation 74 read-only storage-preflight live result

Date: 2026-08-15

Candidate source checkpoint: `b8f6e9f39f55d7741c0b9122e1ef59b6148836f4`

Host execution checkpoint: `b2868af1d01c3397a204e6e46cbcb345f626645b`

Phone storage mutation: none

## Result

Generation 74 is consumed and revoked. Its one sealed RAM-only boot reached
the exact recovery USB product on the expected physical port and repeatedly
emitted one canonical PASS report:

```text
status=PASS
stage=S99_COMPLETE
logical_block_bytes=4096
lun_bytes=253403070464
gpt_entries=32
userdata_first_lba=2352680
userdata_last_lba=61865978
userdata_blocks=59513299
ext4_blocks=59513299
ext4_minimum_blocks=11698467
proposed_userdata_last_lba=53477375
proposed_root_first_lba=53477376
proposed_root_last_lba=61865978
sgdisk=1.0.10
e2fsprogs=1.47.4
all_read_only=1
block_mounts=0
```

The result proves read-only UFS topology, GPT geometry, clean ext4 inspection,
and a current minimum of 47,916,920,832 bytes. At the rehearsed 51,124,000
block pre-shrink point, measured headroom is 161,486,983,168 bytes.

## Host framing defect

Fastboot accepted the exact 100,663,296-byte image
`4f7343b1701002dfeab327e6d1110c2d77ea9671cfa033e786f7aa591439d9ca`
in 12.843 seconds. The first recovery-anchor listener failed during the
fastboot-to-recovery transition, but the recovery product then remained
stable and a fresh anchor passed on the same boot.

The admitted collector read 8,190 bytes from ACM in one operation and applied
its 2,048-byte bound before splitting complete lines. A bounded receive-only
sample contained 19 complete byte-identical 424-byte PASS frames plus the
134-byte prefix of the next frame. The target report was therefore valid; the
host collector's aggregate-before-framing check was wrong. The correction
now bounds each frame, accepts only byte-identical persistent terminal
repetitions and a valid partial prefix, and rejects changed repetitions and
oversized unframed input. All 23 focused collector tests pass.

Because that correction was not the collector hash admitted by Generation
74, the same-boot sample is retained as derived postmortem evidence rather
than relabeled as the original admitted JSON capture.

## Rollback and postmortem

Recovery disconnected intentionally at 04:17:10, approximately 178 seconds
after enumeration. Exact Alpine fallback returned on the same USB location 18
seconds later. Its signed identity passed at a 44.1 C maximum temperature.

The signed bounded postmortem reports pstore unavailable, so crash absence is
inconclusive. PMIC PON evidence is exact: `PS_HOLD`, `HARD_RESET`, and watchdog
signal absent. No fatal token or correlated lineage record was available.
This is consistent with the reviewed recovery rollback path and supplies no
evidence of a watchdog reset.

The exact claim exists in both entered locations and the source record is
gone. The policy row is revoked. Generation 74 must never be retried or
flashed.
