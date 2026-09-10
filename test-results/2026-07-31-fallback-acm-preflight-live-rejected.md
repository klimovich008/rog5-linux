# Fallback ACM preflight live rejection

Date: 2026-07-31

Result: **REJECTED before signed health; temporary boot unused**

## Outcome

The installed Alpine fallback remained reachable as the exact
`1d6b:0104` composite USB gadget on the expected physical port. The signed
ACM preflight did not produce a health frame or private proof record.

The first authorized attempt stalled while writing the 1,256-byte Python
launcher. Offline analysis found that the host writer did not read the
interactive shell's echoed bytes while writing, allowing full-duplex ACM
backpressure to deadlock both sides. The controller now:

- polls read and write readiness together;
- retains and bounds bytes drained during a write;
- sends one nonce-bound Ctrl-C/newline plus split-literal shell-ready command
  before the larger loader;
- labels each bounded write stage and reports byte progress; and
- rejects malformed stage labels and duplicate or echoed readiness markers.

Thirty-eight ACM protocol tests and all seventeen lifecycle methods pass with
that change.

## Live localization

The enhanced failure classes localized the connected state:

1. a separate reset write completed, but `shell-sync` remained at `0/90`
   bytes;
2. an atomic 92-byte reset-plus-sync preamble wrote, but no shell-ready marker
   returned;
3. `usbreset` of the exact ASUS device completed without restoring a reader;
4. root-owned host unbind/rebind of the exact ASUS USB device forced full
   deconfiguration and re-enumeration on the same physical port, but the
   shell-ready marker still did not return.

This distinguishes a missing or wedged device-side `/dev/ttyGS0` reader from
host echo backpressure. The transport fix is hardware-informed but remains
unaccepted live until a fresh fallback boot restores the supervisor.

## Independent control-path evidence

A temporary, non-default host profile assigned `169.254.77.1/16` to the
phone's CDC-NCM interface. The fallback responded at `169.254.77.2` with zero
packet loss. Its live Ed25519 SSH host-key fingerprint exactly matched the
retained private pin. Strict key-only SSH rejected the available local client
identities, consistent with the earlier fallback-key admission result.

The temporary NetworkManager profile was then removed. No fallback
`authorized_keys` entry or configuration changed.

## Safety state

- No fastboot command, experimental temporary boot, kexec, flash, mount,
  partition operation, or explicit phone-file write occurred.
- BusyBox history and read-induced ext4 atime effects remain possible for the
  attempted ACM shell preambles.
- The no-replace private proof path remains absent.
- The corrected headless temporary boot remains unused.
- The phone remains on the installed Alpine fallback with USB-NCM and ACM
  enumeration, but ACM control is unavailable until the phone is rebooted.

## Next action

Perform one physical fallback reboot. After the exact USB product returns,
rerun the signed ACM preflight once. Only a valid host-key-signed proof record
may advance to the complete deployment preflight and guarded temporary boot.
