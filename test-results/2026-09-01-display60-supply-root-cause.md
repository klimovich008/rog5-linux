# Display60 V3 supply root cause

Result: **display FAIL with target SSH; fallback PASS**.

- V3 deliberately omitted Wi-Fi radio/WPA/DHCP units.
- Target `db445eb9-c48a-4e15-bf54-00d9f08fc66f` reached switch-root and SSH.
- NCM, status probe, battery (100%, Full, 8.556 V, 29.9 C), p24 read-only,
  Tailscale, and V11 fallback worked.
- Status userspace reported Wi-Fi unsupported as designed.
- `/dev/fb0` was absent; backlight count was zero.
- DSI PHY reported missing `vdds` and PLL lock failure.
- DSI host reported missing `vdda`, then deferred for missing `refgen`.
- No panic occurred. V3 is consumed and must never be retried.

Upstream `sm8350-hdk.dts` wires DSI `vdda` to PM8350B L6 (1.2 V) and DSI PHY
`vdds` to PM8350B L5 (0.88 V). The base DT already has `refgen-supply`, but the
exact kernel builds `CONFIG_REGULATOR_QCOM_REFGEN=m` and the module was not in
the early load path. The successor changes only those two DT properties and one
exact early REFGEN module; kernel Image and all unrelated DT properties remain
unchanged.
