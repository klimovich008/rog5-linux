# Generation 40 QMP-UFS allocation-stage live result

Status: **consumed; allocation stage passed; exact fallback passed; never retry or flash**.

Generation 40 temporarily booted the exact signed RAM-only candidate once.
The SM8350 diagnostic probe allocated and initialized its three-entry clock
table, then returned before constructing or registering `rx_symbol_0`, OF
clock-provider publication, PHY creation, or OF PHY-provider registration.
UFS core, platform, and host modules were absent, so no UFS enumeration or
phone-storage access was possible.

The target reached stable NCM in 59.680 seconds and preserved the exact USB
identity, route, address, NetworkManager state, and non-drop firewall state for
the full 12.173-second control window. Exact Alpine fallback then returned with
boot ID `dc36468d-3f59-46c1-9899-8ddc9f816471`; strict fallback identity,
profile restoration, host cleanup, and intent resolution as
`FALLBACK_RETURNED` all passed. Maximum reported fallback temperature was
40.8 degrees C.

This clears clock-data allocation and metadata initialization. Generation 39
had included both dynamic first-clock name construction and the first
`devm_clk_hw_register_fixed_rate()` call, so the remaining failure boundary is
one of those two operations—not clock registration alone.

Recovery observed one pre-existing pstore record with no matching lineage,
while fallback pstore was empty. That is inconclusive and is not evidence that
no crash occurred. No cycle-specific PMIC reset reason was available.
Generation 40's exact claim is irreversibly consumed and must never be retried.

Retained private evidence:
`/home/deck/.local/state/rog5-generation40-live-20260813.ZdglnDdg`.
