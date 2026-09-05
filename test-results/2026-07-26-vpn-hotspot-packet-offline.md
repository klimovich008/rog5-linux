# VPN-backed hotspot packet gate — offline result

Date: 2026-07-26

Result: **PASS OFFLINE for the AP-scoped forwarding policy; no phone, Wi-Fi
radio, VPN endpoint, credential, or external network was used**.

The earlier regression inspected generated nftables text but did not transmit
packets. The same `test-vpn-hotspot.sh` now creates three mount-free network
namespaces inside the privileged, network-disabled builder:

- one hotspot client behind `wlan0`;
- one simulated VPN peer behind `wg0`; and
- one prohibited ordinary uplink with separate IPv4 and IPv6 peers.

Python standard-library UDP peers then prove:

- hotspot-client traffic reaches the simulated VPN peer;
- neither IPv4 nor IPv6 datagrams reach the ordinary uplink;
- an unsolicited VPN-side datagram cannot enter the hotspot client;
- deleting `wg0` makes the health check fail without opening the ordinary
  uplink; and
- teardown removes the nftables table and restores both forwarding sysctls.

The ordinary-uplink peers write a shared marker immediately upon receiving a
datagram. This detects one-way exfiltration even when the return packet is
also dropped. A mutation that added an ordinary-uplink accept and masquerade
path retained the original expected rules but failed on that receipt marker,
proving the packet assertions add coverage beyond text matching.

## Exact inputs

| Input | SHA-256 |
|---|---|
| `vpn-hotspot.sh` | `f270cc05ebf2776179f9eb7e5f1f96d3ce76f5b144c30b961cff26f923fe849d` |
| `rog5-vpn-hotspot.service` | `3f36a12b9df5c1d331eae13be5107fbdc2b32ab7a785b2b8694270ce007b022b` |
| expanded `test-vpn-hotspot.sh` | `a6643d0bd2528e5827161807596bac44cf47852868f60423b65ab26d4cc364c9` |
| builder image | `sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c` |

The production script and service did not need a change.

## Remaining hardware gate

This test substitutes a veth for the encrypted interface and validates the
routing/firewall boundary, not WireGuard cryptography or radio behavior.
Acceptance still requires the real ath11k interface combination, AP security,
DHCP, VPN DNS, a real WireGuard handshake, endpoint reachability, VPN loss and
recovery, IPv6 policy, sustained throughput, thermals, charging, and battery
depletion on the phone.
