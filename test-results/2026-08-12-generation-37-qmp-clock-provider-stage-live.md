# Generation 37 QMP-UFS clock-provider-stage live result

Status: **consumed; target NCM disappeared; exact fallback passed; never retry or flash**.

Generation 37 temporarily booted the exact signed RAM-only candidate once. The
target configured its exact NCM gadget and waited for stable carrier before
loading only `phy-qcom-qmp-ufs.ko`. The diagnostic SM8350 probe advanced past
the Generation 36 boundary through all of `qmp_ufs_register_clocks()`, then was
designed to return before PHY creation or OF PHY-provider registration. UFS
core, platform, and host modules were absent, so no UFS enumeration or phone
storage access was possible.

Exact retained host events (+0200):

- target product enumeration: 23:01:55.588;
- target carrier observed: 23:01:55.790;
- exact host profile active: 23:01:57.307;
- target USB disconnect: 23:02:06.863, 11.275 seconds after enumeration and
  9.556 seconds after host activation;
- Alpine USB enumeration: 23:02:25.026;
- exact fallback profile active: 23:02:26.873;
- strict fallback identity recorded: 23:02:29.438;
- intent resolved as `FALLBACK_RETURNED`: 23:02:32.288.

Generation 36 completed a 12.294-second post-module NCM control window, while
Generation 37 lost NCM with timing close to Generation 33's 11.419-second
failure. The only QMP-UFS probe delta was the call to
`qmp_ufs_register_clocks()`. This localizes the failure to that function but
does not yet distinguish its three fixed-rate symbol-clock registrations from
OF clock-provider publication or its cleanup action.

The pinned Alpine fallback returned with boot ID
`d837dd5c-c7f8-41dd-8238-0796a2fcdf42` and maximum reported temperature
46.1 degrees C. Fallback profile restoration, strict SSH identity, intent
resolution, host cleanup, and Steam socket restoration passed. No
cycle-specific pstore or PMIC reset evidence was captured; absence remains
inconclusive. The exact claim is irreversibly consumed and Generation 37 must
never be retried.

Retained private evidence:
`/home/deck/.local/state/rog5-generation37-live-20260812.v5bPbk5O`.
