# VPN-backed hotspot real-WireGuard gate — offline result

Date: 2026-07-27

Result: **PASS OFFLINE for a real kernel WireGuard handshake and encrypted
hotspot-client packet through the production kill-switch. No phone, radio,
VPN provider, user credential, external endpoint, or external network was
used.**

## Fail-first boundary

Commit `297dde875e45624f6f5d667ba7c82abb32a0c616` records the missing
real-WireGuard test:

```text
FAIL missing real-WireGuard hotspot packet test
```

Commit `7b493477bb7b02012b7377ec7f9c6209d6908a34` adds one
credential-free privileged-container test. It does not alter the production
script or service.

## Test topology

The test refuses to start unless its container has no non-loopback network
interface. It then builds only local network namespaces and veth pairs:

```text
hotspot client 10.42.0.2
        |
      wlan0 10.42.0.1
        |
      wg0 10.99.0.1 === encrypted WireGuard === peerwg0 10.99.0.2
        |                                      |
  198.51.100.1/30 ----- local veth ----- 198.51.100.2/30
```

`198.51.100.0/24` is documentation-only TEST-NET space. It exists only on
the local veth underlay. The container has no route or interface to an
external network.

The test generates two disposable WireGuard private keys under a mode-`0700`
temporary directory with `umask 077`, verifies both key files are mode
`0600`, and never prints them. It configures one real kernel WireGuard
interface per peer, then runs the unchanged production sequence:

```text
PASS vpn-hotspot up ap=wlan0 vpn=wg0
PASS vpn-hotspot check ap=wlan0 vpn=wg0
PASS vpn-hotspot down ap=wlan0 vpn=wg0
PASS real WireGuard handshake, encrypted hotspot packet, and cleanup
```

A Python standard-library UDP echo packet originates in the isolated hotspot
client, traverses the production nftables forwarding and masquerade rules,
crosses the encrypted WireGuard tunnel, and returns. Both peers must report a
nonzero latest-handshake timestamp, and the phone-side interface must report
nonzero encrypted receive and transmit counters.

Teardown removes the production nftables table, restores both forwarding
sysctls, removes every temporary interface and namespace, explicitly deletes
both key files, and removes the temporary directory. A second complete run
passes in a fresh disposable container, followed by the original
simulated-VPN IPv4/IPv6 leak, unsolicited ingress, VPN-loss, and cleanup suite
in its own fresh container.

The same test in a normally network-connected container fails before
temporary storage or keys are created:

```text
FAIL test namespace is not network-disabled
```

## Exact inputs

| Input | SHA-256 |
|---|---|
| production `vpn-hotspot.sh` | `f270cc05ebf2776179f9eb7e5f1f96d3ce76f5b144c30b961cff26f923fe849d` |
| production service | `3f36a12b9df5c1d331eae13be5107fbdc2b32ab7a785b2b8694270ce007b022b` |
| existing fail-closed packet test | `a6643d0bd2528e5827161807596bac44cf47852868f60423b65ab26d4cc364c9` |
| real-WireGuard packet test | `c7905a76003a552d1463a450b281e834f37f18534418016fe6e9c4068c7c3868` |
| real-WireGuard contract test | `bb3b32ccd44d204cdd35227881a379f7bfd2d357473136af0b82ee5e5210b1e5` |
| local builder image | `34ecc17078b364df195ad61253520b1cac487dca05773dc4b2fc2bacb0941941` |

Both new scripts pass shell syntax and ShellCheck. The static
network-isolation/ephemeral-key contract, real handshake test, repeat run,
original packet suite, and `git diff --check` also pass.

## Remaining hardware gate

This result accepts the Linux WireGuard cryptographic and production
routing/firewall path, not the phone radio or a VPN provider. Hardware
acceptance still requires:

- ath11k firmware, calibration, regulatory data, and a valid simultaneous
  client/AP interface combination;
- WPA-protected AP association, DHCP, and VPN-reachable DNS;
- an on-phone handshake to the user-selected VPN endpoint without storing
  secrets in the repository;
- endpoint loss/recovery and IPv4/IPv6 DNS-leak tests with a real client; and
- sustained throughput, thermal, charging, and battery-depletion tests.
