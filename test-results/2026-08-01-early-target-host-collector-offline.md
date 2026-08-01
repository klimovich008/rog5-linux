# Early-target host collector

Date: 2026-08-01

Status: **PASS hardware-free; phone capture pending**

## Result

The receive-only host collector for `headless-netroot-early-diag-v1` is now
implemented and wired into both repository test tiers. It starts a bounded
kernel-journal reader before target enumeration, admits exactly one literal
diagnostic USB product and interface `02` `cdc_acm` character device on the
recovery anchor's physical port, and feeds target bytes into the existing
canonical netstring/state validator.

The tty opens with `O_RDONLY`, raw/no-echo/no-`HUPCL` settings, `flock`, and
`TIOCEXCL`. The collector has no serial write method or shell execution path.
The opened character-device number is verified, so a later sysfs disappearance
is classified through descriptor EOF/`EIO` instead of a path race.

Every accepted frame receives host realtime and monotonic timestamps. Matching
USB, `cdc_acm`, and `cdc_ncm` kernel events are ASCII-sanitized, serial-number
lines are excluded, and frame, event, line, time, and complete evidence sizes
are bounded. Exactly one exclusive mode-`0600` canonical JSON file is written
outside the repository. A rejected stream retains only previously validated
records and a bounded reason; raw malformed bytes are never persisted.

## Tests

`scripts/host/test-collect-early-target-diagnostics.py` passes twenty-one cases:

- canonical, fresh, caller-private, host-bound recovery anchor handling;
- new caller-private evidence output outside Git;
- one exact product, ACM interface, physical port, device number, interface
  number, and `cdc_acm` driver;
- rejection when `fuser` reports any holder other than the collector process;
- read-only exclusive raw/no-echo/no-`HUPCL` tty behavior with PTY proof that
  writes fail with `EBADF`;
- timeout/disconnect distinction and timestamps only on validated frames;
- malformed and truncated stream rejection without raw-byte retention, with a
  valid prefix retained identically for split and coalesced input;
- bounded matching USB events with serial-line exclusion, aggregate-burst-safe
  buffering, pre-enumeration retention, and a final disconnect drain;
- preservation of successful and rejected frame prefixes if the final drain
  also fails;
- canonical mode-`0600` evidence and no-replace publication; and
- kernel-reader-before-enumeration ordering with exactly one output.

The deterministic suite executes the real subprocess, nonblocking pipe,
buffering, poll, termination, and wait path through a fixture executable. The
real `/usr/bin/journalctl --dmesg` reader also starts, polls, and stops as the
current unprivileged user. The existing parser/reporter suite remains green.
The complete `scripts/host/test-repository-linux.sh ci` tier passes
with the collector test in sequence, including the full-system ARM64 systemd,
core source/DTB, recovery protocol, rollback, and packaging gates.

No phone, fastboot, ADB, SSH credential, signing key, NFS export, firewall,
phone storage, or privileged host action was used. This result does not prove
that the diagnostic product enumerates or that any target stage is emitted on
the ROG Phone 5.
