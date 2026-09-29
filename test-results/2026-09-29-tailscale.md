# Tailscale on the phone, 2026-09-29

- Package: tailscale 1.102.4-1 (Arch ARM extra); `tailscaled` enabled at boot.
- Logged in by the user as host `rog5`, tailnet IPv4 100.64.0.1.
- The firewall (configs/firewall/rog5-firewall.nft) accepts iifname tailscale0
  and udp 41641; NetworkManager leaves tailscale0 unmanaged.
- SSH stays key-only (sshd); Tailscale SSH is not enabled.
- Old offline nodes rog5-server / rog5-validation-host are earlier setups.
