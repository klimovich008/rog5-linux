# Recovery v18 live staging result

Status: **PASS twice** for credential-free RAM-only staging, exact USB
identity, ACM, NCM, storage isolation, and automatic rollback. Nothing was
flashed. Kexec was not loaded or executed during these two cycles.

## Candidate

- Manifest-pinned AVB SHA-256:
  `b06f016a5f9697a4e51b13159dede83990c30fc9bd36ff642214ac6715c05af7`.
- Both real preflights found exactly one `lahaina` fastboot target.
- Both guarded invocations used only `fastboot boot`.
- The host accepted only exact normalized product `ROG5_recovery`.

## Repeated live gates

| Gate | Cycle 1 | Cycle 2 |
|---|---|---|
| recovery ready | 07:17:32 | 07:22:34 |
| wrapper kernel | expected 5.4.210 staging release | expected 5.4.210 staging release |
| root | RAM-backed `rootfs` | RAM-backed `rootfs` |
| block-backed mounts | 0 | 0 |
| physical disks/partitions | 116 read-only, 0 failures | 116 read-only, 0 failures |
| rollback marker/watchdog | armed/alive | armed/alive |
| ACM supervisor and `/dev/ttyGS0` | alive/present | alive/present |
| authorization/SSH | absent/stopped | absent/stopped |
| UDC/NCM carrier | configured/1 | configured/1 |
| host NCM ICMP | pass | pass |
| exact fallback return | 07:20:49 | 07:25:51 |
| fallback boot identity | changed | changed |

The rollback marker was never removed. Neither cycle required a host reboot
command after recovery started.

BusyBox interactive ash emits an initial terminal cursor-position query. A
noninteractive piped `socat` client should send one sacrificial line before
machine-parsed commands; a normal interactive terminal responds itself. This
did not affect the device gates or supervised ACM transport.

## Promotion

V18 satisfies the two required staging/rollback cycles. The nested Linux 7.1
payload is now eligible for one separate attended load and kexec attempt. The
loader must verify nested hashes, disable exactly one allowlisted Haven
watchdog, load without executing, and retain the host fallback path.
