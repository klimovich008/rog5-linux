# Remote GUI and browser automation

The server exposes remote tools only on loopback. Reach them through SSH forwarding or an authenticated private overlay; do not publish these ports on the internet.

| Service | Loopback port | Purpose |
|---|---:|---|
| Alpine fallback noVNC | 6080 | software-rendered recovery/admin desktop |
| KRDP | 3389 (forwarded locally to 13389) | active Plasma Wayland session through an SSH tunnel |
| ttyd | 7681 | persistent tmux terminal for maintenance and agent CLIs |
| Chromium CDP | 9222 | headless automation endpoint for the dedicated browser profile |

The Arch target uses one Plasma Desktop Wayland compositor. KRDP shares that session; it does not start a second Xvnc/Openbox desktop. Panel DPMS may be off while the compositor and remote session continue running. For the lowest idle use, stay in `multi-user.target` and use SSH or loopback ttyd; switch to `graphical.target` only when KRDP or the local UI is needed.

The staged KRDP user-service override forces `krdpserver` to `127.0.0.1`.
The host helper forwards KRDP, ttyd, Chromium CDP, and the legacy recovery
noVNC port in one SSH process.

## Persistent tunnel on a Linux host

First configure the `rog5-fallback` SSH host alias with the approved private
key and a pinned host key. Neither credential belongs in this repository or
in the service unit. The USB NetworkManager profile must assign the host
`169.254.77.1/16`, install no gateway, remain never-default, and autoconnect
when the phone appears. For the profile used during development:

```sh
rog5_usb_profile=rog5-usb-temporary
nmcli connection modify "$rog5_usb_profile" \
  connection.autoconnect yes \
  ipv4.method manual ipv4.addresses 169.254.77.1/16 \
  ipv4.never-default yes ipv6.method disabled
```

Install the reconnecting user service from the repository:

```sh
scripts/host/test-rog5-remote-tunnel-service.sh
systemctl --user link \
  "$PWD/packaging/host-systemd-user/rog5-remote-tunnel.service"
systemctl --user daemon-reload
systemctl --user enable --now rog5-remote-tunnel.service
systemctl --user status rog5-remote-tunnel.service
```

The unit retries while the phone is absent and invokes the idempotent Alpine
desktop launcher after every successful connection. It retains
`NoNewPrivileges`, a restricted socket-family allowlist, key-only SSH, and
four explicit loopback forwards. `PrivateTmp` is intentionally absent:
on this Nobara host, enabling it in a user service reproducibly makes OpenSSH
reject the otherwise valid root-owned system SSH fragment before connecting.

With the service active, use:

- noVNC: `http://127.0.0.1:6080/vnc.html`;
- ttyd: `http://127.0.0.1:7681/`;
- Chromium DevTools discovery: `http://127.0.0.1:9222/json/version`; and
- KRDP, once configured on the Arch target: `127.0.0.1:13389`.

The noVNC, ttyd, and CDP services have no independent internet-facing
authentication. Their security boundary is the key-authenticated SSH tunnel,
so their phone and host listeners must stay on loopback.

## Windows host

The PowerShell helper provides the same four forwards:

```powershell
powershell -NoProfile -File scripts/host/Start-RemoteTunnel.ps1 `
  -SshKey C:\path\to\rog5_ed25519 `
  -SshHost device-debug-address
```

Connect Windows Remote Desktop to `127.0.0.1:13389`. KRDP credentials are created after first boot and are not stored in the image or repository. The Xvnc/noVNC launchers remain only as vendor-baseline diagnostics and are not part of the Arch target.

ttyd binds to `127.0.0.1:7681` and attaches to a persistent tmux session. Both writable ttyd and Chromium are disabled by default and started on demand:

```sh
systemctl start rog5-ttyd.service
systemctl start rog5-chromium-headless.service
```

Neither endpoint is a substitute for SSH authentication.

Browser automation runs separately from the interactive Plasma user: the
locked `rog5-agent` account owns its profile at
`/var/lib/rog5-agent/chromium`, and the loopback-only service remains disabled
until explicitly started. Its systemd cgroup caps it at two CPUs, 2 GiB RAM,
512 MiB swap, and 256 tasks, with lower CPU/I/O scheduling weight and restart
throttling. The image contains no browser session or provider credential.
Initial capability is read, summarize, and draft. Connecting an account,
sending mail, or submitting job applications stays behind explicit approval,
as described in
[security-automation.md](security-automation.md).

The persistent Alpine 3.24 fallback now passes a narrower live checkpoint on
its installed `5.4.134` vendor kernel: nested KWin Wayland, Plasma,
software-rendered Chromium, ttyd, and noVNC remain usable while the physical
panel state is `off` and brightness is zero. The Linux host tunnel is enabled,
loopback-only, and recovered after an induced SSH-process exit. See the
[live report](../test-results/2026-07-27-alpine-remote-gui-linux-tunnel-live.md).
This does not accept Linux 7.1 display/GPU support, a physical DRM Plasma
session, KRDP, or a wide-area VPN path.
