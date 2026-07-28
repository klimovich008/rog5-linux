# Stable recovery control reference offline result

Date: 2026-07-28

Result: **PASS OFFLINE; NO LIVE AUTHORITY**

The test-first protocol oracle for replacing the interactive recovery shell
is implemented in `tools/recovery_control/reference.py`. Its focused suite is
`scripts/host/test-recovery-control-reference.py`. Neither file is included in
an initramfs, and this checkpoint does not create a bootable image.

## Covered behavior

The 45 focused tests cover:

- bounded netstring framing, every split point, coalesced frames, terminal
  parse failures, truncated input, and per-read/per-feed limits;
- canonical ASCII records, fixed verbs and fields, body hashes, reserved
  sentinels, and result/verb/state consistency;
- device-minted sessions, request replay and conflict handling, one prepared
  bundle per session, and a non-evicting bounded replay ledger;
- atomic commit identity, persisted commit fingerprints and execution-started
  markers, and at-most-once execution across simulated responder crashes;
- failures before claim, after claim, after response, after execution starts,
  on executor exception, and when execution returns unexpectedly;
- session-keyed host write-ahead intent, immutable outcomes, private
  owner-only records, atomic publication, directory durability, and fail-safe
  recovery at each injected write boundary; and
- thread/process controller races, symlink rejection, record tampering,
  duplicate JSON fields, and path replacement after the ledger directory is
  opened.

Independent review found and closed replay-eviction, concurrent host-intent,
transaction-correlation, restart, snapshot-validation, sentinel-collision,
terminal-state, and response-consistency defects before this result.

## Commands

```text
python3 scripts/host/test-recovery-control-reference.py
scripts/host/test-repository-linux.sh quick
git diff --check
```

All pass at this checkpoint.

## Boundary

No phone was booted, rebooted, or flashed. No signing key or other credential
was created or used. The accepted v18 staging image remains unchanged, and
legacy shell-based payload execution remains prohibited.

The next implementation step is a small static native responder plus
pseudo-terminal disconnect/restart tests. Signed bundle, DTB, size/hash, path,
and command-line mutation tests must pass before recovery is rebuilt or any
new live cycle is proposed.
