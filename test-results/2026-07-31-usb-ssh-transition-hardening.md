# USB/SSH transition hardening

Date: 2026-07-31

Result: **PASS HOST/OFFLINE; avoidable USB route and SSH handshake races are
removed. Phone-cycle acceptance remains pending.**

## Network profile

The persistent NetworkManager profile is installed with this exact tuple:

```text
id=rog5-fallback-usb-ssh
uuid=fc2c5320-e072-4702-9803-0081e0f8ee3f
interface=enp4s0f3u1u2
ipv4.method=manual
ipv4.addresses=169.254.77.1/30
ipv4.gateway=
ipv4.dns=
ipv4.never-default=yes
ipv6.method=disabled
autoconnect=yes
autoconnect-priority=100
```

Recovery, target NFS, and Alpine fallback now use one isolated `/30` instead
of replacing a `/16` with a competing prefix during each transition. The
recovery controller pins the exact active profile UUID and complete tuple,
deactivates that profile while it owns the link, and restores the same UUID
after cleanup. Legacy `/16`, extra addresses, route residue, and profile
mutation fail closed.

The installed root-owned controller is byte-identical to the reviewed source,
has metadata `0:0:555:regular file`, and SteamOS read-only protection is
enabled after installation.

## SSH acceptance

Target runtime acceptance now uses one strict SSH connection to:

1. verify the exact kernel;
2. create a fresh volatile staging directory;
3. stream the exact read-only probe over standard input;
4. verify its owner, mode, and SHA-256;
5. execute it once and capture one canonical record; and
6. extract exactly one anchored boot ID from that same record.

Only initial TCP connection establishment may retry, at most three times and
only before the remote command starts. An established session is never
replayed. This replaces five independent SSH/SCP handshakes and closes the
largest software-controlled transition race. USB controller reset and gadget
re-enumeration across fastboot, recovery, and target Linux remain physical
events and cannot be removed by host SSH policy.

## Verification boundary

- Full local repository CI passed.
- GitHub `recovery-core` and `qemu-system` checks passed at commit `707abc1`.
- Host profile inspection and installed-controller hashing passed.
- The exact `lahaina` device remained in fastboot; no boot, transfer, SSH,
  phone-storage access, flash, or erase occurred during this checkpoint.

The earlier strict-SSH fallback cycle exercised the former `/16` profile. The
first live proof of the `/30` profile and single-session target transport must
come from the separately authorized r2 lifecycle.
