# Display60 V6 host-profile race

Result: **R6/R7 infrastructure failure; exact fallback PASS**.

- Source exitrd entered the exact V6 kernel and disconnected normally.
- On USB re-enumeration, NetworkManager autoactivated the normal V11 profile,
  leaving only `10.77.0.1/30`; the target requires `169.254.77.1/30`.
- The pre-switch stage receiver therefore captured no frame. The post-switch
  collector was incorrectly gated on that stage, and its target retry expired.
- After the exact dual-address host profile was restored, the target answered
  `169.254.77.2` continuously until the sealed 900-second rollback.
- Fresh V11 boot `e8b6eff6-4ee3-4920-b4d9-018fe5b7997a`, p24 read-only,
  battery Good at 8.562 V and 30.0 C, and irreversible V6 claim consumption
  passed. No phone storage was modified.

The regression starts the exact-address collector before COMMIT and verifies it
waits through `EADDRNOTAVAIL`. A successor must keep the dual-address profile as
the sole autoconnect owner across the target enumeration. V6 must never retry.
