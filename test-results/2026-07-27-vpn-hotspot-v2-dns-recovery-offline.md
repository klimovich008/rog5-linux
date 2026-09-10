# VPN-backed hotspot v2 DNS/recovery gate — offline result

Date: 2026-07-27

Result: **PASS OFFLINE for VPN-routed UDP/TCP DNS traffic, one-way DNS-leak
detection, WireGuard endpoint loss/recovery, VPN-interface loss/recreation,
and exact cleanup. No phone, radio, provider, user credential, external
endpoint, or external network was used.**

This checkpoint extends the earlier
[packet gate](2026-07-26-vpn-hotspot-packet-offline.md) and
[real-WireGuard gate](2026-07-27-vpn-hotspot-wireguard-offline.md). The two
test runners now select the separately versioned successor-v2 hotspot control
and service by default.

The production v1/v2 controls and services did not change. The accepted
successor-v2 archive and protected export therefore remain byte-exact and do
not require rebuilding.

## Fail-first sequence

Commit `e1f3979` strengthened the static real-WireGuard contract before the
runtime test changed. It stopped on:

```text
FAIL real-WireGuard hotspot test omits: target=${TARGET:-$repo/scripts/device/vpn-hotspot-v2.sh}
```

Commit `3593abb` changes only the existing packet, real-WireGuard, and static
contract tests. It adds no package, service, runtime daemon, credential, or
phone command.

## Simulated VPN/uplink boundary

`test-vpn-hotspot.sh` still creates three mount-free namespaces inside a
privileged container with no external network:

```text
hotspot client <-- wlan0 -- test root -- wg0 --> simulated VPN peer
                                  |
                              uplink0
                                  |
                        prohibited WAN peer
```

It now uses the v2 control/service by default and additionally requires:

- UDP and TCP port-53 traffic to reach the VPN peer;
- neither UDP nor TCP port-53 traffic to reach the ordinary uplink;
- a one-way UDP receipt marker and raw TCP SYN receipt marker to remain
  absent even when return traffic is also blocked;
- deleting `wg0` to fail the health check without opening the ordinary
  uplink;
- DNS-port traffic to remain closed while `wg0` is absent;
- recreating the same `wg0`/peer path to restore UDP/TCP DNS traffic through
  the still-installed kill switch; and
- teardown to restore both forwarding sysctls and remove nftables state.

An extra ordinary-uplink accept was injected before the unchanged terminal
drop, so all existing textual rule assertions still passed. The new packet
evidence rejected it:

```text
FAIL TCP DNS reached the ordinary uplink
PASS DNS leak mutation rejected on one-way receipt evidence
```

The failure path also exposed that namespace sleepers could retain a captured
output pipe after an assertion. Both packet tests now kill and reap their
disposable namespace/server children during cleanup. The mutation then exits
promptly instead of waiting for the namespace timeout.

## Real WireGuard DNS and recovery

`test-vpn-hotspot-wireguard.sh` still refuses any container with a
non-loopback interface, generates two disposable mode-`0600` keys, and uses a
local TEST-NET veth underlay. It now runs the v2 control by default.

A Python standard-library peer implements UDP and TCP DNS framing on
`10.99.0.2:53`. The client sends a valid A-record query for `vpn.test`; the
peer returns a valid no-answer response with the same transaction ID. Both
protocols must traverse the production nftables policy and encrypted
WireGuard tunnel.

The test then lowers only the peer underlay:

```text
ip link set peer-underlay0 down
```

The WireGuard interface and kill switch remain present, but UDP and TCP DNS
queries must time out. After restoring the underlay, both protocols must work
again. Latest-handshake timestamps remain nonzero and both receive/transmit
counters must increase beyond their pre-loss values.

The real-WireGuard run returns:

```text
PASS vpn-hotspot-v2 up ap=wlan0 vpn=wg0
PASS vpn-hotspot-v2 check ap=wlan0 vpn=wg0
PASS vpn-hotspot-v2 check ap=wlan0 vpn=wg0
PASS vpn-hotspot-v2 down ap=wlan0 vpn=wg0
PASS real WireGuard DNS UDP/TCP, endpoint loss/recovery, and cleanup
```

A fresh connected container still refuses before temporary storage or key
generation:

```text
FAIL test namespace is not network-disabled
```

## Revalidation

The following current checks pass:

```text
PASS real-WireGuard hotspot test is v2-default, ephemeral, network-isolated, DNS UDP/TCP, endpoint-recovering, and production-path-bound
PASS v2 VPN-hotspot installs the kill-switch before forwarding, rejects replacement, rolls back partial failure, and lowers AP before firewall cleanup
PASS successor v2 packaging installs exact hardened hotspot controls, preserves v1 evidence, verifies the full root, and embeds no secret
PASS v2 VPN path, UDP/TCP DNS leak blocking, unsolicited isolation, VPN-loss fail-close/recovery, and cleanup
PASS real WireGuard DNS UDP/TCP, endpoint loss/recovery, and cleanup
PASS Linux rootfs tools pin signed input, preserve metadata, and avoid phone writes
```

Both network-disabled tests pass in repeated fresh containers. POSIX shell
syntax, ShellCheck at warning severity, connected-container refusal, the
one-way leak mutation, transition ordering, packaging isolation, and
`git diff --check` also pass. The Linux-rootfs aggregate now delegates the
static real-WireGuard contract. No disposable container remains.

## Exact identities

| Input | SHA-256 |
|---|---|
| accepted v1 hotspot control | `f270cc05ebf2776179f9eb7e5f1f96d3ce76f5b144c30b961cff26f923fe849d` |
| accepted v1 service | `4c29a2cb097a081b9dc4b18abc330d5f6401211cad4178de2b77eb73f0dd5525` |
| production v2 hotspot control | `5e2b4af39227f3afd37a494474faf982f1a87f3e8807406e47196d92b3bb079d` |
| production v2 service | `8ea3d2509bb220d200816571f379c2992c5281771be22d1b84d49d4a716cd814` |
| v2 transition/rollback test | `9d129081d44d2328000fbf9960ace61ebfea9a293fc8f85ffbc85f8a76a9fb91` |
| packet/DNS-leak test | `a1fec9e9ba120a3d970da14511b6f51a8b23a719b95c96cc718c89693f4d1257` |
| real-WireGuard DNS/recovery test | `9fdc8853bcb5600956ae164a05b9b98be9dc2fa263cb55f5b0ba39a0a414fad9` |
| static WireGuard contract | `1b33ddbff40629a496f2d793bca30a4740fef0ee354c614f621bdbfa570f5717` |
| Linux-rootfs aggregate | `524ed79df2f36a6d80fc45af710859ac4a81c285719a8beb6a903f7ffed6a1d6` |
| builder image | `34ecc17078b364df195ad61253520b1cac487dca05773dc4b2fc2bacb0941941` |
| builder digest | `sha256:7b2e3415dc638ca4864912c9aa4905425561e21b9d08f1e60e4cfb0a3aa6ff8c` |

## Remaining hardware gate

This result verifies the v2 Linux routing/firewall/WireGuard DNS path, not a
complete phone hotspot. Hardware acceptance still requires:

- ath11k firmware, calibration, regulatory data, and a valid simultaneous
  client/AP combination;
- WPA-protected association and a real DHCP lease advertising the selected
  VPN-reachable resolver;
- an on-phone handshake and DNS response from the user-selected provider
  without storing credentials in Git;
- endpoint loss/recovery and IPv4/IPv6 leak checks from a real Wi-Fi client;
  and
- sustained throughput, thermal, charging, and battery-depletion tests.

No live authority follows from this offline result.
