# Alpine fallback remote GUI and Linux tunnel — live result

Date: 2026-07-27

Result: **PASS for the persistent vendor-Alpine administration baseline;
not acceptance of Linux 7.1, accelerated rendering, KRDP, a public remote
path, or a persistent mainline release**.

## Scope

The operator returned the phone to its installed Alpine system. This
checkpoint verified the existing recovery/admin desktop, repaired the Linux
host's persistent SSH tunnel, and tested screen-off operation. It did not boot
or flash a candidate kernel, mount a PC-backed root, expose a service to the
internet, connect an external account, or configure a VPN provider.

The live device reported:

- Alpine Linux 3.24.0 on
  `5.4.134-qgki-perf-00001-g6c308144c23e`;
- an ext4 root on the existing physical userdata-backed filesystem;
- one running power-button indicator;
- screen state `off` and panel brightness `0/1023`;
- zero swap use and approximately 10.2 GiB available memory at the final
  snapshot; and
- exact installed copies of the repository desktop and Plasma launchers.

The active kernel is older than the separately proven temporary
`5.4.210-qgki-perf #20` artifact. This result must not be cited as a 5.4.210
or mainline test.

## Phone-side result

The following services were live:

| Component | Binding or state |
|---|---|
| Xvnc | display `:1`, TCP 5901 on loopback only |
| noVNC/websockify | TCP 6080 on loopback only |
| nested KWin Wayland | 1280x720 `wayland-1` session |
| Plasma shell | running in the nested session |
| Chromium | software-rendered Wayland, CDP TCP 9222 on loopback only |
| ttyd/tmux | writable terminal, TCP 7681 on loopback only |

A fresh framebuffer capture visibly showed the nested KDE Wayland compositor
and Chromium. The physical OLED remained off throughout the endpoint,
restart, and visual checks. Chromium displayed its restore-after-unclean-exit
bubble; CDP and the rendered browser window still worked. Clean browser
shutdown remains a follow-up rather than a reason to broaden this baseline.

An earlier same-boot comparison observed approximately 264 MiB less available
memory after starting the nested KDE/Chromium stack, with swap still unused.
That is a useful first bound, not a substitute for the staged PSS, idle-power,
thermal, and battery-depletion campaign.

## Linux host tunnel

The fail-first regression reproduced the host failure:
`PrivateTmp=yes` in an unprivileged Nobara user service caused OpenSSH to
reject the root-owned system SSH fragment. Independent transient-unit probes
passed with `NoNewPrivileges` and the socket-family restriction, and failed
only with `PrivateTmp`.

The production unit therefore removed only `PrivateTmp`; it retains:

- key-only, batch-mode SSH through the separately pinned `rog5-fallback`
  alias;
- `ExitOnForwardFailure` and keepalive failure detection;
- automatic restart every five seconds;
- an idempotent remote desktop-start hook;
- `NoNewPrivileges`, `UMask=0077`, and the AF_UNIX/IPv4/IPv6 allowlist; and
- exactly four host listeners, all on `127.0.0.1`: noVNC 6080, ttyd 7681,
  Chromium CDP 9222, and the future KRDP forward 13389.

The unit was enabled in the user manager. Its normal restart passed, then an
intentional termination of only the main SSH process produced one automatic
restart, a new tunnel process, a successful desktop-start hook, and restored
noVNC, ttyd, and CDP endpoint checks. The isolated NetworkManager USB profile
was changed to autoconnect while retaining a manual address, no gateway,
never-default routing, and disabled IPv6.

KRDP is not running in this Alpine fallback, so local port 13389 is reserved
but not an accepted desktop endpoint. noVNC, ttyd, and CDP have no independent
public authentication and are safe only while both ends remain loopback-only
behind the pinned SSH connection.

## Exact repository inputs

| Input | SHA-256 |
|---|---|
| `packaging/host-systemd-user/rog5-remote-tunnel.service` | `dc1a77c7ed141fc5ae9c515b68ab765d86523fe70334c0019ee506f916901b89` |
| `scripts/host/test-rog5-remote-tunnel-service.sh` | `385fa5cee9400bfc00acab11021f255b5245e8b46115f52aa50a01c903e04400` |
| `scripts/device/desktop-start.sh` | `4e2d83ddb605244f6ab5ffd60e50a528411fa0e9b4b6d1f0ca47997a4852c2e9` |
| `scripts/device/plasma-wayland-session.sh` | `7b36008d22a3da0986842317a28e25fe6c091c6dc72316a4cb062e2e1dc5f4ba` |

The fail-first sandbox regression is commit `67a6bbe`; the compatible unit is
commit `9792f71`. No private key path, host-key fingerprint, device identifier,
browser profile, raw log, or credential is included in this report.

## Remaining gates

- Supervise the target services natively rather than relying on the Alpine
  one-shot boot launcher plus host connection hook.
- Measure per-process PSS, idle power, thermals, and battery depletion with
  headless, KDE, browser, and remote-session states.
- Accept Linux 7.1 display, input, A660 GPU, repeated suspend/reboot, and
  physical-panel behavior before switching the target to DRM/KRDP.
- Configure an authenticated private overlay only after its external service
  and credential use receive separate confirmation.
- Run the real Wi-Fi/VPN fail-closed hotspot gate; only its namespace packet
  policy is currently accepted offline.
