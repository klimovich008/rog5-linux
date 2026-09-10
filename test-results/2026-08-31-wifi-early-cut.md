# Early USB-data cutoff — V21 pass

V21 passed native-root/Wi-Fi startup with USB data removed before the root mount.
It is consumed. V19's runtime/reassociation/traffic pass remains valid. Neither
result is a physical charger-only power-on or sustained-charging claim.

`scripts/host/native-wifi-discovery.py` validates a fresh direct Tailscale UDP
pong against the same peer's immediately read status, then requires a direct
WLAN route and unambiguous source address. IPv4 and unscoped IPv6 are supported.
Offline/relay/stale endpoints are not ready; wrong peers and ambiguous data
are refused. It does not access USB paths, change authentication or prove SSH.
The caller must still verify the project SSH host key and expected new boot ID.

Five focused tests pass in0.002s; active tier passes in91.792s. Kernel, DT,
modules, firmware and initramfs were unchanged during this preparation.

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

## Narrow V21 admission

Source`84c38b597e1530e885c2ad0c3f4abfd0d5814c10` passed all jobs in exact-head
run33439112540, including merge and QEMU. Candidate
`persistent-native-root-wifi-early-cut-v21` keeps the same verified
Image/DT/initramfs. Signed twins match; packaging0.436s. Manifest:
`f42315c90cc27ed2c585846330b85041f6554501e2863b58fda2e6a27cf9e99e`.

The actual V21 callback, preflight snapshot and target/cleanup tail pass in one
namespace; the preserved V20 version reproduces the failure. Complete assembled
controller/observer/gate binding checks run before signing and in connected
preflight. Recovery readiness is explicitly bounded90s with cleanup reserve,
and its exact function test proves no repeated ambiguous reboot. The admission
changed only literal data and status. All earlier trials remain consumed, and
both target timers and V11/ASUS A recovery remained intact.

## V21 physical result

Admission`8d1a5f0958ec06576eb5f9cf6a4a6b4e20091c4b`; target
`1d751cda-609d-4608-99ce-a83264b18038`. The exact early stage triggered USB
data isolation. Fresh authenticated UDP discovery located the new LAN endpoint;
the project SSH key, new boot ID and signed bundle/kernel identity passed.

The conservative cutoff interval was target uptime5.615–5.786s. Native root
mount entry was11.432s, so even the latest bound preceded it by5.646s. USB data
remained off84.504s through Arch/state/WPA/DHCP/WLAN SSH validation. All three
S12 traces passed. Claim→strict LAN SSH was104.211s; complete proof106.971s.
The corrected controller retained a callable `gate_events()` throughout.

USB restored to the same instance. One normal reboot restored V11
`cec1225b-e998-4d97-8728-c56faddbee5c`, state/Tailscale and exact two-node write
scope in64.532s. Claim→restored was172.132s. Host address/port permission and
all temporary observers were removed. Battery remained Full/Good; final
readback8.593V/30.2°C. The existing early SPMI probe warning remains; no claim
of a warning-free kernel is made. No flash, layout, slot or selector changed.

Next qualify physical charger-only power/startup and longer safe charging,
then review the permanent healthy-startup/recovery policy before deployment.
The operator has been asked to have the original charger ready but to retain
the PC connection until a coordinated test. V11 is still the default without
active Wi-Fi; V21 must never be retried.
