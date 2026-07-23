# Remote GUI and browser automation

The server exposes remote tools only on loopback. Reach them through SSH forwarding or an authenticated private overlay; do not publish these ports on the internet.

| Service | Loopback port | Purpose |
|---|---:|---|
| ttyd | 7681 | persistent tmux terminal for maintenance and agent CLIs |
| noVNC/websockify | 6080 | on-demand KDE desktop in a browser |
| Xvnc | 5901 | private backend for noVNC |
| Chromium CDP | 9222 | automation endpoint for the dedicated browser profile |

The physical Plasma Mobile session and nested remote KDE session are separate compositors. Both currently use software rendering because the vendor KGSL driver is rejected. For lowest idle memory, keep the remote desktop stopped and use ttyd/SSH; start KDE/Chromium only when visual work is required. `rog5-desktop-stop` targets only the nested `wayland-1` compositor and dedicated Chromium profile; it leaves the physical `wayland-0` Plasma session and ttyd running.

On Windows, `scripts/host/Start-RemoteTunnel.ps1` opens loopback-only forwards for noVNC and ttyd in one hidden SSH process. The script refuses to replace an occupied local port and records its process ID in an ignored local file.

```powershell
powershell -NoProfile -File scripts/host/Start-RemoteTunnel.ps1 -SshKey C:\path\to\rog5_ed25519 -SshHost device-debug-address
```

`desktop-start.sh` repairs only a stale `:1` Xvnc lock after verifying that its recorded PID is not an Xvnc process. It deliberately does not remove wildcard X sockets, because that could break the physical session. VNC authentication is disabled only because both VNC ports bind to `127.0.0.1`; SSH/private-network authentication is the boundary.

Browser automation should use the dedicated `chromium-server` profile. Initial capability is read, summarize, and draft. Sending mail or submitting job applications stays behind explicit approval, as described in [security-automation.md](security-automation.md).
