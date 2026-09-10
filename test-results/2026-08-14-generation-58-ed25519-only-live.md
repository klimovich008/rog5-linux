# Generation 58 Ed25519-only local-image live result

Date: 2026-08-14

Result: **PASS. The sole RAM-only Generation 58 cycle reached exact read-only
UFS, local-image Arch Linux, systemd, and strict key-only SSH in 333.446
seconds, then returned to the exact Alpine fallback. Generation 58 is consumed
and must never be retried or flashed.**

The cycle ran from exact repository head
`81fe323c8dbdc98576cc95a5bd5cf3e6af0ac4de`. The target boot ID was
`48458874-82c7-4db7-81d8-9b6d3c611e9c`. Runtime attestation passed at target
uptime 250.80 seconds with:

- Linux `7.1.4-gae717d919f87`;
- 116 physical UFS block nodes and exact userdata `/dev/sda23`;
- userdata and the 16 GiB local image both mounted `ro,noload`;
- a tmpfs-backed OverlayFS root;
- zero blocked block queries, blocked SCSI commands, journal-recovery events,
  and UFS error events;
- zero backlights; and
- strict key-only SSH.

The host-observed target stages advanced from `ufs-ready` to successful
`switch_root` in 20.286 seconds. The temporary recovery fastboot transfer and
boot completed in 12.768 seconds. No flash, slot, partition, erase, format, or
phone-storage write operation occurred.

## Host-key result and timing

The intended change passed exactly:

- stock `sshdgenkeys.service` was masked and inactive;
- `rog5-sshd-ed25519-key.service` completed in 28 ms;
- only `ssh_host_ed25519_key` mode 0600 and its public key mode 0644 existed;
- sshd required the replacement service and reached the strict key-only host
  pin; and
- no private host-key contents were captured.

`systemd-analyze time` reported 46.235 seconds in the kernel and 3 minutes
6.094 seconds in userspace, totaling 3 minutes 52.330 seconds. The key change
removed Generation 57's 38.212-second three-algorithm generator and moved sshd
start from 2 minutes 27.965 seconds to 2 minutes 9.867 seconds, about 18 seconds
earlier.

End-to-end acceptance was nevertheless 27.518 seconds slower than Generation
57's 305.928 seconds. This run had larger unrelated timings, notably:

- `dev-loop0.device`: 1 minute 2.909 seconds versus 41.238 seconds;
- `dbus-broker.service`: 44.781 seconds versus 28.814 seconds;
- `rog5-p2-ready.service`: 40.363 seconds versus 21.727 seconds; and
- `sshd.service`: 15.861 seconds versus 9.991 seconds.

Device-unit blame is not itself proof of serialized critical-path work. The
evidence proves the narrow host-key optimization, but it does not establish an
overall boot-time improvement.

## Fallback and independent evidence

Normal systemd reboot returned Alpine with boot ID
`6f5a4082-85fb-4672-94e0-eb47f71c07a8` on the exact original USB port.
Fallback evidence reported:

- maximum temperature: 44.1 C;
- PMIC reset trigger/type: `PS_HOLD` / `HARD_RESET`;
- PMIC watchdog signal: absent;
- fatal tokens: zero; and
- pstore: unavailable with zero records.

Unavailable pstore is inconclusive and is not evidence that a crash could not
have occurred. The accepted target path and explicit systemd reboot provide
positive success evidence for this cycle. The durable intent resolved exactly
to `TARGET_ACCEPTED`; fallback profile restoration and host cleanup passed.
The temporarily stopped Steam web-debug socket was restored enabled, active,
and listening on TCP/8081.

## Publication validation

Focused consumed-state checks passed:

- current Generation 58 profile: 11.025 seconds;
- stable live gate: 4.543 seconds;
- persistent-root live-runner unit suite: 0.128 seconds;
- executor contract: 0.086 seconds;
- retention-cycle admission matrix: 3.279 seconds;
- compatibility oracle: 0.516 seconds;
- source/DTB oracle: 11.612 seconds; and
- recovery policy: 0.495 seconds.

The first full-suite checkpoint stopped after 124.529 seconds on the expected
stale artifact-manifest hash exposed by changing Generation 58 from admitted
to consumed. A second run stopped after 244.180 seconds on a stale three-image
allow-count assertion. A third run stopped after 281.438 seconds on the same
stale observer/core/Generation58 label in profile tests. Each failure was
corrected with the exact new hash or two-image observer/core count. The final
`scripts/host/test-repository-linux.sh ci` publication run passed in 460.964
seconds.

Private raw evidence remains outside Git at
`/home/deck/.local/state/rog5-generation58-ed25519-live-20260814.o5X2fQOn`.
No key material or private dump is copied into the repository.
