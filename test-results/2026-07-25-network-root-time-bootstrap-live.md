# Network-root volatile time bootstrap live report

Status: **live gate passed; exact fallback restored**. The target clock was
about 2.38 million seconds behind the synchronized host and converged after one
guarded volatile correction. The PMIC RTC remained disabled, no phone storage
was exposed or written, and nothing was flashed.

## Scope

This test reused the exact manifest-pinned network-root v5 bundle. UFS, its
PHY, RTC, RMTFS, GPUCC, GPU, GMU, the Adreno SMMU, display,
QMP/SuperSpeed, and secondary USB remained disabled. The target root stayed on
read-only NFSv4.2 plus a volatile tmpfs/OverlayFS upper.

The new host tool was allowed to change only the running kernel's
`CLOCK_REALTIME`. It contains no `hwclock`, `timedatectl set-time`, RTC device,
PMIC offset, block-device, or flash operation.

## Staging transport

The host was NTP-synchronized and clean before the test. The exact-peer NFS
server passed its prepared-root verifier and exposed one read-only export only
to the USB target address.

One terminal-backed serial command was prefixed by a cursor-position response
and rejected by the staging shell before kexec loaded. Rollback remained
armed. A Python standard-library transport then opened ACM with `O_NOCTTY`,
flushed stale input, sent the fixed loader command, stripped control queries
before displaying output, and observed all three nested hash checks plus the
loader PASS marker. The same transport sent the separately attended
`kexec -e` and observed staging ACM departure.

That successful inline transport is now captured as
`scripts/host/network-root-acm.py`. Its actions are fixed to normal load,
diagnostic load, and kexec execute; execute has a separate guard. A
pseudoterminal regression proves that a DSR query is stripped and never sent
back as command input. The repository helper itself is offline-tested and
will replace terminal attachment on the next live boot.

## Target safety gate

The normal, unmasked target passed:

- exact Linux `7.1.4-g7a5cef0db479` with systemd PID 1 and running systemd;
- successful normal udev-trigger/modules-load results;
- OverlayFS `/` and the exact read-only NFSv4.2 lower;
- zero physical block devices and zero block-backed mounts;
- exact USB carrier/address;
- zero failed units and zero fatal signatures;
- 33 thermal zones with a 37 C maximum;
- an armed rollback watchdog with no disarm marker; and
- RTC DT status `disabled`, no RTC module, and zero RTC devices.

## Time correction

A controlled test first moved only the target's volatile system clock ten
seconds backward. RTC remained disabled, storage remained absent, and rollback
remained armed.

`sync-network-root-time.sh` then:

1. required the host's `NTPSynchronized=yes`;
2. required the dedicated private key to have no group/world access and used
   strict known-host checking with the network-root host alias;
3. repeated the target kernel, systemd, NFS/OverlayFS, storage, USB, failed
   unit, fatal-log, watchdog, and RTC gates;
4. measured an initial drift of 2,378,466 seconds after the controlled skew;
5. changed only Linux system time and reported `changed=1`;
6. required convergence within three seconds; and
7. repeated the RTC, storage, watchdog, USB, systemd, and fatal-log checks.

The much larger-than-injected drift proves that v5 cannot assume useful time
from its boot chain even with the invalid PMIC RTC disabled. An independent
strict-SSH sample placed target time inside the bounded host sampling interval
after correction.

## Reboot and cleanup

Only after the time gate passed was the network-root watchdog disarmed through
the fail-resumable repository helper. The target remained healthy and normal
systemd reboot returned to the exact persistent fallback.

Strict fallback SSH passed after activating the intentionally
non-autoconnecting host profile. Final cleanup proved:

- zero NFS listeners, exports, mounts, and mountd processes;
- zero temporary NFS kernel threads and no export mount;
- no temporary drop-zone interface, service, port, rich rule, or masquerade;
- no network-root `/30`, exactly the fallback `/16`;
- no Fastboot or ADB device; and
- active ModemManager.

## Decision and next gate

- Accept the guarded host-time bootstrap for attended USB network-root boots.
- Keep PMK8350 RTC disabled and never write it merely to mask the bad value.
- Use the new fixed-action ACM helper on the next boot; do not attach an
  interactive terminal to the staging shell.
- Add authenticated network time only after Wi-Fi is accepted, then verify
  reconnect, backward/forward correction, TLS, package signatures, and timer
  behavior.
- A cold-power-loss time test remains separate from the passing warm-boot
  network-root result.
