# Early USB-data cutoff — V20 host failure and fix

V19 proved Wi-Fi runtime/reassociation/traffic with USB data disabled after
startup. The next question is whether the unchanged target completes native
root and Wi-Fi startup when data is removed before the root mount. This is
still not a physical charger-only cold-boot claim.

`scripts/host/native-wifi-discovery.py` validates a fresh direct Tailscale UDP
pong against the same peer's immediately read status, then requires a direct
WLAN route and unambiguous source address. IPv4 and unscoped IPv6 are supported.
Offline/relay/stale endpoints are not ready; wrong peers and ambiguous data
are refused. It does not access USB paths, change authentication or prove SSH.
The caller must still verify the project SSH host key and expected new boot ID.

Five focused tests pass in0.002s; active tier passes in91.792s. Kernel, DT,
modules, firmware and initramfs are unchanged. No new phone boot has run.

The intended cutoff is triggered only by the expected new kernel's exact
`ufs-ready/ENTER` stage2 after irreversible claim entry. Revalidate the USB
instance and retain bounded same-instance restoration. After WLAN is available,
map the host cutoff time into a target-uptime interval using a bounded SSH clock
sample and compare it with the kernel log. In native mode, the actual root
mount occurs at **userdata-mount**, not the later image-mount stage; the exact
sealed init path and V19 log confirm this. Do not claim an early cutoff unless
the conservative upper bound precedes that mount entry.

V19 and earlier remain consumed. ASUS slot A, V11 and protected phone storage
remain untouched. Managed Tailscale SSH still has its separate account check;
using authenticated network discovery plus ordinary key-authenticated LAN SSH
does not satisfy or bypass that check.

## Narrow V20 admission

Source`d186b027218ff43e19823015c4ca13d40fee0803` passed all jobs in exact-head
run33436474231, including merge compatibility and QEMU. The fresh RAM-only
candidate`persistent-native-root-wifi-early-cut-v20` retains the exact V19
Image/DT/initramfs. Identical signed twins packaged in0.463s; manifest:
`e459948131640d19d7f5e03105b00c828177c0a05cf226dcd49c4db480a767ed`.

Controller replay covers the post-claim exact stage2 trigger, stale SSH identity,
conservative cutoff timing and restore-before-reboot cleanup. Host sleep is
inhibited during the trial. USB restoration remains independently bounded180s;
fresh discovery stops by140s after cutoff. No target timer is disarmed. The
literal data-only admission changes no execution code or historical claims.
At admission V20 was unconsumed; no persistent selector change was authorized
by this admission. Its subsequent failed qualification is recorded below.

## V20 outcome: failed qualification, not a kernel failure

V20 is consumed. Target`533b1053-8c59-4adf-a79c-c52b4e70cc4b` reached the
correct early stage and the host disabled USB. The assembled Python controller
then raised `TypeError: 'list' object is not callable`: its preflight assignment
`gate_events=[...]` replaced the previously defined `gate_events()` callback.
Fragment-only tests had excluded that shared namespace. Classification: R2/R7.

Cleanup restored the same USB instance after0.182s, so this is not an
early-USB-free boot pass. The unchanged kernel subsequently reached Arch,
radio/WPA/DHCP and state services. The controller attempted recovery before SSH
was ready and correctly sent no reboot. After bounded evidence collection,
one normal reboot was requested over authenticated SSH; V11
`62b2f823-8873-4344-94d3-176a22e60349` and state/Tailscale restored in67.067s
from that request. Exact write scope and host cleanup passed. No flash, slot,
layout or selector change occurred.

## Targeted prevention

The exact V20 controller and its execution hash are retained unchanged.
`check-controller-bindings.py` checks complete assembled module-level function,
lambda and import names for collisions with preflight/control-flow bindings.
It rejects the actual V20 file at function line239/rebinding line347. This is a
narrow check, not a proof of arbitrary Python behavior.

The fixed offline template names the snapshot `gate_preflight_events`. A
regression executes the actual callback and preflight assignment together:
the original raises the observed error; the fixed version retains a callable
and reads fresh gate events. A second focused fix waits boundedly for recovery
SSH but never repeats an ambiguous reboot request. A future plan must explicitly
supply that readiness budget and retain cleanup margin.

Three public binding tests, the exact namespace regression and recovery-readiness
test pass; active tier92.264s. No kernel/DT/firmware/initramfs rebuild is needed.
Do not issue a successor until the complete assembled controller passes these
checks alongside its existing replay and exact-artifact gates. Never retry V20.
