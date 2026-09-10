# Generation 104 probe-writer live result

Date: 2026-08-23

Result: **CONSUMED; WRITE OUTCOME AMBIGUOUS.** Generation 104 must never be
retried or flashed.

The signed transfer, PREPARE, and COMMIT passed. The exact historical
Generation-64 bounded-write Image/DTB/UFS lineage exposed `ROG5 persistent
root` NCM from 08:12:43 to 08:12:57, then stock slot A returned at 08:13:15.
That 14-second shape matches the known probe-write, relock, read-only remount,
root verification, and later aggregate UFS-health rollback path.

The host stage-listener command started after target departure, so no stage
frame or current writer boot ID was retained. The candidate is therefore
permanently consumed with an ambiguous write outcome; timing is not promoted
to proof.

The freshly staged Arch image was independently verified to contain no probe
before this sole writer. A read-only successor can therefore discriminate the
outcome without another write: require exact probe metadata, format, image
UUID, exactly one canonical producer UUID distinct from the current boot, and
all normal storage relock and root-seal checks. This is narrower than retrying
the writer and preserves at-most-once execution.
