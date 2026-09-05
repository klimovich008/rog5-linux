# Persistent Tailscale V10 — live runtime PASS, login pending

- Exact-head GitHub run `33279225715` passed head, merge, QEMU and publication
  for commit `7d1b903238d036ca2df433a2636b2f3d1754afe1`.
- V9 stopped cleanly with all 117 UFS nodes read-only. Slot A remained active
  during the one p24-only transfer.
- V10 sparse SHA-256 `915b4a32…899e`; all six chunks completed in 72.639
  seconds. No GPT, boot, firmware or other partition changed.
- First V10 boot ID `75a07173-cb47-43b1-8586-2d0ea2cdab15` reached stable
  pinned SSH at 10.77.0.2 in 57 seconds. The dedicated shared host profile
  autoconnected at 10.77.0.1/30 without changing the recovery profile.
- Signed bundle ID, V49 high-speed marker, zero UFS errors, systemd `running`,
  zero failed units, exact 117-node/two-writable-node scope, p23 state and
  persistent SSH identity passed.
- `rog5-tailscaled.service` started automatically. The helper record proves
  Tailscale 1.102.3, p23 state, tmpfs executables and fixed 10.77.0.2/30
  routing. TUN is active.
- Power remained Full/Good at 8.673 V and 29.9°C, +262 mA side USB input, and
  35.5°C maximum thermal.

Remaining external gate: approve the active Tailscale browser login, then
verify the assigned Tailscale IP/SSH and one unattended reboot.
