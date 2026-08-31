# Wi-Fi USB-data isolation preparation

V18's automatic radio/state/WPA/DHCP/WLAN-SSH cycle and V11 fallback passed.
The next question is operation without the USB data connection, followed by
reconnect/load/power observations. The qualified kernel/DT/modules/firmware and
initramfs are unchanged; V18 remains consumed and must never be retried.

## Host-only implementation

`scripts/host/quiesce-native-usb-data.py` changes only the `authorized` attribute
of one authenticated native ROG5 USB instance at the fixed physical path.
The caller must first prove the signed target's early stage on that link;
descriptors alone are not authentication. An open directory descriptor, current
pathname/inode, device number and exact descriptors are revalidated around
every write. The helper disables data once, holds for at most300 seconds and
restores the same instance on timeout or interruption. A replacement device is
never touched. Hub defaults, port power, phone storage and boot state are not
changed.

Five hardware-free tests exercise bounded disable/restore, wrong identity,
wrong number, symlinks, initially disabled state, replacement, interruption and
duration refusal. They pass in0.008s; the active tier passes in96.848s.
No physical USB isolation or new phone boot has run at this checkpoint.

Linux documents device authorization as control over configuration/interfaces,
not a guarantee of power delivery. The reviewed implementation unconfigures the
device. Therefore the eventual test must measure input power and distinguish
data isolation from physical wall-charger/cold-boot qualification.
[Kernel USB authorization documentation](https://docs.kernel.org/usb/authorization.html).

## Observation channel

The existing separate Tailscale test client and phone are both online. The
phone's LAN address changed between V17 and V18, so it must not be guessed for
a new boot. Tailscale SSH currently requests its account check; the operator
has been sent the sign-in link. No policy, SSH key check or authentication gate
was bypassed. The pending connection performs only a pinned identity/read-only
proof if admitted. Do not consume a phone candidate merely to discover that
the observation channel is unavailable.

The proposed cut should follow exact early target identification and precede
local-root startup. Compare the actual cutoff and target stage timings rather
than assuming the cut occurred early enough. Preserve independent host USB
events, bounded restoration and the existing target rollback timers. A later
physical charger-only boot remains necessary before claiming full independence.
