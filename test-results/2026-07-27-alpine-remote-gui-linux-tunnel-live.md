# Alpine fallback remote GUI and Linux tunnel — live result

Date: 2026-07-27

Result: **PASS for the persistent vendor-Alpine administration baseline;
not acceptance of Linux 7.1, accelerated rendering, KRDP, a public remote
path, or a persistent mainline release**.

## Scope

The operator returned the phone to its installed Alpine system. This
checkpoint verified the existing recovery/admin desktop, repaired the Linux
host's persistent SSH tunnel, added bounded process supervision, and tested
screen-off operation. It did not boot or flash a candidate kernel, mount a
PC-backed root, expose a service to the internet, connect an external account,
or configure a VPN provider.

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
or mainline test. Its module tree has none of the matching ADSP/battery
modules used by the 5.4.210 charging launcher, and its power-supply class was
empty. The launcher correctly refused the kernel mismatch; no incompatible
module was loaded. Battery status, current, and depletion therefore cannot be
accepted on this boot.

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

Chromium later exited without an OOM signature, proving that connection-level
SSH restart was insufficient supervision. A new phone-side supervisor checks
Xvnc, websockify, KWin, Plasma, Chromium, and ttyd every 30 seconds and invokes
the existing idempotent launcher only when a process is missing. Two induced
main-browser `TERM` tests restored a new Chromium/CDP endpoint in 11 and 8
seconds respectively, retained one supervisor, kept swap unused, and left the
physical panel off.

An earlier same-boot comparison observed approximately 264 MiB less available
memory after starting the nested KDE/Chromium stack, with swap still unused.
That is a useful first bound, not a substitute for the staged PSS, idle-power,
thermal, and battery-depletion campaign.

The redacted collector then reported 1,035,504 KiB aggregate used memory,
10,547,512 KiB available, 305,016 KiB PSS across the selected Plasma/KWin
processes, zero swap, and a 42.5 °C maximum readable thermal-zone sample.
A separate 15-second quiet sample measured 0.37% aggregate CPU busy and
41.5 °C maximum temperature. These are short diagnostic observations, not
idle-power or battery acceptance.

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
- an idempotent remote singleton-supervisor `start` hook;
- `NoNewPrivileges`, `UMask=0077`, and the AF_UNIX/IPv4/IPv6 allowlist; and
- exactly four host listeners, all on `127.0.0.1`: noVNC 6080, ttyd 7681,
  Chromium CDP 9222, and the future KRDP forward 13389.

The first prototype kept the remote supervisor as the forwarding SSH
command. An induced tunnel exit left that shell reparented to PID 1, and the
reconnect created a second supervisor. That prototype was rejected; the
service was stopped and both exact processes were removed.

The accepted design keeps `ssh -N` as the host service's main process. Its
post-connect action starts a phone-side pidfile/flock singleton that survives
host-tunnel loss independently. A repeated `start` is a no-op. After an
induced main-SSH exit, systemd created a new forwarding process while the
same phone supervisor remained, exactly one supervisor existed, and noVNC,
ttyd, and CDP all passed. The isolated NetworkManager USB profile was changed
to autoconnect while retaining a manual address, no gateway, never-default
routing, and disabled IPv6.

KRDP is not running in this Alpine fallback, so local port 13389 is reserved
but not an accepted desktop endpoint. noVNC, ttyd, and CDP have no independent
public authentication and are safe only while both ends remain loopback-only
behind the pinned SSH connection.

## Exact repository inputs

| Input | SHA-256 |
|---|---|
| `packaging/host-systemd-user/rog5-remote-tunnel.service` | `91b93017f52822320c6161709d9e7bd8cfe657f8f9a033b0e2a7cea7709515f1` |
| `scripts/host/test-rog5-remote-tunnel-service.sh` | `6331836c4935a4e3055d4ab4b95eee3cb435160d37d08f18b5d3a947755c5ddf` |
| `scripts/device/desktop-supervisor.sh` | `e5dea2bce370ec82cd2d6f96ce1172cca59ffd1d3e5997a9e88f3facfb8527fb` |
| `scripts/device/test-desktop-supervisor.sh` | `d9b3daf0fa8ac10335caa42519b42969635b67535e121f6db44ccf2d269d9a13` |
| `scripts/device/install-runtime-tools.sh` | `5237c66fe6d68e8d3ee55fa87e20614b1d76fddae6bbb3edfe9801b9f32f1c4a` |
| `scripts/device/desktop-start.sh` | `4e2d83ddb605244f6ab5ffd60e50a528411fa0e9b4b6d1f0ca47997a4852c2e9` |
| `scripts/device/plasma-wayland-session.sh` | `7b36008d22a3da0986842317a28e25fe6c091c6dc72316a4cb062e2e1dc5f4ba` |

The fail-first sandbox regression is commit `67a6bbe`; the compatible unit is
commit `9792f71`. Desktop supervision has fail-first commits `95bc8b8` and
`f7eaf66`; the accepted singleton implementation is commit `88c764a`. No
private key path, host-key fingerprint, device identifier, browser profile,
raw log, or credential is included in this report.

## Remaining gates

- Start the supervisor directly from the eventual target init system. The
  Alpine fallback currently bootstraps it through the first host connection,
  after which it survives tunnel reconnects.
- Measure per-process PSS, idle power, thermals, and battery depletion with
  headless, KDE, browser, and remote-session states.
- Repeat battery measurements only on a kernel with its matching charger and
  ADSP modules; never force-load the 5.4.210 modules into installed 5.4.134.
- Accept Linux 7.1 display, input, A660 GPU, repeated suspend/reboot, and
  physical-panel behavior before switching the target to DRM/KRDP.
- Configure an authenticated private overlay only after its external service
  and credential use receive separate confirmation.
- Run the real Wi-Fi/VPN fail-closed hotspot gate; only its namespace packet
  policy is currently accepted offline.
