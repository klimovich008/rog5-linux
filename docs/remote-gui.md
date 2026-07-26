# Remote GUI and browser automation

The server exposes remote tools only on loopback. Reach them through SSH forwarding or an authenticated private overlay; do not publish these ports on the internet.

| Service | Loopback port | Purpose |
|---|---:|---|
| KRDP | 3389 (forwarded locally to 13389) | active Plasma Wayland session through an SSH tunnel |
| ttyd | 7681 | persistent tmux terminal for maintenance and agent CLIs |
| Chromium CDP | 9222 | headless automation endpoint for the dedicated browser profile |

The Arch target uses one Plasma Desktop Wayland compositor. KRDP shares that session; it does not start a second Xvnc/Openbox desktop. Panel DPMS may be off while the compositor and remote session continue running. For the lowest idle use, stay in `multi-user.target` and use SSH or loopback ttyd; switch to `graphical.target` only when KRDP or the local UI is needed.

The staged KRDP user-service override forces `krdpserver` to `127.0.0.1`. The host helper forwards KRDP, ttyd, Chromium CDP, and the legacy recovery noVNC port in one SSH process:

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

None of this is live on Linux 7.1 yet. Rejected recovery v6 did enumerate
ACM/NCM on Windows and exposed the SSH port, but ACM writes timed out, no SSH
credential was used, the RAM-only/storage gates were not run, and rollback did
not pass. A rebuilt recovery must pass those gates before Arch, Plasma, or
KRDP can be tested.
