# Wi-Fi USB-data isolation preparation

V19 passed runtime USB-data isolation, reassociation, traffic and V11 fallback.
It is consumed. USB-data-absent boot and sustained charging remain unproven.
The qualified kernel/DT/modules/firmware and initramfs are unchanged.

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
These checks preceded the physical V19 cycle below.

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

## V19 runtime qualification admission

The early-cut boot test remains pending. To continue the separate runtime
qualification while managed Tailscale SSH awaits its account check, V19 first
boots normally and proves its actual LAN address, SSH key and boot ID. Only
then may the host disable USB data for180s. The cycle sends64MiB of bounded
read-only traffic, requests one WPA reassociation, samples power/thermal/storage
state in RAM, restores USB and reboots to V11. It does not bypass or modify
Tailscale authentication, and it will not be reported as USB-free boot proof.

Source`b29417605173bcbe60f014da87626301f3998f65` passed every job in
exact-head run33430706319. Candidate`persistent-native-root-wifi-isolation-v19`
reuses V18's exact Image/DT/initramfs and has identical signed core twins;
packaging took0.459s. Manifest:
`b62f7c1e7b7cd790c64b4e0576345289420699c60324c5f95778997b7620e224`.

The exact WPA client sent one REASSOCIATE command to a fake control endpoint.
The sampler ran against the actual Arch root without RF; its1MiB stream check
passed. Controller replay checks verified WLAN before cutoff, no reassociation
retry after a lost acknowledgment, full isolation duration, same-device restore
and restore-before-reboot ordering. The admission is literal data only; target
timers remained armed. No persistent selector change.

## V19 result

Admission`093a619ea8d4381f4cb81559f08458d35854e164`; target boot
`bd9df6cf-ff2d-4935-840d-c1d7f2d6d9c9`. Automatic WLAN proof completed
69.904s after claim consumption. USB data was disabled for180.089s, with no
host NCM interface.115 complete safety samples include114 with target carrier0.
One reassociation produced a new connection event; it was not retried. Two
32MiB uncompressed SSH streams passed exact byte checks in1.412s/6.335s.
These are short transfer observations, not a sustained throughput benchmark.

USB restored to the same instance. Normal reboot restored
V11`7750f962-9b70-4c28-b786-5b2309b03788`, shared SSH/state/Tailscale and exact
two-node write scope in63.187s. Claim→restored was316.554s. Temporary host
address/port permission and all observers were removed. No flash, partition,
slot, selector or new persistent configuration change occurred.

During isolation, input stayed online at about5V, capped500mA, with sampled
mean input402mA. Battery samples averaged−22mA, ranged−310…+9mA, and the charge
counter did not change. Pack voltage stayed8.535–8.595V; battery temperature
peaked30.3°C and thermal-zone maximum42.8°C. Thus safe short runtime passed,
but neither the unchanged counter nor voltage recovery proves net-positive
charging. Charger-only and longer power testing remain necessary.

No new matched panic/oops/crash/UFS-error marker appeared against V18. Both
logs contain the same early SPMI SID5 register0x104 transaction failure/status3
and probe warning before Wi-Fi starts; do not call the kernel warning-free.

An interactive authenticated Tailscale UDP ping during USB isolation reported
the same LAN endpoint already verified by SSH. This is network discovery,
not managed Tailscale SSH authentication. Its exact timestamp was not retained;
the command's USB-authorized readback was0. A later capture script arrived after
the planned reboot began and refused the missing USB node. Integrate discovery
before the next lifecycle deadline; do not burn another cycle for that capture.
