# Generation 43 QMP-UFS second-clock runtime-PM live result

Status: **consumed; second clock passed; exact fallback passed; never retry or flash**.

Generation 43 temporarily booted the exact signed RAM-only candidate once.
The generic CCF correction held balanced runtime-PM references for registered
clock providers outside `prepare_lock`; the SM8350 QMP-UFS diagnostic probe
then completed both fixed-rate `rx_symbol_0` and `rx_symbol_1` clock
registrations and returned before `tx_symbol_0`, OF clock-provider
publication, PHY creation, or provider registration. UFS core, platform, and
host modules were absent, so no UFS enumeration or phone-storage access was
possible.

The target reached stable NCM in 60.264 seconds and preserved the exact USB
identity, route, address, NetworkManager state, and non-drop firewall state for
the full 12.014-second control window. Exact Alpine fallback then returned with
boot ID `0d9cf09b-5f22-4c7f-bb41-93e414f1725c`; strict fallback identity,
profile restoration, host cleanup, and intent resolution as
`FALLBACK_RETURNED` all passed. Maximum reported fallback temperature was
39.8 degrees C.

This hardware result clears the second fixed-rate clock registration with the
generic CCF runtime-PM correction. The next discriminator may cross the third
fixed-rate `tx_symbol_0` clock while retaining the same correction and
returning before OF clock-provider publication and every provider/PHY
boundary.

Fallback pstore was empty and no cycle-specific PMIC reset reason was
available. Both observations are inconclusive. Generation 43's exact claim is
irreversibly consumed and must never be retried.

Retained private evidence:
`/home/deck/.local/state/rog5-generation43-live-20260813.1wcgdCGR`.
