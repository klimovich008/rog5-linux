# Generation 39 QMP-UFS first-fixed-clock live result

Status: **consumed; target NCM disappeared; exact fallback passed; never retry or flash**.

Generation 39 temporarily booted the exact signed RAM-only candidate once.
The diagnostic SM8350 probe allocated its clock-data table and registered only
`rx_symbol_0`, then was designed to return before the second and third clocks,
OF clock-provider publication, PHY creation, or OF PHY-provider registration.
UFS core, platform, and host modules were absent, so no UFS enumeration or
phone-storage access was possible.

Exact retained host events (+0200):

- claim entered: 00:40:51.541;
- recovery product enumerated: 00:41:20.473;
- COMMIT intent created: approximately 00:41:41.912;
- recovery USB disconnected: 00:41:47.623;
- target product enumerated: 00:41:48.382;
- target carrier observed: 00:41:48.551;
- exact host profile active: 00:41:49.923;
- target USB disconnected: 00:41:59.655, 11.273 seconds after enumeration,
  11.105 seconds after carrier, and 9.732 seconds after host activation;
- Alpine enumerated: 00:42:17.818;
- exact fallback profile restoration completed: 00:42:20.174;
- strict fallback identity recorded: 00:42:22.372;
- intent resolved `FALLBACK_RETURNED`: 00:42:25.216.

The 11.273-second target window is effectively identical to Generations 37
and 38. Because Generation 39 never reached the second or third clock, the
failure is narrowed to clock-data allocation/metadata setup or the first
`devm_clk_hw_register_fixed_rate()` call. It does not distinguish those two
operations.

The Generation 38 host cleanup-race correction passed live: controller success
was followed by all exact one-transfer server cleanup markers within the
bounded grace, before the target cycle proceeded. Exact Alpine fallback
returned with boot ID `958d4bc0-b7e1-4414-be45-47be60afc140` and maximum
reported temperature 42.5 degrees C. Recovery observed one pre-existing pstore
record with no matching lineage; it cannot be attributed to this cycle. No
cycle-specific PMIC reset reason was available, so reset cause remains
unknown. Generation 39's exact claim is irreversibly consumed and must never
be retried.

Retained private evidence:
`/home/deck/.local/state/rog5-generation39-live-20260813.7hcnchT4`.
