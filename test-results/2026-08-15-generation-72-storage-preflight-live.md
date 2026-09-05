# Generation 72 read-only storage preflight

Generation 72 was entered once on 2026-08-15 and is irreversibly consumed. It
must never be retried.

The temporary RAM-only boot reached the exact `ROG5 recovery` USB product on
the anchored port. Recovery enumerated 4.595 seconds after fastboot
disconnected, remained present for 12.557 seconds, and then followed its fixed
rollback path. Exact Alpine fallback enumerated 18.162 seconds later.

The pre-armed receive-only collector opened the exact recovery ACM interface
but rejected its first newline-terminated payload as `storage-preflight report
shape is not exact`. Generation 72 did not retain the rejected bytes, so no
storage stage or terminal reason can be trusted retrospectively.

Fallback was the expected Alpine kernel, init, compatible, and ext4 root. It
contained no pstore records and no exact fatal kernel signature. The last
complete PMIC cycle was `PS_HOLD` / `HARD_RESET` with no watchdog signal. This
matches the recovery's intentional ten-second failure-visibility rollback; an
empty pstore result remains inconclusive by itself.

No phone storage was mounted or written by the candidate. Its source contains
only read-only block-device checks and the observed timeline ended through the
known rollback route.

Two concrete transport defects were confirmed offline against the retained
ASUS `u_serial` source:

- the shell reporter did not place target `ttyGS0` in raw mode, while the exact
  host parser requires bytes unchanged by `OPOST`/`ONLCR`;
- it reopened and closed `ttyGS0` for every record across UDC bind and a forced
  soft disconnect. `gs_close()` drains and then resets or frees the gadget FIFO,
  so a record can be discarded or lose framing.

The successor configures raw mode before the first report, keeps one target
descriptor open for the complete cycle, retains a bounded malformed payload
under a rejected-only evidence format, and continues to reject malformed data
rather than accepting it. Generation 73 remains a separate candidate and has
not been booted by this record.
