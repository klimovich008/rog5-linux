# Automatic Wi-Fi boot: implementation checkpoint

V17 already passed WPA2/CCMP, DHCP and strict SSH over Wi-Fi. This follow-up
packages the same qualified radio/kernel/DT inputs for automatic local startup.
V18 passed automatic startup and is consumed. This remains a RAM-test
composition, not a persistent release. V11 and stock ASUS slot A are unchanged.

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

The implementation checkpoint preceded candidate signing and the live cycle
below. No kernel rebuild, flash, slot or selector change was needed.

## Narrow V18 admission

Executable source`20ef71024d47e705cd1654818b6e3ccfa2ac704e` passed all jobs in
exact-head run33425976612, including merge and QEMU. The fresh signed RAM-only
candidate`persistent-native-root-wifi-automatic-v18` has identical core twins;
packaging took0.473s. Manifest:
`ac1b008b67394a4c4641ec567e10474e484ff90d6382a643f498a9a41e0d88da`.

Data-only admission`ff2a209d6dd1ec9ccc53c43b3db2f6688ac068b1` did not change
execution code or earlier claims. Controller replay passed; the target phase
only observed automatic startup and verified WLAN SSH. The private network
configuration was added without overwrite to the existing p23 state image.

## V18 physical result

Target`93a14b2f-2019-4d32-bfc9-418b52d04033` automatically qualified the radio,
mounted state, restored SSH identity, associated with WPA2/CCMP, obtained DHCP,
and accepted exact-key/boot-ID SSH over the host's bound WLAN route. No host
command started target radio/WPA/DHCP or transferred target setup data after boot.
All three captured S12 phases passed the existing ordered read/write-ACK verifier.
The radio stage preceded writable state; service state used only sda+sda23.

Claim→USB SSH:59.257s. Claim→Wi-Fi SSH plus adjacent evidence:71.337s.
Requested reboot→restored V11:63.685s. Claim→restored V11:135.154s.
V11 boot`ac39a52f-dd50-4bc9-9d20-449a67aace83` restored state/Tailscale and
the exact two-node write scope. Private Wi-Fi configuration metadata survived.
The temporary management address,8079 permission and observers were removed.

Battery was Full/Good,8.599V/30°C; the sampled current was−6mA. This short
full-battery sample does **not** prove sustained net-positive Wi-Fi charging.
Neither USB-data-absent boot nor long reconnect/load operation is claimed.
Both trial rollback timers remained armed; V18 must never be retried.
Next validate those remaining conditions before selecting a persistent Wi-Fi
release. V11 remains the current default, without active Wi-Fi support.
