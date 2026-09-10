# Direct-clone systematic review

Generation 209 (`e2image`, 420 seconds) and Generation 211 (37 direct ranges,
840 seconds) both exhausted their clone bounds. Exact softdog fallback passed.
Generation 211 had no per-extent records, so a specific stalled range cannot be
distinguished from insufficient aggregate throughput.

The fixed map contains 1,850,654,720 bytes and splits without dividing an
extent:

- extents 1–19: 670,892,032 bytes;
- extent 20: 891,424,768 bytes;
- extents 21–37: 288,337,920 bytes.

Each extent overwrite is deterministic and idempotent. The next architecture
uses one one-use RAM-only candidate per fixed chunk, emits BEGIN/PASS for every
extent, syncs, relocks all 117 nodes, and returns exact fastboot. fsck, grow,
seal, and native-root verification run only after all three chunks pass.

Claude Opus could not run because the existing OAuth session had expired. No
credential was requested or supplied; the conclusion above is independently
derived from the sealed map and live timing evidence.
