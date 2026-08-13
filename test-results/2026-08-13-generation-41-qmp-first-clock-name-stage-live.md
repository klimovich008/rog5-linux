# Generation 41 QMP-UFS first-symbol-clock-name live result

Status: **consumed; name stage passed; exact fallback passed; never retry or flash**.

Generation 41 temporarily booted the exact signed RAM-only candidate once.
The SM8350 diagnostic probe allocated its clock-data table, constructed the
dynamic `rx_symbol_0` name, and returned before the first
`devm_clk_hw_register_fixed_rate()` call, the remaining clocks, OF
clock-provider publication, PHY creation, or OF PHY-provider registration.
UFS core, platform, and host modules were absent, so no UFS enumeration or
phone-storage access was possible.

The target reached stable NCM in 60.001 seconds and preserved the exact USB
identity, route, address, NetworkManager state, and non-drop firewall state for
the full 12.359-second control window. Exact Alpine fallback then returned with
boot ID `e8fae709-dd1f-4c44-bcff-cc7b985977bd`; strict fallback identity,
profile restoration, host cleanup, and intent resolution as
`FALLBACK_RETURNED` all passed. Maximum reported fallback temperature was
40.1 degrees C.

This clears clock-data allocation, metadata initialization, `dev_name()`,
`snprintf()`, and first-clock name construction. Together with Generation 39,
it isolates the earliest remaining boundary to the first fixed-rate CCF clock
registration. Earlier project evidence shows that global orphan reparenting
inside that registration can invoke callbacks belonging to unrelated
runtime-suspended clock providers; the next candidate must correct that CCF
boundary before advancing it.

Fallback pstore was empty. That is inconclusive and is not evidence that no
crash occurred. No cycle-specific PMIC reset reason was available. Generation
41's exact claim is irreversibly consumed and must never be retried.

Retained private evidence:
`/home/deck/.local/state/rog5-generation41-live-20260813.XuU0DsfO`.
