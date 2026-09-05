# Fallback-to-fastboot anchored diagnostics — live

Date: 2026-08-03

Result: **PASS live diagnosis and offline correction**. The exact persistent
Alpine fallback passed its guarded health preflight. A pinned SSH session then
acknowledged one `RESTART2("bootloader")` request, after which the fallback USB
gadget disconnected. Neither fastboot nor another phone USB mode appeared
during the helper's fixed 45-second window or an additional read-only
60-second observation. The host kernel recorded one anchored USB disconnect
and no re-enumeration in those windows.

The phone later appeared as exactly one ASUS fastboot device `0b05:4daf` at
the same physical USB port. This report does not infer whether firmware,
physical operator input, or another delayed transition caused that later
appearance. No second reboot request was sent.

Generation-5 recovery was not booted, contacted, or consumed. No flash, erase,
format, slot change, partition write, phone-storage mount, or target kexec
occurred. The dedicated fallback SSH credential was used only through strict
host-key pinning; private serial and key material remain outside Git.

## Diagnostic gap and correction

The standalone SSH reboot helper previously reduced every terminal transition
failure to `fastboot did not appear`. Its test was changed first and failed on
the missing anchored disconnect classification. The corrected helper now:

- finds exactly one `1d6b:0104:ROG5LINUX` fallback device and pins its real
  sysfs location before the reboot request;
- requires successful fastboot to return at that location as `0b05:4daf`
  with the expected serial before accepting exact product `lahaina`;
- distinguishes no disconnect, disconnect without re-enumeration, Linux
  fallback return, another USB mode, fastboot USB without userspace discovery,
  and anchored serial/identity changes;
- fails closed when fallback `dmesg` is unavailable or unreadable;
- retains the fixed production 45-second deadline and one-second polling;
- has no runtime fixture/sysfs override surface; tests mechanically rewrite
  only a private temporary copy; and
- remains reboot-only: source and tests reject boot, flash, erase, raw-memory,
  storage-write, and host-key bypass surfaces.

The expanded test covers exact success markers, SSH disconnect after an
authenticated request, wrong serial/product/port/sysfs identity, zero and
duplicate fallback devices, unexpected fastboot state, all terminal USB
classifications, and production absence of test overrides.

## Review and verification

A bounded tool-free Claude review found a real `set -e` branch hazard and the
missing boundary tests; both were corrected. Later review attempts requested
prohibited tool access and therefore produced no verdict. Their textual
findings were independently checked: applicable findings were implemented,
while the claimed unreachable unexpected-state branch was disproved by its
two-count condition and passing behavioral test.

The focused helper test and complete
`scripts/host/test-repository-linux.sh ci` tier pass. Publication and GitHub
Actions evidence remain to be added. The next phone action remains a fresh
Generation-5 `diagnostic-preflight`; it may run only from a clean, pushed,
GitHub-green tree while this same exact fastboot device remains present.
