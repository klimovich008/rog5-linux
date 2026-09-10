# Generation 57 volatile-systemd local-image live result

Date: 2026-08-14

Result: **PASS. The sole RAM-only Generation 57 cycle reached exact read-only
UFS, local-image Arch Linux, systemd, and strict key-only SSH in 305.928
seconds, then returned to the exact Alpine fallback. Generation 57 is consumed
and must never be retried or flashed.**

The target boot ID was `329e8c88-6a34-4387-8601-059ae440a3af`. Runtime
attestation passed at target uptime 245.02 seconds with:

- Linux `7.1.4-gae717d919f87`;
- 116 physical UFS block nodes and exact userdata `/dev/sda23`;
- userdata and the 16 GiB local image both mounted `ro,noload`;
- a tmpfs-backed OverlayFS root;
- zero blocked block queries, blocked SCSI commands, journal-recovery events,
  and UFS error events;
- zero backlights; and
- strict key-only SSH.

The host-observed target stages advanced from `ufs-ready` to a successful
`switch_root` in 18.614 seconds. No flash, slot, partition, erase, format, or
phone-storage write operation occurred.

## Timing effect

`systemd-analyze time` reported:

- kernel: 43.766 seconds;
- userspace: 2 minutes 59.697 seconds;
- total: 3 minutes 43.463 seconds; and
- `multi-user.target`: 2 minutes 59.696 seconds in userspace.

Generation 56 reported 43.699 seconds kernel plus 3 minutes 54.559 seconds
userspace. The volatile markers and vconsole mask therefore removed 54.862
seconds from measured userspace and 56.313 seconds from lifecycle acceptance.
Generation 57 is 15.5% faster than Generation 56 and 19.5% faster than the
approximately 380-second Generation 20 NFS baseline.

Neither `ldconfig.service` nor `systemd-vconsole-setup.service` appeared in
the blame or critical chain, proving the intended optimization. The next
largest observations were:

- `dev-sda23.device`: 1 minute 46.059 seconds;
- `dev-loop0.device`: 41.238 seconds;
- `systemd-logind.service`: 40.424 seconds;
- `sshdgenkeys.service`: 38.212 seconds;
- `dbus-broker.service`: 28.814 seconds; and
- `rog5-p2-ready.service`: 21.727 seconds.

Device-unit blame is not automatically a critical-chain cause. The next cycle
must distinguish real udev/device-settle work from parallel elapsed time before
changing storage or service ordering.

## Fallback and independent evidence

Normal systemd reboot returned Alpine with boot ID
`53d7d3f3-950f-461e-bd75-9e27406732b7` on the exact original USB port.
Fallback evidence reported:

- maximum temperature: 44.5 C;
- PMIC reset trigger/type: `PS_HOLD` / `HARD_RESET`;
- PMIC watchdog signal: absent;
- fatal tokens: zero; and
- pstore: unavailable with zero records.

The empty/unavailable pstore result is inconclusive and is not evidence that a
crash could not have occurred. The normal accepted target path and explicit
reboot provide the positive success evidence for this cycle. The host intent
resolved exactly to `TARGET_ACCEPTED`, cleanup passed, and the temporarily
stopped Steam web-debug socket was restored active and enabled.
