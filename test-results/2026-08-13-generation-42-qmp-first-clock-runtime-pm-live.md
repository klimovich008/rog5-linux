# Generation 42 QMP-UFS first-clock runtime-PM live result

Status: **consumed; first clock passed; exact fallback passed; never retry or flash**.

Generation 42 temporarily booted the exact signed RAM-only candidate once.
The generic CCF correction held balanced runtime-PM references for registered
clock providers outside `prepare_lock`; the SM8350 QMP-UFS diagnostic probe
then completed the first fixed-rate `rx_symbol_0` clock registration and
returned before the second and third clocks, OF clock-provider publication,
PHY creation, or provider registration. UFS core, platform, and host modules
were absent, so no UFS enumeration or phone-storage access was possible.

The target reached stable NCM in 61.333 seconds and preserved the exact USB
identity, route, address, NetworkManager state, and non-drop firewall state for
the full 12.246-second control window. Exact Alpine fallback then returned with
boot ID `fac10c66-6a43-464a-9109-ef27c788efc6`; strict fallback identity,
profile restoration, host cleanup, and intent resolution as
`FALLBACK_RETURNED` all passed. Maximum reported fallback temperature was
40.5 degrees C.

This hardware result clears the first fixed-rate clock registration with the
generic CCF runtime-PM correction. The next discriminator may cross the second
fixed-rate clock while retaining the same correction and returning before the
third clock and every provider/PHY boundary.

Fallback pstore was empty and no cycle-specific PMIC reset reason was
available. Both observations are inconclusive. Generation 42's exact claim is
irreversibly consumed and must never be retried.

Retained private evidence:
`/home/deck/.local/state/rog5-generation42-live-20260813.Qm7r2qGj`.
