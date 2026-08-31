# Automatic Wi-Fi boot: implementation checkpoint

V17 already passed WPA2/CCMP, DHCP and strict SSH over Wi-Fi. This follow-up
packages the same qualified radio/kernel/DT inputs for automatic local startup.
It is a RAM-test composition, not a persistent release or an admitted candidate.
V11 and stock ASUS slot A remain unchanged; all trials through V17 are consumed.

## Changes

- A sealed archive marker enables USB-carrier-independent startup only for
  read-only native root with SSH diagnostics disabled. Legacy diagnostic and
  write modes retain their attended gate. Power, role, route and storage checks
  remain; a powered side port is still required.
- Automatic radio qualification runs after P2, before writable p23 state.
  It reuses the qualified query/AUTO/held-OEM/activation sequence and exact
  modules, raw/cache checks, UFS reads and PCI identity. Traces are bounded.
- WPA reads a root-only configuration from the existing p23 state image, after
  persistent SSH identity is restored. Foreground WPA and DHCP are supervised;
  DHCP maintains its WLAN lease and uses the native resolved hook.
- Automatic Tailscale startup retains the USB rescue address without requiring
  carrier or installing a USB default route. Legacy V11 behavior is unchanged.
- Rollback starts before early SSH/P2 and does not depend on `basic.target`.
  An absolute 900s boot deadline and the qualified 600s radio timer remain
  armed for this trial. No successful association automatically disarms them.

## Failures prevented before another phone cycle

R2/R3/R4: an ordinary transient timer service inherits `After=basic.target`,
which could block rollback behind early radio startup. Actual Arch transient
units with inert actions confirmed the dependency. Explicit no-default and
shutdown dependencies fix it; pre-P2 failures cannot prevent the boot timer
from starting. The sanitized live properties are a regression fixture.

R2: appending new cpio members after the base archive violates the release
verifier's sorted-name contract. The generator now orders all entries, and the
real C verifier rejects an intentionally unsorted fixture. Existing archive
member bytes/metadata remain unchanged except the three named boot helpers.

## Validation so far

- Seven focused automatic-boot tests pass, including the real C newc parser.
- Full local CI passes in459.396s (previous full checkpoint438.238s); the
  frozen code tree was unchanged. An earlier133.819s run rejected `/dev/shm`
  under a historical no-device-path fixture. Moving only this turn's scratch
  there freed `/tmp` for the successful run; no data was deleted.
- Exact sealed BusyBox syntax/stat checks pass.
- Exact BusyBox route lookup passes with NO-CARRIER in a disposable host
  namespace; the direct source/address/route check remains enforced.
- Actual Arch WPA/DHCP argv pass in isolated empty network namespaces with
  dummy configuration, without RF or real credentials.
- Systemd accepts the startup graph; inert executable substitution was used
  only for that ordering check, not as proof of the actual executable behavior.
- Initramfs twins match: `1d4a8ff015af00da56074ea28545cb6e63b7e72c92800a5565489b647dd3e3d2`.
  Composition took3.309s/3.265s. The release verifier accepts the actual archive.
  No kernel/module/firmware rebuild was performed.

The next physical question is automatic radio→state→WPA→DHCP→SSH startup
without target-side commands supplied by the host. Then test USB-data absence,
reconnect, load/charging and fallback before any persistent selector change.
The private Wi-Fi configuration has not yet been staged. No new claim, signing,
phone boot, storage write, flash, slot or selector change occurred in this checkpoint.
