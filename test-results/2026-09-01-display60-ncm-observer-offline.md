# Display60 post-switch NCM observer

Result: **offline PASS; no phone cycle**.

- Added one signed, read-only systemd observer for the display-diagnostic path.
- It records REFGEN, DSI, DRM, fb, backlight, status-screen and bounded filtered
  dmesg state as present, absent, unsupported or error.
- It sends one immutable record from `169.254.77.2` to `169.254.77.1:8077`; the
  host validates exact candidate, kernel release, boot ID, endpoints, framing,
  bounds, hex encoding and dmesg SHA-256.
- Optional missing display fields never trigger rollback. The observer contains
  no storage, backlight-write, reboot or panel-command path.
- Exact V5 sealed AArch64 BusyBox replay passed `sh -n`, `od -An -tx1 -v`,
  `tail -c`, `sha256sum`, and `nc -n -w -s` compatibility.
- Focused tests: 1.813 seconds. Active tier: 101.965 seconds.
- The timing lattice now requires a 1,020-second host envelope around the sealed
  900-second rollback and 90-second cleanup allowance.

The V5 kernel, DTB and module archive remain unchanged. A new phone cycle is
useful only after composing a fresh signed initramfs and separate one-use claim.
