# Early USB-data cutoff — preparation

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
