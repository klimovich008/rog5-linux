# Alpine vendor-kernel complete boot-log capture — live HOLD

Date: 2026-07-27

Result: **HOLD. A tested private capture path now exists, but the current
kernel ring no longer contains boot origin and is correctly rejected as a
complete boot log. A separately authorized normal Alpine reboot followed by
an immediate read-only capture remains required.**

The phone stayed on the installed Alpine 3.24 fallback and kernel
`5.4.134-qgki-perf-00001-g6c308144c23e`. No phone file, service, process,
module, display, network configuration, boot state, NFS state, or credential
changed.

## Capture contract

`capture-vendor-kernel-log.sh` connects only through the pinned
`rog5-fallback` SSH alias with batch mode, strict host-key checking,
identity-only authentication, and bounded connection/runtime timeouts. Its
remote program:

- verifies the exact fallback kernel, BusyBox PID 1, root identity, and
  `qcom,lahaina-mtp` compatible;
- reads `dmesg` without a phone-side temporary file;
- contains no reboot, kexec, module, mount, or storage-write command; and
- frames the stream so a disconnect cannot produce an accepted artifact.

The host accepts only a new `.log` path below the Git-ignored
`test-results/private` tree. It uses mode `0600`, a 2 MiB bound, one start
marker, one terminal marker, an atomic hard-link publication, and
no-overwrite behavior. SSH failure, malformed framing, empty content, and a
ring without a time-zero `Linux version` entry all leave no output artifact.

## Live result

The first version preserved the complete current ring, after which review
showed that startup had already been overwritten. A new fail-first fixture
demonstrated that the original acceptance check incorrectly treated a
well-framed late ring as a complete boot log. The implementation now rejects
that case.

The preserved private evidence was renamed to:

```text
test-results/private/2026-07-27-alpine-vendor-kernel-ring-incomplete.log
```

Its identity is:

```text
mode=0600
bytes=209449
log_lines=2421
sha256=c10fcb3d47f823a7f8eae3d8e5dedfc7664579d12723f1e5a28f2e2f3f26f9b4
first_monotonic_seconds=32220.875363
last_monotonic_seconds=37100.746298
coverage_seconds=4879.871
boot_origin_lines=0
fatal_signature_lines=0
```

The 81.3-minute ring consisted entirely of three recurring vendor messages:

| Message class | Lines |
|---|---:|
| five-second load-average report | 976 |
| SCSI cache synchronization | 734 |
| ASUS kernel-top report | 711 |
| total | 2,421 |

Zero fatal signatures in this retained interval do not prove a clean boot,
because the boot interval is absent.

An actual invocation of the strengthened tool against a fresh private
filename returned:

```text
FAIL kernel ring no longer contains the boot origin
```

No partial artifact remained.

## Screen-off I/O observation

A low-overhead, single-SSH-session 30-second sample kept the screen state
`off`, brightness at zero, and measured:

```text
cpu_busy_percent=0.79
sda_reads_delta=0
sda_writes_delta=28
sda_sectors_written_delta=336
sda_io_ms_delta=40
memory_available_kib=10564284 -> 10564068
swap_in_delta=0
swap_out_delta=0
```

A second in-memory `/proc/*/io` attribution sample avoided phone-side files:

```text
sda_writes_delta=36
sda_sectors_written_delta=544
sda_io_ms_delta=56
new_dmesg_lines=8
new_scsi_sync_lines=2
new_loadavg_lines=6
new_ktop_lines=0
```

The 544 sectors are 272 KiB at the block-stat 512-byte sector unit.
Chromium accounted for 88 KiB of attributable physical writes, the ext4
journal for 12 KiB, and Plasma shell for 4 KiB. The process accounting does
not cover every block-layer byte, but it supports keeping Chromium on demand
for both RAM and idle-write reduction.

## ASUS debug observation

Read-only inspection found:

```text
/proc/asusdebug-switch=asusdebug: on
/sys/module/asus_debug/parameters/enable=1
/sys/module/asus_debug/parameters/ktop_delay=60000
```

The vendor debug proc controls are world-writable. The fallback should remain
an administrator-only recovery/server environment, not a multi-user security
boundary. No debug or runtime-PM value was changed. Disabling vendor debug or
changing UFS policy is not justified without a reversible, separately
authorized wall-power comparison.

The mainline target does not need to reproduce ASUS's periodic debug worker.
The SCSI synchronization cadence and block writes should instead be measured
again under headless Arch, then with Chromium and Plasma enabled separately.

## Test identities

| Input | SHA-256 |
|---|---|
| private capture tool | `1a70840c5fc1113f88bd0e82f7f2b6ebdfd8a3748807b85a85f1b8e05a9c6ec7` |
| capture fixture | `2977d555ad4bedcd0ad49dbca1e67683c6e18ab4438a706d73ca8807d19b4ec9` |
| Linux-rootfs aggregate | `62f35b0aecaba1dd33ace7f6d72c38bf303c1d25febb6f7e308c95441c6655f8` |

The audit trail is:

- `1b96e17`: initial missing-tool fail-first contract;
- `98e39cb`: private atomic capture implementation;
- `277439c`: overwritten-boot-origin fail-first contract; and
- `93190c8`: boot-origin acceptance fix.

Validation returned:

```text
PASS complete vendor-kernel log capture is read-only, private, atomic, and fail-closed
PASS Linux rootfs tools pin signed input, preserve metadata, and avoid phone writes
```

Bash syntax, ShellCheck at warning severity, `git diff --check`, SSH failure,
malformed stream, outside path, overwrite, incomplete ring, and exact-content
fixtures pass.

## Remaining gate

After a separately authorized normal reboot into the same persistent Alpine
fallback, run the capture immediately after pinned SSH returns:

```sh
scripts/host/capture-vendor-kernel-log.sh \
  test-results/private/YYYY-MM-DD-alpine-vendor-kernel-boot.log
```

Only a `PASS` from the strengthened boot-origin gate can close the roadmap
item. The private raw log must remain ignored; Git should receive its hash,
redacted subsystem findings, and any concrete porting implications.
