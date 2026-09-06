# Arch Plasma/server userspace readiness — offline audit

Date: 2026-07-27

Result: **PASS OFFLINE for package availability, headless-first policy,
loopback-only remote-service configuration, credential absence, resource
controls, and the corrected future VPN-hotspot unit. HOLD for rebuilding and
booting a successor normal Arch root.**

No chroot service was started. No network profile, VPN provider, KRDP
credential, browser account, email, CV, machine identity, or user secret was
created or used. The phone remained in its persistent Alpine fallback.

## Sealed v10 diagnostic-root audit

The immutable v10 GPU diagnostic root contains the current normal userspace
package families needed for a modern server and Plasma desktop:

- Plasma Desktop/Workspace, KWin Wayland, XWayland, KScreen, Plasma-NM,
  greetd, and KRDP;
- Chromium, Node.js/npm, Python/pip, Git, ttyd, and tmux;
- NetworkManager, OpenSSH, WireGuard tools, nftables, and dnsmasq;
- Mesa, Vulkan Freedreno, PipeWire, and WirePlumber.

The `npm` launcher is an absolute in-root symlink to the installed npm CLI;
it resolves correctly when the root is mounted as `/`.

The boot policy is headless-first:

```text
default.target=multi-user.target
NetworkManager.service=enabled
sshd.service=enabled
rog5-server-inhibit.service=enabled
greetd.service=enabled for graphical.target
rog5-chromium-headless.service=disabled
rog5-ttyd.service=disabled
rog5-vpn-hotspot.service=disabled
```

The KRDP user override binds to loopback. WireGuard configuration,
NetworkManager connection profiles, KRDP settings, KWallet data, and machine
ID are absent. The `rog5` desktop account is present.

This proves offline userspace availability only. The diagnostic root still
needs accepted DRM/display/GPU hardware before a physical KWin/Plasma or KRDP
session can be called working.

## Immutable-root boundary

The v10 root intentionally inherits the manifest-pinned production root used
by the accepted diagnostic chain. It predates the newer locked
`rog5-agent` account and still contains the older, disabled Chromium service
that uses the interactive `rog5` account. It also contains the earlier,
disabled VPN-hotspot unit.

Neither file may be edited in place: doing so would invalidate the sealed v10
whole-root comparison. The disabled old Chromium unit must not be used for
personal-account automation. The next normal Arch root must instead be
rebuilt from current packaging, which provides the locked, no-login,
device-isolated, resource-bounded `rog5-agent` service.

## VPN-hotspot systemd diagnosis and correction

Read-only `systemd-analyze verify --root` found one ordering cycle in the old
disabled hotspot unit:

```text
network-online.target
  after dnsmasq.service
  after rog5-vpn-hotspot.service
  after network-online.target
```

Arch’s `dnsmasq.service` is `Before=network-online.target`. The project unit
was `After=network-online.target` and unnecessarily
`Before=dnsmasq.service`, closing the cycle.

Commit `8eaa152a2d6647b4cb1fdeb474afbb72b3bb0676` records the
fail-first packaging gate:

```text
FAIL VPN-hotspot unit cycles dnsmasq before network-online and itself after network-online
```

Commit `cae569df92471fa4556604b03a02bf3a3c3a5127` removes only that
`Before=` edge. Dnsmasq remains wanted and starts before
`network-online.target`; `bind-dynamic` lets it wait for the interface. The
hotspot profile remains non-autoconnecting, and the service still installs
the nftables kill-switch before `nmcli` raises the AP.

The staged Arch verifier now includes
`rog5-vpn-hotspot.service` in its `systemd-analyze verify` invocation. The
candidate unit has no ordering-cycle diagnostic, the static order contract
passes, and both the simulated-VPN and real-WireGuard production-path packet
suites continue to pass.

Important corrected inputs are:

| Input | SHA-256 |
|---|---|
| VPN-hotspot service | `4c29a2cb097a081b9dc4b18abc330d5f6401211cad4178de2b77eb73f0dd5525` |
| fail-first/order contract | `88f9e96f58e77de429764fa6f766b2215be80284a99e96964105f61dfb1c8a11` |
| fail-closed packet suite | `f1675b2da560c76e2b8d1779adaf94b6f8ef8313696a40fa860c87855840f1f9` |
| staged-root verifier | `e8ab452b1994ffbffe0a0e1db32e3b2f66866d813e8f32b03713fb4f2545e87f` |

## Independent userspace contracts

The current repository tests also pass:

```text
PASS browser automation is locked, isolated from the desktop account, loopback-only, credential-free, and on-demand
PASS redacted runtime collector covers desktop, automation, power, display, thermal, and interface counters
PASS desktop supervisor is singleton, leaves healthy services alone, and retries a missing browser without touching boot state
PASS idempotent screen off/on/toggle test
PASS Linux host remote-tunnel service is loopback-only, identity-pinned, reconnecting, and desktop-supervising
PASS Linux rootfs tools pin signed input, preserve metadata, and avoid phone writes
PASS VPN-hotspot systemd order is cycle-free by contract and covered by the staged-root verifier
```

The remote stack stays loopback-only. The default server target avoids Plasma,
KRDP, ttyd, Chromium, and hotspot RAM/CPU cost until explicitly requested.
The current hardened browser service is capped at two CPUs, 2 GiB RAM,
512 MiB swap, and 256 tasks.

## Desktop choice and remaining gate

The target remains normal KDE Plasma Desktop on Wayland. GNOME would duplicate
the compositor, display-manager, portal, and background-service stack without
solving a demonstrated blocker, so it remains a fallback evaluation only if
Plasma fails a concrete requirement.

Before promotion:

1. build a fresh normal Arch archive from current packaging;
2. run the complete AArch64 staged-root verifier before archival and after a
   clean metadata-preserving extraction;
3. prove the corrected VPN unit, locked `rog5-agent`, loopback bindings,
   secret absence, and headless default in that exact archive;
4. derive a new non-diagnostic export without altering or reusing v10
   authorization; and
5. only after the display/GPU gates, test physical Plasma/KRDP, panel-off
   operation, RAM/idle CPU, thermals, and battery use on the phone.
